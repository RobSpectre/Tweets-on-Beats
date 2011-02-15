#!/usr/bin/env ruby
require 'soundcloud'
require 'httparty'
require 'twitter'
require 'tweetstream'
OA_KEY= "kc6ehamapugja8gy5zbzmjqwbuarkepd"
TWITTER_USER = "twonbe"
TWITTER_PASS = "foobar"
#TW_CT = "bzdPlHk429kKb3ZsUfhQw"
#TW_CS = "25hF3WTQ6h9njyqgS2V9a0jQ2MBkePdBwBshA5IajlY"
#TW_AT = "251275058-4xfy2Bw1MR6fW1KHdz61px1NzPO7ao5i8E46U0NR"
#TW_AS = "6O2kYW5osJMXDfvlxu3Bj9nZcSctxNrpNMxAq8HhcbI"
#

TW_CT = "Mw8wRMrrTZDzX3ig1Z71A"
TW_CS = "p9AQBMC1Brdpe7RK0SCeSO7kWbnyRmpN66IDmv4J34"
TW_AT = "251212628-nnKe54jjBSlgRguRbwBkXXYKPQ82PUXpeoGS2upx"
TW_AS = "qMtYi6Xi5J0ZVaTWYluiuBxkMsoxz7yOrXr6OMWZgw"

Twitter.configure do |config|
  config.consumer_key = TW_CT
  config.consumer_secret = TW_CS
  config.oauth_token = TW_AT
  config.oauth_token_secret = TW_AS
end

def amplify(text)
  res= HTTParty.get("http://portaltnx20.openamplify.com/AmplifyWeb_v20/AmplifyThis", :query => {apiKey: "kc6ehamapugja8gy5zbzmjqwbuarkepd", responseFormat: "json", inputText:text})
  res["ns1:AmplifyResponse"]["AmplifyReturn"]
end

def get_mood(text)
 amplify(text)["Styles"]["Polarity"]["Mean"]["Value"].to_f
end

def handle_tweet(user, text)
  p "handling #{text}"
  # analyse mood.
  #  mood = get_mood(text)
  # pick a midi
  # canoris midi,text -> speech
  voice_file = sing(text, user) #  voice_file = sing2(text)
  #voice_file = "speech.wav"

  #beat_file = "beats/#{Dir.new('beats').map { |x| x }[2..-1].sample}"
  #`sox #{beat_file} -c 2 beat.wav`
  
  beat_file = "beats/main_88.wav"
  
  mix_file = mix(voice_file, beat_file)
  track_url = upload(text, mix_file)
  tweet!("#TweetsOnBeats @#{user} yo dig this:", track_url)
rescue e
  puts "FAIL"
  p e
end

def sing(tweet, user)
  #file = "speech.aiff"
  #`say -v Fred ". . . . . . . . . . . #{tweet.gsub('"', '\"')}" -o #{file}`
  file = `python ../python/getvox.py "#{tweet.gsub('"', '\"')}" #{user}`
  `sox #{file} -c 2 speech.wav rate 44100`
  "speech.wav"
  
end

def mix(voice_file, beat_file)
  #mix_file = "mix.wav"
  #`sox -m #{voice_file} #{beat_file} #{mix_file}`
  #mix_file
  `./mixdown.rb #{voice_file} #{beat_file}`
  "TweetBeat.wav"
end

def upload(title, file)
  p 'authing'
  client = soundcloud_client
  
  p 'uploading'
  track = client.post("/tracks", :track => {
    :title => title,
    :asset_data => File.new(file),
    :license => "no-rights-reserved",
    :type => 'other',
    :tag_list => "tweetsonbeats",
    :downloadable => true,
    :genre => "TweetBeat",
    :purchase_url => "http://tweetsonbeats.com",
    :description => "a <a href='http://tweetsonbeats.com'>TweetsOnBeats.com</a> production."
  })

  p 'done'
  
  track.track.permalink_url
end

def tweet!(text, link)
  puts "Tweet #{text} #{link}"
  Twitter::Client.new.update("#{text} #{link}")
end

def soundcloud_client
  return @client if @client
  @client = Soundcloud.new({
    :client_id => "vr3PzfPLrjJ9ngajKYnLIw",
    :client_secret => "zxHGUHgl4noSTG9zPTTsNgC6ZCiBCuX9lym1pHx4",
    :username => "tweetsonbeats",
    :password => "test"
  })
end


def sing2(text)
  #HTTParty.get("http://cache-a.oddcast.com/c_fs/.mp3", {
  #  :text => 'dont fuck with me',
  #  :voice => 12,
  #  :language => 1,
  #  :engine => 6,
  #  :songId => 2
  #})
  text = URI.escape(text)
  url = HTTParty.get("http://cache-a.oddcast.com/c_fs/.mp3?text=#{text}&voice=12&language=1&engine=6&songId=2")["oddcastReply"]["location"]
  `wget "#{url}" -O voice.mp3 2> /dev/null`
  
  `sox voice.mp3 -c 2 speech.wav rate 44100`
  
  "speech.wav"
end

track = "#beatify"
TweetStream::Client.new(TWITTER_USER, TWITTER_PASS).filter(:track => track) { |s|  handle_tweet(s.user.screen_name, s.text.gsub(track, "")) }
#handle_tweet("johanneswagener", "super duper mega awesome cool")