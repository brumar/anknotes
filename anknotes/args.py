# -*- coding: utf-8 -*-
import re
from datetime import datetime

### Anknotes Imports
from anknotes.constants import *
from anknotes.base import item_to_list, caller_name, is_str, is_seq_type, is_dict_type
from anknotes.dicts import DictCaseInsensitive
from anknotes.dicts_base import DictKey

class Args(object):

    def __init__(self, func_kwargs=None, func_args=None, func_args_list=None, set_list=None, set_dict=None,
                 require_all_args=None, limit_max_args=None, override_kwargs=None, use_set_list_as_arg_list=False):
        from logging import write_file_contents, pf
        self.__require_all_args = require_all_args or False
        self.__limit_max_args = limit_max_args if limit_max_args is not None else True
        self.__override_kwargs = override_kwargs or False
        self.__set_args_and_kwargs(func_args, func_kwargs)
        self.__func_args_list = use_set_list_as_arg_list and [set_list[i*2] for i in range(0, len(set_list)/2)] or func_args_list
        if self.__func_args_list:
            self.process_args()
        self.__init_set(set_list, set_dict)

    def __init_set(self, set_list=None, set_dict=None):
        if not set_list or set_dict:
            return
        self.__conv_set_list(set_list)
        self.set_kwargs(set_list, set_dict)

    def __conv_set_list(self, set_list=None):
        if set_list is None:
            return
        func_args_count = len(self.__func_args_list)
        for i in range(0, len(set_list)/2):
            if not set_list[i*2] and func_args_count > i:
                set_list[i*2] = self.__func_args_list[i]

    def __set_args_and_kwargs(self, *a, **kw)
        self.__func_args, self.__func_kwargs = self.__get_args_and_kwargs(*a, **kw)

    def __get_args_and_kwargs(self, func_args=None, func_kwargs=None, name=None, allow_cls_override=True):
        if not func_args and not func_kwargs:
            return self.args or [], self.kwargs or DictCaseInsensitive()
        func_args = func_args or allow_cls_override and self.args or []
        func_kwargs = func_kwargs or allow_cls_override and self.kwargs or DictCaseInsensitive()
        if is_seq_type(func_kwargs) and is_dict_type(func_args):
            func_args, func_kwargs = func_kwargs, func_args
        func_args = self.__args_to_list(func_args)
        if isinstance(func_kwargs, dict):
            func_kwargs = DictCaseInsensitive(func_kwargs, key=name, parent_key='kwargs')
        if not isinstance(func_args, list):
            func_args = []
        if not isinstance(func_kwargs, DictCaseInsensitive):
            func_kwargs = DictCaseInsensitive(key=name)
        return func_args, func_kwargs

    def __args_to_list(self, func_args):
        if not is_str(func_args):
            return list(func_args)
        lst = []
        for arg in item_to_list(func_args, chrs=','):
            lst += [arg] + [None]
        return lst

    @property
    def kwargs(self):
        return self.__func_kwargs

    @property
    def args(self):
        return self.__func_args

    @property
    def keys(self):
        return self.kwargs.keys()

    def key_transform(self, key, keys=None):
        if keys is None:
            keys = self.keys
        key = key.strip()
        key_lower = key.lower()
        for k in keys:
            if k.lower() == key_lower:
                return k
        return key

    def get_kwarg(self, key, **kwargs):
        kwargs['update_kwargs'] = False
        return self.process_kwarg(key, **kwargs)

    def process_kwarg(self, key, default=None, func_kwargs=None, replace_none_type=True, delete_from_kwargs=None, return_value_only=True, update_cls_args=True):
        delete_from_kwargs = delete_from_kwargs is not False
        cls_kwargs = func_kwargs is None
        func_kwargs = self.kwargs if cls_kwargs else DictCaseInsensitive(func_kwargs)
        key = self.key_transform(key, func_kwargs.keys())
        if key not in func_kwargs:
            return (func_kwargs, default) if delete_from_kwargs and not return_value_only else default
        val = func_kwargs[key]
        if val is None and replace_none_type:
            val = default
        if delete_from_kwargs:
            del func_kwargs[key]
            if cls_kwargs and update_cls_args:
                del self.__func_kwargs[key]
        if not delete_from_kwargs or return_value_only:
            return val
        return func_kwargs, val

    def process_kwargs(self, get_args=None, set_dict=None, func_kwargs=None, delete_from_kwargs=True, update_cls_args=True, **kwargs):
        method_name='process_kwargs'
        kwargs['return_value_only'] = False
        cls_kwargs = func_kwargs is None
        func_kwargs = self.kwargs if cls_kwargs else DictCaseInsensitive(func_kwargs)
        keys = func_kwargs.keys()
        for key, value in set_dict.items() if set_dict else []:
            key = self.key_transform(key, keys)
            if key not in func_kwargs:
                func_kwargs[key] = value
        if not get_args:
            if cls_kwargs and update_cls_args:
                self.__func_kwargs = func_kwargs
            return func_kwargs
        gets = []
        for arg in get_args:
            # for arg in args:
            if len(arg) is 1 and isinstance(arg[0], list):
                arg = arg[0]
            result = self.process_kwarg(arg[0], arg[1], func_kwargs=func_kwargs, delete_from_kwargs=delete_from_kwargs, **kwargs)
            if delete_from_kwargs:
                func_kwargs = result[0]
                result = result[1]
            gets.append(result)
        if cls_kwargs and update_cls_args:
            self.__func_kwargs = func_kwargs
        if delete_from_kwargs:
            return [func_kwargs] + gets
        return gets

    def get_kwarg_values(self, *args, **kwargs):
        kwargs['return_value_only'] = True
        if not 'delete_from_kwargs' in kwargs:
            kwargs['delete_from_kwargs'] = False
        return self.get_kwargs(*args, **kwargs)

    def get_kwargs(self, *args_list, **kwargs):
        method_name='get_kwargs'
        lst = []
        for args in args_list:
            if isinstance(args, dict):
                args = item_to_list(args)
                args_dict = args
            if isinstance(args, list):
                lst += [args[i * 2:i * 2 + 2] for i in range(0, len(args) / 2)]
            else:
                lst += [[arg, None] for arg in item_to_list(args)]
        return self.process_kwargs(get_args=lst, **kwargs)

    def process_args(self, arg_list=None, func_args=None, func_kwargs=None, update_cls_args=True):
        method_name='process_args'
        arg_list = item_to_list(arg_list) if arg_list else self.__func_args_list
        cls_args = func_args is None
        cls_kwargs = func_kwargs is None
        func_args, func_kwargs = self.__get_args_and_kwargs(func_args, func_kwargs)
        arg_error = ''
        if not func_args:
            return func_args, func_kwargs
        for i in range(0, len(arg_list)):
            if len(func_args) is 0:
                break
            arg = arg_list[i]
            if arg in func_kwargs and not self.__override_kwargs:
                formats = (caller_name(return_string=True), arg)
                raise TypeError("Anknotes.Args: %s() got multiple arguments for keyword argument '%s'" % formats)
            func_kwargs[arg] = func_args[0]
            del func_args[0]
        else:
            if self.__require_all_args:
                arg_error = 'least'
        if func_args and self.__limit_max_args:
            arg_error = 'most'
        if arg_error:
            formats = (caller_name(return_string=True), arg_error, len(arg_list), '' if arg_list is 1 else 's', len(func_args))
            raise TypeError('Anknotes.Args: %s() takes at %s %d argument%s (%d given)' % formats)
        if cls_args and update_cls_args:
            self.__func_args = func_args
        if cls_kwargs and update_cls_args:
            self.__func_kwargs = func_kwargs
        return func_args, func_kwargs

    def set_kwargs(self, set_list=None, set_dict=None, func_kwargs=None, name=None, delete_from_kwargs=None, *args, **kwargs):
        method_name='set_kwargs'
        new_args = []
        lst, dct = self.__get_args_and_kwargs(set_list, set_dict, allow_cls_override=False)
        if isinstance(lst, list):
            dct.update({lst[i * 2]: lst[i * 2 + 1] for i in range(0, len(lst) / 2)})
            lst = []
        for arg in args:
            new_args += item_to_list(arg, False)
        dct.update({key: None for key in item_to_list(lst, chrs=',') + new_args})
        dct.update(kwargs)
        dct_items = dct.items()
        processed_kwargs = self.process_kwargs(func_kwargs=func_kwargs, set_dict=dct, name=name, delete_from_kwargs=delete_from_kwargs).items()
        return self.process_kwargs(func_kwargs=func_kwargs, set_dict=dct, name=name, delete_from_kwargs=delete_from_kwargs)