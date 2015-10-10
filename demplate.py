#demplate! (aka derek's template! geddit...!!)
# .....................
# .....................
# i'll show myself out...

#let's just rip off django's demplating syntax
#https://docs.djangoproject.com/en/1.7/topics/templates/
#{# comments #}
#{{ variable }}
#{% tag %}
#tags to support
#  if, elif, else | end
#  for | end

import re
import string

# setup metacharacters
START_VAR  = "{{"
END_VAR    = "}}"
START_TAG  = "{%"
END_TAG    = "%}"
START_COM  = "{#"
END_COM    = "#}"
siteTokens = map(re.escape, (START_VAR, END_VAR, START_TAG, END_TAG, START_COM, END_COM))
metaChars  = re.compile(r'('+'|'.join(siteTokens)+')')

# setup conditional statements
#  if, elif, else | end
#  for | end
FOR_REGEX  = re.compile(r'^\s+for\s+([^\s]+)\s+in\s+([^\s]+)\s+$')
IF_REGEX   = re.compile(r'^\s+if\s+([^\s]+)\s+$')
ELIF_REGEX = re.compile(r'^\s+elif\s+([^\s]+)\s+$')
ELSE_REGEX = re.compile(r'^\s+else\s+$')
END_REGEX  = re.compile(r'^\s+end\s+$')

class ParseSite:
   def __init__(self, site):
      self.tokens = []
      self.curToken = -1
      self.tokenCount = 0
      self.tokenize(site)
      # spent N minutes wondering why my tokens weren't persisting
      # had this as 
      # self.tokenize(site)
      # self.tokens = []
      # RIP.
   def tokenize(self, site):
      # tokenize doc by splitting it up
      self.tokens = re.split(metaChars, site)
      self.tokenCount = len(self.tokens)
   def showTokens(self):
      print self.tokens
   def notLastToken(self):
      return self.curToken < (self.tokenCount-1)
   def nextToken(self):
      if self.notLastToken():
         self.curToken += 1
         return self.tokens[self.curToken]
      else:
         #try to handle this nicely, if we accidentally overshoot
         return ""
   def processTokens(self):
      while self.notLastToken():
         curToken = self.nextToken()
         if curToken == START_VAR:
            print "var"
   def processVar(self):
      self.addNode
   def addNode(self, Node):
      

class VarNode:
   def __init__(self, varName):
      self.varName = varName
   def output(self):
      return exec("print self.varName")







filename = "test.html"
site = open(filename, "r").read()
x = ParseSite(site)

x.showTokens()
x.processTokens()
