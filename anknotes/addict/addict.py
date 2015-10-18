from inspect import isgenerator
import re
import os
import copy
from anknotes.logging_base import write_file_contents, reset_logs

class Dict(dict):
    """
    Dict is a subclass of dict, which allows you to get AND SET(!!)
    items in the dict using the attribute syntax!

    When you previously had to write:

    my_dict = {'a': {'b': {'c': [1, 2, 3]}}}

    you can now do the same simply by:

    my_Dict = Dict()
    my_Dict.a.b.c = [1, 2, 3]

    Or for instance, if you'd like to add some additional stuff,
    where you'd with the normal dict would write

    my_dict['a']['b']['d'] = [4, 5, 6],

    you may now do the AWESOME

    my_Dict.a.b.d = [4, 5, 6]

    instead. But hey, you can always use the same syntax as a regular dict,
    however, this will not raise TypeErrors or AttributeErrors at any time
    while you try to get an item. A lot like a defaultdict.

    """

    def __init__(self, *a, **kw):
        """
        If we're initialized with a dict, make sure we turn all the
        subdicts into Dicts as well.

        """
        a = list(a)
        mro = self._get_arg_(a, int, 'mro', kw)
        self.log_init('Dict', mro, a, kw)
        for arg in a:
            if not arg:
                continue
            elif isinstance(arg, dict):
                for key, val in arg.items():
                    self[key] = val
            elif isinstance(arg, tuple) and (not isinstance(arg[0], tuple)):
                self[arg[0]] = arg[1]
            elif isinstance(arg, (list, tuple)) or isgenerator(arg):
                for key, val in arg:
                    self[key] = val
            else:
                raise TypeError("Dict does not understand "
                                "{0} types".format(arg.__class__))

        for key, val in kw.items():
            self[key] = val

    def __setattr__(self, name, value):
        """
        setattr is called when the syntax a.b = 2 is used to set a value.

        """
        if hasattr(Dict, name):
            raise AttributeError("'Dict' object attribute "
                                 "'{0}' is read-only".format(name))
        else:
            self[name] = value

    def __setitem__(self, name, value):
        """
        This is called when trying to set a value of the Dict using [].
        E.g. some_instance_of_Dict['b'] = val. If 'val

        """
        value = self._hook(value)
        super(Dict, self).__setitem__(name, value)

    def _hook(self, item):
        """
        Called to ensure that each dict-instance that are being set
        is a addict Dict. Recurses.

        """
        if isinstance(item, dict):
            return self._new_instance_(item)
        if isinstance(item, (list, tuple)):
            return item.__class__(self._hook(elem) for elem in item)
        return item

    def __getattr__(self, item):
        if item not in self and item in dir(self):
            return super(Dict, self).__getattr__(item)
        return self.__getitem__(item)
        
    def _new_instance_(self, *a, **kw):
        return (self.__class__.mro()[self._mro_offset_] if '_mro_offset_' in dir(self.__class__) else self.__class__)(*a, **kw)
        
    def __getitem__(self, name):
        """
        This is called when the Dict is accessed by []. E.g.
        some_instance_of_Dict['a'];
        If the name is in the dict, we return it. Otherwise we set both
        the attr and item to a new instance of Dict.

        """
        if name not in self:
            self[name] = self._new_instance_()
        return super(Dict, self).__getitem__(name)

    def __delattr__(self, name):
        """ Is invoked when del some_addict.b is called. """
        del self[name]

    _re_pattern = re.compile('[a-zA-Z_][a-zA-Z0-9_]*')
    
    def log(self, str_, method, do_print=True, prefix=''):
        cls = self.__class__
        str_lbl = self.label.full if self.label else ''
        if str_lbl:
            str_lbl += ': '
        str_ = prefix + '%17s %-20s %s' % ('<%s>' % cls.__name__, str_lbl, str_)
        if do_print:
            print str_
        write_file_contents(str_, 'Dicts\\%s\\%s' % (cls.__name__, method))  

    def log_action(self, method, action, name, value, key=None, via=None, extra='', log_self=False):
        if key in ['_my_attrs_','_override_default_']:
            return
        if extra:
            extra += ' '
        type = ('<%s>' % value.__class__.__name__).center(10)
        log_str = action.ljust(12) + ' '
        log_str += name.ljust(12) + ' '
        log_str += ('via '+via if via else '').ljust(10) + ' '
        log_str += ('for `%s`' % key if key else '').ljust(25) + ' '
        log_str += 'to %10s%s %s' % (extra, type, str(value))
        if log_self:
            log_str += ' \n\n Self:  ' + repr(self)
        self.log(log_str, method); 
    
    def log_init(self, type, mro, a, kw):
        cls = self.__class__        
        mro_name = cls.mro()[mro].__name__
        mro_name = (':' + mro_name) if mro_name != cls.__name__ and mro_name != type else ''
        log_str =  "Init: %s%s #%d" % (type, mro_name, mro)
        log_str += "\n   Args: %s" % a if a else ""
        log_str += "\n KWArgs: %s" % kw if kw else ""
        self.log(log_str + '\n', '__init__', prefix='-'*40+'\n', do_print=False)

    def clear_logs(self):
        name=self.__class__.__name__
        reset_logs('Dicts' + os.path.sep + name, self.make_banner(name))
    
    @staticmethod
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
    
    def _get_arg_(self, a, cls=None, key=None, kw=None, default=None):
        if cls is None:
            cls = (str, unicode)
        if a and isinstance(a[0], cls):
            val = a[0]
            del a[0]
        elif kw and key in kw:
            val = kw[key]
            del kw[key]
        else:
            val = self.get_default_value(cls, default)
        return val        

    def _key_transform_(self, key, keys=None, all=False, attrs=False):
        return key
        
    def _key_transform_all_(self, key, keys=None):
        return self._key_transform_(key, keys, all=True)
        
    def _key_transform_attrs_(self, key, keys=None):
        return self._key_transform_(key, keys, attrs=True)

    def __contains__(self, item):
        key = self._key_transform_(item)
        return key in self._dict_keys_()
    
    def _is_obj_attr_(self, key):
        keys = self._obj_attrs_()
        key = self._key_transform_(key, keys)
        return key in keys
    
    def _dict_keys_(self):
        dict_keys = []
        for k in self.keys():
            if isinstance(k, str):
                m = self._re_pattern.match(k)
                if m:
                    dict_keys.append(m.string)
        return dict_keys
        
    def _obj_attrs_(self):
        return list(dir(self.__class__))
    
    def __dir__(self):
        """
        Return a list of addict object attributes.
        This includes key names of any dict entries, filtered to the subset of
        valid attribute names (e.g. alphanumeric strings beginning with a
        letter or underscore).  Also includes attributes of parent dict class.
        """
        return self._dict_keys_() + self._obj_attrs_()
    
    def _ipython_display_(self):
        print(str(self))  # pragma: no cover

    def _repr_html_(self):
        return str(self)

    def prune(self, prune_zero=False, prune_empty_list=True):
        """
        Removes all empty Dicts and falsy stuff inside the Dict.
        E.g
        >>> a = Dict()
        >>> a.b.c.d
        {}
        >>> a.a = 2
        >>> a
        {'a': 2, 'b': {'c': {'d': {}}}}
        >>> a.prune()
        >>> a
        {'a': 2}

        Set prune_zero=True to remove 0 values
        E.g
        >>> a = Dict()
        >>> a.b.c.d = 0
        >>> a.prune(prune_zero=True)
        >>> a
        {}

        Set prune_empty_list=False to have them persist
        E.g
        >>> a = Dict({'a': []})
        >>> a.prune()
        >>> a
        {}
        >>> a = Dict({'a': []})
        >>> a.prune(prune_empty_list=False)
        >>> a
        {'a': []}
        """
        for key, val in list(self.items()):
            if ((not val) and ((val != 0) or prune_zero) and
                    not isinstance(val, list)):
                del self[key]
            elif isinstance(val, Dict):
                val.prune(prune_zero, prune_empty_list)
                if not val:
                    del self[key]
            elif isinstance(val, (list, tuple)):
                new_iter = self._prune_iter(val, prune_zero, prune_empty_list)
                if (not new_iter) and prune_empty_list:
                    del self[key]
                else:
                    if isinstance(val, tuple):
                        new_iter = tuple(new_iter)
                    self[key] = new_iter

    @classmethod
    def _prune_iter(cls, some_iter, prune_zero=False, prune_empty_list=True):
        new_iter = []
        for item in some_iter:
            if item == 0 and prune_zero:
                continue
            elif isinstance(item, Dict):
                item.prune(prune_zero, prune_empty_list)
                if item:
                    new_iter.append(item)
            elif isinstance(item, (list, tuple)):
                new_item = item.__class__(
                    cls._prune_iter(item, prune_zero, prune_empty_list))
                if new_item or not prune_empty_list:
                    new_iter.append(new_item)
            else:
                new_iter.append(item)
        return new_iter

    def to_dict(self):
        """ Recursively turn your addict Dicts into dicts. """
        base = {}
        cls = self.__class__
        for key, value in self.items():
            if isinstance(value, cls):
                base[key] = value.to_dict()
            elif isinstance(value, (list, tuple)):
                base[key] = value.__class__(
                    item.to_dict() if isinstance(item, cls) else
                    item for item in value)
            else:
                base[key] = value
        return base

    def copy(self):
        """
        Return a disconnected deep copy of self. Children of type Dict, list
        and tuple are copied recursively while values that are instances of
        other mutable objects are not copied.

        """
        return self._new_instance_(self.to_dict())

    def __deepcopy__(self, memo):
        """ Return a disconnected deep copy of self. """

        y = self.__class__()
        memo[id(self)] = y
        for key, value in self.items():
            y[copy.deepcopy(key, memo)] = copy.deepcopy(value, memo)
        return y

    def update(self, d):
        """ Recursively merge d into self. """

        for k, v in d.items():
            if ((k not in self) or
                    (not isinstance(self[k], dict)) or
                    (not isinstance(v, dict))):
                self[k] = v
            else:
                self[k].update(v)
