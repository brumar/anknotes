import os
import sys
from anknotes.constants_standard import ANKNOTES
from anknotes.base import item_to_list, item_to_set, is_str
from anknotes.dicts import DictNumeric, DictCaseInsensitive
from anknotes.dicts_base import DictKey

class Counter(DictNumeric):
    _override_default_ = False
    _default_ = '_count_'
    _count_ = 0
    _my_aggregates_ = 'max|max_allowed'
    _my_attrs_ = '_count_'

    def __init__(self, *a, **kw):
        a, cls, mro = list(a), self.__class__, self._get_arg_(a, int, 'mro', kw)
        super(cls.mro()[mro], self).__init__(mro+1, *a, **kw)
        self.prop(['count', 'cnt'], 'default')
        cls.default_override = cls.sum

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
        a, cls, mro = list(a), self.__class__, self._get_arg_(a, int, 'mro', kw)
        super(cls.mro()[mro], self).__init__(mro+1, *a, **kw)

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
        return self.count

    def aggregateSummary(self, includeHeader=True):
        aggs = '!max|!+max_allowed|total|+handled|++success|+++completed|+++queued|++delayed'
        counts = self._get_summary_(header_only=True) if includeHeader else []
        parents, last_level = [], 1
        for key_code in aggs.split('|'):
            override_default = key_code[0] is not '!'
            counts += [DictCaseInsensitive(marker='*' if override_default else ' ', child_values={}, children=['<aggregate>'])]
            if not override_default:
                key_code = key_code[1:]
            key = key_code.lstrip('+')
            counts.level, counts.value = len(key_code) - len(key) + 1, getattr(self, key)
            counts.class_name = type(counts.value)
            if counts.class_name is not int:
                counts.value = counts.value.getDefault()
            parent_lbl = '.'.join(parents)
            counts.key, counts.label = DictKey(key, parent_lbl), DictKey(key, parent_lbl, 'label')
            if counts.level < last_level:
                del parents[-1]
            elif counts.level > last_level:
                parents.append(key)
            last_level = counts.level
        return self._summarize_lines_(counts, includeHeader)

    def fullSummary(self, title='Evernote Counter'):
        return '\n'.join(
            [self.make_banner(title + ": Summary"),
             self.__repr__(),
             ' ',
             self.make_banner(title + ": Aggregates"),
             self.aggregateSummary(False)])
