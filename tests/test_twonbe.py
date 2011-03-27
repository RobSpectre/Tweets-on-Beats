'''
Tweets On Beats Tests

written by /rob, 23 March 2011
(as Twitter Search still sucks and I can't test my new code any other way)
'''
import unittest
import logging
import logging.handlers
from mock import Mock
import datetime

import sys, os
sys.path.append(os.path.abspath("."))
import twonbe

'''
Job Tests
'''

class Test_Job(unittest.TestCase):
    def setUp(self):
        self.util = twonbe.Utility()
        self.queue = Mock()
        self.tweet = {'iso_language_code': 'en', 'to_user_id_str': None, 'text': 'This is not a test of the emergency broadcasting system.  It\'s the real thing. #beatify', 'from_user_id_str': '229093598', 'profile_image_url': 'http://a3.twimg.com/sticky/default_profile_images/default_profile_6_normal.png', 'id': 50873958400147456L, 'source': '&lt;a href=&quot;http://twitter.com/&quot;&gt;web&lt;/a&gt;', 'id_str': '50873958400147456', 'from_user': 'twonbe', 'from_user_id': 229093598, 'to_user_id': None, 'geo': None, 'created_at': 'Thu, 24 Mar 2011 10:57:51 +0000', 'metadata': {'result_type': 'recent'}}
'''    
class Test_PollTwitter(Test_Job):
    def setUp(self):
        Test_Job.setUp(self)
        self.expected_request = "http://search.twitter.com/search.json?q=%23beatify&result_type=recent"
        self.expected_request_lastprocessed = "http://search.twitter.com/search.json?q=%23beatify&result_type=recent&since_id=12345"
        self.poll = twonbe.PollTwitter("0", self.queue)
    
    def test_buildRequest(self):
        test = self.poll.buildRequest()
        self.assertEqual(test, self.expected_request)
    
    def test_buildRequestWithLastProcessedId(self):
        self.poll.lastProcessedId = "12345"
        test = self.poll.buildRequest()
        self.assertEqual(test, self.expected_request_lastprocessed)

    def test_Polling(self):
        test = self.poll.process()
        self.assertTrue(test)

class Test_CheckTweet(Test_Job):
    def setUp(self):
        Test_Job.setUp(self)
        # Set up mock tweets
        self.spanish_tweet = dict(self.tweet)
        self.spanish_tweet['iso_language_code'] = "es"
        self.new = dict(self.tweet)
        self.new['created_at'] = datetime.datetime.strftime(datetime.datetime.utcnow(), "%a, %d %b %Y %H:%M:%S")
        self.contains_rt = dict(self.tweet)
        self.contains_rt['text'] = "RT This contains a retweet."
        self.util.redis.sadd("attempted", self.tweet['id_str'])
    
    def tearDown(self):
        self.util.redis.delete("attempted")
        
    def test_isAttempted(self):
        check = twonbe.CheckTweet("0", self.queue, self.tweet)
        test = check.isAttempted()
        self.assertTrue(test, "Result was instead: %s" % str(test))
    
    def test_isNotAttempted(self):
        self.util.redis.srem("attempted", self.tweet['id_str'])
        check = twonbe.CheckTweet("0", self.queue, self.tweet)
        test = check.isAttempted()
        self.assertFalse(test, "Result was instead: %s" % str(test))

    def test_isOld(self):
        print self.tweet
        check = twonbe.CheckTweet("0", self.queue, self.tweet)
        test = check.isOld()
        self.assertTrue(test, "Result was instead: %s" % str(test))
 
    def test_isNew(self):
        check = twonbe.CheckTweet("0", self.queue, self.new)
        test = check.isOld()
        self.assertFalse(test, "Result was instead: %s" % str(test))
        
    def test_isNotEnglish(self):
        check = twonbe.CheckTweet("0", self.queue, self.spanish_tweet)
        test = check.isNotEnglish()
        self.assertTrue(test, "Result was instead: %s" % str(test))
        
    def test_isEnglish(self):
        check = twonbe.CheckTweet("0", self.queue, self.tweet)
        test = check.isNotEnglish()
        self.assertFalse(test, "Result was instead: %s" % str(test))
        
    def test_isRetweet(self):
        check = twonbe.CheckTweet("0", self.queue, self.contains_rt)
        test = check.isRetweet()
        self.assertTrue(test, "Result was instead: %s" % str(test))
    
    def test_isNotRetweet(self):
        check = twonbe.CheckTweet("0", self.queue, self.tweet)
        test = check.isRetweet()
        self.assertFalse(test, "Result was instead: %s" % str(test))
    
    def test_processFail(self):
        check = twonbe.CheckTweet("0", self.queue, self.tweet)
        test = check.process()
        self.assertFalse(test, "Result was instead: %s" % str(test))
    
    def test_processSuccess(self):
        self.util.redis.srem("attempted", self.tweet['id_str'])
        check = twonbe.CheckTweet("0", self.queue, self.new)
        test = check.process()
        self.assertTrue(test, "Result was instead: %s" % str(test))
'''

class Test_CheckTweet(Test_Job):
    def setUp(self):
        Test_Job.setUp(self)
        self.tweet['text'] = "This tweet $!%# contains http://loadsof.junk with other @dn0t"
        self.contains_uri = "This contains a link http://example.com"
        self.contains_hashtag = "This tweet contains a #hashtag."
        self.contains_reply = "This tweet contains a reference to @dN0t."
        self.contains_characters = "This tweet !# contains $% a bunch of %^ characters &*()"
        self.filter = twonbe.FilterTweet("0", self.queue, self.tweet)
        
    def test_filterUris(self):
        test = self.filter.filterUris(self.contains_uri)
        self.assertEqual(test, "This contains a link ")
    
    def test_filterReplies(self):
        test = self.filter.filterReplies(self.contains_reply)
        self.assertEqual(test, "This tweet contains a reference to Rob Spectre.")
        
    def test_filterTags(self):
        test = self.filter.filterTags(self.contains_hashtag)
        self.assertEqual(test, "This tweet contains a ")
        
    def test_filterCharacters(self):
        test = self.filter.filterCharacters(self.contains_characters)
        self.assertEqual(test, "This tweet  contains  a bunch of  characters ")
    
    def test_processSuccess(self):       
        test = self.filter.process()
        self.assertEqual(self.filter.tweet['filtered_text'], "This tweet  contains  with other Rob Spectre")
'''
Utility Tests
'''
'''
class Test_Utility(unittest.TestCase):
    def setUp(self):
        self.util = twonbe.Utility()
        
class Test_timestr(Test_Utility):
    def setUp(self):
        self.seconds = 6888888
        self.bad_input = "foobar"
        self.expected = "79 days 17 hours 34 min 48.000 s"
        Test_Utility.setUp(self)
    
    def test_timestr(self):
        test = self.util.timestr(self.seconds)
        self.assertEqual(test, self.expected,
                         "Timestr did not return value %s, instead returned: %s" % (self.expected, test))
    
    def test_badInput(self):
        self.assertRaises(TypeError, self.util.timestr, self.bad_input)
        
class Test_request(Test_Utility):
    def setUp(self):
        self.fourohfour_uri = "http://www.gonzee.tv/404.html"
        self.unreachable_uri = "http://foo.bar"
        self.bad_path = "not even a path"
        self.get_uri = "http://dev.dn0t.dontexist.com/static_test.html"
        self.post_uri = "http://dev.dn0t.dontexist.com/postEcho.php"
        self.expected_post = "<html>\n<head>\n<title>Echo POST</title>\n<body>\n\t<h1>test</h1>\n</body>\n</html>\n"
        self.expected_json = {"echo":"test"}
        self.expected_html = '<!DOCTYPE html> \n<html lang="en"> \n<head>\n\t<title>Static Test URL</title> \n</head>\n<body>\n<h1>Why are you reading this, human?</h1>\n</body>\n</html>\n'
        Test_Utility.setUp(self)
    
    def test_getRequest(self):
        test = self.util.request(self.get_uri)
        self.assertEqual(test, self.expected_html)
        
    def test_get404(self):
        test = self.util.request(self.fourohfour_uri)
        self.assertFalse(test)
        
    def test_unreachable(self): 
        test = self.util.request(self.unreachable_uri)
        self.assertFalse(test)
        
    def test_postRequest(self):
        params = {"echo": "test"}
        test = self.util.request(self.post_uri, params)
        self.assertEqual(test, self.expected_post,
                         "Unexpected output: %s" % (str(test)))
    
    def test_getJSON(self):
        params = {"echo": "test", "format": "json"}
        test = self.util.request(self.post_uri + "?json", params)
        print test
        self.assertEqual(test, self.expected_json, 
                         "Unexpected output: %s" % (str(test)))
        
    def test_badPath(self):
        test = self.util.request(self.bad_path)
        
class Test_write(Test_Utility):
    def setUp(self):
        self.good_dir = "good_file"
        self.bad_dir = "foo/bar/bad_file"
        self.no_rights = "/var/log/no_rights"
        self.cleanup = False
        Test_Utility.setUp(self)
        
    def test_goodDir(self):
        test = self.util.write(self.good_dir, "This is a good file.")
        self.cleanup = self.good_dir
        self.assertTrue(self.cleanup)
        
    def test_badDir(self):
        self.assertRaises(twonbe.TwonbeError, self.util.write, self.bad_dir, "This is a bad file.")
    
    def test_noRights(self):
        self.assertRaises(twonbe.TwonbeError, self.util.write, self.no_rights, "This file has no rights.")
    
    def tearDown(self):
        if self.cleanup:
            os.remove(self.cleanup)
            
class Test_delete(Test_Utility):
    def setUp(self):
        self.good_dir = "good_file"
        self.bad_dir = "foo/bar/bad_file"
        self.no_rights = "/var/log/no_rights"
        Test_Utility.setUp(self)
    
    def writeFile(self, file, data):
        try:
            f = open(file, "w")
            f.write(data)
            f.close()
        except:
            raise Exception
    
    def test_goodDir(self):
        good_file = self.writeFile(self.good_dir, "This is a good file.")
        test = self.util.delete(self.good_dir)
        self.assertTrue(test)
    
    def test_badDir(self):
        self.assertRaises(twonbe.TwonbeError, self.util.delete, self.bad_dir)
        
    def test_noRights(self):
        self.assertRaises(twonbe.TwonbeError, self.util.delete, self.no_rights)
'''       