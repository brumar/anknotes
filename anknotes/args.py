# -*- coding: utf-8 -*-
import sys
import re
from datetime import datetime

### Check if in Anki
inAnki = 'anki' in sys.modules

### Anknotes Imports
from anknotes.constants import *
from anknotes.base import item_to_list, caller_name, is_str_type
from anknotes.dicts import DictCaseInsensitive

if inAnki:
    from aqt import mw


class Args(object):    
    require_all_args = False
    limit_max_args = True
    override_kwargs = False
    last_log_method=None

    def log(self, obj, title='Args', method=None):
        if method is None:
            method = obj['method_name']
            if title != '*':
                obj = obj[title]
        if self.last_log_method != method:
            self.write_file_contents('-'*80 + '\n%s\n' % method.center(80) + '-' * 80, 'args\\main', clear=self.last_log_method is None)
            self.write_file_contents('-'*80 + '\n%s\n' % method.center(80) + '-' * 80, 'args\\'+method, clear=self.last_log_method is None)
        self.write_file_contents(title + ': ' + self.pf(obj), 'args\\'+method)
        self.write_file_contents(title + ': ' + self.pf(obj), 'args\\main')
        self.last_log_method=method

    def __init__(self, func_kwargs=None, func_args=None, func_args_list=None, set_list=None, set_dict=None,
                 require_all_args=None, limit_max_args=None, override_kwargs=None, use_set_list_as_arg_list=False):
        from logging import write_file_contents, pf
        self.write_file_contents=write_file_contents
        self.pf = pf
        method_name='__init__'
        if require_all_args is not None:
            self.require_all_args = require_all_args
        if limit_max_args is not None:
            self.limit_max_args = limit_max_args
        if override_kwargs is not None:
            self.override_kwargs = override_kwargs
        self.__func_args, self.__func_kwargs = [], DictCaseInsensitive()
        self.log(locals(), 'func_args')
        self.log(locals(), 'func_kwargs')
        # self.log(locals(), '*')
        func_args, func_kwargs = self.__get_args_and_kwargs(func_args, func_kwargs)
        self.log(locals(), 'func_args')
        self.log(locals(), 'func_kwargs')
        self.__func_args, self.__func_kwargs = func_args, func_kwargs
        if use_set_list_as_arg_list:
            func_args_list = [set_list[i*2] for i in range(0, len(set_list)/2)]
        self.__func_args_list = func_args_list
        if func_args_list:
            self.log(locals(), 'func_args_list')
            self.process_args()
        if set_list:
            func_args_count = len(func_args_list)
            for i in range(0, len(set_list)/2):
                if not set_list[i*2] and func_args_count > i:
                    set_list[i*2] = func_args_list[i]
        self.log(locals(), 'set_list')
        self.log(locals(), 'set_dict')
        if set_list or set_dict:
            self.set_kwargs(set_list=set_list, set_dict=set_dict)

    def __get_args_and_kwargs(self, func_args=None, func_kwargs=None, name=None, allow_cls_override=True):
        if not func_args and not func_kwargs:
            return self.args, self.kwargs
        if not func_args:
            func_args = self.args if self.args and allow_cls_override else []
        if not func_kwargs:
            func_kwargs = self.kwargs if self.kwargs and allow_cls_override else {}
        if ((isinstance(func_kwargs, list) or isinstance(func_kwargs, tuple)) and
                (isinstance(func_args, dict) or isinstance(func_args, DictCaseInsensitive))):
            func_args, func_kwargs = func_kwargs, func_args
        if isinstance(func_args, tuple):
            func_args = list(func_args)
        if is_str_type(func_args):
            lst = []
            for arg in item_to_list(func_args, chrs=','):
                lst += [arg] + [None]
            func_args = lst
        if isinstance(func_kwargs, dict):
            func_kwargs = DictCaseInsensitive(func_kwargs, label=name)
        if not isinstance(func_args, list):
            func_args = []
        if not isinstance(func_kwargs, DictCaseInsensitive):
            func_kwargs = DictCaseInsensitive(label=name)
        return func_args, func_kwargs

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
        self.log(locals(), 'func_kwargs')
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
        self.log(locals(), 'get_args')
        for arg in get_args:
            # for arg in args:
            if len(arg) is 1 and isinstance(arg[0], list):
                arg = arg[0]
            self.log(locals(), 'arg')
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

    # def get_args(self, *args_list, **kwargs_):
    #     kwargs = DictCaseInsensitive({
    #         'suffix_type_to_name': True, 'max_args': -1, 'default_value': None,
    #         'return_expanded':     True, 'return_values_only': False
    #     })
    #     kwargs.update(kwargs_)
    #     max_args = kwargs.max_args
    #     results = DictCaseInsensitive()
    #     max_args = len(self.args) if max_args < 1 else min(len(self.args), max_args)
    #     values = []
    #     args_to_del = []
    #     get_names = [
    #         [names[i * 2:i * 2 + 2] for i in range(0, len(names) / 2)] if isinstance(names, list) else [[name, None] for
    #                                                                                                     name in
    #                                                                                                     item_to_list(names)]
    #         for names in args_list]
    #
    #     for get_name in get_names:
    #         for get_name_item in get_name:
    #             if len(get_name_item) is 1 and isinstance(get_name_item[0], list):
    #                 get_name_item = get_name_item[0]
    #             name = get_name_item[0]
    #             types = get_name_item[1]
    #             name = name.replace('*', '')
    #             types = item_to_list(types)
    #             is_none_type = types[0] is None
    #             key = name + ('_' + types[0].__name__) if kwargs.suffix_type_to_name and not is_none_type else ''
    #             key = key_transform(key, func_kwargs.keys())
    #             result = DictCaseInsensitive(Match=False, MatchedKWArg=False, MatchedArg=False, Name=key,
    #                                          value=kwargs.default_value)
    #             if key in func_kwargs:
    #                 result.value = func_kwargs[key]
    #                 del func_kwargs[key]
    #                 result.Match = True
    #                 result.MatchedKWArg = True
    #                 continue
    #             if is_none_type:
    #                 continue
    #             for i in range(0, max_args):
    #                 if i in args_to_del:
    #                     continue
    #                 arg = args[i]
    #                 for t in types:
    #                     if not isinstance(arg, t):
    #                         continue
    #                     result.value = arg
    #                     result.Match = True
    #                     result.MatchedArg = True
    #                     args_to_del.append(i)
    #                     break
    #                 if result.Match:
    #                     break
    #             values.append(result.value)
    #             results[name] = result
    #     args = [x for i, x in enumerate(args) if i not in args_to_del]
    #     results.func_kwargs = func_kwargs
    #     results.args = args
    #     if kwargs.return_values_only:
    #         return values
    #     if kwargs.return_expanded:
    #         return [args, func_kwargs] + values
    #     return results
    #
    #
    # def __get_default_listdict_args(args, kwargs, name):
    #     results_expanded = __get_args(args, kwargs, [name + '*', [list, str, unicode], name, [dict, DictCaseInsensitive]])
    #     if results_expanded[2] is None:
    #         results_expanded[2] = []
    #     if results_expanded[3] is None:
    #         results_expanded[3] = {}
    #     return results_expanded

    def get_kwarg_values(self, *args, **kwargs):
        kwargs['return_value_only'] = True
        if not 'delete_from_kwargs' in kwargs:
            kwargs['delete_from_kwargs'] = False
        return self.get_kwargs(*args, **kwargs)

    def get_kwargs(self, *args_list, **kwargs):
        method_name='get_kwargs'
        self.log(locals(), 'args_list')
        lst = []
        for args in args_list:
            self.log(locals(), 'args')
            if isinstance(args, dict):
                args = item_to_list(args)
                args_dict = args
                self.log(locals(), 'args_dict')
            if isinstance(args, list):
                lst += [args[i * 2:i * 2 + 2] for i in range(0, len(args) / 2)]
            else:
                lst += [[arg, None] for arg in item_to_list(args)]
        self.log(locals(), 'lst')
        return self.process_kwargs(get_args=lst, **kwargs)

    def process_args(self, arg_list=None, func_args=None, func_kwargs=None, update_cls_args=True):
        method_name='process_args'
        arg_list = item_to_list(arg_list) if arg_list else self.__func_args_list
        self.log(locals(), 'arg_list')
        cls_args = func_args is None
        cls_kwargs = func_kwargs is None
        func_args, func_kwargs = self.__get_args_and_kwargs(func_args, func_kwargs)
        arg_error = ''
        self.log(locals(), 'func_args')
        self.log(locals(), 'func_kwargs')
        if not func_args:
            return func_args, func_kwargs
        for i in range(0, len(arg_list)):
            if len(func_args) is 0:
                break
            arg = arg_list[i]
            if arg in func_kwargs and not self.override_kwargs:
                formats = (caller_name(return_string=True), arg)
                raise TypeError("Anknotes.Args: %s() got multiple arguments for keyword argument '%s'" % formats)
            func_kwargs[arg] = func_args[0]
            del func_args[0]
        else:
            if self.require_all_args:
                arg_error = 'least'
        if func_args and self.limit_max_args:
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
        self.log(locals(), 'kwargs')
        self.log(locals(), 'set_list')
        lst, dct = self.__get_args_and_kwargs(set_list, set_dict, allow_cls_override=False)
        self.log(locals(), 'lst')
        if isinstance(lst, list):
            dct.update({lst[i * 2]: lst[i * 2 + 1] for i in range(0, len(lst) / 2)})
            lst = []
        for arg in args:
            new_args += item_to_list(arg, False)
        self.log(locals(), 'lst')
        dct.update({key: None for key in item_to_list(lst, chrs=',') + new_args})
        dct.update(kwargs)
        self.log(locals(), 'lst')
        self.log(locals(), 'dct')
        self.log(locals(), 'func_kwargs')
        return self.process_kwargs(func_kwargs=func_kwargs, set_dict=dct, name=name, delete_from_kwargs=delete_from_kwargs)