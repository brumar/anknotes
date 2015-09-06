import os
import os.path
import re
import pprint
from HTMLParser import HTMLParser
import datetime
import shutil
import threading
import time
import errno

# try:
    # from pysqlite2 import dbapi2 as sqlite
# except ImportError:
    # from sqlite3 import dbapi2 as sqlite


from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.type.ttypes import NoteSortOrder
from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode
from evernote.api.client import EvernoteClient

import anki
import aqt
from anki.hooks import wrap
# from anki.db import DB
from aqt.preferences import Preferences
from aqt.utils import showInfo, getText, openLink, getOnlyText
from aqt.qt import QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, SIGNAL, QCheckBox, QComboBox, QSpacerItem, QSizePolicy, QWidget, QSpinBox
from aqt import mw


PATH = os.path.dirname(os.path.abspath(__file__))
ANKNOTES_TEMPLATE_FRONT = 'FrontTemplate.htm'
ANKNOTES_CSS = u'_AviAnkiCSS.css'
ANKNOTES_DB = u'anknotes.db'
MODEL_EVERNOTE_DEFAULT = 'evernote_note'
MODEL_EVERNOTE_REVERSIBLE = 'evernote_note_reversible'
MODEL_EVERNOTE_REVERSE_ONLY = 'evernote_note_reverse_only'
MODEL_EVERNOTE_CLOZE = 'evernote_note_cloze'
MODEL_TYPE_CLOZE = 1


TEMPLATE_EVERNOTE_DEFAULT = 'EvernoteReview' 
TEMPLATE_EVERNOTE_REVERSED = 'EvernoteReviewReversed' 
TEMPLATE_EVERNOTE_CLOZE = 'EvernoteReviewCloze' 
FIELD_TITLE = 'Title'
FIELD_CONTENT = 'Content'
FIELD_SEE_ALSO = 'See_Also'
FIELD_TOC = 'TOC'
FIELD_OUTLINE = 'Outline'
FIELD_EXTRA = 'Extra'
FIELD_EVERNOTE_GUID = 'Evernote GUID'
FIELD_UPDATE_SEQUENCE_NUM = 'updateSequenceNum'
FIELD_EVERNOTE_GUID_PREFIX = 'evernote_guid='

DECK_DEFAULT = "Evernote"
DECK_TOC = DECK_DEFAULT + "::See Also::TOC"
DECK_OUTLINE = DECK_DEFAULT + "::See Also::Outline"

EVERNOTE_TAG_TOC = '#TOC'
EVERNOTE_TAG_OUTLINE = '#Outline'
EVERNOTE_TAG_REVERSIBLE = '#Reversible'
EVERNOTE_TAG_REVERSE_ONLY = '#Reversible_Only'

TABLE_SEE_ALSO = "anknotes_see_also"
TABLE_EVERNOTE_NOTEBOOKS = "anknotes_evernote_notebooks"
TABLE_EVERNOTE_TAGS = "anknotes_evernote_tags"
TABLE_EVERNOTE_NOTES = u'anknotes_evernote_notes'

# Note that Evernote's API documentation says not to run API calls to findNotes with any less than a 15 minute interval
AUTO_IMPORT_TIMER_INTERVAL = 60 * 15
EVERNOTE_METADATA_QUERY_LIMIT = 10000
EVERNOTE_GET_NOTE_LIMIT = 10000

SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE = True
SETTING_EVERNOTE_TAGS_TO_IMPORT_DEFAULT_VALUE = "#Anki_Import"
SETTING_DEFAULT_ANKI_DECK_DEFAULT_VALUE = DECK_DEFAULT

ANKNOTES_EVERNOTE_CONSUMER_KEY = "holycrepe"
ANKNOTES_EVERNOTE_IS_SANDBOXED = False

SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT = 'anknotesDeleteEvernoteTagsToImport'
SETTING_UPDATE_EXISTING_NOTES = 'anknotesUpdateExistingNotes'
SETTING_EVERNOTE_PAGING = 'anknotesEvernotePaging'
SETTING_EVERNOTE_AUTH_TOKEN = 'anknotesEvernoteAuthToken_' + ANKNOTES_EVERNOTE_CONSUMER_KEY
if ANKNOTES_EVERNOTE_IS_SANDBOXED: SETTING_EVERNOTE_AUTH_TOKEN += "_SANDBOX"
SETTING_KEEP_EVERNOTE_TAGS = 'anknotesKeepEvernoteTags'
SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME = 'anknotesUseEvernoteNotebookNameForAnkiDeckName'
SETTING_EVERNOTE_TAGS_TO_IMPORT = 'anknotesEvernoteTagsToImport'
# Deprecated
# SETTING_DEFAULT_ANKI_TAG = 'anknotesDefaultAnkiTag'
SETTING_DEFAULT_ANKI_DECK = 'anknotesDefaultAnkiDeck'

# ankThread = False 
# ankDB = None

# class AnkDB(object):
    # def __init__(self, path, text=None, timeout=0):
        # encpath = path
        # if isinstance(encpath, unicode):
            # encpath = path.encode("utf-8")
        # self._db = sqlite.connect(encpath, timeout=timeout, check_same_thread=False)
        # if text:
            # self._db.text_factory = text
        # self._path = path
        # self.echo = os.environ.get("DBECHO")
        # self.mod = False

    # def execute(self, sql, *a, **ka):
        # s = sql.strip().lower()
        # # mark modified?
        # for stmt in "insert", "update", "delete":
            # if s.startswith(stmt):
                # self.mod = True
        # t = time.time()
        # if ka:
            # # execute("...where id = :id", id=5)
            # res = self._db.execute(sql, ka)
        # else:
            # # execute("...where id = ?", 5)
            # res = self._db.execute(sql, a)
        # if self.echo:
            # #print a, ka
            # print sql, "%0.3fms" % ((time.time() - t)*1000)
            # if self.echo == "2":
                # print a, ka
        # return res

    # def executemany(self, sql, l):
        # self.mod = True
        # t = time.time()
        # self._db.executemany(sql, l)
        # if self.echo:
            # print sql, "%0.3fms" % ((time.time() - t)*1000)
            # if self.echo == "2":
                # print l    

    # def commit(self):
        # t = time.time()
        # self._db.commit()
        # if self.echo:
            # print "commit %0.3fms" % ((time.time() - t)*1000)
                
    # def scalar(self, *a, **kw):
        # res = self.execute(*a, **kw).fetchone()
        # if res:
            # return res[0]
        # return None      

    # def first(self, *a, **kw):
        # c = self.execute(*a, **kw)
        # res = c.fetchone()
        # c.close()
        # return res        
        
    # def close(self):
        # self._db.close()        
        

def anknotesInitDB():
    global ankThread, ankDB
    ankThread = True 
    # path = os.path.join(PATH, ANKNOTES_DB)
    # path = os.path.abspath(path)
    # create = not os.path.exists(path)
    # if create:
        # base = os.path.basename(path)
        # for c in ("/", ":", "\\"):
            # assert c not in base
    # connect
    # ankDB = AnkDB(path)
    adb = anknotesDB()
    # if create:
    adb.execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL, PRIMARY KEY(guid) );""" % TABLE_EVERNOTE_NOTES)
    adb.execute( """CREATE TABLE IF NOT EXISTS `%s` ( `id` INTEGER, `note_guid` TEXT NOT NULL, `number` INTEGER NOT NULL DEFAULT 100, `uid` INTEGER NOT NULL DEFAULT -1, `shard` TEXT NOT NULL DEFAULT -1, `guid` TEXT NOT NULL, `html` TEXT NOT NULL, `title` TEXT NOT NULL, `from_toc` INTEGER DEFAULT 0, `is_toc` INTEGER DEFAULT 0, `is_outline` INTEGER DEFAULT 0, PRIMARY KEY(id) );""" % TABLE_SEE_ALSO) 
    adb.execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `parentGuid` TEXT, `updateSequenceNum` INTEGER NOT NULL, PRIMARY KEY(guid) );""" % TABLE_EVERNOTE_TAGS)
    adb.execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `serviceUpdated` INTEGER NOT NULL, `stack` TEXT, PRIMARY KEY(guid) );""" % TABLE_EVERNOTE_NOTEBOOKS)        
        
        # ver = _createankDB(ankDB)
    # else:
        # ver = _upgradeSchema(ankDB)
    # ankDB.execute("pragma temp_store = memory")
    # if sync:
        # ankDB.execute("pragma cache_size = 10000")
        # ankDB.execute("pragma journal_mode = wal")
    # else:
    # ankDB.execute("pragma synchronous = off")    

def anknotesDB():
    global ankThread, ankDB
    # return ankDB
    # if ankThread:
        # log("DB is in threaded mode")
        # return ankDB
    # else:
    return mw.col.db

evernote_cloze_count = 0


class UpdateExistingNotes:
    IgnoreExistingNotes, UpdateNotesInPlace, DeleteAndReAddNotes = range(3)
    

class RateLimitErrorHandling:
    IgnoreError, ToolTipError, AlertError = range(3)    
    
EDAM_RATE_LIMIT_ERROR_HANDLING = RateLimitErrorHandling.ToolTipError

def HandleSocketError(e, str):
    errorcode = v[0]
    if errorcode==errno.ECONNREFUSED:
        str = "Error: Connection was refused while %s\r\n" % str
        "Please retry your request a few minutes"
        log_prefix = 'ECONNREFUSED'
    elif errorcode==10060:
        str = "Error: Connection timed out while %s\r\n" % str
        "Please retry your request a few minutes"
        log_prefix = 'ETIMEDOUT'    
    else: 
        return False
    log_error( " SocketError.%s:  "  % log_prefix + str)    
    log( " SocketError.%s:  "  % log_prefix + str, 'api')         
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(str)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
        show_tooltip(str)
    return True

def HandleEDAMRateLimitError(e, str):
    if not e.errorCode is EDAMErrorCode.RATE_LIMIT_REACHED:
        return False
    m, s = divmod(e.rateLimitDuration, 60)
    str = "Error: Rate limit has been reached while %s\r\n" % str
    str += "Please retry your request in {} min".format("%d:%02d" %(m, s))
    log_str = " EDAMErrorCode.RATE_LIMIT_REACHED:  " + str.replace('\r\n', '\n')
    log_error(log_str)    
    log(log_str, 'api')    
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(str)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
        show_tooltip(str)
    return True
        
    
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

def find_evernote_links(content):
    return re.finditer(r'<a href="(?P<URL>evernote:///?view/(?P<uid>[\d]+?)/(?P<shard>s\d+)/(?P<guid>[\w\-]+?)/(?P=guid)/?)"(?: shape="rect")?>(?P<Title>.+?)</a>', content)    


  
def log(content, filename=''):
    if not filename: filename = 'anknotes.log'
    else: 
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = 'anknotes-%s.log' % filename
        
    try:
        content=content.encode('ascii', 'ignore')
    except Exception:
        pass
    content = content.replace('\r', '\r                          ').replace('\n', '\n                          ')
    st = str(datetime.datetime.now()).split('.')[0]
    with open( PATH + '\\' + filename, 'a+') as fileLog:
        print>>fileLog, ' [%s]: ' % st + content 
    
def log_sql(value):
    log(value, 'sql')

    
def log_error(value):
    log(value, '+error')    
    
def log_dump(obj, title="Object", filename=''):
    if not filename: filename = 'anknotes-dump.log'
    else: 
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = 'anknotes-dump-%s.log' % filename
    content = pprint.pformat(obj, indent=4, width=80)
    try:
        content=content.encode('ascii', 'ignore')
    except Exception:
        pass
    st = str(datetime.datetime.now()).split('.')[0]
    
    if title[0] is '-':
        prefix = " **** Dumping %s" % title[1:]
    else:        
        prefix = " **** Dumping %s" % title
        log(prefix)
    prefix += '\r\n' 
    content = prefix + content.replace(', ', ', \n ')
    content = content.replace('\r', '\r                          ').replace('\n', '\n                          ')
    with open( PATH + '\\' + filename, 'a+') as fileLog:
        print>>fileLog, '\n [%s]: ' % st + content     

        
        
class AnkiNotePrototype:
    fields = {}
    tags = []
    evernote_tags_to_import = []
    model_name = MODEL_EVERNOTE_DEFAULT    
    evernote_guid = ""
    def __init__(self, fields, tags, evernote_tags_to_import = list()):
        self.fields = fields
        self.tags = tags 
        if FIELD_EVERNOTE_GUID in fields:
            self.evernote_guid = fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '')
        self.evernote_tags_to_import = evernote_tags_to_import
        
        self.process_note()
    
    @staticmethod
    def evernote_cloze_regex(match):
        global evernote_cloze_count
        matchText = match.group(1)    
        if matchText[0] == "#":
            matchText = matchText[1:]
        else:
            evernote_cloze_count += 1    
        if evernote_cloze_count == 0:
            evernote_cloze_count = 1
        
        # print "Match: Group #%d: %s" % (evernote_cloze_count, matchText)
        return "{{c%d::%s}}" % (evernote_cloze_count, matchText)

    def process_note_see_also(self):
        if not FIELD_SEE_ALSO in self.fields or not FIELD_EVERNOTE_GUID in self.fields:
            return         
                         
        anknotesDB().execute("DELETE FROM %s WHERE note_guid = '%s' " % (TABLE_SEE_ALSO, self.evernote_guid))
        
        link_num = 0
        for match in find_evernote_links(self.fields[FIELD_SEE_ALSO]):
            link_num += 1
            title_text = strip_tags(match.group('Title'))
            is_toc = 0
            is_outline = 0
            if title_text is "O" or title_text is "Outline": is_outline = 1
            if title_text == "TOC": is_toc = 1
            anknotesDB().execute("INSERT INTO %s (note_guid, number, uid, shard, guid, html, title, from_toc, is_toc, is_outline) VALUES('%s', %d, %d, '%s', '%s', '%s', '%s', 0, %d, %d)" % (TABLE_SEE_ALSO, self.evernote_guid,link_num, int(match.group('uid')), match.group('shard'), match.group('guid'), match.group('Title'), title_text, is_toc, is_outline))
            # print "Link: %s: %s" % (match.group('guid'), title_text) 
            # for id, ivl in anknotesDB().execute("select id, ivl from cards limit 3"):
                
    
    
    
        # .NET Regex: <a href="(?<URL>evernote:///?view/(?<uid>[\d]+)/(?<shard>s\d+)/(?<guid>[\w\-]+)/\k<guid>/?)"(?: shape="rect")?>(?<Title>.+?)</a>
        # links_match 
    
        
    def process_note_content(self):
        if not FIELD_CONTENT in self.fields:
            return 
        content = self.fields[FIELD_CONTENT]
        ################################## Step 1: Modify Evernote Links
        # We need to modify Evernote's "Classic" Style Note Links due to an Anki bug with executing the evernote command with three forward slashes.
        # For whatever reason, Anki cannot handle evernote links with three forward slashes, but *can* handle links with two forward slashes.
        content = content.replace("evernote:///", "evernote://")
        
        # Modify Evernote's "New" Style Note links that point to the Evernote website. Normally these links open the note using Evernote's web client.
        # The web client then opens the local Evernote executable. Modifying the links as below will skip this step and open the note directly using the local Evernote executable
        content = re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([\w\d\-]+)', r'evernote://view/\2/\1/\3/\3/', content)
        
        ################################## Step 2: Modify Image Links        
        # Currently anknotes does not support rendering images embedded into an Evernote note. 
        # As a work around, this code will convert any link to an image on Dropbox, to an embedded <img> tag. 
        # This code modifies the Dropbox link so it links to a raw image file rather than an interstitial web page
        # Step 2.1: Modify HTML links to Dropbox images
        dropbox_image_url_regex = r'(?P<URL>https://www.dropbox.com/s/[\w\d]+/.+\.(jpg|png|jpeg|gif|bmp))(?P<QueryString>(?:\?dl=(?:0|1))?)'
        dropbox_image_src_subst = r'<a href="\g<URL>}\g<QueryString>}" shape="rect"><img src="\g<URL>?raw=1" alt="Dropbox Link %s Automatically Generated by Anknotes" /></a>'
        content = re.sub(r'<a href="%s".*?>(?P<Title>.+?)</a>' % dropbox_image_url_regex, dropbox_image_src_subst % "'\g<Title>'", content)
        
        # Step 2.2: Modify Plain-text links to Dropbox images
        try:
            dropbox_image_url_regex = dropbox_image_url_regex.replace('(?P<QueryString>(?:\?dl=(?:0|1))?)', '(?P<QueryString>\?dl=(?:0|1))')
            content = re.sub(dropbox_image_url_regex, dropbox_image_src_subst % "From Plain-Text Link", content)
        except:
            log_error("\nERROR processing note, Step 2.2.  Content: %s" % content)
        
        # Step 2.3: Modify HTML links with the inner text of exactly "(Image Link)"
        content = re.sub(r'<a href="(?P<URL>.+)"[^>]+>(?P<Title>\(Image Link.*\))</a>', 
        r'''<img src="\g<URL>" alt="'\g<Title>' Automatically Generated by Anknotes" /> <BR><a href="\g<URL>">\g<Title></a>''', content)
        
        ################################## Step 3: Change white text to transparent 
        # I currently use white text in Evernote to display information that I want to be initially hidden, but visible when desired by selecting the white text.
        # We will change the white text to a special "occluded" CSS class so it can be visible on the back of cards, and also so we can adjust the color for the front of cards when using night mode
        content = content.replace('<span style="color: rgb(255, 255, 255);">', '<span class="occluded">')
        
        ################################## Step 4: Automatically Occlude Text in <<Double Angle Brackets>>
        content = re.sub(r'&lt;&lt;(.+?)&gt;&gt;', r'&lt;&lt;<span class="occluded">$1</span>&gt;&gt;', content)	

        ################################## Step 5: Create Cloze fields from shorthand. Syntax is {Text}. Optionally {#Text} will prevent the Cloze # from incrementing.
        content = re.sub(r'{(.+?)}', self.evernote_cloze_regex, content)
        
        ################################## Step 6: Process "See Also: " Links
        # .NET regex: (?<PrefixStrip><div><b><span style="color: rgb\(\d{1,3}, \d{1,3}, \d{1,3}\);"><br/></span></b></div>)?(?<SeeAlso>(?<SeeAlsoPrefix><div>)(?<SeeAlsoHeader><span style="color: rgb\(45, 79, 201\);"><b>See Also:(?:&nbsp;)?</b></span>|<b><span style="color: rgb\(45, 79, 201\);">See Also:</span></b>|<b style=[^>]+?><span style="color: rgb\(45, 79, 201\);">See Also:</span></b>)(?<SeeAlsoContents>.+))(?<Suffix></en-note>)
        see_also_match = re.search(r'(?P<PrefixStrip><div><b><span style="color: rgb\(\d{1,3}, \d{1,3}, \d{1,3}\);"><br/></span></b></div>)?(?P<SeeAlso>(?P<SeeAlsoPrefix><div>)(?P<SeeAlsoHeader><span style="color: rgb\(45, 79, 201\);"><b>See Also:(?:&nbsp;)?</b></span>|<b><span style="color: rgb\(45, 79, 201\);">See Also:</span></b>|<b style=[^>]+?><span style="color: rgb\(45, 79, 201\);">See Also:</span></b>)(?P<SeeAlsoContents>.+))(?P<Suffix></en-note>)', content)
        # see_also_match = re.search(r'(?P<PrefixStrip><div><b><span style="color: rgb\(\d{1,3}, \d{1,3}, \d{1,3}\);"><br/></span></b></div>)?(?P<SeeAlso>(?:<div>)(?P<SeeAlsoHeader><span style="color: rgb\(45, 79, 201\);">(?:See Also|<b>See Also:</b>).*?</span>).+?)(?P<Suffix></en-note>)', content) 
        
        if see_also_match:
            content = content.replace(see_also_match.group(0), see_also_match.group('Suffix'))
            self.fields[FIELD_SEE_ALSO] = see_also_match.group('SeeAlso').replace('<b style="color: rgb(0, 0, 0); font-family: Tahoma; font-style: normal; font-variant: normal; letter-spacing: normal; orphans: 2; text-align: -webkit-auto; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-size-adjust: auto; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); font-size: medium;">', '<b>')                 
            self.process_note_see_also()
        
        ################################## Note Processing complete. 
        self.fields[FIELD_CONTENT] = content
    
    def process_note(self):
        self.model_name = MODEL_EVERNOTE_DEFAULT        
        # Process Note Content 
        self.process_note_content()
                
        # Dynamically determine Anki Card Type 
        if FIELD_CONTENT in self.fields and "{{c1::" in self.fields[FIELD_CONTENT]: 
            self.model_name = MODEL_EVERNOTE_CLOZE
        elif EVERNOTE_TAG_REVERSIBLE in self.tags: 
            self.model_name = MODEL_EVERNOTE_REVERSIBLE
            
            if mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True):
                self.tags.remove(EVERNOTE_TAG_REVERSIBLE)
        elif EVERNOTE_TAG_REVERSE_ONLY in self.tags: 
            model_name = MODEL_EVERNOTE_REVERSE_ONLY
            if mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True):
                self.tags.remove(EVERNOTE_TAG_REVERSE_ONLY)

class Anki:
    def update_evernote_cards(self, evernote_cards):
        return self.add_evernote_cards(evernote_cards, None, True)

    def add_evernote_cards(self, evernote_cards, deck, update=False):
        count = 0
        deck_original = deck
        for card in evernote_cards:
            anki_field_info = {
                               FIELD_TITLE: card.front.decode('utf-8'),
                               FIELD_CONTENT: card.back.decode('utf-8'),
                               FIELD_EVERNOTE_GUID: FIELD_EVERNOTE_GUID_PREFIX + card.guid,
                               FIELD_UPDATE_SEQUENCE_NUM: str(card.updateSequenceNum)
                               }
            if not update:
                anki_field_info.update ({
                               FIELD_SEE_ALSO: u'',
                               FIELD_TOC: u'',
                               FIELD_OUTLINE: u'',
                               FIELD_EXTRA: u'',
                               })                
            # Deprecated 
            # card.tags.append(tag)
            if update:
                debug_fields = anki_field_info.copy()
                del debug_fields[FIELD_CONTENT]
                log_dump(debug_fields, "-      > UPDATE_EVERNOTE_CARDS → ADD_EVERNOTE_CARDS: evernote_cards: card: FIELDS ")
            anki_note_prototype = AnkiNotePrototype(anki_field_info, card.tags, self.evernoteTags)
            if not update:
                if EVERNOTE_TAG_TOC in card.tags:
                    deck = DECK_TOC     
                elif EVERNOTE_TAG_OUTLINE in card.tags:
                    deck = DECK_OUTLINE
                elif mw.col.conf.get(SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME, True):                
                    if not card.notebookGuid in self.notebook_data:
                        log_error("Unexpected error: Notebook GUID '%s' could not be found in notebook data: %s" % (card.notebookGuid, str(self.notebook_data)))
                        notebook = anknotesDB().execute("SELECT name, stack FROM %s WHERE guid = '%s'" % (TABLE_EVERNOTE_NOTEBOOKS, card.notebookGuid)).fetchone()
                        if not notebook: 
                            log_error("   ADD_EVERNOTE_CARDS FATAL ERROR: UNABLE TO FIND NOTEBOOK '%s'. " % notebookGuid)                        
                            return count
                        log("Getting notebook info: %s" % str(notebook))
                        notebook_name, notebook_stack = notebook
                        self.notebook_data[card.notebookGuid] = {"stack": notebook_stack, "name": notebook_name}
                            
                    notebook = self.notebook_data[card.notebookGuid]
                    deck = deck_original
                    if notebook['stack']:
                        deck += u'::' + notebook['stack']
                    deck += "::" + notebook['name']
                    deck = deck.replace(": ", "::")                
            
            if update:
                debug_fields = anki_note_prototype.fields.copy()
                del debug_fields[FIELD_CONTENT]
                log_dump(debug_fields, "-      > UPDATE_EVERNOTE_CARDS → ADD_EVERNOTE_CARDS: anki_note_prototype: FIELDS ")            
            
            if update:
                self.update_note(anki_note_prototype)
            else:
                self.add_note(deck, anki_note_prototype)
            count += 1
        return count

    def delete_anki_cards(self, guid_ids):
        col = self.collection()
        card_ids = []
        for guid in guid_ids:
            card_ids += mw.col.findCards(guid)
        col.remCards(card_ids)
        return len(card_ids)

    def update_note(self, anki_note_prototype):
        col = self.collection()
        evernote_guid = anki_note_prototype.fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '')
        note_id = col.findNotes(evernote_guid)[0]
        note = anki.notes.Note(col, None, note_id)
        note.tags = anki_note_prototype.tags
        
        fields_to_update = [FIELD_TITLE, FIELD_CONTENT, FIELD_SEE_ALSO, FIELD_UPDATE_SEQUENCE_NUM]
        fld_content_ord = -1
        log_dump({'note.fields': note.fields, 'note._model.flds': note._model['flds']}, "-      > UPDATE_NOTE → anki.notes.Note: _model: flds")   
        flag_changed = False
        for fld in note._model['flds']:
            for field_to_update in fields_to_update:            
                if field_to_update is FIELD_CONTENT:
                    fld_content_ord = fld.get('ord')
                if field_to_update in fld.get('name') and field_to_update in anki_note_prototype.fields:
                    try:
                        # log(" >  Updating field %s " % field_to_update)
                        if not flag_changed:
                            flag_changed = (not note.fields[fld.get('ord')] is anki_note_prototype.fields[field_to_update])                                            
                        note.fields[fld.get('ord')] = anki_note_prototype.fields[field_to_update] 
                    except:
                        log_error("ERROR: UPDATE_NOTE: Unable to set note.fields for field '%s'. Ord: %s. Note fields count: %d" % (field_to_update, str(fld.get('ord')), len(note.fields)) )
                        raise
                   
            # TODO: Add support for extracting an 'Extra' field from the Evernote Note contents
            # we dont have to update the evernote guid because if it changes we wont find this note anyway
        
        if not fld_content_ord is -1:
            debug_fields = list(note.fields)
            del debug_fields[fld_content_ord]
            log_dump(debug_fields, "-      > UPDATE_NOTE → anki.notes.Note: FIELDS ")          
        
        if flag_changed:
            note.flush()            
        else:
            log("Not updating Note '%s': no fields have been changed" % evernote_guid)
        return note.id

    def add_note(self, deck_name, anki_note_prototype):
        note = self.create_note(deck_name, anki_note_prototype)
        if note is not None:
            collection = self.collection()
            collection.addNote(note)
            collection.autosave()
            self.start_editing()
            return note.id

    def create_note(self, deck_name, anki_note_prototype):
        id_deck = self.decks().id(deck_name)
        model = self.models().byName(anki_note_prototype.model_name)
        col = self.collection()
        note = anki.notes.Note(col, model)
        note.model()['did'] = id_deck
        note.tags = anki_note_prototype.tags
        for name, value in anki_note_prototype.fields.items():
            note[name] = value
        return note

    # def create_evernote_tables(self):
        # anknotesDB().execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL, PRIMARY KEY(guid) );""" % TABLE_EVERNOTE_NOTES)
        # anknotesDB().execute( """CREATE TABLE IF NOT EXISTS `%s` ( `id` INTEGER, `note_guid` TEXT NOT NULL, `number` INTEGER NOT NULL DEFAULT 100, `uid` INTEGER NOT NULL DEFAULT -1, `shard` TEXT NOT NULL DEFAULT -1, `guid` TEXT NOT NULL, `html` TEXT NOT NULL, `title` TEXT NOT NULL, `from_toc` INTEGER DEFAULT 0, `is_toc` INTEGER DEFAULT 0, `is_outline` INTEGER DEFAULT 0, PRIMARY KEY(id) );""" % TABLE_SEE_ALSO) 
        # anknotesDB().execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `parentGuid` TEXT, `updateSequenceNum` INTEGER NOT NULL, PRIMARY KEY(guid) );""" % TABLE_EVERNOTE_TAGS)
        # anknotesDB().execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `serviceUpdated` INTEGER NOT NULL, `stack` TEXT, PRIMARY KEY(guid) );""" % TABLE_EVERNOTE_NOTEBOOKS)
        

    def add_evernote_model(self, mm, modelName, templates, cloze=False):
        model = mm.byName(modelName)
        if not model:            
            model = mm.new(modelName)
            # Add Field for Evernote GUID:
            #  Note that this field is first because Anki requires the first field to be unique
            evernote_guid_field = mm.newField(FIELD_EVERNOTE_GUID)
            evernote_guid_field['sticky'] = True
            evernote_guid_field['font'] = 'Consolas'
            evernote_guid_field['size'] = 10
            mm.addField(model, evernote_guid_field)  

            # Add Standard Fields:
            mm.addField(model, mm.newField(FIELD_TITLE))
            
            evernote_content_field = mm.newField(FIELD_CONTENT)
            evernote_content_field['size'] = 14
            mm.addField(model, evernote_content_field) 
            
            evernote_see_also_field = mm.newField(FIELD_SEE_ALSO)
            evernote_see_also_field['size'] = 14
            mm.addField(model, evernote_see_also_field)   
            
            evernote_extra_field = mm.newField(FIELD_EXTRA)
            evernote_extra_field['size'] = 12
            mm.addField(model, evernote_extra_field)  
            
            evernote_toc_field = mm.newField(FIELD_TOC)
            evernote_toc_field['size'] = 10
            mm.addField(model, evernote_toc_field)
            
            evernote_outline_field = mm.newField(FIELD_OUTLINE)
            evernote_outline_field['size'] = 10
            mm.addField(model, evernote_outline_field)
            
            # Add USN to keep track of changes vs Evernote's servers 
            evernote_usn_field = mm.newField(FIELD_UPDATE_SEQUENCE_NUM)
            evernote_guid_field['font'] = 'Consolas'
            evernote_usn_field['size'] = 10
            mm.addField(model, evernote_usn_field)
            
            # Add Templates
            # for template in templates:
                # mm.addTemplate(model, template)
                
            if modelName is MODEL_EVERNOTE_DEFAULT or modelName is MODEL_EVERNOTE_REVERSIBLE:
                # Create Default Template
                default_template = mm.newTemplate(TEMPLATE_EVERNOTE_DEFAULT)
                default_template['qfmt'] =  templates['Front']
                default_template['afmt'] =  templates['Back']
                mm.addTemplate(model, default_template)
            if modelName is MODEL_EVERNOTE_REVERSE_ONLY or modelName is MODEL_EVERNOTE_REVERSIBLE:
                # Create Reversed Template
                reversed_template = mm.newTemplate(TEMPLATE_EVERNOTE_REVERSED)
                reversed_template['qfmt'] =  templates['Front']
                reversed_template['afmt'] =  templates['Back']
                mm.addTemplate(model, reversed_template)
            if modelName is MODEL_EVERNOTE_CLOZE:
                # Create Cloze Template        
                cloze_template = mm.newTemplate(TEMPLATE_EVERNOTE_CLOZE)
                cloze_template['qfmt'] =  templates['Front']
                cloze_template['afmt'] =  templates['Back']                
                mm.addTemplate(model, cloze_template)
                
            # Update Sort field to Title
            model['sortf'] = 1
           
            # Update Model CSS
            model['css'] = '@import url("_AviAnkiCSS.css");'
            if cloze:
                model['type'] = MODEL_TYPE_CLOZE
            mm.add(model)        
        self.evernoteModels[modelName] = model['id']
        
    def add_evernote_models(self):  # adapted from the IREAD plug-in from Frank        
    
        col = self.collection()
        mm = col.models
                
        # evernote_model = mm.byName(MODEL_EVERNOTE_DEFAULT)
        
        field_names = {"Title": FIELD_TITLE, "Content": FIELD_CONTENT, "Extra": FIELD_EXTRA, "See Also": FIELD_SEE_ALSO, "TOC": FIELD_TOC, "Outline": FIELD_OUTLINE}
                
        # Generate Front and Back Templates from HTML Template in anknotes' addon directory
        templates = {"Front": file( os.path.join(PATH, ANKNOTES_TEMPLATE_FRONT) , 'r').read() % field_names } 
        templates["Back"] = templates["Front"].replace("<div id='Side-Front'>", "<div id='Side-Back'>")
            

                
        self.evernoteModels = {}
        self.add_evernote_model(mm, MODEL_EVERNOTE_DEFAULT,  templates)
        self.add_evernote_model(mm, MODEL_EVERNOTE_REVERSE_ONLY,  templates)
        self.add_evernote_model(mm, MODEL_EVERNOTE_REVERSIBLE,  templates)
        self.add_evernote_model(mm, MODEL_EVERNOTE_CLOZE,  templates, True)

    # Should deprecate this 
    def get_guids_from_anki_card_ids(self, ids):
        guids = []
        for a_id in ids:
            card = self.collection().getCard(a_id)
            items = card.note().items()
            for key, value in items:
                if key is FIELD_EVERNOTE_GUID:
                    guids.append(value.replace(FIELD_EVERNOTE_GUID_PREFIX, ''))
        return guids
        
    def get_guids_from_anki_note_ids(self, ids):
        guids = []
        self.usns = {}
        for a_id in ids:
            note = self.collection().getNote(a_id)
            try:
                items = note.items()   
            except:
                log_error("Unable to get note items for Note ID: %d" % a_id)
                raise
            dict = {}
            for key, value in items:                
                if not key is FIELD_CONTENT:
                    dict[key] = value
            if FIELD_EVERNOTE_GUID in dict:                
                guid = dict[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '')    
                guids.append(guid)
                if FIELD_UPDATE_SEQUENCE_NUM in dict:
                    self.usns[guid] = dict[FIELD_UPDATE_SEQUENCE_NUM]    
                else:
                    log("   ! get_guids_from_anki_note_ids: Note '%s' is missing USN!" % guid)
        return guids        
        
    # Should deprecate this
    def get_evernote_notes_by_anki_card_ids(self, ids):
        guids = {}
        for a_id in ids:
            card = self.collection().getCard(a_id)
            items = card.note().items()
            fields = {}
            for key, value in items:
                fields[key] = value
            if FIELD_EVERNOTE_GUID in fields:
                guids[fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '')] = fields
        return guids        

    def get_evernote_notes_by_anki_note_ids(self, ids):
        guids = {}
        for a_id in ids:
            note = self.collection().getNote(a_id)
            items = note.items()
            fields = {}
            for key, value in items:
                fields[key] = value
            if FIELD_EVERNOTE_GUID in fields:
                guids[fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '')] = fields
        return guids            
        
    def can_add_note(self, deck_name, model_name, fields):
        return bool(self.create_note(deck_name, model_name, fields))

    def search_evernote_models_query(self):        
        query = ""
        delimiter = ""
        for mName, mid in self.evernoteModels.items():
            query += delimiter + "mid:" + str(mid)
            delimiter = " OR "
        return query 
            
    def get_anknotes_card_ids(self):
        ids = self.collection().findCards(self.search_evernote_models_query())
        return ids        
            
    def get_anknotes_note_ids(self):
        ids = self.collection().findNotes(self.search_evernote_models_query())
        return ids        
        
    def get_anki_note_from_guid(self, guid):
        col = self.collection()
        ids = col.findNotes(FIELD_EVERNOTE_GUID_PREFIX + guid)        
        # TODO: Ugly work around for a big. Fix this later
        if not ids: return None
        if not ids[0]: return None 
        note = anki.notes.Note(col, None, ids[0])
        return note
         
    def get_cards_id_from_tag(self, tag):        
        query = "tag:" + tag
        ids = self.collection().findCards(query)
        return ids
        
    def get_anknotes_note_ids_by_tag(self, tag):        
        query = "tag:" + tag + " AND (%s)" % self.search_evernote_models_query()
        ids = self.collection().findNotes(query)
        return ids

    def process_see_also_content(self, anki_note_ids):
        for a_id in anki_note_ids:
            note = self.collection().getNote(a_id)
            try:
                items = note.items()   
            except:
                log_error("Unable to get note items for Note ID: %d" % a_id)
                raise
            fields = {}
            for key, value in items:             
                fields[key] = value
            if not fields[FIELD_SEE_ALSO]:
                
                anki_note_prototype = AnkiNotePrototype(fields, note.tags, [])                
                if anki_note_prototype.fields[FIELD_SEE_ALSO]:
                    log("Checked see also for Note '%s': %s" % (fields[FIELD_EVERNOTE_GUID], fields[FIELD_TITLE]))
                    log(u" → %s " % fields[FIELD_SEE_ALSO])
                    self.update_note(anki_note_prototype)
        
    def process_toc_and_outlines(self):
        toc_anki_ids = self.get_cards_id_from_tag(EVERNOTE_TAG_TOC)
        toc_evernote_guids = self.get_evernote_notes_by_anki_card_ids(toc_anki_ids)
        query_update_toc_links = "UPDATE %s SET is_toc = 1 WHERE " % TABLE_SEE_ALSO
        delimiter = ""
        link_exists = 0
        for toc_guid, fields in toc_evernote_guids.items():
            for match in find_evernote_links(fields[FIELD_CONTENT]): 
                link_guid = match.group('guid')
                uid = int(match.group('uid'))
                shard = match.group('shard')
                if link_guid is toc_guid: continue 
                link_title = strip_tags(match.group('Title'))
                link_number = 1 + anknotesDB().scalar("select COUNT(*) from %s WHERE note_guid = '%s' " % (TABLE_SEE_ALSO, link_guid))
                toc_link_title = fields[FIELD_TITLE]
                toc_link_html = '<span style="color: rgb(173, 0, 0);"><b>%s</b></span>' % toc_link_title
                query = """INSERT INTO `%s`(`note_guid`, `number`, `uid`, `shard`, `guid`, `html`, `title`, `from_toc`, `is_toc`)
SELECT '%s', %d, %d, '%s', '%s', '%s', '%s', 1, 1 FROM `%s` 
WHERE NOT EXISTS (SELECT * FROM `%s` 
      WHERE `note_guid`='%s' AND `guid`='%s') 
LIMIT 1 """ % (TABLE_SEE_ALSO, link_guid, link_number, uid, shard,  toc_guid, toc_link_html.replace(u'\'', u'\'\''), toc_link_title.replace(u'\'', u'\'\''), TABLE_SEE_ALSO, TABLE_SEE_ALSO, link_guid, toc_guid)
                log_sql('UPDATE_ANKI_DB: Add See Also Link: SQL Query: ' + query)
                anknotesDB().execute(query)

                # print "Link: %s: %s" % (match.group('guid'), title_text) 
                # for id, ivl in anknotesDB().execute("select id, ivl from cards limit 3"):
            query_update_toc_links += delimiter + "guid = '%s'" % toc_guid
            delimiter = " OR "        
        anknotesDB().execute(query_update_toc_links)
        
        linked_notes_fields = {}
        # We have populated all toc links 
        for note_guid in anknotesDB().list("select DISTINCT note_guid from %s WHERE is_toc = 1 ORDER BY note_guid ASC" % TABLE_SEE_ALSO):
            note = self.get_anki_note_from_guid(note_guid)
            if not note: continue
            if EVERNOTE_TAG_TOC in note.tags: continue 
            
            for fld in note._model['flds']:
                if FIELD_TITLE in fld.get('name'):
                    note_title = note.fields[fld.get('ord')] 
                    continue 
            
            note_toc = ""
            note_outline = ""  
            toc_header = ""
            outline_header = ""
            toc_count = 0
            outline_count = 0
            
            #log(" > Starting Note: %s: %s" % (note_guid, note_title))

            
            
            for link_guid, is_toc, is_outline in anknotesDB().execute("select guid, is_toc, is_outline from %s WHERE note_guid = '%s' AND (is_toc = 1 OR is_outline = 1) ORDER BY number ASC" % (TABLE_SEE_ALSO, note_guid)):    
                if link_guid in linked_notes_fields:
                    linked_note_contents = linked_notes_fields[link_guid][FIELD_CONTENT]
                    linked_note_title = linked_notes_fields[link_guid][FIELD_TITLE]
                else:                    
                    linked_note = self.get_anki_note_from_guid(link_guid)
                    if not linked_note: continue 
                    linked_note_contents = ""
                    for fld in linked_note._model['flds']:
                        if FIELD_CONTENT in fld.get('name'):
                            linked_note_contents = linked_note.fields[fld.get('ord')]                        
                        elif FIELD_TITLE in fld.get('name'):
                            linked_note_title = linked_note.fields[fld.get('ord')]                   
                    if linked_note_contents:
                        linked_notes_fields[link_guid] = {FIELD_TITLE: linked_note_title, FIELD_CONTENT: linked_note_contents}

                #log("  > Processing Link: %s: %s"  % (link_guid, linked_note_title)) 
                if linked_note_contents: 
                    if is_toc:      
                        toc_count += 1
                        if toc_count is 1:
                            toc_header = "<span class='header'>TABLE OF CONTENTS</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:                            
                            toc_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (toc_count, linked_note_title)
                            note_toc += "<BR><HR>"
                           
                        note_toc += linked_note_contents
                        #log("   > Appending TOC #%d contents" % toc_count) 
                    else:
                        outline_count += 1
                        if outline_count is 1:
                            outline_header = "<span class='header'>OUTLINE</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:                            
                            outline_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (outline_count, linked_note_title)
                            note_outline += "<BR><HR>"
                           
                        note_outline += linked_note_contents
                        #log("   > Appending Outline #%d contents" % outline_count) 
                        
            if outline_count + toc_count > 0:
                if outline_count > 1:
                    note_outline = "<span class='Outline'>%s</span><BR><BR>" % outline_header + note_outline                
                if toc_count > 1:
                    note_toc = "<span class='TOC'>%s</span><BR><BR>" % toc_header + note_toc            
                for fld in note._model['flds']:
                    if FIELD_TOC in fld.get('name'):
                        note.fields[fld.get('ord')] = note_toc
                    elif FIELD_OUTLINE in fld.get('name'):
                        note.fields[fld.get('ord')] = note_outline
                #log(" > Flushing Note \r\n")
                note.flush()
            
        

    def start_editing(self):
        self.window().requireReset()

    def stop_editing(self):
        if self.collection():
            self.window().maybeReset()

    def window(self):
        return aqt.mw

    def collection(self):
        return self.window().col

    def models(self):
        return self.collection().models

    def decks(self):
        return self.collection().decks


class EvernoteCard:
    front = ""
    back = ""
    guid = ""
    updateSequenceNum = -1
    tags = []
    notebookGuid = []
    

    def __init__(self, q, a, g, tags, notebookGuid, updateSequenceNum):
        self.front = q
        self.back = a
        self.guid = g
        self.tags = tags
        self.notebookGuid = notebookGuid
        self.updateSequenceNum = updateSequenceNum


class Evernote:
    def __init__(self):
        auth_token = mw.col.conf.get(SETTING_EVERNOTE_AUTH_TOKEN, False)
        self.tag_data = {}
        self.notebook_data = {}
        self.getNoteCount = 0
        
        if not auth_token:
            # First run of the Plugin we did not save the access key yet
            secrets = {'holycrepe': '36f46ea5dec83d4a', 'scriptkiddi-2682': '965f1873e4df583c'}
            client = EvernoteClient(
                consumer_key=ANKNOTES_EVERNOTE_CONSUMER_KEY,
                consumer_secret=secrets[ANKNOTES_EVERNOTE_CONSUMER_KEY],
                # sandbox = True
                sandbox=ANKNOTES_EVERNOTE_IS_SANDBOXED
            )
            request_token = client.get_request_token('https://fap-studios.de/anknotes/index.html')
            url = client.get_authorize_url(request_token)
            showInfo("We will open a Evernote Tab in your browser so you can allow access to your account")
            openLink(url)
            oauth_verifier = getText(prompt="Please copy the code that showed up, after allowing access, in here")[0]
            auth_token = client.get_access_token(
                request_token.get('oauth_token'),
                request_token.get('oauth_token_secret'),
                oauth_verifier)
            mw.col.conf[SETTING_EVERNOTE_AUTH_TOKEN] = auth_token
            #log("Saved Auth Token: %s" % auth_token)
        self.token = auth_token
        self.client = EvernoteClient(token=auth_token, sandbox=ANKNOTES_EVERNOTE_IS_SANDBOXED)
        self.initialize_note_store()

    def initialize_note_store(self):
        api_action_str = u'trying to initialize the Evernote Client.'
        log(" EVERNOTE_API_CALL: get_note_store", 'api')
        try:            
            self.noteStore = self.client.get_note_store()                                  
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): return False
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): return False
            raise                         
        return True

    # Deprecated 
    # def find_tag_guid(self, tag):
        # log(" EVERNOTE_API_CALL: listTags")
        # list_tags = self.noteStore.listTags()        
        # for evernote_tag in list_tags:
            # if str(evernote_tag.name).strip() == str(tag).strip():
                # return evernote_tag.guid

    def create_evernote_cards(self, guid_set):
        if mw.col.conf.get(SETTING_KEEP_EVERNOTE_TAGS, SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE):
            if not self.check_tags_up_to_date(guid_set): 
                self.process_tag_guids(guid_set)
            if not self.check_notebooks_up_to_date(guid_set): 
                self.process_notebook_guids(guid_set)                
        cards = []
        # if mw.col.conf.get(SETTING_KEEP_EVERNOTE_TAGS, SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE):
            # tags = self.noteStore.getNoteTagNames(self.token, note_guid)        
        for guid in guid_set:
            note_info = self.get_note_information(guid)
            if note_info is None:
                return cards
            title, content, tags, notebookGuid, updateSequenceNum = note_info
            log_dump([title, guid, tags, notebookGuid, updateSequenceNum], '-  > UPDATE_IN_ANKI → CREATE_EVERNOTE_CARDS → EVERNOTE_CARD(title, guid, tags, notebookGuid, updateSequenceNum)')
            cards.append(EvernoteCard(title, content, guid, tags, notebookGuid, updateSequenceNum))
        return cards


        
      
    
    def check_notebooks_up_to_date(self, guid_set):        
        notebook_guids = []        
        for guid in guid_set:
            note_metadata = self.metadata[guid]
            notebookGuid = note_metadata.notebookGuid 
            if not notebookGuid:
                log_error("   > Notebook check: Unable to find notebook guid for '%s'. Returned '%s'. Metadata: %s" % (guid, str(notebookGuid), str(note_metadata)))
            elif not notebookGuid in notebook_guids and not notebookGuid in self.notebook_data:                
                notebook  = anknotesDB().execute("SELECT name, stack FROM %s WHERE guid = '%s'" % (TABLE_EVERNOTE_NOTEBOOKS, notebookGuid)).fetchone()
                if not notebook: 
                    log("   > Notebook check: Missing notebook guid '%s'. Will update with an API call." % notebookGuid)
                    return False
                notebook_name, notebook_stack = notebook
                self.notebook_data[notebookGuid] = {"stack": notebook_stack, "name": notebook_name}
                notebook_guids.append(notebookGuid)
        
        #log("   > All notebooks are in the database")       
        return True        
        
    def process_notebook_guids(self, guid_set):
        api_action_str = u'trying to update Evernote notebooks.'
        log(" EVERNOTE_API_CALL: listNotebooks", 'api')
        try:            
            notebooks = self.noteStore.listNotebooks(self.token)                               
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): return None
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): return None
            raise       
        data = []
        for notebook in notebooks:
            self.notebook_data[notebook.guid] = {"stack": notebook.stack, "name": notebook.name}
            data.append([notebook.guid, notebook.name, notebook.updateSequenceNum, notebook.serviceUpdated, notebook.stack])
        #log("Updating %d notebooks" % len(notebooks))
        anknotesDB().executemany("INSERT OR REPLACE INTO `%s`(`guid`,`name`,`updateSequenceNum`,`serviceUpdated`, `stack`) VALUES (?, ?, ?, ?, ?)" % TABLE_EVERNOTE_NOTEBOOKS, data)        
    
    def check_tags_up_to_date(self, guid_set):        
        tag_guids = []
        for guid in guid_set:
            note_metadata = self.metadata[guid]
            for tag_guid in note_metadata.tagGuids:
                if not tag_guid in tag_guids and not tag_guid in self.tag_data: 
                    tag_name = anknotesDB().scalar("SELECT name FROM %s WHERE guid = '%s'" % (TABLE_EVERNOTE_TAGS, tag_guid))
                    if not tag_name: 
                        return False
                    self.tag_data[tag_guid] = tag_name 
                    tag_guids.append(tag_guid)
        
        #log("   > All tags are in the database")       
        return True
       
    def process_tag_guids(self, guid_set):
        api_action_str = u'trying to update Evernote tags.'
        log(" EVERNOTE_API_CALL: listTags", 'api')
        try:            
            tags = self.noteStore.listTags(self.token)                                
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): return None
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): return None
            raise       
        data = []
        for tag in tags:
            self.tag_data[tag.guid] = tag.name
            data.append([tag.guid, tag.name, tag.parentGuid, tag.updateSequenceNum])
        #log("Updating %d tags" % len(tags))
        anknotesDB().executemany("INSERT OR REPLACE INTO `%s`(`guid`,`name`,`parentGuid`,`updateSequenceNum`) VALUES (?, ?, ?, ?)" % TABLE_EVERNOTE_TAGS, data)        
    
    def get_note_information(self, note_guid):
        tags = []
        
        if self.getNoteCount > EVERNOTE_GET_NOTE_LIMIT: 
            log("Aborting Evernote.get_note_information: EVERNOTE_GET_NOTE_LIMIT of %d has been reached" % EVERNOTE_GET_NOTE_LIMIT)
            return None
        
        api_action_str = u'trying to retrieve a note. We will save the notes downloaded thus far.'
        log(" EVERNOTE_API_CALL: getNote: GUID: '%s'" % note_guid, 'api')        
        try:                        
            whole_note = self.noteStore.getNote(self.token, note_guid, True, False, False, False)                                          
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): return None
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): return None
            raise     
        self.getNoteCount += 1
        tagNames = []
        tagGuids = list(whole_note.tagGuids)
        removeTagsToImport = mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True)
        for tag_guid in whole_note.tagGuids:
            tagName = self.tag_data[tag_guid]
            if removeTagsToImport and tagName in self.evernoteTags:
                tagGuids.remove(tag_guid)
            else:
                tagNames.append(tagName)                
        tagNames = sorted(tagNames, key=lambda s: s.lower())
        #log("TagNames: %s" % str(tagNames))
        
        
        
        sql_query = u'INSERT OR REPLACE INTO `%s`(`guid`,`title`,`content`,`updated`,`created`,`updateSequenceNum`,`notebookGuid`,`tagGuids`,`tagNames`) VALUES (\'%s\',\'%s\',\'%s\',%d,%d,%d,\'%s\',\'%s\',\'%s\');' % (TABLE_EVERNOTE_NOTES, whole_note.guid.decode('utf-8'), whole_note.title.decode('utf-8').replace(u'\'', u'\'\''), whole_note.content.decode('utf-8'), whole_note.updated, whole_note.created, whole_note.updateSequenceNum, whole_note.notebookGuid.decode('utf-8'), u',' + u','.join(tagGuids).decode('utf-8') + u',', u',' + u','.join(tagNames).decode('utf-8') + u',')
         
        log_sql('UPDATE_ANKI_DB: Add Note: SQL Query: ' + sql_query)
        
        anknotesDB().execute(sql_query)
         
        # anknotesDB().execute(u"INSERT OR REPLACE INTO `%s`(`guid`,`title`,`content`,`updated`,`created`,`updateSequenceNum`,`notebookGuid`,`tagGuids`,`tagNames`) VALUES (?,?,?,?,?,?,?,?,?);" % TABLE_EVERNOTE_NOTES, whole_note.guid, whole_note.title.decode('utf-8'), whole_note.content.decode('utf-8'), whole_note.updated, whole_note.created, whole_note.updateSequenceNum, whole_note.notebookGuid, u',' + u','.join(tagGuids).decode('utf-8') + u',', u',' + u','.join(tagNames).decode('utf-8') + u',')
                
        if not mw.col.conf.get(SETTING_KEEP_EVERNOTE_TAGS, SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE):
            tagNames = []
               
        return whole_note.title, whole_note.content, tagNames, whole_note.notebookGuid, whole_note.updateSequenceNum


        

class Controller:
    def __init__(self, threaded=False):
 
        self.evernoteTags = mw.col.conf.get(SETTING_EVERNOTE_TAGS_TO_IMPORT, SETTING_EVERNOTE_TAGS_TO_IMPORT_DEFAULT_VALUE).split(",")
        # Deprecated
        # self.ankiTag = mw.col.conf.get(SETTING_DEFAULT_ANKI_TAG, SETTING_DEFAULT_ANKI_TAG_DEFAULT_VALUE)
        self.deck = mw.col.conf.get(SETTING_DEFAULT_ANKI_DECK, SETTING_DEFAULT_ANKI_DECK_DEFAULT_VALUE)
        self.updateExistingNotes = mw.col.conf.get(SETTING_UPDATE_EXISTING_NOTES, UpdateExistingNotes.UpdateNotesInPlace)
        self.anki = Anki()
        # media directory
        media_dir = re.sub("(?i)\.(anki2)$", ".media", self.anki.collection().path)
        # convert dir to unicode if it's not already
        if isinstance(media_dir , str):
            media_dir = unicode(media_dir , sys.getfilesystemencoding())        
        shutil.copy2(os.path.join(PATH, ANKNOTES_CSS), os.path.join(media_dir, ANKNOTES_CSS))
        
        self.anki.add_evernote_models()
        
        anknotesInitDB()
        
        
        # self.anki.create_evernote_tables()
        # log("Creating evernote tables ... ")
        
        self.evernote = Evernote()

    def test_anki(self, title, guid, filename = ""):
        if not filename: filename = title 
        fields = {FIELD_TITLE: title, FIELD_CONTENT: file( os.path.join(PATH, filename.replace('.enex', '') + ".enex") , 'r').read(), FIELD_EVERNOTE_GUID: FIELD_EVERNOTE_GUID_PREFIX + guid}
        tags = ['NoTags', 'NoTagsToRemove']
        en_tags = ['NoTagsToRemove']
        return AnkiNotePrototype(fields, tags, en_tags)
   
        
        
    def process_toc(self):
        anki_note_ids = self.anki.get_anknotes_note_ids()
        anki_guids =  self.anki.get_guids_from_anki_note_ids(anki_note_ids)    
        self.evernote.getNoteCount = 0        
        self.anki.process_see_also_content(anki_note_ids)
        # self.anki.process_toc_and_outlines()        
        
    def proceed(self): 
            
        log("  > Starting Evernote Import")   
        if not hasattr(self.evernote, 'noteStore'):
            # if not self.evernote.initialize_note_store():
            log("Note store does not exist. Aborting.")
            return False                
            
        self.anki.evernoteTags = self.evernoteTags 
        self.evernote.evernoteTags = self.evernoteTags
        self.evernote.getNoteCount = 0
        
        anki_note_ids = self.anki.get_anknotes_note_ids()
        anki_guids =  self.anki.get_guids_from_anki_note_ids(anki_note_ids)  
        evernote_guids, self.evernote.metadata = self.get_evernote_guids_from_tags(self.evernoteTags)        
        
        notes_to_add = set(evernote_guids) - set(anki_guids)
        notes_to_update = set(evernote_guids) - set(notes_to_add)
        notes_already_up_to_date = []
        
        for evernote_guid in notes_to_update:
            db_usn = anknotesDB().scalar("SELECT updateSequenceNum FROM %s WHERE guid = ?" % TABLE_EVERNOTE_NOTES, evernote_guid)            
            server_usn =  self.evernote.metadata[evernote_guid].updateSequenceNum
            if evernote_guid in self.anki.usns:
                current_usn = self.anki.usns[evernote_guid]
                eq1 = (current_usn == str(server_usn))
                eq2 = (str(db_usn) == str(server_usn))
                
                if current_usn == str(server_usn):
                    log_info = None # 'ANKI NOTE UP-TO-DATE'
                    notes_already_up_to_date.append(evernote_guid)
                elif str(db_usn) == str(server_usn):
                    log_info = 'DATABASE ENTRY UP-TO-DATE'
                else:
                    log_info = 'NO COPIES UP-TO-DATE'
            else:
                current_usn = 'N/A'
                eq1 = 'N/A'
                eq2 = 'N/A'
                log_info = 'NO ANKI USN EXISTS'
            if log_info:
                log("   > USN check for note '%s': %s: db/current/server = %s,%s,%s;  eq: %s,%s" % (evernote_guid, log_info, str(db_usn), str(current_usn), str(server_usn), str(eq1), str(eq2)))
                
        notes_already_up_to_date = set(notes_already_up_to_date)
        notes_to_update = notes_to_update - notes_already_up_to_date
        
        log_dump(notes_to_add, "    > New Notes (%d)" % len(notes_to_add), 'note_guids')
        log_dump(notes_to_update, "    > Existing Out-Of-Date Notes (%d)" % len(notes_to_update), 'note_guids')
        log_dump(notes_already_up_to_date, "    > Existing Up-To-Date Notes (%d)" % len(notes_already_up_to_date), 'note_guids')
        
        self.anki.start_editing()
        n = self.import_into_anki(notes_to_add, self.deck)
        if self.updateExistingNotes is UpdateExistingNotes.IgnoreExistingNotes:
            tooltip = "%d new card(s) have been imported. Updating is disabled." % n
        else:
            n2 = len(notes_to_update)
            n3 = len(notes_already_up_to_date)
            if self.updateExistingNotes is UpdateExistingNotes.UpdateNotesInPlace:
                update_str = "in-place"
                self.update_in_anki(notes_to_update)
            else:
                update_str = "(deleted and re-added)"
                self.anki.delete_anki_cards(notes_to_update)
                self.import_into_anki(notes_to_update, self.deck)
            tooltip = "%d new card(s) have been imported and %d existing card(s) have been updated %s." % (n, n2, update_str)            
            if len(notes_already_up_to_date) > 0:
                tooltip += "<BR><BR>\r\n%d existing card(s) are already up-to-date with Evernote's servers, so they were not retrieved." % n3
        show_tooltip(tooltip)
        log("   > Import Complete: %s" % tooltip.replace('<BR><BR>', '')) 
        self.anki.stop_editing()
        self.anki.collection().autosave()

    def update_in_anki(self, guid_set):
        cards = self.evernote.create_evernote_cards(guid_set)
        
        number = self.anki.update_evernote_cards(cards)
        return number

    def import_into_anki(self, guid_set, deck):
        cards = self.evernote.create_evernote_cards(guid_set)
        self.anki.notebook_data = self.evernote.notebook_data
        number = self.anki.add_evernote_cards(cards, deck)
        return number

    def get_evernote_guids_from_tags(self, tags):
        notes_metadata = {}
        note_guids = []
        query = "any: "
        for tag in tags:
            query += "tag:{} ".format(tag.strip())
        evernote_filter = NoteFilter(words=query, ascending=True, order=NoteSortOrder.UPDATED)
        
        #log("   > Searching Evernote with query: " + query)
        
        spec = NotesMetadataResultSpec(includeTitle = False, includeUpdated = False, includeUpdateSequenceNum = True, includeTagGuids = True, includeNotebookGuid = True)
        
        offset = (int(mw.col.conf.get(SETTING_EVERNOTE_PAGING, 1)) - 1) * 250        
        api_action_str = u'trying to get search for note metadata'
        log(" EVERNOTE_API_CALL: findNotesMetadata: [Offset: %d]: Query: '%s'" % (offset, query), 'api')
        try:            
            result = self.evernote.noteStore.findNotesMetadata(self.evernote.token, evernote_filter, offset, EVERNOTE_METADATA_QUERY_LIMIT, spec)                           
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): return note_guids, notes_metadata
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): return note_guids, notes_metadata
            raise                 
        
        
        log("    > Metadata Results: Total Notes %d  |    Returned Notes: %d    |   Update Count: %d " % (result.totalNotes, len(result.notes), result.updateCount))
        # #log("    > Notes Metadata: ")
        
        #log_dump(pprint.pformat(result.notes, indent=4, width=80), "Notes Metadata")
        
        for note in result.notes:
            note_guids.append(note.guid)
            notes_metadata[note.guid] = note
        return note_guids, notes_metadata


def show_tooltip(text, time_out=3000):
    aqt.utils.tooltip(text, time_out)


def main(threaded=False):
    controller = Controller(threaded)
    controller.proceed()
    
def toc():
    controller = Controller()
    controller.process_toc()      
    
def do_auto_import():
    threading.Timer(AUTO_IMPORT_TIMER_INTERVAL, do_auto_import).start()
    str = "Initiating Auto Import"
    log(str)
    show_tooltip(str)
    main(True)               
    
def auto_import():          
    # aqt.anknotesDB().close()
    #aqt.anknotesDB()._db = sqlite.connect(aqt.anknotesDB()._path, check_same_thread=False)    
    threading.Timer(10, do_auto_import).start()
    


def setup_evernote(self):
    global default_anki_deck
    global evernote_default_tag
    global evernote_paging
    global evernote_tags_to_import
    global delete_evernote_tags_to_import
    global keep_evernote_tags
    global update_existing_notes
    global use_evernote_notebook_name_for_anki_deck_name

    widget = QWidget()
    layout = QVBoxLayout()
    layout_tags = QHBoxLayout()

    # Default Anki Deck
    default_anki_deck_label = QLabel("Default Anki Deck:")
    default_anki_deck = QLineEdit()
    default_anki_deck.setText(mw.col.conf.get(SETTING_DEFAULT_ANKI_DECK, SETTING_DEFAULT_ANKI_DECK_DEFAULT_VALUE))
    layout.insertWidget(int(layout.count()) + 1, default_anki_deck_label)
    layout.insertWidget(int(layout.count()) + 2, default_anki_deck)
    default_anki_deck.connect(default_anki_deck, SIGNAL("editingFinished()"), update_default_anki_deck)
    

    
    # Use Evernote Notebook Name for Anki Deck Name
    use_evernote_notebook_name_for_anki_deck_name = QCheckBox("Use Evernote Notebook Name for Anki Deck Name", self)
    use_evernote_notebook_name_for_anki_deck_name.setChecked(mw.col.conf.get(SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME, True))
    use_evernote_notebook_name_for_anki_deck_name.stateChanged.connect(update_keep_evernote_tags)
    layout.insertWidget(int(layout.count()) + 1, use_evernote_notebook_name_for_anki_deck_name)        

    # Deprecated:
    # Default Anki Tag
    # evernote_default_tag_label = QLabel("Default Anki Tag:")
    # evernote_default_tag = QLineEdit()
    # evernote_default_tag.setText(mw.col.conf.get(SETTING_DEFAULT_ANKI_TAG, SETTING_DEFAULT_ANKI_TAG_DEFAULT_VALUE))
    # layout.insertWidget(int(layout.count()) + 1, evernote_default_tag_label)
    # layout.insertWidget(int(layout.count()) + 2, evernote_default_tag)
    # evernote_default_tag.connect(evernote_default_tag, SIGNAL("editingFinished()"), update_evernote_default_tag)

    # Evernote Tags to Import
    evernote_tags_to_import_label = QLabel("Evernote Tags to Import:")
    evernote_tags_to_import = QLineEdit()
    evernote_tags_to_import.setText(mw.col.conf.get(SETTING_EVERNOTE_TAGS_TO_IMPORT, SETTING_EVERNOTE_TAGS_TO_IMPORT_DEFAULT_VALUE))
    layout.insertWidget(int(layout.count()) + 1, evernote_tags_to_import_label)
    layout.insertWidget(int(layout.count()) + 2, evernote_tags_to_import)
    evernote_tags_to_import.connect(evernote_tags_to_import,
                                    SIGNAL("editingFinished()"),
                                    update_evernote_tags_to_import)    
                                    
    # Evernote Paging
    evernote_paging_label = QLabel("Evernote Paging:")
    evernote_paging = QSpinBox()
    evernote_paging.setValue(mw.col.conf.get(SETTING_EVERNOTE_PAGING, 1))
    layout.insertWidget(int(layout.count()) + 1, evernote_paging_label)
    layout.insertWidget(int(layout.count()) + 2, evernote_paging)
    evernote_paging.connect(evernote_paging,
                                    SIGNAL("valueChanged(int)"),
                                    update_evernote_paging)                                        

    # Keep Evernote Tags
    keep_evernote_tags = QCheckBox("Keep Evernote Tags", self)
    keep_evernote_tags.setChecked(mw.col.conf.get(SETTING_KEEP_EVERNOTE_TAGS, SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE))
    keep_evernote_tags.stateChanged.connect(update_keep_evernote_tags)
    layout_tags.insertWidget(int(layout_tags.count()) + 1, keep_evernote_tags)
    

    # Delete Tags To Import 
    delete_evernote_tags_to_import = QCheckBox("Delete Evernote Tags Used To Import", self)
    delete_evernote_tags_to_import.setChecked(mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True))
    delete_evernote_tags_to_import.stateChanged.connect(update_delete_evernote_tags_to_import)
    layout_tags.insertWidget(int(layout_tags.count()) + 1, delete_evernote_tags_to_import)    
    
    # Add Horizontal Layout for Evernote Tag Options
    layout.addItem(layout_tags)  

    # Update Existing Notes
    update_existing_notes = QComboBox()
    update_existing_notes.addItems(["Ignore Existing Notes", "Update Existing Notes In-Place",
                                    "Delete and Re-Add Existing Notes"])
    update_existing_notes.setCurrentIndex(mw.col.conf.get(SETTING_UPDATE_EXISTING_NOTES,
                                                          UpdateExistingNotes.UpdateNotesInPlace))
    update_existing_notes.activated.connect(update_update_existing_notes)
    layout.insertWidget(int(layout.count()) + 1, update_existing_notes)

    # Vertical Spacer
    vertical_spacer = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
    layout.addItem(vertical_spacer)

    # Parent Widget
    widget.setLayout(layout)

    # New Tab
    self.form.tabWidget.addTab(widget, "Evernote Importer")

def update_default_anki_deck():
    mw.col.conf[SETTING_DEFAULT_ANKI_DECK] = default_anki_deck.text()

def update_evernote_paging(value):
    mw.col.conf[SETTING_EVERNOTE_PAGING] = evernote_paging.value()
    

def update_use_evernote_notebook_name_for_anki_deck_name():
    mw.col.conf[SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME] = use_evernote_notebook_name_for_anki_deck_name.isChecked()    
    
# Deprecated:    
# def update_evernote_default_tag():
    # mw.col.conf[SETTING_DEFAULT_ANKI_TAG] = evernote_default_tag.text()

def update_evernote_tags_to_import():
    mw.col.conf[SETTING_EVERNOTE_TAGS_TO_IMPORT] = evernote_tags_to_import.text()

def update_delete_evernote_tags_to_import():
    mw.col.conf[SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT] = delete_evernote_tags_to_import.isChecked()    

def update_keep_evernote_tags():
    mw.col.conf[SETTING_KEEP_EVERNOTE_TAGS] = keep_evernote_tags.isChecked()

def update_update_existing_notes(index):
    mw.col.conf[SETTING_UPDATE_EXISTING_NOTES] = index

 

action = aqt.qt.QAction("Import from Evernote", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), main)
aqt.mw.form.menuTools.addAction(action)

# action = aqt.qt.QAction("Start Evernote Auto-Import!", aqt.mw)
# aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), auto_import)
# aqt.mw.form.menuTools.addAction(action)

action = aqt.qt.QAction("Process Evernote TOC [Power Users Only!]", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), toc)
aqt.mw.form.menuTools.addAction(action)

Preferences.setupOptions = wrap(Preferences.setupOptions, setup_evernote)
