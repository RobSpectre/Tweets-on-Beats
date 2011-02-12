'''
Tweet2Beats Vox Generator
Written by /rob and vincent
Music Hack Day NYC 12 February 2011

Usage:
Execute script with text to receive a musical text-to-speech mp3.


'''

'''Modules'''
import re, string
import simplejson as json
import urllib2
import sys


'''Objects'''
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
        
class Syllables:
    '''
    COPYRIGHT

    Distributed under the same terms as Perl.
    Contact the author with any questions.
    
    AUTHOR
    Greg Fast 
    Dispenser (python port)
    
     http://toolserver.org/~dispenser/sources/syllable.py
    '''
    def __init__(self, word):
        self.syllables = self.syllable(word)
        
        self.SubSyl = (
               'cial',
               'tia',
               'cius',
               'cious',
               'giu',              # belgium!
               'ion',
               'iou',
               'sia$',
               '.ely$',             # absolutely! (but not ely!)
              )
        self.AddSyl = ( 
               'ia',
               'riet',
               'dien',
               'iu',
               'io',
               'ii',
               '[aeiouym]bl$',     # -Vble, plus -mble
               '[aeiou]{3}',       # agreeable
               '^mc',
               'ism$',             # -isms
               '([^aeiouy])\1l$',  # middle twiddle battle bottle, etc.
               '[^l]lien',         # alien, salient [1]
                   '^coa[dglx].',      # [2]
               '[^gq]ua[^auieo]',  # i think this fixes more than it breaks
                'dnt$',           # couldn't
              )

    def syllable(word):
        word = word.lower()
        word = word.replace('\'', '')    # fold contractions.  not very effective.
        word = re.sub(r'e$', '', word);    # strip trailing "e"s
        scrugg = re.split(r'[^aeiouy]+', word); # '-' should perhaps be added?
        for i in scrugg:
            if not i: 
                scrugg.remove(i)
        syl = 0;
        # special cases
        for syll in self.SubSyl:
            if re.search(syll, word): syl -= 1
        for syll in self.AddSyl:
            if re.search(syll, word): syl += 1
        if len(word)==1: syl +=1    # 'x'
        # count vowel groupings
        syl += len(scrugg)
        return (syl or 1)    # got no vowels? ("the", "crwth")
    
    def read(self):
        return self.syllables

'''Implementation'''
if __name__ == "__main__":
    try:
        text = sys.argv[1]
    except IndexError:
        print "Usage: getvox.py \"String you want vox for.\""
    filter = TweetFilter(text)
    text = filter.read()
    print Syllables(text).read()
    