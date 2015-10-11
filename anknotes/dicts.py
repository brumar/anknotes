import os
import sys
from pprint import pprint
from addict import Dict
from anknotes.constants import *
from anknotes.base import item_to_list, item_to_set 

class DictCaseInsensitive(Dict):
    def print_banner(self, title):
        print self.make_banner(title)

    @staticmethod
    def make_banner(title):
        return '\n'.join(["-" * max(ANKNOTES.FORMATTING.COUNTER_BANNER_MINIMUM, len(title) + 5), title,
                          "-" * max(ANKNOTES.FORMATTING.COUNTER_BANNER_MINIMUM, len(title) + 5)])

    def _process_kwarg_(self, kwargs, key, default=None, replace_none_type=True):
        key = self._key_transform_(key, kwargs.keys())
        if key not in kwargs:
            return default
        val = kwargs[key]
        if val is None and replace_none_type:
            val = default
        del kwargs[key]
        return val

    def _key_transform_(self, key, keys=None):
        if keys is None:
            keys = self.keys()
        for k in keys:
            if k.lower() == key.lower():
                return k
        return key

    def __init__(self, *args, **kwargs):
        # if not is_str_type(label): raise TypeError("Cannot create counter label from non-string type: " + str(label))
        # print "kwargs: %s" % (str(kwargs))
        lbl = self._process_kwarg_(kwargs, 'label', 'root')
        parent_lbl = self._process_kwarg_(kwargs, 'parent_label', '')
        delete = self._process_kwarg_(kwargs, 'delete', None)
        # print "lbl: %s\nkwargs: %s" % (lbl, str(kwargs))
        self._label_ = lbl
        self._parent_label_ = parent_lbl
        super(self.__class__, self).__init__(*args, **kwargs)
        if delete:
            self.delete_keys(delete)

    def reset(self, keys_to_keep=None):
        if keys_to_keep is None:
            keys_to_keep = self._my_aggregates_.lower().split("|")
        for key in self.keys():
            if key.lower() not in keys_to_keep:
                del self[key]

    _label_ = ''
    _parent_label_ = ''
    _my_aggregates_ = ''
    _my_attrs_ = '_label_|_parent_label_|_my_aggregates_'

    @property
    def label(self): return self._label_

    @property
    def parent_label(self): return self._parent_label_

    @property
    def full_label(self): return self.parent_label + ('.' if self.parent_label else '') + self.label

    def delete_keys(self, keys_to_delete):
        keys = self.keys()
        if not isinstance(keys_to_delete, list):
            keys_to_delete = item_to_list(keys_to_delete, chrs=' *,')
        for key in keys_to_delete:
            key = self._key_transform_(key)
            if key in keys:
                del self[key]

    @staticmethod
    def _is_protected_(key):
        return (key.startswith('_') and key.endswith('_')) or key.startswith('__')

    def __setattr__(self, key, value):
        key_adj = self._key_transform_(key)
        if self._is_protected_(key):
            if key.lower() not in self._my_attrs_.lower().split('|'):
                raise AttributeError("Attempted to set protected item %s on %s" % (key, self.__class__.__name__))
            else:
                super(Dict, self).__setattr__(key, value)
            # elif key == 'Count':
            # self.setCount(value)
            # # super(CaseInsensitiveDict, self).__setattr__(key, value)
            # setattr(self, 'Count', value)
        elif hasattr(self, key):
            # print "Setting key " + key + ' value... to ' + str(value)
            self[key_adj] = value
        else:
            print "Setting attr %s to type %s value %s" % (key_adj, type(value), value)
            super(Dict, self).__setitem__(key_adj, value)

    def __setitem__(self, name, value):
        # print "Setting item %s to type %s value %s" % (name, type(value), value)
        super(Dict, self).__setitem__(name, value)

    def __getitem__(self, key):
        adjkey = self._key_transform_(key)
        if adjkey not in self:
            if self._is_protected_(key):
                if key.lower() not in self._my_attrs_.lower().split('|'):
                    try:
                        return super(Dict, self).__getattr__(key.lower())
                    except Exception:
                        raise (KeyError("Could not find protected item " + key))
                return super(DictCaseInsensitive, self).__getattr__(key.lower())
            # print "Creating missing item: " + self.parent_label + ('.' if self.parent_label else '') + self.label  + ' -> ' + repr(adjkey)
            self[adjkey] = DictCaseInsensitive()
            self[adjkey]._label_ = adjkey
            self[adjkey]._parent_label_ = self.full_label
        try:
            return super(DictCaseInsensitive, self).__getitem__(adjkey)
        except TypeError:
            return "<null>"