import collections
from anknotes.imports import in_anki
from anknotes.base import item_to_list, is_str, is_str_type, in_delimited_str, delete_keys, key_transform, str_capitalize, ank_prop, pad_digits
from anknotes.dicts_base import DictAnk

mw = None

class DictCaseInsensitive(DictAnk):
    def __init__(self, *a, **kw):
        a, cls, mro = list(a), self.__class__, self._get_arg_(a, int, 'mro', kw)
        super(cls.mro()[mro], self).__init__(mro+1, *a, **kw)

    def _key_transform_(self, key, keys=None, all=False, attrs=False):
        mapping = keys or self
        if attrs:
            mapping, all = dir(mapping.__class__), False
        return key_transform(mapping, key, all=all)

class DictNumeric(DictCaseInsensitive):
    _default_value_ = 0
    def __init__(self, *a, **kw):
        a, cls, mro = list(a), self.__class__, self._get_arg_(a, int, 'mro', kw)
        super(cls.mro()[mro], self).__init__(mro+1, *a, **kw)

    def _convert_(self, val=None):
        def _check_(val):
            return val if isinstance(val, (int, long, float)) else None
        value = val is not None
        if not value:
            val = self
        if _check_(val):
            return val
        if isinstance(val, (DictNumeric)):
            return _check_(value and val.getDefault() or val.getDefaultAttr()) or _check_(val.getValueAttr()) or self._default_value_
        return self._default_value_

    @property
    def sum(self):
        def_val = self._convert_()
        sum = not self._override_default_ and def_val or 0
        for key in self:
            if not self._is_my_aggregate_(key):
                sum += self._convert_(self[key])
        if sum == int(sum):
            return int(sum)
        return sum

    def increment(self, val=1, negate=False, **kwargs):
        new_count = self.__add__(val, negate, True)
        self.setDefault(new_count)
        return self

    step = increment
    def __bool__(self): return self.__simplify__() > 0
    def __div__(self, y): return self.__simplify__() / y
    def __rdiv__(self, y): return 1 / self.__div__(y)
    __truediv__ = __div__

    def __mul__(self, y): return y * self.__simplify__()
    __rmul__ = __mul__

    def __add__(self, y, negate=False, increment=False): return self.__simplify__(increment) + y * (-1 if negate else 1)
    def __sub__ (self, y): return self.__add__(y, True)
    def __rsub__ (self, y): return self.__sub__(y) * -1
    def __isub__ (self, y): return self.increment(y, True)

    default_override = sum


class DictString(DictCaseInsensitive):
    _default_ = '_label_name_'
    _default_value_ = ''
    _value_ = ''

    def __init__(self, *a, **kw):
        a, cls, mro = list(a), self.__class__, self._get_arg_(a, int, 'mro', kw)
        cls_mro = cls.mro()[mro]
        self._my_attrs_ += '|_value_|_summarize_dont_print_default_'
        super(cls_mro, self).__init__(mro+1, *a, **kw)
        cls_mro.setSecondary = cls_mro.setValueAttr
        cls_mro.getSecondary = cls_mro.getValueAttr

    def getDefault(self):
        lbl = str_capitalize(self.label.full)
        return lbl[:1].lower() + lbl[1:]

class DictSettings(DictString):
    _cls_missing_attrs_ = True
    def __init__(self, *a, **kw):
        a, cls, mro = list(a), self.__class__, self._get_arg_(a, int, 'mro', kw)
        super(cls.mro()[mro], self).__init__(mro+1, *a, **kw)

    @property
    def mw(self):
        global mw
        if mw is None and in_anki():
            from aqt import mw
        return mw

    def fetch(self, default=''):
        mw = self.mw
        if not mw:
            raise Exception("Attempted to fetch from DictSettings without mw instance")
        default_value = self.val
        if default_value is None:
            default_value = default
        return mw.col.conf.get(self.getDefault(), default_value)

    def save(self, value):
        mw = self.mw
        if not mw:
            raise Exception("Attempted to save from DictSettings without mw instance")
        mw.col.conf[self.getDefault()] = value
        mw.col.setMod()
        mw.col.save()
        return True