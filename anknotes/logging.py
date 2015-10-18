# Python Imports
from datetime import datetime, timedelta
import difflib
import pprint
import re
import shutil
import time
from fnmatch import fnmatch


# Anknotes Shared Imports
from anknotes.constants import *
from anknotes.logging_base import write_file_contents, rm_log_path, reset_logs, filter_logs
from anknotes.base import item_to_list, is_str, is_str_type, caller_name, create_log_filename, str_safe, encode, decode
from anknotes.methods import create_timer
from anknotes.args import Args
from anknotes.graphics import *
from anknotes.dicts import DictCaseInsensitive

# Anki Imports
try:
    from aqt import mw
    from aqt.utils import tooltip
    from aqt.qt import QMessageBox, QPushButton, QSizePolicy, QSpacerItem, QGridLayout, QLayout
except Exception:
    pass


def show_tooltip(text, time_out=7, delay=None, do_log=False, **kwargs):
    if not hasattr(show_tooltip, 'enabled'):
        show_tooltip.enabled = None
    if do_log:
        log(text, **kwargs)
    if delay:
        try:
            return create_timer(delay, tooltip, text, time_out * 1000)
        except Exception:
            pass
    if show_tooltip.enabled is not False:
        tooltip(text, time_out * 1000)


def counts_as_str(count, max_=None):
    from anknotes.counters import Counter
    if isinstance(count, Counter):
        count = count.val
    if isinstance(max_, Counter):
        max_ = max_.val
    if max_ is None or max_ <= 0:
        return str(count).center(3)
    if count == max_:
        return "All  %s" % str(count).center(3)
    return "Total %s of %s" % (str(count).center(3), str(max_).center(3))


def format_count(format_str, count):
    """
    :param format_str:
    :type format_str : str | unicode
    :param count:
    :return:
    """
    if not count > 0:
        return ' ' * len(format_str % 1)
    return format_str % count


def show_report(title, header=None, log_lines=None, delay=None, log_header_prefix=' ' * 5,
                blank_line_before=True, blank_line_after=True, hr_if_empty=False, **kw):
    if log_lines is None:
        log_lines = []
    if header is None:
        header = []
    lines = []
    for line in ('<BR>'.join(header) if isinstance(header, list) else header).split('<BR>') + (
            '<BR>'.join(log_lines).split('<BR>') if log_lines else []):
        level = 0
        while line and line[level] is '-': level += 1
        lines.append('\t' * level + ('\t\t- ' if lines else '') + line[level:])
    if len(lines) > 1:
        lines[0] += ': '
    log_text = '<BR>'.join(lines)
    if not header and not log_lines:
        i = title.find('> ')
        show_tooltip(title[0 if i < 0 else i + 2:], delay=delay)
    else:
        show_tooltip(log_text.replace('\t', '&nbsp; ' * 4), delay=delay)
    if blank_line_before:
        log_blank(**kw)
    log(title, **kw)
    if len(lines) == 1 and not lines[0]:
        if hr_if_empty:
            log("-" * ANKNOTES.FORMATTING.LINE_LENGTH, timestamp=False, **kw)
        return
    log("-" * ANKNOTES.FORMATTING.LINE_LENGTH + '\n' + log_header_prefix + log_text.replace('<BR>', '\n'),
        timestamp=False, replace_newline=True, **kw)
    if blank_line_after:
        log_blank(**kw)

def showInfo(message, title="Anknotes: Evernote Importer for Anki", textFormat=0, cancelButton=False, richText=False,
             minHeight=None, minWidth=400, styleSheet=None, convertNewLines=True):
    global imgEvernoteWebMsgBox, icoEvernoteArtcore, icoEvernoteWeb
    msgDefaultButton = QPushButton(icoEvernoteArtcore, "Okay!", mw)

    if not styleSheet:
        styleSheet = file(FILES.ANCILLARY.CSS_QMESSAGEBOX, 'r').read()

    if not is_str_type(message):
        message = str(message)

    if richText:
        textFormat = 1
        message = '<style>\n%s</style>\n\n%s' % (styleSheet, message)
    global messageBox
    messageBox = QMessageBox()
    messageBox.addButton(msgDefaultButton, QMessageBox.AcceptRole)
    if cancelButton:
        msgCancelButton = QPushButton(icoTomato, "No Thanks", mw)
        messageBox.addButton(msgCancelButton, QMessageBox.RejectRole)
    messageBox.setDefaultButton(msgDefaultButton)
    messageBox.setIconPixmap(imgEvernoteWebMsgBox)
    messageBox.setTextFormat(textFormat)

    messageBox.setWindowIcon(icoEvernoteWeb)
    messageBox.setWindowIconText("Anknotes")
    messageBox.setText(message)
    messageBox.setWindowTitle(title)
    hSpacer = QSpacerItem(minWidth, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

    layout = messageBox.layout()
    """:type : QGridLayout """
    layout.addItem(hSpacer, layout.rowCount() + 1, 0, 1, layout.columnCount())
    ret = messageBox.exec_()
    if not cancelButton:
        return True
    if messageBox.clickedButton() == msgCancelButton or messageBox.clickedButton() == 0:
        return False
    return True


def diffify(content, split=True):
    for tag in [u'div', u'ol', u'ul', u'li', u'span']:
        content = content.replace(u"<" + tag, u"\n<" + tag).replace(u"</%s>" % tag, u"</%s>\n" % tag)
    content = re.sub(r'[\r\n]+', u'\n', content)
    return content.splitlines() if split else content


def generate_diff(value_original, value):
    try:
        return '\n'.join(list(difflib.unified_diff(diffify(value_original), diffify(value), lineterm='')))
    except Exception:
        pass
    try:
        return '\n'.join(
        list(difflib.unified_diff(diffify(decode(value_original)), diffify(value), lineterm='')))
    except Exception:
        pass
    try:
        return '\n'.join(
        list(difflib.unified_diff(diffify(value_original), diffify(decode(value)), lineterm='')))
    except Exception:
        pass
    try:
        return '\n'.join(list(
        difflib.unified_diff(diffify(decode(value_original)), diffify(decode(value)), lineterm='')))
    except Exception:
        raise


def PadList(lst, length=ANKNOTES.FORMATTING.LIST_PAD):
    newLst = []
    for val in lst:
        if isinstance(val, list):
            newLst.append(PadList(val, length))
        else:
            newLst.append(val.center(length))
    return newLst


def JoinList(lst, joiners='\n', pad=0, depth=1):
    if is_str_type(joiners):
        joiners = [joiners]
    str_ = ''
    if pad and is_str_type(lst):
        return lst.center(pad)
    if not lst or not isinstance(lst, list):
        return lst
    delimit = joiners[min(len(joiners), depth) - 1]
    for val in lst:
        if str_:
            str_ += delimit
        str_ += JoinList(val, joiners, pad, depth + 1)
    return str_


def PadLines(content, line_padding=ANKNOTES.FORMATTING.LINE_PADDING_HEADER, line_padding_plus=0, line_padding_header='',
             pad_char=' ', **kwargs):
    if not line_padding and not line_padding_plus and not line_padding_header:
        return content
    if not line_padding:
        line_padding = line_padding_plus; line_padding_plus = True
    if str(line_padding).isdigit():
        line_padding = pad_char * int(line_padding)
    if line_padding_header:
        content = line_padding_header + content; line_padding_plus = len(line_padding_header) + 1
    elif line_padding_plus is True:
        line_padding_plus = content.find('\n')
    if str(line_padding_plus).isdigit():
        line_padding_plus = pad_char * int(line_padding_plus)
    return line_padding + content.replace('\n', '\n' + line_padding + line_padding_plus)


def obj2log_simple(content):
    if not is_str_type(content):
        content = str(content)
    return content


def convert_filename_to_local_link(filename):
    return 'file:///' + filename.replace("\\", "//")


class Logger(object):
    base_path = None
    path_suffix = None
    caller_info = None
    default_filename = None
    defaults = {}
    auto_header=True
    default_banner=None

    def wrap_filename(self, filename=None, final_suffix='', wrap_fn_auto_header=True, crosspost=None, **kwargs):
        if filename is None:
            filename = self.default_filename
        if self.base_path is not None:
            filename = os.path.join(self.base_path, filename if filename else '')
        if self.path_suffix is not None:
            i_asterisk = filename.find('*')
            if i_asterisk > -1:
                final_suffix += filename[i_asterisk + 1:]
                filename = filename[:i_asterisk]
            filename += self.path_suffix + final_suffix
        if crosspost is not None:
            crosspost = [self.wrap_filename(cp)[0] for cp in item_to_list(crosspost, False)]
            kwargs['crosspost'] = crosspost

        if wrap_fn_auto_header and self.auto_header and self.default_banner and not os.path.exists(get_log_full_path(filename)):
            log_banner(self.default_banner, filename)
        return filename, kwargs

    def error(self, content, crosspost=None, *a, **kw):
        if crosspost is None:
            crosspost = []
        crosspost.append(self.wrap_filename('error'), **DictCaseInsensitive(self.defaults, kw))
        log_error(content, crosspost=crosspost, *a, **kw)

    def dump(self, obj, title='', filename=None, *args, **kwargs):
        filename, kwargs = self.wrap_filename(filename, **DictCaseInsensitive(self.defaults, kwargs))
        # noinspection PyArgumentList
        log_dump(obj, title, filename, *args, **kwargs)

    def blank(self, filename=None, *args, **kwargs):
        filename, kwargs = self.wrap_filename(filename, **DictCaseInsensitive(self.defaults, kwargs))
        log_blank(filename, *args, **kwargs)

    def banner(self, title, filename=None, *args, **kwargs):
        filename, kwargs = self.wrap_filename(filename, **DictCaseInsensitive(self.defaults, kwargs, wrap_fn_auto_header=False))
        self.default_banner = title
        log_banner(title, filename, *args, **kwargs)

    def go(self, content=None, filename=None, wrap_filename=True, *args, **kwargs):
        if wrap_filename:
            filename, kwargs = self.wrap_filename(filename, **DictCaseInsensitive(self.defaults, kwargs))
        log(content, filename, *args, **kwargs)

    def plain(self, content=None, filename=None, *args, **kwargs):
        filename, kwargs = self.wrap_filename(filename, **DictCaseInsensitive(self.defaults, kwargs))
        log_plain(content, filename, *args, **kwargs)

    log = do = add = go

    def default(self, *args, **kwargs):
        self.log(wrap_filename=False, *args, **DictCaseInsensitive(self.defaults, kwargs))

    def __init__(self, base_path=None, default_filename=None, rm_path=False, no_base_path=None, **kwargs):
        self.defaults = kwargs
        if no_base_path and not default_filename:
            default_filename = no_base_path
        self.default_filename = default_filename
        if base_path:
            self.base_path = base_path
        elif not no_base_path:
            self.caller_info = caller_name()
            if self.caller_info:
                self.base_path = create_log_filename(self.caller_info.Base) + os.path.sep
        if rm_path:
            rm_log_path(self.base_path)


def log_blank(*args, **kwargs):
    log(None, *args, **DictCaseInsensitive(kwargs, timestamp=False, delete='content'))


def log_plain(*args, **kwargs):
    log(*args, **DictCaseInsensitive(kwargs, timestamp=False))

def rm_log_paths(*args, **kwargs):
    for arg in args:
        rm_log_path(arg, **kwargs)

def log_banner(title, filename=None, length=ANKNOTES.FORMATTING.BANNER_MINIMUM, append_newline=True, timestamp=False,
               chr='-', center=True, clear=True, crosspost=None, prepend_newline=False, *args, **kwargs):
    if crosspost is not None:
        for cp in item_to_list(crosspost, False):
            log_banner(title, cp, **DictCaseInsensitive(kwargs, locals(), delete='title crosspost kwargs args filename'))
    if length is 0:
        length = ANKNOTES.FORMATTING.LINE_LENGTH + 1
    if center:
        title = title.center(length - (ANKNOTES.FORMATTING.TIMESTAMP_PAD_LENGTH if timestamp else 0))
    if prepend_newline:
        log_blank(filename, **kwargs)
    log(chr * length, filename, clear=clear, timestamp=False, **kwargs)
    log(title, filename, timestamp=timestamp, **kwargs)
    log(chr * length, filename, timestamp=False, **kwargs)
    if append_newline:
        log_blank(filename, **kwargs)


_log_filename_history = []


def set_current_log(fn):
    global _log_filename_history
    _log_filename_history.append(fn)


def end_current_log(fn=None):
    global _log_filename_history
    if fn:
        _log_filename_history.remove(fn)
    else:
        _log_filename_history = _log_filename_history[:-1]


def get_log_full_path(filename=None, extension='log', as_url_link=False, prefix='', filter_disabled=True, **kwargs):
    global _log_filename_history
    logging_base_name = FILES.LOGS.BASE_NAME
    filename_suffix = ''
    if filename and filename.startswith('*'):
        filename_suffix = '\\' + filename[1:]
        logging_base_name = ''
        filename = None
    if filename is None:
        if FILES.LOGS.USE_CALLER_NAME:
            caller = caller_name()
            if caller:
                filename = caller.Base.replace('.', '\\')
        if filename is None:
            filename = _log_filename_history[-1] if _log_filename_history else FILES.LOGS.ACTIVE
    if not filename:
        filename = logging_base_name
        if not filename:
            filename = FILES.LOGS.DEFAULT_NAME
    else:
        if filename[0] is '+':
            filename = filename[1:]
        filename = (logging_base_name + '-' if logging_base_name and logging_base_name[-1] != '\\' else '') + filename
    filename += filename_suffix
    if filename and filename.endswith(os.path.sep):
        filename += 'main'
    filename = re.sub(r'[^\w\-_\.\\]', '_', filename)
    if filter_disabled and not filter_logs(filename):
        return False
    filename += ('.' if filename and filename[-1] is not '.' else '') + extension
    full_path = os.path.join(FOLDERS.LOGS, filename)
    if prefix:
        parent, fn = os.path.split(full_path)
        if fn != '.' + extension:
            fn = '-' + fn
        full_path = os.path.join(parent, prefix + fn)
    full_path = os.path.abspath(full_path)
    if not os.path.exists(os.path.dirname(full_path)):
        os.makedirs(os.path.dirname(full_path))
    if as_url_link:
        return convert_filename_to_local_link(full_path)
    return full_path


def encode_log_text(content, encode_text=True, **kwargs):
    if not encode_text:
        return content
    try:
        return encode(content)
    except Exception:
        return content


def parse_log_content(content, prefix='', **kwargs):
    if content is None:
        return '', prefix
    if not is_str_type(content):
        content = pf(content, pf_replace_newline=False, pf_encode_text=False)
    if not content:
        content = '{EMPTY STRING}'
    if content.startswith("!"):
        content = content[1:]; prefix = '\n'
    return content, prefix


def process_log_content(content, prefix='', timestamp=None, do_encode=True, **kwargs):
    content = pad_lines_regex(content, timestamp=timestamp, **kwargs)
    st = '[%s]:\t' % datetime.now().strftime(ANKNOTES.DATE_FORMAT) if timestamp else ''
    return prefix + ' ' + st + (encode_log_text(content, **kwargs) if do_encode else content), content


def crosspost_log(content, filename=None, crosspost_to_default=False, crosspost=None, do_show_tooltip=False, **kwargs):
    if crosspost_to_default and filename:
        summary = " ** %s%s: " % ('' if filename.upper() == 'ERROR' else 'CROSS-POST TO ', filename.upper()) + content
        log(summary[:200], **kwargs)
    if do_show_tooltip:
        show_tooltip(content)
    if not crosspost:
        return
    for fn in item_to_list(crosspost):
        log(content, fn, **kwargs)


def pad_lines_regex(content, timestamp=None, replace_newline=None, try_decode=True, **kwargs):
    content = PadLines(content, **kwargs)
    if not (timestamp and replace_newline is not False) and not replace_newline:
        return content
    try:
        return re.sub(r'[\r\n]+', u'\n' + ANKNOTES.FORMATTING.TIMESTAMP_PAD, content)
    except UnicodeDecodeError:
        if not try_decode:
            raise
    return re.sub(r'[\r\n]+', u'\n' + ANKNOTES.FORMATTING.TIMESTAMP_PAD, decode(content))

# @clockit
def log(content=None, filename=None, **kwargs):
    kwargs = Args(kwargs).set_kwargs('line_padding, line_padding_plus, line_padding_header', timestamp=True)
    write_file_contents('Log Args: ' + str(kwargs.items()), 'args\\log_kwargs', get_log_full_path=get_log_full_path)
    content, prefix = parse_log_content(content, **kwargs)
    crosspost_log(content, filename, **kwargs)
    full_path = get_log_full_path(filename, **kwargs)
    if full_path is False:
        return
    content, print_content = process_log_content(content, prefix, **kwargs)
    write_file_contents(content, full_path, print_content=print_content, get_log_full_path=get_log_full_path, **kwargs)


def log_sql(content, a=None, kw=None, self=None, sql_fn_prefix='', **kwargs):
    table = re.sub(r'[^A-Z_ ]', ' ', content.upper())
    table = ' %s ' % re.sub(' +', ' ', table).replace(' IF NOT EXISTS ', ' ').replace(' IF EXISTS ', ' ').strip()
    if table.startswith('CREATE') or table.startswith('DROP'):
        table = 'TABLES'
    else:
        for stmt in ' WHERE , VALUES '.split(','):
            i = table.find(stmt)
            if i > -1:
                table = table[:i]
        found = (-1, None)
        for stmt in ' FROM , INTO , UPDATE , TABLE '.split(','):
            i = table.find(stmt)
            if i is -1:
                continue
            if i > found[0] > -1:
                continue
            found = (i, stmt)
        if found[0] > -1:
            table = table[found[0] + len(found[1]):].strip()
        if ' ' in table:
            table = table[:table.find(' ')]
    if a or kw:
        content = u"SQL: %s" % content
        if self:
            content += u"\n\nSelf:   " + pf(self, pf_encode_text=False, pf_decode_text=True)
        if a:
            content += u"\n\nArgs:   " + pf(a, pf_encode_text=False, pf_decode_text=True)
        if kw:
            content += u"\n\nKwargs: " + pf(kw, pf_encode_text=False, pf_decode_text=True)
    log(content, 'sql\\' + sql_fn_prefix + table, **kwargs)


def log_error(content, *a, **kw):
    kwargs = Args(a, kw, set_list=['crosspost_to_default', True], use_set_list_as_arg_list=True, require_all_args=False).kwargs
    log(content, 'error', **kwargs)


def pf(obj, title='', pf_replace_newline=True, pf_encode_text=True, pf_decode_text=False, *a, **kw):
    content = pprint.pformat(obj, indent=4, width=ANKNOTES.FORMATTING.PPRINT_WIDTH)
    content = content.replace(', ', ', \n ')
    if pf_replace_newline:
        content = content.replace('\r', '\r' + ' ' * 30).replace('\n', '\n' + ' ' * 30)
    if pf_encode_text:
        content = encode_log_text(content)
    elif pf_decode_text:
        content = decode(content, errors='ignore')
    if title:
        content = title + ": " + content
    return content


def print_dump(*a, **kw):
    content = pf(*a, **kw)
    print content
    return content


pp = print_dump


def log_dump(obj, title="Object", filename='', crosspost_to_default=True, **kwargs):
    content = pprint.pformat(obj, indent=4, width=ANKNOTES.FORMATTING.PPRINT_WIDTH)
    try:
        content = decode(content, errors='ignore')
    except Exception:
        pass
    content = content.replace("\\n", '\n').replace('\\r', '\r')
    if filename and filename[0] is '+':
        summary = " ** CROSS-POST TO %s: " % filename[1:] + content
        log(summary[:200])
    full_path = get_log_full_path(filename, prefix='dump', **kwargs)
    if full_path is False:
        return
    if not title:
        title = "<%s>" % obj.__class__.__name__
    if title.startswith('-'):
        crosspost_to_default = False; title = title[1:]
    prefix = " **** Dumping %s" % title
    if crosspost_to_default:
        log(prefix + + " to " + os.path.splitext(full_path.replace(FOLDERS.LOGS + os.path.sep, ''))[0])

    content = encode_log_text(content)

    try:
        prefix += '\r\n'
        content = prefix + content.replace(', ', ', \n ')
        content = content.replace("': {", "': {\n ")
        content = content.replace('\r', '\r' + ' ' * 30).replace('\n', '\n' + ' ' * 30)
    except Exception:
        pass

    if not os.path.exists(os.path.dirname(full_path)):
        os.makedirs(os.path.dirname(full_path))
    try_print(full_path, content, prefix, **kwargs)


def try_print(full_path, content, prefix='', line_prefix=u'\n ', attempt=0, clear=False, timestamp=True, **kwargs):
    try:
        st = '[%s]: ' % datetime.now().strftime(ANKNOTES.DATE_FORMAT) if timestamp else ''
        print_content = line_prefix + (u' <%d>' % attempt if attempt > 0 else u'') + u' ' + st
        if attempt is 0:
            print_content += content
        elif attempt is 1:
            print_content += decode(content)
        elif attempt is 2:
            print_content += encode(content)
        elif attempt is 3:
            print_content = encode(print_content) + encode(content)
        elif attempt is 4:
            print_content = decode(print_content) + decode(content)
        elif attempt is 5:
            print_content += "Error printing content: " + str_safe(content)
        elif attempt is 6:
            print_content += "Error printing content: " + content[:10]
        elif attempt is 7:
            print_content += "Unable to print content."
        with open(full_path, 'w+' if clear else 'a+') as fileLog:
            print>> fileLog, print_content
    except Exception as e:
        if attempt < 8:
            try_print(full_path, content, prefix=prefix, line_prefix=line_prefix, attempt=attempt + 1,
                                  clear=clear)
        else:
            log("Try print error to %s: %s" % (os.path.split(full_path)[1], str(e)))


def log_api(method, content='', **kw):
    if content:
        content = ': ' + content
    log(" API_CALL [%3d]: %10s%s" % (get_api_call_count(), method, content), 'api', **kw)


def get_api_call_count():
    path = get_log_full_path('api')
    if path is False or not os.path.exists(path):
        return 0
    api_log = file(path, 'r').read().splitlines()
    count = 1
    for i in range(len(api_log), 0, -1):
        call = api_log[i - 1]
        if "API_CALL" not in call:
            continue
        ts = call.replace(':\t', ': ').split(': ')[0][2:-1]
        td = datetime.now() - datetime.strptime(ts, ANKNOTES.DATE_FORMAT)
        if td >= timedelta(hours=1):
            break
        count += 1
    return count
