'''
TweetOnBeats Mixer
Written by /rob, adapted from Johannes Wagener's Ruby implementation
Music Hack Day NYC 12 February 2011
'''

'''Modules'''
import subprocess
import sys
import os
import random

'''Classes'''
class Mixer:
    def __init__(self, vox):
        # Vox, beat and outro raw files.
        self.beat = self.getBeat()
        self.vox = vox
        self.outro = self.getOutro()
        
        # Volumes
        self.vox_volume = 0.7
        self.beat_volume = 0.6
        
        # Mixing parameters
        self.bpm = int(self.beat.split("_")[1])
        self.offset= int((60.0/(self.bpm / 4))*2)
        self.voice_length = os.path.getsize(self.vox) / 7452
        self.almost_full_length = int(self.offset + self.voice_length + 1)
        
        # Mix that shit.
        self.twonbe = self.mix(self.beat, self.vox, self.outro)
               
    def mix(self, beat, vox, outro):
        # Generate mixing temporary filenames.
        vox_tmp = self.tempFileName("v1")
        vox_tmp2 = self.tempFileName("v2")
        beat_tmp = self.tempFileName()
        mix_tmp = self.tempFileName()
        final_tmp = self.tempFileName("final")
        
        print vox_tmp2
        # Sox mixing
        self.log("Mixing TwOnBe...")
        self.log("Converting vox...")
        convert_vox = subprocess.Popen(["sox", "-G", self.vox, "-c", "2", vox_tmp, "rate", "44100"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        convert_vox.wait()
        self.log(convert_vox.communicate())
        
        self.log("Mixing vox offset of " + str(self.offset))
        offset_vox = subprocess.Popen(["sox", "-G", vox_tmp, vox_tmp2, "vol", str(self.vox_volume), "delay", str(self.offset), str(self.offset)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        offset_vox.wait()
        self.log(str(offset_vox.communicate()))
        
        self.log("Trimming beat...")
        trim_beat = subprocess.Popen(["sox", self.beat, beat_tmp, "trim", "0", str(self.almost_full_length), "vol", str(self.beat_volume)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        trim_beat.wait()
        self.log(str(trim_beat.communicate()))
        
        self.log("Mixing vox and beat...")
        mix_vox_and_beat = subprocess.Popen(["sox", "-G", "-m", vox_tmp2, beat_tmp, mix_tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        mix_vox_and_beat.wait()
        self.log(str(mix_vox_and_beat.communicate()))
        
        self.log("Mixing TwOnBe outro...")
        mix_twonbe = subprocess.Popen(["sox", "-G",  mix_tmp, outro, final_tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        mix_twonbe.wait()
        self.log(str(mix_twonbe.communicate()))
        
        return final_tmp
      
    def read(self):
        return self.twonbe

    def write(self, file, data):
        try:
            f = open("/tmp/" + str(file), 'wb')
            f.write(data)
            f.close()
            return True
        except:
            return False
        
    def getBeat(self):
        try:
            beats = os.listdir("beats")
            beat = random.choice(beats)
            return "beats/" + str(beat)
        except OSError:
            raise MixerError("Cannot find beats directory.")
        
    def getOutro(self):
        try:
            outros = os.listdir("outros")
            outro = random.choice(outros)
            return "outros/" + str(outro)
        except OSError:
            raise MixerError("Cannot find beats directory.")
    
    def tempFileName(self, name="", ext=".wav"):
        return "/tmp/tweetsonbeats-" + name + str(random.randint(1, 9999)) + ext
    
    def log(self, string):
        print string
        
class MixerError(Exception):
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
        vox = sys.argv[1]
    except IndexError:
        print "Usage: mixer.py [path to voice file]"
    mixer = Mixer(vox)
    try:
        print mixer.read()
    except:
        print "Mix failed!"