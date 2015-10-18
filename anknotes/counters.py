import os
import sys
from anknotes.constants_standard import ANKNOTES
from anknotes.base import item_to_list, item_to_set, is_str
from anknotes.dicts import DictNumeric
from anknotes.dicts_base import DictKey

class Counter(DictNumeric):
    _override_default_ = False
    _default_ = '_count_'
    _count_ = 0
    _my_aggregates_ = 'max|max_allowed'
    _my_attrs_ = '_count_'

    def __init__(self, *a, **kw):
        a = list(a)
        mro = self._get_arg_(a, int, 'mro', kw)
        cls = self.__class__
        # # self.log_init('Cnt', mro, a, kw)
        super(cls.mro()[mro], self).__init__(mro+1, *a, **kw)
        self.prop(['count', 'cnt'], 'default')
        self.__class__.default_override = self.__class__.sum

    def setCount(self, value):
        self._count_ = value

    def getCount(self):
        return self._count_

    def getDefault(self, allow_override=True):
        if allow_override and self._override_default_:
            return self.default_override
        return self.sum


class EvernoteCounter(Counter):
    _mro_offset_ = 1
    _default_override_ = True

    def __init__(self, *a, **kw):
        a = list(a)
        mro = self._get_arg_(a, int, 'mro', kw)
        # # self.log_init('ENCnt', mro, a, kw)
        super(self.__class__.mro()[mro], self).__init__(mro+1, *a, **kw)

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
        return self.count  # - self.max - self.max_allowed

    def aggregateSummary(self, includeHeader=True):
        aggs = '!max|!+max_allowed|total|+handled|++success|+++completed|+++queued|++delayed'
        counts = self._get_summary_(header_only=True) if includeHeader else []
        parents = []
        last_level = 1
        for key_code in aggs.split('|'):
            override_default = key_code[0] is not '!'
            if not override_default:
                key_code = key_code[1:]
            key = key_code.lstrip('+')
            level = len(key_code) - len(key) + 1
            val = getattr(self, key)
            cls = type(val)
            if cls is not int:
                val = val.getDefault()
            parent_lbl = '.'.join(parents)
            keyd = DictKey(key, parent_lbl)
            labeld = DictKey(key, parent_lbl, type='label')
            counts += [dict(level=level, label=labeld, key=keyd, value=val, marker='*' if override_default else ' ', class_name=cls, child_values={}, children=['<aggregate>'])]
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
             self.aggregateSummary(False)])
