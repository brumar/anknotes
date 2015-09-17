# -*- coding: utf-8 -*-
### Python Imports
import socket
import stopwatch
from StringIO import StringIO

try:
    from lxml import etree

    eTreeImported = True
except:
    eTreeImported = False
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
from anknotes.shared import *
from anknotes.error import *

if not eTreeImported:
    ### Anknotes Class Imports
    from anknotes.EvernoteNoteFetcher import EvernoteNoteFetcher
    from anknotes.EvernoteNotePrototype import EvernoteNotePrototype

    ### Evernote Imports
    from anknotes.evernote.edam.type.ttypes import Note as EvernoteNote
    from anknotes.evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException, EDAMNotFoundException
    from anknotes.evernote.api.client import EvernoteClient

    try:
        from aqt.utils import openLink, getText, showInfo
    except: pass


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
    DTD = None
    hasValidator = None

    def __init__(self):
        global eTreeImported, dbLocal
        self.tag_data = {}
        self.notebook_data = {}
        self.noteStore = None
        self.getNoteCount = 0
        self.hasValidator = eTreeImported
        if ankDBIsLocal():
            return
        self.keepEvernoteTags = mw.col.conf.get(SETTINGS.KEEP_EVERNOTE_TAGS, SETTINGS.KEEP_EVERNOTE_TAGS_DEFAULT_VALUE)
        auth_token = mw.col.conf.get(SETTINGS.EVERNOTE_AUTH_TOKEN, False)
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

    def validateNoteBody(self, noteBody, title="Note Body"):
        # timerFull = stopwatch.Timer()
        # timerInterval = stopwatch.Timer(False)
        if not self.DTD:
            timerInterval = stopwatch.Timer()
            log("Loading ENML DTD", "lxml", timestamp=False, do_print=True)
            self.DTD = etree.DTD(ANKNOTES.ENML_DTD)
            log("DTD Loaded in %s\n" % str(timerInterval), "lxml", timestamp=False, do_print=True)
            timerInterval.stop()
            del timerInterval

        # timerInterval.reset()
        # log("Loading XML for %s" % title, "lxml", timestamp=False, do_print=False)
        try:
            tree = etree.parse(StringIO(noteBody))
        except Exception as e:
            # timer_header = ' at %s. The whole process took %s' % (str(timerInterval), str(timerFull))
            log_str = "XML Loading of %s failed.\n    - Error Details: %s" % (title, str(e))
            log(log_str, "lxml", timestamp=False, do_print=True)
            log_error(log_str, False)
            return False, log_str
        # log("XML Loaded in %s for %s" % (str(timerInterval), title), "lxml", timestamp=False, do_print=False)
        # timerInterval.stop()
        # timerInterval.reset()
        # log("Validating %s with ENML DTD" % title, "lxml", timestamp=False, do_print=False)
        try:
            success = self.DTD.validate(tree)
        except Exception as e:
            log_str = "DTD Validation of %s failed.\n    - Error Details: %s" % (title, str(e))
            log(log_str, "lxml", timestamp=False, do_print=True)
            log_error(log_str, False)
            return False, log_str
        log("Validation %-9s for %s" % ("Succeeded" if success else "Failed", title), "lxml", timestamp=False,
            do_print=True)
        errors = self.DTD.error_log.filter_from_errors()
        if not success:
            log_str = "DTD Validation Errors for %s: \n%s\n" % (title, errors)
            log(log_str, "lxml", timestamp=False)
            log_error(log_str, False)
        # timerInterval.stop()
        # timerFull.stop()
        # del timerInterval
        # del timerFull
        return success, errors

    def validateNoteContent(self, content, title="Note Contents"):
        """

        :param content: Valid ENML without the <en-note></en-note> tags. Will be processed by makeNoteBody
        :return:
        """
        return self.validateNoteBody(self.makeNoteBody(content), title)

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
    def makeNoteBody(content, resources=[], encode=True):
        ## Build body of note

        nBody = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        nBody += "<!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\">"
        nBody += "<en-note>%s" % content
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

    def addNoteToMakeNoteQueue(self, noteTitle, noteContents, tagNames=list(), parentNotebook=None, resources=[],
                               guid=None):
        sql = "FROM %s WHERE " % TABLES.MAKE_NOTE_QUEUE
        if guid:
            sql += "guid = '%s'" % guid
        else:
            sql += "title = '%s' AND contents = '%s'" % (escape_text_sql(noteTitle), escape_text_sql(noteContents))
        statuses = ankDB().all('SELECT validation_status ' + sql)
        if len(statuses) > 0:
            if str(statuses[0]['validation_status']) == '1': return EvernoteAPIStatus.Success
            ankDB().execute("DELETE " + sql)
        # log_sql(sql)
        # log_sql([ guid, noteTitle, noteContents, ','.join(tagNames), parentNotebook])
        ankDB().execute(
            "INSERT INTO %s(guid, title, contents, tagNames, notebookGuid) VALUES(?, ?, ?, ?, ?)" % TABLES.MAKE_NOTE_QUEUE,
            guid, noteTitle, noteContents, ','.join(tagNames), parentNotebook)
        return EvernoteAPIStatus.RequestQueued

    def makeNote(self, noteTitle, noteContents, tagNames=list(), parentNotebook=None, resources=[], guid=None,
                 validated=None):
        """
        Create or Update a Note instance with title and body
        Send Note object to user's account
        :type noteTitle: str
        :param noteContents: Valid ENML without the <en-note></en-note> tags. Will be processed by makeNoteBody
        :rtype : (EvernoteAPIStatus, EvernoteNote)
        :returns Status and Note
        """
        callType = "create"

        if validated is None:
            if not ANKNOTES.ENABLE_VALIDATION:
                validated = True
            else:
                validation_status = self.addNoteToMakeNoteQueue(noteTitle, noteContents, tagNames, parentNotebook,
                                                                resources, guid)
                if not validation_status.IsSuccess and not self.hasValidator:
                    return validation_status, None

        ourNote = EvernoteNote()
        ourNote.title = noteTitle.encode('utf-8')
        if guid:
            callType = "update"
            ourNote.guid = guid

            ## Build body of note  
        nBody = self.makeNoteBody(noteContents, resources)
        if not validated is True and not validation_status.IsSuccess:
            success, errors = self.validateNoteBody(nBody, ourNote.title)
            if not success:
                return EvernoteAPIStatus.UserError, None
        ourNote.content = nBody

        self.initialize_note_store()

        while '' in tagNames: tagNames.remove('')
        if len(tagNames) > 0:
            if ANKNOTES.EVERNOTE_IS_SANDBOXED and not '#Sandbox' in tagNames:
                tagNames.append("#Sandbox")
            ourNote.tagNames = tagNames

        ## parentNotebook is optional; if omitted, default notebook is used
        if parentNotebook:
            if hasattr(parentNotebook, 'guid'):
                ourNote.notebookGuid = parentNotebook.guid
            elif isinstance(parentNotebook, str) or isinstance(parentNotebook, unicode):
                ourNote.notebookGuid = parentNotebook

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

    def check_notebook_metadata(self, notes):
        """
        :param notes:
        :type : list[EvernoteNotePrototype]
        :return:
        """
        if not hasattr(self, 'notebook_data'):
            self.notebook_data = {x.guid:{'stack': x.stack, 'name': x.name} for x in ankDB().execute("SELECT * FROM %s WHERE 1" % TABLES.EVERNOTE.NOTEBOOKS) }
        for note in notes:
            assert(isinstance(note, EvernoteNotePrototype))
            if not note.NotebookGuid in self.notebook_data:
                self.update_notebook_db()
                if not note.NotebookGuid in self.notebook_data:
                    log_error("FATAL ERROR: Notebook GUID %s for Note %s: %s does not exist on Evernote servers" % (note.NotebookGuid, note.Guid, note.Title))
                    raise EDAMNotFoundException()
                    return False
        return True

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
                if not note_metadata.tagGuids: continue
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
        if not hasattr(self, 'tag_data'): self.tag_data = {}
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
        if not hasattr(self, 'tag_data'):
            self.tag_data = {x.guid: x.name for x in ankDB().execute("SELECT guid, name FROM %s WHERE 1" % TABLES.EVERNOTE.TAGS)}
        missing_tags = [x for x in tag_guids_original if x not in self.tag_data]
        if len(missing_tags) > 0:
            self.update_tags_db()
            missing_tags = [x for x in tag_guids_original if x not in self.tag_data]
            if len(missing_tags) > 0:
                log_error("FATAL ERROR: Tag Guid(s) %s were not found on the Evernote Servers" % str(missing_tags))
                raise EDAMNotFoundException()

        tagNamesToImport = get_tag_names_to_import({x: self.tag_data[x] for x in tag_guids_original})
        """:type : dict[string, EvernoteTag]"""
        if tagNamesToImport:
            is_struct = None
            for k, v in tagNamesToImport.items():
                if is_struct is None: is_struct = isinstance(v, EvernoteTag)
                tagGuids.append(k)
                tagNames.append(v.Name if is_struct else v)
            tagNames = sorted(tagNames, key=lambda s: s.lower())
        return tagGuids, tagNames


DEBUG_RAISE_API_ERRORS = False
