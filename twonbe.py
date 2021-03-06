'''
Tweets On Beats
A Twitter bot that puts your beat on a fat (or alternatively phat) beat.

Version 2.0 - a shiteload better.

Written by /rob, 11 March 2011
'''
import threading
import Queue
import logging
import logging.handlers
import urllib
import urllib2
import simplejson
import redis
import datetime
import re
import os
import tweepy
import face_client
import hashlib
import subprocess
import random

'''
Configuration variables
'''
searchapi = "http://search.twitter.com"
keyword = "#beatify"
logging_level = logging.DEBUG
log_handler = logging.handlers.RotatingFileHandler("/tmp/tweetsonbeats.log", maxBytes=524288000, backupCount=5) 
log_formatter = logging.Formatter('%(asctime)s::%(name)s::%(levelname)s::%(message)s')
log_handler.setFormatter(log_formatter)
logging.basicConfig()
redis_host = "localhost"

'''
Main Daemon
Broker for all Twonbe jobs
'''
class TwonbeDaemon(threading.Thread):
    def __init__(self, queue):
        self.elapsed = 0
        self.fault = False
        self.util = Utility() 
        self.jobs = []
        self.queue = queue
        threading.Thread.__init__(self)

        # Configuration directives
        self.log = logging.getLogger("TwonbeDaemon")  
        self.log.setLevel(logging_level)
        self.log.addHandler(log_handler)
        self.log.info("Initialized.")

    def run(self):
        # Main loop
        self.log.info("Launching Twonbe Daemon.")
        try:
            while self.fault is False:
                try:
                    self.process()
                except Exception as e:
                    raise TwonbeError(e, "Error encountered processing job.")
        except KeyboardInterrupt:
            print "\nDone!"

    def process(self):
        # Process job queue
        global logging_level
        if logging_level == logging.DEBUG and self.jobs:
            self.log.debug("Job queue: %s" % (str(self.queue.qsize())))
        if not self.queue.empty():
            job = self.queue.get()
            try:
                self.log.info("Processing job: %s" % (job.name))
                job.start()
            except Exception as e:
                self.stop()
                raise TwonbeError(e, "encountered error with job: %s" % (job.name))
    
    def stop(self):
        self.log.debug("Stop command received.")
        self.fault = True
        return self.log.info("Stop command issued.")


'''
Object for Jobs

Extend this object and add to TwonbeDaemon object to queue and process.
'''
class Job(threading.Thread):
    def __init__(self, name, id, queue, interval=None):
        threading.Thread.__init__(self)
        self.name = name   
        self.id = id
        self.interval = interval
        self.elapsed = 0
        self.util = Utility()
        self.timer = threading.Event()
        self.queue = queue
        
        # Configuration directives
        self.log = logging.getLogger(name)
        self.log.setLevel(logging_level)
        self.log.addHandler(log_handler)
        self.log.debug("Created %s job: %s" % (self.name, self.id))
    
    def run(self):
        # Error-safe wrapper for user-defined job logic
        if self.interval:
            self.log.debug("Starting job in %s seconds." % (str(self.interval)))
            self.timer.wait(self.interval)
        self.log.debug("Starting %s job: %s" % (self.name, self.id))
        try:
            self.log.info("Processing %s job: %s" % (self.name, self.id))
            self.process()
            self.log.debug("Finished %s job: %s" % (self.name, self.id))
        except KeyboardInterrupt:
            print "\nDone!"
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed:" % (self.name, self.id))
        
    def process(self):
        # Extend this function to initiate job logic.
        return


'''
Jobs
These are the individual jobs chained together to convert a tweet into a Twonbe
'''
class PollTwitter(Job):
    def __init__(self, id, queue, lastProcessedId=None):
        self.id = id
        self.lastProcessedId = lastProcessedId
        Job.__init__(self, "PollTwitter", id, queue, 30)
    
    def process(self):
        self.log.debug("Starting to process polling job.")
        path = self.buildRequest()
        if path:
            try:
                data = self.util.request(path)
            except:
                self.log.error("Error polling Twitter.")
                self.queue.put(PollTwitter(str(int(self.id) + 1), self.queue, self.lastProcessedId))
                return False
        else:
            raise TwonbeError("Error polling", "Could not build request path.")
        
        if data and data['results']:
            for tweet in reversed(data['results']):
                self.log.debug("Queueing up tweet to be checked: %s" % (tweet['id_str']))
                self.queue.put(CheckTweet(tweet['id_str'], self.queue, tweet))
                lastProcessedId = tweet['id_str']
            self.log.debug('Completed poll - scheduling next one.')
            self.queue.put(PollTwitter(str(int(self.id) + 1), self.queue, lastProcessedId))
            return True
        else:
            self.log.debug("No results returned.")
            self.queue.put(PollTwitter(str(int(self.id) + 1), self.queue, self.lastProcessedId))
            return False
    
    def buildRequest(self):
        # Build polling request
        self.log.debug("Building polling request.")
        global searchapi
        global keyword
        if self.lastProcessedId:
            params = {
                'q': keyword,
                'result_type': "recent",
                'since_id': self.lastProcessedId
            }
        else:
            params = {
                'q': keyword,
                'result_type': "recent"
            }
        return searchapi + "/search.json?" + urllib.urlencode(params)

class CheckTweet(Job):
    def __init__(self, id, queue, tweet):
        self.id = id
        self.tweet = tweet
        self.limit = 600
        Job.__init__(self, "CheckTweet", id, queue)
        
    def process(self):
        if self.isNotEnglish() or self.isAttempted() or self.isOld() or self.isRetweet():
            self.log.debug("Tweet does not pass initial checks - skipping.")
            return False
        else:
            self.log.info("Tweet passes initial checks - filtering.")
            self.queue.put(FilterTweet(self.id, self.queue, self.tweet))
            return True
        
    def isAttempted(self):
        self.log.debug("Checking if tweet has been attempted before...")
        if self.util.redis.sadd("attempted", self.tweet['id_str']):
            self.log.debug("Tweet has not been attempted before..")
            return False
        else:
            self.log.debug("Tweet has been attempted before. Skipping.")
            return True
    
    def isOld(self):
        self.log.debug("Checking if tweet is too older than %s seconds." % (str(self.limit)))
        now = datetime.datetime.utcnow()
        timestamp = self.tweet['created_at'].replace(" +0000", "")
        then = datetime.datetime.strptime(timestamp, "%a, %d %b %Y %H:%M:%S")
        delta = now - then
        self.log.debug(str(now))
        self.log.debug(str(then))
        self.log.debug(str(delta))
        if delta.seconds < self.limit:
            self.log.debug("Tweet is not too old.")
            return False
        else:
            self.log.debug("Tweet is too old. Skipping.")
            return True
    
    def isNotEnglish(self):
        self.log.debug("Checking if tweet is in English.")
        if self.tweet['iso_language_code'] == "en":
            self.log.debug("Tweet is in English.")
            return False
        else:
            self.log.debug("Tweet is not in English. Skipping.")
            return True
    
    def isRetweet(self):
        if "RT" in self.tweet['text']:
            return True
        else:
            return False

class FilterTweet(Job):
    def __init__(self, id, queue, tweet):
        self.id = id
        self.tweet = tweet
        Job.__init__(self, "FilterTweet", id, queue)
    
    def process(self):
        self.log.debug("Filtering string: %s" % (self.tweet['text']))
        input = self.tweet['text']
        input = self.filterUris(input)
        input = self.filterReplies(input)
        input = self.filterTags(input)
        input = self.filterCharacters(input)
        if input:
            self.log.debug("String filtered as: %s" % (input))
            self.tweet['filtered_text'] = input
        self.queue.put(GenderCheck(self.id, self.queue, self.tweet))
        return True
    
    def filterUris(self, input):
        if "http" in input:
            t = input[input.find("http://"):]
            if " " in t:
                t = t[:t.find(" ")]
            output = input.replace(t, '')
            return output
        else:
            return input
        
    def filterReplies(self, input):
        if "@ " in input:
            pass
        elif "@" in input:
            t = input[input.find("@"):]
            t = "@" + self.filterCharacters(t)
            self.log.debug("Replacing name %s with full name." % (t))
            if " " in t:
                t = t[:t.find(" ")]
            user = self.util.request("http://api.twitter.com/1/users/show.json?screen_name=" + t)
            if user:
                return input.replace(t, user['name'])
        return input
        
    def filterTags(self, input):
        if "#" in input:
            t = input[input.find("#"):]
            if " " in t:
                t = t[:t.find(" ")]
            output = input.replace(t, "")
            return output
        else:
            return input
        
    def filterCharacters(self, input):
        pattern = re.compile('[^\'\s\w_]+')
        output = pattern.sub('', input)
        return output   
    
class GenderCheck(Job):
    def __init__(self, id, queue, tweet):
        self.id = id
        self.tweet = tweet
        self.face = face_client.FaceClient()
        Job.__init__(self, "GenderCheck", id, queue)
        
    def process(self):
        try:
            if "normal" in self.tweet['profile_image_url']:
                self.tweet['profile_image_url'] = self.tweet['profile_image_url'].replace("normal", "bigger")
            detection = self.detect(self.tweet['profile_image_url'])
        except face_client.FaceError:
            gender = "neuter"
        if detection['status']:
            try:
                gender = detection['photos'][0]['tags'][0]['attributes']['gender']['value']
            except:
                gender = "neuter"
        else:
            gender = "neuter"
        self.tweet['gender'] = gender
        return self.queue.put(SynthesizeTweet(self.id, self.queue, self.tweet))
                    
    def detect(self, uri):
        return self.face.faces_detect(uri)

class SynthesizeTweet(Job):
    def __init__(self, id, queue, tweet):
        self.id = id
        self.tweet = tweet
        self.voice = "usenglishfemale1"
        self.hash = None
        Job.__init__(self, "SynthesizeTweet", id, queue)
        
    def process(self):
        self.log.debug("Synthesizing filtered text...")
        hash = hashlib.md5(self.tweet['filtered_text']).hexdigest()
        voice = self.getVoice(self.tweet['gender'])
        vox = self.downloadVox(voice, self.tweet['filtered_text'])
        self.tweet['vox_path'] = self.writeVox(hash, vox)
        return self.queue.put(MixTwonbe(self.id, self.queue, self.tweet))
           
    def getVoice(self, gender):
        if gender == "female":
            return "usenglishfemale1"
        else:
            return "usenglishmale1"
    
    def downloadVox(self, voice, text):
        self.log.debug("Downloading vox...")
        path = "https://api.ispeech.org/api/rest/?"
        params = {
            'apikey': "38fcab81215eb701f711df929b793a89",
            'action': "convert",
            'voice': voice,
            'speed': -2,
            'text': text
        }
        vox = self.util.request(path, params)
        if vox:
            self.log.debug("Vox downloaded.")
            return vox
        else:
            self.log.error("Failed to download vox!")
            return False
    
    def writeVox(self, hash, vox):
        self.util.write("/tmp/" + str(hash) + ".mp3", vox)
        return "/tmp/" + str(hash) + ".mp3"
    
class MixTwonbe(Job):
    def __init__(self, id, queue, tweet):
        self.id = id
        self.tweet = tweet
        
        # Vox, beat and outro raw files.
        self.vox = self.tweet['vox_path']
        
        # Volumes
        self.vox_volume = 0.7
        self.beat_volume = 0.6
        
        Job.__init__(self, "MixTwonbe", id, queue)
        
    def process(self):
        self.log.debug("Mixing TwOnBe...")
        
        # Generate mixing temporary filenames.
        beat = self.getBeat()
        outro = self.getOutro()
        vox_tmp = self.tempFileName("v1")
        vox_tmp2 = self.tempFileName("v2")
        beat_tmp = self.tempFileName()
        mix_tmp = self.tempFileName()
        final_tmp = self.tempFileName("final")
        
        params = self.setMixingParameters(beat, self.vox)
        
        # Mix TwOnBe
        try:
            vox_tmp = self.convertVox(self.vox, vox_tmp)
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to convert vox:" % (self.name, self.id))
        try:
            vox_tmp2 = self.offsetVox(vox_tmp, vox_tmp2)
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to offset vox:" % (self.name, self.id))
        try:
            beat_tmp = self.trimBeat(beat, beat_tmp)
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to trim beat:" % (self.name, self.id))
        try:
            mix_tmp = self.mixVoxAndBeat(vox_tmp2, beat_tmp, mix_tmp)
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to mix vox and beat:" % (self.name, self.id))
        try:
            final_tmp = self.mixOutro(mix_tmp, outro, final_tmp)
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to mix outro:" % (self.name, self.id))
        
        # Add paths to tweet
        self.tweet['vox_tmp'] = vox_tmp
        self.tweet['vox_tmp2'] = vox_tmp2
        self.tweet['beat_tmp'] = beat_tmp
        self.tweet['mix_tmp'] = mix_tmp
        self.tweet['twonbe'] = final_tmp
        
        # Queue up next job
        return self.queue.put(UploadTwonbe(self.id, self.queue, self.tweet))
    
    def setMixingParameters(self, beat, vox):
        self.log.debug("Setting mixing parameters...")
        # Mixing parameters
        self.bpm = int(beat.split("_")[1])
        self.log.debug("BPM set to: %i" % self.bpm)
        self.offset= int(60.0/(self.bpm / 4))
        self.log.debug("Offset set to: %i" % self.offset)
        self.voice_length = os.path.getsize(vox) / 7452
        self.log.debug("Voice length set to: %i" % self.voice_length)
        self.almost_full_length = int(self.offset + self.voice_length + 1)
        self.log.debug("Almost Full Length set to: %i" % self.almost_full_length)
        self.log.debug("Mixing parameters set.")
    
    def convertVox(self, vox, vox_tmp):
        self.log.debug("Converting vox...")
        convert_vox = subprocess.Popen(["sox", "-G", vox, "-c", "2", vox_tmp, "rate", "44100"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        convert_vox.wait()
        self.log.debug(convert_vox.communicate())
        self.log.debug("Vox converted.")
        return vox_tmp
    
    def offsetVox(self, vox_tmp, vox_tmp2):
        self.log.debug("Offsetting vox...")
        self.log.debug("Mixing vox offset of " + str(self.offset))
        offset_vox = subprocess.Popen(["sox", "-G", vox_tmp, vox_tmp2, "vol", str(self.vox_volume), "delay", str(self.offset), str(self.offset)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        offset_vox.wait()
        self.log.debug(str(offset_vox.communicate()))
        self.log.debug("Vox offset.")
        return vox_tmp2
        
    def trimBeat(self, beat, beat_tmp):
        self.log.debug("Trimming beat...")
        trim_beat = subprocess.Popen(["sox", beat, beat_tmp, "trim", "0", str(self.almost_full_length), "vol", str(self.beat_volume)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        trim_beat.wait()
        self.log.debug(str(trim_beat.communicate()))
        return beat_tmp
    
    def mixVoxAndBeat(self, vox_tmp2, beat_tmp, mix_tmp):
        self.log.debug("Mixing vox and beat...")
        mix_vox_and_beat = subprocess.Popen(["sox", "-G", "-m", vox_tmp2, beat_tmp, mix_tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        mix_vox_and_beat.wait()
        self.log.debug(str(mix_vox_and_beat.communicate()))
        return mix_tmp
    
    def mixOutro(self, mix_tmp, outro, final_tmp):
        self.log.debug("Mixing TwOnBe outro...")
        mix_twonbe = subprocess.Popen(["sox", "-G",  mix_tmp, outro, final_tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        mix_twonbe.wait()
        self.log.debug(str(mix_twonbe.communicate()))
        return final_tmp
               
    def getBeat(self):
        try:
            beats = os.listdir("beats")
            beat = random.choice(beats)
            return "beats/" + str(beat)
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed:" % (self.name, self.id))
        
    def getOutro(self):
        try:
            outros = os.listdir("outros")
            outro = random.choice(outros)
            return "outros/" + str(outro)
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed:" % (self.name, self.id))
    
    def tempFileName(self, name="", ext=".wav"):
        return "/tmp/tweetsonbeats-" + name + str(random.randint(1, 9999)) + ext

class UploadTwonbe(Job):
    def __init__(self, id, queue, tweet):
        self.id = id
        self.tweet = tweet
        Job.__init__(self, "UploadTwonbe", id, queue)
    
    def process(self):
        self.log.debug("Uploading TwOnBe...")
        self.log.debug("TwOnBe located: %s" % str(self.tweet['twonbe']))
        self.log.debug("User: %s" % str(self.tweet['from_user']))
        self.log.debug("Filtered text: %s" % str(self.tweet['filtered_text']))
        try:
            mix_twonbe = subprocess.Popen(["ruby", "upload.rb", self.tweet['twonbe'], self.tweet['from_user'], self.tweet['filtered_text']], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            mix_twonbe.wait()
            output = mix_twonbe.communicate()
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to upload TwOnBe:" % (self.name, self.id))
        if "http://" in str(output[0]):
            self.log.debug("Twonbe uploaded here: %s" % (str(output[0])))
            self.tweet['soundcloud_path'] = str(output[0])
        else:
            raise TwonbeError("UploadError", "Received this error: %s" % str(output))
        self.log.debug("Queueing cleanup of files:")   
        self.queue.put(CleanupTwonbe(self.id, self.queue, self.tweet))
        self.queue.put(TweetTwonbe(self.id, self.queue, self.tweet))

class TweetTwonbe(Job):
    def __init__(self, id, queue, tweet):
        self.id = id
        self.tweet = tweet
        # Twitter credentials
        self.consumer_token = "Mw8wRMrrTZDzX3ig1Z71A"
        self.consumer_secret = "p9AQBMC1Brdpe7RK0SCeSO7kWbnyRmpN66IDmv4J34"
        self.access_token = "251212628-nnKe54jjBSlgRguRbwBkXXYKPQ82PUXpeoGS2upx"
        self.access_secret = "qMtYi6Xi5J0ZVaTWYluiuBxkMsoxz7yOrXr6OMWZgw"      
        Job.__init__(self, "TweetTwonbe", id, queue)
    
    def process(self):
        self.log.debug("Tweeting TwOnBe to user: %s" % (str(self.id)))
        template = self.getTemplate()        
        auth = tweepy.OAuthHandler(self.consumer_token, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_secret)
        api = tweepy.API(auth)
        tweet = template % (self.tweet['from_user'], self.tweet["soundcloud_path"])
        self.log.debug("Tweeting: %s" % (tweet))
        tweet = api.update_status(tweet)
        return self.store()
    
    def getTemplate(self):
        self.log.debug("Loading template file.")
        templateFile = open("templates.txt")
        templates = [i for i in templateFile.readlines()]
        template = random.choice(templates)
        self.log.debug("Selecting template: %s" % (template))
        return template
    
    def store(self):
        self.log.debug("Storing tweet in cache.")
        self.util.redis.sadd(self.tweet['id_str'], self.tweet)
        return self.util.redis.sadd("processed", self.tweet['id_str'])

class CleanupTwonbe(Job):
    def __init__(self, id, queue, tweet):
        self.id = id
        self.tweet = tweet
        Job.__init__(self, "TweetTwonbe", id, queue)
        
    def process(self):
        cleanup_list = [self.tweet['vox_tmp'], self.tweet['vox_tmp2'], self.tweet['beat_tmp'], self.tweet['mix_tmp'], self.tweet['twonbe'], self.tweet['vox_path']]
        for file in cleanup_list:
            self.log.debug("Deleting %s" % (file))
            try:
                self.util.delete(file)
            except Exception as e:
                raise TwonbeError(e, "%s: %s failed to delete file %s" % (self.name, self.id, file))
            self.log.debug("Deleted %s" % (file))
        return self.log.debug("Cleanup job complete.")
        

'''
Utility functions
'''
class Utility(object):
    def __init__(self):
        # Configuration directives
        self.log = logging.getLogger("Utility")
        self.hash = None
        global logging_level
        self.log.setLevel(logging_level)
        self.log.addHandler(log_handler)
        self.redis = redis.Redis(redis_host)
    
    def timestr(self, seconds):
        if seconds >= 24*60*60:
            days,seconds = divmod(seconds,24*60*60)
            return "%i days %s" % (days, self.timestr(seconds))        
        elif seconds >= 60*60:
            hours,seconds = divmod(seconds,60*60)
            return "%i hours %s" % (hours,self.timestr(seconds))
        elif seconds >= 60:
            return "%i min %.3f s" % divmod(seconds, 60)
        elif seconds >= 1:
            return "%.3f s" % seconds
        else:
            return "%i ms" % int(seconds*1000)
    
    def request(self, path, params=None):
        # Add debugging to post if logging level is debug
        if logging_level == logging.DEBUG:
            h=urllib2.HTTPHandler(debuglevel=1)
            opener = urllib2.build_opener(h)
            urllib2.install_opener(opener)
        if "http" not in path:
            self.log.debug("Path is not a URI - skipping.")
            return False
        if params:
            self.log.debug("Making post request...")
            request = urllib2.Request(path, urllib.urlencode(params))
            print request
        else:
            request = urllib2.Request(path)
        self.log.debug("Retrieving URI: %s" % (path))
        try:
            r = urllib2.urlopen(request)
        except urllib2.URLError as e:
            self.log.error("Could not reach URI: %s" % (path))
            return False
        self.log.debug("URI retrieved: %s" % (path))
        if "json" in path:
            return simplejson.loads(r.read())
        else:
            return r.read()
    
    def write(self, file, data):
        try:
            f = open(file, "w")
            f.write(data)
            f.close()
            return True
        except Exception as e:
            raise TwonbeError(e, "Error writing file %s" % (file))
    
    def delete(self, file):
        try:
            os.remove(file)
            return True
        except Exception as e:
            raise TwonbeError(e, "Error delete file %s" % (file))
     

'''
Twonbe Exception
'''
class TwonbeError(Exception):
    def __init__(self, message, e):
        Exception.__init__(self, message)
        # Configuration directives
        self.log = logging.getLogger("TwonbeError")
        self.log.setLevel(logging_level)
        self.log.addHandler(log_handler)
        if logging_level == logging.DEBUG:
            self.errorOut(message, e)
        else:
            self.errorLog(message, e)
    
    def errorLog(self, message, e):
        self.log.error("%s! %s" % (str(e), message))
        pass
        
    def errorOut(self, message, e):
        return self.log.error("%s! %s" % (str(e), message))
            
'''
Implementation
'''
def main():
    queue = Queue.Queue(0)
    tob = TwonbeDaemon(queue)
    queue.put(PollTwitter("0", queue))
    tob.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "\nDone!"