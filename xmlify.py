import os
import sys

###############################
########### READ ME ###########
###############################

# The syntax validator will stop after encountering the first error.
# After fixing that error, additional ones may be reported.

###############################
####### CUSTOMIZE THESE #######
###############################
FILENAME = 'myFile.xml'
NAME = 'My Code'
files = ['main.c']

#########################################
####### CODE BELOW (DO NOT TOUCH) #######
#########################################

VERBOSE = False
for t in sys.argv:
	if t == '-v':
		VERBOSE = True

# Stack Frame states
STATE_NEED_NAME = 0
STATE_NEED_PARENTHESIS = 1
STATE_IN_PARENTHESIS = 2
STATE_WAITING_COMMA = 3
STATE_WAITING_BRACKETS = 4
STATE_IN_BRACKETS = 5
STATE_DONE = 6

STATE_WAITING_CLOSE_PARENTHESIS = 7
STATE_CLOSED = 8

DATATYPE = ['int', 'float', 'string', 'void', 'vector', 'bool']
ARITHMETIC = ['/', '*', '+', '-']
BINARY = ['==', '!=', '<=', '>=', '>', '<', '&&', '||']
FLOW = ['(', ')', '{', '}', ',', ';', ':']

COMBINED = ARITHMETIC + BINARY

LOGIC = ['if', 'for', 'while', 'switch', 'case']

DELIMITER = [',', ';']
IGNORE = ['const']

SYMBOLS = [ARITHMETIC, BINARY, FLOW]

class CustomFunction:
	def __init__(self, name, datatype):
		self.name = name
		self.datatype = datatype
		self.parameters = []

	def add(self, datatype):
		self.parameters.append(datatype)

FUNCTIONS = {}
BASE_JOB = None

THE_TRIGGER_KNOWS = []
IN_TRIGGER = False

KNOWN_FOR = []
KNOWN_TRIGGERS = []
KNOWN_VARIABLES = ['cNumberPlayers', 'cInvalidVector', 'cOriginVector', 'cActivationTime']
KNOWN_TYPES = ['int', 'vector', 'vector', 'int']

ERRORED = False

def error(msg):
	global ln
	global line
	global ERRORED
	ERRORED = True
	print(msg)
	print("Line " + str(ln) + ":\n    " + line)

class Job:
	def __init__(self, name, parent):
		self.name = name
		self.parent = parent
		self.type = ''
		self.datatype = ''
		self.closed = False
		self.expected = []
		self.children = []
	
	def debug(self):
		val = self.name
		if len(self.children) > 0:
			val = val + '('
			first = True
			for c in self.children:
				if not first:
					val = val + ',' + c.debug()
				else:
					val = val + c.debug()
					first = False
			val = val + ')'
		return val

	def resolve(self):
		self.closed = True
		for c in self.children:
			c.resolve()

	def accept(self, token):
		accepted = True
		if len(self.children) > 0:
			# Do you want this token?
			accepted = self.children[-1].accept(token)
		else:
			accepted = False
		return accepted

	def insertAbove(self, frametype, token):
		self.parent.children.remove(self)
		self.parent.children.append(frametype(token, self.parent))
		self.parent = self.parent.children[-1]
		self.parent.children.append(self)

	def parseGeneric(self, token):
		global KNOWN_VARIABLES
		accepted = True
		if token in FUNCTIONS:
			self.children.append(Function(token, self))
		elif token in KNOWN_VARIABLES:
			self.children.append(Variable(token, self))
		elif token == '""':
			self.children.append(Literal(token, self, 'string'))
		elif token.isnumeric():
			self.children.append(Literal(token, self, 'int'))
		elif token[0] == '-' and len(token) > 0:
			if token[1:].isnumeric():
				self.children.append(Literal(token, self, 'int'))
			elif '.' in token[1:]:
				isFloat = True
				for c in token[1:token.find('.')]:
					isFloat = isFloat and c.isnumeric()
				for c in token[token.find('.')+1:]:
					isFloat = isFloat and c.isnumeric()
				if isFloat:
					self.children.append(Literal(token, self, 'float'))
				else:
					accepted = False
			else:
				accepted = False
		elif token == 'vector':
			self.children.append(Literal(token, self, 'vector'))
		elif '.' in token:
			isFloat = True
			for c in token[:token.find('.')]:
				isFloat = isFloat and c.isnumeric()
			for c in token[token.find('.')+1:]:
				isFloat = isFloat and c.isnumeric()
			if isFloat:
				self.children.append(Literal(token, self, 'float'))
			else:
				accepted = False
		elif token in ['true', 'false']:
			self.children.append(Literal(token, self, 'bool'))
		elif token == '(':
			self.children.append(Parenthesis(token, self))
		elif token == 'return':
			self.children.append(Returner(self))
		else:
			accepted = False
		return accepted

# Mathables will check for arithmetic operators and act accordingly
class Mathable(Job):
	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if token in ARITHMETIC:
				insertPoint = self
				while insertPoint.parent.name in COMBINED and COMBINED.index(insertPoint.parent.name) <= COMBINED.index(token):
					insertPoint = insertPoint.parent
				insertPoint.insertAbove(Arithmetic, token)
			elif token in BINARY:
				insertPoint = self
				while insertPoint.parent.name in COMBINED and COMBINED.index(insertPoint.parent.name) <= COMBINED.index(token):
					insertPoint = insertPoint.parent
				insertPoint.insertAbove(Binary, token)
			else:
				accepted = False
		return accepted

class BaseFrame(Job):
	def __init__(self):
		super().__init__("Base", None)
		self.broken = False

	def debug(self):
		if not self.broken:
			for c in self.children:
				print(c.debug())

	def accept(self, token):
		accepted = True
		# The only things that exist in the BaseFrame are functions and triggers
		if not self.broken and not super().accept(token):
			if token in DATATYPE:
				self.children.append(Declaration(token, self))
			elif token == 'rule':
				self.children.append(Trigger(token, self))
			elif token == ';':
				self.children.pop()
			else:
				error("Unrecognized token: " + token)
				self.broken = True
				accepted = False
		return accepted

class StackFrame(Job):
	def __init__(self, name, parent):
		global KNOWN_VARIABLES
		super().__init__(name, parent)
		self.depth = len(KNOWN_VARIABLES)
		self.state = 0

	def resolve(self):
		super().resolve()

	def accept(self, token):
		global KNOWN_VARIABLES
		global KNOWN_TYPES
		accepted = True
		if not super().accept(token):
			if self.state == STATE_WAITING_BRACKETS:
				if token == '{':
					if len(self.children) > 0:
						error("Invalid syntax before {")
					self.state = STATE_IN_BRACKETS
				elif token == ';':
					self.state = STATE_DONE
					self.resolve()
					self.parent.children.remove(self)
				else:
					accepted = self.parseGeneric(token)
			elif self.state == STATE_IN_BRACKETS:
				if token == ';':
					self.children[0].resolve()
					if not self.children[0].type in ['ASSIGNMENT', 'FUNCTION', 'BREAK']:
						error("Unrecognized command.")
					self.children.pop()
				elif token == '}':
					KNOWN_VARIABLES = KNOWN_VARIABLES[:self.depth]
					KNOWN_TYPES = KNOWN_TYPES[:self.depth]
					self.state = STATE_CLOSED
					if self.name != 'if':
						self.resolve()
						self.parent.children.pop()
				elif self.name == 'switch' and not token == 'case':
					accepted = False
				elif token in LOGIC:
					self.children.append(Logic(token, self))
				elif token in DATATYPE:
					if len(self.children) > 0:
						error("Invalid syntax: " + token)
						accepted = False
					else:
						self.children.append(Declaration(token, self))
				elif self.parseGeneric(token):
					accepted = True
				else:
					accepted = False
					if token != 'return':
						self.resolve()
			elif self.state == STATE_CLOSED:
				if self.name != 'if' or token != 'else':
					accepted = False
					self.resolve()
					self.parent.children.pop()
				else:
					self.resolve()
					self.parent.children.pop()
					self.parent.children.append(Logic('else', self.parent))
					self.parent.children[-1].state = STATE_WAITING_BRACKETS
			else:
				accepted = False
		return accepted

class Logic(StackFrame):
	def __init__(self, name, parent):
		global KNOWN_FOR
		super().__init__(name, parent)
		self.state = STATE_NEED_PARENTHESIS
		self.type = 'LOGIC'
		self.datatype = 'void'
		self.fordepth = len(KNOWN_FOR)
		if name == 'case':
			self.state = STATE_IN_PARENTHESIS

	def resolve(self):
		global KNOWN_FOR
		super().resolve()
		KNOWN_FOR = KNOWN_FOR[:self.fordepth]

	def accept(self, token):
		global KNOWN_VARIABLES
		global KNOWN_TYPES
		global KNOWN_FOR
		accepted = True
		if not super().accept(token):
			if self.state == STATE_NEED_PARENTHESIS:
				if token == '(':
					self.state = STATE_IN_PARENTHESIS
				else:
					accepted = False
					error("Invalid syntax before parenthesis: " + token)
			elif self.state == STATE_IN_PARENTHESIS:
				if self.name == 'for':
					# the first item in the for loop is the variable name
					self.children.append(Declaration('int', self))
					self.children[0].name = token
					self.children[0].state = STATE_NEED_PARENTHESIS
					if token in KNOWN_FOR:
						error("Using duplicate variable in nested for loop")
						accepted = False
					elif token in KNOWN_VARIABLES:
						if KNOWN_TYPES[KNOWN_VARIABLES.index(token)] != 'int':
							error("Using a non-integer variable in for-loop: " + token)
							accepted = False
						else:
							KNOWN_FOR.append(token)
					else:
						KNOWN_VARIABLES.append(token)
						KNOWN_TYPES.append('int')
						self.depth = len(KNOWN_VARIABLES) # variables declared in for loops persist
						KNOWN_FOR.append(token)
					self.state = STATE_WAITING_COMMA
				elif (self.name == 'case' and token == ':') or (self.name != 'case' and token == ')'):
					if len(self.children) == 0:
						error("Empty " + self.name)
						accepted = False
					elif self.name == 'switch' or self.name == 'case':
						if self.children[0].datatype != 'int':
							error("Contents of " + self.name + " do not resolve to an integer! " + self.children[0].datatype)
							accepted = False
					elif self.children[0].type == 'ASSIGNMENT':
						error("Assignment operator in " + self.name + ". Use == instead.")
						accepted = False
					elif self.children[0].datatype != 'bool':
						error("Contents of " + self.name + " do not resolve to a boolean! " + self.children[0].datatype)
						accepted = False
					if accepted:
						self.children[0].resolve()
						self.children.clear()
						self.state = STATE_WAITING_BRACKETS
				else:
					accepted = self.parseGeneric(token)
			elif self.state == STATE_WAITING_COMMA:
				if token == ';':
					self.state = STATE_WAITING_CLOSE_PARENTHESIS
					self.children[0].resolve()
					self.children.pop()
					self.children.append(Literal('0', self, 'int'))
				else:
					accepted = False
			elif self.state == STATE_WAITING_CLOSE_PARENTHESIS:
				if token == ')':
					if len(self.children) == 0:
						error("Empty " + self.name)
						accepted = False
					elif self.children[0].name not in ['<','>','<=','>=']:
						error("Invalid syntax in for loop: " + self.children[0].name)
						accepted = False
					else:
						self.children[0].resolve()
						self.children.clear()
						self.state = STATE_WAITING_BRACKETS
				else:
					accepted = self.parseGeneric(token)
			elif self.state == STATE_WAITING_BRACKETS:
				if token == 'if' and self.name == 'else':
					self.state = STATE_NEED_PARENTHESIS
					self.name = 'if'
				else:
					accepted = False
			elif self.state == STATE_IN_BRACKETS:
				if token in ['break', 'continue']:
					searchState = self
					while searchState.name not in ['for', 'while'] and searchState.parent:
						searchState = searchState.parent
					if searchState.name in ['for','while']:
						self.children.append(Literal('0',self,'int'))
						self.children[-1].closed = True
						self.children[-1].type = 'BREAK'
					else:
						accepted = False
				else:
					accepted = False
			else:
				accepted = False
		return accepted


class Trigger(StackFrame):
	def __init__(self, name, parent):
		super().__init__('', parent)
		self.state = STATE_NEED_NAME
		self.type = 'TRIGGER'
		self.datatype = 'void'
		global IN_TRIGGER
		IN_TRIGGER = True

	def resolve(self):
		if self.state == STATE_CLOSED:
			global THE_TRIGGER_KNOWS
			global IN_TRIGGER
			IN_TRIGGER = False
			THE_TRIGGER_KNOWS = []

	def accept(self, token):
		global KNOWN_VARIABLES
		global KNOWN_TRIGGERS
		accepted = True
		if not super().accept(token):
			if self.state == STATE_NEED_NAME:
				if token in KNOWN_VARIABLES:
					error("Declaring a trigger that shares a name with a function or variable: " + token)
					accepted = False
				elif token in KNOWN_TRIGGERS:
					error("Declaring a trigger that shares a name with another trigger: " + token)
					accepted = False
				else:
					KNOWN_TRIGGERS.append(token)
					self.name = token
					self.state = STATE_WAITING_BRACKETS
			elif self.state == STATE_WAITING_BRACKETS:
				if not (token in ['active', 'inactive', 'highFrequency', 'runImmediately'] or 'minInterval' in token or 'maxInterval' in token):
					error("Unknown syntax for trigger declaration: " + token)
					accepted = False
			else:
				accepted = False
		return accepted

class Returner(Job):
	def __init__(self, parent):
		super().__init__('return', parent)
		self.type = 'FUNCTION'
		self.state = STATE_NEED_PARENTHESIS
		self.datatype = 'void'

	def resolve(self):
		if not self.closed:
			super().resolve()
			if len(self.children) != 1:
				error("Invalid syntax in return statement")
			else:
				self.datatype = self.children[0].datatype
			self.children.clear()
			self.state = STATE_DONE

	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if self.state == STATE_NEED_PARENTHESIS:
				if token == '(':
					self.state = STATE_IN_PARENTHESIS
				else:
					accepted = False
					if token == ';':
						self.datatype = 'void'
						self.closed = True
						self.state = STATE_DONE
			elif self.state == STATE_IN_PARENTHESIS:
				if token == ')':
					self.resolve()
				else:
					accepted = self.parseGeneric(token)
			else:
				accepted = False
		return accepted

class Declaration(StackFrame):
	def __init__(self, name, parent):
		super().__init__('', parent)
		global ln
		global line
		self.state = STATE_NEED_NAME
		self.type = 'VARIABLE'
		self.datatype = name
		self.returner = None
		self.returnType = 'void'
		self.ln = ln
		self.line = line

	def resolve(self):
		if not self.closed:
			self.closed = True
			super().resolve()
			if self.type == 'FUNCTION':
				FUNCTIONS.update({self.name : CustomFunction(self.name, self.datatype)})
				for frame in self.children:
					FUNCTIONS[self.name].add(frame.datatype)
		elif self.state == STATE_CLOSED:
			if self.returnType != self.datatype:
				global ERRORED
				ERRORED = True
				print("Function must return a value of type " + self.datatype)
				print("Line " + str(self.ln) + ":\n    " + self.line)

	def accept(self, token):
		global THE_TRIGGER_KNOWS
		global IN_TRIGGER
		global KNOWN_VARIABLES
		global KNOWN_TYPES
		accepted = True
		# intercept return statements
		if not super().accept(token):
			if self.state == STATE_NEED_NAME:
				if token in KNOWN_VARIABLES:
					error("Declaring a function or variable name that was already declared in this context: " + token)
					accepted = False
				elif token in THE_TRIGGER_KNOWS and IN_TRIGGER:
					error("Duplicate declaration of variable within the same trigger: " + token)
				else:
					self.name = token
					self.state = STATE_NEED_PARENTHESIS
					KNOWN_VARIABLES.append(self.name)
					KNOWN_TYPES.append(self.datatype)
					if IN_TRIGGER:
						THE_TRIGGER_KNOWS.append(self.name)
			elif self.state == STATE_NEED_PARENTHESIS:
				if not token in ['=', '(']:
					accepted = False
				elif token == '(':
					# shift depth forward to remember this function
					self.depth = len(KNOWN_VARIABLES)
					self.state = STATE_IN_PARENTHESIS
					self.type = 'FUNCTION'
				else:
					self.resolve()
					self.insertAbove(Assignment, token)
					self.state = STATE_DONE
			elif self.state == STATE_IN_PARENTHESIS:
				if self.type == 'FUNCTION' and token in DATATYPE:
					self.children.append(Declaration(token, self))
					self.state = STATE_WAITING_COMMA
				elif self.type == 'FUNCTION' and token == ')':
					if len(self.children) > 0:
						error("Invalid syntax in function declaration. All parameters must have default values")
					else:
						self.resolve()
						self.children.clear()
						self.state = STATE_WAITING_BRACKETS
				else:
					accepted = False
			elif self.state == STATE_WAITING_COMMA:
				if not token in [',',')']:
					accepted = False
				else:
					self.children[-1].resolve()
					if self.children[-1].type != 'ASSIGNMENT':
						error("Invalid syntax in function declaration. All parameters must have default values")
					self.state = STATE_IN_PARENTHESIS
					if token == ')':
						self.resolve()
						self.children.clear()
						self.state = STATE_WAITING_BRACKETS
			elif self.state == STATE_IN_BRACKETS:
				if token == 'return':
					self.returner = Returner(self)
				else:
					accepted = False
			else:
				accepted = False
		if self.returner is not None:
			if token == ';':
				self.returner.resolve()
				if self.returner.datatype != self.datatype:
					if not (self.returner.datatype in ['int', 'float'] and self.datatype in ['int', 'float']):
						error("Return type of " + self.returner.datatype + " does not match function return type of " + self.datatype)
				else:
					self.returnType = self.returner.datatype
				self.returner = None
		elif token == 'return':
			child = self
			while len(child.children) > 0:
				child = child.children[-1]
			self.returner = child
		return accepted

class Assignment(Job):
	def __init__(self, name, parent):
		super().__init__(name, parent)
		self.type = 'ASSIGNMENT'

	def resolve(self):
		if not self.closed:
			super().resolve()
			self.closed = True
			if len(self.children) != 2:
				error("Incorrect number of inputs for assignment operator " + self.name)
			else:
				self.datatype = self.children[0].datatype
				if self.datatype != self.children[1].datatype:
					if not (self.datatype in ['int', 'float'] and self.children[1].datatype in ['int', 'float']):
						error("Cannot assign " + self.children[1].datatype + " to " + self.datatype)

	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if self.closed:
				accepted = False
			elif len(self.children) < 2:
				accepted = self.parseGeneric(token)
			else:
				self.resolve()
				accepted = False
		return accepted

class Literal(Mathable):
	def __init__(self, name, parent, datatype):
		super().__init__(name, parent)
		self.type = 'LITERAL'
		self.datatype = datatype
		if datatype != 'vector':
			self.closed = True
		else:
			self.state = 0

	def resolve(self):
		super().resolve()
		if self.datatype == 'vector':
			if len(self.children) != 3:
				error("vector literal must contain 3 numeric components but only found " + str(len(self.children)))

	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if self.closed:
				accepted = False
			else:
				if self.state == 0:
					if token == '(':
						self.state = 1
					else:
						accepted = False
				elif self.state == 1:
					if token == ')':
						self.resolve()
					elif token == ',':
						if len(self.children) == 3:
							error("Vector only accepts three parameters")
							accepted = False
					elif self.parseGeneric(token):
						accepted = self.children[-1].type == 'LITERAL' and self.children[-1].datatype in ['int', 'float']
						if not accepted:
							error("Vector literals can only contain literal integers or floats. Variables are not allowed.")
		return accepted


class Function(Mathable):
	def __init__(self, name, parent):
		super().__init__(name, parent)
		self.name = name
		self.type = 'FUNCTION'
		self.datatype = FUNCTIONS[name].datatype
		self.expected = FUNCTIONS[name].parameters
		self.state = 0
		self.count = 0

	def resolve(self):
		if not self.closed:
			super().resolve()
			self.closed = True
			if self.state != 3:
				error("Missing close parenthesis");
			elif len(self.children) > len(self.expected):
				error("Too many inputs for " + self.name + " expected " + str(len(self.expected)) + " but received " + str(len(self.children)))
			else:
				for i in range(len(self.children)):
					if self.expected[i] != self.children[i].datatype:
						if not (self.expected[i] in ['int', 'float'] and self.children[i].datatype in ['int', 'float']):
							error("Incorrect datatype in " + self.name + " parameter " + str(i+1) + "! Expected " + self.expected[i] + " but got " + self.children[i].datatype)
				self.name = self.datatype
				self.children = []

	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if self.closed:
				accepted = False
			elif self.state == 0:
				if token == '(':
					self.state = 1
				else:
					accepted = False
			elif token == ')':
				self.state = 3;
				self.resolve()
			elif self.state == 1:
				accepted = self.parseGeneric(token)
				if accepted:
					self.state = 2
			elif self.state == 2:
				if token == ',':
					if len(self.children) == self.count:
						error("Unused comma")
						accepted = False
					else:
						self.children[-1].resolve()
						self.count = len(self.children)
						self.state = 1;
				else:
					error("Missing comma in function statement in: " + self.name)
					accepted = False
				
		return accepted

class Variable(Mathable):
	def __init__(self, name, parent):
		global KNOWN_VARIABLES
		super().__init__(name, parent)
		self.name = name
		self.type = 'VARIABLE'
		self.datatype = KNOWN_TYPES[KNOWN_VARIABLES.index(name)]
		self.closed = True

	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if token == '=':
				self.insertAbove(Assignment, token)
			else:
				accepted = False
		return accepted


class Arithmetic(Mathable):
	def __init__(self, name, parent):
		super().__init__(name, parent)
		self.type = 'ARITHMETIC'

	def resolve(self):
		if not self.closed:
			super().resolve()
			self.closed = True
			if len(self.children) != 2:
				error("Incorrect number of inputs for arithmetic operator " + self.name)
			else:
				self.datatype = self.children[0].datatype
				for i in range(2):
					if self.children[i].datatype in ['bool', 'void']:		
						error("Cannot perform arithmetic operator " + self.name + " on " + self.children[i].name + " of type " + self.children[i].datatype)
				
				if self.datatype == 'string' and self.name in ['-', '/', '*']:
					error("Cannot perform arithmetic operator " + self.name + " on a string!")
				elif self.datatype != self.children[1].datatype and self.children[1].datatype == 'string':
					error("Cannot add a string to a " + self.datatype)

				self.name = self.datatype
				self.children = []

	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if self.closed:
				accepted = False
			elif len(self.children) < 2:
				accepted = self.parseGeneric(token)
			else:
				self.resolve()
				accepted = False
		return accepted



class Binary(Mathable):
	def __init__(self, name, parent):
		super().__init__(name, parent)
		self.type = 'BINARY'
		self.datatype = 'bool'
		if self.name in ['&&', '||']:
			self.expected = ['bool', 'bool']

	def resolve(self):
		if not self.closed:
			super().resolve()
			self.closed = True
			if len(self.children) != 2:
				error("Incorrect number of inputs for boolean operator " + self.name)
			elif len(self.expected) > 0:
				self.datatype = self.expected[0]
				for i in range(2):
					if self.children[i].datatype != self.expected[i]:
						error("Invalid datatype used in logic statement " + self.name + ". Expected boolean but received " + self.children[i].datatype)
			else:
				if self.children[0].datatype != self.children[1].datatype:
					if not (self.children[0].datatype in ['int', 'float'] and self.children[1].datatype in ['int', 'float']):
						error("Cannot perform boolean operator " + self.name + " on data of type " + self.children[0].datatype + " and " + self.children[1].datatype)

				self.children = []

	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if self.closed:
				accepted = False
			elif len(self.children) < 2:
				accepted = self.parseGeneric(token)
			else:
				self.resolve()
				accepted = False
		return accepted

class Parenthesis(Mathable):
	def __init__(self, name, parent):
		super().__init__(name, parent)
		self.type = 'PARENTHESIS'

	def resolve(self):
		if not self.closed:
			self.closed = True
			if len(self.children) != 1:
				error("Unresolved operations in parenthesis")
			else:
				self.datatype = self.children[0].datatype
				self.name = self.datatype
				self.children = []

	def accept(self, token):
		accepted = True
		if not super().accept(token):
			if self.closed:
				accepted = False
			else:
				if token == ')':
					self.resolve()
				else:
					accepted = self.parseGeneric(token)
		return accepted


##########################
####### END SYNTAX #######
##########################


def removeStrings(line):
	retline = ""
	isString = False
	for i in range(len(line)):
		token = line[i]
		if token == '"':
			if i == 0 or line[i-1] != "\\":
				isString = not isString
			else:
				continue
		if not isString or token == '"':
			retline = retline + token
	if "//" in retline:
		retline = retline[:retline.find("//")]
	return retline

print("Reading Command Viewer")
with open('Commands.xml', 'r') as fd:
	line = fd.readline()
	while line:
		if '<method' in line:
			fq = line.find('"') + 1
			lq = line.rfind('"')
			name = line[line.rfind('"',0,lq-1)+1:lq] # The thing between the last two quotes
			FUNCTIONS.update({name: CustomFunction(name, line[fq:line.find('"',fq+1)])})
			while not '</method' in line:
				if '<parameters' in line:
					fq = line.find('"') + 1
					FUNCTIONS[name].add(line[fq:line.find('"',fq+1)])
				line = fd.readline()
		line = fd.readline()

print("rmsification start!")

ln = 1
FILE_1 = None
comment = False
try:
	with open(FILENAME, 'w') as file_data_2:
		with open("template.txt", 'r') as template:
			line = template.readline()
			while line:
				file_data_2.write(line)
				line = template.readline()
		file_data_2.write('\n<Effect name="'+ NAME +'">\n')
		file_data_2.write('<Command>xsDisableSelf();}}</Command>\n')
		for f in files:
			FILE_1 = f
			ln = 1
			pcount = 0 # parenthesis
			bcount = 0 # brackets
			sys.stdout.flush()
			print("parsing " + FILE_1 + "...")
			rewrite = []
			thedepth = 0
			BASE_JOB = BaseFrame()
			with open(FILE_1, 'r') as file_data_1:
				line = file_data_1.readline()
				while line:
					# Rewrite history
					reline = line.strip()
					nostrings = removeStrings(reline)
					if '}' in nostrings:
						thedepth = thedepth - 1
					reline = "\t" * thedepth + reline
					rewrite.append(reline)
					if '{' in nostrings:
						thedepth = thedepth + 1
					thedepth = thedepth + nostrings.count('(') - nostrings.count(')')
					pcount = pcount + nostrings.count('(') - nostrings.count(')')
					bcount = bcount + nostrings.count('{') - nostrings.count('}')
					
					if not line.isspace():
						if ('/*' in line):
							comment = True

						if not comment:
							if not ERRORED:
								templine = nostrings
								for s in SYMBOLS:
									for n in s:
										if n == '-':
											templine = list(templine)
											for i in range(len(templine)-1):
												if templine[i] == '-':
													if templine[i+1].isnumeric() and templine[i-1] in [' ', '(', ',']:
														templine[i] = ' -'
													else:
														templine[i] = ' - '
											templine = "".join(templine)
										else:
											templine = templine.replace(n, ' ' + n + ' ')
								templine = templine.replace('=', ' = ').replace(' =  = ', ' == ').replace('! = ', ' != ').replace(' >  = ', ' >= ').replace(' <  = ', '<=').replace('minInterval ', 'minInterval').replace('maxInterval ', 'maxInterval').replace('\t', ' ')
								tokens = [token for token in templine.split(' ') if token != '']

								for token in tokens:
									if not token in IGNORE:
										#print(token)
										BASE_JOB.accept(token)
										if VERBOSE and not ERRORED:
											BASE_JOB.debug()
							
							templine = reline.strip()
							if '//' in templine:
								templine = templine[:templine.find('//')].strip()

							# Obsolete Sanity Checks
							if (len(templine) > 240):
								print("Line length greater than 240! Length is " + str(len(templine)))
								print("Line " + str(ln) + ":\n    " + line)
							if len(templine) > 0 and not (templine[-1] == ';' or templine[-1] == '{' or templine[-1] == '}' or templine[-2:] == '||' or templine[-2:] == '&&' or templine[-1] == ',' or templine[-4:] == 'else' or templine[0:4] == 'rule' or templine == 'highFrequency' or templine == 'runImmediately' or templine[-1] == '/' or templine[-6:] == 'active' or templine[0:11] == 'minInterval' or templine[0:4] == 'case' or templine[0:7] == 'switch('):
								print("Missing semicolon")
								print("Line " + str(ln) + ":\n    " + line)

							# reWrite the line
							if '<' in line or '&' in line or '|' in line:
								file_data_2.write('<Command><![CDATA[' + line.rstrip() + ']]></Command>\n')
							else:
								file_data_2.write('<Command>' + line.rstrip() + '</Command>\n')
						if ('*/' in line):
							comment = False
					else:
						file_data_2.write('\n')
					line = file_data_1.readline()
					ln = ln + 1
			BASE_JOB.resolve()
			# reformat the .c raw code
			with open(FILE_1, 'w') as file_data_1:
				for line in rewrite:
					file_data_1.write(line + '\n')
			if pcount < 0:
				print("ERROR: Extra close parenthesis detected!\n")
			elif pcount > 0:
				print("ERROR: Missing close parenthesis detected!\n")
			if bcount < 0:
				print("ERROR: Extra close brackets detected!\n")
			elif bcount > 0:
				print("ERROR: Missing close brackets detected!\n")
		
		file_data_2.write('<Command>rule zenowashere</Command>\n')
      	file_data_2.write('<Command>inactive</Command>\n')
      	file_data_2.write('<Command>highFrequency</Command>\n')
      	file_data_2.write('<Command>{</Command>\n')
	    file_data_2.write('<Command>if(true) {</Command>\n')
	    file_data_2.write('<Command>xsDisableSelf();</Command>\n')
		file_data_2.write('</Effect>\n')
		file_data_2.write('</Effects>\n')
		file_data_2.write('</trigger>')
except IOError:
	sys.exit("Files not found!")

print("Done!")