# -*- coding: utf-8 -*-
### Python Imports
import socket
try:    from pysqlite2 import dbapi2 as sqlite
except ImportError: from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
from anknotes.shared import *

### Evernote Imports 
from evernote.edam.type.ttypes import Note
from evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException, EDAMNotFoundException
from evernote.api.client import EvernoteClient

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

DEBUG_RAISE_API_ERRORS = False    

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
                
        def __init__(self, evernote, evernote_guid = None, use_local_db_only = False):
            self.result = self.EvernoteNoteFetcherResult()
            self.api_calls = 0
            self.keepEvernoteTags = True         
            self.evernote = evernote
            self.use_local_db_only = use_local_db_only
            self.updateSequenceNum = -1
            if not evernote_guid:
                self.evernote_guid = ""
                return             
            self.evernote_guid = evernote_guid 
            if not self.use_local_db_only:
                self.updateSequenceNum = self.evernote.metadata[self.evernote_guid].updateSequenceNum 
            self.getNote()              
          
        def getNoteLocal(self):
            # Check Anknotes database for note
            query = "SELECT guid, title, content, notebookGuid, tagNames, updateSequenceNum FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, self.evernote_guid)
            if self.updateSequenceNum > -1:
                query += " AND `updateSequenceNum` = %d" % (self.updateSequenceNum)
            db_note = ankDB().first(query)
            # showInfo(self.evernote_guid + '\n\n' + query)
            if not db_note: return False
            note_guid, note_title, note_content, note_notebookGuid, note_tagNames, note_usn = db_note
            if not self.use_local_db_only:
                log("                     > getNoteLocal: Note '%s': %-40s" % (self.evernote_guid, note_title), 'api')
            self.updateSequenceNum = note_usn 
            self.tagNames = note_tagNames[1:-1].split(',') if self.keepEvernoteTags else []
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
            sql_query_header = u'INSERT OR REPLACE INTO `%s`' % (TABLES.EVERNOTE.NOTES)
            sql_query_header_history = u'INSERT INTO `%s`' % (TABLES.EVERNOTE.NOTES_HISTORY)
            sql_query_columns = u'(`guid`,`title`,`content`,`updated`,`created`,`updateSequenceNum`,`notebookGuid`,`tagGuids`,`tagNames`) VALUES (\'%s\',\'%s\',\'%s\',%d,%d,%d,\'%s\',\'%s\',\'%s\');' % (self.whole_note.guid.decode('utf-8'), title, content, self.whole_note.updated, self.whole_note.created, self.whole_note.updateSequenceNum, self.whole_note.notebookGuid.decode('utf-8'), u',' + u','.join(self.tagGuids).decode('utf-8') + u',', tag_names)            
            sql_query = sql_query_header + sql_query_columns
            log_sql('UPDATE_ANKI_DB: Add Note: SQL Query: ' + sql_query)
            ankDB().execute(sql_query)     
            sql_query = sql_query_header_history + sql_query_columns
            ankDB().execute(sql_query)     
            
        def getNoteRemoteAPICall(self):
            api_action_str = u'trying to retrieve a note. We will save the notes downloaded thus far.'
            log_api("getNote [%3d]" % (self.api_calls+1), "GUID: '%s'" % (self.evernote_guid))  
            
            try:                        
                self.whole_note = self.evernote.noteStore.getNote(self.evernote.token, self.evernote_guid, True, False, False, False)
            except EDAMSystemException as e:
                if HandleEDAMRateLimitError(e, api_action_str): 
                    self.result.status = 1
                    if DEBUG_RAISE_API_ERRORS: raise 
                    return False
                raise         
            except socket.error, v:
                if HandleSocketError(v, api_action_str): 
                    self.result.status = 2
                    if DEBUG_RAISE_API_ERRORS: raise 
                    return False
                raise 
            assert self.whole_note.guid == self.evernote_guid 
            self.result.status = 0
            self.result.source = 2
            return True
        
        def getNoteRemote(self):
            # if self.getNoteCount > EVERNOTE.GET_NOTE_LIMIT: 
                # log("Aborting Evernote.getNoteRemote: EVERNOTE.GET_NOTE_LIMIT of %d has been reached" % EVERNOTE.GET_NOTE_LIMIT)
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
                self.updateSequenceNum = self.evernote.metadata[self.evernote_guid].updateSequenceNum if not self.use_local_db_only else -1
            if self.getNoteLocal(): return True 
            if self.use_local_db_only: return False 
            return self.getNoteRemote()        

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
        
    def updateNote(self, guid, noteTitle, noteBody, tagNames=list(), parentNotebook=None,  resources=[]):
        return self.makeNote(noteTitle, noteBody, tagNames=tagNames, parentNotebook=parentNotebook,  resources=resources, guid=guid)
        
    def makeNoteBody(self, noteBody, encode=True):
       ## Build body of note

        nBody = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        nBody += "<!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\">"
        nBody += "<en-note>%s" % noteBody
        # if resources:
            # ### Add Resource objects to note body
            # nBody += "<br />" * 2
            # ourNote.resources = resources
            # for resource in resources:
                # hexhash = binascii.hexlify(resource.data.bodyHash)
                # nBody += "Attachment with hash %s: <br /><en-media type=\"%s\" hash=\"%s\" /><br />" % \
                    # (hexhash, resource.mime, hexhash)
        nBody += "</en-note>"
        if encode:
            nBody = nBody.encode('utf-8')    
        return nBody

    def makeNote(self, noteTitle, noteBody, tagNames=list(), parentNotebook=None,  resources=[], guid=None):
            """
            Create or Update a Note instance with title and body 
            Send Note object to user's account
            """

            callType = "create"
            
            ourNote = Note()
            ourNote.title = noteTitle.encode('utf-8')
            if guid:
                callType = "update"
                ourNote.guid = guid 

            ## Build body of note  
            nBody = self.makeNoteBody(noteBody)
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
            log_api(callType + "Note", "'%s'" % (noteTitle))        
            try:                            
                note = getattr(self.noteStore,callType+'Note')(self.token, ourNote)
            except EDAMSystemException as e:
                if HandleEDAMRateLimitError(e, api_action_str): 
                    if DEBUG_RAISE_API_ERRORS: raise 
                    return 1, None
            except socket.error, v:
                if HandleSocketError(v, api_action_str): 
                    if DEBUG_RAISE_API_ERRORS: raise 
                    return 2, None  
            except EDAMUserException, edue:
                ## Something was wrong with the note data
                ## See EDAMErrorCode enumeration for error code explanation
                ## http://dev.evernote.com/documentation/reference/Errors.html#Enum_EDAMErrorCode
                print "EDAMUserException:", edue
                log_error("-------------------------------------------------")
                log_error("EDAMUserException:  " + str(edue))
                log_error(str( ourNote.tagNames ))
                log_error(str( ourNote.content ))
                log_error("-------------------------------------------------\r\n")
                if DEBUG_RAISE_API_ERRORS: raise 
                return 3, None
            except EDAMNotFoundException, ednfe:
                print "EDAMNotFoundException:", ednfe
                log_error("-------------------------------------------------")
                log_error("EDAMNotFoundException:  " + str(ednfe))
                if callType is "update":
                    log_error(str( ourNote.guid ))
                if ourNote.notebookGuid:
                    log_error(str( ourNote.notebookGuid ))
                log_error("-------------------------------------------------\r\n")
                if DEBUG_RAISE_API_ERRORS: raise 
                return 4, None
            except Exception, e:
                print "Unknown Exception:", e
                log_error("-------------------------------------------------")
                log_error("Unknown Exception:  " + str(e))
                log_error(str( ourNote.tagNames ))
                log_error(str( ourNote.content ))
                log_error("-------------------------------------------------\r\n")
                raise
            # noinspection PyUnboundLocalVariable
            note.content = nBody
            return 0, note                  
    
    def create_evernote_notes(self, evernote_guids = None, use_local_db_only=False):  
        if not hasattr(self, 'guids') or evernote_guids: self.evernote_guids = evernote_guids
        if not use_local_db_only:
            self.check_ancillary_data_up_to_date()        
        notes = []   
        fetcher = self.EvernoteNoteFetcher(self, use_local_db_only=use_local_db_only)
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
                notebook  = ankDB().first("SELECT name, stack FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTEBOOKS, notebookGuid))
                if not notebook: 
                    log("   > Notebook check: Missing notebook guid '%s'. Will update with an API call." % notebookGuid)
                    return False
                notebook_name, notebook_stack = notebook
                self.notebook_data[notebookGuid] = {"stack": notebook_stack, "name": notebook_name}
                notebook_guids.append(notebookGuid)
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
            data.append([notebook.guid, notebook.name, notebook.updateSequenceNum, notebook.serviceUpdated, notebook.stack])
        ankDB().execute("DROP TABLE %s " % TABLES.EVERNOTE.NOTEBOOKS)
        ankDB().InitNotebooks(True)
        log_dump(data, 'update_notebook_db table data')
        ankDB().executemany("INSERT INTO `%s`(`guid`,`name`,`updateSequenceNum`,`serviceUpdated`, `stack`) VALUES (?, ?, ?, ?, ?)" % TABLES.EVERNOTE.NOTEBOOKS, data)  
        log_dump(ankDB().all("SELECT * FROM %s WHERE 1" % TABLES.EVERNOTE.NOTEBOOKS), 'sql data')

    def check_tags_up_to_date(self):        
        tag_guids = []
        for evernote_guid in self.evernote_guids:
            if not evernote_guid in self.metadata:
                log_error('Could not find note metadata for Note ''%s''' % evernote_guid)
                return False
            else:            
                note_metadata = self.metadata[evernote_guid]            
                for tag_guid in note_metadata.tagGuids:                
                    if not tag_guid in tag_guids and not tag_guid in self.tag_data: 
                        tag_name = ankDB().scalar("SELECT name FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.TAGS, tag_guid))
                        if not tag_name: 
                            return False
                        self.tag_data[tag_guid] = tag_name 
                        tag_guids.append(tag_guid)   
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
        ankDB().executemany("INSERT OR REPLACE INTO `%s`(`guid`,`name`,`parentGuid`,`updateSequenceNum`) VALUES (?, ?, ?, ?)" % TABLES.EVERNOTE.TAGS, data)        
    
    def get_tag_names_from_evernote_guids(self, tag_guids_original):        
        tagGuids = []
        tagNames = []
        tagNamesToImport = get_tag_names_to_import({x: self.tag_data[x] for x in tag_guids_original})
        for k,v in tagNamesToImport.items():
            tagGuids.append(k)
            tagNames.append(v)
        tagNames = sorted(tagNames, key=lambda s: s.lower())
        return tagGuids, tagNames     
     