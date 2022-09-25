#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  1 23:43:59 2018

@author: speppou

Script to automatically add videos from a reddit page. 
The script scans the top videos in 24 hours, extract the YT video URLs and 
adds them to the playlist, if they aren't already there. 
It keeps the playlist at maximum number of videos

"""

import urllib.request 
import urllib.parse
import os

import google.oauth2.credentials

import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import httplib2
import sys

from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

PL_ids = [  # these playlists must belong to the authenticated user
  'PLRg7KDv3GZUTX7kKaNhnmpPNBrIunNO64',
  'PLRg7KDv3GZUSSSBpvFIfUrNk-yQ_SMucK',
  ]
reddit_URLs = [
  'https://old.reddit.com/r/videos/top/?sort=top&t=day',
  'https://old.reddit.com/r/mealtimevideos/top/?sort=top&t=day',
  ]

API_KEY = '' # insert your API key here

maxVids = 100

def main(reddit_URL, PL_id, maxVids):
      #get the reddit page data
    page = get_webpage(reddit_URL)
    URLs = extract_URLs(page)
    
    # When running locally, disable OAuthlib's HTTPs verification. When
    # running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    client = get_authenticated_service()
 
    
    playlistItems = playlist_items_list_by_playlist_id(
      client,
      part = 'snippet',
      maxResults = 5,
      playlistId = PL_id
      )
    
    # find videos already in playlist
    vidInPL = [
      playlistItems['items'][i]['snippet']['resourceId']['videoId'] 
      for i in range(len(playlistItems['items'])) 
      ]
    
    # check to see if any videos are already in the playlist and remove them 
    # from list
    URLs = set(URLs).difference(vidInPL)
    
    # add videos to playlist
    for i, URL in enumerate(URLs):
        playlist_items_insert(
          client, 
        {
         'snippet.playlistId': PL_id,
         'snippet.resourceId.kind': 'youtube#video',
         'snippet.resourceId.videoId': URL,
         'snippet.position': '',
         },
        part='snippet',
        onBehalfOfContentOwner='',
        key=API_KEY
        )    
        
    #print('Added ' + str(len(URLs)) + ' videos to playlist')
    
    # update list of videos
    playlistItems = playlist_items_list_by_playlist_id(
      client,
      part = 'snippet',
      maxResults = 5,
      playlistId = PL_id
      )
    
    vidInPL = [
      playlistItems['items'][i]['id'] 
      for i in range(len(playlistItems['items'])) 
      ]
    
    # delete videos if there is more than 100
    if playlistItems['pageInfo']['totalResults'] > maxVids:
      for URL in vidInPL[-(len(vidInPL) - maxVids):]:
        playlist_items_delete(client, id=URL)
                
        
#### OAuth2 stuff ####        

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account.
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = "m1zzing"

os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

# Authorize the request and store authorization credentials.
def get_authenticated_service():
  flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=YOUTUBE_READ_WRITE_SCOPE,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("%s-oauth2.json" % sys.argv[0])
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage)

  return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))

def print_response(response):
  print(response)

# Build a resource based on a list of properties given as key-value pairs.
# Leave properties with empty values out of the inserted resource.
def build_resource(properties):
  resource = {}
  for p in properties:
    # Given a key like "snippet.title", split into "snippet" and "title", where
    # "snippet" will be an object and "title" will be a property in that object.
    prop_array = p.split('.')
    ref = resource
    for pa in range(0, len(prop_array)):
      is_array = False
      key = prop_array[pa]

      # For properties that have array values, convert a name like
      # "snippet.tags[]" to snippet.tags, and set a flag to handle
      # the value as an array.
      if key[-2:] == '[]':
        key = key[0:len(key)-2:]
        is_array = True

      if pa == (len(prop_array) - 1):
        # Leave properties without values out of inserted resource.
        if properties[p]:
          if is_array:
            ref[key] = properties[p].split(',')
          else:
            ref[key] = properties[p]
      elif key not in ref:
        # For example, the property is "snippet.title", but the resource does
        # not yet have a "snippet" object. Create the snippet object here.
        # Setting "ref = ref[key]" means that in the next time through the
        # "for pa in range ..." loop, we will be setting a property in the
        # resource's "snippet" object.
        ref[key] = {}
        ref = ref[key]
      else:
        # For example, the property is "snippet.description", and the resource
        # already has a "snippet" object.
        ref = ref[key]
  return resource

# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):
  good_kwargs = {}
  if kwargs is not None:
    for key, value in kwargs.items():
      if value:
        good_kwargs[key] = value
  return good_kwargs

def playlist_items_list_by_playlist_id(client, **kwargs):
  kwargs = remove_empty_kwargs(**kwargs)
  
  res = client.playlistItems().list(
    **kwargs
    ).execute()

  nextPageToken = res.get('nextPageToken')
  while ('nextPageToken' in res):
     nextPage = client.playlistItems().list(
        **kwargs, pageToken=nextPageToken
        ).execute()
     res['items'] = res['items'] + nextPage['items']
     

     if 'nextPageToken' not in nextPage:
            res.pop('nextPageToken', None)
     else:
            nextPageToken = nextPage['nextPageToken']

  return res

def playlist_items_insert(client, properties, **kwargs):
  resource = build_resource(properties)

  # See full sample for function
  kwargs = remove_empty_kwargs(**kwargs)

  response = client.playlistItems().insert(
    body=resource,
    **kwargs
  ).execute()

  return response
  
def playlist_items_delete(client, **kwargs):
  # See full sample for function
  kwargs = remove_empty_kwargs(**kwargs)

  response = client.playlistItems().delete(
    **kwargs
  ).execute()

  return(response)  

#### Script specific functions ####

def get_webpage(url):
    user_agent = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.3 (KHTML, like Gecko) Chrome/6.0.472.63 Safari/534.3'
    headers = { 'User-Agent' : user_agent }
    values = {'name' : 'foo',
              'location' : 'Boston',
              'language' : 'Python' }
    data = urllib.parse.urlencode(values).encode("utf-8")
    req = urllib.request.Request(url, data, headers)
    response =  urllib.request.urlopen(req)
    page = response.read()
    response.close() # its always safe to close an open connection
    
    return page.decode()  
    
def extract_URLs(page):
  URLs = []
  startIndex = 0
  for i in range(page.count('youtube.com/watch?v=')):
      #find next url
      index = page.find('youtube.com/watch?v=', startIndex)
      URLs.append(page[index + 20 : index + 31])
      startIndex = index + 30  
      
  return URLs


if __name__ == '__main__':
  
  for reddit_URL, PL_id in zip(reddit_URLs, PL_ids):
    main(
      reddit_URL = reddit_URL,
      PL_id = PL_id,
      maxVids = maxVids,
      )
  
              
            
            
