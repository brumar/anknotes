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


from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.type.ttypes import NoteSortOrder
from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode
from evernote.api.client import EvernoteClient

import anki
import aqt
from anki.hooks import wrap
from aqt.preferences import Preferences
from aqt.utils import getText, openLink, getOnlyText
from aqt.qt import QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, SIGNAL, QCheckBox, \
QComboBox, QSpacerItem, QSizePolicy, QWidget, QSpinBox, QFormLayout, QGridLayout, QFrame, QPalette, \
QRect, QStackedLayout, QDateEdit, QDateTimeEdit, QTimeEdit, QDate, QDateTime, QTime, QPushButton, QIcon, QMessageBox, QPixmap
from aqt import mw


PATH = os.path.dirname(os.path.abspath(__file__))
ANKNOTES_TEMPLATE_FRONT = 'FrontTemplate.htm'
ANKNOTES_CSS = u'_AviAnkiCSS.css'
ANKNOTES_ICON_EVERNOTE_WEB = u'evernote_web.ico'
ANKNOTES_IMAGE_EVERNOTE_WEB = ANKNOTES_ICON_EVERNOTE_WEB.replace('.ico', '.png')
ANKNOTES_ICON_EVERNOTE_ARTCORE = u'evernote_artcore.ico'
ANKNOTES_IMAGE_EVERNOTE_ARTCORE = ANKNOTES_ICON_EVERNOTE_ARTCORE.replace('.ico', '.png')
ANKNOTES_LOG_BASE_PATH = 'logs\\anknotes'

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

# Note that Evernote's API documentation says not to run API calls to findNoteMetadata with any less than a 15 minute interval
EVERNOTE_PAGING_RESTART_INTERVAL = 60 * 15
# Auto Paging is probably only useful in the first 24 hours, when API usage is unlimited,  or when executing a search that is likely to have most of the notes up-to-date locally
# To keep from overloading Evernote's servers, and flagging our API key, I recommend pausing 5-15 minutes in between searches, the higher the better.
EVERNOTE_PAGING_TIMER_INTERVAL = 60 * 15
# Obviously setting this to True will result in an infinite loop with Anki never being responsive. 
# This is intended to be used while keeping Anki open overnight, and force-closing Anki with the task manager when you are done
EVERNOTE_PAGING_RESTART_WHEN_COMPLETE = False
EVERNOTE_METADATA_QUERY_LIMIT = 10000
EVERNOTE_GET_NOTE_LIMIT = 10000

SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE = True
SETTING_EVERNOTE_QUERY_TAGS_DEFAULT_VALUE = "#Anki_Import"
SETTING_DEFAULT_ANKI_DECK_DEFAULT_VALUE = DECK_DEFAULT

ANKNOTES_EVERNOTE_CONSUMER_KEY = "holycrepe"
ANKNOTES_EVERNOTE_IS_SANDBOXED = False

SETTING_EVERNOTE_QUERY_TAGS = 'anknotesEvernoteQueryTags'
SETTING_EVERNOTE_QUERY_USE_TAGS = 'anknotesEvernoteQueryUseTags'
SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_RELATIVE = 'anknotesEvernoteQueryLastUpdatedValueRelative'
SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE =  'anknotesEvernoteQueryLastUpdatedValueAbsoluteDate'
SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME =  'anknotesEvernoteQueryLastUpdatedValueAbsoluteDateTime'
SETTING_EVERNOTE_QUERY_LAST_UPDATED_TYPE =  'anknotesEvernoteQueryLastUpdatedType'
SETTING_EVERNOTE_QUERY_USE_LAST_UPDATED = 'anknotesEvernoteQueryUseLastUpdated'
SETTING_EVERNOTE_QUERY_NOTEBOOK = 'anknotesEvernoteQueryNotebook'
SETTING_EVERNOTE_QUERY_NOTEBOOK_DEFAULT_VALUE = 'My Anki Notebook'
SETTING_EVERNOTE_QUERY_USE_NOTEBOOK = 'anknotesEvernoteQueryUseNotebook'
SETTING_EVERNOTE_QUERY_NOTE_TITLE = 'anknotesEvernoteQueryNoteTitle'
SETTING_EVERNOTE_QUERY_USE_NOTE_TITLE = 'anknotesEvernoteQueryUseNoteTitle'
SETTING_EVERNOTE_QUERY_SEARCH_TERMS = 'anknotesEvernoteQuerySearchTerms'
SETTING_EVERNOTE_QUERY_USE_SEARCH_TERMS = 'anknotesEvernoteQueryUseSearchTerms'
SETTING_EVERNOTE_QUERY_ANY = 'anknotesEvernoteQueryAny'

SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT = 'anknotesDeleteEvernoteTagsToImport'
SETTING_UPDATE_EXISTING_NOTES = 'anknotesUpdateExistingNotes'
SETTING_EVERNOTE_PAGINATION_CURRENT_PAGE = 'anknotesEvernotePaginationCurrentPage'
SETTING_EVERNOTE_AUTO_PAGING = 'anknotesEvernoteAutoPaging'
SETTING_EVERNOTE_AUTH_TOKEN = 'anknotesEvernoteAuthToken_' + ANKNOTES_EVERNOTE_CONSUMER_KEY
if ANKNOTES_EVERNOTE_IS_SANDBOXED: SETTING_EVERNOTE_AUTH_TOKEN += "_SANDBOX"
SETTING_KEEP_EVERNOTE_TAGS = 'anknotesKeepEvernoteTags'
SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME = 'anknotesUseEvernoteNotebookNameForAnkiDeckName'
SETTING_DEFAULT_ANKI_DECK = 'anknotesDefaultAnkiDeck'

class UpdateExistingNotes:
    IgnoreExistingNotes, UpdateNotesInPlace, DeleteAndReAddNotes = range(3)
    
class EvernoteQueryLocationType:
    RelativeDay, RelativeWeek, RelativeMonth, RelativeYear, AbsoluteDate, AbsoluteDateTime = range(6)
    
class RateLimitErrorHandling:
    IgnoreError, ToolTipError, AlertError = range(3)    
    
EDAM_RATE_LIMIT_ERROR_HANDLING = RateLimitErrorHandling.ToolTipError 
 
 
class EvernoteQueryLocationValueQSpinBox(QSpinBox):
    __prefix = ""
    def setPrefix(self, text):
        self.__prefix = text 
    def prefix(self):
        return self.__prefix
    def valueFromText(self, text):        
        if text == self.prefix():
            return 0
        return text[len(self.prefix())+1:]
    def textFromValue(self, value):
        if value == 0:
            return self.prefix() 
        return self.prefix() + "-" + str(value)

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
def anknotesInitDb_Tags(force = False):
    if_exists = " IF NOT EXISTS" if not force else ""
    anknotesDB().execute("""CREATE TABLE %s `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `parentGuid` TEXT, `updateSequenceNum` INTEGER NOT NULL, PRIMARY KEY(guid) );""" % (if_exists,TABLE_EVERNOTE_TAGS)) 
def anknotesInitDb_Notebooks(force = False):
    if_exists = " IF NOT EXISTS" if not force else ""
    anknotesDB().execute("""CREATE TABLE %s `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `serviceUpdated` INTEGER NOT NULL, `stack` TEXT, PRIMARY KEY(guid) );""" % (if_exists, TABLE_EVERNOTE_NOTEBOOKS))
def anknotesInitDB():
    adb = anknotesDB() 
    adb.execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL, PRIMARY KEY(guid) );""" % TABLE_EVERNOTE_NOTES)
    adb.execute( """CREATE TABLE IF NOT EXISTS `%s` ( `id` INTEGER, `source_evernote_guid` TEXT NOT NULL, `number` INTEGER NOT NULL DEFAULT 100, `uid` INTEGER NOT NULL DEFAULT -1, `shard` TEXT NOT NULL DEFAULT -1, `target_evernote_guid` TEXT NOT NULL, `html` TEXT NOT NULL, `title` TEXT NOT NULL, `from_toc` INTEGER DEFAULT 0, `is_toc` INTEGER DEFAULT 0, `is_outline` INTEGER DEFAULT 0, PRIMARY KEY(id) );""" % TABLE_SEE_ALSO) 
    anknotesInitDb_Tags()
    anknotesInitDb_Notebooks()

def anknotesDB(): 
    return mw.col.db

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
    # Regex .NET Version: <a href="(?<URL>evernote:///?view/(?<uid>[\d]+?)/(?<shard>s\d+)/(?<guid>[\w\-]+?)/(\k<guid>)/?)"(?: [^>]*?)?>(?<Title>.+?)</a>
    return re.finditer(r'<a href="(?P<URL>evernote:///?view/(?P<uid>[\d]+?)/(?P<shard>s\d+)/(?P<guid>[\w\-]+?)/(?P=guid)/?)"(?: shape="rect")?>(?P<Title>.+?)</a>', content)    

def log(content, filename='', prefix=''):
    if content[0] == "!":
        content = content[1:]
        prefix = '\n'        
    if not filename: filename = ANKNOTES_LOG_BASE_PATH + '.log'
    else: 
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = ANKNOTES_LOG_BASE_PATH + '-%s.log' % filename        
    try:
        content=content.encode('ascii', 'ignore')       
    except Exception:
        pass
    content = content.replace('\r', '\r                              ').replace('\n', '\n                              ')    
    st = str(datetime.now()).split('.')[0]
    full_path = PATH + '\\' + filename
    if not os.path.exists(os.path.dirname(full_path)): 
        os.mkdir(os.path.dirname(full_path))
    with open(full_path , 'a+') as fileLog:
        print>>fileLog, prefix + ' [%s]: ' % st + content 
    
def log_sql(value):
    log(value, 'sql')

def log_error(value):
    log(value, '+error')    
    
def log_dump(obj, title="Object", filename=''):
    if not filename: filename = ANKNOTES_LOG_BASE_PATH + '-dump.log'
    else: 
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = ANKNOTES_LOG_BASE_PATH + '-dump-%s.log' % filename
    content = pprint.pformat(obj, indent=4, width=80)
    try:
        content=content.encode('ascii', 'ignore') 
    except Exception:
        pass
    st = str(datetime.now()).split('.')[0]    
    if title[0] is '-':
        prefix = " **** Dumping %s" % title[1:]
    else:        
        prefix = " **** Dumping %s" % title
        log(prefix)
    prefix += '\r\n' 
    content = prefix + content.replace(', ', ', \n ')
    content = content.replace('\r', '\r                              ').replace('\n', '\n                              ')
    full_path = PATH + '\\' + filename
    if not os.path.exists(os.path.dirname(full_path)): 
        os.mkdir(os.path.dirname(full_path))
    with open(full_path, 'a+') as fileLog:
        print>>fileLog, '\n [%s]: ' % st + content     

def get_dict_from_list(list, keys_to_ignore=list()):
    dict = {}
    for key, value in list: 
        if not key in keys_to_ignore: dict[key] = value  
    return dict 
    
def get_evernote_guid_from_anki_fields(fields):        
    if not FIELD_EVERNOTE_GUID in fields: return None
    return fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '')    
        
class AnkiNotePrototype:
    fields = {}
    tags = []
    evernote_query_tags = []
    model_name = ""    
    evernote_guid = ""
    cloze_count = 0
    def __init__(self, fields, tags, evernote_query_tags = list()):
        self.fields = fields
        self.tags = tags 
        self.evernote_guid = get_evernote_guid_from_anki_fields(fields)
        self.evernote_query_tags = evernote_query_tags
        self.cloze_count = 0
        self.model_name = MODEL_EVERNOTE_DEFAULT 
        self.process_note()
    
    def evernote_cloze_regex(self, match):
        matchText = match.group(1)    
        if matchText[0] == "#":
            matchText = matchText[1:]
        else:
            self.cloze_count += 1    
        if self.cloze_count == 0:
            self.cloze_count = 1
        return "{{c%d::%s}}" % (self.cloze_count, matchText)

    def process_note_see_also(self):
        if not FIELD_SEE_ALSO in self.fields or not FIELD_EVERNOTE_GUID in self.fields:
            return         
        anknotesDB().execute("DELETE FROM %s WHERE source_evernote_guid = '%s' " % (TABLE_SEE_ALSO, self.evernote_guid))
        link_num = 0
        for match in find_evernote_links(self.fields[FIELD_SEE_ALSO]):
            link_num += 1
            title_text = strip_tags(match.group('Title'))
            is_toc = 1 if (title_text == "TOC") else 0
            is_outline = 1 if (title_text is "O" or title_text is "Outline") else 0
            anknotesDB().execute("INSERT INTO %s (source_evernote_guid, number, uid, shard, target_evernote_guid, html, title, from_toc, is_toc, is_outline) VALUES('%s', %d, %d, '%s', '%s', '%s', '%s', 0, %d, %d)" % (TABLE_SEE_ALSO, self.evernote_guid,link_num, int(match.group('uid')), match.group('shard'), match.group('guid'), match.group('Title'), title_text, is_toc, is_outline))
            
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
        if see_also_match:
            content = content.replace(see_also_match.group(0), see_also_match.group('Suffix'))
            self.fields[FIELD_SEE_ALSO] = see_also_match.group('SeeAlso').replace('<b style="color: rgb(0, 0, 0); font-family: Tahoma; font-style: normal; font-variant: normal; letter-spacing: normal; orphans: 2; text-align: -webkit-auto; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-size-adjust: auto; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); font-size: medium;">', '<b>')                 
            self.process_note_see_also()
        
        # TODO: Add support for extracting an 'Extra' field from the Evernote Note contents        
        ################################## Note Processing complete. 
        self.fields[FIELD_CONTENT] = content
    
    def detect_note_model(self):
        delete_evernote_query_tags = mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True)
        if FIELD_CONTENT in self.fields and "{{c1::" in self.fields[FIELD_CONTENT]: 
            self.model_name = MODEL_EVERNOTE_CLOZE
        elif EVERNOTE_TAG_REVERSIBLE in self.tags: 
            self.model_name = MODEL_EVERNOTE_REVERSIBLE
            if delete_evernote_query_tags: self.tags.remove(EVERNOTE_TAG_REVERSIBLE)
        elif EVERNOTE_TAG_REVERSE_ONLY in self.tags: 
            model_name = MODEL_EVERNOTE_REVERSE_ONLY
            if delete_evernote_query_tags: self.tags.remove(EVERNOTE_TAG_REVERSE_ONLY)    
    
    def process_note(self):   
        self.process_note_content()                
        self.detect_note_model()

class Anki:
    def update_evernote_notes(self, evernote_notes):
        return self.add_evernote_notes(evernote_notes, None, True)
        
    def get_deck_name_from_evernote_notebook(self, notebookGuid, deck):
        if not notebookGuid in self.notebook_data:
            log_error("Unexpected error: Notebook GUID '%s' could not be found in notebook data: %s" % (notebookGuid, str(self.notebook_data)))
            notebook = anknotesDB().first("SELECT name, stack FROM %s WHERE guid = '%s'" % (TABLE_EVERNOTE_NOTEBOOKS, notebookGuid))
            if not notebook: 
                log_error("   get_deck_name_from_evernote_notebook FATAL ERROR: UNABLE TO FIND NOTEBOOK '%s'. " % notebookGuid)                        
                return None
            log("Getting notebook info: %s" % str(notebook))
            notebook_name, notebook_stack = notebook
            self.notebook_data[notebookGuid] = {"stack": notebook_stack, "name": notebook_name}
        notebook = self.notebook_data[notebookGuid]
        if notebook['stack']:
            deck += u'::' + notebook['stack']
        deck += "::" + notebook['name']
        deck = deck.replace(": ", "::")           
        if deck[:2] == '::':
            deck = deck[2:]
        return deck

    def add_evernote_notes(self, evernote_notes, deck, update=False):
        count = 0
        deck_original = deck
        for note in evernote_notes:
            try: 
                title = note.title
                content = note.content
                if isinstance(title , str):
                    title = unicode(title , 'utf-8')  
                if isinstance(content , str):
                    content = unicode(content , 'utf-8')  
                    # content = unicode(content , sys.getfilesystemencoding())                        
                
                anki_field_info = {
                                   FIELD_TITLE: title,
                                   FIELD_CONTENT: content,
                                   FIELD_EVERNOTE_GUID: FIELD_EVERNOTE_GUID_PREFIX + note.guid,
                                   FIELD_UPDATE_SEQUENCE_NUM: str(note.updateSequenceNum)
                                   }
            except:
                log_error("Unable to set field info for: Note '%s': '%s'" % (note.title , note.guid ))
                log_dump(note.content, " NOTE CONTENTS ")
                log_dump(note.content.encode('utf-8'), " NOTE CONTENTS ")
                raise                
            if not update:
                anki_field_info.update ({FIELD_SEE_ALSO: u'', FIELD_TOC: u'', FIELD_OUTLINE: u'', FIELD_EXTRA: u'',})  
                if EVERNOTE_TAG_TOC in note.tags:
                    deck = DECK_TOC     
                elif EVERNOTE_TAG_OUTLINE in note.tags:
                    deck = DECK_OUTLINE
                elif not deck_original or mw.col.conf.get(SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME, True):  
                        deck = self.get_deck_name_from_evernote_notebook(note.notebookGuid, deck_original)        
                        if not deck: return None
                if deck[:2] == '::':
                    deck = deck[2:]
            anki_note_prototype = AnkiNotePrototype(anki_field_info, note.tags, self.evernoteTags)
            if update:
                debug_fields = anki_note_prototype.fields.copy()
                del debug_fields[FIELD_CONTENT]
                log_dump(debug_fields, "-      > UPDATE_evernote_notes → ADD_evernote_notes: anki_note_prototype: FIELDS ")            
                self.update_note(anki_note_prototype)
                count += 1
            else:
                if not -1 == self.add_note(deck, anki_note_prototype): count += 1            
        return count

    def delete_anki_cards(self, evernote_guids):
        col = self.collection()
        card_ids = []
        for evernote_guid in evernote_guids:
            card_ids += mw.col.findCards(FIELD_EVERNOTE_GUID_PREFIX + evernote_guid)
        col.remCards(card_ids)
        return len(card_ids)

    def update_note(self, anki_note_prototype):
        col = self.collection()
        evernote_guid = get_evernote_guid_from_anki_fields(anki_note_prototype.fields)
        anki_note_id = col.findNotes(evernote_guid)[0]
        note = anki.notes.Note(col, None, anki_note_id)
        value = u','.join(anki_note_prototype.tags)
        value_original = u','.join(note.tags)
        flag_changed = (value != value_original)
        if flag_changed:
            log("Changing tags:\n From: '%s' \n To:   '%s'" % (value_original, value  ), 'AddUpdateNote')
            note.tags = anki_note_prototype.tags                
        fields_to_update = [FIELD_TITLE, FIELD_CONTENT, FIELD_SEE_ALSO, FIELD_UPDATE_SEQUENCE_NUM]
        fld_content_ord = -1
        log_dump({'note.fields': note.fields, 'note._model.flds': note._model['flds']}, "-      > UPDATE_NOTE → anki.notes.Note: _model: flds")   
        flag_changed = False
        for fld in note._model['flds']:
            if FIELD_EVERNOTE_GUID in fld.get('name'):
                    eguid_original = note.fields[fld.get('ord')].replace(FIELD_EVERNOTE_GUID_PREFIX, '')        
            for field_to_update in fields_to_update:                
                if field_to_update in fld.get('name') and field_to_update in anki_note_prototype.fields:
                    if field_to_update is FIELD_CONTENT:
                        fld_content_ord = fld.get('ord')                
                    try:
                        value = anki_note_prototype.fields[field_to_update]
                        value_original = note.fields[fld.get('ord')]
                        if isinstance(value , str):
                            value = unicode(value , 'utf-8')  
                        if isinstance(value_original , str):
                            value_original = unicode(value_original , 'utf-8')  
                        if not value == value_original:
                            flag_changed = True
                            note.fields[fld.get('ord')] = value
                            log("Changing field #%d %s:\n From: '%s' \n To:   '%s'" % (fld.get('ord'), field_to_update, value_original, value  ), 'AddUpdateNote')
                    except:
                        log_error("ERROR: UPDATE_NOTE: Note '%s': %s: Unable to set note.fields for field '%s'. Ord: %s. Note fields count: %d" % (anki_note_prototype.evernote_guid, anki_note_prototype.fields[FIELD_TITLE], field_to_update, str(fld.get('ord')), len(note.fields)) )
                        raise
        
        if not fld_content_ord is -1:
            debug_fields = list(note.fields)
            del debug_fields[fld_content_ord]
            log_dump(debug_fields, "-      > UPDATE_NOTE → anki.notes.Note: FIELDS ")          
        
        
        if flag_changed:
            db_title = anknotesDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (TABLE_EVERNOTE_NOTES, eguid_original))            
            log(' %s: UPDATE: ' % anki_note_prototype.fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '') +'    ' + anki_note_prototype.fields[FIELD_TITLE], 'AddUpdateNote')   
            if anki_note_prototype.fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '') != eguid_original or anki_note_prototype.fields[FIELD_TITLE] != db_title:
                log(' %s:     DB: ' % eguid_original +'    ' + db_title, 'AddUpdateNote')   
            note.flush()            
        else:
            log("Not updating Note '%s': no fields have been changed" % evernote_guid)
        return note.id

    def add_note(self, deck_name, anki_note_prototype):
        note = self.create_note(deck_name, anki_note_prototype)
        if note is not None:
            collection = self.collection()
            db_title = anknotesDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (TABLE_EVERNOTE_NOTES, anki_note_prototype.fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '')))
            log(' %s:    ADD: ' % anki_note_prototype.fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '') + '    ' + anki_note_prototype.fields[FIELD_TITLE], 'AddUpdateNote')            
            if anki_note_prototype.fields[FIELD_TITLE] != db_title:
                log(' %s:     DB: ' % re.sub(r'.', ' ', anki_note_prototype.fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, '')) + '    ' + db_title, 'AddUpdateNote')            
            
            try:
                collection.addNote(note)
            except:
                log_error("Unable to collection.addNote for Note %s:    %s" % (anki_note_prototype.fields[FIELD_EVERNOTE_GUID].replace(FIELD_EVERNOTE_GUID_PREFIX, ''), db_title))
                log_dump(note.fields, '- FAILED collection.addNote: ')
                return -1
            
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
            evernote_usn_field['font'] = 'Consolas'
            evernote_usn_field['size'] = 10
            mm.addField(model, evernote_usn_field)
            
            # Add Templates
                
            if modelName is MODEL_EVERNOTE_DEFAULT or modelName is MODEL_EVERNOTE_REVERSIBLE:
                # Add Default Template
                default_template = mm.newTemplate(TEMPLATE_EVERNOTE_DEFAULT)
                default_template['qfmt'] =  templates['Front']
                default_template['afmt'] =  templates['Back']
                mm.addTemplate(model, default_template)
            if modelName is MODEL_EVERNOTE_REVERSE_ONLY or modelName is MODEL_EVERNOTE_REVERSIBLE:
                # Add Reversed Template
                reversed_template = mm.newTemplate(TEMPLATE_EVERNOTE_REVERSED)
                reversed_template['qfmt'] =  templates['Front']
                reversed_template['afmt'] =  templates['Back']
                mm.addTemplate(model, reversed_template)
            if modelName is MODEL_EVERNOTE_CLOZE:
                # Add Cloze Template        
                cloze_template = mm.newTemplate(TEMPLATE_EVERNOTE_CLOZE)
                cloze_template['qfmt'] =  templates['Front']
                cloze_template['afmt'] =  templates['Back']                
                mm.addTemplate(model, cloze_template)
                
            # Update Sort field to Title (By default set to GUID since it is the first field)
            model['sortf'] = 1
           
            # Update Model CSS
            model['css'] = '@import url("_AviAnkiCSS.css");'
            
            # Set Type to Cloze 
            if cloze:
                model['type'] = MODEL_TYPE_CLOZE
            
            # Add Model to Collection
            mm.add(model)        
        
        # Add Model id to list
        self.evernoteModels[modelName] = model['id']
        
    def add_evernote_models(self):      
        col = self.collection()
        mm = col.models 
        field_names = {"Title": FIELD_TITLE, "Content": FIELD_CONTENT, "Extra": FIELD_EXTRA, "See Also": FIELD_SEE_ALSO, "TOC": FIELD_TOC, "Outline": FIELD_OUTLINE}
                
        # Generate Front and Back Templates from HTML Template in anknotes' addon directory
        templates = {"Front": file( os.path.join(PATH, ANKNOTES_TEMPLATE_FRONT) , 'r').read() % field_names } 
        templates["Back"] = templates["Front"].replace("<div id='Side-Front'>", "<div id='Side-Back'>")
        
        self.evernoteModels = {}
        self.add_evernote_model(mm, MODEL_EVERNOTE_DEFAULT,  templates)
        self.add_evernote_model(mm, MODEL_EVERNOTE_REVERSE_ONLY,  templates)
        self.add_evernote_model(mm, MODEL_EVERNOTE_REVERSIBLE,  templates)
        self.add_evernote_model(mm, MODEL_EVERNOTE_CLOZE,  templates, True)
        
    def setup_ancillary_files(self):
        # Copy CSS file from anknotes addon directory to media directory 
        media_dir = re.sub("(?i)\.(anki2)$", ".media", self.collection().path)
        if isinstance(media_dir , str):
            media_dir = unicode(media_dir , sys.getfilesystemencoding())        
        shutil.copy2(os.path.join(PATH, ANKNOTES_CSS), os.path.join(media_dir, ANKNOTES_CSS))            
        
    def get_anki_fields_from_anki_note_id(self, a_id, fields_to_ignore=list()):
        note = self.collection().getNote(a_id)
        try: items = note.items()   
        except:
            log_error("Unable to get note items for Note ID: %d" % a_id)
            raise        
        return get_dict_from_list(items, fields_to_ignore)     
    
    def get_evernote_guids_from_anki_note_ids(self, ids, process_usns=True):
        evernote_guids = []
        self.usns = {}
        for a_id in ids:
            fields = self.get_anki_fields_from_anki_note_id(a_id, [FIELD_CONTENT])  
            evernote_guid = get_evernote_guid_from_anki_fields(fields)
            if not evernote_guid: continue
            evernote_guids.append(evernote_guid)
            log('Anki USN for Note %s is %s' % (evernote_guid, fields[FIELD_UPDATE_SEQUENCE_NUM]), 'anki-usn')
            if FIELD_UPDATE_SEQUENCE_NUM in fields: self.usns[evernote_guid] = fields[FIELD_UPDATE_SEQUENCE_NUM]    
            else: log("   ! get_evernote_guids_from_anki_note_ids: Note '%s' is missing USN!" % evernote_guid)
        return evernote_guids           
    
    def get_evernote_guids_and_anki_fields_from_anki_note_ids(self, ids):
        evernote_guids = {}
        for a_id in ids:
            fields = self.get_anki_fields_from_anki_note_id(a_id)
            evernote_guid = get_evernote_guid_from_anki_fields(fields)
            if evernote_guid: evernote_guids[evernote_guid] = fields
        return evernote_guids             

    def search_evernote_models_query(self):        
        query = ""
        delimiter = ""
        for mName, mid in self.evernoteModels.items():
            query += delimiter + "mid:" + str(mid)
            delimiter = " OR "
        return query 
            
    def get_anknotes_note_ids(self):
        ids = self.collection().findNotes(self.search_evernote_models_query())
        return ids        
        
    def get_anki_note_from_evernote_guid(self, evernote_guid):
        col = self.collection()
        ids = col.findNotes(FIELD_EVERNOTE_GUID_PREFIX + evernote_guid)        
        # TODO: Ugly work around for a bug. Fix this later
        if not ids: return None
        if not ids[0]: return None 
        note = anki.notes.Note(col, None, ids[0])
        return note
        
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
        self.extract_links_from_toc()
        self.insert_toc_and_outline_contents_into_notes()        
        
    def extract_links_from_toc(self):
        toc_anki_ids = self.get_anknotes_note_ids_by_tag(EVERNOTE_TAG_TOC)
        toc_evernote_guids = self.get_evernote_guids_and_anki_fields_from_anki_note_ids(toc_anki_ids)
        query_update_toc_links = "UPDATE %s SET is_toc = 1 WHERE " % TABLE_SEE_ALSO
        delimiter = ""
        link_exists = 0
        for toc_evernote_guid, fields in toc_evernote_guids.items():
            for match in find_evernote_links(fields[FIELD_CONTENT]): 
                target_evernote_guid = match.group('guid')
                uid = int(match.group('uid'))
                shard = match.group('shard')
                if target_evernote_guid is toc_evernote_guid: continue 
                link_title = strip_tags(match.group('Title'))
                link_number = 1 + anknotesDB().scalar("select COUNT(*) from %s WHERE source_evernote_guid = '%s' " % (TABLE_SEE_ALSO, target_evernote_guid))
                toc_link_title = fields[FIELD_TITLE]
                toc_link_html = '<span style="color: rgb(173, 0, 0);"><b>%s</b></span>' % toc_link_title
                query = """INSERT INTO `%s`(`source_evernote_guid`, `number`, `uid`, `shard`, `target_evernote_guid`, `html`, `title`, `from_toc`, `is_toc`)
SELECT '%s', %d, %d, '%s', '%s', '%s', '%s', 1, 1 FROM `%s` 
WHERE NOT EXISTS (SELECT * FROM `%s` 
      WHERE `source_evernote_guid`='%s' AND `target_evernote_guid`='%s') 
LIMIT 1 """ % (TABLE_SEE_ALSO, target_evernote_guid, link_number, uid, shard,  toc_evernote_guid, toc_link_html.replace(u'\'', u'\'\''), toc_link_title.replace(u'\'', u'\'\''), TABLE_SEE_ALSO, TABLE_SEE_ALSO, target_evernote_guid, toc_evernote_guid)
                log_sql('UPDATE_ANKI_DB: Add See Also Link: SQL Query: ' + query)
                anknotesDB().execute(query)
            query_update_toc_links += delimiter + "target_evernote_guid = '%s'" % toc_evernote_guid
            delimiter = " OR "        
        anknotesDB().execute(query_update_toc_links)               
        
    def insert_toc_and_outline_contents_into_notes(self):    
        linked_notes_fields = {}
        for source_evernote_guid in anknotesDB().list("select DISTINCT source_evernote_guid from %s WHERE is_toc = 1 ORDER BY source_evernote_guid ASC" % TABLE_SEE_ALSO):
            note = self.get_anki_note_from_evernote_guid(source_evernote_guid)
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
            for target_evernote_guid, is_toc, is_outline in anknotesDB().execute("select target_evernote_guid, is_toc, is_outline from %s WHERE source_evernote_guid = '%s' AND (is_toc = 1 OR is_outline = 1) ORDER BY number ASC" % (TABLE_SEE_ALSO, source_evernote_guid)):    
                if target_evernote_guid in linked_notes_fields:
                    linked_note_contents = linked_notes_fields[target_evernote_guid][FIELD_CONTENT]
                    linked_note_title = linked_notes_fields[target_evernote_guid][FIELD_TITLE]
                else:                    
                    linked_note = self.get_anki_note_from_evernote_guid(target_evernote_guid)
                    if not linked_note: continue 
                    linked_note_contents = u""
                    for fld in linked_note._model['flds']:
                        if FIELD_CONTENT in fld.get('name'):
                            linked_note_contents = linked_note.fields[fld.get('ord')]                        
                        elif FIELD_TITLE in fld.get('name'):
                            linked_note_title = linked_note.fields[fld.get('ord')]                   
                    if linked_note_contents:
                        linked_notes_fields[target_evernote_guid] = {FIELD_TITLE: linked_note_title, FIELD_CONTENT: linked_note_contents}
                if linked_note_contents: 
                    if isinstance(linked_note_contents , str):
                        linked_note_contents = unicode(linked_note_contents , 'utf-8')                     
                    if is_toc:      
                        toc_count += 1
                        if toc_count is 1:
                            toc_header = "<span class='header'>TABLE OF CONTENTS</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:                            
                            toc_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (toc_count, linked_note_title)
                            note_toc += "<BR><HR>"
                           
                        note_toc += linked_note_contents
                        log("   > Appending TOC #%d contents" % toc_count) 
                    else:
                        outline_count += 1
                        if outline_count is 1:
                            outline_header = "<span class='header'>OUTLINE</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:                            
                            outline_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (outline_count, linked_note_title)
                            note_outline += "<BR><HR>"
                           
                        note_outline += linked_note_contents
                        log("   > Appending Outline #%d contents" % outline_count) 
                        
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
                log(" > Flushing Note \r\n")
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




class Evernote(object):
    class EvernoteNote:
        title = ""
        content = ""
        guid = ""
        updateSequenceNum = -1
        tags = []
        notebookGuid = ""
        status = -1
        
        def __init__(self, title=None, content=None, guid=None, tags=None, notebookGuid=None, updateSequenceNum=None, whole_note=None):
            self.status = -1
            self.tags = tags 
            if not whole_note is None:
                self.title = whole_note.title
                self.content = whole_note.content
                self.guid = whole_note.guid 
                self.notebookGuid = whole_note.notebookGuid
                self.updateSequenceNum = whole_note.updateSequenceNum                
                return
            self.title = title
            self.content = content
            self.guid = guid
            self.notebookGuid = notebookGuid
            self.updateSequenceNum = updateSequenceNum
     
            
    class EvernoteNoteFetcher(object):
        class EvernoteNoteFetcherResult(object):
            def __init__(self, note=None, status=-1, source=-1):
                self.note = note 
                self.status = status 
                self.source = source 
        def __init__(self, evernote, evernote_guid = None):
            self.result = self.EvernoteNoteFetcherResult()
            self.api_calls = 0
            self.keepEvernoteTags = True         
            self.evernote = evernote #uper(Evernote.EvernoteNoteFetcher, self)
            if not evernote_guid:
                self.evernote_guid = "" 
                self.updateSequenceNum = -1
                return             
            self.evernote_guid = evernote_guid 
            self.updateSequenceNum = self.evernote.metadata[self.evernote_guid].updateSequenceNum
            self.keepEvernoteTags = True 
            self.getNote()    
          
        def getNoteLocal(self):
            # Check Anknotes database for note
            db_note = anknotesDB().first("SELECT guid, title, content, notebookGuid, tagNames FROM %s WHERE guid = '%s' AND `updateSequenceNum` = %d" % (TABLE_EVERNOTE_NOTES, self.evernote_guid, self.updateSequenceNum))
            if not db_note: return False
            note_guid, note_title, note_content, note_notebookGuid, note_tagNames = db_note
            log("  > getNoteLocal: Note '%s': '%s' has an up-to-date entry in the Anknotes db. Skipping API call and using db entry instead. " % (self.evernote_guid, note_title), 'api')
            self.tagNames = [] if not self.keepEvernoteTags else note_tagNames[1:-1].split(',')                   
            self.result.note = self.evernote.EvernoteNote(note_title, note_content, note_guid, self.tagNames, note_notebookGuid, self.updateSequenceNum)      
            assert self.result.note.guid == self.evernote_guid
            self.result.status = 0
            self.result.source = 1
            return True

        def addNoteFromServerToDB(self):
            # Note that values inserted into the db need to be converted from byte strings (utf-8) to unicode
            title = self.whole_note.title
            content = self.whole_note.content
            tag_names =  u',' + u','.join(self.tagNames).decode('utf-8') + u','
            if isinstance(title , str):
                title = unicode(title , 'utf-8')  
            if isinstance(content , str):
                content = unicode(content , 'utf-8') 
            if isinstance(tag_names , str):
                tag_names = unicode(tag_names , 'utf-8')  
            title = title.replace(u'\'', u'\'\'')
            content = content.replace(u'\'', u'\'\'')
            tag_names = tag_names.replace(u'\'', u'\'\'')
            sql_query = u'INSERT OR REPLACE INTO `%s`(`guid`,`title`,`content`,`updated`,`created`,`updateSequenceNum`,`notebookGuid`,`tagGuids`,`tagNames`) VALUES (\'%s\',\'%s\',\'%s\',%d,%d,%d,\'%s\',\'%s\',\'%s\');' % (TABLE_EVERNOTE_NOTES, self.whole_note.guid.decode('utf-8'), title, content, self.whole_note.updated, self.whole_note.created, self.whole_note.updateSequenceNum, self.whole_note.notebookGuid.decode('utf-8'), u',' + u','.join(self.tagGuids).decode('utf-8') + u',', tag_names)
            log_sql('UPDATE_ANKI_DB: Add Note: SQL Query: ' + sql_query)
            anknotesDB().execute(sql_query)     
        
        def getNoteRemoteAPICall(self):
            api_action_str = u'trying to retrieve a note. We will save the notes downloaded thus far.'
            log(" EVERNOTE_API_CALL: getNote: %3d: GUID: '%s'" % (self.api_calls + 1, self.evernote_guid), 'api')        
            try:                        
                self.whole_note = self.evernote.noteStore.getNote(self.evernote.token, self.evernote_guid, True, False, False, False)                                          
            except EDAMSystemException as e:
                if HandleEDAMRateLimitError(e, api_action_str): 
                    self.result.status = 1
                    return False
                raise         
            except socket.error, v:
                if HandleSocketError(v, api_action_str): 
                    self.result.status = 2
                    return False
                raise 
            assert self.whole_note.guid == self.evernote_guid 
            self.result.status = 0
            self.result.source = 2
            return True
        
        def getNoteRemote(self):
            # if self.getNoteCount > EVERNOTE_GET_NOTE_LIMIT: 
                # log("Aborting Evernote.getNoteRemote: EVERNOTE_GET_NOTE_LIMIT of %d has been reached" % EVERNOTE_GET_NOTE_LIMIT)
                # return None        
            if not self.getNoteRemoteAPICall(): return False 
            self.api_calls += 1
            self.tagGuids, self.tagNames = self.evernote.get_tag_names_from_evernote_guids(self.whole_note.tagGuids)
            self.addNoteFromServerToDB()
            if not self.keepEvernoteTags: self.tagNames = []
            self.result.note = self.evernote.EvernoteNote(whole_note=self.whole_note,  tags=self.tagNames)
            
            assert self.result.note.guid == self.evernote_guid
            return True

        def getNote(self, evernote_guid = None):
            if evernote_guid:
                self.result.note = None
                self.evernote_guid = evernote_guid 
                self.updateSequenceNum = self.evernote.metadata[self.evernote_guid].updateSequenceNum            
            if self.getNoteLocal(): return True 
            return self.getNoteRemote()        

    def __init__(self):
        auth_token = mw.col.conf.get(SETTING_EVERNOTE_AUTH_TOKEN, False)
        self.keepEvernoteTags = mw.col.conf.get(SETTING_KEEP_EVERNOTE_TAGS, SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE)
        self.tag_data = {}
        self.notebook_data = {}
        self.getNoteCount = 0
        
        if not auth_token:
            # First run of the Plugin we did not save the access key yet
            secrets = {'holycrepe': '36f46ea5dec83d4a', 'scriptkiddi-2682': '965f1873e4df583c'}
            client = EvernoteClient(
                consumer_key=ANKNOTES_EVERNOTE_CONSUMER_KEY,
                consumer_secret=secrets[ANKNOTES_EVERNOTE_CONSUMER_KEY],
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
        self.token = auth_token
        self.client = EvernoteClient(token=auth_token, sandbox=ANKNOTES_EVERNOTE_IS_SANDBOXED)
        self.initialize_note_store()

    def initialize_note_store(self):
        api_action_str = u'trying to initialize the Evernote Client.'
        log(" EVERNOTE_API_CALL: get_note_store", 'api')
        try:            
            self.noteStore = self.client.get_note_store()                                  
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): return 1
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): return 2
            raise                         
        return 0
    
    def create_evernote_notes(self, evernote_guids = None):  
        if not hasattr(self, 'guids') or evernote_guids: self.evernote_guids = evernote_guids
        self.check_ancillary_data_up_to_date()        
        notes = []   
        fetcher = self.EvernoteNoteFetcher(self)
        fetcher.keepEvernoteTags = self.keepEvernoteTags
        local_count = 0
        for evernote_guid in self.evernote_guids:
            self.evernote_guid = evernote_guid 
            if not fetcher.getNote(evernote_guid): 
                return fetcher.result.status, local_count, notes     
            if fetcher.result.source is 1:
                local_count += 1
            notes.append(fetcher.result.note)
        return 0, local_count, notes
    
    def check_ancillary_data_up_to_date(self):
        if not self.check_tags_up_to_date(): 
            self.update_tags_db()
        if not self.check_notebooks_up_to_date(): 
            self.update_notebook_db()    
    
    def update_ancillary_data(self):
        self.update_tags_db()
        self.update_notebook_db()                
    
    def check_notebooks_up_to_date(self):        
        notebook_guids = []        
        for evernote_guid in self.evernote_guids:
            note_metadata = self.metadata[evernote_guid]
            notebookGuid = note_metadata.notebookGuid 
            if not notebookGuid:
                log_error("   > Notebook check: Unable to find notebook guid for '%s'. Returned '%s'. Metadata: %s" % (evernote_guid, str(notebookGuid), str(note_metadata)))
            elif not notebookGuid in notebook_guids and not notebookGuid in self.notebook_data:                
                notebook  = anknotesDB().first("SELECT name, stack FROM %s WHERE guid = '%s'" % (TABLE_EVERNOTE_NOTEBOOKS, notebookGuid))
                if not notebook: 
                    log("   > Notebook check: Missing notebook guid '%s'. Will update with an API call." % notebookGuid)
                    return False
                notebook_name, notebook_stack = notebook
                self.notebook_data[notebookGuid] = {"stack": notebook_stack, "name": notebook_name}
                notebook_guids.append(notebookGuid)
        return True        
        
    def update_notebook_db(self):
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
        anknotesDB().execute("DROP TABLE %s " % TABLE_EVERNOTE_NOTEBOOKS)
        anknotesInitDb_Notebooks(True)
        log_dump(data, 'update_notebook_db table data')
        anknotesDB().executemany("INSERT INTO `%s`(`guid`,`name`,`updateSequenceNum`,`serviceUpdated`, `stack`) VALUES (?, ?, ?, ?, ?)" % TABLE_EVERNOTE_NOTEBOOKS, data)  
        log_dump(anknotesDB().all("SELECT * FROM %s WHERE 1" % TABLE_EVERNOTE_NOTEBOOKS), 'sql data')

    def check_tags_up_to_date(self):        
        tag_guids = []
        for evernote_guid in self.evernote_guids:
            if not evernote_guid in self.metadata: # hasattr('tagGuids'), note_metadata:
                log_error('Could not find note metadata for Note ''%s''' % evernote_guid)
                return False
            else:            
                note_metadata = self.metadata[evernote_guid]            
                for tag_guid in note_metadata.tagGuids:                
                    if not tag_guid in tag_guids and not tag_guid in self.tag_data: 
                        tag_name = anknotesDB().scalar("SELECT name FROM %s WHERE guid = '%s'" % (TABLE_EVERNOTE_TAGS, tag_guid))
                        if not tag_name: 
                            return False
                        self.tag_data[tag_guid] = tag_name 
                        tag_guids.append(tag_guid)   
        return True
       
    def update_tags_db(self):
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
        anknotesDB().execute("DROP TABLE %s " % TABLE_EVERNOTE_TAGS)
        anknotesInitDb_Tags(True)
        anknotesDB().executemany("INSERT OR REPLACE INTO `%s`(`guid`,`name`,`parentGuid`,`updateSequenceNum`) VALUES (?, ?, ?, ?)" % TABLE_EVERNOTE_TAGS, data)        
    
    def get_tag_names_from_evernote_guids(self, tag_guids_original):
        tagNames = []
        tagGuids = list(tag_guids_original)
        removeTagsToImport = mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True)
        for tagGuid in tag_guids_original:
            tagName = self.tag_data[tagGuid]
            if removeTagsToImport and tagName in self.evernoteTags:
                tagGuids.remove(tagGuid)
            else:
                tagNames.append(tagName)                
        tagNames = sorted(tagNames, key=lambda s: s.lower())
        return tagGuids, tagNames     
        
class Controller:
    def __init__(self):
        self.evernoteTags = mw.col.conf.get(SETTING_EVERNOTE_QUERY_TAGS, SETTING_EVERNOTE_QUERY_TAGS_DEFAULT_VALUE).split(",")
        self.deck = mw.col.conf.get(SETTING_DEFAULT_ANKI_DECK, SETTING_DEFAULT_ANKI_DECK_DEFAULT_VALUE)
        self.updateExistingNotes = mw.col.conf.get(SETTING_UPDATE_EXISTING_NOTES, UpdateExistingNotes.UpdateNotesInPlace)
        self.anki = Anki()        
        self.anki.setup_ancillary_files()        
        self.anki.add_evernote_models()        
        anknotesInitDB()
        self.evernote = Evernote()        
    
    def test_anki(self, title, evernote_guid, filename = ""):
        if not filename: filename = title 
        fields = {FIELD_TITLE: title, FIELD_CONTENT: file( os.path.join(PATH, filename.replace('.enex', '') + ".enex") , 'r').read(), FIELD_EVERNOTE_GUID: FIELD_EVERNOTE_GUID_PREFIX + evernote_guid}
        tags = ['NoTags', 'NoTagsToRemove']
        en_tags = ['NoTagsToRemove']
        return AnkiNotePrototype(fields, tags, en_tags)
   
    def process_toc(self):
        anki_note_ids = self.anki.get_anknotes_note_ids()
        self.evernote.getNoteCount = 0        
        self.anki.process_see_also_content(anki_note_ids)
        self.anki.process_toc_and_outlines()        

    def update_ancillary_data(self):
        self.evernote.update_ancillary_data()
        
    def check_note_sync_status(self, evernote_guids):
        notes_already_up_to_date = []
        for evernote_guid in evernote_guids:
            db_usn = anknotesDB().scalar("SELECT updateSequenceNum FROM %s WHERE guid = ?" % TABLE_EVERNOTE_NOTES, evernote_guid)            
            server_usn =  self.evernote.metadata[evernote_guid].updateSequenceNum
            if evernote_guid in self.anki.usns:
                current_usn = self.anki.usns[evernote_guid]                
                if current_usn == str(server_usn):
                    log_info = None # 'ANKI NOTE UP-TO-DATE'
                    notes_already_up_to_date.append(evernote_guid)
                elif str(db_usn) == str(server_usn):
                    log_info = 'DATABASE ENTRY UP-TO-DATE'
                else:
                    log_info = 'NO COPIES UP-TO-DATE'
            else:
                current_usn = 'N/A'
                log_info = 'NO ANKI USN EXISTS'
            if log_info:
                log("   > USN check for note '%s': %s: db/current/server = %s,%s,%s" % (evernote_guid, log_info, str(db_usn), str(current_usn), str(server_usn)), 'usn')        
        return notes_already_up_to_date
    
    def proceed(self, auto_paging = False): 
        log("!  > Starting Evernote Import: Page #%d: %s" % (mw.col.conf.get(SETTING_EVERNOTE_PAGINATION_CURRENT_PAGE, 1), generate_evernote_query()))       
        if not auto_paging:
            if not hasattr(self.evernote, 'noteStore'):
                log("    > Note store does not exist. Aborting.")
                return False           
            self.anki.evernoteTags = self.evernoteTags 
            self.evernote.evernoteTags = self.evernoteTags
            self.evernote.getNoteCount = 0
        
        anki_note_ids = self.anki.get_anknotes_note_ids()
        anki_evernote_guids =  self.anki.get_evernote_guids_from_anki_note_ids(anki_note_ids)  
                
        status, counts, server_evernote_guids, self.evernote.metadata = self.get_evernote_metadata() 

        if status == 1:
            log("   > Aborting operation. Over the rate limit when getting Evernote metadata")
            return False
        elif status == 2:
            log("   > Delaying operation. Blocking thread for 30s then retrying. Socket error when getting Evernote metadata")
            time.sleep(30)            
            return self.proceed(auto_paging)
        
        notes_to_add = set(server_evernote_guids) - set(anki_evernote_guids)
        notes_to_update = set(server_evernote_guids) - set(notes_to_add)
        
        notes_already_up_to_date = set(self.check_note_sync_status(notes_to_update))
        notes_to_update = notes_to_update - notes_already_up_to_date
        
        log ("          - New Notes (%d)" % len(notes_to_add) + "    > Existing Out-Of-Date Notes (%d)" % len(notes_to_update) + "    > Existing Up-To-Date Notes (%d)\n" % len(notes_already_up_to_date))
        log_dump(notes_to_add, "-    > New Notes (%d)" % len(notes_to_add), 'evernote_guids')
        log_dump(notes_to_update, "-    > Existing Out-Of-Date Notes (%d)" % len(notes_to_update), 'evernote_guids')
        log_dump(notes_already_up_to_date, "-    > Existing Up-To-Date Notes (%d)" % len(notes_already_up_to_date), 'evernote_guids')
        
        self.anki.start_editing()
        status, local_count_1, n = self.import_into_anki(notes_to_add, self.deck)
        local_count_2 = 0
        if self.updateExistingNotes is UpdateExistingNotes.IgnoreExistingNotes:
            tooltip = "%d new note(s) have been imported. Updating is disabled.\n" % n        
        else:
            n2 = len(notes_to_update)
            n3 = len(notes_already_up_to_date)
            if self.updateExistingNotes is UpdateExistingNotes.UpdateNotesInPlace:
                update_str = "in-place"
                status2, local_count_2, n2_actual = self.update_in_anki(notes_to_update)
            else:
                update_str = "(deleted and re-added)"
                self.anki.delete_anki_cards(notes_to_update)
                status2, local_count_2, n2_actual = self.import_into_anki(notes_to_update, self.deck)
            diff = n2 - n2_actual
            tooltip = "%d new note(s) have been imported and %d existing note(s) have been updated %s." % (n, n2, update_str)            
            if diff > 0:
                reason_str = ', for reasons unknown' if status2 == 0 else ', possibly because rate limits were reached' if status2 == 1 else ', possibly because network errors occurred'
                tooltip += "<BR>There is a discrepancy of %d note(s) that were not imported into Anki%s." % (n3, reason_str)
        if local_count_1 > 0:
            tooltip += "<BR> --- %d new note(s) were unexpectedly found in the local db and did not require an API call." % local_count_1
            tooltip += "<BR> --- %d new note(s) required an API call" % (n - local_count_1)
        if local_count_2 > 0:
            tooltip += "<BR> --- %d existing note(s) were unexpectedly found in the local db and did not require an API call." % local_count_2   
            tooltip += "<BR> --- %d existing note(s) required an API call" % (n2 - local_count_2)
        
        if len(notes_already_up_to_date) > 0:
                tooltip += "<BR>%d existing note(s) are already up-to-date with Evernote's servers, so they were not retrieved." % n3        
        
        show_tooltip(tooltip)
        log(("   > Import Complete: <BR>%s\n" % tooltip).replace('<BR><BR>', '<BR>').replace('<BR>', '\n   - ')) 
        self.anki.stop_editing()
        self.anki.collection().autosave()
        
        if mw.col.conf.get(SETTING_EVERNOTE_AUTO_PAGING, True):         
            restart = 0
            restart_msg = ""
            suffix = ""
            if status == 1 or status2 == 1:
                log("   > Aborting Auto Paging: Over the rate limit when getting Evernote notes")
            elif status == 2 or status2 == 2:
                log("   > Delaying Auto Paging: Blocking thread for 30s then retrying. Socket error when getting Evernote notes")
                time.sleep(30)            
                return self.proceed(True)
            elif counts['remaining'] <= 0:
                mw.col.conf[SETTING_EVERNOTE_PAGINATION_CURRENT_PAGE] = 1
                if mw.col.conf.get(EVERNOTE_PAGING_RESTART_WHEN_COMPLETE, True):                    
                    restart = EVERNOTE_PAGING_RESTART_INTERVAL
                    restart_msg = "   > Restarting Auto Paging: All %d notes have been processed and EVERNOTE_PAGING_RESTART_WHEN_COMPLETE is TRUE\n" % counts['total']
                    suffix = "   - Per EVERNOTE_PAGING_RESTART_INTERVAL, "
                else:
                    log("   > Terminating Auto Paging: All %d notes have been processed and EVERNOTE_PAGING_RESTART_WHEN_COMPLETE is FALSE" % counts['total'])
            else:
                mw.col.conf[SETTING_EVERNOTE_PAGINATION_CURRENT_PAGE] = counts['page'] + 1
                restart = EVERNOTE_PAGING_TIMER_INTERVAL
                restart_msg = "   > Initiating Auto Paging: \n   - Page %d completed. \n   - %d notes remain. \n   - %d of %d notes have been processed\n" % (counts['page'], counts['remaining'], counts['completed'], counts['total'])
                suffix = "   - Delaying Auto Paging: Per EVERNOTE_PAGING_TIMER_INTERVAL, "
            if restart_msg:                  
                if restart > 0:
                    m, s = divmod(restart, 60)
                    suffix += "will block thread for {} min before continuing\n".format("%d:%02d" %(m, s))     
                log(restart_msg + suffix)                
                if restart > 0:
                    time.sleep(restart)
                return self.proceed(True)

    def update_in_anki(self, evernote_guids):
        status, local_count, notes = self.evernote.create_evernote_notes(evernote_guids)
        number = self.anki.update_evernote_notes(notes)
        return status, local_count, number

    def import_into_anki(self, evernote_guids, deck):
        status, local_count, notes = self.evernote.create_evernote_notes(evernote_guids)
        self.anki.notebook_data = self.evernote.notebook_data
        number = self.anki.add_evernote_notes(notes, deck)
        return status, local_count, number
    
    def get_evernote_metadata(self):
        notes_metadata = {}
        evernote_guids = []        
        query = generate_evernote_query()
        evernote_filter = NoteFilter(words=query, ascending=True, order=NoteSortOrder.UPDATED)
        counts = {'page': int(mw.col.conf.get(SETTING_EVERNOTE_PAGINATION_CURRENT_PAGE, 1)), 'total': -1, 'current': -1}
        counts['offset'] = (counts['page'] - 1) * 250        
        spec = NotesMetadataResultSpec(includeTitle = False, includeUpdated = False, includeUpdateSequenceNum = True, includeTagGuids = True, includeNotebookGuid = True)     
        api_action_str = u'trying to get search for note metadata'
        log(" EVERNOTE_API_CALL: findNotesMetadata: [Offset: %d]: Query: '%s'" % (counts['offset'], query), 'api')
        try:            
            result = self.evernote.noteStore.findNotesMetadata(self.evernote.token, evernote_filter, counts['offset'], EVERNOTE_METADATA_QUERY_LIMIT, spec)                           
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): return 1, counts, evernote_guids, notes_metadata
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): return 2, counts, evernote_guids, notes_metadata
            raise                 
        counts['total'] = int(result.totalNotes)
        counts['current'] = len(result.notes)
        counts['completed'] = counts['current'] + counts['offset']
        counts['remaining'] = counts['total'] - counts['completed']

        log("          - Metadata Results: Total Notes: %d  |    Returned Notes: %d    |   Result Range: %d-%d    |   Notes Remaining: %d    |   Update Count: %d " % (counts['total'], counts['current'],  counts['offset'], counts['completed'], counts['remaining'], result.updateCount))
        for note in result.notes:
            # if note.guid == 'ae4f3510-51d7-48b3-a138-9299a1937d5b':
            evernote_guids.append(note.guid)
            notes_metadata[note.guid] = note
        return 3, counts, evernote_guids, notes_metadata

def show_tooltip(text, time_out=3000):
    aqt.utils.tooltip(text, time_out)

def main():
    controller = Controller()
    controller.proceed()

def update_ancillary_data():
    controller = Controller()
    controller.update_ancillary_data()    
    
def toc():
    controller = Controller()
    controller.process_toc()      
    
def gen_qt_hr():       
    vbox = QVBoxLayout()
    hr = QFrame()
    hr.setAutoFillBackground(True)
    hr.setFrameShape(QFrame.HLine)
    hr.setStyleSheet("QFrame { background-color: #0060bf; color: #0060bf; }")
    hr.setFixedHeight(2)
    vbox.addWidget(hr)
    vbox.addSpacing(4)
    return vbox
def setup_evernote(self):
    global icoEvernoteWeb
    global imgEvernoteWeb
    global evernote_default_tag
    global evernote_query_any   
    global evernote_query_use_tags
    global evernote_query_tags
    global evernote_query_use_notebook
    global evernote_query_notebook
    global evernote_query_use_note_title
    global evernote_query_note_title
    global evernote_query_use_search_terms
    global evernote_query_search_terms
    global evernote_query_use_last_updated
    global evernote_query_last_updated_type
    global evernote_query_last_updated_value_stacked_layout
    global evernote_query_last_updated_value_relative_spinner
    global evernote_query_last_updated_value_absolute_date
    global evernote_query_last_updated_value_absolute_datetime
    global evernote_query_last_updated_value_absolute_time
    global default_anki_deck
    global use_evernote_notebook_name_for_anki_deck_name
    global delete_evernote_query_tags
    global keep_evernote_tags
    global evernote_pagination_current_page_spinner
    global evernote_pagination_auto_paging

    widget = QWidget()
    layout = QVBoxLayout()    
    hbox = QHBoxLayout()


    ########################## QUERY ##########################
    group = QGroupBox("EVERNOTE SEARCH OPTIONS:")
    group.setStyleSheet('QGroupBox{    font-size: 10px;    font-weight: bold;  color: rgb(105, 170, 53);}')
    form = QFormLayout()

    form.addRow(gen_qt_hr())    
    
    # Evernote Query: Match Any Terms
    evernote_query_any = QCheckBox("     Match Any Terms", self)
    evernote_query_any.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_ANY, True))
    evernote_query_any.stateChanged.connect(update_evernote_query_any)
    evernote_query_any.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    

    
    button_show_generated_evernote_query = QPushButton(icoEvernoteWeb, "Show Full Query", self)
    button_show_generated_evernote_query.setAutoDefault(False)
    button_show_generated_evernote_query.connect(button_show_generated_evernote_query,
                                    SIGNAL("clicked()"),
                                    handle_show_generated_evernote_query)    
    
    
    # Add Form Row for Match Any Terms
    hbox = QHBoxLayout()
    # hbox.addWidget(QLabel("       "))
    hbox.addWidget(evernote_query_any)
    hbox.addWidget(button_show_generated_evernote_query)
    form.addRow("<b>Search Query:</b>", hbox)      
        
    # Evernote Query: Tags
    evernote_query_tags = QLineEdit()
    evernote_query_tags.setText(mw.col.conf.get(SETTING_EVERNOTE_QUERY_TAGS, SETTING_EVERNOTE_QUERY_TAGS_DEFAULT_VALUE))
    evernote_query_tags.connect(evernote_query_tags,
                                    SIGNAL("textEdited(QString)"),
                                    update_evernote_query_tags)    
                         
    # Evernote Query: Use Tags
    evernote_query_use_tags = QCheckBox(" ", self)
    evernote_query_use_tags.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_TAGS, True))
    evernote_query_use_tags.stateChanged.connect(update_evernote_query_use_tags)  
    
    # Add Form Row for Tags
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_use_tags)
    hbox.addWidget(evernote_query_tags)   
    form.addRow("Tags:", hbox)         
    

    
    # Evernote Query: Search Terms
    evernote_query_search_terms = QLineEdit()
    evernote_query_search_terms.setText(mw.col.conf.get(SETTING_EVERNOTE_QUERY_SEARCH_TERMS, ""))
    evernote_query_search_terms.connect(evernote_query_search_terms,
                                    SIGNAL("textEdited(QString)"),
                                    update_evernote_query_search_terms)                                       
                                    
    # Evernote Query: Use Search Terms
    evernote_query_use_search_terms = QCheckBox(" ", self)
    evernote_query_use_search_terms.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_SEARCH_TERMS, False))
    evernote_query_use_search_terms.stateChanged.connect(update_evernote_query_use_search_terms)
                                    
    # Add Form Row for Search Terms
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_use_search_terms) 
    hbox.addWidget(evernote_query_search_terms)  
    form.addRow("Search Terms:", hbox)          
    
    # Evernote Query: Notebook
    evernote_query_notebook = QLineEdit()
    evernote_query_notebook.setText(mw.col.conf.get(SETTING_EVERNOTE_QUERY_NOTEBOOK, SETTING_EVERNOTE_QUERY_NOTEBOOK_DEFAULT_VALUE))
    evernote_query_notebook.connect(evernote_query_notebook,
                                    SIGNAL("textEdited(QString)"),
                                    update_evernote_query_notebook)        
                         
    # Evernote Query: Use Notebook
    evernote_query_use_notebook = QCheckBox(" ", self)
    evernote_query_use_notebook.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_NOTEBOOK, False))
    evernote_query_use_notebook.stateChanged.connect(update_evernote_query_use_notebook)                                    
    
    # Add Form Row for Notebook
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_use_notebook) 
    hbox.addWidget(evernote_query_notebook)  
    form.addRow("Notebook:", hbox)  

    # Evernote Query: Note Title
    hbox = QHBoxLayout()
    evernote_query_note_title = QLineEdit()
    evernote_query_note_title.setText(mw.col.conf.get(SETTING_EVERNOTE_QUERY_NOTE_TITLE, ""))
    hbox.addWidget(evernote_query_note_title)
    evernote_query_note_title.connect(evernote_query_note_title,
                                    SIGNAL("textEdited(QString)"),
                                    update_evernote_query_note_title)        
                         
    # Evernote Query: Use Note Title
    hbox = QHBoxLayout()
    evernote_query_use_note_title = QCheckBox(" ", self)
    evernote_query_use_note_title.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_NOTE_TITLE, False))
    evernote_query_use_note_title.stateChanged.connect(update_evernote_query_use_note_title)
    hbox.addWidget(evernote_query_use_note_title)   
                                        
    # Add Form Row for Note Title
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_use_note_title) 
    hbox.addWidget(evernote_query_note_title)  
    form.addRow("Note Title:", hbox)       
                                    

    
    # Evernote Query: Last Updated Type
    evernote_query_last_updated_type = QComboBox()
    evernote_query_last_updated_type.setStyleSheet(' QComboBox { color: rgb(45, 79, 201); font-weight: bold; } ')
    evernote_query_last_updated_type.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    evernote_query_last_updated_type.addItems([u"Δ Day", u"Δ Week", u"Δ Month", u"Δ Year", "Date", "+ Time"])
    evernote_query_last_updated_type.setCurrentIndex(mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_TYPE,
                                                          EvernoteQueryLocationType.RelativeDay))
    evernote_query_last_updated_type.activated.connect(update_evernote_query_last_updated_type)

    
    # Evernote Query: Last Updated Type: Relative Date
    evernote_query_last_updated_value_relative_spinner = EvernoteQueryLocationValueQSpinBox()
    evernote_query_last_updated_value_relative_spinner.setVisible(False)
    evernote_query_last_updated_value_relative_spinner.setStyleSheet(" QSpinBox, EvernoteQueryLocationValueQSpinBox { font-weight: bold;  color: rgb(173, 0, 0); } ")
    # evernote_query_last_updated_value_relative_spinner.setSpecialValueText(QString(spinner_prefix))
    # evernote_query_last_updated_value_relative_spinner.setPrefix(spinner_prefix + ':')
    evernote_query_last_updated_value_relative_spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    # evernote_query_last_updated_value_relative_spinner.setValue(int(mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_RELATIVE, 0)))
    evernote_query_last_updated_value_relative_spinner.connect(evernote_query_last_updated_value_relative_spinner,
                                    SIGNAL("valueChanged(int)"),    
                                    update_evernote_query_last_updated_value_relative_spinner)        
    
    # Evernote Query: Last Updated Type: Absolute Date
    evernote_query_last_updated_value_absolute_date = QDateEdit()
    evernote_query_last_updated_value_absolute_date.setDisplayFormat('M/d/yy')
    evernote_query_last_updated_value_absolute_date.setCalendarPopup(True)
    evernote_query_last_updated_value_absolute_date.setVisible(False)
    evernote_query_last_updated_value_absolute_date.setStyleSheet("QDateEdit { font-weight: bold;  color: rgb(173, 0, 0); } ")
    evernote_query_last_updated_value_absolute_date.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    # evernote_query_last_updated_value_absolute_date.setDate(absolute_date)
    evernote_query_last_updated_value_absolute_date.connect(evernote_query_last_updated_value_absolute_date,
                                    SIGNAL("dateChanged(QDate)"),    
                                    update_evernote_query_last_updated_value_absolute_date)     
                                    
    # Evernote Query: Last Updated Type: Absolute DateTime
    evernote_query_last_updated_value_absolute_datetime = QDateTimeEdit()
    evernote_query_last_updated_value_absolute_datetime.setDisplayFormat('M/d/yy h:mm AP')
    evernote_query_last_updated_value_absolute_datetime.setCalendarPopup(True)
    evernote_query_last_updated_value_absolute_datetime.setVisible(False)
    evernote_query_last_updated_value_absolute_datetime.setStyleSheet("QDateTimeEdit { font-weight: bold;  color: rgb(173, 0, 0); } ")
    evernote_query_last_updated_value_absolute_datetime.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    # evernote_query_last_updated_value_absolute_datetime.setDateTime(absolute_datetime)
    evernote_query_last_updated_value_absolute_datetime.connect(evernote_query_last_updated_value_absolute_datetime,
                                    SIGNAL("dateTimeChanged(QDateTime)"),    
                                    update_evernote_query_last_updated_value_absolute_datetime)     


                                    
    # Evernote Query: Last Updated Type: Absolute Time
    evernote_query_last_updated_value_absolute_time = QTimeEdit()
    evernote_query_last_updated_value_absolute_time.setDisplayFormat('h:mm AP')
    # evernote_query_last_updated_value_absolute_time.setCalendarPopup(True)
    evernote_query_last_updated_value_absolute_time.setVisible(False)
    evernote_query_last_updated_value_absolute_time.setStyleSheet("QTimeEdit { font-weight: bold;  color: rgb(143, 0, 30); } ")
    evernote_query_last_updated_value_absolute_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    # evernote_query_last_updated_value_absolute_time.setDateTime(absolute_datetime)
    evernote_query_last_updated_value_absolute_time.connect(evernote_query_last_updated_value_absolute_time,
                                    SIGNAL("timeChanged(QTime)"),    
                                    update_evernote_query_last_updated_value_absolute_time)   
                                        
    hbox_datetime = QHBoxLayout()
    hbox_datetime.addWidget(evernote_query_last_updated_value_absolute_date)
    hbox_datetime.addWidget(evernote_query_last_updated_value_absolute_time)
    
    # Evernote Query: Last Updated Type
    evernote_query_last_updated_value_stacked_layout = QStackedLayout()
    evernote_query_last_updated_value_stacked_layout.addWidget(evernote_query_last_updated_value_relative_spinner)
    # evernote_query_last_updated_value_stacked_layout.addWidget(evernote_query_last_updated_value_absolute_date)
    evernote_query_last_updated_value_stacked_layout.addItem(hbox_datetime)
    # hbox_datetime
    # evernote_query_last_updated_value_set_visibilities()
    # if mw.col.conf.get[SETTING_EVERNOTE_QUERY_LAST_UPDATED_TYPE] < EvernoteQueryLocationType.AbsoluteDate:
        

    # # Evernote Query: Last Updated Value
    # evernote_query_last_updated_value = QLineEdit()
    # evernote_query_last_updated_value.setText(mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE, ""))
    # evernote_query_last_updated_value.connect(evernote_query_last_updated_value,
                                    # SIGNAL("editingFinished()"),
                                    # update_evernote_query_last_updated_value)        
                         
    # Evernote Query: Use Last Updated
    evernote_query_use_last_updated = QCheckBox(" ", self)
    evernote_query_use_last_updated.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    evernote_query_use_last_updated.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_LAST_UPDATED, False))
    evernote_query_use_last_updated.stateChanged.connect(update_evernote_query_use_last_updated)
    
    # Add Form Row for Last Updated
    hbox = QHBoxLayout()
    label = QLabel("Last Updated: ")
    hbox.addWidget(evernote_query_use_last_updated) 
    hbox.addWidget(evernote_query_last_updated_type)
    hbox.addWidget(evernote_query_last_updated_value_relative_spinner)  
    hbox.addWidget(evernote_query_last_updated_value_absolute_date)  
    hbox.addWidget(evernote_query_last_updated_value_absolute_time)  
    form.addRow(label, hbox)  

    form.addRow(gen_qt_hr())    
    
    # Evernote Pagination: Current Page                                                                                                   
    evernote_pagination_current_page_spinner = QSpinBox()
    evernote_pagination_current_page_spinner.setStyleSheet("QSpinBox { font-weight: bold;  color: rgb(173, 0, 0);  } ")
    evernote_pagination_current_page_spinner.setPrefix("PAGE: ")
    evernote_pagination_current_page_spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_pagination_current_page_spinner.setValue(mw.col.conf.get(SETTING_EVERNOTE_PAGINATION_CURRENT_PAGE, 1))
    evernote_pagination_current_page_spinner.connect(evernote_pagination_current_page_spinner,
                                    SIGNAL("valueChanged(int)"),    
                                    update_evernote_pagination_current_page_spinner)     
    
   # Evernote Pagination: Auto Paging 
    evernote_pagination_auto_paging = QCheckBox("     Automate", self)
    evernote_pagination_auto_paging.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    evernote_pagination_auto_paging.setFixedWidth(105)
    evernote_pagination_auto_paging.setChecked(mw.col.conf.get(SETTING_EVERNOTE_AUTO_PAGING, True))
    evernote_pagination_auto_paging.stateChanged.connect(update_evernote_pagination_auto_paging)  
                                    

    
    # Add Current Page Options to Horizontal Layout
    # hbox.addWidget(evernote_query_last_updated_value_relative_spinner_label)    
    # hbox.addWidget(evernote_query_last_updated_value_relative_spinner)
    
    # Add Form Rows for Evernote Pagination
    # hbox = QHBoxLayout()
    # hbox.insertSpacing(0, 33)
    # hbox.addWidget(evernote_query_last_updated_value_relative_spinner)    
    # form.addRow("Current Page:", hbox)  
    
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_pagination_auto_paging)
    hbox.addWidget(evernote_pagination_current_page_spinner)
    
    form.addRow("<b>Pagination:</b>", hbox) 
    # form.addRow("", evernote_pagination_auto_paging) 
    




    
    # Add Query Form to Group Box  
    group.setLayout(form)
    
    # Add Query Group Box to Main Layout 
    layout.addWidget(group)        
    
    

    ########################## DECK ##########################
    label = QLabel("<span style='background-color: #bf0060;'><B><U>ANKI NOTE OPTIONS</U>:</B></span>")
    group = QGroupBox("ANKI NOTE OPTIONS:")    
    group.setStyleSheet('QGroupBox{    font-size: 10px;    font-weight: bold;  color: rgb(105, 170, 53);}')
    form = QFormLayout()
    form.addRow(gen_qt_hr())
    # Default Anki Deck
    default_anki_deck = QLineEdit()
    default_anki_deck.setText(mw.col.conf.get(SETTING_DEFAULT_ANKI_DECK, SETTING_DEFAULT_ANKI_DECK_DEFAULT_VALUE))
    default_anki_deck.connect(default_anki_deck, SIGNAL("textEdited(QString)"), update_default_anki_deck)
    
    # Add Form Row for Default Anki Deck 
    hbox = QHBoxLayout()
    hbox.insertSpacing(0, 33)
    hbox.addWidget(default_anki_deck)   
    label_deck = QLabel("<b>Anki Deck:</b>")
    label_deck.setMinimumWidth(100)
    form.addRow(label_deck, hbox)          
    
    
    # Use Evernote Notebook Name for Anki Deck Name
    use_evernote_notebook_name_for_anki_deck_name = QCheckBox("      Append Evernote Notebook", self)
    use_evernote_notebook_name_for_anki_deck_name.setChecked(mw.col.conf.get(SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME, True))
    use_evernote_notebook_name_for_anki_deck_name.stateChanged.connect(update_use_evernote_notebook_name_for_anki_deck_name)

    update_anki_deck_visibilities()
    
     # Add Form Row for Evernote Notebook Integration
    label_deck = QLabel("Evernote Notebook:")
    label_deck.setMinimumWidth(100)
    form.addRow("", use_evernote_notebook_name_for_anki_deck_name)              
    
      
    # # Add Deck Form to Group Box  
    # group.setLayout(form)
    
    # # Add Deck Group Box to Main Layout 
    # layout.addWidget(group)      

    # vertical_spacer = QSpacerItem(5, 0, QSizePolicy.Fixed)
    # layout.addItem(vertical_spacer)
    form.addRow(gen_qt_hr())
    
    # ########################## TAGS ##########################
    # group = QGroupBox("Anki Note: Tags")   
    # form = QFormLayout()    
    
    # Keep Evernote Tags
    keep_evernote_tags = QCheckBox("     Save To Anki Note", self)
    keep_evernote_tags.setChecked(mw.col.conf.get(SETTING_KEEP_EVERNOTE_TAGS, SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE))
    keep_evernote_tags.stateChanged.connect(update_keep_evernote_tags)

    # Delete Tags To Import 
    delete_evernote_query_tags = QCheckBox("     Ignore Search Tags", self)
    delete_evernote_query_tags.setChecked(mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True))
    delete_evernote_query_tags.stateChanged.connect(update_delete_evernote_query_tags) 
    
    # Add Form Row for Evernote Tag Options
    label = QLabel("<b>Evernote Tags:</b>")
    label.setMinimumWidth(100)
    form.addRow(label, keep_evernote_tags) 
    form.addRow(" ", delete_evernote_query_tags) 
    
    form.addRow(gen_qt_hr())
    
    # # Add Tag Options Form to Group Box  
    # group.setLayout(form)    
    # # Add Tag Options Group Box to Main Layout 
    # layout.addWidget(group)      
    
    # ########################## PAGINATION ##########################
    # group = QGroupBox("Evernote Search: Pagination")   
    # form = QFormLayout()       
    
        
    
    # # Add Grid Row for Pagination Options
    # # layout_grid_misc.addWidget(evernote_query_last_updated_value_relative_spinner_group_label, layout_grid_misc.rowCount(), 0)
    # # layout_grid_misc.addWidget(evernote_pagination_auto_paging, layout_grid_misc.rowCount(), 0)
    # # layout_grid_misc.addItem(hbox, layout_grid_misc.rowCount() - 1, 1)   


    # # Add Pagination Options Form to Group Box  
    # group.setLayout(form)    
    # # Add Pagination Options Group Box to Main Layout 
    # layout.addWidget(group)      
    
    # ########################## NOTE UPDATING ##########################
    # group = QGroupBox("Anki: Note Updating")   
    # form = QFormLayout()           
    
    # Note Update Method
    update_existing_notes = QComboBox()
    update_existing_notes.setStyleSheet(' QComboBox { color: #3b679e; font-weight: bold; } QComboBoxItem { color: #A40F2D; font-weight: bold; } ')
    update_existing_notes.addItems(["Ignore Existing Notes", "Update In-Place",
                                    "Delete and Re-Add"])
    update_existing_notes.setCurrentIndex(mw.col.conf.get(SETTING_UPDATE_EXISTING_NOTES,
                                                          UpdateExistingNotes.UpdateNotesInPlace))
    update_existing_notes.activated.connect(update_update_existing_notes)
    
    # Add Form Row for Note Update Method
    hbox = QHBoxLayout()
    hbox.insertSpacing(0, 33)
    hbox.addWidget(update_existing_notes)    
    form.addRow("<b>Note Updating:</b>", hbox)     
    # # Add Grid Row for Update Existing Note Options 
    # layout_grid_misc.addWidget(QLabel("Note Update Method:"), layout_grid_misc.rowCount(), 0)
    # layout_grid_misc.addWidget(update_existing_notes, layout_grid_misc.rowCount() - 1, 1)
    
    # Add Note Update Method Form to Group Box  
    group.setLayout(form)
    
    # Add Note Update Method Group Box to Main Layout 
    layout.addWidget(group)  
    
    evernote_query_text_changed()
    update_evernote_query_visibilities()
    

    # Vertical Spacer
    vertical_spacer = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
    layout.addItem(vertical_spacer)

    # Parent Widget
    widget.setLayout(layout)

    # New Tab
    self.form.tabWidget.addTab(widget, "Anknotes")
    
def update_anki_deck_visibilities():
    if not default_anki_deck.text():
        use_evernote_notebook_name_for_anki_deck_name.setChecked(True)
        use_evernote_notebook_name_for_anki_deck_name.setEnabled(False)
    else:
        use_evernote_notebook_name_for_anki_deck_name.setEnabled(True)
        use_evernote_notebook_name_for_anki_deck_name.setChecked(mw.col.conf.get(SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME, True))
    
def update_default_anki_deck(text):
    mw.col.conf[SETTING_DEFAULT_ANKI_DECK] = text
    update_anki_deck_visibilities()

def update_use_evernote_notebook_name_for_anki_deck_name():
    if default_anki_deck.text():
        mw.col.conf[SETTING_USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME] = use_evernote_notebook_name_for_anki_deck_name.isChecked()    

def update_evernote_query_tags(text):
    mw.col.conf[SETTING_EVERNOTE_QUERY_TAGS] = text
    if text: evernote_query_use_tags.setChecked(True)
    evernote_query_text_changed()

def update_evernote_query_use_tags():
    mw.col.conf[SETTING_EVERNOTE_QUERY_USE_TAGS] = evernote_query_use_tags.isChecked()          
    update_evernote_query_visibilities()

def update_evernote_query_notebook(text):
    mw.col.conf[SETTING_EVERNOTE_QUERY_NOTEBOOK] = text
    if text: evernote_query_use_notebook.setChecked(True)
    evernote_query_text_changed()

def update_evernote_query_use_notebook():
    mw.col.conf[SETTING_EVERNOTE_QUERY_USE_NOTEBOOK] = evernote_query_use_notebook.isChecked()     
    update_evernote_query_visibilities() 

def update_evernote_query_note_title(text):
    mw.col.conf[SETTING_EVERNOTE_QUERY_NOTE_TITLE] = text
    if text: evernote_query_use_note_title.setChecked(True)
    evernote_query_text_changed()

def update_evernote_query_use_note_title():
    mw.col.conf[SETTING_EVERNOTE_QUERY_USE_NOTE_TITLE] = evernote_query_use_note_title.isChecked()   
    update_evernote_query_visibilities()      
    
def update_evernote_query_use_last_updated():
    update_evernote_query_visibilities()
    mw.col.conf[SETTING_EVERNOTE_QUERY_USE_LAST_UPDATED] = evernote_query_use_last_updated.isChecked()      
    
def update_evernote_query_search_terms(text):
    mw.col.conf[SETTING_EVERNOTE_QUERY_SEARCH_TERMS] = text
    if text: evernote_query_use_search_terms.setChecked(True)
    evernote_query_text_changed()
    update_evernote_query_visibilities()
    
def update_evernote_query_use_search_terms():
    update_evernote_query_visibilities()
    mw.col.conf[SETTING_EVERNOTE_QUERY_USE_SEARCH_TERMS] = evernote_query_use_search_terms.isChecked()   

def update_evernote_query_any():
    update_evernote_query_visibilities()
    mw.col.conf[SETTING_EVERNOTE_QUERY_ANY] = evernote_query_any.isChecked()        
    
def update_keep_evernote_tags():
    mw.col.conf[SETTING_KEEP_EVERNOTE_TAGS] = keep_evernote_tags.isChecked()
    evernote_query_text_changed()
    
def update_delete_evernote_query_tags():
    mw.col.conf[SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT] = delete_evernote_query_tags.isChecked()    

def update_evernote_pagination_auto_paging():
    mw.col.conf[SETTING_EVERNOTE_AUTO_PAGING] = evernote_pagination_auto_paging.isChecked()

def update_evernote_pagination_current_page_spinner(value):
    if value < 1: 
        value = 1
        evernote_pagination_current_page_spinner.setValue(1)
    mw.col.conf[SETTING_EVERNOTE_PAGINATION_CURRENT_PAGE] = value  

def update_update_existing_notes(index):
    mw.col.conf[SETTING_UPDATE_EXISTING_NOTES] = index

def evernote_query_text_changed():    
    tags = evernote_query_tags.text() #and evernote_query_use_tags.isChecked()
    search_terms = evernote_query_search_terms.text() #and evernote_query_use_search_terms.isChecked()
    note_title = evernote_query_note_title.text() #and evernote_query_use_note_title.isChecked()
    notebook = evernote_query_notebook.text() #and evernote_query_use_notebook.isChecked()
    tags_active = tags and use_tags.isChecked()
    search_terms_active = search_terms and evernote_query_use_search_terms.isChecked()
    note_title_active = note_title and evernote_query_use_note_title.isChecked()
    notebook_active = notebook and evernote_query_use_notebook.isChecked()
    all_inactive = not (search_terms_active or note_title_active or notebook_active or evernote_query_use_last_updated.isChecked())
    
    if not search_terms:
        evernote_query_use_search_terms.setEnabled(False)
        evernote_query_use_search_terms.setChecked(False)
    else:   
        evernote_query_use_search_terms.setEnabled(True)
        evernote_query_use_search_terms.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_SEARCH_TERMS, True))   
    
    if not note_title:
        evernote_query_use_note_title.setEnabled(False)
        evernote_query_use_note_title.setChecked(False)
    else:   
        evernote_query_use_note_title.setEnabled(True)
        evernote_query_use_note_title.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_NOTE_TITLE, True))    
    
    if not notebook:
        evernote_query_use_notebook.setEnabled(False)
        evernote_query_use_notebook.setChecked(False)
    else:   
        evernote_query_use_notebook.setEnabled(True)
        evernote_query_use_notebook.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_NOTEBOOK, True))    
            
    if not tags and not all_inactive:
        evernote_query_use_tags.setEnabled(False)
        evernote_query_use_tags.setChecked(False)
    else:   
        evernote_query_use_tags.setEnabled(True)
        evernote_query_use_tags.setChecked(mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_TAGS, True))        
        if all_inactive and not tags:
            evernote_query_tags.setText(SETTING_EVERNOTE_QUERY_TAGS_DEFAULT_VALUE)
        
def update_evernote_query_visibilities():
    is_any =  evernote_query_any.isChecked()
    is_tags = evernote_query_use_tags.isChecked()
    is_terms = evernote_query_use_search_terms.isChecked()
    is_title = evernote_query_use_note_title.isChecked()
    is_notebook = evernote_query_use_notebook.isChecked()
    is_updated = evernote_query_use_last_updated.isChecked()
    
    is_disabled_any = not evernote_query_any.isEnabled()
    is_disabled_tags = not evernote_query_use_tags.isEnabled()
    is_disabled_terms = not evernote_query_use_search_terms.isEnabled()
    is_disabled_title = not evernote_query_use_note_title.isEnabled()
    is_disabled_notebook = not evernote_query_use_notebook.isEnabled()
    is_disabled_updated = not evernote_query_use_last_updated.isEnabled()

    override = (not is_tags and not is_terms and not is_title and not is_notebook and not is_updated)
    if override:
        is_tags = True 
        evernote_query_use_tags.setChecked(True)    
    evernote_query_tags.setEnabled(is_tags or is_disabled_tags)
    evernote_query_search_terms.setEnabled(is_terms or is_disabled_terms)
    evernote_query_note_title.setEnabled((is_title or is_disabled_title) and not is_any)
    evernote_query_notebook.setEnabled(is_notebook or is_disabled_notebook)
    evernote_query_last_updated_value_set_visibilities()
    
    # if override:
        # is_tags = True 
        # evernote_query_use_tags.setChecked(True)    
    
    # if not recheck:
        # update_evernote_query_visibilities(True)
    

def update_evernote_query_last_updated_type(index):
    mw.col.conf[SETTING_EVERNOTE_QUERY_LAST_UPDATED_TYPE] = index  
    evernote_query_last_updated_value_set_visibilities()    
    
def evernote_query_last_updated_value_get_current_value():
    index = mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_TYPE, 0)
    if index < EvernoteQueryLocationType.AbsoluteDate:
        return evernote_query_last_updated_value_relative_spinner.text()
    absolute_date_str = mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE, "{:%Y %m %d}".format(datetime.now() - timedelta(days=7))).replace(' ', '')
    if index == EvernoteQueryLocationType.AbsoluteDate:
        return absolute_date_str
    absolute_time_str = mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME, "{:HH mm ss}".format(datetime.now())).replace(' ', '')
    return absolute_date_str + "'T'" + absolute_time_str

def evernote_query_last_updated_value_set_visibilities(set_enabled_only = False):
    index = mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_TYPE, 0)
    evernote_query_use_last_updated.setEnabled(not evernote_query_any.isChecked())
    if not evernote_query_use_last_updated.isChecked() or evernote_query_any.isChecked():
        evernote_query_last_updated_type.setEnabled(False)
        evernote_query_last_updated_value_absolute_date.setEnabled(False)
        evernote_query_last_updated_value_absolute_time.setEnabled(False)
        evernote_query_last_updated_value_relative_spinner.setEnabled(False)
        return 
    
    evernote_query_last_updated_type.setEnabled(True)
    evernote_query_last_updated_value_absolute_date.setEnabled(True)
    evernote_query_last_updated_value_absolute_time.setEnabled(True)
    evernote_query_last_updated_value_relative_spinner.setEnabled(True)
    
    absolute_date = QDate().fromString(mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE, "{:%Y %m %d}".format(datetime.now() - timedelta(days=7))), 'yyyy MM dd')
    if index < EvernoteQueryLocationType.AbsoluteDate:
        evernote_query_last_updated_value_absolute_date.setVisible(False)
        evernote_query_last_updated_value_absolute_time.setVisible(False)
        evernote_query_last_updated_value_relative_spinner.setVisible(True)
        spinner_prefix = ['day', 'week', 'month', 'year'][index]    
        evernote_query_last_updated_value_relative_spinner.setPrefix(spinner_prefix)
        evernote_query_last_updated_value_relative_spinner.setValue(int(mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_RELATIVE, 0)))
        evernote_query_last_updated_value_stacked_layout.setCurrentIndex(0)
    else:        
        evernote_query_last_updated_value_relative_spinner.setVisible(False)
        evernote_query_last_updated_value_absolute_date.setVisible(True)
        evernote_query_last_updated_value_absolute_date.setDate(absolute_date)        
        evernote_query_last_updated_value_stacked_layout.setCurrentIndex(1)
        if index == EvernoteQueryLocationType.AbsoluteDate:
            evernote_query_last_updated_value_absolute_time.setVisible(False)
            evernote_query_last_updated_value_absolute_datetime.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            absolute_time = QTime().fromString(mw.col.conf.get(SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME, "{:HH mm ss}".format(datetime.now())), 'HH mm ss')         
            # absolute_datetime = absolute_date + absolute_time 
            evernote_query_last_updated_value_absolute_time.setTime(absolute_time)      
            evernote_query_last_updated_value_absolute_time.setVisible(True)
            evernote_query_last_updated_value_absolute_datetime.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # evernote_query_last_updated_value_stacked_layout.setCurrentIndex(2)
        
def update_evernote_query_last_updated_value_relative_spinner(value):
    if value < 0: 
        value = 0
        evernote_query_last_updated_value_relative_spinner.setValue(0)
    mw.col.conf[SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_RELATIVE] = value  
            
def update_evernote_query_last_updated_value_absolute_date(date):    
    mw.col.conf[SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE] = date.toString('yyyy MM dd')
    
def update_evernote_query_last_updated_value_absolute_datetime(datetime):    
    mw.col.conf[SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE] = datetime.toString('yyyy MM dd')    
    mw.col.conf[SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME] = datetime.toString('HH mm ss')     
    
def update_evernote_query_last_updated_value_absolute_time(time):    
    mw.col.conf[SETTING_EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME] = time.toString('HH mm ss')      

def generate_evernote_query():
    query = ""
    tags = mw.col.conf.get(SETTING_EVERNOTE_QUERY_TAGS, SETTING_EVERNOTE_QUERY_TAGS_DEFAULT_VALUE).split(",")
    if mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_NOTEBOOK, False):        
        query += 'notebook:"%s" ' % mw.col.conf.get(SETTING_EVERNOTE_QUERY_NOTEBOOK, SETTING_EVERNOTE_QUERY_NOTEBOOK_DEFAULT_VALUE).strip()
    if mw.col.conf.get(SETTING_EVERNOTE_QUERY_ANY, True):
        query += "any: " 
    if mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_NOTE_TITLE, False):        
        query_note_title = mw.col.conf.get(SETTING_EVERNOTE_QUERY_NOTE_TITLE, "")
        if not query_note_title[:1] + query_note_title[-1:] == '""':
            query_note_title = '"%s"' % query_note_title
        query += 'intitle:%s ' % query_note_title
    if mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_TAGS, True):
        for tag in tags:
            query += "tag:%s " % tag.strip()
    if mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_LAST_UPDATED, False):
        query += " updated:%s " % evernote_query_last_updated_value_get_current_value()              
    if mw.col.conf.get(SETTING_EVERNOTE_QUERY_USE_SEARCH_TERMS, False):        
        query += mw.col.conf.get(SETTING_EVERNOTE_QUERY_SEARCH_TERMS, "")
    return query
    
def handle_show_generated_evernote_query():
    showInfo("The Evernote search query for your current options is below. You can press copy the text to your clipboard by pressing the copy keyboard shortcut (CTRL+C in Windows) while this message box has focus.\n\nQuery: %s" % generate_evernote_query(), "Evernote Search Query")
    
action = aqt.qt.QAction("&Import from Evernote", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), main)
aqt.mw.form.menuTools.addAction(action)

action = aqt.qt.QAction("Process Evernote &TOC [Power Users Only!]", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), toc)
aqt.mw.form.menuTools.addAction(action)

action = aqt.qt.QAction("Update Evernote Ancillary Data", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), update_ancillary_data)
aqt.mw.form.menuTools.addAction(action)

Preferences.setupOptions = wrap(Preferences.setupOptions, setup_evernote)

icoEvernoteWeb = QIcon(os.path.join(PATH, ANKNOTES_ICON_EVERNOTE_WEB))
icoEvernoteArtcore = QIcon(os.path.join(PATH, ANKNOTES_ICON_EVERNOTE_ARTCORE))
imgEvernoteWeb = QPixmap(os.path.join(PATH, ANKNOTES_IMAGE_EVERNOTE_WEB), "PNG")
imgEvernoteWebMsgBox = imgEvernoteWeb.scaledToWidth(64)