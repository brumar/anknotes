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
from toc import generateTOCTitle

### Anknotes Main Imports
from anknotes.Anki import Anki
from anknotes.ankEvernote import Evernote
from anknotes.EvernoteNotes import EvernoteNotes
from anknotes.EvernoteNotePrototype import EvernoteNotePrototype
from anknotes import settings
from anknotes.EvernoteImporter import EvernoteImporter

### Evernote Imports 
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.type.ttypes import NoteSortOrder, Note as EvernoteNote
from evernote.edam.error.ttypes import EDAMSystemException

### Anki Imports
from aqt import mw

DEBUG_RAISE_API_ERRORS = False


class Controller:
    evernoteImporter = None 
    """:type : EvernoteImporter"""
    
    def __init__(self):
        self.forceAutoPage = False
        self.auto_page_callback = None
        self.anki = Anki()
        self.anki.deck = mw.col.conf.get(SETTINGS.DEFAULT_ANKI_DECK, SETTINGS.DEFAULT_ANKI_DECK_DEFAULT_VALUE)
        self.anki.setup_ancillary_files()
        self.anki.add_evernote_models()
        ankDB().Init()
        self.evernote = Evernote()

    def test_anki(self, title, evernote_guid, filename=""):
        if not filename: filename = title
        fields = {FIELDS.TITLE: title,
                  FIELDS.CONTENT: file(os.path.join(ANKNOTES.FOLDER_LOGS, filename.replace('.enex', '') + ".enex"),
                                       'r').read(), FIELDS.EVERNOTE_GUID: FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid}
        tags = ['NoTags', 'NoTagsToRemove']
        return AnkiNotePrototype(self.anki, fields, tags)

    def process_unadded_see_also_notes(self):
        update_regex()
        anki_note_ids = self.anki.get_anknotes_note_ids_with_unadded_see_also()
        self.evernote.getNoteCount = 0
        self.anki.process_see_also_content(anki_note_ids)

    def create_auto_toc(self):
        update_regex()
        self.anki.evernoteTags = []
        NoteDB = EvernoteNotes()
        dbRows = NoteDB.populateAllNonCustomRootNotes()
        number_updated = 0
        number_created = 0
        count = 0
        count_create = 0
        count_update = 0
        count_update_skipped = 0
        exist = 0
        error = 0
        status = 0
        notes_created = []
        """
        :type: list[EvernoteNote]
        """
        notes_updated = []
        """
        :type: list[EvernoteNote]
        """
        if len(dbRows) == 0:
            report_tooltip("   > TOC Creation Aborted: No Qualifying Root Titles Found")
            return
        for dbRow in dbRows:
            rootTitle, contents, tagNames, notebookGuid = dbRow.items()
            tagNames = tagNames[1:-1].split(',')
            if EVERNOTE.TAG.REVERSIBLE in tagNames:
                tagNames.remove(EVERNOTE.TAG.REVERSIBLE)
            if EVERNOTE.TAG.REVERSE_ONLY in tagNames:
                tagNames.remove(EVERNOTE.TAG.REVERSE_ONLY)
            tagNames.append(EVERNOTE.TAG.TOC)
            tagNames.append(EVERNOTE.TAG.AUTO_TOC)
            if ANKNOTES.EVERNOTE_IS_SANDBOXED:
                tagNames.append("#Sandbox")
            rootTitle = generateTOCTitle(rootTitle)
            evernote_guid, old_content = ankDB().first(
                "SELECT guid, content FROM %s WHERE UPPER(title) = ? AND tagNames LIKE '%%,' || ? || ',%%'" % TABLES.EVERNOTE.NOTES,
                rootTitle.upper(), EVERNOTE.TAG.AUTO_TOC)
            noteBody = self.evernote.makeNoteBody(contents, encode=False)
            if evernote_guid:
                if old_content == noteBody:
                    count += 1
                    count_update_skipped += 1
                    continue
                log(generate_diff(old_content, noteBody), 'AutoTOC-Create-Diffs')
            if not ANKNOTES.UPLOAD_AUTO_TOC_NOTES or (
                            ANKNOTES.AUTO_TOC_NOTES_MAX > -1 and count_update + count_create > ANKNOTES.AUTO_TOC_NOTES_MAX):
                continue
            self.evernote.initialize_note_store()
            status, whole_note = self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, guid=evernote_guid)
            if not whole_note:
                error += 1
                if status == 1:
                    break
                else:
                    continue
            count += 1
            note = EvernoteNotePrototype(whole_note=whole_note, tags=tagNames)
            if evernote_guid:
                count_update += 1
                notes_updated.append(note)
            else:
                count_create += 1
                notes_created.append(note)
        if count_update + count_create > 0:
            number_updated = self.anki.update_evernote_notes(notes_updated)
            number_created = self.anki.add_evernote_notes(notes_created)

        str_tip = "%d of %d total Auto TOC note(s) successfully generated." % (count, len(dbRows))
        if count_create: str_tip += "<BR> --- %d Auto TOC note(s) were newly created " % count_create
        if number_created: str_tip += "<BR>       --- %d of these were successfully added to Anki " % number_created
        if count_update: str_tip += "<BR> --- %d Auto TOC note(s) already exist in local db and were updated" % count_update
        if number_updated: str_tip += "<BR>       --- %d of these were successfully updated in Anki " % number_updated
        if count_update_skipped: str_tip += "<BR> --- %d Auto TOC note(s) already exist in local db and were unchanged" % count_update_skipped
        if error > 0: str_tip += "<BR> --- %d error(s) occurred " % error
        report_tooltip("   > TOC Creation Complete", str_tip)
        return status, count, exist

    def update_ancillary_data(self):
        self.evernote.update_ancillary_data()

    def proceed(self, auto_paging=False):
        if not self.evernoteImporter:
            self.evernoteImporter = EvernoteImporter()
            self.evernoteImporter.anki = self.anki
            self.evernoteImporter.evernote = self.evernote
        self.evernoteImporter.forceAutoPage = self.forceAutoPage
        self.evernoteImporter.auto_page_callback = self.auto_page_callback
        self.evernoteImporter.currentPage = self.currentPage
        self.evernoteImporter.proceed(auto_paging)
 
    def proceed_full(self, auto_paging=False):
        global latestEDAMRateLimit, latestSocketError
        col = self.anki.collection()
        autoPagingEnabled = (col.conf.get(SETTINGS.EVERNOTE_AUTO_PAGING, True) or self.forceAutoPage)
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


        anki_note_ids = self.anki.get_anknotes_note_ids()
        anki_evernote_guids = self.anki.get_evernote_guids_from_anki_note_ids(anki_note_ids)

        status, MetadataProgress, server_evernote_guids, self.evernote.metadata = self.get_evernote_metadata()
        if status == EvernoteAPIStatus.RateLimitError:
            m, s = divmod(latestEDAMRateLimit, 60)
            report_tooltip("   > Error: Delaying Operation",
                           "Over the rate limit when searching for Evernote metadata<BR>Evernote requested we wait %d:%02d min" % (
                               m, s), delay=5)
            mw.progress.timer(latestEDAMRateLimit * 1000 + 10000, lambda: self.proceed(auto_paging), False)
            return False
        elif status == EvernoteAPIStatus.SocketError:
            report_tooltip("   > Error: Delaying Operation:",
                           "%s when searching for Evernote metadata<BR>We will try again in 30 seconds" %
                           latestSocketError['friendly_error_msg'], delay=5)
            mw.progress.timer(30000, lambda: self.proceed(auto_paging), False)
            return False

        ImportProgress = EvernoteImportProgress(self.anki, server_evernote_guids)
        ImportProgress.loadAlreadyUpdated(self.check_note_sync_status(ImportProgress.GUIDs.Updating))
        log("                                - " + ImportProgress.Summary + "\n", timestamp=False)
        
        
        
        self.anki.start_editing()                
        ImportProgress.processResults(self.import_into_anki(ImportProgress.GUIDs.Adding))
        if self.updateExistingNotes is UpdateExistingNotes.UpdateNotesInPlace:
            ImportProgress.processUpdateInPlaceResults(self.update_in_anki(ImportProgress.GUIDs.Updating))
        elif self.updateExistingNotes is UpdateExistingNotes.DeleteAndUpdate:
            self.anki.delete_anki_cards(ImportProgress.GUIDs.Updating)
            ImportProgress.processDeleteAndUpdateResults(self.import_into_anki(ImportProgress.GUIDs.Updating))
        report_tooltip("   > Import Complete", Import.ResultsSummary)
        self.anki.stop_editing()
        col.autosave()
        if not autoPagingEnabled:
            return 
            
        status = ImportProgress.Status
        restart = 0
        restart_msg = ""
        restart_title = None
        suffix = ""
        if status == EvernoteAPIStatus.RateLimitError:
            m, s = divmod(latestEDAMRateLimit, 60)
            report_tooltip("   > Error: Delaying Auto Paging",
                           "Over the rate limit when getting Evernote notes<BR>Evernote requested we wait %d:%02d min" % (
                               m, s), delay=5)
            mw.progress.timer(latestEDAMRateLimit * 1000 + 10000, lambda: self.proceed(True), False)
            return False
        if status == EvernoteAPIStatus.SocketError:
            report_tooltip("   > Error: Delaying Auto Paging:",
                           "%s when getting Evernote notes<BR>We will try again in 30 seconds" % latestSocketError[
                               'friendly_error_msg'], delay=5)
            mw.progress.timer(30000, lambda: self.proceed(True), False)
            return False
        if MetadataProgress.Completed:
            self.currentPage = 1
            if self.forceAutoPage:
                report_tooltip("   > Terminating Auto Paging",
                               "All %d notes have been processed and forceAutoPage is True" % MetadataProgress.Total,
                               delay=5)
                self.auto_page_callback()
            elif col.conf.get(EVERNOTE.PAGING_RESTART_WHEN_COMPLETE, True):
                restart = EVERNOTE.PAGING_RESTART_INTERVAL
                restart_title = "   > Restarting Auto Paging"
                restart_msg = "All %d notes have been processed and EVERNOTE.PAGING_RESTART_WHEN_COMPLETE is TRUE<BR>" % \
                              MetadataProgress.Total
                suffix = "Per EVERNOTE.PAGING_RESTART_INTERVAL, "
            else:
                report_tooltip("   > Terminating Auto Paging",
                               "All %d notes have been processed and EVERNOTE.PAGING_RESTART_WHEN_COMPLETE is FALSE" %
                               MetadataProgress.Total, delay=5)

        else:
            self.currentPage = MetadataProgress.Page + 1
            restart_title = "   > Initiating Auto Paging"
            restart_msg = "Page %d completed. <BR>%d notes remain. <BR>%d of %d notes have been processed<BR>" % (
                MetadataProgress.Page, MetadataProgress.Remaining, MetadataProgress.Completed, MetadataProgress.Total)
            if self.forceAutoPage or ImportProgress.APICallCount < EVERNOTE.PAGING_RESTART_DELAY_MINIMUM_API_CALLS:
                restart = 0
            else:
                restart = EVERNOTE.PAGING_TIMER_INTERVAL
                suffix = "Delaying Auto Paging: Per EVERNOTE.PAGING_TIMER_INTERVAL, "

        if not self.forceAutoPage:
            col.conf[SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE] = self.currentPage
            col.setMod()
            col.save()

        if restart_msg:
            if restart > 0:
                m, s = divmod(restart, 60)
                suffix += "will delay for %d:%02d min before continuing\n" % (m, s)
            report_tooltip(restart_title, restart_msg + suffix, delay=5)
            if restart > 0:
                mw.progress.timer(restart * 1000, lambda: self.proceed(True), False)
                return False
            else:
                return self.proceed(True)

    def resync_with_local_db(self):
        evernote_guids = get_all_local_db_guids()
        result = self.evernote.create_evernote_notes(evernote_guids, use_local_db_only=True)
        """:type: (int, int, list[EvernoteNote])"""
        status, local_count, notes = result
        number = self.anki.update_evernote_notes(notes, log_update_if_unchanged=False)
        tooltip = '%d Entries in Local DB<BR>%d Evernote Notes Created<BR>%d Anki Notes Successfully Updated' % (
            len(evernote_guids), local_count, number)
        report_tooltip('Resync with Local DB Complete', tooltip)
