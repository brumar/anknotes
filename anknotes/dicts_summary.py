import collections
from addict import Dict
from anknotes.constants_standard import ANKNOTES
from anknotes.base import item_to_list, is_str, is_str_type, in_delimited_str, delete_keys, key_transform, str_capitalize, ank_prop, pad_digits, call, get_unique_strings
from addict import Dict

def _get_summary_(self, level=1, header_only=False):
    summary=Dict(level=level, label=self.label, children=self.keys(), key=self.key, child_values={})
    summary.strs.update(class_name=self.__class__.__name__, marker=' ')
    if self._default_ is not None:
        dval = self.getDefault()
        if dval != self._default_value_:
            summary.strs.default_full = summary.strs.default = dval
            if self._override_default_:
                summary.strs.marker = '*'
        attr = self.getDefaultAttr()
        if attr != self._default_value_:
            summary.strs.default_attr = attr
            summary.strs.marker = '!' if self._override_default_ else '#'
    summary.strs.value = self.has_value and self.val or ''
    summaries=[]
    if header_only:
        return [summary]
    for key in sorted(self.keys()):
        if self._is_my_aggregate_(key):
            continue
        item = self[key]
        if not isinstance(item, Dict):
            summary.child_values[key] = item
        elif not header_only:
            summaries += item._get_summary_(level + 1)
    return [summary] + summaries

def _summarize_lines_(self, summary, header=True, value_pad=3):
    def _summarize_child_lines_(pad_len):
        if not item.child_values:
            return ''
        child_lines = []
        pad = ' '*(pad_len*3-1)
        for child_key in sorted(item.child_values.keys()):
            child_value = str(item.child_values[child_key])
            child_value = pad_digits(child_value)
            marker = '+'
            if child_key.startswith('#'):
                marker = '#'
                child_key = child_key[1:]
            child_lines.append(('%s%s%-15s' % (pad, marker, child_key + ':')).ljust(16+pad_len * 4 + 11) + child_value + marker)
        return '\n' + '\n'.join(child_lines)

    # Begin _summarize_lines_()
    lines = []
    for i, item in enumerate(summary):
        str_full_key = str_full_label = str_label = str_key = str_default_attr = str_value = str_default = str_default_full = ''
        if item.key:
            item.strs.update(akey_full=item.key.join(' -> '), akey_name=item.key.name, akey_parent=item.key.parent)
        if item.label:
            item.strs.update(alabel_full=item.label.join(' -> '), alabel_name=item.label.name, alabel_parent=item.label.parent)
        strs = get_unique_strings(item.strs)
        if strs.alabel_full:
            if strs.akey_full and item.key.parent == item.label.parent:
                strs.alabel_full = '* -> ' + item.label.name
            strs.alabel_full='%sL[%s]' % (' | ' if strs.akey_full else '', strs.alabel_full)
        if strs.akey_full and strs.default_full:
            strs.alabel_full += ': '
        if self._is_my_attr_('_summarize_dont_print_default_') or not strs.default:
            strs.default = strs.default_full = ''
        elif strs.alabel_full:
            strs.default_full = 'D[%s]' % strs.default
        strs.default_full += ':' if strs.value else ''
        if strs.alabel_name:
            strs.alabel_name='%sL[%s]' % (' | ' if strs.akey_name else '', strs.alabel_name)
        if i is 0 and header:
            pad_len = len(strs.class_name) + (len(strs.alabel_full) - len(strs.alabel_name) if strs.alabel_full else 0)
            lines.append("<%s%s:%s%s%s>" % (strs.marker.strip(), strs.class_name, strs.akey_full + strs.alabel_full, strs.default_full,
                         strs.value) + _summarize_child_lines_(item.level+1))
            continue
        str_ = ' ' * (item.level * 3 - 1) + strs.marker + strs.akey_name + strs.alabel_name
        child_str = _summarize_child_lines_(item.level+1)
        strs.val_def = ' '*(value_pad+2)
        strs.value, strs.default, strs.default_attr = pad_digits(strs.value, strs.default, strs.default_attr)
        if strs.value and strs.default:
            strs.val_def = (strs.value + ':').ljust(value_pad+1) + ' ' + strs.default
        elif strs.default:
            strs.val_def += strs.default
        elif strs.value:
            strs.val_def = strs.value.ljust(value_pad)
        if strs.default_attr:
            strs.val_def += ' ' + strs.default_attr
        if strs.val_def.strip() == '':
            strs.marker = ''
        else:
            str_ += ': '
        str_ = str_.ljust(16 + item.level * 4 + 5)
        lines.append(str_ + ' ' + strs.val_def + strs.marker + child_str)
    return '\n'.join(lines)