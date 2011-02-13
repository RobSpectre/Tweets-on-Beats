#from canoris import Canoris, Template, Task
import subprocess, midi, subprocess, midi, re, urllib2, json, uuid, os, \
    string, sys, syllables, math
import simplejson as json

'''
at the character where you're encoding:
    do the next 2 characters represent a phoneme together?

CANORIS_URL = 'http://localhost'
CANORIS_KEY = '867c069719dc45db930c7d9749de8659'
'''

TMP_DIR = '/tmp'
NFS_BASEDIR = '/mnt/m30_local'

PROCESSING_VOCALOID_DIR          = os.path.join(NFS_BASEDIR, 'vocaloid')
PROCESSING_VOCALOID_DIR_CONFIG   = PROCESSING_VOCALOID_DIR.replace('/', '\\')
WINE_ENVIRONMENT                 = '/home/v/vocaloid/environment'
PROCESSING_VOCALOID_SOURCE_DIR   = os.path.join(PROCESSING_VOCALOID_DIR, 'bin')

TMP_DIR = '/tmp'

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
        'a': '@',               #    trap
        'a2': '@',               #    about    This may be '@'               # or may be a more open schwa.
        'A:': '@',               #    palm
        'A@': 'A@',               #    start
        'E': '{',               #    dress
        'e@': 'e@',               #    square
        'I': 'I',               #    kit
        'I2': 'I',               #    intend    As 'I'               #, but also indicates an unstressed syllable.
        'i':  'I',              #    happy    An unstressed "i" sound at the end of a word.
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

'''
def init_canoris():
    Canoris.set_api_key(CANORIS_KEY)
    Canoris.set_base_uri(CANORIS_URL)
    '''

class VocaloidTask():
    def __init__(self, text, midi_path, bpm):
        self.midi_path = midi_path
        syllables = Syllables(text)
        self.text = syllables.read()
        print self.text
        events, ticklength = self.__process_midi_file(midi_path)
        self.sequence = self.__generate_xml(self.__espeak_to_vocaloid_phonemes(
                                                self.__get_espeak_output(self.text)),
                                            events,
                                            1.0/ticklength)
        self.xml_file = self.__save_tmp_file(self.sequence)
        self.wav_file = self.__generate_audio(self.xml_file)

    @staticmethod
    def __get_espeak_output(input):
        text = ' '.join([x['word'] for x in input])
        p = subprocess.Popen(['espeak', '-x', '-q', text], stdout=subprocess.PIPE)
        p.wait()
        text_after_transform = p.communicate()[0].replace("'", "").split(' ')
        for i in range(len(input)):
            input[i]['word'] = text_after_transform[i]
        return input

    @staticmethod
    def __espeak_to_vocaloid_phonemes(input):
        result = []
        for word in input:
            intermediate_result = []
            still_to_translate = word['word'][:]
            while len(still_to_translate) > 0:
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
                # make syllables into words
                if word['count'] > 1:
                    # where do we split?
                    split_ratio = len(intermediate_result) / float(word['count'])
                    split_at_every = math.floor(split_ratio)
                    while len(intermediate_result) > 0:
                        result.append(intermediate_result[0:split_at_every])
                        intermediate_result = intermediate_result[split_at_every:]
                else:
                    result.append(intermediate_result)

        print result
        return result

    @staticmethod
    def __process_midi_file(midi_path):
        midifile = midi.MidiFile()
        midifile.open(midi_path)
        midifile.read()
        midifile.close()

        track = midifile.tracks[0]
        events = []
        last_time = 0
        note_closed_p = True
        for event in track.events:
            if event.type == 'NOTE_OFF' or (event.type == 'NOTE_ON' and not note_closed_p):
                # make sure we don't run into an exception if the midi file
                # is malformed (e.g. doesn't start with a noteon)
                if len(events) > 0:
                    events[-1]['d'] = float(event.time - last_time) #float(midifile.ticksPerQuarterNote)
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
        return events, midifile.ticksPerQuarterNote

    @staticmethod
    def __save_tmp_file(sequence):
        p = os.path.join(TMP_DIR, str(uuid.uuid4()))
        f = open(p, 'w')
        f.write(sequence)
        f.close()
        return p

    @staticmethod
    def __generate_xml(syllables, melody, ticklength):
        sequence = "<melody ticklength='%s'>" % ticklength
        str_syllables = [' '.join(x) for x in syllables]
        syl_i = 0
        mel_i = 0
        while syl_i < len(str_syllables):
            mel_i = mel_i % len(melody)
            if melody[mel_i]['r']:
                sequence += "<rest duration='%s'/>" % melody[mel_i]['d']
            else:
                sequence += "<note duration='%s' pitch='%s' velocity='%s' phonemes='%s'/>" % \
                                (melody[mel_i]['d'], melody[mel_i]['p'], melody[mel_i]['v'], ' '.join(syllables[syl_i]))
                syl_i += 1
            mel_i += 1

        sequence += "</melody>"
        return sequence

    @staticmethod
    def __generate_audio(input_file):
        output_file = p = os.path.join(TMP_DIR, str(uuid.uuid4())+'.wav')
        os.chdir(WINE_ENVIRONMENT)
        executable_full = os.path.join(WINE_ENVIRONMENT, 'VocaloidServer.exe')

        # execute the application
        exec_array = ['wine', executable_full, '--in', input_file, '--out', output_file, '--norm']
        p = subprocess.Popen(exec_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={'WINEPREFIX': WINE_ENVIRONMENT})
        p_result = p.wait()
        # if the return_code is not 0, it should mean an error ocurred
        if p_result != 0:
            output_std, output_err = p.communicate()
            raise Exception("ProcessingError", 'error: ' + str(p_result) + ' ' + str(output_std) + "\n" + str(output_err))
        return output_file

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
        else:
            return input

    def filterReplies(self, input):
        # Extract @reply
        if "@" in input:
            t = input[input.find("@"):]
            t = t[:t.find(" ")]

            user = self.request("http://api.twitter.com/1/users/show.json?screen_name=" + t)
            if user:
                output = input.replace(t, user['name'])
            return output
        else:
            return input

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

class Syllables:
    '''
    Implementation
    text = "@dn0t I'll send that !@#$%#!@$girl home wit a smid-ile http://wtf.me/w00t"
    syllables = Syllables(text)
    print syllables.read()
    '''
    def __init__(self, text):
        self.text = text
        self.output = self.countSyllables(text)

    def countSyllables(self, input):
        list =[]
        for word in input.split(" "):
            count = syllables.count(word)
            list.append({
                "word": word,
                "count": count
            })
        return list

    def read(self):
        return self.output

if __name__ == '__main__':
    #init_canoris()
    vt = VocaloidTask("Ain't no sunshine when she's gone It's not warm when she's away Ain't no sunshine when she's gone And she's always gone too long Anytime she goes away", '/home/v/Sounds/Godfather.mid', 1)


