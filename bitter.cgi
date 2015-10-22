#!/usr/bin/python

# enable debugging
import cgitb
cgitb.enable()

import urlparse
import hashlib
import os
import cgi
import sys
import sqlite3
import time
from Cookie import SimpleCookie
from demplate import *
from collections import defaultdict

DB_NAME = "bitter.db"
MAGIC_STRING = "sjdkfls243u892rjf" # for hashes
DEBUG = False
DEBUG_HEADERS = False

# get params
form = cgi.FieldStorage()

# setup globals (TODO we'll see if this is necessary)
username = ""
password = ""
page = "home"
headers = "Content-Type: text/html"
login = ""
cookies = SimpleCookie()
sid = ""

if DEBUG_HEADERS:
   print headers
   print

siteVariables = {}


# connect to database
conn = sqlite3.connect(DB_NAME);
conn.row_factory = sqlite3.Row
db_conn = conn.cursor()

# set homepage param
try:
   page = form["page"].value
except KeyError:
   page = "home"


# session creation adapted from 
# http://code.activestate.com/recipes/325484-a-very-simple-session-handling-example/
def doLogin():
   global page
   global headers
   global username
   username = form.getfirst("username", "").lower()
   password = form.getfirst("password", "")
   if DEBUG == True: username = "daisyfuentes"
   if DEBUG == True: password = "giants"
   password = hashlib.md5(password).hexdigest()

   db_conn.execute('SELECT * FROM users WHERE lower(username)=? AND password=?', (username, password))
   conn.commit()
   result = db_conn.fetchone()
   if result:
      #page = "feed"
      headers = "Location: ?page=feed"
      username = result["username"]
      createSession(username)

def createSession(username):
   global page
   page = "feed"   #open user's feed on login
   sid = generateHash()
   cookies['sid'] = sid
   db_conn.execute("INSERT INTO sessions VALUES (?, ?)", (username, sid));
   conn.commit()

def generateHash():
   hashString = username + password + MAGIC_STRING + str(time.time())
   hashedString = hashlib.sha256(hashString).hexdigest()
   return hashedString

#def showHeaders(headers={}):
#   if (len(headers.items()) == 0):
#      headers['Content-type'] = 'text/html'
#   for envVar, var in headers.items():
#      print "%s: %s" % (envVar, var)
#      print cookies.output()
#      print

def checkSession():
   global username
   # check for magic cookie
   # http://webpython.codepoint.net/cgi_retrieve_the_cookie
   cookieString = os.environ.get('HTTP_COOKIE')
   if not cookieString:
      return False
   cookies.load(cookieString)
   try:
      sid = cookies['sid'].value
   except:
      return False
   # check if session exists
   db_conn.execute('SELECT * FROM sessions WHERE sid=?', (sid, ))
   conn.commit()
   result = db_conn.fetchone()
   if result:
      username = result["username"]
      return True
   return False

def doLogout():
   global headers
   if checkSession():
      sid = cookies['sid'].value
      sid = cookies['sid']['expires'] = -10
      db_conn.execute('DELETE FROM sessions WHERE sid=?', (sid, ))
      conn.commit()

def convertTime(targetTime):
   convertedTime = time.strftime('%m/%d/%Y %H:%M:%S',  time.gmtime(targetTime))
   return convertedTime

login = form.getfirst("login-btn", "")
if DEBUG == True: login = "yes"
all_search = form.getfirst("main-search", "")
user_search = form.getfirst("user-search", "")

if login:
   doLogin()
   page = "feed"
elif all_search or (user_search and page == "user_search"):
   if checkSession():
      if all_search:
         page = "search"
   else:
      headers = "Location: ?page=home" #if not logged in, take home
      page = "home"
elif page == "logout":
   doLogout()
   headers = "Location: ?page=home"
   page = "home"
elif page == "home":
   if checkSession():
      headers = "Location: ?page=feed" #if logged in redirect to feed
      page = "feed"
elif page == "feed" or page == "settings":
   if not checkSession():
      headers = "Location: ?page=home" #if logged in redirect to feed
      page = "home"
elif page == "user_page":
   page = "user_page"
else:
   page = "error"

def matchingUsers(searchString, matches):
   selectString = "SELECT full_name, description, username, profile_pic, bg_pic FROM users WHERE lower(username) LIKE (?) LIMIT (?)"
   db_conn.execute(selectString, (searchString, str(matches)))
   siteVariables['matchedUsers'] = []
   for row in db_conn:
      curRow = {}
      for key in row.keys():
         curRow[key] = row[key]
      siteVariables['matchedUsers'].append(curRow)


# get details for target username
def myDetails(username):
   global siteVariables
   db_conn.execute('SELECT * FROM users WHERE username=?', (username, ))
   result = db_conn.fetchone()
   siteVariables['myDetails'] = {}
   if result:
      for key in result.keys():
         if key == "profile_pic":
            siteVariables['myDetails']['avatar'] = result[key]
         else:
            siteVariables['myDetails'][key] = result[key]
      if result['description']:
         siteVariables['myDetails']['description'] = result['description']
         siteVariables['myDetails']['view_description'] = result['description']
      else:
         siteVariables['myDetails']['description'] = ""
         siteVariables['myDetails']['view_description'] = "You don't have a description :("
   db_conn.execute('SELECT COUNT(*) FROM bleats WHERE username=?', (username, ))
   siteVariables['myDetails']['bleats'] = db_conn.fetchone()[0]
   db_conn.execute('SELECT COUNT(*) FROM listeners WHERE username=?', (username, ))
   siteVariables['myDetails']['following'] = db_conn.fetchone()[0]
   db_conn.execute('SELECT COUNT(*) FROM listeners WHERE listens=?', (username, ))
   siteVariables['myDetails']['followers'] = db_conn.fetchone()[0]

# populate logged in user's feed
def getFeed():
   global siteVariables
   global username

   listeners = (username, )
   selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE bleats.username=?"
   # get listeners
   db_conn.execute('SELECT * FROM listeners WHERE username=?', (username, ))
   for row in db_conn:
      selectString += " OR bleats.username=?"
      listeners = (str(row['listens']), ) + listeners
   selectString += " ORDER BY bleats.time DESC"
   db_conn.execute(selectString, listeners)
   # after retrieving, add these to the dictionary
   parseBleats()

def getUserBleats(username):
   global siteVariables

   selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE bleats.username=?"
   selectString += " ORDER BY bleats.time DESC"
   db_conn.execute(selectString, (username, ))
   # after retrieving, add these to the dictionary
   parseBleats()



def searchBleats(searchString):
   # tweet search results
   selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE lower(bleat) LIKE (?)"
   selectString += " ORDER BY bleats.time DESC"
   db_conn.execute(selectString, (searchString, ))
   # after retrieving, add these to the dictionary
   parseBleats()

def processSearchString():
   searchString = form.getfirst("search-txt", "")
   siteVariables['searchString'] = searchString
   searchString = searchString.lower().strip()
   searchString = "%"+searchString+"%"
   return searchString
  

def parseBleats():
   global siteVariables
   siteVariables['myFeed'] = []
   for row in db_conn:
      curRow = {}
      for key in row.keys():
         if key == "time":
            curRow[key] = convertTime(row[key])
         else:
            curRow[key] = row[key]
      siteVariables['myFeed'].append(curRow)
   conn.commit()

def validUser(username):
   db_conn.execute('SELECT * FROM users WHERE lower(username)=?', (username.lower().strip(), ))
   try:
      user = db_conn.fetchone()['username']
   except:
      user = None
   if user:
      return user
   return None
  

# handle page creation
# populate user's feed
if page == "feed" or page == "search" or page == "settings" or page == "user_page" or page == "user_search":
   if page == "feed":
      getFeed()
      myDetails(username)
   # populate search results
   elif page == "search":
      searchString = processSearchString()
      searchBleats(searchString)
      matchingUsers(searchString, 2)
      myDetails(username)
   elif page == "user_search":
      searchString = processSearchString()
      matchingUsers(searchString, 10)
      #public_user = form.getfirst("public_user", "")
      #selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE bleats.username=?"
      #selectString += " ORDER BY bleats.time DESC"
      #db_conn.execute(selectString, (public_user, ))
      myDetails(username)
   elif page == "user_page":
      targetUser = form.getfirst("user", "")
      targetUser = validUser(targetUser)
      if targetUser != None:
         myDetails(targetUser)
         getUserBleats(targetUser)
      else:
         headers = "Location: ?page=feed"



# process relevant page (#TODO if statement this so we don't have massive XSS risks)
filename = page+".html"
site = open(filename, "r").read()
parser = ParseSite(site)
completeSite = parser.processTokens() #returns a SiteNodes group

# show page
print headers
print cookies.output()
print
print completeSite.convert(siteVariables)
print page
print username
print sid

search = form.getfirst("main-search", "")
print search
search = form.getfirst("search-txt", "")
print search

print siteVariables
