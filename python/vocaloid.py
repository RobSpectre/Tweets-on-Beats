import subprocess, midi
from canoris import Canoris, Template, Task

'''
at the character where you're encoding:
    do the next 2 characters represent a phoneme together?
'''

CANORIS_URL = 'http://api.canoris.com'
CANORIS_KEY = '867c069719dc45db930c7d9749de8659'


TRANSLATION_TABLE = {
        'p': 'p',               #
        'b': 'b',              #
        't': 't',               #
        'd': 'd',               #
        'tS': 'tS',               #    church
        'dZ': 'dZ',               #    judge
        'k': 'k',               #
        'g': 'g',               #
        'f': 'f',               #
        'v': 'v',               #
        'T': 'T',               #    thin
        'D': 'D',            #    this
        's': 's',               #
        'z': 'z',               #
        'S': 'S',               #    shop
        'Z': 'Z',               #    pleasure
        'h': 'h',               #
        'm': 'm',               #
        'n': 'n',               #
        'N': 'N',               #    sing
        'l': 'l',               #
        'r': 'r',               #    red (Omitted if not immediately followed by a vowel).
        'j': 'j',               #    yes
        'w': 'w',               #
        '@': '@',               #    alpha    schwa
        '3': '@',               #    better
        '3:': 'U@',               #    nurse
        '@L': 'l',               #    simple
        '@2': 'D',               #    the    Used only for "the".
        '@5': 'tU',              #    to    Used only for "to".
        'a': '{',               #    trap
        'a2': '@',               #    about    This may be '@'               # or may be a more open schwa.
        'A:': '@',               #    palm
        'A@': 'A@',               #    start
        'E': '{',               #    dress
        'e@': 'e@',               #    square
        'I': 'I',               #    kit
        'I2': 'I',               #    intend    As 'I'               #, but also indicates an unstressed syllable.
        'i':  'i:',              #    happy    An unstressed "i" sound at the end of a word.
        'i:': 'i:',               #    fleece
        'i@': 'I@',               #    near
        '0': 'Q',               #    lot
        'V': 'V',               #    strut
        'u:': 'u:',               #    goose
        'U': 'U',               #    foot
        'U@': 'U@',               #    cure
        'O:': 'O:',               #    thought
        'O@': 'O@',               #    north
        'o@': 'O@',                #    force
        'aI': 'aI',               #    price
        'eI': 'eI',               #    face
        'OI': 'OI',               #    choice
        'aU': 'aU',               #    mouth
        'oU': '@U',               #    goat
        ' ': ' ',               # keep spaces!
                     }


def init_canoris():
    Canoris.set_api_key(CANORIS_KEY)
    Canoris.set_api_base(CANORIS_URL)

class VocaloidTask():
    def __init__(self, text, midi_path):
        self.midi_path = midi_path
        # drop in Rob's function here:
        filter = TweetFilter(text)
        self.text = filter.read()
        # end Rob's function
        self.sequence = self.__generate_sequence(
                            self.__espeak_to_vocaloid_phonemes(
                                self.__get_espeak_output(text)),
                                midi_path)


        new_task = Task.create_task('vocaloid', {'voice': 'lara', 'sequence': self.sequence})
        # we're going to check this later, because it won't be done right away.
        self.__save_task(new_task)

    @staticmethod
    def __get_espeak_output(input):
        p = subprocess.Popen(['espeak', '-x', '-q', input], stdout=subprocess.PIPE)
        p.wait()
        return p.communicate()[0]

    @staticmethod
    def __espeak_to_vocaloid_phonemes(input):
        result = []
        intermediate_result = []
        still_to_translate = input
        while len(still_to_translate) > 0:
            if still_to_translate[0] == ' ':
                still_to_translate = still_to_translate[1:]
                if len(intermediate_result) > 0:
                    result.append(intermediate_result)
                intermediate_result = []
                continue
            # take the first 2 characters, see if it's present in the map
            if len(still_to_translate) > 1 and still_to_translate[0:2] in TRANSLATION_TABLE:
                intermediate_result.append(TRANSLATION_TABLE[still_to_translate[0:2]])
                still_to_translate = still_to_translate[2:]
                continue
            else:
                tt = still_to_translate[0]
                still_to_translate = still_to_translate[1:]
                if tt in TRANSLATION_TABLE:
                    intermediate_result.append(TRANSLATION_TABLE[tt])
                    continue
                else:
                    # we can't find the phoneme, let's drop it.
                    pass
        # check if we have some leftover intermediate_results
        if len(intermediate_result) > 0:
            result.append(intermediate_result)
        return result

    @staticmethod
    def process_midi_file(midi_path):
        midifile = midi.MidiFile()
        midifile.open(midi_path)
        midifile.read()
        midifile.close()

        track = midifile.tracks[0]
        events = []
        last_time = 0
        note_closed_p = True
        for event in track.events:
            print event.time
            if event.type == 'NOTE_OFF' and not note_closed_p :
                # make sure we don't run into an exception if the midi file
                # is malformed (e.g. doesn't start with a noteon)
                if len(events) > 0:
                    events[-1]['d'] = event.time - last_time
                    last_time = event.time
                    note_closed_p = True
                last_time = event.time
            if event.type == 'NOTE_ON':
                last_time = event.time
                new_note = {}
                # if we're dealing with a note
                if event.velocity > 0:
                    new_note['v'] = event.velocity
                    new_note['p'] = event.pitch
                    new_note['r'] = False
                else:
                    events[-1]['r'] = True
                note_closed_p = False
                events.append(new_note)
        return events

class TweetFilter:
    '''          
    Implementation
    text = "@dn0t I'll send that !@#$%#!@$girl home wit a smid-ile http://wtf.me/w00t"
    filter = TweetFilter(text)
    print filter.read()
    '''
    def __init__(self, text):
        self.text = text
        self.output = self.filterTweet(text)
        
    def filterTweet(self, input):
        input = self.filterUris(input)
        input = self.filterReplies(input)
        input = self.filterCharacters(input)
        
        output = input
        return output
           
    def filterUris(self, input):
        if "http" in input:
            t = input[input.find("http://"):]
            t = t[:t.find(" ")]
            output = input.replace(t, '')
            output = output[:-1]
        return output
    
    def filterReplies(self, input):
        # Extract @reply
        if "@" in input:
            t = input[input.find("@"):]
            t = t[:t.find(" ")]
        
            user = self.request("http://api.twitter.com/1/users/show.json?screen_name=" + t)
            if user:
                output = input.replace(t, user['name'])
            else:
                output
            
        return output
    
    def filterCharacters(self, input):
        pattern = re.compile('[^\'\s\w_]+')
        output = pattern.sub('', input)
        return output
    
    def filterObscenity(self, input):
        self.stub = True
        
    def read(self):
        return self.output
    
    def request(self, path, format="json"):
        # Add debugging to post
        #h=urllib2.HTTPHandler(debuglevel=1)
        #opener = urllib2.build_opener(h)
        #urllib2.install_opener(opener)

        request = urllib2.Request(path)
        try:
            r = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            print "Error!: " + str(e)
            return False
        
        data = r.read()
        
        if format is "json":       
            return json.loads(data)
        else:
            return data


'''



'''


if __name__ == '__main__':
    events = VocaloidTask.process_midi_file('/home/v/Sounds/Godfather.mid')
    print [x['p'] for x in events]
    print [x['d'] for x in events]

