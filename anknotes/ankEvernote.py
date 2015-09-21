# -*- coding: utf-8 -*-
### Python Imports
import socket

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
from anknotes.shared import *
from anknotes.error import *

### Anknotes Class Imports
from anknotes.EvernoteNoteFetcher import EvernoteNoteFetcher

### Evernote Imports 
from evernote.edam.type.ttypes import Note as EvernoteNote
from evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException, EDAMNotFoundException
from evernote.api.client import EvernoteClient

from aqt.utils import openLink

### Anki Imports
# import anki
# import aqt
# from anki.hooks import wrap, addHook
# from aqt.preferences import Preferences
# from aqt.utils import getText, openLink, getOnlyText
# from aqt.qt import QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, SIGNAL, QCheckBox, \
# QComboBox, QSpacerItem, QSizePolicy, QWidget, QSpinBox, QFormLayout, QGridLayout, QFrame, QPalette, \
# QRect, QStackedLayout, QDateEdit, QDateTimeEdit, QTimeEdit, QDate, QDateTime, QTime, QPushButton, QIcon, QMessageBox, QPixmap, QMenu, QAction
# from aqt import mw

class Evernote(object):
    metadata = {}
    """:type : dict[str, evernote.edam.type.ttypes.Note]"""
    notebook_data = {}
    """:type : dict[str, anknotes.structs.EvernoteNotebook]"""
    tag_data = {}
    """:type : dict[str, anknotes.structs.EvernoteTag]"""

    def __init__(self):
        auth_token = mw.col.conf.get(SETTINGS.EVERNOTE_AUTH_TOKEN, False)
        self.keepEvernoteTags = mw.col.conf.get(SETTINGS.KEEP_EVERNOTE_TAGS, SETTINGS.KEEP_EVERNOTE_TAGS_DEFAULT_VALUE)
        self.tag_data = {}
        self.notebook_data = {}
        self.noteStore = None
        self.getNoteCount = 0
        if not auth_token:
            # First run of the Plugin we did not save the access key yet
            secrets = {'holycrepe': '36f46ea5dec83d4a', 'scriptkiddi-2682': '965f1873e4df583c'}
            client = EvernoteClient(
                consumer_key=ANKNOTES.EVERNOTE_CONSUMER_KEY,
                consumer_secret=secrets[ANKNOTES.EVERNOTE_CONSUMER_KEY],
                sandbox=ANKNOTES.EVERNOTE_IS_SANDBOXED
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
            mw.col.conf[SETTINGS.EVERNOTE_AUTH_TOKEN] = auth_token
        self.token = auth_token
        self.client = EvernoteClient(token=auth_token, sandbox=ANKNOTES.EVERNOTE_IS_SANDBOXED)

    def initialize_note_store(self):
        if self.noteStore:
            return 0
        api_action_str = u'trying to initialize the Evernote Client.'
        log_api("get_note_store")
        try:
            self.noteStore = self.client.get_note_store()
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                return 1
            raise
        except socket.error, v:
            if HandleSocketError(v, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                return 2
            raise
        return 0

    def updateNote(self, guid, noteTitle, noteBody, tagNames=list(), parentNotebook=None, resources=[]):
        """
        Update a Note instance with title and body
        Send Note object to user's account
        :rtype : (EvernoteAPIStatus, evernote.edam.type.ttypes.Note)
        :returns Status and Note
        """
        return self.makeNote(noteTitle, noteBody, tagNames=tagNames, parentNotebook=parentNotebook, resources=resources,
                             guid=guid)

    @staticmethod
    def makeNoteBody(noteBody, resources=[], encode=True):
        ## Build body of note

        nBody = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        nBody += "<!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\">"
        nBody += "<en-note>%s" % noteBody
        # if resources:
        #     ### Add Resource objects to note body
        #     nBody += "<br />" * 2
        #     ourNote.resources = resources
        #     for resource in resources:
        #         hexhash = binascii.hexlify(resource.data.bodyHash)
        #         nBody += "Attachment with hash %s: <br /><en-media type=\"%s\" hash=\"%s\" /><br />" % \
        #             (hexhash, resource.mime, hexhash)
        nBody += "</en-note>"
        if encode:
            nBody = nBody.encode('utf-8')
        return nBody

    def makeNote(self, noteTitle, noteBody, tagNames=list(), parentNotebook=None, resources=[], guid=None):
        """
        Create or Update a Note instance with title and body
        Send Note object to user's account
        :type noteTitle: str
        :rtype : (EvernoteAPIStatus, EvernoteNote)
        :returns Status and Note
        """
        callType = "create"

        ourNote = EvernoteNote()
        ourNote.title = noteTitle.encode('utf-8')
        if guid:
            callType = "update"
            ourNote.guid = guid

            ## Build body of note  
        nBody = self.makeNoteBody(noteBody, resources)
        ourNote.content = nBody

        if '' in tagNames: tagNames.remove('')
        if len(tagNames) > 0:
            if ANKNOTES.EVERNOTE_IS_SANDBOXED:
                tagNames.append("#Sandbox")
            ourNote.tagNames = tagNames

        ## parentNotebook is optional; if omitted, default notebook is used
        if parentNotebook and hasattr(parentNotebook, 'guid'):
            ourNote.notebookGuid = parentNotebook.guid

        ## Attempt to create note in Evernote account

        api_action_str = u'trying to %s a note' % callType
        log_api(callType + "Note", "'%s'" % noteTitle)
        try:
            note = getattr(self.noteStore, callType + 'Note')(self.token, ourNote)
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                return EvernoteAPIStatus.RateLimitError, None
        except socket.error, v:
            if HandleSocketError(v, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                return EvernoteAPIStatus.SocketError, None
        except EDAMUserException, edue:
            ## Something was wrong with the note data
            ## See EDAMErrorCode enumeration for error code explanation
            ## http://dev.evernote.com/documentation/reference/Errors.html#Enum_EDAMErrorCode
            print "EDAMUserException:", edue
            log_error("-------------------------------------------------")
            log_error("EDAMUserException:  " + str(edue))
            log_error(str(ourNote.tagNames))
            log_error(str(ourNote.content))
            log_error("-------------------------------------------------\r\n")
            if DEBUG_RAISE_API_ERRORS: raise
            return EvernoteAPIStatus.UserError, None
        except EDAMNotFoundException, ednfe:
            print "EDAMNotFoundException:", ednfe
            log_error("-------------------------------------------------")
            log_error("EDAMNotFoundException:  " + str(ednfe))
            if callType is "update":
                log_error(str(ourNote.guid))
            if ourNote.notebookGuid:
                log_error(str(ourNote.notebookGuid))
            log_error("-------------------------------------------------\r\n")
            if DEBUG_RAISE_API_ERRORS: raise
            return EvernoteAPIStatus.NotFoundError, None
        except Exception, e:
            print "Unknown Exception:", e
            log_error("-------------------------------------------------")
            log_error("Unknown Exception:  " + str(e))
            log_error(str(ourNote.tagNames))
            log_error(str(ourNote.content))
            log_error("-------------------------------------------------\r\n")
            # return EvernoteAPIStatus.UnhandledError, None
            raise
        # noinspection PyUnboundLocalVariable
        note.content = nBody
        return EvernoteAPIStatus.Success, note

    def create_evernote_notes(self, evernote_guids=None, use_local_db_only=False):
        """
        Create EvernoteNote objects from Evernote GUIDs using EvernoteNoteFetcher.getNote().
        Will prematurely return if fetcher.getNote fails

        :rtype : EvernoteNoteFetcherResults
        :param evernote_guids:
        :param use_local_db_only: Do not initiate API calls
        :return: EvernoteNoteFetcherResults
        """
        if not hasattr(self, 'guids') or evernote_guids: self.evernote_guids = evernote_guids
        if not use_local_db_only:
            self.check_ancillary_data_up_to_date()
        notes = []
        fetcher = EvernoteNoteFetcher(self, use_local_db_only=use_local_db_only)
        if len(evernote_guids) == 0:
            fetcher.results.Status = EvernoteAPIStatus.EmptyRequest
            return fetcher.results 
        fetcher.keepEvernoteTags = self.keepEvernoteTags
        for evernote_guid in self.evernote_guids:
            self.evernote_guid = evernote_guid
            if not fetcher.getNote(evernote_guid):
                return fetcher.results
        return fetcher.results 

    def check_ancillary_data_up_to_date(self):
        if not self.check_tags_up_to_date():
            self.update_tags_db()
        if not self.check_notebooks_up_to_date():
            self.update_notebook_db()

    def update_ancillary_data(self):
        self.update_tags_db()
        self.update_notebook_db()

    def check_notebooks_up_to_date(self):
        for evernote_guid in self.evernote_guids:
            note_metadata = self.metadata[evernote_guid]
            notebookGuid = note_metadata.notebookGuid
            if not notebookGuid:
                log_error("   > Notebook check: Unable to find notebook guid for '%s'. Returned '%s'. Metadata: %s" % (
                    evernote_guid, str(notebookGuid), str(note_metadata)))
            elif notebookGuid not in self.notebook_data:
                nb = EvernoteNotebook(fetch_guid=notebookGuid)
                if not nb.success:
                    log("   > Notebook check: Missing notebook guid '%s'. Will update with an API call." % notebookGuid)
                    return False
                self.notebook_data[notebookGuid] = nb
        return True

    def update_notebook_db(self):
        api_action_str = u'trying to update Evernote notebooks.'
        log_api("listNotebooks")
        try:
            notebooks = self.noteStore.listNotebooks(self.token)
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                return None
            raise
        except socket.error, v:
            if HandleSocketError(v, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                return None
            raise
        data = []
        for notebook in notebooks:
            self.notebook_data[notebook.guid] = {"stack": notebook.stack, "name": notebook.name}
            data.append(
                [notebook.guid, notebook.name, notebook.updateSequenceNum, notebook.serviceUpdated, notebook.stack])
        ankDB().execute("DROP TABLE %s " % TABLES.EVERNOTE.NOTEBOOKS)
        ankDB().InitNotebooks(True)
        log_dump(data, 'update_notebook_db table data')
        ankDB().executemany(
            "INSERT INTO `%s`(`guid`,`name`,`updateSequenceNum`,`serviceUpdated`, `stack`) VALUES (?, ?, ?, ?, ?)" % TABLES.EVERNOTE.NOTEBOOKS,
            data)
        log_dump(ankDB().all("SELECT * FROM %s WHERE 1" % TABLES.EVERNOTE.NOTEBOOKS), 'sql data')

    def check_tags_up_to_date(self):
        for evernote_guid in self.evernote_guids:
            if evernote_guid not in self.metadata:
                log_error('Could not find note metadata for Note ''%s''' % evernote_guid)
                return False
            else:
                note_metadata = self.metadata[evernote_guid]
                for tag_guid in note_metadata.tagGuids:
                    if tag_guid not in self.tag_data:
                        tag = EvernoteTag(fetch_guid=tag_guid)
                        if not tag.success:
                            return False
                        self.tag_data[tag_guid] = tag
        return True

    def update_tags_db(self):
        api_action_str = u'trying to update Evernote tags.'
        log_api("listTags")
        try:
            tags = self.noteStore.listTags(self.token)
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                return None
            raise
        except socket.error, v:
            if HandleSocketError(v, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                return None
            raise
        data = []
        for tag in tags:
            self.tag_data[tag.guid] = tag.name
            data.append([tag.guid, tag.name, tag.parentGuid, tag.updateSequenceNum])
        ankDB().execute("DROP TABLE %s " % TABLES.EVERNOTE.TAGS)
        ankDB().InitTags(True)
        ankDB().executemany(
            "INSERT OR REPLACE INTO `%s`(`guid`,`name`,`parentGuid`,`updateSequenceNum`) VALUES (?, ?, ?, ?)" % TABLES.EVERNOTE.TAGS,
            data)

    def get_tag_names_from_evernote_guids(self, tag_guids_original):
        tagGuids = []
        tagNames = []
        tagNamesToImport = get_tag_names_to_import({x: self.tag_data[x] for x in tag_guids_original})
        for k, v in tagNamesToImport.items():
            tagGuids.append(k)
            tagNames.append(v)
        tagNames = sorted(tagNames, key=lambda s: s.lower())
        return tagGuids, tagNames


DEBUG_RAISE_API_ERRORS = False
