#!/usr/bin/env python

#||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# Author: Shane 'SajeOne' Brown
# Date: 13/03/2016
# Revision 3: Allowed mp3tags to exist in local dir or /usr/bin
# Description: Syncs a youtube playlist with a local folder
#||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||

import json
from pprint import pprint
import urllib.request as REQ
import urllib.error
import subprocess as sp
import os
from os.path import isfile, join, expanduser
import sys
import argparse
import re
import string

# Get Directory of config.json
def getConfigDir():
    xdgConfig = str(os.getenv('XDG_CONFIG_HOME'))

    if not xdgConfig:
        if verbose:
            print("Warning: XDG_CONFIG_HOME not defined, attempting config read from local directory")

        xdgConfig = os.path.dirname(os.path.realpath(__file__))

    if not os.path.exists(xdgConfig + "/youtubeSync"):
        try:
            os.makedirs(xdgConfig + "/youtubeSync")
        except OSError:
            print("Could not write to CONFIG directory. Not owned by you?")
            return False


    xdgConfig += "/youtubeSync"
    return xdgConfig

# Load the config file into memory
def loadConfigFile(path):
    try:
        with open(path + "/config.json", "r") as configFile:
            data = configFile.read()
            jsonObj = json.loads(data)
            return jsonObj
    except (FileNotFoundError, IOError) as e:
        return False

# Write default config in the case one doesn't exist
def writeDefaultConfig():
    xdgConfig = getConfigDir() 

    musicDir = expanduser("~") + "/Music"

    configList = {'playlistID': 'PUT_PLAYLIST_ID_HERE', 'googleAPIKey': 'PUT_KEY_HERE', 'destination': musicDir}

    jsonSaveFile = json.dumps(configList, indent=4)
    with open(xdgConfig + "/config.json", "w") as configFile:
        print(jsonSaveFile, file=configFile)

    print("Created default config at " + xdgConfig)

# Download youtube video at URL specified and convert to mp3 in path folder
def downloadVideo(url, path):
    proc = sp.Popen(['youtube-dl', '--extract-audio', '--audio-format', 'mp3', '--output', path + "/%(title)s.%(ext)s", url], stdout=sp.PIPE)
    result = proc.communicate()[0]
    status = proc.returncode
    

    if status == 0:
        return True

    return False

# Download Google API Json for playlist
def downloadPage(url):
    try:
        response = REQ.urlopen(url)
        data = response.read()
    except urllib.error.HTTPError as e:
        data = e.read()

    text = data.decode('utf-8')
    return text


# Decode the JSON to python DICT
def decodeJson(encodedJson):
    data = json.loads(encodedJson)
    return data

# convert list to form without any special characters or whitespace
def convertListFileSystemNeutral(convList):
    for index, value in enumerate(convList):
        convList[index] = re.sub('[^a-zA-Z\d]+', '', os.path.splitext(convList[index])[0])

    return convList


# convert string to form without any special characters or whitespace
def convertStringFileSystemNeutral(song):
    song = re.sub('[^a-zA-Z\d]+', '', os.path.splitext(song)[0])
    return song

def getListDiff(list1, list2):
    tempList = []
    for item1 in list1: 
        item1Trunc = os.path.splitext(item1)[0]
        item1Trunc = convertStringFileSystemNeutral(item1Trunc)
        for item2 in list2: 
            item2 = convertStringFileSystemNeutral(item2)
            if item1Trunc == item2:
                tempList.append(item1)
    
    return list(set(list1) - set(tempList))

# Get list of songs from directory
def getSongList(path):
    songs = [f for f in os.listdir(path) if isfile(join(path, f))]
    return songs

# Handle json errors from Google API response
def errorHandleJson(jsonResp):
    reason = None
    if "error" in jsonResp:
        reason = jsonResp['error']['errors'][0]['reason']
        if reason == "keyInvalid":
            reason = "Invalid API Key"
        elif reason == "playlistNotFound":
            reason = "Could not find YouTube playlist"

    return reason

# Parse program arguments 
def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--id3tag', help="Automatically sets up ID3 tags based on '-' delimiter. Requires optional dependency 'python-mutagen'", action="store_true")
    parser.add_argument('-v', '--verbose', help="Includes skipped songs(Already downloaded and in active playlist)", action="store_true")
    parser.add_argument('-s', '--simulate', help="Simulates without actually downloading, good for speed testing", action="store_true")
    args = parser.parse_args()
    return args

# BEGIN EXECUTION

## Handle Arguments
args = parseArguments()

tagFiles = False
verbose = False
simulate = False

if args.id3tag:
   tagFiles = True

if args.verbose:
    verbose = True

if args.simulate:
    simulate = True


## Handle Configuration
xdgConfig = getConfigDir()

if not xdgConfig:
    sys.exit(1)

config = loadConfigFile(xdgConfig)

if not config:
    writeDefaultConfig()
    print("No config, wrote default. Ensure to edit appropriately")
    sys.exit(1)

url = "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId=" + config['playlistID'] + "&key=" + config['googleAPIKey'] + "&maxResults=50"


## Download page and decode data
page = downloadPage(url)

try:
    jsonData = decodeJson(page)
except json.decoder.JSONDecodeError:
    print("Error: Could not decode JSON response, ensure config.json is setup properly")
    sys.exit(1)

response = errorHandleJson(jsonData)
if response is not None:
    print("Error: " + response)
    sys.exit(1)

songs = getSongList(config['destination'])
neutralSongs = convertListFileSystemNeutral(songs)

curSongList = []

## Loop through items and compare repos
for items in jsonData['items']:
    curSongList.append(items['snippet']['title'])

    neutralSnippet = convertStringFileSystemNeutral(items['snippet']['title'])
    if not neutralSnippet in neutralSongs:
        print("Downloading " + items['snippet']['title'] + "..")
        if not simulate and not downloadVideo("https://youtube.com/watch?v=" + items['snippet']['resourceId']['videoId'], config['destination']):
            print("\n--DOWNLOAD FAILED--\n")
    else:
        if verbose:
            print("SKIPPING " + items['snippet']['title'])


## Delete songs removed from remote
songs = getSongList(config['destination'])

songsForDeletion = getListDiff(songs, curSongList)

for item in songsForDeletion:
    try:
        os.remove(config['destination'] + "/" + item)
        print("Removed " + item)
    except FileNotFoundError:
        print("Could not remove " + item)

## If -t flag add ID3 tags to files
if tagFiles: 
    if os.path.isfile("/usr/bin/mp3tags"):
        proc = sp.Popen(['mp3tags', '-p', config['destination']], stdout=sp.PIPE, stderr=sp.PIPE)
    elif os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + "/mp3tags.py"):
        proc = sp.Popen(['python', 'mp3tags.py', '-p', config['destination']], stdout=sp.PIPE, stderr=sp.PIPE)
    else:
        print("Could not find mp3tags in /usr/bin or mp3tags.py in youtube-sync directory. Aborting tagging..")
        sys.exit(1)
    result = proc.communicate()[1]

    result = str(result).replace('\\n', '\n').replace("\\\'", '\'')

    if not proc.returncode:
        print("ID3 Tagged Files")
    else:
        print("\nFailed to tag files\n" + result)
