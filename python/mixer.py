'''
TweetOnBeats Mixer
Written by /rob, adapted from Johannes Wagener's Ruby implementation
Music Hack Day NYC 12 February 2011
'''

'''Modules'''
import subprocess

'''Classes'''
class Mixdown:
    def __init__(self, beat, vox):
        self.beat = beat
        self.vox = vox
        
    def offset(self, vox):
        stub = True
        
    def mix(self, beat, vox):
        stub = True
      
    def read(self):
        return self.mix

    def write(self, file, data):
        try:
            f = open("/tmp/" + str(file), 'wb')
            f.write(data)
            f.close()
            return True
        except:
            return False
        

'''Implementation'''
if __name__ == "__main__":
    stub = True