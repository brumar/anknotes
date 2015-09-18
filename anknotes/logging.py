# Python Imports
from datetime import datetime, timedelta
import difflib
import pprint
import re

# Anknotes Shared Imports
from anknotes.constants import *
from anknotes.graphics import *

# Anki Imports
try:
    from aqt import mw
    from aqt.utils import tooltip
    from aqt.qt import QMessageBox, QPushButton, QSizePolicy, QSpacerItem, QGridLayout, QLayout
except:
    pass


def str_safe(strr, prefix=''):
    try:
        strr = str((prefix + strr.__repr__()))
    except:
        strr = str((prefix + strr.__repr__().encode('utf8', 'replace')))
    return strr


def print_safe(strr, prefix=''):
    print str_safe(strr, prefix)


def show_tooltip(text, time_out=7000, delay=None):
    if delay:
        try:
            return mw.progress.timer(delay, lambda: tooltip(text, time_out), False)
        except:
            pass
    tooltip(text, time_out)

def counts_as_str(count, max=None):
    if max is None: return pad_center(count, 3)
    if count == max: return "All  %s" % (pad_center(count, 3))
    return "Total %s of %s" % (pad_center(count, 3), pad_center(max, 3))

def show_report(title, header, log_lines=[], delay=None, log_header_prefix = ' '*5):
    lines = []
    for line in ('<BR>'.join(header) if isinstance(header, list) else header).split('<BR>') + ('<BR>'.join(log_lines).split('<BR>') if log_lines else []):
        level = 0
        while line and line[level] is '-': level += 1
        lines.append('\t'*level + ('\t\t- ' if lines else '') + line[level:])
    if len(lines) > 1: lines[0] += ': '
    log_text = '<BR>'.join(lines)
    show_tooltip(log_text.replace('\t', '&nbsp; '), delay=delay)
    log_blank()
    log(title)
    log(" " + "-" * 192 + '\n' + log_header_prefix + log_text.replace('<BR>', '\n'), timestamp=False, replace_newline=True)
    log_blank()


def showInfo(message, title="Anknotes: Evernote Importer for Anki", textFormat=0, cancelButton=False, richText=False, minHeight=None, minWidth=400, styleSheet=None, convertNewLines=True):
    global imgEvernoteWebMsgBox, icoEvernoteArtcore, icoEvernoteWeb
    msgDefaultButton = QPushButton(icoEvernoteArtcore, "Okay!", mw)
    msgCancelButton = QPushButton(icoTomato, "No Thanks", mw)
    if not styleSheet:
        styleSheet = file(ANKNOTES.QT_CSS_QMESSAGEBOX, 'r').read()

    if not isinstance(message, str) and not isinstance(message, unicode):
        message = str(message)

    if richText:
        textFormat = 1
        message = message.replace('\n', '<BR>\n')
        message = '<style>\n%s</style>\n\n%s' % (styleSheet, message)
    global messageBox
    messageBox = QMessageBox()
    messageBox.addButton(msgDefaultButton, QMessageBox.AcceptRole)
    if cancelButton:
        messageBox.addButton(msgCancelButton, QMessageBox.RejectRole)
    messageBox.setDefaultButton(msgDefaultButton)
    messageBox.setIconPixmap(imgEvernoteWebMsgBox)
    messageBox.setTextFormat(textFormat)

    # message = ' %s %s' % (styleSheet, message)
    # log(message, replace_newline=False)
    messageBox.setWindowIcon(icoEvernoteWeb)
    messageBox.setWindowIconText("Anknotes")
    messageBox.setText(message)
    messageBox.setWindowTitle(title)
    # if minHeight:
    #     messageBox.setMinimumHeight(minHeight)
    # messageBox.setMinimumWidth(minWidth)
    #
    # messageBox.setFixedWidth(1000)
    hSpacer = QSpacerItem(minWidth, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

    layout = messageBox.layout()
    """:type : QGridLayout """
    # layout.addItem(hSpacer, layout.rowCount() + 1, 0, 1, layout.columnCount())
    layout.addItem(hSpacer, layout.rowCount() + 1, 0, 1, layout.columnCount())
    # messageBox.setStyleSheet(styleSheet)


    ret = messageBox.exec_()
    if not cancelButton:
        return True
    if messageBox.clickedButton() == msgCancelButton or messageBox.clickedButton() == 0:
        return False
    return True

def diffify(content):
    for tag in ['div', 'ol', 'ul', 'li']:
        content = content.replace("<" + tag, "\n<" + tag).replace("</%s>" % tag, "</%s>\n" % tag)
    content = re.sub(r'[\r\n]+', '\n', content)
    return content.splitlines()

def pad_center(val, length=20, favor_right=True):
    val = str(val)
    pad = max(length - len(val), 0)
    pads = [int(round(float(pad) / 2))]*2
    if sum(pads) > pad: pads[favor_right] -= 1
    return ' ' * pads[0] + val + ' ' * pads[1]

def generate_diff(value_original, value):
    try:
        return '\n'.join(list(difflib.unified_diff(diffify(value_original), diffify(value), lineterm='')))
    except:
        pass
    try:
        return '\n'.join(
            list(difflib.unified_diff(diffify(value_original.decode('utf-8')), diffify(value), lineterm='')))
    except:
        pass
    try:
        return '\n'.join(
            list(difflib.unified_diff(diffify(value_original), diffify(value.decode('utf-8')), lineterm='')))
    except:
        pass
    try:
        return '\n'.join(list(
            difflib.unified_diff(diffify(value_original.decode('utf-8')), diffify(value.decode('utf-8')), lineterm='')))
    except:
        raise


def obj2log_simple(content):
    if not isinstance(content, str) and not isinstance(content, unicode):
        content = str(content)
    return content

def convert_filename_to_local_link(filename):
    return 'file:///' + filename.replace("\\", "//")

def log_blank(filename='', clear=False, extension='log'):
    log(timestamp=False, filename=filename, clear=clear, extension=extension)


def log_plain(content=None, filename='', prefix='', clear=False, extension='log',
              replace_newline=None, do_print=False):
    log(timestamp=False, content=content, filename=filename, prefix=prefix, clear=clear, extension=extension,
        replace_newline=replace_newline, do_print=do_print)

def log_banner(title, filename, length=80, append_newline=True):
    log("-" * length, filename, clear=True, timestamp=False)
    log(pad_center(title, length),filename, timestamp=False)
    log("-" * length, filename, timestamp=False)
    if append_newline: log_blank(filename)

def get_log_full_path(filename='', extension='log', as_url_link=False):
    if not filename:
        filename = ANKNOTES.LOG_BASE_NAME + '.' + extension
    else:
        if filename[0] is '+':
            filename = filename[1:]
        filename = ANKNOTES.LOG_BASE_NAME + '-%s.%s' % (filename, extension)
    full_path = os.path.join(ANKNOTES.FOLDER_LOGS, filename)
    if as_url_link: return convert_filename_to_local_link(full_path)
    return full_path

def log(content=None, filename='', prefix='', clear=False, timestamp=True, extension='log',
        replace_newline=None, do_print=False):
    if content is None: content = ''
    else:
        content = obj2log_simple(content)
        if len(content) == 0: content = '{EMPTY STRING}'
        if content[0] == "!":
            content = content[1:]
            prefix = '\n'
    if filename and filename[0] is '+':
        # filename = filename[1:]
        summary = " ** CROSS-POST TO %s: " % filename[1:] + content
        log(summary[:200])
    full_path = get_log_full_path(filename, extension)
    try:
        content = content.encode('utf-8')
    except Exception:
        pass
    if timestamp or replace_newline is True:
        spacer = '\t'*6
        content = content.replace('\r\n', '\n').replace('\r', '\r'+spacer).replace('\n', '\n'+spacer)
    if timestamp:
        st = '[%s]:\t' % datetime.now().strftime(ANKNOTES.DATE_FORMAT)
    else:
        st = ''
    if not os.path.exists(os.path.dirname(full_path)):
        os.mkdir(os.path.dirname(full_path))
    with open(full_path, 'w+' if clear else 'a+') as fileLog:
        print>> fileLog, prefix + ' ' + st + content
    if do_print:
        print prefix + ' ' + st + content

def log_sql(value):
    log(value, 'sql')

def log_error(value, crossPost=True):
    log(value, '+' if crossPost else '' + 'error')


def print_dump(obj):
    content = pprint.pformat(obj, indent=4, width=80)
    content = content.replace(', ', ', \n ')
    content = content.replace('\r', '\r                              ').replace('\n',
                                                                                '\n                              ')
    if isinstance(content, str):
        content = unicode(content, 'utf-8')
    print content


def log_dump(obj, title="Object", filename='', clear=False, timestamp=True, extension='.log'):
    content = pprint.pformat(obj, indent=4, width=80)
    try: content = content.decode('utf-8', 'ignore')
    except Exception: pass
    if filename and filename[0] is '+':
        summary = " ** CROSS-POST TO %s: " % filename[1:] + content
        log(summary[:200])
    filename = 'dump' + ('-%s' % filename) if filename else ''
    full_path = get_log_full_path(filename, extension)
    st = ''
    if timestamp:
        st = datetime.now().strftime(ANKNOTES.DATE_FORMAT)
        st = '[%s]: ' % st

    if title[0] == '-':
        prefix = " **** Dumping %s" % title[1:]
    else:
        prefix = " **** Dumping %s" % title
        log(prefix)

    if isinstance(content, str):
        content = unicode(content, 'utf-8')

    try:
        prefix += '\r\n'
        content = prefix + content.replace(', ', ', \n ')
        content = content.replace("': {", "': {\n ")
        content = content.replace('\r', '\r                              ').replace('\n',
                                                                                    '\n                              ')
    except:
        pass

    if not os.path.exists(os.path.dirname(full_path)):
        os.mkdir(os.path.dirname(full_path))
    with open(full_path, 'w+' if clear else 'a+') as fileLog:
        try:
            print>> fileLog, (u'\n %s%s' % (st, content))
            return
        except:
            pass
        try:
            print>> fileLog, (u'\n <1> %s%s' % (st, content.decode('utf-8')))
            return
        except:
            pass
        try:
            print>> fileLog, (u'\n <2> %s%s' % (st, content.encode('utf-8')))
        except:
            pass
        try:
            print>> fileLog, ('\n <3> %s%s' % (st, content.decode('utf-8')))
            return
        except:
            pass
        try:
            print>> fileLog, ('\n <4> %s%s' % (st, content.encode('utf-8')))
            return
        except:
            pass
        try:
            print>> fileLog, (u'\n %s%s' % (st, "Error printing content: " + str_safe(content)))
            return
        except:
            pass
        print>> fileLog, (u'\n %s%s' % (st, "Error printing content: " + content[:10]))


def log_api(method, content=''):
    if content: content = ': ' + content
    log(" API_CALL [%3d]: %10s%s" % (get_api_call_count(), method, content), 'api')


def get_api_call_count():
    api_log = file(os.path.join(ANKNOTES.FOLDER_LOGS, ANKNOTES.LOG_BASE_NAME + '-api.log'), 'r').read().splitlines()
    count = 1
    for i in range(len(api_log), 0, -1):
        call = api_log[i - 1]
        if not "API_CALL" in call:
            continue
        ts = call.replace(':\t', ': ').split(': ')[0][2:-1]
        td = datetime.now() - datetime.strptime(ts, ANKNOTES.DATE_FORMAT)
        if td < timedelta(hours=1):
            count += 1
        else:
            return count
    return count

log('completed %s' % __name__, 'import')