### Python Imports
import socket

### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.EvernoteNote import EvernoteNote
from anknotes.error import *

### Evernote Imports
from evernote.edam.error.ttypes import EDAMSystemException


class EvernoteNoteFetcher(object):
    class EvernoteNoteFetcherResult(object):
        def __init__(self, note=None, status=-1, source=-1):
            self.note = note
            self.status = status
            self.source = source

    def __init__(self, evernote, evernote_guid=None, use_local_db_only=False):
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
        query = "SELECT guid, title, content, notebookGuid, tagNames, updateSequenceNum FROM %s WHERE guid = '%s'" % (
        TABLES.EVERNOTE.NOTES, self.evernote_guid)
        if self.updateSequenceNum > -1:
            query += " AND `updateSequenceNum` = %d" % self.updateSequenceNum
        db_note = ankDB().first(query)
        # showInfo(self.evernote_guid + '\n\n' + query)
        if not db_note: return False
        note_guid, note_title, note_content, note_notebookGuid, note_tagNames, note_usn = db_note
        if not self.use_local_db_only:
            log("                   > getNoteLocal:  GUID: '%s': %-40s" % (self.evernote_guid, note_title), 'api')
        self.updateSequenceNum = note_usn
        self.tagNames = note_tagNames[1:-1].split(',') if self.keepEvernoteTags else []
        self.result.note = EvernoteNote(note_title, note_content, note_guid, self.tagNames,
                                                      note_notebookGuid, self.updateSequenceNum)
        assert self.result.note.guid == self.evernote_guid
        self.result.status = 0
        self.result.source = 1
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
        self.result.note = EvernoteNote(whole_note=self.whole_note, tags=self.tagNames)

        assert self.result.note.guid == self.evernote_guid
        return True

    def getNote(self, evernote_guid=None):
        if evernote_guid:
            self.result.note = None
            self.evernote_guid = evernote_guid
            self.updateSequenceNum = self.evernote.metadata[
                self.evernote_guid].updateSequenceNum if not self.use_local_db_only else -1
        if self.getNoteLocal(): return True
        if self.use_local_db_only: return False
        return self.getNoteRemote()
