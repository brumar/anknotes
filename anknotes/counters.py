from addict import Dict
import os 
from pprint import pprint
absolutely_unused_variable = os.system("cls")

def print_banner(title):
	print "-" * 40 
	print title
	print "-" * 40 


class Counter(Dict):
	@staticmethod
	def print_banner(title):
		print "-" * 40 
		print title
		print "-" * 40 
	
	def __init__(self, *args, **kwargs):
		self.setCount(0)
		return super(Counter, self).__init__(*args, **kwargs)
		
	def __key_transform__(self, key):
		for k in self.keys():
			if k.lower() == key.lower(): return k 
		return key
		# return key[0].upper() + key[1:].lower()
	
	__count__ = 0
	__is_exclusive_sum__ = False 
	# @property 
	# def Count(self):
		# return self.__count__
	__my_attrs__ = '__count__|__is_exclusive_sum__'
	def getCount(self):
		if self.__is_exclusive_sum__: return self.main_count
		return self.__count__
		
	def setCount(self, value):
		self.__is_exclusive_sum__ = False
		self.__count__ = value 
		
	@property
	def main_count(self):
		self.print_banner("Getting main Count ")
		sum = 0
		for key in self.iterkeys():
			val = self[key]
			if isinstance(val, int):
				sum += val 				
			elif isinstance(val, Counter):
				if hasattr(val, 'Count'): sum += val.getCount()
				
			print 'main_count: ' +  key + ': - ' + str(val) + ' ~ ' + str(sum) 
		return sum
		
	@property
	def value(self):
		if not hasattr(self, 'Count'): return 0
		return self.getCount()
	
	
	def increment(self, y):
		# from copy import deepcopy
		self.setCount(self.getCount() + y)
		# return copy
		
		
	def __sub__(self, y):
		return self.__add__(-1 * y)
		print " Want to subtr y " + y
	
	def __sum__(self):
		return 12
	# def __add__(self, y):
		# return self.Count + y
	
	def __setattr__(self, key, value):		
		key_adj = self.__key_transform__(key)
		if key[0:2] + key[-2:] == '____': 
			if key.lower() not in self.__my_attrs__.lower().split('|'):
				raise AttributeError("Attempted to set protected item %s on %s" % (key, self.__class__.__name__))
			else:  super(Dict, self).__setattr__(key, value)
		elif key == 'Count':
			self.setCount(value)
			# super(CaseInsensitiveDict, self).__setattr__(key, value)
			# setattr(self, 'Count', value)
		elif (hasattr(self, key)): 
			print "Setting key " + key + ' value... to ' + str(value)
			self[key_adj].setCount(value)
		else: super(Counter, self).__setitem__(key_adj, value)

	# def __setitem__(self, key, value):		
		# if key[0:2] + key[-2:] == '____': raise AttributeError("Attempted to set protected item %s on %s" % (key, self.__class__.__name__))
		# else: super(CaseInsensitiveDict, self).__setitem__(self.__key_transform__(key), value)

	# def __str__(self):
		# return str(self.getCount()) + '\n' + super(Dict, self).__str__()
		
	# def __repr__(self):
		# return str(self.getCount()) + '\n' + super(Dict, self).__repr__() 
		
	# def __str_base__(self):
		# return  super(Dict, self).__str__()
		
	# def __repr_base__(self):
		# return  super(Dict, self).__repr__()
		
	def __repr__(self):
		strr = "<%s%d>" % ('*' if self.__is_exclusive_sum__ else '', self.getCount() )
		delimit=': '
		if len(self.keys()) > 0:			
			strr += delimit 
			delimit=''
			delimit_suffix=''
			for key in self.keys():				
				val = self[key]
				is_recursive = hasattr(val, 'keys') and len(val.keys())
				strr += delimit + delimit_suffix 
				delimit_suffix=''				
				if is_recursive: strr += '\n { '				
				else: strr += '   '
				strr += "%s: %s" % (key, self[key].__repr__().replace('\n', '\n  '))
				if is_recursive: 
					strr += ' }'				
					delimit_suffix='\n'
				delimit=', '
			strr += ""
		return strr
		
	def __getitem__(self, key):
		# print "Getting " + key
		adjkey = self.__key_transform__(key)
		# if hasattr(self, key.lower()):
			# print "I have " + key
			
			# return super(CaseInsensitiveDict, self).__getitem__(key.lower())
		if key == 'Count': return self.getCount()
		if adjkey not in self: 
			if key[0:2] + key[-2:] == '____': 
				if key.lower() not in self.__my_attrs__.lower().split('|'): return super(Dict, self).__getattr__(key.lower())
				return super(Counter, self).__getattr__(key.lower())
			# new_dict = CaseInsensitiveDict()
			# new_dict.Count = 0 
			# print "New dict for " + key
			self[adjkey] = Counter()			
			self[adjkey].__is_exclusive_sum__ = True 
		return super(Counter, self).__getitem__(adjkey)
	

# Counts = Counter()
# # Counts.Count = 0
# Counts.Max = 100
# print "Counts.Max: " + str(Counts )
# Counts.Current.Updated.setCount(5)
# Counts.Current.Updated.Skipped.setCount(3)
# Counts.Current.Created.setCount(20)
# print "Counts.Current.* " + str(Counts.getCount() )
# # Counts.max += 1
# # Counts.Total += 1
# print "Now, Final Counts: \n"
# print Counts 
# # print Counts.New.Skipped + 5
# print Counts.Current.main_count


# print_banner("pprint counts 1")
# pprint( Counts)
# Counts.increment(-7)
# print_banner("pprint counts -= 7")
# pprint( Counts)
# print_banner("pprint counts.current.created.count")
# pprint(Counts.Current.Created.getCount())