### Python Imports
import socket

### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.EvernoteNotePrototype import EvernoteNotePrototype
from anknotes.error import *

### Evernote Imports
from evernote.edam.error.ttypes import EDAMSystemException


class EvernoteNoteFetcher(object):



    def __init__(self, evernote, evernote_guid=None, use_local_db_only=False):
        """

        :type evernote: ankEvernote.Evernote
        """
        self.results = EvernoteNoteFetcherResults()
        self.result = EvernoteNoteFetcherResult()
        self.api_calls = 0
        self.keepEvernoteTags = True
        self.evernote = evernote
        self.tagNames = []
        self.use_local_db_only = use_local_db_only
        self.__update_sequence_number__ = -1
        if not evernote_guid:
            self.evernote_guid = ""
            return
        self.evernote_guid = evernote_guid
        if not self.use_local_db_only:
            self.__update_sequence_number__ = self.evernote.metadata[self.evernote_guid].updateSequenceNum
        self.getNote()

    def UpdateSequenceNum(self):
        if self.result.Note:
            return self.result.Note.UpdateSequenceNum
        return self.__update_sequence_number__

    def reportSuccess(self, note, source=None):
        self.reportResult(EvernoteAPIStatus.Success, note, source)
    
    def reportResult(self, status=None, note=None, source=None):         
        if note:
            self.result.Note = note             
            status = EvernoteAPIStatus.Success
            if not source:
                source = 2
        if status: 
            self.result.Status = status
        if source:
            self.result.Source = source         
        self.results.reportResult(self.result)        
        
    def getNoteLocal(self):
        # Check Anknotes database for note
        query = "SELECT guid, title, content, notebookGuid, tagNames, updateSequenceNum FROM %s WHERE guid = '%s'" % (
            TABLES.EVERNOTE.NOTES, self.evernote_guid)
        if self.UpdateSequenceNum() > -1:
            query += " AND `updateSequenceNum` = %d" % self.UpdateSequenceNum()
        db_note = ankDB().first(query)
        """:type : sqlite.Row"""
        if not db_note: return False
        if not self.use_local_db_only:
            log("                   > getNoteLocal:  GUID: '%s': %-40s" % (self.evernote_guid, db_note['title']), 'api')
        assert db_note['guid'] == self.evernote_guid
        self.reportSuccess(EvernoteNotePrototype(db_note=db_note), 1)
        self.tagNames = self.result.Note.TagNames if self.keepEvernoteTags else []        
        return True

    def addNoteFromServerToDB(self):
        # Note that values inserted into the db need to be converted from byte strings (utf-8) to unicode
        title = self.whole_note.title
        content = self.whole_note.content
        tag_names = u',' + u','.join(self.tagNames).decode('utf-8') + u','
        if isinstance(title, str):
            title = unicode(title, 'utf-8')
        if isinstance(content, str):
            content = unicode(content, 'utf-8')
        if isinstance(tag_names, str):
            tag_names = unicode(tag_names, 'utf-8')
        title = title.replace(u'\'', u'\'\'')
        content = content.replace(u'\'', u'\'\'')
        tag_names = tag_names.replace(u'\'', u'\'\'')
        sql_query_header = u'INSERT OR REPLACE INTO `%s`' % TABLES.EVERNOTE.NOTES
        sql_query_header_history = u'INSERT INTO `%s`' % TABLES.EVERNOTE.NOTES_HISTORY
        sql_query_columns = u'(`guid`,`title`,`content`,`updated`,`created`,`updateSequenceNum`,`notebookGuid`,`tagGuids`,`tagNames`) VALUES (\'%s\',\'%s\',\'%s\',%d,%d,%d,\'%s\',\'%s\',\'%s\');' % (
            self.whole_note.guid.decode('utf-8'), title, content, self.whole_note.updated, self.whole_note.created,
            self.whole_note.updateSequenceNum, self.whole_note.notebookGuid.decode('utf-8'),
            u',' + u','.join(self.tagGuids).decode('utf-8') + u',', tag_names)
        sql_query = sql_query_header + sql_query_columns
        log_sql('UPDATE_ANKI_DB: Add Note: SQL Query: ' + sql_query)
        ankDB().execute(sql_query)
        sql_query = sql_query_header_history + sql_query_columns
        ankDB().execute(sql_query)

    def getNoteRemoteAPICall(self):
        api_action_str = u'trying to retrieve a note. We will save the notes downloaded thus far.'
        log_api("  > getNote [%3d]" % (self.api_calls + 1), "GUID: '%s'" % self.evernote_guid)

        try:
            self.whole_note = self.evernote.noteStore.getNote(self.evernote.token, self.evernote_guid, True, False,
                                                              False, False)
            """:type : evernote.edam.type.ttypes.Note"""
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str):
                self.reportResult(EvernoteAPIStatus.RateLimitError)
                if DEBUG_RAISE_API_ERRORS: raise
                return False
            raise
        except socket.error, v:
            if HandleSocketError(v, api_action_str):
                self.reportResult(EvernoteAPIStatus.SocketError)
                if DEBUG_RAISE_API_ERRORS: raise
                return False
            raise
        assert self.whole_note.guid == self.evernote_guid
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
        self.reportSuccess(EvernoteNotePrototype(whole_note=self.whole_note, tags=self.tagNames))        
        return True

    def getNote(self, evernote_guid=None):
        if evernote_guid:
            self.result.Note = None
            self.evernote_guid = evernote_guid
            self.__update_sequence_number__ = self.evernote.metadata[
                self.evernote_guid].updateSequenceNum if not self.use_local_db_only else -1
        if self.getNoteLocal(): return True
        if self.use_local_db_only: return False
        return self.getNoteRemote()
