# -*- coding: utf-8 -*-
### Python Imports
import socket

try:    from pysqlite2 import dbapi2 as sqlite
except ImportError: from sqlite3 import dbapi2 as sqlite

### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.error import HandleSocketError, HandleEDAMRateLimitError

### Anknotes Class Imports
from anknotes.AnkiNote import AnkiNotePrototype
import anknotes.EvernoteNotes as EN
from anknotes.toc import generateTOCTitle

### Anknotes Main Imports
from anknotes.Anki import Anki
from anknotes.Evernote import Evernote
from anknotes import settings

### Evernote Imports 
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.type.ttypes import NoteSortOrder
from evernote.edam.error.ttypes import EDAMSystemException

### Anki Imports
# noinspection PyUnresolvedReferences
from aqt import mw

DEBUG_RAISE_API_ERRORS = False    

class Controller:
    def __init__(self):        
        self.forceAutoPage = False
        self.auto_page_callback = None
        self.updateExistingNotes = mw.col.conf.get(SETTINGS.UPDATE_EXISTING_NOTES, UpdateExistingNotes.UpdateNotesInPlace)
        self.anki = Anki()        
        self.anki.deck = mw.col.conf.get(SETTINGS.DEFAULT_ANKI_DECK, SETTINGS.DEFAULT_ANKI_DECK_DEFAULT_VALUE)
        self.anki.setup_ancillary_files()        
        self.anki.add_evernote_models()        
        ankDB().Init()
        self.evernote = Evernote()             
    
    def test_anki(self, title, evernote_guid, filename = ""):
        if not filename: filename = title 
        fields = {FIELDS.TITLE: title, FIELDS.CONTENT: file( os.path.join(ANKNOTES.FOLDER_LOGS, filename.replace('.enex', '') + ".enex") , 'r').read(), FIELDS.EVERNOTE_GUID: FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid}
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
        NoteDB = EN.EvernoteNotes()
        NoteDB.baseQuery = "notebookGuid != 'fdccbccf-ee70-4069-a587-82772a96d9d3' AND notebookGuid != 'faabcd80-918f-49ca-a349-77fd0036c051'"
        dbRows = NoteDB.populateAllRootNotesMissingOrAutoTOC()    
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
        notes_updated = []
        if len(dbRows) == 0: 
            report_tooltip("   > TOC Creation Aborted: No Qualifying Root Titles Found")
            return 
        for dbRow in dbRows:
            rootTitle, contents, tagNames, notebookGuid = dbRow 
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
            # baseNote = None
            # whole_note = None
            evernote_guid, old_content = ankDB().first("SELECT guid, content FROM %s WHERE UPPER(title) = ? AND tagNames LIKE '%%,' || ? || ',%%'" % TABLES.EVERNOTE.NOTES, rootTitle.upper(), EVERNOTE.TAG.AUTO_TOC)
            # if evernote_guid:
                # baseNote = self.get_anki_note_from_evernote_guid(evernote_guid)
            # if evernote_guid: 
                # whole_note = self.evernote.updateNote(evernote_guid, rootTitle, contents, tagNames, notebookGuid)        
                # anki_field_info = [
                    # FIELDS.TITLE: rootTitle,
                    # FIELDS.CONTENT: contents,
                    # FIELDS.EVERNOTE_GUID: FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid
                # ]
                # anki_note_prototype = AnkiNotePrototype(self, anki_field_info, tagNames, baseNote, notebookGuid = notebookGuid, count=count, count_update = count_update, max_count=max_count)
            # else:
            noteBody = self.evernote.makeNoteBody(contents, encode=False)
            # noteBodyCompare = noteBody #.decode('utf-8')
            # old_contentCompare = old_content #.decode('utf-8')
            # eq = (noteBodyCompare == old_contentCompare)
            if evernote_guid:             
                if old_content == noteBody:
                    count += 1
                    count_update_skipped += 1 
                    continue       
                log(generate_diff(old_content, noteBody), 'AutoTOC-Create-Diffs')
            self.evernote.initialize_note_store()
            status, whole_note = self.evernote.makeNote(rootTitle, contents, tagNames, notebookGuid, guid=evernote_guid)                    
            if not whole_note:
                error += 1
                if status == 1:
                    break
                else:
                    continue
            count += 1 
            note = self.evernote.EvernoteNote(whole_note=whole_note,  tags=tagNames)                    
            if evernote_guid:
                count_update += 1 
                notes_updated.append(note)
            else:
                count_create += 1
                notes_created.append(note)
        
        if count_update + count_create > 0:
            # self.evernote.check_ancillary_data_up_to_date()
            # self.anki.notebook_data = self.evernote.notebook_data
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
        
    def check_note_sync_status(self, evernote_guids):
        notes_already_up_to_date = []
        for evernote_guid in evernote_guids:
            db_usn = ankDB().scalar("SELECT updateSequenceNum FROM %s WHERE guid = ?" % TABLES.EVERNOTE.NOTES, evernote_guid)            
            server_usn =  self.evernote.metadata[evernote_guid].updateSequenceNum
            if evernote_guid in self.anki.usns:
                current_usn = self.anki.usns[evernote_guid]                
                if current_usn == str(server_usn):
                    log_info = None # 'ANKI NOTE UP-TO-DATE'
                    notes_already_up_to_date.append(evernote_guid)
                elif str(db_usn) == str(server_usn):
                    log_info = 'DATABASE ENTRY UP-TO-DATE'
                else:
                    log_info = 'NO COPIES UP-TO-DATE'
            else:
                current_usn = 'N/A'
                log_info = 'NO ANKI USN EXISTS'
            if log_info:
                log("   > USN check for note '%s': %s: db/current/server = %s,%s,%s" % (evernote_guid, log_info, str(db_usn), str(current_usn), str(server_usn)), 'usn')        
        return notes_already_up_to_date
    
    def proceed(self, auto_paging = False):      
        global latestEDAMRateLimit
        autoPagingEnabled = (mw.col.conf.get(SETTINGS.EVERNOTE_AUTO_PAGING, True) or self.forceAutoPage)
        lastImport = mw.col.conf.get(SETTINGS.EVERNOTE_LAST_IMPORT, None)      
        mw.col.conf[SETTINGS.EVERNOTE_LAST_IMPORT] = datetime.now().strftime(ANKNOTES.DATE_FORMAT)
        mw.col.setMod()
        mw.col.save()
        lastImportStr = get_friendly_interval_string(lastImport)
        if lastImportStr:
            lastImportStr = ' [LAST IMPORT: %s]' % lastImportStr
        log("!  > Starting Evernote Import: Page #%d: %-60s%s" % (self.currentPage, settings.generate_evernote_query(), lastImportStr))       
        log("-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------", timestamp=False)
        if not auto_paging:
            if not hasattr(self.evernote, 'noteStore'):
                log("    > Note store does not exist. Aborting.")
                return False           
            self.evernote.getNoteCount = 0
        
        anki_note_ids = self.anki.get_anknotes_note_ids()
        anki_evernote_guids =  self.anki.get_evernote_guids_from_anki_note_ids(anki_note_ids)  
                
        status, counts, server_evernote_guids, self.evernote.metadata = self.get_evernote_metadata() 

        if status == 1:                       
            m, s = divmod(latestEDAMRateLimit, 60)
            log("   > Delaying operation for %d:%02d min. Over the rate limit when getting Evernote metadata") % (m, s)
            mw.progress.timer(latestEDAMRateLimit * 1000, lambda: self.proceed(auto_paging), False)   
            return False
        elif status == 2:
            log("   > Delaying operation. Blocking thread for 30s then retrying. Socket error when getting Evernote metadata")            
            mw.progress.timer(30000, lambda: self.proceed(auto_paging), False)   
            return False # self.proceed(auto_paging)
        
        notes_to_add = set(server_evernote_guids) - set(anki_evernote_guids)
        notes_to_update = set(server_evernote_guids) - set(notes_to_add)
        
        notes_already_up_to_date = set(self.check_note_sync_status(notes_to_update))
        notes_to_update = notes_to_update - notes_already_up_to_date
        
        log ("                                 - New Notes (%d)" % len(notes_to_add) + "    > Existing Out-Of-Date Notes (%d)" % len(notes_to_update) + "    > Existing Up-To-Date Notes (%d)\n" % len(notes_already_up_to_date))
        # log_dump(notes_to_add, "-    > New Notes (%d)" % len(notes_to_add), 'evernote_guids')
        # log_dump(notes_to_update, "-    > Existing Out-Of-Date Notes (%d)" % len(notes_to_update), 'evernote_guids')
        # log_dump(notes_already_up_to_date, "-    > Existing Up-To-Date Notes (%d)" % len(notes_already_up_to_date), 'evernote_guids')
        
        self.anki.start_editing()
        status, local_count_1, n = self.import_into_anki(notes_to_add)
        local_count_2 = 0
        n2 = 0
        n3 = 0
        status2 = 0
        if self.updateExistingNotes is UpdateExistingNotes.IgnoreExistingNotes:
            tooltip = "%d new note(s) have been imported. Updating is disabled.\n" % n        
        else:
            n2 = len(notes_to_update)
            n3 = len(notes_already_up_to_date)
            if self.updateExistingNotes is UpdateExistingNotes.UpdateNotesInPlace:
                update_str = "in-place"
                status2, local_count_2, n2_actual = self.update_in_anki(notes_to_update)
            else:
                update_str = "(deleted and re-added)"
                self.anki.delete_anki_cards(notes_to_update)
                status2, local_count_2, n2_actual = self.import_into_anki(notes_to_update)
            diff = n2 - n2_actual
            tooltip = "%d new note(s) have been imported and %d existing note(s) have been updated %s." % (n, n2, update_str)            
            if diff > 0:
                reason_str = ', for reasons unknown' if status2 == 0 else ', possibly because rate limits were reached' if status2 == 1 else ', possibly because network errors occurred'
                tooltip += "<BR>There is a discrepancy of %d note(s) that were not imported into Anki%s." % (n3, reason_str)
        api_call_count = (n - local_count_1) + (n2 - local_count_2)
        if local_count_1 > 0:
            tooltip += "<BR> --- %d new note(s) were unexpectedly found in the local db and did not require an API call." % local_count_1
            tooltip += "<BR> --- %d new note(s) required an API call" % (n - local_count_1)
        if local_count_2 > 0:
            tooltip += "<BR> --- %d existing note(s) were unexpectedly found in the local db and did not require an API call." % local_count_2   
            tooltip += "<BR> --- %d existing note(s) required an API call" % (n2 - local_count_2)        
        if len(notes_already_up_to_date) > 0:
                tooltip += "<BR>%d existing note(s) are already up-to-date with Evernote's servers, so they were not retrieved." % n3                
        
        report_tooltip("   > Import Complete", tooltip)        
        self.anki.stop_editing()
        self.anki.collection().autosave()
        
        if autoPagingEnabled:
            restart = 0
            restart_msg = ""
            restart_title=None
            suffix = ""
            if status == 1 or status2 == 1:
                m, s = divmod(latestEDAMRateLimit+10, 60)                
                report_tooltip("   > Delaying Auto Paging for %d:%02d min. Over the rate limit when getting Evernote metadata", delay=5) % (m, s)
                mw.progress.timer(latestEDAMRateLimit * 1000 + 10000, lambda: self.proceed(True), False)               
                return False 
            elif status == 2 or status2 == 2:
                report_tooltip("   > Delaying Auto Paging: Blocking thread for 30s then retrying. Socket error when getting Evernote notes", delay=5)
                mw.progress.timer(30000, lambda: self.proceed(True), False)   
                return False 
            elif counts['remaining'] <= 0:
                self.currentPage = 1
                if self.forceAutoPage:
                    report_tooltip("   > Terminating Auto Paging: All %d notes have been processed and forceAutoPage is True" % counts['total'], delay=5)
                    self.auto_page_callback()
                elif mw.col.conf.get(EVERNOTE.PAGING_RESTART_WHEN_COMPLETE, True):                    
                    restart = EVERNOTE.PAGING_RESTART_INTERVAL                    
                    restart_msg = "   > Restarting Auto Paging: All %d notes have been processed and EVERNOTE.PAGING_RESTART_WHEN_COMPLETE is TRUE\n" % counts['total']
                    suffix = "   - Per EVERNOTE.PAGING_RESTART_INTERVAL, "
                else:
                    report_tooltip("   > Terminating Auto Paging: All %d notes have been processed and EVERNOTE.PAGING_RESTART_WHEN_COMPLETE is FALSE" % counts['total'], delay=5)
                
            else:
                self.currentPage = counts['page'] + 1                
                restart_title = "   > Initiating Auto Paging: "
                restart_msg = "   - Page %d completed. \n   - %d notes remain. \n   - %d of %d notes have been processed\n" % (counts['page'], counts['remaining'], counts['completed'], counts['total'])
                if self.forceAutoPage or api_call_count < EVERNOTE.PAGING_RESTART_DELAY_MINIMUM_API_CALLS:
                    restart = 0
                else:
                    restart = EVERNOTE.PAGING_TIMER_INTERVAL
                    suffix = "   - Delaying Auto Paging: Per EVERNOTE.PAGING_TIMER_INTERVAL, "
            
            if not self.forceAutoPage:
                mw.col.conf[SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE] = self.currentPage
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

    def update_in_anki(self, evernote_guids):
        status, local_count, notes = self.evernote.create_evernote_notes(evernote_guids)
        self.anki.notebook_data = self.evernote.notebook_data
        number = self.anki.update_evernote_notes(notes)
        return status, local_count, number

    def import_into_anki(self, evernote_guids):
        status, local_count, notes = self.evernote.create_evernote_notes(evernote_guids)
        self.anki.notebook_data = self.evernote.notebook_data
        number = self.anki.add_evernote_notes(notes)
        return status, local_count, number
        
    def resync_with_local_db(self):
        evernote_guids = get_all_local_db_guids()
        status, local_count, notes = self.evernote.create_evernote_notes(evernote_guids, use_local_db_only=True)
        # self.anki.notebook_data = self.evernote.notebook_data
        number = self.anki.update_evernote_notes(notes, log_update_if_unchanged=False)
        tooltip = 'Resync with Local DB Complete.<BR>   - %d Entries in Local DB<BR>   - %d Evernote Notes Created<BR>   - %d Anki Notes Successfully Updated' % (len(evernote_guids), local_count, number)
        report_tooltip(tooltip)
    
    def get_evernote_metadata(self):
        notes_metadata = {}
        evernote_guids = []        
        query = settings.generate_evernote_query()
        evernote_filter = NoteFilter(words=query, ascending=True, order=NoteSortOrder.UPDATED)
        counts = {'page': int(self.currentPage), 'total': -1, 'current': -1}
        counts['offset'] = (counts['page'] - 1) * 250        
        spec = NotesMetadataResultSpec(includeTitle = False, includeUpdated = False, includeUpdateSequenceNum = True, includeTagGuids = True, includeNotebookGuid = True)     
        api_action_str = u'trying to search for note metadata'
        log_api("findNotesMetadata", "[Offset: %d]: Query: '%s'" % (counts['offset'], query))
        try:            
            result = self.evernote.noteStore.findNotesMetadata(self.evernote.token, evernote_filter, counts['offset'], EVERNOTE.METADATA_QUERY_LIMIT, spec)                           
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): 
                if DEBUG_RAISE_API_ERRORS: raise 
                return 1, counts, evernote_guids, notes_metadata
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): 
                if DEBUG_RAISE_API_ERRORS: raise 
                return 2, counts, evernote_guids, notes_metadata
            raise                 
        counts['total'] = int(result.totalNotes)
        counts['current'] = len(result.notes)
        counts['completed'] = counts['current'] + counts['offset']
        counts['remaining'] = counts['total'] - counts['completed']

        log("                                 - Metadata Results: Total Notes: %d  |    Returned Notes: %d    |   Result Range: %d-%d    |   Notes Remaining: %d    |   Update Count: %d " % (counts['total'], counts['current'],  counts['offset'], counts['completed'], counts['remaining'], result.updateCount), timestamp=False)
        for note in result.notes:
            evernote_guids.append(note.guid)
            notes_metadata[note.guid] = note
        return 3, counts, evernote_guids, notes_metadata

