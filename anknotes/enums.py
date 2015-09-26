from anknotes.enum import Enum, EnumMeta, IntEnum
from anknotes import enum
class AutoNumber(Enum):
	def __new__(cls, *args):
		"""

		:param cls:
		:return:
		:rtype : AutoNumber
		"""
		value = len(cls.__members__) + 1
		if args and args[0]: value=args[0]
		while value in cls._value2member_map_: value += 1
		obj = object.__new__(cls)
		obj._id_ = value
		obj._value_ = value
		# if obj.name in obj._member_names_:
		#     raise KeyError
		return obj
class OrderedEnum(Enum):
	def __ge__(self, other):
		if self.__class__ is other.__class__:
			return self._value_ >= other._value_
		return NotImplemented
	def __gt__(self, other):
		if self.__class__ is other.__class__:
			return self._value_ > other._value_
		return NotImplemented
	def __le__(self, other):
		if self.__class__ is other.__class__:
			return self._value_ <= other._value_
		return NotImplemented
	def __lt__(self, other):
		if self.__class__ is other.__class__:
			return self._value_ < other._value_
		return NotImplemented
class auto_enum(EnumMeta):
	def __new__(metacls, cls, bases, classdict):
		original_dict = classdict
		classdict = enum._EnumDict()
		for k, v in original_dict.items():
			classdict[k] = v
		temp = type(classdict)()
		names = set(classdict._member_names)
		i = 0

		for k in classdict._member_names:
			v = classdict[k]
			if v == () :
				v = i
			else:
				i = max(v, i)
			i += 1
			temp[k] = v
		for k, v in classdict.items():
			if k not in names:
				temp[k] = v
		return super(auto_enum, metacls).__new__(
				metacls, cls, bases, temp)

	def __ge__(self, other):
		if self.__class__ is other.__class__:
			return self._value_ >= other._value_
		return NotImplemented
	def __gt__(self, other):
		if self.__class__ is other.__class__:
			return self._value_ > other._value_
		return NotImplemented
	def __le__(self, other):
		if self.__class__ is other.__class__:
			return self._value_ <= other._value_
		return NotImplemented
	def __lt__(self, other):
		if self.__class__ is other.__class__:
			return self._value_ < other._value_
		return NotImplemented

AutoNumberedEnum = auto_enum('AutoNumberedEnum', (OrderedEnum,), {})

AutoIntEnum = auto_enum('AutoIntEnum', (IntEnum,), {})


#
#
# class APIStatus(AutoIntEnum):
#     Val1=()
#     """:type : AutoIntEnum"""
#     Val2=()
#     """:type : AutoIntEnum"""
#     Val3=()
#     """:type : AutoIntEnum"""
#     Val4=()
#     """:type : AutoIntEnum"""
#     Val5=()
#     """:type : AutoIntEnum"""
#     Val6=()
#     """:type : AutoIntEnum"""
#
#     Val1, Val2, Val3, Val4, Val5, Val6, Val7 = range(1, 8)
