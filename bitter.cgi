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
   print form
   print form.getfirst("login-btn", "")

siteVariables = {
   'your_name' : 'Desmond',
   'your_age' : 6,
   'athlete_list' : ['john', 'jay', 'smith']
}


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
elif all_search or user_search:
   if checkSession():
      page = "search"
   else:
      headers = "Location: ?page=home" #if logged in redirect to feed
      page = "home"
elif page == "logout":
   doLogout()
   headers = "Location: ?page=home"
   page = "home"
elif page == "home":
   if checkSession():
      headers = "Location: ?page=feed" #if logged in redirect to feed
      page = "feed"
elif page == "feed":
   if not checkSession():
      headers = "Location: ?page=home" #if logged in redirect to feed
      page = "home"
else:
   page = "error"

def matchingUsers(searchString, matches):
   searchString = "%"+searchString+"%"
   selectString = "SELECT full_name, description, username, profile_pic, bg_pic FROM users WHERE lower(username) LIKE (?) LIMIT (?)"
   db_conn.execute(selectString, (searchString, str(matches)))
   siteVariables['matchedUsers'] = []
   for row in db_conn:
      curRow = {}
      for key in row.keys():
         curRow[key] = row[key]
      siteVariables['matchedUsers'].append(curRow)

#print "hello"
# load page variables
#page = "feed"
#username = "DaisyFuentes"
if page == "feed" or page == "search":
   # populate user's feed
   if page == "feed":
      listeners = (username, )
      selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE bleats.username=?"
      # get listeners
      db_conn.execute('SELECT * FROM listeners WHERE username=?', (username, ))
      for row in db_conn:
         selectString += " OR bleats.username=?"
         listeners = (str(row['listens']), ) + listeners
      selectString += " ORDER BY bleats.time DESC"
      db_conn.execute(selectString, listeners)
   # populate search results
   elif page == "search":
      searchString = form.getfirst("search-txt", "")
      siteVariables['searchString'] = searchString
      searchString = searchString.lower().strip()
      if user_search == "submit":
         numMatchingUsers = 10 #TODO / TBD
         matchingUsers(searchString, numMatchingUsers)
         page = "user_search"
      else:
         numMatchingUsers = 2
         matchingUsers(searchString, numMatchingUsers)
         # tweet search results
         selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE lower(bleat) LIKE (?)"
         searchString = "%"+searchString+"%"
         selectString += " ORDER BY bleats.time DESC"
         db_conn.execute(selectString, (searchString, ))
      # user search results
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
   # get user data
   db_conn.execute('SELECT * FROM users WHERE username=?', (username, ))
   result = db_conn.fetchone()
   siteVariables['myDetails'] = {}
   if result:
      siteVariables['myDetails']['full_name'] = result['full_name']
      siteVariables['myDetails']['username'] = result['username']
      siteVariables['myDetails']['avatar'] = result['profile_pic']
      if result['description']:
         siteVariables['myDetails']['description'] = result['description']
      else:
         siteVariables['myDetails']['description'] = "You don't have a description :("
   db_conn.execute('SELECT COUNT(*) FROM bleats WHERE username=?', (username, ))
   siteVariables['myDetails']['bleats'] = db_conn.fetchone()[0]
   db_conn.execute('SELECT COUNT(*) FROM listeners WHERE username=?', (username, ))
   siteVariables['myDetails']['following'] = db_conn.fetchone()[0]
   db_conn.execute('SELECT COUNT(*) FROM listeners WHERE listens=?', (username, ))
   siteVariables['myDetails']['followers'] = db_conn.fetchone()[0]


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
