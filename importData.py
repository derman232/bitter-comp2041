#!/usr/bin/python

#script to setup tables and import all data
#to be run on an empty database (undefined activity on non-empty database)
#Derek Peczek

#TODO confirm all profile pics are actually JPGs!!

import glob
import sqlite3
import re
import hashlib

USER_DIR    = "/import/adams/2/z3459551/public_html/bitter/dataset-small/users/"
BLEAT_DIR   = "/import/adams/2/z3459551/public_html/bitter/dataset-small/bleats/"
DEFAULT_PIC = "https://www.gravatar.com/avatar/d489b737cd6a6074c634ebfbb2a39396.jpg"
PROFILE_DIR = "http://www.cse.unsw.edu.au/~cs2041/15s2/assignments/bitter/dataset-small/users/"

def createTables():
   c.execute('''CREATE TABLE users (
   email           TEXT,
   full_name       TEXT,
   password        TEXT,
   username        TEXT PRIMARY KEY,
   home_latitude   REAL,
   home_suburb     TEXT,
   profile_pic     TEXT,
   home_longitude  REAL )''')
   c.execute('''CREATE TABLE listeners (
   username        TEXT,
   listens         TEXT )''')
   c.execute('''CREATE TABLE bleats (
   bleat_id        TEXT PRIMARY KEY,
   in_reply_to     TEXT,
   username        TEXT,
   longitude       REAL,
   latitude        REAL,
   time            INT ,
   bleat           TEXT )''')
   c.execute('''CREATE TABLE sessions (
   username        TEXT,
   sid             TEXT )''')



conn = sqlite3.connect('bitter.db');
c = conn.cursor()

createTables()

userDict = {
   'listens'         : '',
   'email'           : '',
   'full_name'       : '',
   'password'        : '',
   'username'        : '',
   'home_latitude'   : '',
   'home_suburb'     : '',
   'home_longitude'  : ''
}
bleatDict = {
   'in_reply_to'     : '',
   'username'        : '',
   'longitude'       : '',
   'latitude'        : '',
   'time'            : '',
   'bleat'           : ''
}

for bleatsFile in glob.glob(BLEAT_DIR+"*"):
   userSearch = r"" + re.escape(BLEAT_DIR) + "(.*)"
   bleat_id   = re.match(userSearch, bleatsFile).group(1)

   for line in open(bleatsFile):
      line = line.strip()
      details = line.split(':', 1)
      details[0] = details[0].strip()
      details[1] = details[1].strip()
      bleatDict[details[0]] = details[1]
   values = (
      bleat_id                ,
      bleatDict['in_reply_to'],
      bleatDict['username']   ,
      bleatDict['longitude']  ,
      bleatDict['latitude']   ,
      bleatDict['time']       ,
      bleatDict['bleat']      
   )
   c.execute("INSERT INTO bleats VALUES (?, ?, ?, ?, ?, ?, ?)", values);
   bleatDict = bleatDict.fromkeys(bleatDict, '')



for a in glob.glob(USER_DIR+"*"):
   userFile = a + "/details.txt"
   profile_pic = a + "/profile.jpg"

   # check if profile pic exists
   try:
      with open(profile_pic) as file:
         pass
   except IOError as e:
      profile_pic = DEFAULT_PIC

   userSearch = r"" + re.escape(USER_DIR) + "(.*)"
   userDict['username'] = re.match(userSearch, a).group(1)
   if profile_pic != DEFAULT_PIC:
      profile_pic = PROFILE_DIR + userDict['username'] + "/profile.jpg"

   for line in open(userFile):
      line = line.strip()
      details = line.split(':', 1)
      details[0] = details[0].strip()
      details[1] = details[1].strip()
      userDict[details[0]] = details[1]
   userDict['password'] = hashlib.md5(userDict['password']).hexdigest() #hash password
   values = (
      userDict['email']         ,
      userDict['full_name']     ,
      userDict['password']      ,
      userDict['username']      ,
      userDict['home_latitude'] ,
      userDict['home_suburb']   ,
      profile_pic               ,
      userDict['home_longitude']
   )
   c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", values)

   for line in userDict['listens'].split():
      values = (
         userDict['username'],
         line
      )
      c.execute("INSERT INTO listeners VALUES (?, ?)", values)
   userDict = userDict.fromkeys(userDict, '')

conn.commit()
conn.close()
