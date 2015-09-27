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
# load_time = datetime.now()
# log("Loaded controller at " + load_time.isoformat(), 'import')
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
		did_break=True
		notes_created, notes_updated, queries1, queries2 = ([] for i in range(4))
		"""
		:type: (list[EvernoteNote], list[EvernoteNote], list[str], list[str])
		"""
		noteFetcher = EvernoteNoteFetcher()
		tmr = stopwatch.Timer(len(dbRows), 25, "Upload of Validated Evernote Notes", automated=automated, enabled=EVERNOTE.UPLOAD.ENABLED, max_allowed=EVERNOTE.UPLOAD.MAX, display_initial_info=True)
		if tmr.actionInitializationFailed: return tmr.status, 0, 0
		for dbRow in dbRows:
			entry = EvernoteValidationEntry(dbRow)
			evernote_guid, rootTitle, contents, tagNames, notebookGuid = entry.items()
			tagNames = tagNames.split(',')		
			if not tmr.checkLimits(): break 
			whole_note = tmr.autoStep(self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, guid=evernote_guid, validated=True), rootTitle, evernote_guid)
			if tmr.report_result == False: raise ValueError
			if tmr.status.IsDelayableError: break
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
		else: did_break=False			
		tmr.Report(self.anki.add_evernote_notes(notes_created) if tmr.counts.created else 0, self.anki.update_evernote_notes(notes_updated) if tmr.counts.updated else 0)
		if tmr.counts.created.anki: ankDB().executemany("DELETE FROM %s WHERE title = ? and contents = ? " % TABLES.NOTE_VALIDATION_QUEUE, queries2)            
		if tmr.counts.updated.anki: ankDB().executemany("DELETE FROM %s WHERE guid = ? " % TABLES.NOTE_VALIDATION_QUEUE, queries1)		
		if tmr.is_success: ankDB().commit()
		if did_break and tmr.status != EvernoteAPIStatus.ExceededLocalLimit: mw.progress.timer((30 if tmr.status.IsDelayableError else EVERNOTE.UPLOAD.RESTART_INTERVAL) * 1000, lambda: self.upload_validated_notes(True), False)	
		return tmr.status, tmr.counts, 0

	def create_auto_toc(self):
		def check_old_values():			
			old_values = ankDB().first(
				"SELECT guid, content FROM %s WHERE UPPER(title) = ? AND tagNames LIKE '%%,' || ? || ',%%'" % TABLES.EVERNOTE.NOTES,
				rootTitle.upper(), TAGS.AUTO_TOC)		
			if not old_values: 
				log(rootTitle, 'AutoTOC-Create\\Add')				
				return None, contents
			evernote_guid, old_content = old_values
			# log(['old contents exist', old_values is None, old_values, evernote_guid, old_content])
			noteBodyUnencoded = self.evernote.makeNoteBody(contents, encode=False)
			if type(old_content) != type(noteBodyUnencoded):
				log([rootTitle, type(old_content), type(noteBodyUnencoded)], 'AutoTOC-Create\\Update\\Diffs\\_')
				raise UnicodeWarning
			old_content = old_content.replace('guid-pending', evernote_guid).replace("'", '"')
			noteBodyUnencoded = noteBodyUnencoded.replace('guid-pending', evernote_guid).replace("'", '"')
			if old_content == noteBodyUnencoded:
				log(rootTitle, 'AutoTOC-Create\\Skipped')		
				tmr.reportSkipped()
				return None, None 
			log(noteBodyUnencoded, 'AutoTOC-Create\\Update\\New\\'+rootTitle, clear=True)
			log(generate_diff(old_content, noteBodyUnencoded), 'AutoTOC-Create\\Update\\Diffs\\'+rootTitle, clear=True)		
			return evernote_guid, contents.replace('/guid-pending/', '/%s/' % evernote_guid).replace('/guid-pending/', '/%s/' % evernote_guid)
		
		update_regex()
		NotesDB = EvernoteNotes()
		NotesDB.baseQuery = ANKNOTES.HIERARCHY.ROOT_TITLES_BASE_QUERY
		dbRows = NotesDB.populateAllNonCustomRootNotes()
		notes_created, notes_updated = [], []
		"""
		:type: (list[EvernoteNote], list[EvernoteNote])
		"""
		info = stopwatch.ActionInfo('Creation of Table of Content Note(s)', row_source='Root Title(s)', enabled=EVERNOTE.UPLOAD.ENABLED)
		tmr = stopwatch.Timer(len(dbRows), 25, info, max_allowed=EVERNOTE.UPLOAD.MAX)	
		tmr.label = 'create-auto_toc'		
		if tmr.actionInitializationFailed: return tmr.tmr.status, 0, 0
		for dbRow in dbRows:
			evernote_guid = None
			rootTitle, contents, tagNames, notebookGuid = dbRow.items()
			tagNames = (set(tagNames[1:-1].split(',')) | {TAGS.TOC, TAGS.AUTO_TOC} |  ({"#Sandbox"} if EVERNOTE.API.IS_SANDBOXED else set())) - {TAGS.REVERSIBLE, TAGS.REVERSE_ONLY}
			rootTitle = generateTOCTitle(rootTitle)			
			evernote_guid, contents = check_old_values()
			if contents is None: continue 
			if not tmr.checkLimits(): break 
			whole_note = tmr.autoStep(self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, guid=evernote_guid), rootTitle, evernote_guid)
			if tmr.report_result == False: raise ValueError
			if tmr.status.IsDelayableError: break
			if not tmr.status.IsSuccess: continue 
			(notes_updated if evernote_guid else notes_created).append(EvernoteNotePrototype(whole_note=whole_note))
		tmr.Report(self.anki.add_evernote_notes(notes_created) if tmr.counts.created.completed else 0, self.anki.update_evernote_notes(notes_updated) if tmr.counts.updated.completed else 0)
		if tmr.counts.queued: ankDB().commit()
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
		evernote_guids = get_all_local_db_guids() 
		results = self.evernote.create_evernote_notes(evernote_guids, use_local_db_only=True)        
		""":type: EvernoteNoteFetcherResults"""
		show_report('Resync with Local DB: Starting Anki Update of %d Note(s)' % len(evernote_guids))
		number = self.anki.update_evernote_notes(results.Notes, log_update_if_unchanged=False)
		tooltip = '%d Evernote Notes Created<BR>%d Anki Notes Successfully Updated' % (results.Local, number)
		show_report('Resync with Local DB Complete')
