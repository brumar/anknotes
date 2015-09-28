from addict import Dict
import os
from pprint import pprint
absolutely_unused_variable = os.system("cls")

def print_banner(title):
	print "-" * 40
	print title
	print "-" * 40


class Counter(Dict):
	def print_banner(self, title):
		print self.make_banner(title)
	
	@staticmethod
	def make_banner(title):
		return '\n'.join(["-" * 40, title ,"-" * 40])
		
	def __init__(self, *args, **kwargs):
		self.setCount(0)
		# if not isinstance(label, unicode) and not isinstance(label, str): raise TypeError("Cannot create counter label from non-string type: " + str(label))
		self.__label__ = "root"
		self.__parent_label__ = ""
		self.__is_exclusive_sum__ = True
		# return super(Counter, self).__init__(*args, **kwargs)

	def __key_transform__(self, key):
		for k in self.keys():
			if k.lower() == key.lower(): return k
		return key
		# return key[0].upper() + key[1:].lower()

	__count__ = 0
	__label__ = ''
	__parent_label__ = ''
	__is_exclusive_sum__ = False
	__my_aggregates__ = 'max|max_allowed'
	__my_attrs__ = '__count__|__is_exclusive_sum__|__label__|__parent_label__|__my_aggregates__'	
	def getCount(self):
		if self.__is_exclusive_sum__: return self.sum
		return self.__count__

	def setCount(self, value):
		self.__is_exclusive_sum__ = False
		self.__count__ = value

	@property
	def label(self): return self.__label__

	@property
	def parent_label(self): return self.__parent_label__

	@property
	def full_label(self): return self.parent_label + ('.' if self.parent_label else '') + self.label

	@property
	def get(self):
		return self.getCount()

	val = value = cnt = count = get

	@property
	def sum(self):
		# self.print_banner("Getting main Count ")
		sum = 0
		for key in self.iterkeys():
			if key in self.__my_aggregates__.split("|"): continue 
			val = self[key]
			if isinstance(val, int):
				sum += val
			elif isinstance(val, Counter) or isinstance(val, EvernoteCounter):
				sum += val.getCount()
			# print 'sum: ' +  key + ': - ' + str(val) + ' ~ ' + str(sum)
		return sum

	def increment(self, y=1, negate=False):
		newCount = self.__sub__(y) if negate else self.__add__(y) 
		# print "Incrementing %s by %d to %d" % (self.full_label, y, newCount)
		self.setCount(newCount)
		return newCount

	step = increment

	def __coerce__(self, y): return (self.getCount(), y)
	
	def __div__(self, y):
		return self.getCount() / y
		
	def __rdiv__(self, y):
		return y / self.getCount()
		
	__truediv__ = __div__
	
	def __mul__(self, y): return y * self.getCount()
	__rmul__ = __mul__
	
	def __sub__(self, y):
		return self.getCount() - y 
		# return self.__add__(y, negate=True)
		
	def __add__(self, y, negate=False):
		# if isinstance(y, Counter):
			# print "y=getCount: %s" % str(y)
			# y = y.getCount()
		return self.getCount() + y 
		# * (-1 if negate else 1)
		
	__radd__ = __add__
		
	def __rsub__(self, y, negate=False):
		return y - self.getCount()
	
	def __iadd__(self, y):
		self.increment(y)
			
	def __isub__(self, y):
		self.increment(y, negate=True)		
	
	def __truth__(self):
		print "truth"
		return True 
		
	def __bool__(self):
		return self.getCount() > 0
		
	__nonzero__ = __bool__

	def __setattr__(self, key, value):
		key_adj = self.__key_transform__(key)
		if key[0:1] + key[-1:] == '__':
			if key.lower() not in self.__my_attrs__.lower().split('|'):
				raise AttributeError("Attempted to set protected item %s on %s" % (key, self.__class__.__name__))
			else:  super(Dict, self).__setattr__(key, value)
		elif key == 'Count':
			self.setCount(value)
			# super(CaseInsensitiveDict, self).__setattr__(key, value)
			# setattr(self, 'Count', value)
		elif (hasattr(self, key)):
			# print "Setting key " + key + ' value... to ' + str(value)
			self[key_adj].setCount(value)
		else:
			print "Setting attr %s to type %s value %s" % (key_adj, type(value), value)
			super(Dict, self).__setitem__(key_adj, value)

	def __setitem__(self, name, value):
		# print "Setting item %s to type %s value %s" % (name, type(value), value)
		super(Dict, self).__setitem__(name, value)
		
	def __get_summary__(self,level=1,header_only=False):
		keys=self.keys()
		counts=[Dict(level=level,label=self.label,full_label=self.full_label,value=self.getCount(),is_exclusive_sum=self.__is_exclusive_sum__,class_name=self.__class__.__name__,children=keys)]
		if header_only: return counts 
		for key in keys:
			# print "Summaryzing key %s: %s " % (key, type( self[key]))
			if key not in self.__my_aggregates__.split("|"):
				counts += self[key].__get_summary__(level+1)
		return counts 

	def __summarize_lines__(self, summary,header=True):
		lines=[]
		for i, item in enumerate(summary):
			exclusive_sum_marker = '*' if item.is_exclusive_sum and len(item.children) > 0 else ' '
			if i is 0 and header: 
				lines.append("<%s%s:%s:%d>" % (exclusive_sum_marker.strip(), item.class_name, item.full_label, item.value))
				continue 
			# strr = '%s%d' % (exclusive_sum_marker, item.value)
			strr = (' ' * (item.level * 2 - 1) + exclusive_sum_marker + item.label + ':').ljust(16+item.level*2)
			lines.append(strr+' ' + str(item.value).rjust(3) + exclusive_sum_marker)
		return '\n'.join(lines)		
		
	def __repr__(self):
		return self.__summarize_lines__(self.__get_summary__())

	def __getitem__(self, key):
		adjkey = self.__key_transform__(key)
		if key == 'Count': return self.getCount()
		if adjkey not in self:
			if key[0:1] + key[-1:] == '__':
				if key.lower() not in self.__my_attrs__.lower().split('|'): 
					try:
						return super(Dict, self).__getattr__(key.lower())
					except:
						raise(KeyError("Could not find protected item " + key))
				return super(Counter, self).__getattr__(key.lower())
			# print "Creating missing item: " + self.parent_label + ('.' if self.parent_label else '') + self.label  + ' -> ' + repr(adjkey)
			self[adjkey] =  Counter(adjkey)
			self[adjkey].__label__ = adjkey
			self[adjkey].__parent_label__ = self.full_label
			self[adjkey].__is_exclusive_sum__ = True		
		try:
			return super(Counter, self).__getitem__(adjkey)
		except TypeError:
			return "<null>"
			# print "Unexpected type of self in __getitem__: " + str(type(self))
			# raise TypeError
		# except:
			# raise 
		

class EvernoteCounter(Counter):
	@property
	def success(self):
		return self.created + self.updated

	@property
	def queued(self):
		return self.created.queued + self.updated.queued

	@property
	def completed(self):
		return self.created.completed + self.updated.completed

	@property
	def delayed(self):
		return self.skipped + self.queued		

	@property
	def total(self):
		return self.getCount() #- self.max - self.max_allowed

	def aggregateSummary(self, includeHeader=True):
		aggs = '!max|!+max_allowed|total|+success|++completed|++queued|+delayed'
		counts=self.__get_summary__(header_only=True) if includeHeader else []
		parents = []
		last_level=1
		for key_code in aggs.split('|'):
			is_exclusive_sum = key_code[0] is not '!'
			if not is_exclusive_sum: key_code = key_code[1:]
			key = key_code.lstrip('+')
			level = len(key_code) - len(key) + 1			
			val = self.__getattr__(key)
			cls = type(val)
			if cls is not int: val = val.getCount()
			parent_lbl = '.'.join(parents)
			full_label = parent_lbl + ('.' if parent_lbl else '') + key 
			counts+=[Dict(level=level,label=key,full_label=full_label,value=val,is_exclusive_sum=is_exclusive_sum,class_name=cls,children=['<aggregate>'])]
			if level < last_level: del parents[-1]
			elif level > last_level: parents.append(key)
			last_level = level 
		return self.__summarize_lines__(counts,includeHeader)
		
	def fullSummary(self, title='Evernote Counter'):
		return '\n'.join(
		[self.make_banner(title + ": Summary"),
		self.__repr__(),
		' ',
		self.make_banner(title + ": Aggregates"),
		self.aggregateSummary(False)]
		)
	
	def __getattr__(self, key):
		if hasattr(self, key) and key not in self.keys(): 
			return getattr(self, key)
		return super(EvernoteCounter, self).__getattr__(key)
	
	def __getitem__(self, key):
		# print 'getitem: ' + key
		return super(EvernoteCounter, self).__getitem__(key)
		
from pprint import pprint

def test():
	global Counts
	Counts = EvernoteCounter()	
	Counts.unhandled.step(5)
	Counts.skipped.step(3)
	Counts.error.step()
	Counts.updated.completed.step(9)
	Counts.created.completed.step(9)
	Counts.created.completed.subcount.step(3)
	# Counts.updated.completed.subcount = 0
	Counts.created.queued.step()
	Counts.updated.queued.step(3)
	Counts.max = 150
	Counts.max_allowed  = -1
	Counts.print_banner("Evernote Counter: Summary")
	print (Counts)
	Counts.print_banner("Evernote Counter: Aggregates")
	print (Counts.aggregateSummary())
	
	return

	Counts.print_banner("Evernote Counter")
	print Counts
	Counts.skipped.step(3)
	# Counts.updated.completed.step(9)
	# Counts.created.completed.step(9)
	Counts.print_banner("Evernote Counter")
	print Counts
	Counts.error.step()
	# Counts.updated.queued.step()
	# Counts.created.queued.step(7)
	Counts.print_banner("Evernote Counter")
	# print Counts

# test()


