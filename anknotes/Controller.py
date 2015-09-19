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
from anknotes.EvernoteNoteFetcher import EvernoteNoteFetcher
from anknotes import settings
from anknotes.EvernoteImporter import EvernoteImporter

### Evernote Imports 
from anknotes.evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from anknotes.evernote.edam.type.ttypes import NoteSortOrder, Note as EvernoteNote
from anknotes.evernote.edam.error.ttypes import EDAMSystemException

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
        fields = {
            FIELDS.TITLE:                                           title,
            FIELDS.CONTENT:                                         file(
                os.path.join(ANKNOTES.FOLDER_LOGS, filename.replace('.enex', '') + ".enex"),
                'r').read(), FIELDS.EVERNOTE_GUID:                  FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid
            }
        tags = ['NoTags', 'NoTagsToRemove']
        return AnkiNotePrototype(self.anki, fields, tags)

    def process_unadded_see_also_notes(self):
        update_regex()
        anki_note_ids = self.anki.get_anknotes_note_ids_with_unadded_see_also()
        self.evernote.getNoteCount = 0
        self.anki.process_see_also_content(anki_note_ids)

    def upload_validated_notes(self, automated=False):
        self.anki.evernoteTags = []
        dbRows = ankDB().all("SELECT * FROM %s WHERE validation_status = 1 " % TABLES.MAKE_NOTE_QUEUE)
        number_updated = 0
        number_created = 0
        count = 0
        count_create = 0
        count_update = 0
        exist = 0
        error = 0
        status = EvernoteAPIStatus.Uninitialized
        notes_created = []
        """
        :type: list[EvernoteNote]
        """
        notes_updated = []
        """
        :type: list[EvernoteNote]
        """
        queries1 = []
        queries2 = []
        noteFetcher = EvernoteNoteFetcher()
        SIMULATE = False
        if len(dbRows) == 0:
            if not automated:
                show_report("   > Upload of Validated Notes Aborted", "No Qualifying Validated Notes Found")
            return
        else:
            log("   > Upload of Validated Notes Initiated", "%d Successfully Validated Notes Found" % len(dbRows))

        for dbRow in dbRows:
            entry = EvernoteValidationEntry(dbRow)
            evernote_guid, rootTitle, contents, tagNames, notebookGuid = entry.items()
            tagNames = tagNames.split(',')
            if not ANKNOTES.UPLOAD_AUTO_TOC_NOTES or (
                            ANKNOTES.AUTO_TOC_NOTES_MAX > -1 and count_update + count_create >= ANKNOTES.AUTO_TOC_NOTES_MAX):
                continue
            if SIMULATE:
                status = EvernoteAPIStatus.Success
            else:
                status, whole_note = self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, guid=evernote_guid,
                                                        validated=True)
            if status.IsError:
                error += 1
                if status == EvernoteAPIStatus.RateLimitError or status == EvernoteAPIStatus.SocketError:
                    break
                else:
                    continue
            count += 1
            if status.IsSuccess:
                if not SIMULATE:
                    noteFetcher.addNoteFromServerToDB(whole_note, tagNames)
                    note = EvernoteNotePrototype(whole_note=whole_note, tags=tagNames)
                if evernote_guid:
                    if not SIMULATE:
                        notes_updated.append(note)
                    queries1.append([evernote_guid])
                    count_update += 1
                else:
                    if not SIMULATE:
                        notes_created.append(note)
                    queries2.append([rootTitle, contents])
                    count_create += 1
        if not SIMULATE and count_update + count_create > 0:
            number_updated = self.anki.update_evernote_notes(notes_updated)
            number_created = self.anki.add_evernote_notes(notes_created)
        count_max = len(dbRows)

        str_tip_header = "%s Validated Note(s) successfully generated." % counts_as_str(count, count_max)
        str_tips = []
        if count_create: str_tips.append("%s Validated Note(s) were newly created " % counts_as_str(count_create))
        if number_created: str_tips.append("-%-3d of these were successfully added to Anki " % number_created)
        if count_update: str_tips.append("%s Validated Note(s) already exist in local db and were updated" % counts_as_str(count_update))
        if number_updated: str_tips.append("-%-3d of these were successfully updated in Anki " % number_updated)
        if error > 0: str_tips.append("%d Error(s) occurred " % error)
        show_report("   > Upload of Validated Notes Complete", str_tip_header, str_tips)

        if len(queries1) > 0:
            ankDB().executemany("DELETE FROM %s WHERE guid = ? " % TABLES.MAKE_NOTE_QUEUE, queries1)
        if len(queries2) > 0:
            ankDB().executemany("DELETE FROM %s WHERE title = ? and contents = ? " % TABLES.MAKE_NOTE_QUEUE, queries2)
        # log(queries1)

        ankDB().commit()
        return status, count, exist

    def create_auto_toc(self):
        update_regex()
        self.anki.evernoteTags = []
        NotesDB = EvernoteNotes()
        NotesDB.baseQuery = ANKNOTES.ROOT_TITLES_BASE_QUERY
        dbRows = NotesDB.populateAllNonCustomRootNotes()
        # dbRows = NoteDB.populateAllPotentialRootNotes()
        number_updated = 0
        number_created = 0
        count = 0
        count_create = 0
        count_update = 0
        count_update_skipped = 0
        count_queued = 0
        count_queued_create = 0
        count_queued_update = 0
        exist = 0
        error = 0
        status = EvernoteAPIStatus.Uninitialized
        notes_created = []
        """
        :type: list[EvernoteNote]
        """
        notes_updated = []
        """
        :type: list[EvernoteNote]
        """
        if len(dbRows) == 0:
            show_report("   > TOC Creation Aborted", 'No Qualifying Root Titles Found')
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
            old_values = ankDB().first(
                "SELECT guid, content FROM %s WHERE UPPER(title) = ? AND tagNames LIKE '%%,' || ? || ',%%'" % TABLES.EVERNOTE.NOTES,
                rootTitle.upper(), EVERNOTE.TAG.AUTO_TOC)
            evernote_guid = None
            # noteBody = self.evernote.makeNoteBody(contents, encode=True)

            noteBodyUnencoded = self.evernote.makeNoteBody(contents, encode=False)
            if old_values:
                evernote_guid, old_content = old_values
                if type(old_content) != type(noteBodyUnencoded):
                    log([rootTitle, type(old_content), type(noteBody)], 'AutoTOC-Create-Diffs\\_')
                    raise UnicodeWarning
                old_content = old_content.replace('guid-pending', evernote_guid)
                noteBodyUnencoded = noteBodyUnencoded.replace('guid-pending', evernote_guid)
                if old_content == noteBodyUnencoded:
                    count += 1
                    count_update_skipped += 1
                    continue
                contents = contents.replace('/guid-pending/', '/%s/' % evernote_guid).replace('/guid-pending/', '/%s/' % evernote_guid)
                log(generate_diff(old_content, noteBodyUnencoded), 'AutoTOC-Create-Diffs\\'+rootTitle)
            if not ANKNOTES.UPLOAD_AUTO_TOC_NOTES or (
                            ANKNOTES.AUTO_TOC_NOTES_MAX > -1 and count_update + count_create >= ANKNOTES.AUTO_TOC_NOTES_MAX):
                continue
            status, whole_note = self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, guid=evernote_guid)
            if status.IsError:
                error += 1
                if status == EvernoteAPIStatus.RateLimitError or status == EvernoteAPIStatus.SocketError:
                    break
                else:
                    continue
            if status == EvernoteAPIStatus.RequestQueued:
                count_queued += 1
                if old_values: count_queued_update += 1
                else: count_queued_create += 1
                continue
            count += 1
            if status.IsSuccess:
                note = EvernoteNotePrototype(whole_note=whole_note, tags=tagNames)
                if evernote_guid:
                    notes_updated.append(note)
                    count_update += 1
                else:
                    notes_created.append(note)
                    count_create += 1
        if count_update + count_create > 0:
            number_updated = self.anki.update_evernote_notes(notes_updated)
            number_created = self.anki.add_evernote_notes(notes_created)
        count_total = count + count_queued
        count_max = len(dbRows)
        str_tip_header = "%s Auto TOC note(s) successfully generated" % counts_as_str(count_total, count_max)
        str_tips = []
        if count_create: str_tips.append("%-3d Auto TOC note(s) were newly created " % count_create)
        if number_created: str_tips.append("-%d of these were successfully added to Anki " % number_created)
        if count_queued_create: str_tips.append("-%s Auto TOC note(s) are brand new and and were queued to be added to Anki " % counts_as_str(count_queued_create))
        if count_update: str_tips.append("%-3d Auto TOC note(s) already exist in local db and were updated" % count_update)
        if number_updated: str_tips.append("-%s of these were successfully updated in Anki " % counts_as_str(number_updated))
        if count_queued_update:  str_tips.append("-%s Auto TOC note(s) already exist in local db and were queued to be updated in Anki" % counts_as_str(count_queued_update))
        if count_update_skipped: str_tips.append("-%s Auto TOC note(s) already exist in local db and were unchanged" % counts_as_str(count_update_skipped))
        if error > 0: str_tips.append("%d Error(s) occurred " % error)
        show_report("   > TOC Creation Complete: ", str_tip_header, str_tips)

        if count_queued > 0:
            ankDB().commit()

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
        if not hasattr(self, 'currentPage'):
            self.currentPage = 1
        self.evernoteImporter.currentPage = self.currentPage
        if hasattr(self, 'ManualGUIDs'):
            self.evernoteImporter.ManualGUIDs = self.ManualGUIDs
        self.evernoteImporter.proceed(auto_paging)

    def resync_with_local_db(self):
        evernote_guids = get_all_local_db_guids()
        result = self.evernote.create_evernote_notes(evernote_guids, use_local_db_only=True)
        """:type: (int, int, list[EvernoteNote])"""
        status, local_count, notes = result
        number = self.anki.update_evernote_notes(notes, log_update_if_unchanged=False)
        tooltip = '%d Entries in Local DB<BR>%d Evernote Notes Created<BR>%d Anki Notes Successfully Updated' % (
            len(evernote_guids), local_count, number)
        show_report('Resync with Local DB Complete', tooltip)
