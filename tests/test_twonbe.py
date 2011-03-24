'''
Tweets On Beats Tests

written by /rob, 23 March 2011
(as Twitter Search still sucks and I can't test my new code any other way)
'''
import unittest
import logging
import logging.handlers

import sys, os
sys.path.append(os.path.abspath("."))
import twonbe


'''
Configuration variables
'''
searchapi = "http://search.twitter.com"
keyword = "#beatify"
logging_level = logging.INFO
log_handler = logging.handlers.RotatingFileHandler("tweetsonbeats_test.log", maxBytes=524288000, backupCount=5) 
log_formatter = logging.Formatter('%(asctime)s::%(name)s::%(levelname)s::%(message)s')
log_handler.setFormatter(log_formatter)
logging.basicConfig()
redis_host = "localhost"


'''
Job Tests
'''
class Test_PollTwitter(unittest.TestCase):
    def setUp(self):
        twonbe = twonbe.TwonbeDaemon()
    
    def test_buildRequest(self):
        stub = True
    
    
    


'''
Utility Tests
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
            