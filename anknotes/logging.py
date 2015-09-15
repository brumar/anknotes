### Python Imports
from datetime import datetime, timedelta
import difflib
import pprint
import re

### Anknotes Shared Imports
from anknotes.constants import *
from anknotes.graphics import *

### Anki Imports
try:
        from aqt import mw
        from aqt.utils import tooltip
        from aqt.qt import QMessageBox, QPushButton
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


def show_tooltip(text, time_out=3000, delay=None):
    if delay:
        try:
            return mw.progress.timer(delay, lambda: tooltip(text, time_out), False)
        except:
            pass
    tooltip(text, time_out)


def report_tooltip(log_title, log_text="", delay=None, prefix='- '):
    str_tip = log_text
    if not str_tip:
        str_tip = log_title

    show_tooltip(str_tip, delay=delay)

    if log_title:
        log_title += ": "
        delimit = "-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"
        if log_text:
            log_text = delimit + "<BR>%s\n" % log_text
        log(log_title)
    log_text = log_text.replace('<BR><BR>', '<BR>').replace('<BR>', '\n   ' + prefix )
    log(log_text, timestamp=False, replace_newline=True)


def showInfo(message, title="Anknotes: Evernote Importer for Anki", textFormat=0):
    global imgEvernoteWebMsgBox, icoEvernoteArtcore
    msgDefaultButton = QPushButton(icoEvernoteArtcore, "Okay!", mw)

    if not isinstance(message, str) and not isinstance(message, unicode):
        message = str(message)

    messageBox = QMessageBox()
    messageBox.addButton(msgDefaultButton, QMessageBox.AcceptRole)
    messageBox.setDefaultButton(msgDefaultButton)
    messageBox.setIconPixmap(imgEvernoteWebMsgBox)
    messageBox.setTextFormat(textFormat)
    messageBox.setText(message)
    messageBox.setWindowTitle(title)
    messageBox.exec_()


def diffify(content):
    for tag in ['div', 'ol', 'ul', 'li']:
        content = content.replace("<" + tag, "\n<" + tag).replace("</%s>" % tag, "</%s>\n" % tag)
    content = re.sub(r'[\r\n]+', '\n', content)
    return content.splitlines()


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


def log(content='', filename='', prefix='', clear=False, timestamp=True, extension='log', blank=False,
        replace_newline=None):
    if blank:
        filename = content
        content = ''
        timestamp = False
    else:
        content = obj2log_simple(content)
        if len(content) == 0: content = '{EMPTY STRING}'
        if content[0] == "!":
            content = content[1:]
            prefix = '\n'
    if not filename:
        filename = ANKNOTES.LOG_BASE_NAME + '.' + extension
    else:
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = ANKNOTES.LOG_BASE_NAME + '-%s.%s' % (filename, extension)
    try:
        content = content.encode('utf-8')
    except Exception:
        pass
    if timestamp or replace_newline is True:
        content = content.replace('\r', '\r                              ').replace('\n',
                                                                                    '\n                              ')
    if timestamp:
        st = '[%s]: ' % datetime.now().strftime(ANKNOTES.DATE_FORMAT)
    else:
        st = ''
    full_path = os.path.join(ANKNOTES.FOLDER_LOGS, filename)
    if not os.path.exists(os.path.dirname(full_path)):
        os.mkdir(os.path.dirname(full_path))
    with open(full_path, 'w+' if clear else 'a+') as fileLog:
        print>> fileLog, prefix + ' ' + st + content


log("Log Loaded", "load")


def log_sql(value):
    log(value, 'sql')


def log_error(value):
    log(value, '+error')


def print_dump(obj):
    content = pprint.pformat(obj, indent=4, width=80)
    content = content.replace(', ', ', \n ')
    content = content.replace('\r', '\r                              ').replace('\n',
                                                                                '\n                              ')
    if isinstance(content, str):
        content = unicode(content, 'utf-8')
    print content


def log_dump(obj, title="Object", filename='', clear=False, timestamp=True):
    content = pprint.pformat(obj, indent=4, width=80)
    if not filename:
        filename = ANKNOTES.LOG_BASE_NAME + '-dump.log'
    else:
        if filename[0] is '+':
            filename = filename[1:]
            # noinspection PyUnboundLocalVariable
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = ANKNOTES.LOG_BASE_NAME + '-dump-%s.log' % filename
    try:
        content = content.encode('ascii', 'ignore')
    except Exception:
        pass
    st = ''
    if timestamp:
        st = datetime.now().strftime(ANKNOTES.DATE_FORMAT)
        st = '[%s]: ' % st

    if title[0] == '-':
        prefix = " **** Dumping %s" % title[1:]
    else:
        prefix = " **** Dumping %s" % title
        log(prefix)
    prefix += '\r\n'
    content = prefix + content.replace(', ', ', \n ')
    content = content.replace("': {", "': {\n ")
    content = content.replace('\r', '\r                              ').replace('\n',
                                                                                '\n                              ')
    full_path = os.path.join(ANKNOTES.FOLDER_LOGS, filename)
    if isinstance(content, str):
        content = unicode(content, 'utf-8')
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
        ts = call.split(': ')[0][2:-1]
        td = datetime.now() - datetime.strptime(ts, ANKNOTES.DATE_FORMAT)
        if td < timedelta(hours=1):
            count += 1
        else:
            return count
    return count
