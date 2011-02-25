#!/usr/bin/env ruby
require 'rubygems'
require 'soundcloud'

def upload(file, user, text)
  track = soundcloud_client.post("/tracks", :track => {
    :title        => "@#{user}: #{text}",
    :asset_data   => File.new(file),
    :license      => "no-rights-reserved",
    :type         => 'other',
    :tag_list     => "TweetsOnBeats",
    :downloadable => true,
    :genre        => "TweetBeat",
    :purchase_url => "http://tweetsonbeats.com",
    :video_url    => "http://www.youtube.com/watch?v=wed0gUDahnw",
    :description  => "written by <a href=\"http://twitter.com/#{user}\">@#{user}</a>. a <a href='http://tweetsonbeats.com'>TweetsOnBeats.com</a> production. "
  })
  track.permalink_url
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

file = ARGV.shift
user = ARGV.shift
text = ARGV.shift

puts upload(file, user, text)
