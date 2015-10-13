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
from demplate import *

DB_NAME = "bitter.db"

# get params
form = cgi.FieldStorage()

# connect to database
conn = sqlite3.connect(DB_NAME);
db_conn = conn.cursor()

# set homepage param
try:
   page = form["page"].value
except KeyError:
   page = "home"

# setup variables for parsing
siteVariables = {
   'your_name' : 'Desmond',
   'your_age' : 6,
   'athlete_list' : ['john', 'jay', 'smith']
}

# process relevant page (#TODO if statement this so we don't have massive XSS risks)
filename = page+".html"
site = open(filename, "r").read()
parser = ParseSite(site)
completeSite = parser.processTokens() #returns a SiteNodes group

# show page
print "Content-Type: text/html;charset=utf-8"
print

print completeSite.convert(siteVariables)

login = form.getfirst("login-btn", "").lower()
if (login):
   print "dologin"
   username = form.getfirst("username", "").lower()
   password = form.getfirst("password", "")
   password = hashlib.md5(password).hexdigest()

   db_conn.execute('SELECT * FROM users WHERE lower(username)=? AND password=?', (username, password))
   result = db_conn.fetchone()
   if result:
      page = "feed"
      doLogin(username)

def doLogin(username):
   print "magic to come"


