# -*- coding: utf-8 -*-
import sys
import re
from fnmatch import fnmatch
import inspect
from addict import Dict
from collections import defaultdict
import string
from datetime import datetime

### Check if in Anki
inAnki = 'anki' in sys.modules

### Anknotes Imports
from anknotes.constants import *

if inAnki:
    from aqt import mw
    # from aqt.qt import QIcon, QPixmap, QPushButton, QMessageBox
    # from anknotes.evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode, EDAMUserException, \
    #     EDAMNotFoundException

class SafeDict(defaultdict):
    def __init__(self, *a, **kw):
        dct = Dict(*a, **kw)
        dct = dct.to_dict()
        super(self.__class__, self).__init__(self.__missing__, dct)

    def __getitem__(self, key):
        item = super(self.__class__, self).__getitem__(key)
        if isinstance(item, dict):
            item = SafeDict(item)
        return item

    def __missing__(self, key):
        return '{' + key + '}'

def is_str_type(str_):
    return str_ and (isinstance(str_, str) or isinstance(str_, unicode))

def fmt(str_, recursion=None, *a, **kw):
    """
    :type str_: str | unicode
    :type recursion : int | dict | list
    :rtype: str | unicode
    """
    if not isinstance(recursion, int):
        a = [recursion] + list(a)
        recursion = 1
    dct = SafeDict(*a, **kw)
    str_ = string.Formatter().vformat(str_, [], dct)
    if recursion <= 0:
        return str_
    return fmt(str_, recursion-1, *a, **kw)

def str_safe(str_, prefix=''):
    try:
        str_ = str((prefix + str_.__repr__()))
    except Exception:
        str_ = str((prefix + str_.__repr__().encode('utf8', 'replace')))
    return str_


def print_safe(str_, prefix=''):
    print str_safe(str_, prefix)

def item_to_list(item, list_from_unknown=True, chrs=''):
    if isinstance(item, list):
        return item
    if isinstance(item, dict):
        lst = []
        for key, value in item.items():
            lst += [key, value]
        return lst
    if is_str_type(item):
        for c in chrs:
            item = item.replace(c, '|')
        return item.split('|')
    if item is None:
        return []
    if list_from_unknown:
        return [item]
    return item

def item_to_set(item, **kwargs):
    if isinstance(item, set):
        return item
    item = item_to_list(item, **kwargs)
    if not isinstance(item, list):
        return item
    return set(item)

def matches_list(item, lst):
    item = item.lower()
    for index, value in enumerate(item_to_list(lst)):
        value = value.lower()
        if fnmatch(item, value) or fnmatch(item + 's', value):
            return index 
    return -1     
    
def get_friendly_interval_string(lastImport):
    if not lastImport:
        return ""
    td = (datetime.now() - datetime.strptime(lastImport, ANKNOTES.DATE_FORMAT))
    days = td.days
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 1:
        lastImportStr = "%d days" % td.days
    else:
        hours = round(hours)
        hours_str = '' if hours == 0 else ('1:%02d hr' % minutes) if hours == 1 else '%d Hours' % hours
        if days == 1:
            lastImportStr = "One Day%s" % ('' if hours == 0 else ', ' + hours_str)
        elif hours > 0:
            lastImportStr = hours_str
        else:
            lastImportStr = "%d:%02d min" % (minutes, seconds)
    return lastImportStr


def clean_evernote_css(str_):
    remove_style_attrs = '-webkit-text-size-adjust: auto|-webkit-text-stroke-width: 0px|background-color: rgb(255, 255, 255)|color: rgb(0, 0, 0)|font-family: Tahoma|font-size: medium;|font-style: normal|font-variant: normal|font-weight: normal|letter-spacing: normal|orphans: 2|text-align: -webkit-auto|text-indent: 0px|text-transform: none|white-space: normal|widows: 2|word-spacing: 0px|word-wrap: break-word|-webkit-nbsp-mode: space|-webkit-line-break: after-white-space'.replace(
        '(', '\\(').replace(')', '\\)')
    # 'margin: 0px; padding: 0px 0px 0px 40px; '
    return re.sub(r' ?(%s);? ?' % remove_style_attrs, '', str_).replace(' style=""', '')


def caller_names(return_string=True, simplify=True):
    return [c.Base if return_string else c for c in [__caller_name(i, simplify) for i in range(0, 20)] if
            c and c.Base]


class CallerInfo:
    Class = []
    Module = []
    Outer = []
    Name = ""
    simplify = True
    __keywords_exclude = ['pydevd', 'logging', 'base', '__caller_name', 'stopwatch', 'process_args']
    __keywords_strip = ['__maxin__', 'anknotes', '<module>']
    __outer = []
    filtered = True

    @property
    def __trace(self):
        return self.Module + self.Outer + self.Class + [self.Name]

    @property
    def Trace(self):
        t = self.__strip(self.__trace)
        return t if not self.filtered or not [e for e in self.__keywords_exclude if e in t] else []

    @property
    def Base(self):
        return '.'.join(self.__strip(self.Module + self.Class + [self.Name])) if self.Trace else ''

    @property
    def Full(self):
        return '.'.join(self.Trace)

    def __strip(self, lst):
        return [t for t in lst if t and t not in self.__keywords_strip]

    def __init__(self, parentframe=None):
        """

        :rtype : CallerInfo
        """
        if not parentframe:
            return
        self.Class = parentframe.f_locals['self'].__class__.__name__.split(
            '.') if 'self' in parentframe.f_locals else []
        module = inspect.getmodule(parentframe)
        self.Module = module.__name__.split('.') if module else []
        self.Name = parentframe.f_code.co_name if parentframe.f_code.co_name is not '<module>' else ''
        self.__outer = [[f[1], f[3]] for f in inspect.getouterframes(parentframe) if f]
        self.__outer.reverse()
        self.Outer = [f[1] for f in self.__outer if
                      f and f[1] and not [exclude for exclude in self.__keywords_exclude + [self.Name] if
                                          exclude in f[0] or exclude in f[1]]]
        del parentframe


def create_log_filename(str_):
    if str_ is None:
        return ""
    str_ = str_.replace('.', '\\')
    str_ = re.sub(r"(^|\\)([^\\]+)\\\2(\b.|\\.|$)", r"\1\2\\", str_)
    str_ = re.sub(r"^\\*(.+?)\\*$", r"\1", str_)
    return str_


# @clockit
def caller_name(skip=None, simplify=True, return_string=False, return_filename=False):
    if skip is None:
        names = [__caller_name(i, simplify) for i in range(0, 20)]
    else:
        names = [__caller_name(skip, simplify=simplify)]
    for c in [c for c in names if c and c.Base]:
        return create_log_filename(c.Base) if return_filename else c.Base if return_string else c
    return "" if return_filename or return_string else None


def __caller_name(skip=0, simplify=True):
    """
    :rtype : CallerInfo
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return None
    parentframe = stack[start][0]
    c_info = CallerInfo(parentframe)
    del parentframe
    return c_info


