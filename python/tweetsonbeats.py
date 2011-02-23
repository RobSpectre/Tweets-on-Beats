'''
TweetOnBeats Listener
Written by /rob, adapted from Johannes Wagener's Ruby implementation
Music Hack Day NYC 12 February 2011

'''

'''Modules'''
import re, string, os
import simplejson as json
import urllib2
import sys
import hashlib
import face_client
import urllib
import tweepy
import time
from textwrap import TextWrapper
from random import choice
import mixer

'''Classes'''
class StreamWatcherListener(tweepy.StreamListener):
    '''
    Object that watches for tweets marked #beatify.
    '''
    status_wrapper = TextWrapper(width=60, initial_indent='    ', subsequent_indent='    ')

    def on_status(self, status):
        try:
            tempProcessor = TweetProcessor(status)
            TweetProcessor.process()
            print '\n %s  %s  via %s\n' % (status.author.screen_name, status.created_at, status.source)
        except:
            # Catch any unicode errors while printing to console
            # and just ignore them to avoid breaking application.
            pass

    def on_error(self, status_code):
        print 'An error has occured! Status code = %s' % status_code
        return True  # keep stream alive

    def on_timeout(self):
        print 'Snoozing Zzzzzz'

    def start():
        # Prompt for login credentials and setup stream object
        username = "twonbe"
        password = "foobar"
        stream = tweepy.Stream(username, password, StreamWatcherListener(), timeout=None)
    
        follow_list = None
        track_list = "#beatify"
    
        stream.filter(follow_list, track_list)


class TweetProcessor:
    '''
    Object for processing tweets themselves.
    This is where the magic happens.
    '''
    def __init__(self, tweet=None):
        self.tweet = tweet
        #self.filter = TweetFilter(tweet.text, tweet.author)
        
    def process(self):
        filter = FilterTweet(self.tweet.text, self.tweet.screen_name).read()
        
        if filter['user']['gender'] == "male":
            voice = "usenglishmale1"
        else:
            voice = "usenglishfemale1"
            
        vox = self.getVox(filter['text'], voice)
        twonbe = self.mixdown(vox)
           
    def getVox(self, text, voice="usenglishfemale1"):
        hash = hashlib.md5(text).hexdigest()
        path = "https://api.ispeech.org/api/rest/?"
        params = {
            'apikey': "38fcab81215eb701f711df929b793a89",
            'action': "convert",
            'voice': voice,
            'speed': -2,
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
        return "/tmp/" + str(hash) + ".mp3"
    
    def mixdown(self, vox):
        mixer = mixer.Mixdown(vox)
        return mixer.read()
    
    def upload(self):
        stub = true

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
            except:
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


class GenderDetect(face_client.FaceClient):
    '''
    Wrapper object for FaceClient API
    '''
    def detect(self, uri):
        return self.faces_detect(uri)


class TwonbeError(Exception):
    '''
    For exceptions particular to Twonbe logic.
    '''
    def __init__(self, error_message):
        self.error_message = error_message

    def __str__(self):
        return '%s' % (self.error_message)


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
        espeak = Say(filter['text'], voice)
        print "/tmp/" + espeak.read()
    else:
        print False