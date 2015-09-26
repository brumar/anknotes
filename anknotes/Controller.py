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

DEBUG_RAISE_API_ERRORS = False


class Controller:
	evernoteImporter = None
	""":type : EvernoteImporter"""

	def __init__(self):
		self.forceAutoPage = False
		self.auto_page_callback = None
		self.anki = Anki()
		self.anki.deck = mw.col.conf.get(SETTINGS.ANKI.DECKS.BASE, SETTINGS.ANKI.DECKS.BASE_DEFAULT_VALUE)
		self.anki.setup_ancillary_files()
		ankDB().Init()
		self.anki.add_evernote_models()        
		self.evernote = Evernote()

	def test_anki(self, title, evernote_guid, filename=""):
		if not filename: filename = title
		fields = {
			FIELDS.TITLE:                                           title,
			FIELDS.CONTENT:                                         file(
				os.path.join(FOLDERS.LOGS, filename.replace('.enex', '') + ".enex"),
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
		dbRows = ankDB().all("SELECT * FROM %s WHERE validation_status = 1 " % TABLES.NOTE_VALIDATION_QUEUE)
		retry=True
		notes_created, notes_updated, queries1, queries2 = ([] for i in range(4))
		"""
		:type: (list[EvernoteNote], list[EvernoteNote], list[str], list[str])
		"""
		noteFetcher = EvernoteNoteFetcher()
		tmr = stopwatch.Timer(len(dbRows), 25, "Upload of Validated Evernote Notes")
		if tmr.actionInitializationFailed: return tmr.status, 0, 0
		if not EVERNOTE.UPLOAD.ENABLED: 
			tmr.info.ActionLine("Aborted", "EVERNOTE.UPLOAD.ENABLED is set to False")
			return EvernoteAPIStatus.Disabled
		for dbRow in dbRows:
			entry = EvernoteValidationEntry(dbRow)
			evernote_guid, rootTitle, contents, tagNames, notebookGuid = entry.items()
			tagNames = tagNames.split(',')						
			if -1 < EVERNOTE.UPLOAD.MAX <= count_update + count_create: 
				tmr.reportStatus(EvernoteAPIStatus.DelayedDueToRateLimit if EVERNOTE.UPLOAD.RESTART_INTERVAL > 0 else EvernoteAPIStatus.ExceededLocalLimit)
				log("upload_validated_notes: Count exceeded- Breaking with status " + str(tmr.status))
				break
			whole_note = tmr.autoStep(self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, guid=evernote_guid, validated=True), rootTitle, evernote_guid)
			if tmr.report_result == False: raise ValueError
			if tmr.status.IsDelayableError: 
				log("upload_validated_notes: Delayable error - breaking with status " + str(tmr.status))
				break 
			if not tmr.status.IsSuccess: continue 
			if not whole_note.tagNames: whole_note.tagNames = tagNames 
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
			retry=False
			log("upload_validated_notes: Did not break out of for loop")
		log("upload_validated_notes: Outside of the for loop ")
			
		tmr.Report(self.anki.add_evernote_notes(notes_created) if tmr.count_created else 0, self.anki.update_evernote_notes(notes_updated) if tmr.count_updated else 0)
		if tmr.subcount_created: ankDB().executemany("DELETE FROM %s WHERE title = ? and contents = ? " % TABLES.NOTE_VALIDATION_QUEUE, queries2)            
		if tmr.subcount_updated: ankDB().executemany("DELETE FROM %s WHERE guid = ? " % TABLES.NOTE_VALIDATION_QUEUE, queries1)		
		if tmr.is_success: ankDB().commit()
		if retry and tmr.status != EvernoteAPIStatus.ExceededLocalLimit: mw.progress.timer((30 if tmr.status.IsDelayableError else EVERNOTE.UPLOAD.RESTART_INTERVAL) * 1000, lambda: self.upload_validated_notes(True), False)	
		return tmr.status, tmr.count, 0

	def create_auto_toc(self):
		update_regex()
		NotesDB = EvernoteNotes()
		NotesDB.baseQuery = ANKNOTES.HIERARCHY.ROOT_TITLES_BASE_QUERY
		dbRows = NotesDB.populateAllNonCustomRootNotes()
		# number_updated = number_created = 0
		# count = count_create = count_update = count_update_skipped = 0
		# count_queued = count_queued_create = count_queued_update = 0
		# exist = error = 0
		# status = EvernoteAPIStatus.Uninitialized
		notes_created, notes_updated = [], []
		"""
		:type: (list[EvernoteNote], list[EvernoteNote])
		"""
		info = stopwatch.ActionInfo('Creation of Table of Content Note(s)', row_source='Root Title(s)')
		tmr = stopwatch.Timer(len(dbRows), 25, info)		
		if tmr.actionInitializationFailed: return tmr.status, 0, 0
		for dbRow in dbRows:
			rootTitle, contents, tagNames, notebookGuid = dbRow.items()
			tagNames = (set(tagNames[1:-1].split(',')) | {TAGS.TOC, TAGS.AUTO_TOC} |  ({"#Sandbox"} if EVERNOTE.API.IS_SANDBOXED else set())) - {TAGS.REVERSIBLE, TAGS.REVERSE_ONLY}
			rootTitle = generateTOCTitle(rootTitle)
			old_values = ankDB().first(
				"SELECT guid, content FROM %s WHERE UPPER(title) = ? AND tagNames LIKE '%%,' || ? || ',%%'" % TABLES.EVERNOTE.NOTES,
				rootTitle.upper(), TAGS.AUTO_TOC)
			evernote_guid = None
			noteBodyUnencoded = self.evernote.makeNoteBody(contents, encode=False)
			if old_values:
				evernote_guid, old_content = old_values
				if type(old_content) != type(noteBodyUnencoded):
					log([rootTitle, type(old_content), type(noteBodyUnencoded)], 'AutoTOC-Create-Diffs\\_')
					raise UnicodeWarning
				old_content = old_content.replace('guid-pending', evernote_guid)
				noteBodyUnencoded = noteBodyUnencoded.replace('guid-pending', evernote_guid)				
				if old_content == noteBodyUnencoded:
					tmr.report
					count += 1
					count_update_skipped += 1
					continue
				contents = contents.replace('/guid-pending/', '/%s/' % evernote_guid).replace('/guid-pending/', '/%s/' % evernote_guid)
				log(noteBodyUnencoded, 'AutoTOC-Create-New\\'+rootTitle, clear=True)
				log(generate_diff(old_content, noteBodyUnencoded), 'AutoTOC-Create-Diffs\\'+rootTitle, clear=True)
			if not EVERNOTE.UPLOAD.ENABLED or (
							-1 < EVERNOTE.UPLOAD.MAX <= count_update + count_create):
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
				note = EvernoteNotePrototype(whole_note=whole_note)
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
		results = self.evernote.create_evernote_notes(evernote_guids, use_local_db_only=True)        
		""":type: EvernoteNoteFetcherResults"""
		show_report('Resync with Local DB: Starting Anki Update of %d Note(s)' % len(evernote_guids))
		number = self.anki.update_evernote_notes(results.Notes, log_update_if_unchanged=False)
		tooltip = '%d Evernote Notes Created<BR>%d Anki Notes Successfully Updated' % (results.Local, number)
		show_report('Resync with Local DB Complete')
