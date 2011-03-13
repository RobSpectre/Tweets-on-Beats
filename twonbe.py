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

'''
Configuration variables
'''
searchapi = "http://search.twitter.com"
keyword = "beatify"
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
            json = self.util.request(path)
        else:
            raise TwonbeError("Error polling", "Could not build request path.")
        
        if json:
            self.log.debug("Parsing JSON object.")
            data = simplejson.loads(json)
        else:
            raise TwonbeError("Error polling", "Could not parse JSON object.")
        
        if data:
            for tweet in data['results']:
                self.log.debug("Queueing up tweet to be checked: %s" % (tweet['id_str']))
                self.twonbe.addJob(CheckTweet(tweet['id_str'], tweet))
                lastProcessedId = tweet['id_str']
            self.log.debug('Completed poll - scheduling next one.')
            return self.twonbe.addJob(PollTwitter(str(int(self.id) + 1), lastProcessedId))
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
        if self.isNotEnglish() or self.isOld() or self.isAttempted():
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
        self.log.debug("Processing this shit!")
    
class GenderCheck(Job):
    def __init__(self, id):
        Job.__init__(self, "GenderCheck", id)

class SynthesizeTweet(Job):
    def __init__(self, id):
        Job.__init__(self, "SynthesizeTweet", id)
    
class MixTwonbe(Job):
    def __init__(self, id):
        Job.__init__(self, "MixTwonbe", id)

class UploadTwonbe(Job):
    def __init__(self, id):
        Job.__init__(self, "UploadTwonbe", id)

class TweetTwonbe(Job):
    def __init__(self, id):
        Job.__init__(self, "TweetTwonbe", id)

class CleanupTwonbe(Job):
    def __init__(self, id):
        Job.__init__(self, "TweetTwonbe", id)

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
    
    def request(self, path):
        # Add debugging to post if logging level is debug
        global logging_level
        if logging_level == logging.DEBUG:
            h=urllib2.HTTPHandler(debuglevel=1)
            opener = urllib2.build_opener(h)
            urllib2.install_opener(opener)
        request = urllib2.Request(path)
        self.log.debug("Retrieving URI: %s" % (path))
        try:
            r = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            self.log.error("Could not get URI: %s" % (path))
            return False
        self.log.debug("URI retrieved: %s" % (path))
        data = r.read()   
        return data
     

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