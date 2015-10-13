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

# get params
form = cgi.FieldStorage()

# setup globals (TODO we'll see if this is necessary)
username = ""
password = ""
page = "home"
headers = {}
cookies = SimpleCookie()
sid = ""
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
   username = form.getfirst("username", "").lower()
   password = form.getfirst("password", "")
   password = hashlib.md5(password).hexdigest()

   db_conn.execute('SELECT * FROM users WHERE lower(username)=? AND password=?', (username, password))
   conn.commit()
   result = db_conn.fetchone()
   if result:
      createSession(username)

def createSession(username):
   page = "feed"   #open user's feed on login
   sid = generateHash()
   cookies['sid'] = sid
   db_conn.execute("INSERT INTO sessions VALUES (?, ?)", (username, sid));
   conn.commit()

def generateHash():
   hashString = username + password + MAGIC_STRING + str(time.time())
   hashedString = hashlib.sha256(hashString).hexdigest()
   return hashedString

def showHeaders(headers={}):
   if (len(headers.items()) == 0):
      headers['Content-type'] = 'text/html'
   for envVar, var in headers.items():
      print "%s: %s" % (envVar, var)
      print cookies.output()
      print

def checkSession():
   global page
   global username
   # check for magic cookie
   # http://webpython.codepoint.net/cgi_retrieve_the_cookie
   cookieString = os.environ.get('HTTP_COOKIE')
   cookies.load(cookieString)
   sid = cookies['sid'].value
   # check if session exists
   db_conn.execute('SELECT * FROM sessions WHERE sid=?', (sid, ))
   conn.commit()
   result = db_conn.fetchone()
   if result:
      page = "feed"
      username = result["username"]

login = form.getfirst("login-btn", "")
if (login):
   doLogin()
else:
   checkSession()


# process relevant page (#TODO if statement this so we don't have massive XSS risks)
filename = page+".html"
site = open(filename, "r").read()
parser = ParseSite(site)
completeSite = parser.processTokens() #returns a SiteNodes group

# show page
showHeaders(headers)
print completeSite.convert(siteVariables)

print username
