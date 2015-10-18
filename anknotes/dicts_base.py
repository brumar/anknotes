import collections
from addict import Dict
from anknotes.constants_standard import ANKNOTES
from anknotes.base import item_to_list, is_str, is_str_type, in_delimited_str, delete_keys, key_transform, str_capitalize, ank_prop, pad_digits, call


class DictKey(object):
    _type_=None
    _name_=None
    _parent_=None
    _delimiter_=None
    _default_name_='Root'
    _default_parent_=''
    _parent_dict_=None
    _self_dict_=None

    def __init__(self, name=None, parent=None, delimiter=None, type=None, default_name=None, default_parent=None, parent_dict=None, self_dict=None):
        if type is None:
            type = 'key'
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
    _label_ = None
    _key_ = None
    _value_ = None
    _parent_ = None
    _my_aggregates_ = ''
    _my_attrs_ = ''
    _mro_offset_ = 0
    _default_ = None
    _default_value_ = None
    _override_default_ = None
    _cls_missing_attrs_ = False

    def _copy_keys_from_parent_(self, kw):
        method = '_copy_keys_from_parent_'
        keys=['key', 'label']
        def_k = self.__class__.__name__
        def_pk = ''
        for k0 in keys:
            if k0 in kw and is_str_type(kw[k0]):
                kw[k0+'_name'] = kw[k0]
                del kw[k0]
        k0, k1 = keys[0], keys[1]
        if k1 not in kw and k0 in kw:
            kw[k1] = kw[k0]
        k0, k1 = k0 + '_name', k1 + '_name'
        if k1 not in kw and k0 in kw:
            kw[k1] = kw[k0]
        for k in keys:
            kn = self._process_kwarg_(kw, '%s_name' % k, None)
            self._my_attrs_ += '|_%s_' % k
            if k not in kw:
                if kn:
                    kw[k] = DictKey(kn, parent_dict=self._parent_, type=k, self_dict=self)
                else:
                    kw[k] = DictKey(parent_dict=self._parent_, type=k, self_dict=self)
            value = self._process_kwarg_(kw, k, None)
            setattr(self, '_%s_' % k, value)

    def __init__(self, *a, **kw):
        method = '__init__'
        cls = self.__class__
        a = list(a)
        self._my_attrs_ += '|_cls_missing_attrs_|_my_aggregates_|_default_|_default_value_|_override_default_|_mro_offset_|_parent_'
        mro = self._get_arg_(a, int, 'mro', kw)
        self._parent_=self._get_arg_(a, DictAnk)
        kwo = self._copy_keys_from_parent_(kw)
        self.log_init( 'DA', mro, a, kw)
        override_default = self._process_kwarg_(kw, 'override_default', True)
        delete = self._process_kwarg_(kw, 'delete', None)
        initialize = self._process_kwarg_(kw, 'initialize', None)
        if self._default_:
            if not self._is_my_attr_(self._default_):
                self._my_attrs_ += '|' + self._default_
            extra = ''
            if hasattr(self, self._default_):
                value = getattr(self, self._default_)
            else:
                value = self._default_value_
                extra = 'default value of '
            # self.log_action(method, 'Initializing', 'Default Attr', value, self._default_, extra=extra)
            self.setDefault(value)
            if self._override_default_ is not None:
                self._override_default_ = override_default
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

    def initialize_keys(self, *a):
        for keys in a:
            for k in item_to_list(keys):
                val = self[k]
        return val

    def set_keys(self, *a, **kw):
        self.__init__(*a, **kw)

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
            if val is None:
                val = self._default_value_
            return val
        return self._default_value_

    def _getDefault(self, allow_override=True):
        if self._default_ is None:
            return None
        if allow_override and self._override_default_ and self.default_override:
            return self.default_override
        return self.getDefaultAttr()

    def setDefault(self, value, reset_override=True):
        if self._default_ is None:
            return
        if reset_override:
            self._override_default_ = False
        setattr(self, self._default_, value)

    def getDefaultOrValue(self):
        if self._default_ is None:
            return self.getValueAttr()
        return self.getDefault()

    getDefault = _getDefault
    getSecondary = getDefault
    setSecondary = setDefault

    # default = property(getDefault, setDefault, None, 'Property for `default` attribute')

    @property
    def default_override(self):
        return None

    @property
    def has_value(self):
        return self._is_my_attr_('_value_')

    def _new_instance_(self, *a, **kw):
        return self.__class__.mro()[self._mro_offset_](*a, **kw)

    def _hash_str_single_(self):
        hash_str = self.__class__.__name__
        if self.key.full:
            hash_str += ': ' + self.key.full
        if self.label.full:
            hash_str += ': ' + self.label.full
        if self._default_ is not None:
            hash_str += ': [%s]' % self.default
        if self.has_value is not None:
            hash_str += ': {%s}' % self.val
        return hash_str

    def _hash_str_(self):
        hash_str = self._hash_str_single_()
        child_hashes=[]
        for key in self.keys():
            item = self[key]
            item_hash_str = str(key) + ": "
            if isinstance(item, self.__class__):
                item_hash_str += item._hash_str_()
            else:
                item_hash_str += str(item)
            child_hashes.append(item_hash_str)
        if child_hashes:
            hash_str += ': <%s>' % ', '.join(child_hashes)
        return hash_str

    def _hash_tuple_(self):
        hashes=[(self.__class__.__name__, self.key.full, self.label.full, self.default, self.val)]
        for key in self.keys():
            item = self[key]
            if not hasattr(key, '__hash__'):
                return None
            if isinstance(item, DictAnk):
                item_hash = item._hash_tuple_()
            elif hasattr(item, '__hash__'):
                item_hash = (item,)
            else:
                return None
            hashes.append(((key,), item_hash))
        return tuple(hashes)

    def __hash__(self):
        def c_mul(a, b):
            return eval(hex((long(a) * b) & 0xFFFFFFFFL)[:-1])

        def str_hash(val):
            if not val:
                return 0 # empty
            value = ord(val[0]) << 7
            for char in val:
                value = c_mul(1000003, value) ^ ord(char)
            value = value ^ len(val)
            if value == -1:
                value = -2
            return value

        def tuple_hash(val):
            value = 0x345678
            for item in val:
                value = c_mul(1000003, value) ^ hash(item)
            value = value ^ len(val)
            if value == -1:
                value = -2
            return value

        # Begin __hash__()
        return hash(self._hash_tuple_())




    # @property
    # def value(self):
        # return self.getValue()

    # @value.setter
    # def value(self, value):
        # self.setValue(value)

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

    def print_banner(self, title):
        print self.make_banner(title)

    @staticmethod
    def make_banner(title):
        return '\n'.join(["-" * max(ANKNOTES.FORMATTING.COUNTER_BANNER_MINIMUM, len(title) + 5), title,
                          "-" * max(ANKNOTES.FORMATTING.COUNTER_BANNER_MINIMUM, len(title) + 5)])

    def delete_keys(self, keys_to_delete):
        delete_keys(self, keys_to_delete)

    def _is_my_attr_(self, key):
        return in_delimited_str(key, self._my_attrs_ + '|_my_attrs_')

    def _is_my_aggregate_(self, key):
        return in_delimited_str(key, self._my_aggregates_)

    def _process_kwarg_(self, kwargs, key, default=None, replace_none_type=True):
        key = self._key_transform_(key, kwargs)
        if key not in kwargs:
            return default
        val = kwargs[key]
        if val is None and replace_none_type:
            val = default
        del kwargs[key]
        return val

    @staticmethod
    def _is_protected_(key):
        return (key.startswith('_') and key.endswith('_')) or key.startswith('__')

    def reset(self, keys_to_keep=None):
        if keys_to_keep is None:
            keys_to_keep = self._my_aggregates_.lower().split("|")
        for key in self.keys():
            if key.lower() not in keys_to_keep:
                del self[key]

    def _get_summary_(self, level=1, header_only=False):
        summary=dict(level=level, label=self.label, class_name=self.__class__.__name__, children=self.keys(), key=self.key, child_values={}, marker=' ')
        child_values={}
        if self._default_ is not None:
            summary['default'] = self.getDefault()
            if self._override_default_:
                summary['marker'] = '*'
            attr = self.getDefaultAttr()
            if attr != summary['default'] and attr != self._default_value_:
                summary['default_attr'] = attr
                summary['marker'] = '!' if self._override_default_ else '#'
        if self.has_value:
            summary['value'] = self.val
        summaries=[]
        if header_only:
            return [summary]
        for key in sorted(self.keys()):
            if self._is_my_aggregate_(key):
                continue
            item = self[key]
            if not isinstance(item, Dict):
                child_values[key] = item
            elif not header_only:
                summaries += item._get_summary_(level + 1)
        summary['child_values'] = child_values
        return [summary] + summaries

    def _summarize_lines_(self, summary, header=True, value_pad=3):
        def _summarize_child_lines_(pad_len):
            child_values = item['child_values']
            if not child_values:
                return ''
            child_lines = []
            pad = ' '*(pad_len*3-1)
            for child_key in sorted(child_values.keys()):
                child_value = str(child_values[child_key])
                if child_value.isdigit():
                    child_value = child_value.rjust(3)
                marker = '+'
                if child_key.startswith('#'):
                    marker = '#'
                    child_key = child_key[1:]
                child_lines.append(('%s%s%-15s' % (pad, marker, child_key + ':')).ljust(16+pad_len * 4 + 11) + child_value + '+')
            return '\n' + '\n'.join(child_lines)

        # Begin _summarize_lines_()
        lines = []
        for i, item in enumerate(summary):
            str_full_key = str_full_label = str_label = str_key = str_default_attr = str_value = str_default = str_default_full = ''
            key, label = item['key'], item['label']
            if key:
                str_full_key = key.join(' -> ')
                str_key = key.name
            if label:
                str_full_label = label.join(' -> ')
                str_label = label.name if label.name != str_key else ''
            if 'default_attr' in item and item['default_attr'] not in [str_key, str_label]:
                str_default_attr = str(item['default_attr'])
            if 'value' in item and item['value'] not in [str_key, str_label, str_default_attr]:
                str_value = str(item['value'])
            if str_full_label == str_full_key:
                str_full_label = ''
            if str_full_label:
                if str_full_key and key.parent == label.parent:
                    str_full_label = '* -> ' + label.name
                str_full_label='%sL[%s]' % (' | ' if str_full_key else '', str_full_label)
            if str_full_key:
                str_full_label += ': '
            if 'default' in item and not self._is_my_attr_('_summarize_dont_print_default_'):
                str_default = str_default_full = str(item['default'])
                if str_full_label and item['default'] != self._default_value_:
                    str_default_full = 'D[%s]' % str_default
                str_default_full += ':' if str_value and str_value != str_default else ''
                if str_default in [str_label, str_key]:
                    str_default = ''
            if str_label:
                str_label='%sL[%s]' % (' | ' if str_key else '', str_label)
            if str_key:
                str_label += ': '
            if i is 0 and header:
                pad_len = len(item['class_name'])
                if str_full_label:
                    pad_len += len(str_full_label) - len(str_label)
                lines.append("<%s%s:%s%s%s>" % (item['marker'].strip(), item['class_name'], str_full_key + str_full_label, str_default_full,
                             str_value if str_value != str_default else '') + _summarize_child_lines_(item['level']+1))
                continue
            str_ = ' ' * (item['level'] * 3 - 1) + item['marker'] + str_key + str_label
            child_str = _summarize_child_lines_(item['level']+1)
            str_ = str_.ljust(16 + item['level'] * 4 + 5)
            str_val_def = ' '*(value_pad+2)
            str_value, str_default, str_default_attr = pad_digits(str_value, str_default, str_default_attr)
            if str_value and str_default:
                str_val_def = (str_value + ':').ljust(value_pad+1) + ' ' + str_default
            elif str_default:
                str_val_def += str_default
            elif str_value:
                str_val_def = str_value.ljust(value_pad)
            if str_default_attr:
                str_val_def += ' ' + str_default_attr
            elif str_val_def.strip() == '':
                item['marker'] = ''
            lines.append(str_ + ' ' + str_val_def + item['marker'] + child_str)
        return '\n'.join(lines)

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
        method = '__setattr__'
        action = 'Setting ' + ( key + ' -> ' + key_adj if key != key_adj else '')
        if self._is_protected_(key):
            if not self._is_my_attr_(key):
                raise AttributeError("Attempted to set protected built-in item %s on %s\n\nMy Attrs: %s" % (key_adj, self.__class__.__name__, self._my_attrs_))
            else:
                log_value = value[:200] if is_str_type(value) else value
                if (key_adj == self._default_ or key_adj == '_default_') and value != self._default_value_:
                    self.log_action(method, action, 'My Attr', log_value, key_adj, 'super')
                super(Dict, self).__setattr__(key_adj, value)
        elif self._default_ and is_str(key_adj) and (key_adj.lower() == 'default' or key_adj.lower() == self._default_.strip('_')):
            if value != self._default_value_:
                self.log_action(method, action, 'Default', value, key_adj)
            self.setDefault(value)
        elif key_adj in self:
            attr_val = getattr(self, key_adj)
            if self._default_ and isinstance(attr_val, self.__class__):
                name = 'Secondary'
                if isinstance(value, self.__class__):
                    name += ' [%s]' % str(value)
                    value = value.getDefaultAttr()
                self.log_action(method, action, name, value, key_adj)
                attr_val.setSecondary(value)
            else:
                self.log_action(method, action, 'Attr', value, key_adj)
                super(self.__class__.mro()[-4], self).__setattr__(key_adj, value)
                # self[key_adj] = valuef
        else:
            self.log_action(method, 'Creating' + (' CLS' if self._cls_missing_attrs_ else ''), 'Missing Attr', value, key_adj, log_self=True)
            if self._cls_missing_attrs_:
                self[key_adj] = self._new_instance_(self, key_name=key_adj, override_default=True)
                self[key_adj].setValue(value)
            else:
                super(self.__class__.mro()[-4], self).__setitem__(key_adj, value)

    def __setitem__(self, name, value):
        method = '__setitem__'
        action = 'Setting'
        log_value = value[:200] if is_str_type(value) else value
        self.log_action(method, action, 'Item', log_value, name)
        super(self.__class__.mro()[-4], self).__setitem__(name, value)

    def __getitem__(self, key):
        key_adj = self._key_transform_all_(key)
        method = '__getitem__'
        if self._default_ and is_str(key_adj) and (key_adj.lower() == 'default' or key_adj.lower() == self._default_.strip('_')):
            return self.getDefault()
        if not getattr(key_adj, '__hash__'):
            self.log("Unhashable key: <%s> %s [Hash: %s]" % (key_adj.__class__.__name__, repr(key_adj), getattr(key_adj, '__hash__')), method)
        if key_adj not in self:
            if key_adj in dir(self.__class__):
                # return super(self.__class__.mro()[-3], self).__getattr__(key_adj)
                self.log_action(method, 'Returning', 'Missing Attr', self.label.full, key_adj, 'getitem')
                return super(self.__class__.mro()[-3], self).__getattr__(key_adj)
            elif self._is_protected_(key):
                if not self._is_my_attr_(key):
                    try:
                        return super(self.__class__.mro()[-3], self).__getattr__(key.lower())
                    except Exception:
                        raise (KeyError("Could not find protected built-in item " + key))
                self.log_action(method, 'Skipping', 'Missing My Attr', self.label.full, key_adj, 'getitem')
                return None
                # return super(self.__class__, self).__getattr__(key_adj)
            # elif key_adj in dir(self.__class__):
                # self.log_action(method, 'Returning', 'Missing Attr', self.label.full, key_adj, 'getitem')
                # return super(self.__class__.mro()[-3], self).__getattr__(key_adj)
            else:
                self.log_action(method, 'Creating', 'Missing Item', self.label.full, key_adj)
                self[key_adj] = self._new_instance_(self, key_name=key_adj, override_default=True)
        try:
            return super(self.__class__.mro()[-4], self).__getitem__(key_adj)
        except TypeError:
            return "<null>"

