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
import memcache

'''
Configuration variables
'''
searchapi = "http://search.twitter.com"
keyword = "beatify"
memcacheHosts = ['localhost:11211']
loggingLevel = logging.DEBUG
logging.basicConfig()


'''
Main Daemon
Broker for all Twonbe jobs
'''
class TwonbeDaemon(threading.Thread):
    def __init__(self, interval=10):
        self.elapsed = 0
        self.fault = False
        self.timer = threading.Event()
        self.interval = interval
        self.util = Utility() 
        self.jobs = []
        threading.Thread.__init__(self)

        # Configuration directives
        self.log = logging.getLogger("TwonbeDaemon")  
        global loggingLevel
        self.log.setLevel(loggingLevel)
        self.log.info("Initialized.")

    def run(self):
        # Main loop
        self.log.info("Launching Twonbe Daemon.")
        while self.fault is False:
            self.log.debug("Elapsed time: %s" % (str(self.elapsed)))
            try:
                self.process()
            except Exception as e:
                raise TwonbeError(e, "Error encountered processing job.")
            self.check()
            self.timer.wait(self.interval)
            self.elapsed = self.elapsed + self.interval

    def process(self):
        # Process job queue
        global loggingLevel
        if loggingLevel == logging.DEBUG:
            self.log.debug("Job queue: %s" % (str(len(self.jobs))))
        if self.jobs:
            for job in self.jobs:
                try:
                    self.log.info("Processing job: %s" % (job.name))
                    job.process()
                    job.elapsed = 0
                except Exception as e:
                    self.stop()
                    raise TwonbeError(e, "encountered error with job: %s" % (job.name))
    
    def addJob(self, job):
        self.log.debug("Adding new %s job: %s" % (job.name, job.id))
        try:
            self.jobs
            self.jobs.append(job)
        except Exception as e:
            raise TwonbeError(e, "encountered error adding %s job: %s" % (job.name, job.id))
        return self.log.debug("Added new %s job: %s" % (job.name, job.id))
    
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
class Job(object):
    def __init__(self, name, id, interval=10):
        self.name = name   
        self.id = id
        self.interval = interval
        self.elapsed = 0
        self.util = Utility()
        global twonbe
        self.twonbe = twonbe
        
        # Configuration directives
        self.log = logging.getLogger(name)
        global loggingLevel
        self.log.setLevel(loggingLevel)
        self.log.debug("Created %s job: %s" % (self.name, self.id))
    
    def run(self):
        # Error-safe wrapper for user-defined job logic
        self.log.debug("Starting %s job: %s" % (self.name, self.id))
        try:
            self.log.info("Processing %s job: %s" % (self.name, self.id))
            self.process()
            self.log.debug("Finished %s job: %s" % (self.name, self.id))
        except Exception as e:
            raise TwonbeError(e, "%s failed:" % (job.name))
        
    def process(self):
        # Extend this function to initiate job logic.
        return


'''
Jobs
These are the individual jobs chained together to convert a tweet into a Twonbe
'''
class PollTwitter(Job):
    def __init__(self, id, lastProcessedId=None):
        self.lastProcessedId = lastProcessedId
        Job.__init__(self, "PollTwitter", id)
    
    def process(self):
        # Build polling request
        self.log.debug("Building polling request.")
        global searchapi
        global keyword
        if self.lastProcessedId:
            params = {
                'q': keyword,
                'result_type': "recent",
                'since_id': lastProcessedId
            }
        else:
            params = {
                'q': keyword,
                'result_type': "recent"
            }
        path = searchapi + "/search.json?" + urllib.urlencode(params)
        json = self.util.request(path)
        self.log.debug("Parsing JSON object.")
        data = simplejson.loads(data)
        self.log.debug("Returned JSON: %s" % (str(data)))

class FilterTweet(Job):
    def __init__(self, id):
        Job.__init__(self, "FilterTweet", id)
    
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


'''
Utility functions
'''
class Utility:
    def __init__(self):
        # Configuration directives
        self.log = logging.getLogger("Utility")
        global loggingLevel
        self.log.setLevel(loggingLevel)
        if loggingLevel == logging.DEBUG:
            logger = 1
        else:
            logger = 0
        global memcacheHosts
        self.mc = memcache.Client(memcacheHosts, debug=logger)
    
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
        global loggingLevel
        if loggingLevel == logging.DEBUG:
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
    def __init__(self, e, m):
        # Configuration directives
        self.log = logging.getLogger("TwonbeError")
        global loggingLevel
        self.log.setLevel(loggingLevel)
        self.log.error(self.errorMessage(e, m))
    
    def errorMessage(self, e, m):
        return "%s! %s" % (m, self.args[0])
        
   
    
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