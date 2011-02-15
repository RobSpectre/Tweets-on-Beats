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
import syllables
import subprocess
import hashlib
import face_client
import urllib

'''Objects'''
class TweetFilter:
    '''
    Implementation
    text = "@dn0t I'll send that !@#$%#!@$girl home wit a smid-ile http://wtf.me/w00t"
    filter = TweetFilter(text)
    print filter.read()
    '''
    def __init__(self, text, username):
        self.text = text
        self.output = self.filterTweet(text)
        if self.output:
            self.syllables = Syllables(text)
            self.user = self.getUser(username)

    def filterTweet(self, input):
        if "RT" not in input:
            input = self.filterUris(input)
            input = self.filterReplies(input)
            input = self.filterTags(input)
            input = self.filterCharacters(input)   
            output = input
            return output
        else:
            return False

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
        
    def filterTags(self, input):
        # Extract #hashtag
        if "#" in input:
            t = input[input.find("#"):]
            t = t[:t.find(" ")]
            output = input.replace(t, "")
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
        if self.output:
            return {
                    'text': self.output,
                    'user': self.user,
                    'syllables': self.syllables.read()
            }

    def getUser(self, username):
        user = self.request("http://api.twitter.com/1/users/show.json?screen_name=" + username)
        if not user:
            return False

        # Try to fetch gender
        myDetector = GenderDetect()
        uri = user['profile_image_url'].replace("_normal", "")
        try:
            detection = myDetector.detect(uri)
        except face_client.FaceError:
            detection = {}
            detection['status'] = False
            gender = "neuter"
        if detection['status']:
            try:
                gender = detection['photos'][0]['tags'][0]['attributes']['gender']['value']
            except KeyError:
                gender = "neuter"
        else:
            gender = "neuter"

        return {'name': user['name'], 'gender': gender}

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

class GenderDetect(face_client.FaceClient):
    def detect(self, uri):
        return self.faces_detect(uri)

class Espeak(TweetFilter):
    def __init__(self, text, voice=5):
        self.text = text
        self.output = self.say(text, voice)

    def say(self, text, voice):
        hash = hashlib.md5(text).hexdigest()
        path = "https://api.ispeech.org/api/rest/?"
        params = {
            'apikey': "38fcab81215eb701f711df929b793a89",
            'action': "convert",
            'voice': voice,
            'text': text
        }

        request = urllib2.Request(path, urllib.urlencode(params))
        try:
            r = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            print "Error!: " + str(e)
            return False

        data = r.read()
        f = open("/tmp/" + str(hash) + ".mp3", 'wb')
        f.write(data)
        f.close()
        return str(hash) + ".mp3"

    def read(self):
        return self.output


'''Implementation'''
if __name__ == "__main__":
    try:
        text = sys.argv[1]
        user = sys.argv[2]
    except IndexError:
        print "Usage: getvox.py \"String you want vox for.\""
    filter = TweetFilter(text,user).read()
    if filter:
        if filter['user']['gender'] == "male":
            voice = "usenglishmale1"
        else:
            voice = "usenglishfemale1"
        espeak = Espeak(filter['text'], voice)
        print "/tmp/" + espeak.read()
    else:
        print False