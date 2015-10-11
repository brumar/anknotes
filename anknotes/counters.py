import os
import sys
from pprint import pprint
from addict import Dict
from anknotes.constants import *
from anknotes.base import item_to_list, item_to_set, is_str_type
from anknotes.dicts import DictCaseInsensitive

class Counter(Dict):
    def print_banner(self, title):
        print self.make_banner(title)

    @staticmethod
    def make_banner(title):
        return '\n'.join(["-" * max(ANKNOTES.FORMATTING.COUNTER_BANNER_MINIMUM, len(title) + 5), title,
                          "-" * max(ANKNOTES.FORMATTING.COUNTER_BANNER_MINIMUM, len(title) + 5)])

    def __init__(self, *args, **kwargs):
        self.setCount(0)
        lbl = self._process_kwarg_(kwargs, 'label', 'root')
        parent_lbl = self._process_kwarg_(kwargs, 'parent_label', '')
        is_exclusive_sum = self._process_kwarg_(kwargs, 'is_exclusive_sum', True)
        if not is_str_type(lbl): raise TypeError("Cannot create counter label from non-string type: " + str(lbl))
        self._label_ = lbl
        self._parent_label_ = parent_lbl
        self._is_exclusive_sum_ = is_exclusive_sum
        super(Counter, self).__init__(*args, **kwargs)

    def _process_kwarg_(self, kwargs, key, default=None, replace_none_type=True):
        key = self._key_transform_(key, kwargs.keys())
        if key not in kwargs:
            return default
        val = kwargs[key]
        if val is None and replace_none_type:
            val = default
        del kwargs[key]
        return val

    def reset(self, keys_to_keep=None):
        if keys_to_keep is None:
            keys_to_keep = self._my_aggregates_.lower().split("|")
        for key in self.keys():
            if key.lower() not in keys_to_keep:
                del self[key]

    def _key_transform_(self, key, keys=None):
        if keys is None:
            keys = self.keys()
        for k in keys:
            if k.lower() == key.lower():
                return k
        return key

    @staticmethod
    def _is_protected_(key):
        return (key.startswith('_') and key.endswith('_')) or key.startswith('__')

    _count_ = 0
    _label_ = ''
    _parent_label_ = ''
    _is_exclusive_sum_ = False
    _my_aggregates_ = 'max|max_allowed'
    _my_attrs_ = '_count_|_is_exclusive_sum_|_label_|_parent_label_|_my_aggregates_'

    def getCount(self):
        if self._is_exclusive_sum_:
            return self.sum
        return self._count_

    def setCount(self, value):
        self._is_exclusive_sum_ = False
        self._count_ = value

    @property
    def label(self): return self._label_

    @property
    def parent_label(self): return self._parent_label_

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
            if key in self._my_aggregates_.split("|"):
                continue
            val = self[key]
            if isinstance(val, int):
                sum += val
            elif isinstance(val, Counter) or isinstance(val, EvernoteCounter):
                sum += val.getCount()
                # print 'sum: ' +  key + ': - ' + str(val) + ' ~ ' + str(sum)
        return sum

    def increment(self, val=1, negate=False, **kwargs):
        newCount = self.__sub__(val) if negate else self.__add__(val)
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

    def log(self, str_, method):
        from anknotes.logging import log as log_
        log_(str_, 'counters\\' + method)

    def __setattr__(self, key, value):
        key_adj = self._key_transform_(key)
        method = '__setattr__'
        if self._is_protected_(key):
            if key.lower() not in self._my_attrs_.lower().split('|'):
                raise AttributeError("Attempted to set protected item %s on %s" % (key, self.__class__.__name__))
            else:
                super(Dict, self).__setattr__(key, value)
        elif key == 'Count':
            self.setCount(value)
            # super(CaseInsensitiveDict, self).__setattr__(key, value)
            # setattr(self, 'Count', value)
        elif hasattr(self, key_adj):
            self.log("Setting key " + key + ' value... to ' + str(value), method); self[key_adj].setCount(value)
        else:
            print "Setting attr %s to type %s value %s" % (key_adj, type(value), value)
            super(Dict, self).__setitem__(key_adj, value)

    def __setitem__(self, name, value):
        # print "Setting item %s to type %s value %s" % (name, type(value), value)
        super(Dict, self).__setitem__(name, value)

    def _get_summary_(self, level=1, header_only=False):
        keys = self.keys()
        counts = [Dict(level=level, label=self.label, full_label=self.full_label, value=self.getCount(),
                       is_exclusive_sum=self._is_exclusive_sum_, class_name=self.__class__.__name__, children=keys)]
        if header_only:
            return counts
        for key in keys:
            # print "Summaryzing key %s: %s " % (key, type( self[key]))
            if key not in self._my_aggregates_.split("|"):
                counts += self[key]._get_summary_(level + 1)
        return counts

    def _summarize_lines_(self, summary, header=True):
        lines = []
        for i, item in enumerate(summary):
            exclusive_sum_marker = '*' if item.is_exclusive_sum and len(item.children) > 0 else ' '
            if i is 0 and header:
                lines.append(
                    "<%s%s:%s:%d>" % (exclusive_sum_marker.strip(), item.class_name, item.full_label, item.value))
                continue
            # str_ = '%s%d' % (exclusive_sum_marker, item.value)
            str_ = (' ' * (item.level * 2 - 1) + exclusive_sum_marker + item.label + ':').ljust(16 + item.level * 2)
            lines.append(str_ + ' ' + str(item.value).rjust(3) + exclusive_sum_marker)
        return '\n'.join(lines)

    def __repr__(self):
        return self._summarize_lines_(self._get_summary_())

    def __getitem__(self, key):
        adjkey = self._key_transform_(key)
        if key == 'Count':
            return self.getCount()
        if adjkey not in self.keys():
            if self._is_protected_(key):
                if key.lower() not in self._my_attrs_.lower().split('|'):
                    try:
                        return super(Dict, self).__getattr__(key.lower())
                    except Exception:
                        raise (KeyError("Could not find protected item " + key))
                return super(Counter, self).__getattr__(key.lower())
            # print "Creating missing item: " + self.parent_label + ('.' if self.parent_label else '') + self.label  + ' -> ' + repr(adjkey)
            self[adjkey] = Counter(label=adjkey, parent_label=self.full_label, is_exclusive_sum=True)
            # self[adjkey]._label_ = adjkey
            # self[adjkey]._parent_label_ = self.full_label
            self[adjkey]._is_exclusive_sum_ = True
        try:
            return super(Counter, self).__getitem__(adjkey)
        except TypeError:
            return "<null>"
            # print "Unexpected type of self in __getitem__: " + str(type(self))
            # raise TypeError
            # except Exception:
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
    def handled(self):
        return self.total - self.unhandled - self.error

    @property
    def total(self):
        return self.getCount()  # - self.max - self.max_allowed

    def aggregateSummary(self, includeHeader=True):
        aggs = '!max|!+max_allowed|total|+handled|++success|+++completed|+++queued|++delayed'
        counts = self._get_summary_(header_only=True) if includeHeader else []
        parents = []
        last_level = 1
        for key_code in aggs.split('|'):
            is_exclusive_sum = key_code[0] is not '!'
            if not is_exclusive_sum:
                key_code = key_code[1:]
            key = key_code.lstrip('+')
            level = len(key_code) - len(key) + 1
            val = self.__getattr__(key)
            cls = type(val)
            if cls is not int:
                val = val.getCount()
            parent_lbl = '.'.join(parents)
            full_label = parent_lbl + ('.' if parent_lbl else '') + key
            counts += [Dict(level=level, label=key, full_label=full_label, value=val, is_exclusive_sum=is_exclusive_sum,
                            class_name=cls, children=['<aggregate>'])]
            if level < last_level:
                del parents[-1]
            elif level > last_level:
                parents.append(key)
            last_level = level
        return self._summarize_lines_(counts, includeHeader)

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
    absolutely_unused_variable = os.system("cls")
    del absolutely_unused_variable
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
    Counts.max_allowed = -1
    Counts.print_banner("Evernote Counter: Summary")
    print (Counts)
    Counts.print_banner("Evernote Counter: Aggregates")
    print (Counts.aggregateSummary())

    Counts.reset()

    print Counts.fullSummary('Reset Counter')
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
