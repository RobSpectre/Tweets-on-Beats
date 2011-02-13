#!/usr/bin/env ruby
require 'soundcloud'
require 'httparty'
require 'twitter'
require 'tweetstream'
OA_KEY= "kc6ehamapugja8gy5zbzmjqwbuarkepd"
TWITTER_USER = "twonbe"
TWITTER_PASS = "foobar"
TW_CT = "bzdPlHk429kKb3ZsUfhQw"
TW_CS = "25hF3WTQ6h9njyqgS2V9a0jQ2MBkePdBwBshA5IajlY"
TW_AT = "251275058-4xfy2Bw1MR6fW1KHdz61px1NzPO7ao5i8E46U0NR"
TW_AS = "6O2kYW5osJMXDfvlxu3Bj9nZcSctxNrpNMxAq8HhcbI"


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
  p 1
  voice_file = sing(text)
#  voice_file = sing2(text)
p 2
  beat_file = "beat3.wav"
  
  mix_file = mix(voice_file, beat_file)
p 3
  track_url = upload(text, mix_file)
p 4
  tweet!("@#{user} checkout out your beatified tweet", track_url)
p 5
end

def sing(tweet)
  file = "speech.aiff"
  `say ". . . . . . . . . . . #{tweet.gsub('"', '\"')}" -o #{file}`
  `sox #{file} speech.wav rate 44100`
  "speech.wav"
end

def mix(voice_file, beat_file)
  mix_file = "mix.wav"
  `sox -m #{voice_file} #{beat_file} #{mix_file}`
  mix_file
end

def upload(title, file)
  p track = soundcloud_client.post("/tracks", :track => {
    :title => title,
    :asset_data => File.new(file)
  })
  
  track.track.permalink_url
end

def tweet!(text, link)
  puts "Tweet #{text} #{link}"
  Twitter::Client.new.update("#{text} #{link}")
end

def soundcloud_client
  #return @client if @client
  @client = Soundcloud.new({
    :client_id => "vr3PzfPLrjJ9ngajKYnLIw",
    :client_secret => "zxHGUHgl4noSTG9zPTTsNgC6ZCiBCuX9lym1pHx4",
    :username => "tweets-on-beats",
    :password => "test"
  })
  p @client
  
  
  p @client
#  @client
  
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

track = "#twonbe"
TweetStream::Client.new(TWITTER_USER, TWITTER_PASS).filter(:track => track) { |s|  handle_tweet(s.user.screen_name, s.text.gsub(track, "")) }
#handle_tweet("johanneswagener", "super duper mega awesome cool")