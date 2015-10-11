### Python Imports
import socket

### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.EvernoteNotePrototype import EvernoteNotePrototype
from anknotes.error import *

### Evernote Imports
from evernote.edam.error.ttypes import EDAMSystemException


class EvernoteNoteFetcher(object):
    def __init__(self, evernote=None, guid=None, use_local_db_only=False):
        """

        :type evernote: ankEvernote.Evernote
        """
        self.__reset_data()
        self.results = EvernoteNoteFetcherResults()
        self.result = EvernoteNoteFetcherResult()
        self.api_calls = 0
        self.keepEvernoteTags, self.deleteQueryTags = True, True
        self.evernoteQueryTags, self.tagsToDelete = [], []
        self.use_local_db_only = use_local_db_only
        self.__update_sequence_number = -1
        self.evernote = evernote if evernote else None
        if not guid:
            self.guid = ""; return
        self.guid = guid
        if evernote and not self.use_local_db_only:
            self.__update_sequence_number = self.evernote.metadata[
            self.guid].updateSequenceNum
        self.getNote()

    def __reset_data(self):
        self.tagNames = []
        self.tagGuids = []
        self.whole_note = None

    @property
    def UpdateSequenceNum(self):
        if self.result.Note:
            return self.result.Note.UpdateSequenceNum
        return self.__update_sequence_number

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
        query = "guid = '%s'" % self.guid
        if self.UpdateSequenceNum > -1:
            query += " AND `updateSequenceNum` = %d" % self.UpdateSequenceNum
        db_note = ankDB().first(query)
        """:type : sqlite.Row"""
        if not db_note:
            return False
        if not self.use_local_db_only:
            log(' ' + '-' * 14 + ' ' * 5 + "> getNoteLocal: %s" % db_note['title'], 'api')
        assert db_note['guid'] == self.guid
        self.reportSuccess(EvernoteNotePrototype(db_note=db_note), 1)
        self.setNoteTags(tag_names=self.result.Note.TagNames, tag_guids=self.result.Note.TagGuids)
        return True

    def setNoteTags(self, tag_names=None, tag_guids=None):
        if not self.keepEvernoteTags:
            self.tagGuids, self.tagNames = [], []; return
        # if not tag_names:
        # if self.tagNames: tag_names = self.tagNames
        # if not tag_names and self.result.Note: tag_names = self.result.Note.TagNames
        # if not tag_names and self.whole_note: tag_names = self.whole_note.tagNames
        # if not tag_names: tag_names = None
        if not tag_guids:
            tag_guids = self.tagGuids if self.tagGuids else (
            self.result.Note.TagGuids if self.result.Note else (self.whole_note.tagGuids if self.whole_note else None))
        if not tag_names:
            tag_names = self.tagNames if self.tagNames else (
            self.result.Note.TagNames if self.result.Note else (self.whole_note.tagNames if self.whole_note else None))
        if not self.evernote or self.result.Source is 1:
            self.tagGuids, self.tagNames = tag_guids, tag_names; return
        self.tagGuids, self.tagNames = self.evernote.get_matching_tag_data(tag_guids, tag_names)

    def addNoteFromServerToDB(self, whole_note=None, tag_names=None):
        """
        Adds note to Anknote DB from an Evernote Note object provided by the Evernote API
        :type whole_note : evernote.edam.type.ttypes.Note
        """
        if whole_note:
            self.whole_note = whole_note
        if tag_names:
            self.tagNames = tag_names
        log('Adding  %s: %s' % (self.whole_note.guid, self.whole_note.title), 'ankDB')
        if not self.tagGuids:
            self.tagGuids = self.whole_note.tagGuids
        auto_columns = ['guid', 'title', 'content', 'updated', 'created', 'updateSequenceNum', 'notebookGuid']
        columns = {key: getattr(self.whole_note, key) for key in auto_columns}
        columns.update({key: getattr(self, key) for key in ['tagNames', 'tagGuids']})
        for key, value in columns.items():
            if isinstance(value, list):
                columns[key] = u',' + u','.join(map(lambda x: unicode(x, 'utf-8'), value)) + u','
            elif isinstance(value, str):
                columns[key] = unicode(value, 'utf-8')
        db = ankDB()
        db.insert_or_replace(columns)
        db.insert(columns, table=TABLES.EVERNOTE.NOTES_HISTORY)
        db.commit()

    def getNoteRemoteAPICall(self):
        notestore_status = self.evernote.initialize_note_store()
        if not notestore_status.IsSuccess:
            self.reportResult(notestore_status)
            return False
        api_action_str = u'trying to retrieve a note. We will save the notes downloaded thus far.'
        self.api_calls += 1
        log_api("  > getNote [%3d]" % self.api_calls, self.guid)
        try:
            self.whole_note = self.evernote.noteStore.getNote(self.evernote.token, self.guid, True, False,
                                                              False, False)
            """:type : evernote.edam.type.ttypes.Note"""
        except EDAMSystemException as e:
            if not HandleEDAMRateLimitError(e, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS:
                raise
            self.reportResult(EvernoteAPIStatus.RateLimitError)
            return False
        except socket.error as v:
            if not HandleSocketError(v, api_action_str) or EVERNOTE.API.DEBUG_RAISE_ERRORS:
                raise
            self.reportResult(EvernoteAPIStatus.SocketError)
            return False
        assert self.whole_note.guid == self.guid
        return True

    def getNoteRemote(self):
        if self.api_calls > EVERNOTE.IMPORT.API_CALLS_LIMIT > -1:
            log(
                "Aborting Evernote.getNoteRemote: EVERNOTE.IMPORT.API_CALLS_LIMIT of %d has been reached" % EVERNOTE.IMPORT.API_CALLS_LIMIT)
            return None
        if not self.getNoteRemoteAPICall():
            return False
        # self.tagGuids, self.tagNames = self.evernote.get_tag_names_from_guids(self.whole_note.tagGuids)
        self.setNoteTags(tag_guids=self.whole_note.tagGuids)
        self.addNoteFromServerToDB()
        if not self.keepEvernoteTags:
            self.tagNames = []
        self.reportSuccess(EvernoteNotePrototype(whole_note=self.whole_note, tags=self.tagNames))
        return True

    def setNote(self, whole_note):
        self.whole_note = whole_note
        self.addNoteFromServerToDB()

    def getNote(self, guid=None):
        self.__reset_data()
        if guid:
            self.result.Note = None
            self.guid = guid
            self.evernote.guid = guid
            self.__update_sequence_number = self.evernote.metadata[
                self.guid].updateSequenceNum if not self.use_local_db_only else -1
        if self.getNoteLocal():
            return True
        if self.use_local_db_only:
            return False
        return self.getNoteRemote()
