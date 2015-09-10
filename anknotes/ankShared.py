# -*- coding: utf-8 -*-
import os
import os.path
import re
import pprint
from HTMLParser import HTMLParser
from datetime import datetime, timedelta
import shutil
import time
import errno
import socket
import copy
import ankConsts as ank
try:  from aqt import mw
except: pass
try:    from pysqlite2 import dbapi2 as sqlite
except ImportError: from sqlite3 import dbapi2 as sqlite
try:  from aqt.qt import QIcon, QPixmap, QPushButton, QMessageBox
except: pass 

class UpdateExistingNotes:
    IgnoreExistingNotes, UpdateNotesInPlace, DeleteAndReAddNotes = range(3)
    
class EvernoteQueryLocationType:
    RelativeDay, RelativeWeek, RelativeMonth, RelativeYear, AbsoluteDate, AbsoluteDateTime = range(6)
    
class RateLimitErrorHandling:
    IgnoreError, ToolTipError, AlertError = range(3)  
    
ankNotesDBInstance = None
dbLocal = False     

def ankDB():
    global ankNotesDBInstance, dbLocal
    if not ankNotesDBInstance: 
        if dbLocal: ankNotesDBInstance = ank_DB(os.path.join(ank.PATH, '..\\..\\Evernote\\collection.anki2'))        
        else:  ankNotesDBInstance = ank_DB()        
    return ankNotesDBInstance

def showInfo(message, title="Anknotes: Evernote Importer for Anki", textFormat = 0):
    global imgEvernoteWebMsgBox, icoEvernoteArtcore
    msgDefaultButton = QPushButton(icoEvernoteArtcore, "Okay!", mw) 
    messageBox = QMessageBox()       
    messageBox.addButton(msgDefaultButton, QMessageBox.AcceptRole)
    messageBox.setDefaultButton(msgDefaultButton)
    messageBox.setIconPixmap(imgEvernoteWebMsgBox)
    messageBox.setTextFormat(textFormat)
    messageBox.setText(message)
    messageBox.setWindowTitle(title)
    messageBox.exec_()


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def str_safe(strr, prefix=''):
    try: strr= str((prefix + strr.__repr__()))
    except: strr= str((prefix + strr.__repr__().encode('utf8', 'replace')))
    return strr
    
def print_safe(strr, prefix=''):
    print str_safe(strr, prefix)            
        
def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()
    
def strip_tags_and_new_lines(html):
    return strip_tags(html).replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

def find_evernote_links(content):
    # .NET regex saved to regex.txt as 'Finding Evernote Links'
    return re.finditer(r'<a href="(?P<URL>evernote:///?view/(?P<uid>[\d]+?)/(?P<shard>s\d+)/(?P<guid>[\w\-]+?)/(?P=guid)/?)"(?: shape="rect")?(?: style="[^\"].+?")?(?: shape="rect")?>(?P<Title>.+?)</a>', content)        
    


def log(content, filename='', prefix=''):
    if content[0] == "!":
        content = content[1:]
        prefix = '\n'        
    if not filename: filename = ank.ANKNOTES.LOG_BASE_NAME + '.log'
    else: 
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = ank.ANKNOTES.LOG_BASE_NAME + '-%s.log' % filename        
    try:
        content=content.encode('ascii', 'ignore')       
    except Exception:
        pass
    content = content.replace('\r', '\r                              ').replace('\n', '\n                              ')    
    st = str(datetime.now()).split('.')[0]
    full_path = os.path.join(ank.ANKNOTES.FOLDER_LOGS, filename)
    if not os.path.exists(os.path.dirname(full_path)): 
        os.mkdir(os.path.dirname(full_path))
    with open(full_path , 'a+') as fileLog:
        print>>fileLog, prefix + ' [%s]: ' % st + content 
    
def log_sql(value):
    log(value, 'sql')

def log_error(value):
    log(value, '+error')    
    
def print_dump(obj):
    content = pprint.pformat(obj, indent=4, width=80)  
    content = content.replace(', ', ', \n ')
    content = content.replace('\r', '\r                              ').replace('\n', '\n                              ')
    if isinstance(content , str):
        content = unicode(content , 'utf-8')       
    print content 
    
def log_dump(obj, title="Object", filename=''):
    if not filename: filename = ank.ANKNOTES.LOG_BASE_NAME + '-dump.log'
    else: 
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = ank.ANKNOTES.LOG_BASE_NAME + '-dump-%s.log' % filename
    content = pprint.pformat(obj, indent=4, width=80)
    try:
        content=content.encode('ascii', 'ignore') 
    except Exception:
        pass
    st = str(datetime.now()).split('.')[0]    
    if title[0] == '-':
        prefix = " **** Dumping %s" % title[1:]
    else:        
        prefix = " **** Dumping %s" % title
        log(prefix)
    prefix += '\r\n' 
    content = prefix + content.replace(', ', ', \n ')
    content = content.replace('\r', '\r                              ').replace('\n', '\n                              ')
    full_path = os.path.join(ank.ANKNOTES.FOLDER_LOGS, filename)
    if isinstance(content , str):
        content = unicode(content , 'utf-8')          
    if not os.path.exists(os.path.dirname(full_path)): 
        os.mkdir(os.path.dirname(full_path))
    with open(full_path, 'a+') as fileLog:
        try:
            print>>fileLog, (u'\n [%s]: %s' % (st, content))
        except:
            print>>fileLog, (u'\n [%s]: %s' % (st, "Error printing content: " + content[:10]))

def get_dict_from_list(list, keys_to_ignore=list()):
    dict = {}
    for key, value in list: 
        if not key in keys_to_ignore: dict[key] = value  
    return dict 
    
def get_evernote_guid_from_anki_fields(fields):        
    if not ank.FIELDS.EVERNOTE_GUID in fields: return None
    return fields[ank.FIELDS.EVERNOTE_GUID].replace(ank.FIELDS.EVERNOTE_GUID_PREFIX, '')        
    
class ank_DB(object):
    def __init__(self, path = None, text=None, timeout=0):
        encpath = path
        if isinstance(encpath, unicode):
            encpath = path.encode("utf-8")
        if path:
            self._db = sqlite.connect(encpath, timeout=timeout)
            self._db.row_factory = sqlite.Row
            if text:
                self._db.text_factory = text
            self._path = path
        else:
            self._db = mw.col.db._db
            self._path = mw.col.db._path
        self.echo = os.environ.get("DBECHO")
        self.mod = False

    def execute(self, sql, *a, **ka):
        s = sql.strip().lower()
        # mark modified?
        for stmt in "insert", "update", "delete":
            if s.startswith(stmt):
                self.mod = True
        t = time.time()
        if ka:
            # execute("...where id = :id", id=5)
            res = self._db.execute(sql, ka)
        elif a:
            # execute("...where id = ?", 5)
            res = self._db.execute(sql, a)
        else:
            res = self._db.execute(sql)
        if self.echo:
            #print a, ka
            print sql, "%0.3fms" % ((time.time() - t)*1000)
            if self.echo == "2":
                print a, ka
        return res

    def executemany(self, sql, l):
        self.mod = True
        t = time.time()
        self._db.executemany(sql, l)
        if self.echo:
            print sql, "%0.3fms" % ((time.time() - t)*1000)
            if self.echo == "2":
                print l

    def commit(self):
        t = time.time()
        self._db.commit()
        if self.echo:
            print "commit %0.3fms" % ((time.time() - t)*1000)

    def executescript(self, sql):
        self.mod = True
        if self.echo:
            print sql
        self._db.executescript(sql)

    def rollback(self):
        self._db.rollback()

    def scalar(self, *a, **kw):
        res = self.execute(*a, **kw).fetchone()
        if res:
            return res[0]
        return None

    def all(self, *a, **kw):
        return self.execute(*a, **kw).fetchall()

    def first(self, *a, **kw):
        c = self.execute(*a, **kw)
        res = c.fetchone()
        c.close()
        return res

    def list(self, *a, **kw):
        return [x[0] for x in self.execute(*a, **kw)]

    def close(self):
        self._db.close()

    def set_progress_handler(self, *args):
        self._db.set_progress_handler(*args)

    def __enter__(self):
        self._db.execute("begin")
        return self

    def __exit__(self, exc_type, *args):
        self._db.close()

    def totalChanges(self):
        return self._db.total_changes

    def interrupt(self):
        self._db.interrupt()
        
    def InitTags(self, force = False):
        if_exists = " IF NOT EXISTS" if not force else ""
        self.execute("""CREATE TABLE %s `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `parentGuid` TEXT, `updateSequenceNum` INTEGER NOT NULL, PRIMARY KEY(guid) );""" % (if_exists,ank.TABLES.EVERNOTE.TAGS)) 
        
    def InitNotebooks(self, force = False):
        if_exists = " IF NOT EXISTS" if not force else ""
        self.execute("""CREATE TABLE %s `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `serviceUpdated` INTEGER NOT NULL, `stack` TEXT, PRIMARY KEY(guid) );""" % (if_exists, ank.TABLES.EVERNOTE.NOTEBOOKS))
        
    def Init(self):
        self.execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL, PRIMARY KEY(guid) );""" % ank.TABLES.EVERNOTE.NOTES)
        self.execute( """CREATE TABLE IF NOT EXISTS `%s` ( `id` INTEGER, `source_evernote_guid` TEXT NOT NULL, `number` INTEGER NOT NULL DEFAULT 100, `uid` INTEGER NOT NULL DEFAULT -1, `shard` TEXT NOT NULL DEFAULT -1, `target_evernote_guid` TEXT NOT NULL, `html` TEXT NOT NULL, `title` TEXT NOT NULL, `from_toc` INTEGER DEFAULT 0, `is_toc` INTEGER DEFAULT 0, `is_outline` INTEGER DEFAULT 0, PRIMARY KEY(id) );""" % ank.TABLES.SEE_ALSO) 
        self.InitTags()
        self.InitNotebooks()        
        
def testMethodAvi():
    print "Working"

def HandleSocketError(e, strError):
    errorcode = e[0]
    if errorcode==errno.ECONNREFUSED:
        strError = "Error: Connection was refused while %s\r\n" % strError
        "Please retry your request a few minutes"
        log_prefix = 'ECONNREFUSED'
    elif errorcode==10060:
        strError = "Error: Connection timed out while %s\r\n" % strError
        "Please retry your request a few minutes"
        log_prefix = 'ETIMEDOUT'    
    else: return False
    log_error( " SocketError.%s:  "  % log_prefix + strError)    
    log( " SocketError.%s:  "  % log_prefix + strError, 'api')         
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
        show_tooltip(strError)
    return True

def HandleEDAMRateLimitError(e, strError):
    if not e.errorCode is EDAMErrorCode.RATE_LIMIT_REACHED:
        return False
    m, s = divmod(e.rateLimitDuration, 60)
    strError = "Error: Rate limit has been reached while %s\r\n" % strError
    strError += "Please retry your request in {} min".format("%d:%02d" %(m, s))
    log_strError = " EDAMErrorCode.RATE_LIMIT_REACHED:  " + strError.replace('\r\n', '\n')
    log_error(log_strError)    
    log(log_strError, 'api')    
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
        show_tooltip(strError)
    return True

regex_see_also = None 
def update_regex():
    global regex_see_also    
    regex_str = file( os.path.join(ank.ANKNOTES.FOLDER_ANCILLARY, 'regex-see_also.txt'), 'r').read()    
    regex_str = regex_str.replace('(?<', '(?P<')
    regex_see_also = re.compile(regex_str, re.UNICODE | re.VERBOSE | re.DOTALL)
    
try:
    icoEvernoteWeb = QIcon(ank.ANKNOTES.ICON_EVERNOTE_WEB)
    icoEvernoteArtcore = QIcon(ank.ANKNOTES.ICON_EVERNOTE_ARTCORE)
    imgEvernoteWeb = QPixmap(ank.ANKNOTES.IMAGE_EVERNOTE_WEB, "PNG")
    imgEvernoteWebMsgBox = imgEvernoteWeb.scaledToWidth(64)                
except: pass 