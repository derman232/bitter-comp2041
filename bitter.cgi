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
import re
from Cookie import SimpleCookie
from demplate import *
from collections import defaultdict

DB_NAME = "bitter.db"
MAGIC_STRING = "sjdkfls243u892rjf" # for hashes
MAX_FILE_SIZE = 1024*1024*2 # 2 megabytes in bytes
MAX_FILE_SIZE_STR = "2MB" # 2 megabytes in bytes
MAX_VID_SIZE = 1024*1024*15 # 15 mb videos
MAX_IMG_SIZE = 1024*1024*5  # 5  mb tweet attachments
MAX_DESC_LEN = 100
DEBUG = False
DEBUG_HEADERS = False
DEFAULT_PIC = "https://www.gravatar.com/avatar/d489b737cd6a6074c634ebfbb2a39396.jpg"
DEFAULT_BG  = "http://localhost/~derek/bitter/img/default-banner.jpeg"
VALID_MIME_IMAGES       = ["image/jpeg", "image/png"]
VALID_FILE_EXTS         = ["jpg", "jpeg", "png"]
VALID_MIME_IMAGES_TWTS  = ["image/jpeg", "image/png", "image/gif", "video/mp4"]
VALID_FILE_EXTS_TWTS    = ["jpg", "jpeg", "png", "bmp", "gif", "mp4"]
UPLOAD_DIR = "userimg/"
USER_MATCH = r'^@[a-zA-Z0-9_]{1,30}$'
KEYWORD_MATCH = r'^#[a-zA-Z0-9_]*$'

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
   db_conn.execute("INSERT INTO sessions VALUES (?, ?)", (username, sid))
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


def matchingUsers(searchString, matches):
   selectString = "SELECT full_name, description, username, profile_pic, bg_pic FROM users WHERE lower(username) LIKE (?) LIMIT (?)"
   db_conn.execute(selectString, (searchString, str(matches)))
   siteVariables['matchedUsers'] = []
   for row in db_conn:
      curRow = {}
      for key in row.keys():
         curRow[key] = row[key]
      curRow['following'] = isFollowing(row['username'])
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

      # if description is not empty, replace with dummy text
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
   selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE bleats.username=(?)"

   # get listeners
   db_conn.execute('SELECT * FROM listeners WHERE username=(?)', (username, ))
   for row in db_conn:
      selectString += " OR bleats.username=(?)"
      listeners = listeners + (str(row['listens']), )

   # get '@' tweets
   db_conn.execute('SELECT * FROM reply_to WHERE username=(?)', (username, ))
   for row in db_conn:
      selectString += " OR bleats.bleat_id=(?)"
      listeners = listeners + (str(row['bleat_id']), )

   # set order
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

def getSingleBleat(bleat_id):
   global siteVariables

   selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE bleats.bleat_id=(?)"
   db_conn.execute(selectString, (bleat_id, ))

   parseBleats(True)

# retrieve belats as specified by array
def getManyBleats(bleat_ids):
   selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE "
   for bleat in bleat_ids:
      selectString += "bleats.bleat_id=(?) OR "
   selectString = selectString[:-4]
   selectString += " ORDER BY bleats.time DESC"
   db_conn.execute(selectString, tuple(bleat_ids))
   parseBleats()

# recursively get all replies to a tweet
def getBleatReplies(bleat_id):
   bleatReplies = []
   while True:
      selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE bleats.bleat_id=(?)"
      db_conn.execute(selectString, (bleat_id, ))
      bleat_id = db_conn.fetchone()['in_reply_to']
      if not bleat_id:
         break
      bleatReplies.append(bleat_id)
   return bleatReplies

def searchBleats(searchString):
   # if hashtag search
   if re.match(KEYWORD_MATCH, searchString[1:-1]):
      searchString = "% "+searchString[1:-1]+" %"
      selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE (' ' || lower(bleat) || ' ') LIKE (?)"
      selectString += " ORDER BY bleats.time DESC"
   else:
      # tweet search results
      selectString = "SELECT * FROM bleats INNER JOIN users ON bleats.username=users.username WHERE lower(bleat) LIKE (?)"
      selectString += " ORDER BY bleats.time DESC"
   db_conn.execute(selectString, (searchString, ))
   # after retrieving, add these to the dictionary
   parseBleats()

def parseBleats(singleBleat=False):
   global siteVariables
   if singleBleat:
      siteVariables['featuredBleat'] = []
   else:
      siteVariables['myFeed'] = []
   for row in db_conn:
      curRow = {}
      for key in row.keys():
         if key == "time":
            curRow[key] = convertTime(row[key])
         elif key == "file_1":
            if row[key]:
               extension = row[key].rsplit('.', 1)[-1]
               if extension.lower() == "mp4":
                  curRow['media_type'] = "video"
               else:
                  curRow['media_type'] = "images"
            else:
               curRow['media_type'] = ""
            curRow[key] = row[key]
         elif key == "bleat":
            bleatTxt = row[key].split(' ')
            for n in xrange(len(bleatTxt)):
               if re.match(USER_MATCH, bleatTxt[n]):
                  bleatTxt[n] = '<a href="?page=user_page&user='+bleatTxt[n][1:]+'">'+bleatTxt[n]+'</a>'
               if re.match(KEYWORD_MATCH, bleatTxt[n]):
                  bleatTxt[n] = '<a href="?search-txt=%23'+bleatTxt[n][1:]+'&main-search=submit">'+bleatTxt[n]+'</a>'

            curRow[key] = ' '.join(bleatTxt)
         else:
            curRow[key] = row[key]
      if singleBleat:
         siteVariables['featuredBleat'].append(curRow)
      else:
         siteVariables['myFeed'].append(curRow)
   conn.commit()

def processSearchString():
   searchString = form.getfirst("search-txt", "")
   siteVariables['searchString'] = searchString
   searchString = searchString.lower().strip()
   searchString = "%"+searchString+"%"
   return searchString

def validBleat(bleat_id):
   db_conn.execute('SELECT * FROM bleats WHERE bleat_id=(?)', (bleat_id, ))
   try:
      bleat_id = db_conn.fetchone()['bleat_id']
   except:
      bleaet_id = None
   if bleat_id:
      return bleat_id
   return None

def bleatToUser(bleat_id):
   db_conn.execute('SELECT * FROM bleats WHERE bleat_id=(?)', (bleat_id, ))
   user = db_conn.fetchone()['username']
   return user



def validUser(username, caseSensitive=False):
   if caseSensitive:
      db_conn.execute('SELECT * FROM users WHERE username=(?)', (username.strip(), ))
   else:
      db_conn.execute('SELECT * FROM users WHERE lower(username)=(?)', (username.lower().strip(), ))
   try:
      user = db_conn.fetchone()['username']
   except:
      user = None
   if user:
      return user
   return None
  
def existingEmail(email):
   db_conn.execute('SELECT * FROM users WHERE lower(email)=?', (email.lower().strip(), ))
   try:
      email = db_conn.fetchone()['email']
   except:
      email = None
   if email:
      return email
   return None

def isNumber(n):
   try:
      float(n)
      return True
   except ValueError:
      return False

def validUsername(username):
   return bool(re.match(r'^[a-zA-Z0-9_]{1,30}$', username))

#at least one digit, one uppercase, one lowercase, and can contain special characters !@#$%_^&*
def validPassword(password):
   return bool(re.match(r'^(?=.*[\d])(?=.*[A-Z])(?=.*[a-z])[\w\d!@#$%_\^\&\*]{6,40}$', password))

def validEmail(email):
   # to avoid a philosphical debate on this stuff... 
   # http://stackoverflow.com/questions/201323/using-a-regular-expression-to-validate-an-email-address
   return bool(re.match(r'[^@]+@[^@]+\.[^@]+', email))


def getNewUserFormFields ():
   global siteVariables
   formFields = {
      'new_user' : form.getfirst("new_user", ""),
      'new_pass' : form.getfirst("new_pass", ""),
      'full_name' : form.getfirst("full_name", ""),
      'description' : form.getfirst("description", ""),
      'email' : form.getfirst("email", ""),
      'location' : form.getfirst("location", ""),
      'profile_pic' : form.getfirst("profile_pic", ""),
      'bg_pic' : form.getfirst("bg_pic", ""),
      'home_location' : form.getfirst("home_location", ""),
      'home_lat' : form.getfirst("home_lat", ""),
      'home_long' : form.getfirst("home_long", "")
   }
   try:
      formFields['profile_pic'] = form['profile_pic']
   except:
      pass
   try:
      formFields['bg_pic'] = form['bg_pic']
   except:
      pass

   siteVariables['formFields'] = formFields
   return formFields

def checkImage(curPic):
   errorMsg = ''
   valid = True
   try:
      if curPic.filename:
         # check if file is right type
         extension = curPic.filename.rsplit('.', 1)[-1]
         if curPic.type not in VALID_MIME_IMAGES:
            valid = False
            errorMsg = 'Enter a valid filetype. (.jpeg, .jpg, .png)'
         elif extension not in VALID_FILE_EXTS:
            valid = False
            errorMsg = 'Enter a valid filetype. (.jpeg, .jpg, .png)'
         return valid, errorMsg

         # check if file is too big
         fileSize = len(curPic.value)
         if fileSize > MAX_FILE_SIZE:
            valid = False
            errorMsg = 'Profile picture cannot be larger than '+MAX_FILE_SIZE_STR
            return valid, errorMsg
   except AttributeError:
      pass
   return valid, errorMsg

# validates new user form, and settings form
def processNewUserForm (formFields, settings=False, emptyErrors=False):
   global siteVariables
   valid = True
   errorMsgs = {
      'username' : '',
      'password' : '',
      'full_name' : '',
      'description' :'',
      'email' : '',
      'location' : '',
      'profile_pic' : '',
      'bg_pic' : '',
      'home_location' : ''
   }

   # if empty errors list required, return here
   if emptyErrors:
      siteVariables['errorMsgs'] = errorMsgs
      valid = False
      return valid
   new_user  = formFields['new_user']
   new_pass  = formFields['new_pass']
   full_name = formFields['full_name']
   email     = formFields['email']
   profile_pic = formFields['profile_pic']
   bg_pic = formFields['bg_pic']
   home_lat  = formFields['home_lat']
   home_long = formFields['home_long']
   description = formFields['description']

   # check that required fields are complete if not settings form
   if not settings:
      if not new_user:
         valid = False
         errorMsgs['username'] = 'Enter a username'
      if not new_pass:
         valid = False
         errorMsgs['password'] = 'Enter a password'
      if not full_name:
         valid = False
         errorMsgs['full_name'] = 'Enter your name'
      if not email:
         valid = False
         errorMsgs['email'] = 'Enter your email address'
   # check description length
   if len(description) > MAX_DESC_LEN:
      valid = False
      errorMsgs['description'] = 'Descriptions cannot be longer than 100 characters'
   # check if username is valid
   if not errorMsgs['username'] and not settings:
      if not validUsername(new_user):
         valid = False
         errorMsgs['username'] = 'Username must not be longer than 15 characters, and can only contain [A-Za-z0-9_]'
   # check if username is taken
   if not errorMsgs['username'] and not settings:
      if validUser(new_user):
         valid = False
         errorMsgs['username'] = 'This username is already taken. Please try another one'
   # check if password is valid
   if not errorMsgs['password'] and new_pass:
      if not validPassword(new_pass):
         valid = False
         errorMsgs['password'] = 'Password must contain at least one digit, one uppercase, and one lowercase letter and be 6-40 characters long. Can include special characters !@#$%_^&*'
   # check if email address is valid
   if not errorMsgs['email'] and email:
      if not validEmail(email):
         valid = False
         errorMsgs['email'] = 'Please enter a valid email address'
   if not errorMsgs['email'] and email:
      if existingEmail(email):
         errorMsgs['email'] = 'Email address already registered. <a href="?page=forgot">Reset your password?</a>'
         if settings:
            if email == siteVariables['myDetails']['email']:
               vaild = True
               errorMsgs['email'] = ''
   # check image file things
   imgValid, errorMsgs['profile_pic'] = checkImage(profile_pic)
   if valid:
      valid = imgValid
   imgValid, errorMsgs['bg_pic'] = checkImage(bg_pic)
   if valid:
      valid = imgValid


   # check that both coordinates are present
   if (home_lat and not home_long) or (home_long and not home_lat):
      valid = False
      errorMsgs['home_location'] = 'Weird things man. Try again'
   # check that both coords are numbers
   if (home_lat and home_long):
      if (not isNumber(home_lat)) or (not isNumber(home_long)):
         valid = False
         errorMsgs['home_location'] = 'Weird things man. Try again'

   # add HTML nonsense to error messages
   error_start = '<br><span class="sign_up-error">'
   error_end   = '</span>'
   for key in errorMsgs:
      if errorMsgs[key]:
         errorMsgs[key] = error_start + errorMsgs[key] + error_end

   # add to siteVars and return
   siteVariables['errorMsgs'] = errorMsgs
   return valid

def uploadFile(curFile, fileStyle, username):
   extension = curFile.filename.rsplit('.', 1)[-1]
   if fileStyle == "profile":
      filename = username+"-dp."+extension
   if fileStyle == "background":
      filename = username+"-bg."+extension
   # if we couldn't upload for some reason, fail silently..
   filename = UPLOAD_DIR + filename
   try:
      open(filename, 'wb').write(curFile.file.read())
   except:
      return DEFAULT_PIC
   return filename

def uploadAttachment(curFile, attachmentNum, bleat_id):
   extension = curFile.filename.rsplit('.', 1)[-1]
   filename = str(bleat_id)+"_"+str(attachmentNum)+"."+extension

   # if we couldn't upload for some reason, fail silently..
   filename = UPLOAD_DIR + filename
   try:
      open(filename, 'wb').write(curFile.file.read())
   except:
      pass
   return filename

def addNewUser(formFields):
   # hash password
   formFields['new_pass'] = hashlib.md5(formFields['new_pass']).hexdigest() #hash password

   # set profile pic
   profile_pic = DEFAULT_PIC
   bg_pic = DEFAULT_BG
   try:
      if formFields['profile_pic'].filename:
         profile_pic = uploadFile(formFields['profile_pic'], "profile", formFields['new_user'])
   except:
      pass
   # set background pic
   try:
      if formFields['bg_pic'].filename:
         bg_pic = uploadFile(formFields['bg_pic'], "profile", formFields['new_user'])
   except:
      pass

   values = (
      formFields['email']         ,
      formFields['full_name']     ,
      formFields['new_pass']      ,
      formFields['new_user']      ,
      formFields['home_lat']      ,
      formFields['home_location'] ,
      profile_pic                 ,
      formFields['home_long']     ,
      formFields['description']   ,
      bg_pic       # default backgorund pic
   )
   db_conn.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
   conn.commit()

def updateNewUser(formFields):
   global username
   toUpdate = defaultdict(str)
   for key in formFields.keys():
      if key == 'profile_pic':
         # set profile pic
         try:
            if formFields['profile_pic'].filename:
               profile_pic = uploadFile(formFields['profile_pic'], "profile", formFields['new_user'])
               toUpdate['profile_pic'] = profile_pic
         except:
            pass
      elif key == 'bg_pic':
         # set background pic
         try:
            if formFields['bg_pic'].filename:
               bg_pic = uploadFile(formFields['bg_pic'], "profile", formFields['new_user'])
               toUpdate['bg_pic'] = bg_pic
         except:
            pass
      elif formFields[key]:
         if key == 'home_lat':
            toUpdate['home_latitude'] = formFields[key]
         elif key == 'home_long':
            toUpdate['home_longitude'] = formFields[key]
         elif key == 'home_location':
            toUpdate['home_suburb'] = formFields[key]
         elif key == 'new_pass':
            formFields['new_pass'] = hashlib.md5(formFields['new_pass']).hexdigest() #hash password
            toUpdate['password'] = formFields['new_pass']
         elif key == 'new_user': # skip username, as we can't change it
            continue
         else:
            toUpdate[key] = formFields[key]
      elif key == 'description': # description can be empty
         toUpdate['description'] = formFields['description']

   updateStr = ''
   updateGroup = ()
   for key in toUpdate:
      updateStr = updateStr + key + " = (?), "
      updateGroup = updateGroup + (toUpdate[key], )
   updateStr = "SET " + updateStr[:-2]
   updateStr = "UPDATE users " + updateStr + "WHERE username=(?)"
   updateGroup = updateGroup + (username, )

   db_conn.execute(updateStr, updateGroup)
   conn.commit()

def isFollowing(target, user=None):
   global username

   if user is None:
      user = username
   db_conn.execute('SELECT COUNT(*) FROM listeners WHERE username=(?) AND listens=(?)', (user, target))
   if int(db_conn.fetchone()[0]) != 0:
      return True
   return False

def addFollower(user):
   global username

   if not isFollowing(user, username):
      db_conn.execute("INSERT INTO listeners VALUES (?, ?)", (username, user))
      conn.commit()
   
def removeFollower(user):
   global username

   db_conn.execute("DELETE FROM listeners WHERE username=(?) AND listens=(?)", (username, user))
   conn.commit()



# manage page selection (and some form submission checking...)
login = form.getfirst("login-btn", "")
if DEBUG == True: login = "yes"
all_search = form.getfirst("main-search", "")
user_search = form.getfirst("user-search", "")
sign_up = form.getfirst("sign_up-btn", "")
update_settings = form.getfirst("settings-btn", "")
msg = form.getfirst("msg", "")
new_tweet = form.getfirst("tweet-btn", "")

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
elif page == "feed" or (page == "settings" or update_settings) or page == "followme" or page == "unlisten" or new_tweet or page == "delete":
   if not checkSession():
      headers = "Location: ?page=home" #if not logged in redirect home
      page = "home"
elif page == "user_page":
   page = "user_page"
elif page == "bleat_page":
   page == "bleat_page"
elif page == "sign_up" or sign_up:
   if checkSession():
      headers = "Location: ?page=feed" #if logged in redirect to feed
      page = "feed"
   else:
      page = "sign_up"
else:
   page = "error"


def getTweetFields():
   global siteVariables

   formFields = {
      'new-tweet' : form.getfirst("new-tweet", "").strip(),
      'tweet-lat' : form.getfirst("tweet-lat", ""),
      'tweet-long' : form.getfirst("tweet-long", ""),
      'tweet-media' : form.getfirst("tweet-media", ""),
      'in-reply-to' : form.getfirst("in-reply-to", "")
   }
   try:
      formFields['tweet-media'] = form['tweet-media']
   except:
      pass

   siteVariables['formFields'] = formFields
   return formFields


# note in real twitter, following content rules apply
# Maximum image size is 5MB and maximum video size is 15MB.
# You may include up to 4 photos or 1 animated GIF or 1 video in a Tweet.
# Supported image formats: PNG, JPEG, WEBP and GIF. Animated GIFs are supported.
# Supported video formats: MP4
# https://dev.twitter.com/rest/public/uploading-media
def validateTweetFields(formFields, emptyErrors=False):
   global siteVariables
   valid = True

   errorMsgs = {
      'new-tweet' : '',
      'tweet-location' : '',
      'tweet-media' : '',
      'in-reply-to' : ''
   }
   # if empty errors list required, return here
   if emptyErrors:
      siteVariables['errorMsgs'] = errorMsgs
      valid = False
      return valid

   newTweet   = formFields['new-tweet']
   tweetLat   = formFields['tweet-lat']
   tweetLong  = formFields['tweet-long']
   tweetMedia = formFields['tweet-media']
   inReplyTo  = formFields['in-reply-to']
   imgCount   = 0
   vidCount   = 0
   badMedia   = 0
   badSize    = 0
   mediaError = ""
   if not newTweet:
      valid = False
      errorMsgs['new-tweet'] = "Please enter a bleat to continue"
   elif len(newTweet) > 140:
      valid = False
      errorMsgs['new-tweet'] = "Bleat cannot exceed 140 characters"
   elif (tweetLat and not tweetLong) or (tweetLong and not tweetLat):
      valid = False
      errorMsgs['tweet-location'] = "Something strange happened. Try adding your location again"
   elif inReplyTo:
      # check if bleat is valid
      if not validBleat(inReplyTo):
         valid = False
         errorMsgs['in-reply-to'] = "Something strange happened. Try again later"
   elif not isinstance(tweetMedia, str):
      if not isinstance(tweetMedia, list):
         tweetMedia = [tweetMedia]
      for media in tweetMedia:
         if media.filename:
            if media.type in VALID_MIME_IMAGES_TWTS:
               fileSize = len(media.value)
               if media.type == "video/mp4":
                  vidCount += 1
                  if (fileSize > MAX_VID_SIZE):
                     badSize += 1
               else:
                  if (fileSize > MAX_IMG_SIZE):
                     badSize += 1
                  imgCount += 1
            else:
               badMedia += 1
      if imgCount > 0 and vidCount > 0:
         mediaError = "Please only upload one type of media per tweet"
      elif vidCount > 1:
         mediaError = "Only one video can be attached to a tweet"
      elif imgCount > 4:
         mediaError = "Only up to four images can be attached to a tweet"
      elif badMedia > 0:
         mediaError = "Only PNG, JPEG, GIF & MP4 filetypes are supported"
      elif badSize > 0:
         mediaError = "Images cannot be larger than 5MB, Videos 15MB"
      if mediaError:
         valid = False
         errorMsgs['tweet-media'] = mediaError 

   # add to siteVars and return
   siteVariables['errorMsgs'] = errorMsgs
   return valid

def getHighestId():
   db_conn.execute('SELECT MAX(bleat_id) FROM bleats')
   try:
      return db_conn.fetchone()[0]
   except:
      return 0

def insertTweet(formFields):
   global username
   newTweet   = formFields['new-tweet']
   tweetLat   = formFields['tweet-lat']
   tweetLong  = formFields['tweet-long']
   tweetMedia = formFields['tweet-media']
   inReplyTo  = formFields['in-reply-to']
   curTime = int(time.mktime(time.gmtime()))

   bleat_id = getHighestId() + 1

   # upload images
   attachmentCount = 0
   attachmentNames = ['', '', '', '']
   if not isinstance(tweetMedia, str):
      if not isinstance(tweetMedia, list):
         tweetMedia = [tweetMedia]
      for media in tweetMedia:
         if media.filename:
            attachmentNames[attachmentCount] = uploadAttachment(media, attachmentCount, bleat_id)
            attachmentCount += 1

   # check that replied to bleat's user is actually mentioned in the tweet
   # otherwise, the tweet is not in reply to anything..
   if inReplyTo:
      bleatUser = '@'+bleatToUser(inReplyTo)
      explodedTweet = newTweet.split(' ')
      newBleatUsers = []
      for word in explodedTweet:
         if re.match(USER_MATCH, word):
            newBleatUsers.append(word)
      if bleatUser not in newBleatUsers:
         inReplyTo = ''

   # check if location is set
   hasLocation = 0
   if tweetLat and tweetLong:
      hasLocation = 1
   values = (
      bleat_id           ,
      inReplyTo          , #in_reply_to
      username           ,
      tweetLong          ,
      tweetLat           ,
      hasLocation        ,
      curTime            ,
      attachmentCount    ,
      attachmentNames[0] ,
      attachmentNames[1] ,
      attachmentNames[2] ,
      attachmentNames[3] ,
      newTweet
   )
   db_conn.execute("INSERT INTO bleats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values);
   conn.commit()

   # insert referenced ('@'ed) users to database
   explodedTweet = newTweet.split(' ')
   newBleatUsers = []
   for word in explodedTweet:
      if re.match(USER_MATCH, word):
         newBleatUsers.append(word)
   newBleatUsers = list(set(newBleatUsers))  #remove dulpicates
   if newBleatUsers:
      for user in newBleatUsers:
         user = user[1:]
         if validUser(user, True):
            db_conn.execute("INSERT INTO reply_to VALUES (?, ?)", (bleat_id, user));

def deleteBleat(bleat_id):
   db_conn.execute('SELECT * FROM bleats WHERE bleat_id=(?)', (bleat_id, ))
   files = db_conn.fetchone()['files']
   #TODO clear 'in_reply_to'
   #TODO delete images
   db_conn.execute('DELETE FROM bleats WHERE bleat_id=?', (bleat_id, ))
   conn.commit()


# handle page creation, feed population etc.
if page != "error":
   siteVariables['message'] = False
   siteVariables['message_txt'] = ''

   if page == "feed" or page == "settings" or page == "followme" or page == "unlisten" or page == "delete":
      getFeed()
      myDetails(username)
      if page == "settings":
         formFields = getNewUserFormFields()
         if update_settings:
            validForm = processNewUserForm(formFields, True)
            if validForm:
               updateNewUser(formFields)
               myDetails(username) # re-populate myDetails to reflect updated details
         else:
            processNewUserForm(formFields, False, True) #get empty errorMsgs dict
      elif new_tweet:
         formFields = getTweetFields()
         validForm = validateTweetFields(formFields)
         if validForm:
            insertTweet(formFields)
            getFeed()
      elif page == "followme" or page == "unlisten":
         # add to followers list
         follow_user = form.getfirst("user", "")
         if validUser(follow_user, True):
            if page == "followme":
               addFollower(follow_user)
               headers = "Location: ?page=feed&msg_type=2&msg=True&user=" + follow_user
               page = "feed"
            elif page == "unlisten":
               removeFollower(follow_user)
               headers = "Location: ?page=feed&msg_type=3&msg=True&user=" + follow_user
               page = "feed"
         else:
            headers = "Location: ?page=feed&msg_type=1&msg=True&user=" + follow_user
            page = "feed"
      elif page == "delete":
         targetBleat = form.getfirst("bleat_id", "")
         targetBleat = validBleat(targetBleat)
         if targetBleat != None:
            targetUser = bleatToUser(targetBleat)
            if targetUser == username:
               deleteBleat(targetBleat)
               headers = "Location: ?page=feed&msg_type=4&msg=True"
         page = "feed"
      elif bool(msg):
         follow_user = form.getfirst("user", "")
         if follow_user:
            siteVariables['message'] = True
            msgType = form.getfirst("msg_type", "")
            myMsg = ''
            if (msgType == '1'):
               myMsg = "Couldn't find user to listen to"
            elif (msgType == '2'):
               myMsg = "You are now listening to " + follow_user
            elif (msgType == '3'):
               myMsg = "You are no longer listening to " + follow_user
            elif (msgType == '4'):
               myMsg = "Bleat successfully deleted"
            else:
               siteVariables['message'] = False
            siteVariables['message_txt'] = myMsg

   elif page == "sign_up":
      formFields = getNewUserFormFields()
      if sign_up:
         validForm = processNewUserForm(formFields)
         if validForm:
            addNewUser(formFields)
            headers = "Location: ?page=home"
      else:
         processNewUserForm(formFields) #get empty errorMsgs dict

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
         siteVariables['loggedin_user'] = False
         siteVariables['following'] = False
         if checkSession():
            siteVariables['loggedin_user'] = bool(username == targetUser)
            siteVariables['following'] = isFollowing(targetUser)
      else:
         headers = "Location: ?page=feed"
         page = "feed"
   elif page == "bleat_page":
      targetBleat = form.getfirst("bleat_id", "")
      targetBleat = validBleat(targetBleat)
      siteVariables['targetBleat'] = targetBleat
      if targetBleat != None:
         targetUser = bleatToUser(targetBleat)
         myDetails(targetUser)
         getSingleBleat(targetBleat)
         bleatReplies = getBleatReplies(targetBleat)
         siteVariables['bleat_replies'] = False
         if len(bleatReplies):
            siteVariables['bleat_replies'] = True
            getManyBleats(bleatReplies)
         siteVariables['loggedin_user'] = False
         siteVariables['following'] = False
         if checkSession():
            siteVariables['loggedin_user'] = bool(username == targetUser)
            siteVariables['following'] = isFollowing(targetUser)
      else:
         headers = "Location: ?page=feed"
         page = "feed"



# process relevant page
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
