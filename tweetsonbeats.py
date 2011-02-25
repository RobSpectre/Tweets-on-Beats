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
import datetime
import tweepy
from tweepy.api import API
import time
from textwrap import TextWrapper
from random import choice
import mixer
import subprocess
import random

'''Classes'''
class StreamWatcherListener(tweepy.StreamListener):
    '''
    Object that watches for tweets marked #beatify.
    '''
    def __init__(self, api=None):
        self.api = api or API()
        self.timer = 0
        self.tweets_beated = []
        
    def on_status(self, status):
        try:
            self.log('\n %s \"%s\" : %s for %s' % (status.screen_name, status.text, status.created_at, status.id))
            if status.id not in self.tweets_beated:
                processed = self.processTweet(status)
            else:
                print "Tweet already beated."
        except:
            pass

    def on_error(self, status_code):
        print 'An error has occured! Status code = %s' % status_code
        return True  # keep stream alive

    def on_timeout(self):
        print 'Snoozing Zzzzzz'
        self.timer = self.timer + 1
        if self.timer >= 1:
            print "Haven't heard anything for a while - polling!\n"
            self.poll()
            self.timer = 0
    
    def processTweet(self, status):
        self.tweets_beated.append(status.id)
        tempProcessor = TweetProcessor(status)
        tempProcessor.process()
        self.timer = 0

    def poll(self):
        search = self.api.search('#beatify')
        for tweet in search:
            print str(tweet.id) + " " + str(tweet.created_at) + " " + str(tweet.text)
            now = datetime.datetime.utcnow()
            then = datetime.datetime.strptime(str(tweet.created_at), "%Y-%m-%d %H:%M:%S")
            delta = now - then
            if tweet.id not in self.tweets_beated and delta.seconds < 4000:
                status = tweepy.Status()
                status.id = tweet.id
                status.text = tweet.text
                status.screen_name = tweet.from_user
                status.created_at = tweet.created_at
                self.processTweet(status)


class TweetProcessor:
    '''
    Object for processing tweets themselves.
    This is where the magic happens.
    '''
    def __init__(self, status):       
        # Twitter Credentials
        self.consumer_token = "bzdPlHk429kKb3ZsUfhQw"
        self.consumer_secret = "25hF3WTQ6h9njyqgS2V9a0jQ2MBkePdBwBshA5IajlY"
        self.access_token = "251275058-4xfy2Bw1MR6fW1KHdz61px1NzPO7ao5i8E46U0NR"
        self.access_secret = "6O2kYW5osJMXDfvlxu3Bj9nZcSctxNrpNMxAq8HhcbI"
        
        # Variables
        self.log("Processing tweet: %s by %s - \"%s\"" % (status.id, status.screen_name, status.text))
        self.status = status
        
    def process(self):
        # Filter tweet
        self.log("Filtering tweet...")
        filter = TweetFilter(self.status.text, self.status.screen_name).read()
        self.log("Tweet filtered as: " + filter['text'])
        
        # Synthesize voice.
        if filter['user']['gender'] == "male":
            voice = "usenglishmale1"
        else:
            voice = "usenglishfemale1"
        self.log("Synthesizing tweet...")
        vox = self.getVox(filter['text'], voice)
        
        # Mix TwOnBe
        if vox:
            self.log("Vox generated at " + vox + ".")
            self.log("Slapping that tweet on a beat...")
            twonbe = self.mixdown(vox)
        else:
            raise TwonbeError("Failed to get voice synthesis!")
        
        # Upload TwOnBe        
        if twonbe:
            self.log("Twonbe generated at " + twonbe)
            #upload = self.upload(twonbe, self.status)
            upload = "http://soundcloud.com/tweetsonbeats/twonbe-twitter-search-is-3"
        else:
            raise TwonbeError("Failed to mix tweet to beat!")
        
        # Tweet TwOnBe
        return self.tweet(self.status.screen_name, upload[0][:-1])
        
           
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
        myMixer = mixer.Mixer(vox)
        return myMixer.read()
    
    def tweet(self, user, link):
        # Pick Template
        templateFile = open("templates.txt")
        templates = [i for i in templateFile.readlines()]
        template = random.choice(templates)
        
        # Connect
        auth = tweepy.OAuthHandler(self.consumer_token, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_secret)
        api = tweepy.API(auth)
        tweet = template % (user, link)
        return api.update_status(tweet)
        
    def upload(self, twonbe, status):
        self.log("Uploading TwOnBe...")
        mix_twonbe = subprocess.Popen(["ruby", "upload.rb", twonbe, status.screen_name,  status.text], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        mix_twonbe.wait()
        output = mix_twonbe.communicate()
        self.log(str(output))
        return output
        
    def log(self, string):
        print string + "\n"
        

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
    

def main():
    # Prompt for login credentials and setup stream object
    username = "twonbe"
    password = "foobar"
    auth = tweepy.BasicAuthHandler(username, password)
    stream = tweepy.Stream(auth, StreamWatcherListener(), timeout=None)

    stream.filter(None, track=("#beatify",))


'''Implementation'''
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "\nDone!"