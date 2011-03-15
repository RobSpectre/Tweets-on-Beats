'''
Tweets On Beats
A Twitter bot that puts your beat on a fat (or alternatively phat) beat.

Version 2.0 - a shiteload better.

Written by /rob, 11 March 2011
'''
import threading
import logging
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

'''
Configuration variables
'''
searchapi = "http://search.twitter.com"
keyword = "#beatify"
logging_level = logging.DEBUG
logging.basicConfig()
redis_host = "localhost"

'''
Main Daemon
Broker for all Twonbe jobs
'''
class TwonbeDaemon(threading.Thread):
    def __init__(self, interval=10):
        self.elapsed = 0
        self.fault = False
        self.interval = interval
        self.util = Utility() 
        self.jobs = []
        threading.Thread.__init__(self)

        # Configuration directives
        self.log = logging.getLogger("TwonbeDaemon")  
        global logging_level
        self.log.setLevel(logging_level)
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
                #self.check()
                self.elapsed = self.elapsed + self.interval
        except KeyboardInterrupt:
            print "\nDone!"

    def process(self):
        # Process job queue
        global logging_level
        if logging_level == logging.DEBUG and self.jobs:
            self.log.debug("Job queue: %s" % (str(len(self.jobs))))
        if self.jobs:
            for job in self.jobs:
                try:
                    self.log.info("Processing job: %s" % (job.name))
                    job.elapsed = 0
                    job.start()
                    self.removeJob(job)
                except Exception as e:
                    self.stop()
                    raise TwonbeError(e, "encountered error with job: %s" % (job.name))
    
    def addJob(self, job):
        self.log.debug("Adding new %s job: %s" % (job.name, job.id))
        try:
            self.jobs.append(job)
        except Exception as e:
            raise TwonbeError(e, "encountered error adding %s job: %s" % (job.name, job.id))
        return self.log.debug("Added new %s job: %s" % (job.name, job.id))
    
    def removeJob(self, job):
        self.log.debug("Removing %s job: %s" % (job.name, job.id))
        try:
            self.jobs.remove(job)
        except Exception as e:
            raise TwonbeError(e, "encountered error adding %s job: %s" % (job.name, job.id))
        return self.log.debug("Removed %s job: %s" % (job.name, job.id))
    
    def stop(self):
        self.log.debug("Stop command received.")
        self.fault = True
        return self.log.info("Stop command issued.")
    
    def check(self):
        # Extend this function to run your own check to see if loop should keep running.
        self.log.debug("Running checks to stop daemon.")
        return self.log.debug("No reason to stop daemon.")

        
'''
Object for Jobs

Extend this object and add to TwonbeDaemon object to queue and process.
'''
class Job(threading.Thread):
    def __init__(self, name, id, interval=None):
        threading.Thread.__init__(self)
        self.name = name   
        self.id = id
        self.interval = interval
        self.elapsed = 0
        self.util = Utility()
        self.timer = threading.Event()
        global twonbe
        self.twonbe = twonbe
        
        # Configuration directives
        self.log = logging.getLogger(name)
        global logging_level
        self.log.setLevel(logging_level)
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
    def __init__(self, id, lastProcessedId=None):
        self.id = id
        self.lastProcessedId = lastProcessedId
        Job.__init__(self, "PollTwitter", id, 30)
    
    def process(self):
        self.log.debug("Starting to process polling job.")
        path = self.buildRequest()
        if path:
            data = self.util.request(path)
        else:
            raise TwonbeError("Error polling", "Could not build request path.")
        
        if data:
            if data['results']:
                for tweet in reversed(data['results']):
                    self.log.debug("Queueing up tweet to be checked: %s" % (tweet['id_str']))
                    self.twonbe.addJob(CheckTweet(tweet['id_str'], tweet))
                    lastProcessedId = tweet['id_str']
                self.log.debug('Completed poll - scheduling next one.')
                return self.twonbe.addJob(PollTwitter(str(int(self.id) + 1), lastProcessedId))
            else:
                self.log.debug("No results returned.")
                return self.twonbe.addJob(PollTwitter(str(int(self.id) + 1), self.lastProcessedId))
        else:
            self.log.debug('Found no data in this job - scheduling next one.')
            return self.twonbe.addJob(PollTwitter(str(int(self.id) + 1), self.lastProcessedId))
    
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
    def __init__(self, id, tweet):
        self.id = id
        self.tweet = tweet
        self.limit = 600
        Job.__init__(self, "CheckTweet", id)
        
    def process(self):
        if self.isNotEnglish() or self.isAttempted():
            self.log.debug("Tweet does not pass initial checks - skipping.")
            return False
        else:
            self.log.info("Tweet passes initial checks - filtering.")
            return self.twonbe.addJob(FilterTweet(self.id, self.tweet))
    
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

class FilterTweet(Job):
    def __init__(self, id, tweet):
        self.id = id
        self.tweet = tweet
        Job.__init__(self, "FilterTweet", id)
    
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
        return self.twonbe.addJob(GenderCheck(self.id, self.tweet))
    
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
        if "@ " in input:
            pass
        elif "@" in input:
            t = input[input.find("@"):]
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
    def __init__(self, id, tweet):
        self.id = id
        self.tweet = tweet
        self.face = face_client.FaceClient()
        Job.__init__(self, "GenderCheck", id)
        
    def process(self):
        try:
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
        return self.twonbe.addJob(SynthesizeTweet(self.id, self.tweet))
                    
    def detect(self, uri):
        return self.face.faces_detect(uri)

class SynthesizeTweet(Job):
    def __init__(self, id, tweet):
        self.id = id
        self.tweet = tweet
        self.voice = "usenglishfemale1"
        self.hash = None
        Job.__init__(self, "SynthesizeTweet", id)
        
    def process(self):
        self.log.debug("Synthesizing filtered text...")
        hash = hashlib.md5(self.tweet['filtered_text']).hexdigest()
        voice = self.getVoice(self.tweet['gender'])
        vox = self.downloadVox(voice, self.tweet['filtered_text'])
        self.tweet['vox_path'] = self.writeVox(hash, vox)
        return self.twonbe.addJob(MixTwonbe(self.id, self.tweet))
           
    def getVoice(self, gender):
        if gender == "female":
            return "usenglishfemale1"
        else:
            return "usenglishmale1"
    
    def downloadVox(self, voice, text):
        path = "https://api.ispeech.org/api/rest/?"
        params = {
            'apikey': "38fcab81215eb701f711df929b793a89",
            'action': "convert",
            'voice': voice,
            'speed': -2,
            'text': text
        }
    
    def writeVox(self, hash, vox):
        self.util.write("/tmp/" + str(hash) + ".mp3", vox)
        return "/tmp/" + str(hash) + ".mp3"
    
class MixTwonbe(Job):
    def __init__(self, id, tweet):
        self.id = id
        self.tweet = tweet
        
        # Vox, beat and outro raw files.
        self.beat = self.getBeat()
        self.vox = self.tweet['vox_path']
        self.outro = self.getOutro()
        
        # Volumes
        self.vox_volume = 0.7
        self.beat_volume = 0.6
        
        # Mixing parameters
        self.bpm = int(self.beat.split("_")[1])
        self.offset= int((60.0/(self.bpm / 4))*2)
        self.voice_length = os.path.getsize(self.vox) / 7452
        self.almost_full_length = int(self.offset + self.voice_length + 1)
        
        Job.__init__(self, "MixTwonbe", id)
        
    def process(self):
        # Generate mixing temporary filenames.
        self.vox_tmp = self.tempFileName("v1")
        self.vox_tmp2 = self.tempFileName("v2")
        self.beat_tmp = self.tempFileName()
        self.mix_tmp = self.tempFileName()
        self.final_tmp = self.tempFileName("final")
        
        # Mix TwOnBe
        try:
            self.convertVox()
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to convert vox:" % (self.name, self.id))
        try:
            self.offsetVox()
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to offset vox:" % (self.name, self.id))
        try:
            self.trimBeat()
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to trim beat:" % (self.name, self.id))
        try:
            self.mixVoxAndBeat()
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to mix vox and beat:" % (self.name, self.id))
        try:
            self.mixOutro()
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to mix outro:" % (self.name, self.id))
        
        # Add paths to tweet
        self.tweet['vox_tmp'] = self.vox_tmp
        self.tweet['vox_tmp2'] = self.vox_tmp2
        self.tweet['beat_tmp'] = self.beat_tmp
        self.tweet['mix_tmp'] = self.mix_tmp
        self.tweet['twonbe'] = self.final_tmp
        
        # Queue up next job
        return self.twonbe.addJob(UploadTwonbe(self.id, self.tweet))
    
    def convertVox(self):
        self.log.debug("Mixing TwOnBe...")
        self.log.debug("Converting vox...")
        convert_vox = subprocess.Popen(["sox", "-G", self.vox, "-c", "2", self.vox_tmp, "rate", "44100"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        convert_vox.wait()
        return self.log.debug(convert_vox.communicate())
    
    def offsetVox(self):
        self.log.debug("Mixing vox offset of " + str(self.offset))
        offset_vox = subprocess.Popen(["sox", "-G", self.vox_tmp, self.vox_tmp2, "vol", str(self.vox_volume), "delay", str(self.offset), str(self.offset)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        offset_vox.wait()
        return self.log.debug(str(offset_vox.communicate()))
        
    def trimBeat(self):
        self.log.debug("Trimming beat...")
        trim_beat = subprocess.Popen(["sox", self.beat, self.beat_tmp, "trim", "0", str(self.almost_full_length), "vol", str(self.beat_volume)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        trim_beat.wait()
        return self.log.debug(str(trim_beat.communicate()))
    
    def mixVoxAndBeat(self):
        self.log.debug("Mixing vox and beat...")
        mix_vox_and_beat = subprocess.Popen(["sox", "-G", "-m", self.vox_tmp2, self.beat_tmp, self.mix_tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        mix_vox_and_beat.wait()
        return self.log.debug(str(mix_vox_and_beat.communicate()))
    
    def mixOutro(self):
        self.log.debug("Mixing TwOnBe outro...")
        mix_twonbe = subprocess.Popen(["sox", "-G",  self.mix_tmp, self.outro, self.final_tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        mix_twonbe.wait()
        return self.log.debug(str(mix_twonbe.communicate()))
               
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
    def __init__(self, id, tweet):
        self.id = id
        self.tweet = tweet
        Job.__init__(self, "UploadTwonbe", id)
    
    def process(self):
        self.log.debug("Uploading TwOnBe...")
        try:
            mix_twonbe = subprocess.Popen(["ruby", "upload.rb", self.tweet['twonbe'], self.tweet['from_user'],  self.tweet['filtered_text']], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            mix_twonbe.wait()
            output = mix_twonbe.communicate()
        except Exception as e:
            raise TwonbeError(e, "%s: %s failed to upload TwOnBe:" % (self.name, self.id))
        self.log.debug("Twonbe uploaded here: %s" % (output))
        self.tweet['soundcloud_path'] = output
        self.log.debug("Queueing cleanup of files:")
        self.twonbe.addJob(CleanupTwonbe(self.id, self.tweet))
        return self.twonbe.addJob(TweetTwonbe(self.id, self.tweet))

class TweetTwonbe(Job):
    def __init__(self, id, tweet):
        self.id = id
        self.tweet = tweet
        # Twitter credentials
        self.consumer_token = "bzdPlHk429kKb3ZsUfhQw"
        self.consumer_secret = "25hF3WTQ6h9njyqgS2V9a0jQ2MBkePdBwBshA5IajlY"
        self.access_token = "251275058-4xfy2Bw1MR6fW1KHdz61px1NzPO7ao5i8E46U0NR"
        self.access_secret = "6O2kYW5osJMXDfvlxu3Bj9nZcSctxNrpNMxAq8HhcbI"      
        Job.__init__(self, "TweetTwonbe", id)
    
    def process(self):
        template = self.getTemplate()        
        auth = tweepy.OAuthHandler(self.consumer_token, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_secret)
        api = tweepy.API(auth)
        tweet = template % (self.tweet['from_user'], self.tweet["soundcloud_path"])
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
    def __init__(self, id, cleanup):
        self.id = id
        self.cleanup = cleanup
        Job.__init__(self, "TweetTwonbe", id)
        
    def process(self):
        cleanuplist = [self.tweet['vox_tmp'], self.tweet['vox_tmp2'], self.tweet['beat_tmp'], self.tweet['mix_tmp'], self.tweet['twonbe'], self.tweet['vox_path']]
        for file in cleanupList:
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
class Utility:
    def __init__(self):
        # Configuration directives
        self.log = logging.getLogger("Utility")
        self.hash = None
        global logging_level
        self.log.setLevel(logging_level)
        if logging_level == logging.DEBUG:
            logger = 1
        else:
            logger = 0
        global redis_host
        self.redis = redis.Redis(redis_host)
    
    def timestr(self, seconds):
        if seconds >= 24*60*60:
            days,seconds = divmod(seconds,24*60*60)
            return "%i days %s" % (days, self.timestr(seconds))        
        elif seconds >= 60*60:
            hours,seconds = divmod(seconds,60*60)
            return "%i hours %s" % (hours,timestr(seconds))
        elif seconds >= 60:
            return "%i min %.3f s" % divmod(seconds, 60)
        elif seconds >= 1:
            return "%.3f s" % seconds
        else:
            return "%i ms" % int(seconds*1000)
    
    def request(self, path, params=None):
        # Add debugging to post if logging level is debug
        global logging_level
        if logging_level == logging.DEBUG:
            h=urllib2.HTTPHandler(debuglevel=1)
            opener = urllib2.build_opener(h)
            urllib2.install_opener(opener)
        if params:
            request = urllib2.Request(path, urllib.urlencode(params))
        else:
            request = urllib2.Request(path)
        self.log.debug("Retrieving URI: %s" % (path))
        try:
            r = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            self.log.error("Could not get URI: %s" % (path))
            return False
        self.log.debug("URI retrieved: %s" % (path))
        if "json" in path:
            return simplejson.loads(r.read())
        else:
            return r.read()
    
    def write(self, file, data):
        try:
            f = open(file)
            f.write(data)
            f.close()
            return True
        except Exception as e:
            raise TwonbeError(e, "Error writing file %s" % (file))
    
    def delete(self, file):
        try:
            os.remove(file)
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
        global logging_level
        self.log.setLevel(logging_level)
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
    global twonbe
    twonbe = TwonbeDaemon()
    twonbe.addJob(PollTwitter("0"))
    twonbe.start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "\nDone!"