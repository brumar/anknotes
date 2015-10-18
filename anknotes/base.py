# -*- coding: utf-8 -*-
import re
from fnmatch import fnmatch
import inspect
from collections import defaultdict, Iterable
from bs4 import UnicodeDammit
import string
from datetime import datetime


### Anknotes Imports
from anknotes.imports import in_anki

### Anki Imports
if in_anki():
    from aqt import mw

class SafeDict(defaultdict):
    def __init__(self, *a, **kw):
        for i, arg in enumerate(a):
            if arg is None:
                raise TypeError("SafeDict arg %d is NoneType" % (i + 1))
        dct = dict(*a, **kw)
        super(self.__class__, self).__init__(self.__missing__, dct)

    def __getitem__(self, key):
        item = super(self.__class__, self).__getitem__(key)
        if isinstance(item, dict):
            item = SafeDict(item)
        return item

    def __missing__(self, key):
        return '{' + key + '}'

def decode(str_, is_html=False, errors='strict'):
    if isinstance(str_, unicode):
        return str_
    if isinstance(str_, str):
        return UnicodeDammit(str_, ['utf-8'], is_html=is_html).unicode_markup
    return unicode(str_, 'utf-8', errors)

def decode_html(str_):
    return decode(str_, True)

def encode(str_):
    if isinstance(str_, unicode):
        return str_.encode('utf-8')
    return str_

def is_str(str_):
    return str_ and is_str_type(str_)

def is_str_type(str_):
    return isinstance(str_, (str, unicode))

def is_seq_type(*a):
    for item in a:
        if not isinstance(item, Iterable) or not hasattr(item, '__iter__'):
            return False
    return True

def is_dict_type(*a):
    for item in a:
        if not isinstance(item, dict) or hasattr(item, '__dict__'):
            return False
    return True

def get_unique_strings(*a):
    lst=[]
    items=[]
    if a and isinstance(a[0], dict):
        lst = a[0].copy()
        a = a[0].items()
    else:
        a = enumerate(a)
    for key, str_ in sorted(a):
        if isinstance(str_, list):
            str_, attr = str_
            str_ = getattr(str_, attr, None)
        if not str_ or str_ in lst or str_ in items:
            if isinstance(lst, list):
                lst.append('')
            else:
                lst[key] = ''
            continue
        items.append(str_)
        str_ = str(str_)
        if isinstance(lst, list):
            lst.append(str_)
        else:
            lst[key] = str_
    return lst

def call(func, *a, **kw):
    if not callable(func):
        return func
    spec=inspect.getargspec(func)
    if not spec.varargs:
        a = a[:len(spec.args)]
    if not spec.keywords:
        kw = {key:value for key, value in kw.items() if key in spec.args}
    return func(*a, **kw)

def fmt(str_, recursion=None, *a, **kw):
    """
    :type str_: str | unicode
    :type recursion : int | dict | list
    :rtype: str | unicode
    """
    if not isinstance(recursion, int):
        if recursion is not None:
            a = [recursion] + list(a)
        recursion = 1
    dct = SafeDict(*a, **kw)
    str_ = string.Formatter().vformat(str_, [], dct)
    if recursion <= 0:
        return str_
    return fmt(str_, recursion-1, *a, **kw)

def pad_digits(*a, **kw):
    conv = []
    for str_ in a:
        if isinstance(str_, int):
            str_ = str(str_)
        if not is_str_type(str_):
            conv.append('')
        else:
            conv.append(str_.rjust(3) if str_.isdigit() else str_)
    if len(conv) is 1:
        return conv[0]
    return conv

def str_safe(str_, prefix=''):
    repr_ = str_.__repr__()
    try:
        str_ = str(prefix + repr_)
    except Exception:
        str_ = str(prefix + encode(repr_, errors='replace'))
    return str_

def str_split_case(str_, ignore_underscore=False):
    words=[]
    word=''
    for chr in str_:
        last_chr = word[-1:]
        if chr.isupper() and (last_chr.islower() or (ignore_underscore and last_chr is '_')):
            words.append(word)
            word = ''
        word += chr
    return words + [word]

def str_capitalize(str_, phrase_delimiter='.', word_delimiter='_'):
    phrases = str_.split(phrase_delimiter)
    return ''.join(''.join([word.capitalize() for word in phrase.split(word_delimiter)]) for phrase in phrases)

def in_delimited_str(key, str_, chr='|', case_insensitive=True):
    if case_insensitive:
        key = key.lower()
        str_ = str_.lower()
    return key in str_.strip(chr).split(chr)

def print_safe(str_, prefix=''):
    print str_safe(str_, prefix)

def item_to_list(item, list_from_unknown=True, chrs='', split_chr='|'):
    if is_seq_type(item):
        return list(item)
    if isinstance(item, dict):
        return [y for x in item.items() for y in x]
    if is_str(item):
        for c in chrs:
            item = item.replace(c, split_chr or ' ')
        return item.split(split_chr)
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
            return index + 1
    return 0

def get_default_value(cls, default=None):
    if default is not None:
        return default
    if cls is str or cls is unicode:
        return ''
    elif cls is int:
        return 0
    elif cls is bool:
        return False
    return None

def key_transform(mapping, key, all=False):
    key_lower = key.lower()
    match = [k for k in (mapping if isinstance(mapping, Iterable) and not all else dir(mapping)) if k.lower() == key_lower]
    return match and match[0] or key

def delete_keys(mapping, keys_to_delete):
    if not isinstance(keys_to_delete, list):
        keys_to_delete = item_to_list(keys_to_delete, chrs=' *,')
    for key in keys_to_delete:
        key = key_transform(mapping, key)
        if key in mapping:
            del mapping[key]

def ank_prop(self, keys, fget=None, fset=None, fdel=None, doc=None):
    for key in list(keys):
        all_args=locals()
        args = {}
        try:
            property_ = getattr(self.__class__, key)
        except AttributeError:
            property_ = property()

        for v in ['fget', 'fset', 'fdel']:
            args[v] = all_args[v]
            if not args[v]:
                args[v] = getattr(property_, v)
            if is_str(args[v]):
                args[v] = getattr(self.__class__, args[v])
            if isinstance(args[v], property):
                args[v] = getattr(args[v], v)
        if not doc:
            doc = property_.__doc__
        if not doc:
            doc = fget.__doc__
        args['doc'] = doc
        property_ = property(**args)
        setattr(self.__class__, key, property_)

def get_friendly_interval_string(lastImport):
    if not lastImport:
        return ""
    from anknotes.constants import ANKNOTES
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

