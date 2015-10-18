# -*- coding: utf-8 -*-
### Python Imports
import socket
from datetime import datetime

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.error import *

### Anknotes Class Imports
from anknotes.AnkiNotePrototype import AnkiNotePrototype
from anknotes.EvernoteNotePrototype import EvernoteNotePrototype
from anknotes.EvernoteNoteTitle import generateTOCTitle
from anknotes import stopwatch
### Anknotes Main Imports
from anknotes.Anki import Anki
from anknotes.ankEvernote import Evernote
from anknotes.EvernoteNotes import EvernoteNotes
from anknotes.EvernoteNoteFetcher import EvernoteNoteFetcher
from anknotes import settings
from anknotes.EvernoteImporter import EvernoteImporter

### Evernote Imports
from anknotes.evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from anknotes.evernote.edam.type.ttypes import NoteSortOrder, Note as EvernoteNote
from anknotes.evernote.edam.error.ttypes import EDAMSystemException

### Anki Imports
from aqt import mw


# load_time = datetime.now()
# log("Loaded controller at " + load_time.isoformat(), 'import')
class Controller:
    evernoteImporter = None
    """:type : EvernoteImporter"""

    def __init__(self):
        self.forceAutoPage = False
        self.auto_page_callback = None
        self.anki = Anki()
        self.anki.deck = SETTINGS.ANKI.DECKS.BASE.fetch()
        self.anki.setup_ancillary_files()
        ankDB().Init()
        self.anki.add_evernote_models()
        self.evernote = Evernote()

    def test_anki(self, title, evernote_guid, filename=""):
        if not filename:
            filename = title
        fields = {
            FIELDS.TITLE:                          title,
            FIELDS.CONTENT:                        file(
                os.path.join(FOLDERS.LOGS, filename.replace('.enex', '') + ".enex"),
                'r').read(), FIELDS.EVERNOTE_GUID: FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid
        }
        tags = ['NoTags', 'NoTagsToRemove']
        return AnkiNotePrototype(self.anki, fields, tags)

    def process_unadded_see_also_notes(self):
        update_regex()
        anki_note_ids = self.anki.get_anknotes_note_ids_with_unadded_see_also()
        self.evernote.getNoteCount = 0
        self.anki.process_see_also_content(anki_note_ids)

    def upload_validated_notes(self, automated=False):
        db = ankDB(TABLES.NOTE_VALIDATION_QUEUE)
        dbRows = db.all("validation_status = 1")
        notes_created, notes_updated, queries1, queries2 = ([] for i in range(4))
        """
        :type: (list[EvernoteNote], list[EvernoteNote], list[str], list[str])
        """
        noteFetcher = EvernoteNoteFetcher()
        tmr = stopwatch.Timer(len(dbRows), 25, infoStr="Upload of Validated Evernote Notes", automated=automated,
                              enabled=EVERNOTE.UPLOAD.ENABLED, max_allowed=EVERNOTE.UPLOAD.MAX,
                              label='Validation\\upload_validated_notes\\', display_initial_info=True)
        if tmr.actionInitializationFailed:
            return tmr.status, 0, 0
        for dbRow in dbRows:
            entry = EvernoteValidationEntry(dbRow)
            evernote_guid, rootTitle, contents, tagNames, notebookGuid, noteType = entry.items()
            tagNames = tagNames.split(',')
            if not tmr.checkLimits():
                break
            whole_note = tmr.autoStep(
                self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, guid=evernote_guid,
                                       noteType=noteType, validated=True), rootTitle, evernote_guid)
            if tmr.report_result is False:
                raise ValueError
            if tmr.status.IsDelayableError:
                break
            if not tmr.status.IsSuccess:
                continue
            if not whole_note.tagNames:
                whole_note.tagNames = tagNames
            noteFetcher.addNoteFromServerToDB(whole_note, tagNames)
            note = EvernoteNotePrototype(whole_note=whole_note)
            assert whole_note.tagNames
            assert note.Tags
            if evernote_guid:
                notes_updated.append(note)
                queries1.append([evernote_guid])
            else:
                notes_created.append(note)
                queries2.append([rootTitle, contents])
        else:
            tmr.reportNoBreak()
        tmr.Report(self.anki.add_evernote_notes(notes_created) if tmr.counts.created else 0,
                   self.anki.update_evernote_notes(notes_updated) if tmr.counts.updated else 0)
        if tmr.counts.created.completed.subcount:
            db.executemany("DELETE FROM {t} WHERE title = ? and contents = ? ", queries2)
        if tmr.counts.updated.completed.subcount:
            db.executemany("DELETE FROM {t} WHERE guid = ? ", queries1)
        if tmr.is_success:
            db.commit()
        if tmr.should_retry:
            create_timer(30 if tmr.status.IsDelayableError else EVERNOTE.UPLOAD.RESTART_INTERVAL,
                         self.upload_validated_notes, True)
        return tmr.status, tmr.count, 0

    def create_toc_auto(self):
        db = ankDB()
        def check_old_values():
            old_values = db.first("UPPER(title) = UPPER(?) AND tagNames LIKE '{t_tauto}'",
                                  rootTitle, columns='guid, content')
            if not old_values:
                log.go(rootTitle, 'Add')
                return None, contents
            evernote_guid, old_content = old_values
            noteBodyUnencoded = self.evernote.makeNoteBody(contents, encode=False)
            if type(old_content) != type(noteBodyUnencoded):
                log.go([rootTitle, type(old_content), type(noteBodyUnencoded)], 'Update\\Diffs\\_')
                raise UnicodeWarning
            old_content = old_content.replace('guid-pending', evernote_guid).replace("'", '"')
            noteBodyUnencoded = noteBodyUnencoded.replace('guid-pending', evernote_guid).replace("'", '"')
            if old_content == noteBodyUnencoded:
                log.go(rootTitle, 'Skipped')
                tmr.reportSkipped()
                return None, None
            log.go(noteBodyUnencoded, 'Update\\New\\' + rootTitle, clear=True)
            log.go(generate_diff(old_content, noteBodyUnencoded), 'Update\\Diffs\\' + rootTitle, clear=True)
            return evernote_guid, contents.replace(
                '/guid-pending/', '/%s/' % evernote_guid).replace('/guid-pending/', '/%s/' % evernote_guid)

        update_regex()
        noteType = 'create-toc_auto_notes'
        db.delete("noteType = '%s'" % noteType, table=TABLES.NOTE_VALIDATION_QUEUE)
        NotesDB = EvernoteNotes()
        NotesDB.baseQuery = ANKNOTES.HIERARCHY.ROOT_TITLES_BASE_QUERY
        dbRows = NotesDB.populateAllNonCustomRootNotes()
        notes_created, notes_updated = [], []
        """
        :type: (list[EvernoteNote], list[EvernoteNote])
        """
        info = stopwatch.ActionInfo('Creation of Table of Content Note(s)', row_source='Root Title(s)')
        log = Logger('See Also\\2-%s\\' % noteType, rm_path=True)
        tmr = stopwatch.Timer(len(dbRows), 25, info, max_allowed=EVERNOTE.UPLOAD.MAX,
                              label=log.base_path)
        if tmr.actionInitializationFailed:
            return tmr.status, 0, 0
        for dbRow in dbRows:
            rootTitle, contents, tagNames, notebookGuid = dbRow.items()
            tagNames = (set(tagNames[1:-1].split(',')) | {TAGS.TOC, TAGS.TOC_AUTO} | (
                {"#Sandbox"} if EVERNOTE.API.IS_SANDBOXED else set())) - {TAGS.REVERSIBLE, TAGS.REVERSE_ONLY}
            rootTitle = generateTOCTitle(rootTitle)
            evernote_guid, contents = check_old_values()
            if contents is None:
                continue
            if not tmr.checkLimits():
                break
            if not EVERNOTE.UPLOAD.ENABLED:
                tmr.reportStatus(EvernoteAPIStatus.Disabled, title=rootTitle)
                continue
            whole_note = tmr.autoStep(
                self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, noteType=noteType,
                                       guid=evernote_guid), rootTitle, evernote_guid)
            if tmr.report_result is False:
                raise ValueError
            if tmr.status.IsDelayableError:
                break
            if not tmr.status.IsSuccess:
                continue
            (notes_updated if evernote_guid else notes_created).append(EvernoteNotePrototype(whole_note=whole_note))
        tmr.Report(self.anki.add_evernote_notes(notes_created) if tmr.counts.created.completed else 0,
                   self.anki.update_evernote_notes(notes_updated) if tmr.counts.updated.completed else 0)
        if tmr.counts.queued:
            db.commit()
        return tmr.status, tmr.count, tmr.counts.skipped.val

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
        log_banner('Resync With Local DB', clear=False, append_newline=False, prepend_newline=True)
        evernote_guids = get_all_local_db_guids()
        tmr = stopwatch.Timer(evernote_guids, strInfo='Resync Notes From Local DB', label='resync_with_local_db\\')
        results = self.evernote.create_evernote_notes(evernote_guids, use_local_db_only=True)
        """:type: EvernoteNoteFetcherResults"""
        log('  > Finished Creating Evernote Notes: '.ljust(40) + tmr.str_long)
        tmr.reset()
        number = self.anki.update_evernote_notes(results.Notes, log_update_if_unchanged=False)
        log('  > Finished Updating Anki Notes: '.ljust(40) + tmr.str_long)
        tooltip = '%d Evernote Notes Created<BR>%d Anki Notes Successfully Updated' % (results.Local, number)
        show_report('  > Resync with Local DB Complete', tooltip)
