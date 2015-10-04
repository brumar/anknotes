# -*- coding: utf-8 -*-
### Python Imports
import socket
import stopwatch
import sys
from datetime import datetime, timedelta
from StringIO import StringIO

# try:
# from lxml import etree
# eTreeImported = True
# except ImportError:
# eTreeImported = False

inAnki = 'anki' in sys.modules
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
from anknotes.shared import *
from anknotes.error import *

if inAnki:
    ### Anknotes Class Imports
    from anknotes.EvernoteNoteFetcher import EvernoteNoteFetcher
    from anknotes.EvernoteNotePrototype import EvernoteNotePrototype

    ### Evernote Imports
    from anknotes.evernote.edam.type.ttypes import Note as EvernoteNote
    from anknotes.evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException, EDAMNotFoundException
    from anknotes.evernote.api.client import EvernoteClient

    from aqt.utils import openLink, getText, showInfo


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
    __hasValidator__ = None
    token = None
    client = None
    """:type : EvernoteClient """

    def hasValidator(self):
        if self.__hasValidator__ is None: self.__hasValidator__ = import_etree()
        return self.__hasValidator__

    def __init__(self):
        self.tag_data = {}
        self.notebook_data = {}
        self.noteStore = None
        self.getNoteCount = 0
        # self.hasValidator = eTreeImported
        if ankDBIsLocal():
            log("Skipping Evernote client load (DB is Local)", 'client')
            return
        self.setup_client()

    def setup_client(self):
        auth_token = mw.col.conf.get(SETTINGS.EVERNOTE.AUTH_TOKEN, False)
        if not auth_token:
            # First run of the Plugin we did not save the access key yet
            secrets = {'holycrepe': '36f46ea5dec83d4a', 'scriptkiddi-2682': '965f1873e4df583c'}
            client = EvernoteClient(
                consumer_key=EVERNOTE.API.CONSUMER_KEY,
                consumer_secret=secrets[EVERNOTE.API.CONSUMER_KEY],
                sandbox=EVERNOTE.API.IS_SANDBOXED
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
            mw.col.conf[SETTINGS.EVERNOTE.AUTH_TOKEN] = auth_token
        else: client = EvernoteClient(token=auth_token, sandbox=EVERNOTE.API.IS_SANDBOXED)
        self.token = auth_token
        self.client = client
        log("Set up Evernote Client", 'client')

    def initialize_note_store(self):
        if self.noteStore:
            return EvernoteAPIStatus.Success
        api_action_str = u'trying to initialize the Evernote Note Store.'
        log_api("get_note_store")
        if not self.client:
            log_error(
                "Client does not exist for some reason. Did we not initialize Evernote Class? Current token: " + str(
                    self.token))
            self.setup_client()
        try: self.noteStore = self.client.get_note_store()
        except EDAMSystemException as e:
            if not HandleEDAMRateLimitError(e, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return EvernoteAPIStatus.RateLimitError
        except socket.error, v:
            if not HandleSocketError(v, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return EvernoteAPIStatus.SocketError
        return EvernoteAPIStatus.Success

    def loadDTD(self):
        if self.DTD: return
        timerInterval = stopwatch.Timer()
        log("Loading ENML DTD", "lxml", timestamp=False, do_print=True)
        self.DTD = etree.DTD(FILES.ANCILLARY.ENML_DTD)
        log("DTD Loaded in %s\n" % str(timerInterval), "lxml", timestamp=False, do_print=True)
        log('    > Note Validation: ENML DTD Loaded in %s' % str(timerInterval))
        del timerInterval

    def validateNoteBody(self, noteBody, title="Note Body"):
        self.loadDTD()
        noteBody = noteBody.replace('"http://xml.evernote.com/pub/enml2.dtd"',
                                    '"%s"' % convert_filename_to_local_link(FILES.ANCILLARY.ENML_DTD))
        parser = etree.XMLParser(dtd_validation=True, attribute_defaults=True)
        try: root = etree.fromstring(noteBody, parser)
        except Exception as e:
            log_str = "XML Loading of %s failed.\n    - Error Details: %s" % (title, str(e))
            log(log_str, "lxml", timestamp=False, do_print=True)
            log_error(log_str, False)
            return False, [log_str]
        try: success = self.DTD.validate(root)
        except Exception as e:
            log_str = "DTD Validation of %s failed.\n    - Error Details: %s" % (title, str(e))
            log(log_str, "lxml", timestamp=False, do_print=True)
            log_error(log_str, False)
            return False, [log_str]
        log("Validation %-9s for %s" % ("Succeeded" if success else "Failed", title), "lxml", timestamp=False,
            do_print=True)
        errors = [str(x) for x in self.DTD.error_log.filter_from_errors()]
        if not success:
            log_str = "DTD Validation Errors for %s: \n%s\n" % (title, str(errors))
            log(log_str, "lxml", timestamp=False)
            log_error(log_str, False)
        return success, errors

    def validateNoteContent(self, content, title="Note Contents"):
        """

        :param content: Valid ENML without the <en-note></en-note> tags. Will be processed by makeNoteBody
        :return:
        """
        return self.validateNoteBody(self.makeNoteBody(content), title)

    def updateNote(self, guid, noteTitle, noteBody, tagNames=None, parentNotebook=None, noteType=None, resources=None):
        """
        Update a Note instance with title and body
        Send Note object to user's account
        :rtype : (EvernoteAPIStatus, evernote.edam.type.ttypes.Note)
        :returns Status and Note
        """
        if resources is None: resources = []
        return self.makeNote(noteTitle, noteBody, tagNames=tagNames, parentNotebook=parentNotebook, noteType=noteType,
                             resources=resources,
                             guid=guid)

    @staticmethod
    def makeNoteBody(content, resources=None, encode=True):
        ## Build body of note
        if resources is None: resources = []
        nBody = content
        if not nBody.startswith("<?xml"):
            nBody = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            nBody += "<!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\">"
            nBody += "<en-note>%s" % content + "</en-note>"
        if encode and isinstance(nBody, unicode):
            nBody = nBody.encode('utf-8')
        return nBody

    @staticmethod
    def addNoteToMakeNoteQueue(noteTitle, noteContents, tagNames=list(), parentNotebook=None, resources=None,
                               noteType=None,
                               guid=None):
        if not noteType: noteType = 'Unspecified'
        if resources is None: resources = []
        sql = "FROM %s WHERE noteType = '%s' AND " % (TABLES.NOTE_VALIDATION_QUEUE, noteType) + (
            ("guid = '%s'" % guid) if guid else "title = '%s' AND contents = '%s'" % (
                escape_text_sql(noteTitle), escape_text_sql(noteContents)))
        statuses = ankDB().all('SELECT validation_status ' + sql)
        if len(statuses) > 0:
            if str(statuses[0]['validation_status']) == '1': return EvernoteAPIStatus.Success
            ankDB().execute("DELETE " + sql)
        ankDB().execute(
            "INSERT INTO %s(guid, title, contents, tagNames, notebookGuid, noteType) VALUES(?, ?, ?, ?, ?, ?)" % TABLES.NOTE_VALIDATION_QUEUE,
            guid, noteTitle, noteContents, ','.join(tagNames), parentNotebook, noteType)
        return EvernoteAPIStatus.RequestQueued

    def makeNote(self, noteTitle=None, noteContents=None, tagNames=None, parentNotebook=None, resources=None,
                 noteType=None, guid=None,
                 validated=None, enNote=None):
        """
        Create or Update a Note instance with title and body
        Send Note object to user's account
        :type noteTitle: str
        :param noteContents: Valid ENML without the <en-note></en-note> tags. Will be processed by makeNoteBody
        :type enNote : EvernoteNotePrototype
        :rtype : (EvernoteAPIStatus, EvernoteNote)
        :returns Status and Note
        """
        if tagNames is None: tagNames = []
        if enNote: guid, noteTitle, noteContents, tagNames, parentNotebook = enNote.Guid, enNote.FullTitle, enNote.Content, enNote.Tags, enNote.NotebookGuid or parentNotebook
        if resources is None: resources = []
        callType = "create"
        validation_status = EvernoteAPIStatus.Uninitialized
        if validated is None:
            if not EVERNOTE.UPLOAD.VALIDATION.ENABLED: validated = True
            else:
                validation_status = self.addNoteToMakeNoteQueue(noteTitle, noteContents, tagNames, parentNotebook,
                                                                resources, guid)
                if not validation_status.IsSuccess and not self.hasValidator: return validation_status, None
        log('%s: %s: ' % ('+VALIDATOR ' if self.hasValidator else '' + noteType, str(validation_status), noteTitle),
            'validation')
        ourNote = EvernoteNote()
        ourNote.title = noteTitle.encode('utf-8')
        if guid: callType = "update"; ourNote.guid = guid

        ## Build body of note
        nBody = self.makeNoteBody(noteContents, resources)
        if validated is not True and not validation_status.IsSuccess:
            success, errors = self.validateNoteBody(nBody, ourNote.title)
            if not success: return EvernoteAPIStatus.UserError, None
        ourNote.content = nBody

        notestore_status = self.initialize_note_store()
        if not notestore_status.IsSuccess: return notestore_status, None

        while '' in tagNames: tagNames.remove('')
        if len(tagNames) > 0:
            if EVERNOTE.API.IS_SANDBOXED and not '#Sandbox' in tagNames: tagNames.append("#Sandbox")
            ourNote.tagNames = tagNames

        ## parentNotebook is optional; if omitted, default notebook is used
        if parentNotebook:
            if hasattr(parentNotebook, 'guid'): ourNote.notebookGuid = parentNotebook.guid
            elif hasattr(parentNotebook, 'Guid'): ourNote.notebookGuid = parentNotebook.Guid
            elif isinstance(parentNotebook, str) or isinstance(parentNotebook,
                                                               unicode): ourNote.notebookGuid = parentNotebook

        ## Attempt to create note in Evernote account

        api_action_str = u'trying to %s a note' % callType
        log_api(callType + "Note", "'%s'" % noteTitle)
        try:
            note = getattr(self.noteStore, callType + 'Note')(self.token, ourNote)
        except EDAMSystemException as e:
            if not HandleEDAMRateLimitError(e, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return EvernoteAPIStatus.RateLimitError, None
        except socket.error, v:
            if not HandleSocketError(v, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return EvernoteAPIStatus.SocketError, None
        except EDAMUserException, edue:
            ## Something was wrong with the note data
            ## See EDAMErrorCode enumeration for error code explanation
            ## http://dev.evernote.com/documentation/reference/Errors.html#Enum_EDAMErrorCode
            print "EDAMUserException:", edue
            log_error("-" * 50, crosspost_to_default=False)
            log_error("EDAMUserException:  " + str(edue), crosspost='api')
            log_error(str(ourNote.tagNames), crosspost_to_default=False)
            log_error(str(ourNote.content), crosspost_to_default=False)
            log_error("-" * 50 + "\r\n", crosspost_to_default=False)
            if EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return EvernoteAPIStatus.UserError, None
        except EDAMNotFoundException, ednfe:
            print "EDAMNotFoundException:", ednfe
            log_error("-" * 50, crosspost_to_default=False)
            log_error("EDAMNotFoundException:  " + str(ednfe), crosspost='api')
            if callType is "update":
                log_error('GUID: ' + str(ourNote.guid), crosspost_to_default=False)
            if ourNote.notebookGuid:
                log_error('Notebook GUID: ' + str(ourNote.notebookGuid), crosspost_to_default=False)
            log_error("-" * 50 + "\r\n", crosspost_to_default=False)
            if EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return EvernoteAPIStatus.NotFoundError, None
        except Exception, e:
            print "Unknown Exception:", e
            log_error("-" * 50, crosspost_to_default=False)
            log_error("Unknown Exception:  " + str(e))
            log_error(str(ourNote.tagNames), crosspost_to_default=False)
            log_error(str(ourNote.content), crosspost_to_default=False)
            log_error("-" * 50 + "\r\n", crosspost_to_default=False)
            # return EvernoteAPIStatus.UnhandledError, None
            raise
        # noinspection PyUnboundLocalVariable
        note.content = nBody
        return EvernoteAPIStatus.Success, note

    def create_evernote_notes(self, evernote_guids=None, use_local_db_only=False):
        global inAnki
        """
        Create EvernoteNote objects from Evernote GUIDs using EvernoteNoteFetcher.getNote().
        Will prematurely return if fetcher.getNote fails

        :rtype : EvernoteNoteFetcherResults
        :param evernote_guids:
        :param use_local_db_only: Do not initiate API calls
        :return: EvernoteNoteFetcherResults
        """
        if not hasattr(self, 'evernote_guids') or evernote_guids: self.evernote_guids = evernote_guids
        if not use_local_db_only: self.check_ancillary_data_up_to_date()
        fetcher = EvernoteNoteFetcher(self, use_local_db_only=use_local_db_only)
        if len(evernote_guids) == 0: fetcher.results.Status = EvernoteAPIStatus.EmptyRequest; return fetcher.results
        if inAnki:
            fetcher.evernoteQueryTags = mw.col.conf.get(SETTINGS.EVERNOTE.QUERY.TAGS,
                                                        SETTINGS.EVERNOTE.QUERY.TAGS_DEFAULT_VALUE).replace(',',
                                                                                                            ' ').split()
            fetcher.keepEvernoteTags = mw.col.conf.get(SETTINGS.ANKI.TAGS.KEEP_TAGS,
                                                       SETTINGS.ANKI.TAGS.KEEP_TAGS_DEFAULT_VALUE)
            fetcher.deleteQueryTags = mw.col.conf.get(SETTINGS.ANKI.TAGS.DELETE_EVERNOTE_QUERY_TAGS, False)
            fetcher.tagsToDelete = mw.col.conf.get(SETTINGS.ANKI.TAGS.TO_DELETE, "").replace(',', ' ').split()
        for evernote_guid in self.evernote_guids:
            if not fetcher.getNote(evernote_guid): return fetcher.results
        return fetcher.results

    def check_ancillary_data_up_to_date(self):
        new_tags = 0 if self.check_tags_up_to_date() else self.update_tags_database(
            "Tags were not up to date when checking ancillary data")
        new_nbs = 0 if self.check_notebooks_up_to_date() else self.update_notebooks_database()
        self.report_ancillary_data_results(new_tags, new_nbs, 'Forced ')

    def update_ancillary_data(self):
        new_tags = self.update_tags_database("Manual call to update ancillary data")
        new_nbs = self.update_notebooks_database()
        self.report_ancillary_data_results(new_tags, new_nbs, 'Manual ', report_blank=True)

    @staticmethod
    def report_ancillary_data_results(new_tags, new_nbs, title_prefix='', report_blank=False):
        strr = ''
        if new_tags is 0 and new_nbs is 0:
            if not report_blank: return
            strr = 'No new tags or notebooks found'
        elif new_tags is None and new_nbs is None: strr = 'Error downloading ancillary data'
        elif new_tags is None: strr = 'Error downloading tags list, and '
        elif new_nbs is None: strr = 'Error downloading notebooks list, and '

        if new_tags > 0 and new_nbs > 0: strr = '%d new tag%s and %d new notebook%s found' % (
            new_tags, '' if new_tags is 1 else 's', new_nbs, '' if new_nbs is 1 else 's')
        elif new_nbs > 0: strr += '%d new notebook%s found' % (new_nbs, '' if new_nbs is 1 else 's')
        elif new_tags > 0: strr += '%d new tag%s found' % (new_tags, '' if new_tags is 1 else 's')
        show_tooltip("%sUpdate of ancillary data complete: " % title_prefix + strr, do_log=True)

    def set_notebook_data(self):
        if not hasattr(self, 'notebook_data') or not self.notebook_data or len(self.notebook_data.keys()) == 0:
            self.notebook_data = {x['guid']: EvernoteNotebook(x) for x in
                                  ankDB().execute("SELECT guid, name FROM %s WHERE 1" % TABLES.EVERNOTE.NOTEBOOKS)}

    def check_notebook_metadata(self, notes):
        """
        :param notes:
        :type : list[EvernoteNotePrototype]
        :return:
        """
        self.set_notebook_data()
        for note in notes:
            assert (isinstance(note, EvernoteNotePrototype))
            if note.NotebookGuid in self.notebook_data: continue
            new_nbs = self.update_notebooks_database()
            if note.NotebookGuid in self.notebook_data:
                log(
                    "Missing notebook GUID %s for note %s when checking notebook metadata. Notebook was found after updating Anknotes' notebook database." + '' if new_nbs < 1 else ' In total, %d new notebooks were found.' % new_nbs)
                continue
            log_error("FATAL ERROR: Notebook GUID %s for Note %s: %s does not exist on Evernote servers" % (
                note.NotebookGuid, note.Guid, note.Title))
            raise EDAMNotFoundException()
        return True

    def check_notebooks_up_to_date(self):
        for evernote_guid in self.evernote_guids:
            note_metadata = self.metadata[evernote_guid]
            notebookGuid = note_metadata.notebookGuid
            if not notebookGuid:
                log_error("   > Notebook check: Unable to find notebook guid for '%s'. Returned '%s'. Metadata: %s" % (
                    evernote_guid, str(notebookGuid), str(note_metadata)), crosspost_to_default=False)
            elif notebookGuid not in self.notebook_data:
                notebook = EvernoteNotebook(fetch_guid=notebookGuid)
                if not notebook.success:
                    log("   > Notebook check: Missing notebook guid '%s'. Will update with an API call." % notebookGuid)
                    return False
                self.notebook_data[notebookGuid] = notebook
        return True

    def update_notebooks_database(self):
        notestore_status = self.initialize_note_store()
        if not notestore_status.IsSuccess: return None  # notestore_status
        api_action_str = u'trying to update Evernote notebooks.'
        log_api("listNotebooks")
        try:
            notebooks = self.noteStore.listNotebooks(self.token)
            """: type : list[evernote.edam.type.ttypes.Notebook] """
        except EDAMSystemException as e:
            if not HandleEDAMRateLimitError(e, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return None
        except socket.error, v:
            if not HandleSocketError(v, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return None
        data = []
        self.notebook_data = {}
        for notebook in notebooks:
            self.notebook_data[notebook.guid] = {"stack": notebook.stack, "name": notebook.name}
            data.append(
                [notebook.guid, notebook.name, notebook.updateSequenceNum, notebook.serviceUpdated, notebook.stack])
        db = ankDB()
        old_count = db.scalar("SELECT COUNT(*) FROM %s WHERE 1" % TABLES.EVERNOTE.NOTEBOOKS)
        db.execute("DROP TABLE %s " % TABLES.EVERNOTE.NOTEBOOKS)
        db.InitNotebooks(True)
        # log_dump(data, 'update_notebooks_database table data', crosspost_to_default=False)
        db.executemany(
            "INSERT INTO `%s`(`guid`,`name`,`updateSequenceNum`,`serviceUpdated`, `stack`) VALUES (?, ?, ?, ?, ?)" % TABLES.EVERNOTE.NOTEBOOKS,
            data)
        db.commit()
        # log_dump(ankDB().all("SELECT * FROM %s WHERE 1" % TABLES.EVERNOTE.NOTEBOOKS), 'sql data', crosspost_to_default=False)
        return len(self.notebook_data) - old_count

    def update_tags_database(self, reason_str=''):
        if hasattr(self, 'LastTagDBUpdate') and datetime.now() - self.LastTagDBUpdate < timedelta(minutes=15):
            return None
        self.LastTagDBUpdate = datetime.now()
        notestore_status = self.initialize_note_store()
        if not notestore_status.IsSuccess: return None  # notestore_status
        api_action_str = u'trying to update Evernote tags.'
        log_api("listTags" + (': ' + reason_str) if reason_str else '')
        try:
            tags = self.noteStore.listTags(self.token)
            """: type : list[evernote.edam.type.ttypes.Tag] """
        except EDAMSystemException as e:
            if not HandleEDAMRateLimitError(e, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return None
        except socket.error, v:
            if not HandleSocketError(v, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS: raise
            return None
        data = []
        self.tag_data = {}
        enTag = None
        for tag in tags:
            enTag = EvernoteTag(tag)
            self.tag_data[enTag.Guid] = enTag
            data.append(enTag.items())
        if not enTag: return None
        db = ankDB()
        old_count = db.scalar("SELECT COUNT(*) FROM %s WHERE 1" % TABLES.EVERNOTE.TAGS)
        ankDB().execute("DROP TABLE %s " % TABLES.EVERNOTE.TAGS)
        ankDB().InitTags(True)
        ankDB().executemany(enTag.sqlUpdateQuery(), data)
        ankDB().commit()
        return len(self.tag_data) - old_count

    def set_tag_data(self):
        if not hasattr(self, 'tag_data') or not self.tag_data or len(self.tag_data.keys()) == 0:
            self.tag_data = {x['guid']: EvernoteTag(x) for x in
                             ankDB().execute("SELECT guid, name FROM %s WHERE 1" % TABLES.EVERNOTE.TAGS)}

    def get_missing_tags(self, current_tags, from_guids=True):
        if isinstance(current_tags, list): current_tags = set(current_tags)
        self.set_tag_data()
        all_tags = set(self.tag_data.keys() if from_guids else [v.Name for k, v in self.tag_data.items()])
        missing_tags = current_tags - all_tags
        if missing_tags:
            log_error("Missing Tag %s(s) were found:\nMissing: %s\n\nCurrent: %s\n\nAll Tags: %s\n\nTag Data: %s" % (
                'Guids' if from_guids else 'Names', ', '.join(sorted(missing_tags)), ', '.join(sorted(current_tags)),
                ', '.join(sorted(all_tags)), str(self.tag_data)))
        return missing_tags

    def get_matching_tag_data(self, tag_guids=None, tag_names=None):
        tagGuids = []
        tagNames = []
        assert tag_guids or tag_names
        from_guids = True if (tag_guids is not None) else False
        tags_original = tag_guids if from_guids else tag_names
        if self.get_missing_tags(tags_original, from_guids):
            self.update_tags_database("Missing Tag %s(s) Were found when attempting to get matching tag data" % (
                'Guids' if from_guids else 'Names'))
            missing_tags = self.get_missing_tags(tags_original, from_guids)
            if missing_tags:
                identifier = 'Guid' if from_guids else 'Name'
                keys = ', '.join(sorted(missing_tags))
                log_error("FATAL ERROR: Tag %s(s) %s were not found on the Evernote Servers" % (identifier, keys))
                raise EDAMNotFoundException(identifier.lower(), keys)
        if from_guids: tags_dict = {x: self.tag_data[x] for x in tags_original}
        else: tags_dict = {[k for k, v in self.tag_data.items() if v.Name is tag_name][0]: tag_name for tag_name in
                           tags_original}
        tagNamesToImport = get_tag_names_to_import(tags_dict)
        """:type : dict[string, EvernoteTag]"""
        if tagNamesToImport:
            is_struct = None
            for k, v in tagNamesToImport.items():
                if is_struct is None: is_struct = isinstance(v, EvernoteTag)
                tagGuids.append(k)
                tagNames.append(v.Name if is_struct else v)
            tagNames = sorted(tagNames, key=lambda s: s.lower())
        return tagGuids, tagNames

    def check_tags_up_to_date(self):
        for evernote_guid in self.evernote_guids:
            if evernote_guid not in self.metadata:
                log_error('Could not find note metadata for Note ''%s''' % evernote_guid)
                return False
            note_metadata = self.metadata[evernote_guid]
            if not note_metadata.tagGuids: continue
            for tag_guid in note_metadata.tagGuids:
                if tag_guid in self.tag_data: continue
                tag = EvernoteTag(fetch_guid=tag_guid)
                if not tag.success: return False
                self.tag_data[tag_guid] = tag
        return True
