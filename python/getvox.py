import re, string
import simplejson as json
import urllib2

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
    
    def filterReplies(self, input):
        # Extract @reply
        if "@" in input:
            t = input[input.find("@"):]
            t = t[:t.find(" ")]
        
            user = self.request("http://api.twitter.com/1/users/show.json?screen_name=" + t)
            output = input.replace(t, user['name'])
            
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