#!/usr/bin/env ruby
def temp_file(name='', ext='.wav')
  "/tmp/tweetsonbeats-#{name}-#{rand()*9999}#{ext}"
end

voice = ARGV.shift
beat = ARGV.shift
bpm = beat.split("_")[1].to_i
offset = 60.0/bpm*4
voice_length = File.size(voice) / 1024 * 0.0116
almost_full_length = offset + voice_length + 2


voice_tmp = temp_file('v1')
voice_tmp2 = temp_file('v2')

beat_tmp = temp_file
mix_tmp = temp_file

`sox -G #{voice} -c 2 #{voice_tmp} rate 44100`
`sox -G #{voice_tmp}  #{voice_tmp2} vol 2.3  delay #{offset.to_i} #{offset.to_i}`

`sox #{beat} #{beat_tmp} trim 0 #{almost_full_length} vol 0.2`

`sox -G -m  #{voice_tmp2} #{beat_tmp} #{mix_tmp}`
`sox -G #{mix_tmp} outro.wav TweetBeat.wav`


#`rm #{voice_tmp} #{beat_tmp} #{mix_tmp} #{voice_tmp2}`
