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
FOR_STR    = re.compile(r'^\s+for\s+([^\s]+)\s+in\s+([^\s]+)\s+$')
IF_STR     = re.compile(r'^\s+if\s+(.*?)\s+$')
ELIF_STR   = re.compile(r'^\s+elif\s+([^\s]+)\s+$')
ELSE_STR   = re.compile(r'^\s+else\s+$')
END_FOR    = re.compile(r'^\s+endfor\s+$')
END_IF     = re.compile(r'^\s+endif\s+$')

class ParseError(Exception):
   pass
class ConversionError(Exception):
   pass

class ParseSite:
   def __init__(self, site):
      self.tokens = []
      self.curToken = -1
      self.tokenCount = 0
      self.tokenize(site)
   def tokenize(self, site):
      # tokenize doc by splitting it up
      self.tokens = re.split(metaChars, site)
      self.tokenCount = len(self.tokens)
   def showTokens(self):
      print self.tokens
   def notLastToken(self):
      return self.curToken < (self.tokenCount-1)
   def nextToken(self):
      self.curToken += 1
      return self.tokens[self.curToken]
   def currentToken(self):
      return self.tokens[self.curToken]
   def processTokens(self, forBlock=False, rootIfBlock=False, ifBlock=False, elifBlock=False, elseBlock=False):
      siteGroup = SiteNodes() #create new site node group

      while self.notLastToken():
         curToken = self.nextToken()
         print curToken
         if curToken == START_VAR:
            curNode = self.processVar()
         elif curToken == START_TAG:
            curToken = self.nextToken()
            # if we're in a block, check if we've reached the end of it 
            if forBlock or ifBlock or elifBlock or elseBlock or rootIfBlock:
               #print curToken + "for" + str(forBlock)
               #print curToken + "if " + str(ifBlock)
               #print curToken + "eli" + str(elifBlock)
               #print curToken + "els" + str(elseBlock)
               #print curToken + "roo" + str(rootIfBlock)
               if forBlock and END_FOR.match(curToken):
                  self.nextToken() # skip over closing tag
                  break
               elif ifBlock and (ELIF_STR.match(curToken) or ELSE_STR.match(curToken)):
                  # go back so we can capture the next statement
                  self.curToken-=2
                  break
               elif elifBlock and (ELIF_STR.match(curToken) or ELSE_STR.match(curToken)):
                  # go back so we can capture the next statement
                  self.curToken-=2
                  break
               elif (ifBlock or elifBlock or elseBlock or rootIfBlock) and END_IF.match(curToken):
                  if not rootIfBlock:
                     # if not root block, go backwards so we can capture the endif again
                     # and exit out of our if block
                     self.curToken-=2
                  else:
                     self.nextToken() # skip over closing tag
                  break
            # otherwise - hold on - we're doing DEEPER
            print "DEEPER"
            curNode = self.processTag(rootIfBlock)
         else:
            curNode = self.processText()
         siteGroup.addNode(curNode)
      return siteGroup
   def processTag(self, rootIfBlock=False):
      #if not self.currentToken() == START_TAG:
      #   raise ParseError("Start tag expected")
      expr = self.currentToken()
      if not self.nextToken() == END_TAG:
         raise ParseError("End tag expected")
      if FOR_STR.match(expr):
         var = FOR_STR.match(expr).group(1)
         cond = FOR_STR.match(expr).group(2)
         print "BEGIN"
         body = self.processTokens(forBlock=True) # process the body
         print "ENDDD"
         print body.myNodes
         curNode = ForNode(var, cond, body)
      elif (IF_STR.match(expr) and rootIfBlock):
         # create an if branch (which also creates the first if node)
         cond = IF_STR.match(expr).group(1)
         body = self.processTokens(ifBlock=True)
         curNode = IfNode("if", cond, body)
         #self.processIf(cond, body)
         #print IF_STR.match(expr).group(1)
         #body = self.processTokens(ifBlock=True) # process the body
         #curNode = ForNode(var, cond, body)
      elif IF_STR.match(expr):
         curNode = self.processIf()
         #curNode = self.processTokens(ifBlock=True)
      elif ELSE_STR.match(expr):
         body = self.processTokens(elseBlock=True)
         expr = "True"  # always evaluate an else statement
         curNode = IfNode("else", expr, body)
      else:
         raise NotImplementedError(expr)
      return curNode
   def processIf(self):
      # add if, elif, else to site tree
      # not strictly neceessary when you think about but probably best practice...
      # (i.e. couldn't we just combine evaluation and node creation :P)
      # go back so we can capture the leading if
      self.curToken-=3
      body = self.processTokens(rootIfBlock=True)
      return IfBranch(body)
   def processVar(self):
      if not self.currentToken() == START_VAR:
         raise ParseError("Start var expected")
      curVar = self.nextToken()
      if not self.nextToken() == END_VAR:
         raise ParseError("End var expected")
      return VarNode(curVar)
   def processText(self):
      return TextNode(self.currentToken())

class SiteNodes():
   def __init__(self):
      self.myNodes = []
   def addNode(self, node):
      self.myNodes.append(node)
   def convert(self):
      converted = ""
      print "SiteNodes convert"
      print self.myNodes
      for node in self.myNodes:
         print "herro"
         print node.convert()
         print "goodbry"
         converted += node.convert()
      return converted
   def convertIf(self):
      for node in self.myNodes:  #loop over nodes until we find true one
         if node.evaluate():
            break
      return node.convert() #convert true node

class IfBranch:
   def __init__(self, body):
      self.inners = []
      self.types = {'if':1, 'elif':0, 'else':0}
      self.body = body
      # create our leading if node (as we will always have an if block)
   #def addNode(self, nodeType, expr):
   #   innerNode = IfNode(nodeType, expr)
   #   self.inners.append(innerNode)
   #   self.types[noType] += 1
   #def convert(self):
      print self.inners
   def convert(self):
      self.converted = ""
      #for node in self.body:
      #   self.converted += node.convert()
      return self.body.convertIf()


class IfNode:
   def __init__(self, ifType, expr, body):
      self.expr = expr
      self.ifType = ifType
      self.body = body
      self.converted = ""
   def getIfType(self):
      return self.ifType
   #def addBody(body):
   #   self.body = body
   def evaluate(self):
      return eval(self.expr)
   def convert(self):
      return self.body.convert()

class ForNode:
   def __init__(self, variable, cond, body):
      self.variable = variable
      self.cond = cond
      self.body = body
   def convert(self):
      #self.converted = ""
      #for node in self.body:
      #   self.converted += node.convert()
      converted = ""
      # use a dictionary fool !
      # http://stackoverflow.com/a/5599313/1813955
      for tempVar in eval(self.cond, globals()):
         exec(self.variable + " = " + tempVar, globals())
         converted += self.body.convert()
      return converted

class VarNode:
   def __init__(self, varName):
      self.varName = varName.strip()
      self.converted = ""
   def convert(self):
      try:
         return str(eval(self.varName, globals()))
      except:
         raise ConversionError("var {{ %s }} undefined" % self.varName)

class TextNode:
   def __init__(self, body):
      self.converted = body
   def convert(self):
      return self.converted


athlete_list = ['john', 'jay', 'smith']


filename = "test.html"
site = open(filename, "r").read()
parser = ParseSite(site)
parser.showTokens()
completeSite = parser.processTokens()

print "huh"
print completeSite.convert()
print "huh"

