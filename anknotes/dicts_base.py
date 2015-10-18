import collections
from addict import Dict
from anknotes.constants_standard import ANKNOTES
from anknotes.base import item_to_list, is_str, is_str_type, in_delimited_str, delete_keys, key_transform, str_capitalize, ank_prop, pad_digits, call, get_unique_strings
from anknotes import dicts_summary

class DictKey(object):
    _type_ = _name_ = _parent_ = _delimiter_ = None
    _default_name_='Root'
    _default_parent_=''
    _parent_dict_ = _self_dict_ = None

    def __init__(self, name=None, parent=None, type=None, self_dict=None, parent_dict=None, default_name=None, default_parent=None, delimiter=None):
        type = type or 'key'
        parent_dict = parent_dict or self_dict is not None and self_dict._parent_
        if parent_dict is not None:
            self._parent_dict_ = parent_dict
            if type == 'key':
                default_name = parent_dict.__class__.__name__
            else:
                base_key = getattr(parent_dict, '_key_')
                default_name = base_key.name
                default_parent = base_key.parent
            base_key = getattr(parent_dict, '_%s_' % type.lower())
            if name is None:
                name = base_key.name
                if parent is None:
                    parent = base_key.parent
            elif parent is None:
                parent = base_key.full
            if delimiter is None:
                delimiter = base_key.delimiter
        all_args = locals()
        for attr in 'name|parent|delimiter|default_name|default_parent|type|self_dict'.split('|'):
            val = all_args[attr]
            if val is None:
                continue
            if (attr == 'name' or attr == 'parent') and not is_str_type(val):
                str_val = str(val)
                if type == 'label' and str_val.isdigit():
                    val = str_val
                else:
                    raise TypeError("Cannot set %s %s from non string type <%s> %s" % (type.capitalize(), attr, val.__class__.__name__, str_val))
            setattr(self, '_%s_' % (attr), val)

    @property
    def type(self):
        return self._type_.capitalize() if self._type_ is not None else 'Key'

    @property
    def name(self):
        return self.call(self._name_, self._default_name_)

    @name.setter
    def name(self, value):
        self._name_ = value

    @property
    def parent(self):
        return self.call(self._parent_, '')

    @property
    def delimiter(self):
        return self._delimiter_ if self._delimiter_ is not None else '.'

    @property
    def full(self):
        return self.join()

    def call(self, value, default=None):
        if value is None:
            return default
        return call(value, self=self, dct=self._self_dict_, parent=self._parent_dict_)

    def join(self, delimiter=None):
        delimiter = delimiter or self.delimiter if self.parent and self.name else ''
        return self.parent + delimiter + self.name

    def __str__(self):
        return self.full

    def __repr__(self):
        return '<%s> %s: %s' % (self.__class__.__name__, self.type, self.full)

class DictAnk(Dict):
    _label_ = _key_ = _value_ = _parent_ = None
    _my_aggregates_ = _my_attrs_ = ''
    _mro_offset_ = 0
    _default_ = _default_value_ = _override_default_ = None
    _cls_missing_attrs_ = False

    def __init__(self, *a, **kw):
        def _copy_keys_from_parent_(kw):
            def init(suffix=''):
                k0, k1 = keys[0] + suffix, keys[1] + suffix
                if k1 not in kw and k0 in kw and kw[k0]:
                    kw[k1] = kw[k0]

            # Begin _copy_keys_from_parent_():
            keys=['key', 'label']
            for k0 in keys:
                if k0 in kw and is_str_type(kw[k0]):
                    kw[k0+'_name'] = kw[k0]
                    del kw[k0]
            init(), init('_name')
            for k in keys:
                kv, kn, kp = self._get_kwargs_(kw, k, '%s_name' % k, ['%s_parent' % k, 'parent_%s' % k])
                self._my_attrs_ += '|_%s_' % k
                kv = kv or DictKey(kn, kp, k, self, self._parent_)
                setattr(self, '_%s_' % k, kv)

        # Begin __init__():
        cls, a = self.__class__, list(a)
        self._my_attrs_ += '|_cls_missing_attrs_|_my_aggregates_|_default_|_default_value_|_override_default_|_mro_offset_|_parent_'
        mro = self._get_arg_(a, int, 'mro', kw)
        self._parent_=self._get_arg_(a, DictAnk)
        _copy_keys_from_parent_(kw)
        override_default = self._get_kwarg_(kw, 'override_default', True)
        delete, initialize = self._get_kwargs_(kw, 'delete', 'initialize')
        if self._default_:
            self._my_attrs_ += '|' + self._default_
            self._override_default_ = override_default if self._override_default_ is not None else None
        super(cls.mro()[mro], self).__init__(mro+1, *a, **kw)
        if delete:
            self.delete_keys(delete)
        if initialize:
            self.initialize_keys(initialize)

    prop = ank_prop

    @property
    def key(self):
        return self._key_

    @property
    def label(self):
        return self._label_

    @property
    def _label_name_(self):
        return self.label.name if self.label else ''

    @_label_name_.setter
    def _label_name_(self, value):
        if not self.label:
            self._label_ = DictKey(value, type='label', self_dict=self)
        else:
            self._label_.name = value

    @property
    def default(self):
        return self.getDefault()

    @default.setter
    def default(self, value):
        return self.setDefault(value)

    def getDefaultAttr(self):
        if self._default_ is None:
            return None
        if self._is_obj_attr_(self._default_):
            val = getattr(self, self._default_)
            return self._default_value_ if val is None else val
        return self._default_value_

    def _getDefault(self, allow_override=True):
        if self._default_ is None:
            return None
        if allow_override and self._override_default_ and self.default_override:
            return self.default_override
        return self.getDefaultAttr()

    def setDefault(self, value, set_override=True):
        if self._default_ is None:
            return
        if set_override is not None:
            self._override_default_ = set_override
        setattr(self, self._default_, value)

    def getDefaultOrValue(self):
        if self._default_ is None:
            return self.getValueAttr()
        return self.getDefault()

    getDefault = _getDefault
    getSecondary = getDefault
    setSecondary = setDefault

    @property
    def default_override(self):
        return None

    @property
    def has_value(self):
        return self._is_my_attr_('_value_')

    def getValueAttr(self):
        if self.has_value:
            return self._value_
        return None

    def setValueAttr(self, value):
        self._value_ = value

    def getValue(self):
        if self.has_value:
            return self._value_
        return self.getDefault()

    def setValue(self, value):
        if self.has_value:
            self._value_ = value
        else:
            self.setDefault(value)

    val = property(getValue, setValue, None, 'Property for `val` attribute')
    get = default

    def _is_my_attr_(self, key):
        return in_delimited_str(key, self._my_attrs_ + '|_my_attrs_')

    def _is_my_aggregate_(self, key):
        return in_delimited_str(key, self._my_aggregates_)

    @staticmethod
    def _is_protected_(key):
        return (key.startswith('_') and key.endswith('_')) or key.startswith('__')

    def _new_instance_(self, *a, **kw):
        return self.__class__.mro()[self._mro_offset_](*a, **kw)

    def __hash__(self, return_items=False):
        def _items_to_hash_():
            def _item_hash_(item):
                if isinstance(item, DictAnk):
                    return item.__hash__(True)
                return (item,)

            # Begin _items_to_hash_():
            base_hash = [self.__class__.__name__, self.key.full, self.label.full, self.default, self.val]
            for i, item in enumerate(base_hash):
                item_hash = _item_hash_(item)
                base_hash[i] = item_hash[0] if len(item_hash) is 1 else item_hash
            hashes=[tuple(base_hash)]
            for key in self:
                item = self[key]
                key_hash = _item_hash_(key)
                item_hash = _item_hash_(item)
                hashes.append((key_hash, item_hash))
            return tuple(hashes)

        # Begin __hash__()
        items = _items_to_hash_()
        return items if return_items or items is None else hash(items)

    def print_banner(self, title):
        print self.make_banner(title)

    @staticmethod
    def make_banner(title):
        return '\n'.join(["-" * max(ANKNOTES.FORMATTING.COUNTER_BANNER_MINIMUM, len(title) + 5), title,
                          "-" * max(ANKNOTES.FORMATTING.COUNTER_BANNER_MINIMUM, len(title) + 5)])

    def delete_keys(self, keys_to_delete):
        delete_keys(self, keys_to_delete)

    def _get_kwargs_(self, kwargs, *a, **kw):
        return [self._get_kwarg_(kwargs, key, **kw) for key in a]

    def _get_kwarg_(self, kwargs, keys, default=None, replace_none_type=True, **kw):
        retval = replace_none_type and default or None
        for key in item_to_list(keys):
            key = self._key_transform_(key, kwargs)
            if key not in kwargs:
                continue
            val = kwargs[key]
            retval = val or retval
            del kwargs[key]
        return retval

    def reset(self, keys_to_keep=None):
        if keys_to_keep is None:
            keys_to_keep = self._my_aggregates_.lower().split("|")
        self.delete_keys([key for key in self if key.lower() not in keys_to_keep])

    _summarize_lines_ = dicts_summary._summarize_lines_
    _get_summary_ = dicts_summary._get_summary_

    def __repr__(self, **kw):
        return self._summarize_lines_(self._get_summary_(), **kw)

    def increment(self, val, negate=False):
        new_value = self.__add__(val, increment=True)
        self.setDefault(new_value)
        return self

    def __simplify__(self, increment=False):
        if increment:
            return self.__simplify_increment__()
        return self.getDefault()

    def __simplify_increment__(self): return self.getDefaultAttr()
    def __coerce__(self, y): return (self.__simplify__(), y)
    def __bool__(self): return bool(self.__simplify__()) or bool(self.items())
    def __truth__(self): return self.__bool__()
    __nonzero__ = __truth__

    def __add__(self, y, increment=False): return self.__simplify__(increment) + y
    def __radd__(self, y): return y + self.__simplify__()
    def __iadd__(self, y): return self.increment(y)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return exc_type is None

    def __setattr__(self, key, value):
        key_adj = self._key_transform_(key)
        if self._is_protected_(key):
            if not self._is_my_attr_(key):
                raise AttributeError("Attempted to set protected built-in item %s on %s\n\nMy Attrs: %s" % (key_adj, self.__class__.__name__, self._my_attrs_))
            else:
                super(Dict, self).__setattr__(key_adj, value)
        elif self._default_ and is_str(key_adj) and (key_adj.lower() == 'default' or key_adj.lower() == self._default_.strip('_')):
            self.setDefault(value)
        elif key_adj in self:
            attr_val = getattr(self, key_adj)
            if self._default_ and isinstance(attr_val, self.__class__):
                attr_val.setSecondary(value.getDefaultAttr() if isinstance(value, self.__class__) else value)
            else:
                super(self.__class__.mro()[-4], self).__setattr__(key_adj, value)
        else:
            if self._cls_missing_attrs_:
                self[key_adj] = self._new_instance_(self, key_name=key_adj, override_default=True)
                self[key_adj].setValue(value)
            else:
                super(self.__class__.mro()[-4], self).__setitem__(key_adj, value)

    def __setitem__(self, name, value):
        super(self.__class__.mro()[-4], self).__setitem__(name, value)

    def __getitem__(self, key):
        key_adj = self._key_transform_all_(key)
        if self._default_ and is_str(key_adj) and (key_adj.lower() == 'default' or key_adj.lower() == self._default_.strip('_')):
            return self.getDefault()
        if key_adj not in self:
            if key_adj in dir(self.__class__):
                return super(self.__class__.mro()[-3], self).__getattr__(key_adj)
            elif self._is_protected_(key):
                try:
                    return None if self._is_my_attr_(key) else super(Dict, self).__getattr__(key)
                except KeyError:
                    raise KeyError("Could not find protected built-in item " + key)
            self[key_adj] = self._new_instance_(self, key_name=key_adj, override_default=True)
        try:
            return super(self.__class__.mro()[-4], self).__getitem__(key_adj)
        except TypeError:
            return "<null>"

