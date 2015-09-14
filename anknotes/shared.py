# -*- coding: utf-8 -*-
### Python Imports
from HTMLParser import HTMLParser
import errno
try:    from pysqlite2 import dbapi2 as sqlite
except ImportError: from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
from anknotes.db import *
from anknotes.logging import *
from anknotes.constants import*
from anknotes.enums import *

### Anki and Evernote Imports
try:
    from aqt import mw
    from aqt.qt import QIcon, QPixmap, QPushButton, QMessageBox
    from aqt.utils import tooltip
    from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode, EDAMUserException, EDAMNotFoundException
except: pass

class RateLimitErrorHandling:
    IgnoreError, ToolTipError, AlertError = range(3)  
EDAM_RATE_LIMIT_ERROR_HANDLING = RateLimitErrorHandling.ToolTipError


def get_friendly_interval_string(lastImport):
    if not lastImport: return ""
    td = (datetime.now() - datetime.strptime(lastImport, ANKNOTES.DATE_FORMAT))
    days = td.days
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 1:
        lastImportStr = "%d days" % td.days
    else:
        hours = round(hours)
        hours_str = '' if hours == 0 else 'One Hour' if hours == 1 else '%d Hours' % hours 
        if days == 1:
            lastImportStr = "One Day%s" % ('' if hours == 0 else ', ' + hours_str)
        elif hours > 0:
            lastImportStr = hours_str                 
        else:
            lastImportStr = "%d:%02d min" % (minutes, seconds)    
    return lastImportStr


class UpdateExistingNotes:
    IgnoreExistingNotes, UpdateNotesInPlace, DeleteAndReAddNotes = range(3)
    
class EvernoteQueryLocationType:
    RelativeDay, RelativeWeek, RelativeMonth, RelativeYear, AbsoluteDate, AbsoluteDateTime = range(6)


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()
    
def strip_tags_and_new_lines(html):
    return strip_tags(html).replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

class EvernoteAccountIDs:
    uid = '0'
    shard = 's100'
    valid = False 
    def __init__(self, uid=None,shard=None):
        self.valid = False 
        if uid and shard:
            if self.update(uid, shard): return 
        try:
            self.uid =  mw.col.conf.get(SETTINGS.EVERNOTE_ACCOUNT_UID, SETTINGS.EVERNOTE_ACCOUNT_UID_DEFAULT_VALUE)
            self.shard = mw.col.conf.get(SETTINGS.EVERNOTE_ACCOUNT_SHARD, SETTINGS.EVERNOTE_ACCOUNT_SHARD_DEFAULT_VALUE)
        except:
            self.uid = SETTINGS.EVERNOTE_ACCOUNT_UID_DEFAULT_VALUE
            self.shard = SETTINGS.EVERNOTE_ACCOUNT_SHARD_DEFAULT_VALUE
            return 
        
    def update(self, uid, shard):        
        if not uid or not shard: return False 
        if uid == '0' or shard == 's100': return False 
        try:
            mw.col.conf[SETTINGS.EVERNOTE_ACCOUNT_UID] = uid
            mw.col.conf[SETTINGS.EVERNOTE_ACCOUNT_SHARD] = shard
        except:
            return False 
        self.uid = uid 
        self.shard = shard 
        self.valid = True 
    
enAccountIDs = None     
  
def get_evernote_account_ids():
    global enAccountIDs 
    if not enAccountIDs:
        enAccountIDs = EvernoteAccountIDs()
    return enAccountIDs

def get_tag_names_to_import(tagNames, evernoteTags=None, evernoteTagsToDelete=None):
    if not evernoteTags:
        evernoteTags = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_TAGS, SETTINGS.EVERNOTE_QUERY_TAGS_DEFAULT_VALUE).split(",") if mw.col.conf.get(SETTINGS.DELETE_EVERNOTE_TAGS_TO_IMPORT, True) else []
    if not evernoteTagsToDelete:
        evernoteTagsToDelete = mw.col.conf.get(SETTINGS.EVERNOTE_TAGS_TO_DELETE, "").split(",")                  
    if isinstance(tagNames, dict):
        return {k: v for k, v in tagNames.items() if v not in evernoteTags and v not in evernoteTagsToDelete}           
    return sorted([v for v in tagNames if v not in evernoteTags and v not in evernoteTagsToDelete], key=lambda s: s.lower())
    
    
def find_evernote_links_as_guids(content):
    return [x.group('guid') for x in find_evernote_links(content)]
    
def find_evernote_links(content):
    # .NET regex saved to regex.txt as 'Finding Evernote Links'
    
    regex_str = r'<a href="(?P<URL>evernote:///?view/(?P<uid>[\d]+?)/(?P<shard>s\d+)/(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/(?P=guid)/?)"(?: shape="rect")?(?: style="[^\"].+?")?(?: shape="rect")?>(?P<Title>.+?)</a>'
    ids = get_evernote_account_ids()
    if not ids.valid:
        match = re.search(regex_str, content)
        if match:
            ids.update(match.group('uid'), match.group('shard'))
    return re.finditer(regex_str, content)        
    
def escape_text(title):
    repl = [u'&', u'&nbsp;', u'>', u'&gt;', u'<', u'&lt;']
    for i in range(0, len(repl), 2):
        title = title.replace(repl[i], repl[i+1])
    return title


def generate_evernote_url(guid):
    ids = get_evernote_account_ids()
    return u'evernote:///view/%s/%s/%s/%s/' % (ids.uid, ids.shard, guid, guid)
    
def generate_evernote_link_by_type(guid, title=None, link_type=None, value=None, escape=True):
    url = generate_evernote_url(guid)
    if not title: title = get_evernote_title_from_guid(guid)
    if escape: title = escape_text(title)
    style = generate_evernote_html_element_style_attribute(link_type, value)
    html = u"""<a href='%s'><span style='%s'>%s</span></a>""" % (url, style, title)
    # print html
    return html       
    
def generate_evernote_link(guid, title=None, value=None, escape=True):
    return generate_evernote_link_by_type(guid, title, 'Links', value, escape=escape)
    
def generate_evernote_link_by_level(guid, title=None, value=None, escape=True):
    return generate_evernote_link_by_type(guid, title, 'Levels', value, escape=escape)

def generate_evernote_html_element_style_attribute(link_type, value, bold=True, group=None):
    global evernote_link_colors
    colors = None 
    if link_type in evernote_link_colors:
        color_types = evernote_link_colors[link_type]
        if link_type is 'Levels':
            if not value: value = 1
            if not group: group = 'OL' if isinstance(value, int) else 'Modifiers'
            if not value in color_types[group]: group = 'Headers'
            if value in color_types[group]:
                colors = color_types[group][value]
        elif link_type is 'Links':
            if not value: value='Default'
            if value in color_types:
                colors = color_types[value]
    if not colors:
        colors = evernote_link_colors['Default']
    colorDefault = colors
    if not isinstance(colorDefault, str) and not isinstance(colorDefault, unicode):
        colorDefault = colorDefault['Default']
    if not colorDefault[-1] is ';': colorDefault += ';'
    style = 'color: ' + colorDefault
    if bold: style += 'font-weight:bold;'
    return style 

def generate_evernote_span(title=None, element_type=None, value=None, guid=None, bold=True, escape=True):
    assert title or guid 
    if not title: title = get_evernote_title_from_guid(guid)
    if escape: title = escape_text(title)
    style = generate_evernote_html_element_style_attribute(element_type, value, bold)
    html = u"<span style='%s'>%s</span>" % (style, title)
    return html


def get_dict_from_list(lst, keys_to_ignore=list()):
    dic = {}
    for key, value in lst:
        if not key in keys_to_ignore: dic[key] = value
    return dic


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

latestEDAMRateLimit = 0
    
def HandleEDAMRateLimitError(e, strError):
    global latestEDAMRateLimit
    if not e.errorCode is EDAMErrorCode.RATE_LIMIT_REACHED:
        return False
    latestEDAMRateLimit = e.rateLimitDuration
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

_regex_see_also = None 
def update_regex():
    global _regex_see_also    
    regex_str = file( os.path.join(ANKNOTES.FOLDER_ANCILLARY, 'regex-see_also.txt'), 'r').read()    
    regex_str = regex_str.replace('(?<', '(?P<')
    _regex_see_also = re.compile(regex_str, re.UNICODE | re.VERBOSE | re.DOTALL)

def regex_see_also():
    global _regex_see_also
    if not _regex_see_also: update_regex()
    return _regex_see_also
    
try:
    icoEvernoteWeb = QIcon(ANKNOTES.ICON_EVERNOTE_WEB)
    icoEvernoteArtcore = QIcon(ANKNOTES.ICON_EVERNOTE_ARTCORE)
    imgEvernoteWeb = QPixmap(ANKNOTES.IMAGE_EVERNOTE_WEB, "PNG")
    imgEvernoteWebMsgBox = imgEvernoteWeb.scaledToWidth(64)                
except: pass 

 
evernote_link_colors = {
 'Levels': {
             'OL':   {
                    1: {
						'Default': 'rgb(106, 0, 129);',
						'Hover': 'rgb(168, 0, 204);'
						},
                    2: {
						'Default': 'rgb(235, 0, 115);',
						'Hover': 'rgb(255, 94, 174);'
						},
                    3: {
						'Default': 'rgb(186, 0, 255);',
						'Hover': 'rgb(213, 100, 255);'
						},
                    4: {
						'Default': 'rgb(129, 182, 255);',
						'Hover': 'rgb(36, 130, 255);'
						},
                    5: {
						'Default': 'rgb(232, 153, 220);',
						'Hover': 'rgb(142, 32, 125);'
						},
                    6: {
						'Default': 'rgb(201, 213, 172);',
						'Hover': 'rgb(130, 153, 77);'
						},
                    7: {
						'Default': 'rgb(231, 179, 154);',
						'Hover': 'rgb(215, 129, 87);'
						},
                    8: {
						'Default': 'rgb(249, 136, 198);',
						'Hover': 'rgb(215, 11, 123);'
						}
              },
              'Headers': {
                    'Auto TOC': 'rgb(11, 59, 225);'
              },
              'Modifiers': {
                    'Orange': 'rgb(222, 87, 0);',
                    'Orange (Light)': 'rgb(250, 122, 0);',
                    'Dark Red/Pink': 'rgb(164, 15, 45);',			
                    'Pink Alternative LVL1:': 'rgb(188, 0, 88);'
               }
            },
  'Titles': {
     'Field Title Prompt': 'rgb(169, 0, 48);'
    },
  'Links': {
    'See Also': {
        'Default': 'rgb(45, 79, 201);',
        'Hover': 'rgb(108, 132, 217);'       
    },
    'TOC': {
		'Default': 'rgb(173, 0, 0);',
		'Hover': 'rgb(196, 71, 71);'       
    },
    'Outline': {
        'Default': 'rgb(105, 170, 53);',
        'Hover': 'rgb(135, 187, 93);'        
    },
    'AnkNotes': {
        'Default': 'rgb(30, 155, 67);',
        'Hover': 'rgb(107, 226, 143);'     
    }
  }
}
 
evernote_link_colors['Default'] = evernote_link_colors['Links']['Outline']
evernote_link_colors['Links']['Default'] = evernote_link_colors['Default']