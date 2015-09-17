# -*- coding: utf-8 -*-
### Python Imports
import socket

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.error import *

### Anknotes Class Imports
from anknotes.AnkiNotePrototype import AnkiNotePrototype
from anknotes.EvernoteNoteTitle import generateTOCTitle

### Anknotes Main Imports
from anknotes.Anki import Anki
from anknotes.ankEvernote import Evernote
from anknotes.EvernoteNotes import EvernoteNotes
from anknotes.EvernoteNotePrototype import EvernoteNotePrototype

try: from anknotes import settings
except: pass

### Evernote Imports 
from anknotes.evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec, NoteMetadata, NotesMetadataList
from anknotes.evernote.edam.type.ttypes import NoteSortOrder, Note as EvernoteNote
from anknotes.evernote.edam.error.ttypes import EDAMSystemException

### Anki Imports
try: from aqt import mw
except: pass

DEBUG_RAISE_API_ERRORS = False


class EvernoteImporter:
    forceAutoPage = False
    auto_page_callback = None
    """:type : lambda"""
    anki = None
    """:type : Anki"""
    evernote = None
    """:type : Evernote"""
    updateExistingNotes = UpdateExistingNotes.UpdateNotesInPlace
    @property
    def ManualMetadataMode(self):
        return (self.ManualGUIDs is not None and len(self.ManualGUIDs) > 0)

    def __init(self):
        self.updateExistingNotes = mw.col.conf.get(SETTINGS.UPDATE_EXISTING_NOTES,
                                                   UpdateExistingNotes.UpdateNotesInPlace)
        self.ManualGUIDs = None

    def override_evernote_metadata(self):
        guids = self.ManualGUIDs
        self.MetadataProgress = EvernoteMetadataProgress(self.currentPage)
        self.MetadataProgress.Total = len(guids)
        self.MetadataProgress.Current = min(self.MetadataProgress.Total - self.MetadataProgress.Offset, 250)
        result = NotesMetadataList()
        result.totalNotes = len(guids)
        result.updateCount = -1
        result.startIndex = self.MetadataProgress.Offset
        result.notes = []
        """:type : list[NoteMetadata]"""
        for i in range(self.MetadataProgress.Offset, self.MetadataProgress.Completed + 1):
            result.notes.append(NoteMetadata(guids[i]))
        result.totalNotes = len(guids)
        self.MetadataProgress.loadResults(result)
        self.evernote.metadata = self.MetadataProgress.NotesMetadata
        return True

    def get_evernote_metadata(self):
        """
        :returns: Metadata Progress Instance
        :rtype : EvernoteMetadataProgress)
        """
        query = settings.generate_evernote_query()
        evernote_filter = NoteFilter(words=query, ascending=True, order=NoteSortOrder.UPDATED)
        self.MetadataProgress = EvernoteMetadataProgress(self.currentPage)
        spec = NotesMetadataResultSpec(includeTitle=False, includeUpdated=False, includeUpdateSequenceNum=True,
                                       includeTagGuids=True, includeNotebookGuid=True)
        api_action_str = u'trying to search for note metadata'
        log_api("findNotesMetadata", "[Offset: %d]: Query: '%s'" % (self.MetadataProgress.Offset, query))
        try:
            result = self.evernote.noteStore.findNotesMetadata(self.evernote.token, evernote_filter,
                                                               self.MetadataProgress.Offset,
                                                               EVERNOTE.METADATA_QUERY_LIMIT, spec)
            """
            :type: NotesMetadataList
            """
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                self.MetadataProgress.Status = EvernoteAPIStatus.RateLimitError
                return False
            raise
        except socket.error, v:
            if HandleSocketError(v, api_action_str):
                if DEBUG_RAISE_API_ERRORS: raise
                self.MetadataProgress.Status = EvernoteAPIStatus.SocketError
                return False
            raise

        self.MetadataProgress.loadResults(result)
        self.evernote.metadata = self.MetadataProgress.NotesMetadata
        log("                                - Metadata Results: %s" % self.MetadataProgress.Summary, timestamp=False)
        return True

    def update_in_anki(self, evernote_guids):
        """ 
        :rtype : EvernoteNoteFetcherResults
        """
        Results = self.evernote.create_evernote_notes(evernote_guids)
        if self.ManualMetadataMode:
            self.evernote.check_notebooks_up_to_date()
        self.anki.notebook_data = self.evernote.notebook_data
        Results.Imported = self.anki.update_evernote_notes(Results.Notes)
        return Results

    def import_into_anki(self, evernote_guids):
        """ 
        :rtype : EvernoteNoteFetcherResults
        """
        Results = self.evernote.create_evernote_notes(evernote_guids)
        if self.ManualMetadataMode:
            self.evernote.check_notebooks_up_to_date()
        self.anki.notebook_data = self.evernote.notebook_data
        Results.Imported = self.anki.add_evernote_notes(Results.Notes)
        return Results

    def check_note_sync_status(self, evernote_guids):
        """
        Check for already existing, up-to-date, local db entries by Evernote GUID
        :param evernote_guids: List of GUIDs
        :return: List of Already Existing Evernote GUIDs
        :rtype: list[str]
        """
        notes_already_up_to_date = []
        for evernote_guid in evernote_guids:
            db_usn = ankDB().scalar("SELECT updateSequenceNum FROM %s WHERE guid = ?" % TABLES.EVERNOTE.NOTES,
                                    evernote_guid)
            if not self.evernote.metadata[evernote_guid].updateSequenceNum:
                server_usn = 'N/A'
            else:
                server_usn = self.evernote.metadata[evernote_guid].updateSequenceNum
            if evernote_guid in self.anki.usns:
                current_usn = self.anki.usns[evernote_guid]
                if current_usn == str(server_usn):
                    log_info = None  # 'ANKI NOTE UP-TO-DATE'
                    notes_already_up_to_date.append(evernote_guid)
                elif str(db_usn) == str(server_usn):
                    log_info = 'DATABASE ENTRY UP-TO-DATE'
                else:
                    log_info = 'NO COPIES UP-TO-DATE'
            else:
                current_usn = 'N/A'
                log_info = 'NO ANKI USN EXISTS'
            if log_info:
                if not self.evernote.metadata[evernote_guid].updateSequenceNum:
                    log_info += ' (Unable to find Evernote Metadata) '
                log("   > USN check for note '%s': %s: db/current/server = %s,%s,%s" % (
                    evernote_guid, log_info, str(db_usn), str(current_usn), str(server_usn)), 'usn')
        return notes_already_up_to_date

    def proceed(self, auto_paging=False):
        self.proceed_start(auto_paging)
        self.proceed_find_metadata(auto_paging)
        self.proceed_import_notes()
        self.proceed_autopage()

    def proceed_start(self, auto_paging=False):
        col = self.anki.collection()
        lastImport = col.conf.get(SETTINGS.EVERNOTE_LAST_IMPORT, None)
        col.conf[SETTINGS.EVERNOTE_LAST_IMPORT] = datetime.now().strftime(ANKNOTES.DATE_FORMAT)
        col.setMod()
        col.save()
        lastImportStr = get_friendly_interval_string(lastImport)
        if lastImportStr:
            lastImportStr = ' [LAST IMPORT: %s]' % lastImportStr
        log("!  > Starting Evernote Import: Page #%d: %-60s%s" % (
            self.currentPage, settings.generate_evernote_query(), lastImportStr))
        log(
            "-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------",
            timestamp=False)
        if not auto_paging:
            if not hasattr(self.evernote, 'noteStore'):
                log("    > Note store does not exist. Aborting.")
                return False
            self.evernote.getNoteCount = 0

    def proceed_find_metadata(self, auto_paging=False):
        global latestEDAMRateLimit, latestSocketError


        # anki_note_ids = self.anki.get_anknotes_note_ids()
        # anki_evernote_guids = self.anki.get_evernote_guids_from_anki_note_ids(anki_note_ids)

        if self.ManualMetadataMode:
            self.override_evernote_metadata()
        else:
            self.get_evernote_metadata()
        if self.MetadataProgress.Status == EvernoteAPIStatus.RateLimitError:
            m, s = divmod(latestEDAMRateLimit, 60)
            show_report("   > Error: Delaying Operation",
                            "Over the rate limit when searching for Evernote metadata<BR>Evernote requested we wait %d:%02d min" % (
                                m, s), delay=5)
            mw.progress.timer(latestEDAMRateLimit * 1000 + 10000, lambda: self.proceed(auto_paging), False)
            return False
        elif self.MetadataProgress.Status == EvernoteAPIStatus.SocketError:
            show_report("   > Error: Delaying Operation:",
                            "%s when searching for Evernote metadata" %
                            latestSocketError['friendly_error_msg'], "We will try again in 30 seconds", delay=5)
            mw.progress.timer(30000, lambda: self.proceed(auto_paging), False)
            return False

        self.ImportProgress = EvernoteImportProgress(self.anki, self.MetadataProgress)
        self.ImportProgress.loadAlreadyUpdated(
           [] if self.ManualMetadataMode else self.check_note_sync_status(self.ImportProgress.GUIDs.Server.Existing.All))
        log("                                - " + self.ImportProgress.Summary + "\n", timestamp=False)

    def proceed_import_notes(self):
        self.anki.start_editing()
        self.ImportProgress.processResults(self.import_into_anki(self.ImportProgress.GUIDs.Server.New))
        if self.updateExistingNotes is UpdateExistingNotes.UpdateNotesInPlace:
            self.ImportProgress.processUpdateInPlaceResults(
                self.update_in_anki(self.ImportProgress.GUIDs.Server.Existing.OutOfDate))
        elif self.updateExistingNotes is UpdateExistingNotes.DeleteAndReAddNotes:
            self.anki.delete_anki_cards(self.ImportProgress.GUIDs.Server.Existing.OutOfDate)
            self.ImportProgress.processDeleteAndUpdateResults(
                self.import_into_anki(self.ImportProgress.GUIDs.Server.Existing.OutOfDate))
        show_report("   > Import Complete", self.ImportProgress.ResultsSummaryLines)
        self.anki.stop_editing()
        self.anki.collection().autosave()

    def proceed_autopage(self):
        if not self.autoPagingEnabled:
            return
        global latestEDAMRateLimit, latestSocketError
        col = self.anki.collection()
        status = self.ImportProgress.Status
        if status == EvernoteAPIStatus.RateLimitError:
            m, s = divmod(latestEDAMRateLimit, 60)
            show_report("   > Error: Delaying Auto Paging",
                            "Over the rate limit when getting Evernote notes<BR>Evernote requested we wait %d:%02d min" % (
                                m, s), delay=5)
            mw.progress.timer(latestEDAMRateLimit * 1000 + 10000, lambda: self.proceed(True), False)
            return False
        if status == EvernoteAPIStatus.SocketError:
            show_report("   > Error: Delaying Auto Paging:",
                            "%s when getting Evernote notes" % latestSocketError[
                                'friendly_error_msg'],
                            "We will try again in 30 seconds", delay=5)
            mw.progress.timer(30000, lambda: self.proceed(True), False)
            return False
        if self.MetadataProgress.IsFinished:
            self.currentPage = 1
            if self.forceAutoPage:
                show_report("   > Terminating Auto Paging",
                                "All %d notes have been processed and forceAutoPage is True" % self.MetadataProgress.Total,
                                delay=5)
                self.auto_page_callback()
                return True
            elif col.conf.get(EVERNOTE.PAGING_RESTART_WHEN_COMPLETE, True):
                restart = EVERNOTE.PAGING_RESTART_INTERVAL
                restart_title = "   > Restarting Auto Paging"
                restart_msg = "All %d notes have been processed and EVERNOTE.PAGING_RESTART_WHEN_COMPLETE is TRUE<BR>" % \
                              self.MetadataProgress.Total
                suffix = "Per EVERNOTE.PAGING_RESTART_INTERVAL, "
            else:
                show_report("   > Completed Auto Paging",
                                "All %d notes have been processed and EVERNOTE.PAGING_RESTART_WHEN_COMPLETE is FALSE" %
                                self.MetadataProgress.Total, delay=5)
                return True
        else:  # Paging still in progress
            self.currentPage = self.MetadataProgress.Page + 1
            restart_title = "   > Continuing Auto Paging"
            restart_msg = "Page %d completed. <BR>%d notes remain. <BR>%d of %d notes have been processed" % (
                self.MetadataProgress.Page, self.MetadataProgress.Remaining, self.MetadataProgress.Completed,
                self.MetadataProgress.Total)
            restart = 0
            if self.forceAutoPage:
                suffix = "<BR>Not delaying as the forceAutoPage flag is set"
            elif self.ImportProgress.APICallCount < EVERNOTE.PAGING_RESTART_DELAY_MINIMUM_API_CALLS:
                suffix = "<BR>Not delaying as the API Call Count of %d is less than the minimum of %d set by EVERNOTE.PAGING_RESTART_DELAY_MINIMUM_API_CALLS" % (
                self.ImportProgress.APICallCount, EVERNOTE.PAGING_RESTART_DELAY_MINIMUM_API_CALLS)
            else:
                restart = EVERNOTE.PAGING_TIMER_INTERVAL
                suffix = "<BR>Delaying Auto Paging: Per EVERNOTE.PAGING_TIMER_INTERVAL, "

        if not self.forceAutoPage:
            col.conf[SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE] = self.currentPage
            col.setMod()
            col.save()

        if restart > 0:
            m, s = divmod(restart, 60)
            suffix += "will delay for %d:%02d min before continuing\n" % (m, s)
        show_report(restart_title, (restart_msg + suffix).split('<BR>'), delay=5)
        if restart > 0:
            mw.progress.timer(restart * 1000, lambda: self.proceed(True), False)
            return False
        return self.proceed(True)

    @property
    def autoPagingEnabled(self):
        return self.anki.collection().conf.get(SETTINGS.EVERNOTE_AUTO_PAGING, True) or self.forceAutoPage
