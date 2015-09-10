# -*- coding: utf-8 -*-
import os
import os.path
import re
import pprint
from HTMLParser import HTMLParser
from datetime import datetime, timedelta
import shutil
import time
import errno
import socket
import copy
from ankEnums import AutoNumber, EvernoteTitleLevels
from ankAnki import AnkiNotePrototype
import ankShared, ankConsts as ank, ankEvernote as EN 
from ankShared import *
import ankSettings

from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.type.ttypes import NoteSortOrder
from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode
from evernote.api.client import EvernoteClient

import anki
import aqt
from anki.hooks import wrap
from aqt.preferences import Preferences
from aqt.utils import getText, openLink, getOnlyText
from aqt.qt import QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, SIGNAL, QCheckBox, \
QComboBox, QSpacerItem, QSizePolicy, QWidget, QSpinBox, QFormLayout, QGridLayout, QFrame, QPalette, \
QRect, QStackedLayout, QDateEdit, QDateTimeEdit, QTimeEdit, QDate, QDateTime, QTime, QPushButton, QIcon, QMessageBox, QPixmap
from aqt import mw

DEBUG_RAISE_API_ERRORS = False    
EDAM_RATE_LIMIT_ERROR_HANDLING = RateLimitErrorHandling.ToolTipError 

class Anki:        
    def __init__(self):
        self.templates = None

    def get_notebook_guid_from_ankdb(self, evernote_guid):
        return ankDB().scalar("SELECT notebookGuid FROM %s WHERE guid = '%s'" % (ank.TABLES.EVERNOTE.NOTES, evernote_guid))
        
    def get_deck_name_from_evernote_notebook(self, notebookGuid, deck=None):
        if not deck:
            deck = self.deck if self.deck else ""
        if not notebookGuid in self.notebook_data:
            log_error("Unexpected error: Notebook GUID '%s' could not be found in notebook data: %s" % (notebookGuid, str(self.notebook_data)))
            notebook = ankDB().first("SELECT name, stack FROM %s WHERE guid = '%s'" % (ank.TABLES.EVERNOTE.NOTEBOOKS, notebookGuid))
            if not notebook: 
                log_error("   get_deck_name_from_evernote_notebook FATAL ERROR: UNABLE TO FIND NOTEBOOK '%s'. " % notebookGuid)                        
                return None
            log("Getting notebook info: %s" % str(notebook))
            notebook_name, notebook_stack = notebook
            self.notebook_data[notebookGuid] = {"stack": notebook_stack, "name": notebook_name}
        notebook = self.notebook_data[notebookGuid]
        if notebook['stack']:
            deck += u'::' + notebook['stack']
        deck += "::" + notebook['name']
        deck = deck.replace(": ", "::")           
        if deck[:2] == '::':
            deck = deck[2:]
        return deck
        
    def update_evernote_notes(self, evernote_notes):
        return self.add_evernote_notes(evernote_notes, True)

    def add_evernote_notes(self, evernote_notes, update=False, evernote_tags_to_remove=None):
        count = 0
        for note in evernote_notes:
            try: 
                title = note.title
                content = note.content
                if isinstance(title , str):
                    title = unicode(title , 'utf-8')  
                if isinstance(content , str):
                    content = unicode(content , 'utf-8')  
                anki_field_info = {
                                   ank.FIELDS.TITLE: title,
                                   ank.FIELDS.CONTENT: content,
                                   ank.FIELDS.EVERNOTE_GUID: ank.FIELDS.EVERNOTE_GUID_PREFIX + note.guid,
                                   ank.FIELDS.UPDATE_SEQUENCE_NUM: str(note.updateSequenceNum),
                                   ank.FIELDS.SEE_ALSO: u''
                                   }
            except:
                log_error("Unable to set field info for: Note '%s': '%s'" % (note.title , note.guid ))
                log_dump(note.content, " NOTE CONTENTS ")
                log_dump(note.content.encode('utf-8'), " NOTE CONTENTS ")
                raise         
            baseNote = None
            if update:
                baseNote = self.get_anki_note_from_evernote_guid(note.guid)
                if not baseNote: log('Updating note %s: COULD NOT FIND ANKI NOTE ID' % (note.guid))
            anki_note_prototype = AnkiNotePrototype(self, anki_field_info, note.tags, evernote_tags_to_remove, baseNote, notebookGuid = note.notebookGuid)
            if update:
                debug_fields = anki_note_prototype.fields.copy()
                del debug_fields[ank.FIELDS.CONTENT]
                log_dump(debug_fields, "-      > UPDATE_evernote_notes → ADD_evernote_notes: anki_note_prototype: ank.FIELDS ")            
                if anki_note_prototype.update_note(): count += 1
            else:
                if not -1 == anki_note_prototype.add_note(): count += 1            
        return count

    def delete_anki_cards(self, evernote_guids):
        col = self.collection()
        card_ids = []
        for evernote_guid in evernote_guids:
            card_ids += mw.col.findCards(ank.FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid)
        col.remCards(card_ids)
        return len(card_ids)

    def add_evernote_model(self, mm, modelName, cloze=False):
        model = mm.byName(modelName)        
        if not model:            
            model = mm.new(modelName)
            templates = self.get_templates()
            
            # Add Field for Evernote GUID:
            #  Note that this field is first because Anki requires the first field to be unique
            evernote_guid_field = mm.newField(ank.FIELDS.EVERNOTE_GUID)
            evernote_guid_field['sticky'] = True
            evernote_guid_field['font'] = 'Consolas'
            evernote_guid_field['size'] = 10
            mm.addField(model, evernote_guid_field)  

            # Add Standard Fields:
            mm.addField(model, mm.newField(ank.FIELDS.TITLE))
            
            evernote_content_field = mm.newField(ank.FIELDS.CONTENT)
            evernote_content_field['size'] = 14
            mm.addField(model, evernote_content_field) 
            
            evernote_see_also_field = mm.newField(ank.FIELDS.SEE_ALSO)
            evernote_see_also_field['size'] = 14
            mm.addField(model, evernote_see_also_field)   
            
            evernote_extra_field = mm.newField(ank.FIELDS.EXTRA)
            evernote_extra_field['size'] = 12
            mm.addField(model, evernote_extra_field)  
            
            evernote_toc_field = mm.newField(ank.FIELDS.TOC)
            evernote_toc_field['size'] = 10
            mm.addField(model, evernote_toc_field)
            
            evernote_outline_field = mm.newField(ank.FIELDS.OUTLINE)
            evernote_outline_field['size'] = 10
            mm.addField(model, evernote_outline_field)
            
            # Add USN to keep track of changes vs Evernote's servers 
            evernote_usn_field = mm.newField(ank.FIELDS.UPDATE_SEQUENCE_NUM)
            evernote_usn_field['font'] = 'Consolas'
            evernote_usn_field['size'] = 10
            mm.addField(model, evernote_usn_field)
            
            # Add Templates
                
            if modelName is ank.MODELS.EVERNOTE_DEFAULT or modelName is ank.MODELS.EVERNOTE_REVERSIBLE:
                # Add Default Template
                default_template = mm.newTemplate(ank.TEMPLATES.EVERNOTE_DEFAULT)
                default_template['qfmt'] =  templates['Front']
                default_template['afmt'] =  templates['Back']
                mm.addTemplate(model, default_template)
            if modelName is ank.MODELS.EVERNOTE_REVERSE_ONLY or modelName is ank.MODELS.EVERNOTE_REVERSIBLE:
                # Add Reversed Template
                reversed_template = mm.newTemplate(ank.TEMPLATES.EVERNOTE_REVERSED)
                reversed_template['qfmt'] =  templates['Front']
                reversed_template['afmt'] =  templates['Back']
                mm.addTemplate(model, reversed_template)
            if modelName is ank.MODELS.EVERNOTE_CLOZE:
                # Add Cloze Template        
                cloze_template = mm.newTemplate(ank.TEMPLATES.EVERNOTE_CLOZE)
                cloze_template['qfmt'] =  templates['Front']
                cloze_template['afmt'] =  templates['Back']                
                mm.addTemplate(model, cloze_template)
                
            # Update Sort field to Title (By default set to GUID since it is the first field)
            model['sortf'] = 1
           
            # Update Model CSS
            model['css'] = '@import url("_AviAnkiCSS.css");'
            
            # Set Type to Cloze 
            if cloze:
                model['type'] = ank.MODELS.TYPE_CLOZE
            
            # Add Model to Collection
            mm.add(model)        
        
        # Add Model id to list
        self.evernoteModels[modelName] = model['id']

    def get_templates(self):                
        field_names = {"Title": ank.FIELDS.TITLE, "Content": ank.FIELDS.CONTENT, "Extra": ank.FIELDS.EXTRA, "See Also": ank.FIELDS.SEE_ALSO, "TOC": ank.FIELDS.TOC, "Outline": ank.FIELDS.OUTLINE, "Evernote GUID Prefix": ank.FIELDS.EVERNOTE_GUID_PREFIX, "Evernote GUID": ank.FIELDS.EVERNOTE_GUID}
        if not self.templates:
            # Generate Front and Back Templates from HTML Template in anknotes' addon directory
            self.templates = {"Front": file( ank.ANKNOTES.TEMPLATE_FRONT , 'r').read() % field_names } 
            self.templates["Back"] = self.templates["Front"].replace("<div id='Side-Front'>", "<div id='Side-Back'>")            
        return self.templates 
    
    def add_evernote_models(self):      
        col = self.collection()
        mm = col.models 
        self.evernoteModels = {}
        self.add_evernote_model(mm, ank.MODELS.EVERNOTE_DEFAULT)
        self.add_evernote_model(mm, ank.MODELS.EVERNOTE_REVERSE_ONLY)
        self.add_evernote_model(mm, ank.MODELS.EVERNOTE_REVERSIBLE)
        self.add_evernote_model(mm, ank.MODELS.EVERNOTE_CLOZE, True)
        
    def setup_ancillary_files(self):
        # Copy CSS file from anknotes addon directory to media directory 
        media_dir = re.sub("(?i)\.(anki2)$", ".media", self.collection().path)
        if isinstance(media_dir , str):
            media_dir = unicode(media_dir , sys.getfilesystemencoding())        
        shutil.copy2(os.path.join(ank.ANKNOTES.FOLDER_ANCILLARY, ank.ANKNOTES.CSS), os.path.join(media_dir, ank.ANKNOTES.CSS))            
        
    def get_anki_fields_from_anki_note_id(self, a_id, fields_to_ignore=list()):
        note = self.collection().getNote(a_id)
        try: items = note.items()   
        except:
            log_error("Unable to get note items for Note ID: %d" % a_id)
            raise        
        return get_dict_from_list(items, fields_to_ignore)     
    
    def get_evernote_guids_from_anki_note_ids(self, ids, process_usns=True):
        evernote_guids = []
        self.usns = {}
        for a_id in ids:
            fields = self.get_anki_fields_from_anki_note_id(a_id, [ank.FIELDS.CONTENT])  
            evernote_guid = get_evernote_guid_from_anki_fields(fields)
            if not evernote_guid: continue
            evernote_guids.append(evernote_guid)
            log('Anki USN for Note %s is %s' % (evernote_guid, fields[ank.FIELDS.UPDATE_SEQUENCE_NUM]), 'anki-usn')
            if ank.FIELDS.UPDATE_SEQUENCE_NUM in fields: self.usns[evernote_guid] = fields[ank.FIELDS.UPDATE_SEQUENCE_NUM]    
            else: log("   ! get_evernote_guids_from_anki_note_ids: Note '%s' is missing USN!" % evernote_guid)
        return evernote_guids           
    
    def get_evernote_guids_and_anki_fields_from_anki_note_ids(self, ids):
        evernote_guids = {}
        for a_id in ids:
            fields = self.get_anki_fields_from_anki_note_id(a_id)
            evernote_guid = get_evernote_guid_from_anki_fields(fields)
            if evernote_guid: evernote_guids[evernote_guid] = fields
        return evernote_guids             

    def search_evernote_models_query(self):        
        query = ""
        delimiter = ""
        for mName, mid in self.evernoteModels.items():
            query += delimiter + "mid:" + str(mid)
            delimiter = " OR "
        return query 
            
    def get_anknotes_note_ids(self, query_filter=""):
        query = self.search_evernote_models_query()
        if query_filter:
            query = query_filter + " (%s)" % query
        ids = self.collection().findNotes(query)
        return ids        
        
    def get_anki_note_from_evernote_guid(self, evernote_guid):
        col = self.collection()
        ids = col.findNotes(ank.FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid)        
        # TODO: Ugly work around for a bug. Fix this later
        if not ids: return None
        if not ids[0]: return None 
        note = anki.notes.Note(col, None, ids[0])
        return note
        
    def get_anknotes_note_ids_by_tag(self, tag):     
        return self.get_anknotes_note_ids("tag:" + tag)
        
    def get_anknotes_note_ids_with_unadded_see_also(self):     
        return self.get_anknotes_note_ids('"See Also" "See_Also:"')
        
    def process_see_also_content(self, anki_note_ids):
        for a_id in anki_note_ids:
            note = self.collection().getNote(a_id)
            try:
                items = note.items()   
            except:
                log_error("Unable to get note items for Note ID: %d" % a_id)
                raise
            fields = {}
            for key, value in items:             
                fields[key] = value
            if not fields[ank.FIELDS.SEE_ALSO]:
                anki_note_prototype = AnkiNotePrototype(self, fields, note.tags, [], note)                
                if anki_note_prototype.fields[ank.FIELDS.SEE_ALSO]:                
                    log("Detected see also contents for Note '%s': %s" % (get_evernote_guid_from_anki_fields(fields), fields[ank.FIELDS.TITLE]))
                    log(u" → %s " % strip_tags_and_new_lines(fields[ank.FIELDS.SEE_ALSO]))                    
                    anki_note_prototype.update_note()
        
    def process_toc_and_outlines(self):
        self.extract_links_from_toc()
        self.insert_toc_and_outline_contents_into_notes()        
        
    def extract_links_from_toc(self):
        toc_anki_ids = self.get_anknotes_note_ids_by_tag(ank.EVERNOTE.TAG.TOC)
        toc_evernote_guids = self.get_evernote_guids_and_anki_fields_from_anki_note_ids(toc_anki_ids)
        query_update_toc_links = "UPDATE %s SET is_toc = 1 WHERE " % ank.TABLES.SEE_ALSO
        delimiter = ""
        link_exists = 0
        for toc_evernote_guid, fields in toc_evernote_guids.items():
            for match in find_evernote_links(fields[ank.FIELDS.CONTENT]): 
                target_evernote_guid = match.group('guid')
                uid = int(match.group('uid'))
                shard = match.group('shard')
                if target_evernote_guid is toc_evernote_guid: continue 
                link_title = strip_tags(match.group('Title'))
                link_number = 1 + ankDB().scalar("select COUNT(*) from %s WHERE source_evernote_guid = '%s' " % (ank.TABLES.SEE_ALSO, target_evernote_guid))
                toc_link_title = fields[ank.FIELDS.TITLE]
                toc_link_html = '<span style="color: rgb(173, 0, 0);"><b>%s</b></span>' % toc_link_title
                query = """INSERT INTO `%s`(`source_evernote_guid`, `number`, `uid`, `shard`, `target_evernote_guid`, `html`, `title`, `from_toc`, `is_toc`)
SELECT '%s', %d, %d, '%s', '%s', '%s', '%s', 1, 1 FROM `%s` 
WHERE NOT EXISTS (SELECT * FROM `%s` 
      WHERE `source_evernote_guid`='%s' AND `target_evernote_guid`='%s') 
LIMIT 1 """ % (ank.TABLES.SEE_ALSO, target_evernote_guid, link_number, uid, shard,  toc_evernote_guid, toc_link_html.replace(u'\'', u'\'\''), toc_link_title.replace(u'\'', u'\'\''), ank.TABLES.SEE_ALSO, ank.TABLES.SEE_ALSO, target_evernote_guid, toc_evernote_guid)
                log_sql('UPDATE_ANKI_DB: Add See Also Link: SQL Query: ' + query)
                ankDB().execute(query)
            query_update_toc_links += delimiter + "target_evernote_guid = '%s'" % toc_evernote_guid
            delimiter = " OR "        
        ankDB().execute(query_update_toc_links)               
        
    def insert_toc_and_outline_contents_into_notes(self):    
        linked_notes_fields = {}
        for source_evernote_guid in ankDB().list("select DISTINCT source_evernote_guid from %s WHERE is_toc = 1 ORDER BY source_evernote_guid ASC" % ank.TABLES.SEE_ALSO):
            note = self.get_anki_note_from_evernote_guid(source_evernote_guid)
            if not note: continue
            if ank.EVERNOTE.TAG.TOC in note.tags: continue 
            for fld in note._model['flds']:
                if ank.FIELDS.TITLE in fld.get('name'):
                    note_title = note.fields[fld.get('ord')] 
                    continue 
            note_toc = ""
            note_outline = ""  
            toc_header = ""
            outline_header = ""
            toc_count = 0
            outline_count = 0
            for target_evernote_guid, is_toc, is_outline in ankDB().execute("select target_evernote_guid, is_toc, is_outline from %s WHERE source_evernote_guid = '%s' AND (is_toc = 1 OR is_outline = 1) ORDER BY number ASC" % (ank.TABLES.SEE_ALSO, source_evernote_guid)):    
                if target_evernote_guid in linked_notes_fields:
                    linked_note_contents = linked_notes_fields[target_evernote_guid][ank.FIELDS.CONTENT]
                    linked_note_title = linked_notes_fields[target_evernote_guid][ank.FIELDS.TITLE]
                else:                    
                    linked_note = self.get_anki_note_from_evernote_guid(target_evernote_guid)
                    if not linked_note: continue 
                    linked_note_contents = u""
                    for fld in linked_note._model['flds']:
                        if ank.FIELDS.CONTENT in fld.get('name'):
                            linked_note_contents = linked_note.fields[fld.get('ord')]                        
                        elif ank.FIELDS.TITLE in fld.get('name'):
                            linked_note_title = linked_note.fields[fld.get('ord')]                   
                    if linked_note_contents:
                        linked_notes_fields[target_evernote_guid] = {ank.FIELDS.TITLE: linked_note_title, ank.FIELDS.CONTENT: linked_note_contents}
                if linked_note_contents: 
                    if isinstance(linked_note_contents , str):
                        linked_note_contents = unicode(linked_note_contents , 'utf-8')                     
                    if (is_toc or is_outline) and (toc_count + outline_count is 0):
                        log("  > Found TOC/Outline for Note '%s': %s" % (source_evernote_guid, note_title), 'See Also')
                    if is_toc:      
                        toc_count += 1
                        if toc_count is 1:
                            toc_header = "<span class='header'>TABLE OF CONTENTS</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:                            
                            toc_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (toc_count, linked_note_title)
                            note_toc += "<BR><HR>"
                           
                        note_toc += linked_note_contents
                        log("   > Appending TOC #%d contents" % toc_count, 'See Also') 
                    else:
                        outline_count += 1
                        if outline_count is 1:
                            outline_header = "<span class='header'>OUTLINE</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:                            
                            outline_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (outline_count, linked_note_title)
                            note_outline += "<BR><HR>"
                           
                        note_outline += linked_note_contents
                        log("   > Appending Outline #%d contents" % outline_count, 'See Also') 
                        
            if outline_count + toc_count > 0:
                if outline_count > 1:
                    note_outline = "<span class='Outline'>%s</span><BR><BR>" % outline_header + note_outline                
                if toc_count > 1:
                    note_toc = "<span class='TOC'>%s</span><BR><BR>" % toc_header + note_toc            
                for fld in note._model['flds']:
                    if ank.FIELDS.TOC in fld.get('name'):
                        note.fields[fld.get('ord')] = note_toc
                    elif ank.FIELDS.OUTLINE in fld.get('name'):
                        note.fields[fld.get('ord')] = note_outline
                log(" > Flushing Note \r\n")
                note.flush()
            
    def start_editing(self):
        self.window().requireReset()

    def stop_editing(self):
        if self.collection():
            self.window().maybeReset()

    def window(self):
        return aqt.mw

    def collection(self):
        return self.window().col

    def models(self):
        return self.collection().models

    def decks(self):
        return self.collection().decks

class Evernote(object):
    class EvernoteNote:
        title = ""
        content = ""
        guid = ""
        updateSequenceNum = -1
        tags = []
        notebookGuid = ""
        status = -1
        
        def __init__(self, title=None, content=None, guid=None, tags=None, notebookGuid=None, updateSequenceNum=None, whole_note=None):
            self.status = -1
            self.tags = tags 
            if not whole_note is None:
                self.title = whole_note.title
                self.content = whole_note.content
                self.guid = whole_note.guid 
                self.notebookGuid = whole_note.notebookGuid
                self.updateSequenceNum = whole_note.updateSequenceNum                
                return
            self.title = title
            self.content = content
            self.guid = guid
            self.notebookGuid = notebookGuid
            self.updateSequenceNum = updateSequenceNum
            
    class EvernoteNoteFetcher(object):
        class EvernoteNoteFetcherResult(object):
            def __init__(self, note=None, status=-1, source=-1):
                self.note = note 
                self.status = status 
                self.source = source 
                
        def __init__(self, evernote, evernote_guid = None):
            self.result = self.EvernoteNoteFetcherResult()
            self.api_calls = 0
            self.keepEvernoteTags = True         
            self.evernote = evernote
            if not evernote_guid:
                self.evernote_guid = "" 
                self.updateSequenceNum = -1
                return             
            self.evernote_guid = evernote_guid 
            self.updateSequenceNum = self.evernote.metadata[self.evernote_guid].updateSequenceNum
            self.keepEvernoteTags = True 
            self.getNote()    
          
        def getNoteLocal(self):
            # Check Anknotes database for note
            db_note = ankDB().first("SELECT guid, title, content, notebookGuid, tagNames FROM %s WHERE guid = '%s' AND `updateSequenceNum` = %d" % (ank.TABLES.EVERNOTE.NOTES, self.evernote_guid, self.updateSequenceNum))
            if not db_note: return False
            note_guid, note_title, note_content, note_notebookGuid, note_tagNames = db_note
            log("  > getNoteLocal: Note '%s': '%s' has an up-to-date entry in the Anknotes db. Skipping API call and using db entry instead. " % (self.evernote_guid, note_title), 'api')
            self.tagNames = [] if not self.keepEvernoteTags else note_tagNames[1:-1].split(',')                   
            self.result.note = self.evernote.EvernoteNote(note_title, note_content, note_guid, self.tagNames, note_notebookGuid, self.updateSequenceNum)      
            assert self.result.note.guid == self.evernote_guid
            self.result.status = 0
            self.result.source = 1
            return True

        def addNoteFromServerToDB(self):
            # Note that values inserted into the db need to be converted from byte strings (utf-8) to unicode
            title = self.whole_note.title
            content = self.whole_note.content
            tag_names =  u',' + u','.join(self.tagNames).decode('utf-8') + u','
            if isinstance(title , str):
                title = unicode(title , 'utf-8')  
            if isinstance(content , str):
                content = unicode(content , 'utf-8') 
            if isinstance(tag_names , str):
                tag_names = unicode(tag_names , 'utf-8')  
            title = title.replace(u'\'', u'\'\'')
            content = content.replace(u'\'', u'\'\'')
            tag_names = tag_names.replace(u'\'', u'\'\'')
            sql_query = u'INSERT OR REPLACE INTO `%s`(`guid`,`title`,`content`,`updated`,`created`,`updateSequenceNum`,`notebookGuid`,`tagGuids`,`tagNames`) VALUES (\'%s\',\'%s\',\'%s\',%d,%d,%d,\'%s\',\'%s\',\'%s\');' % (ank.TABLES.EVERNOTE.NOTES, self.whole_note.guid.decode('utf-8'), title, content, self.whole_note.updated, self.whole_note.created, self.whole_note.updateSequenceNum, self.whole_note.notebookGuid.decode('utf-8'), u',' + u','.join(self.tagGuids).decode('utf-8') + u',', tag_names)
            log_sql('UPDATE_ANKI_DB: Add Note: SQL Query: ' + sql_query)
            ankDB().execute(sql_query)     
        
        def getNoteRemoteAPICall(self):
            api_action_str = u'trying to retrieve a note. We will save the notes downloaded thus far.'
            log(" ank.EVERNOTE.API_CALL: getNote: %3d: GUID: '%s'" % (self.api_calls + 1, self.evernote_guid), 'api')        
            try:                        
                self.whole_note = self.evernote.noteStore.getNote(self.evernote.token, self.evernote_guid, True, False, False, False)
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
            # if self.getNoteCount > ank.EVERNOTE.GET_NOTE_LIMIT: 
                # log("Aborting Evernote.getNoteRemote: ank.EVERNOTE.GET_NOTE_LIMIT of %d has been reached" % ank.EVERNOTE.GET_NOTE_LIMIT)
                # return None        
            if not self.getNoteRemoteAPICall(): return False 
            self.api_calls += 1
            self.tagGuids, self.tagNames = self.evernote.get_tag_names_from_evernote_guids(self.whole_note.tagGuids)
            self.addNoteFromServerToDB()
            if not self.keepEvernoteTags: self.tagNames = []
            self.result.note = self.evernote.EvernoteNote(whole_note=self.whole_note,  tags=self.tagNames)
            
            assert self.result.note.guid == self.evernote_guid
            return True

        def getNote(self, evernote_guid = None):
            if evernote_guid:
                self.result.note = None
                self.evernote_guid = evernote_guid 
                self.updateSequenceNum = self.evernote.metadata[self.evernote_guid].updateSequenceNum            
            if self.getNoteLocal(): return True 
            return self.getNoteRemote()        

    def __init__(self):
        auth_token = mw.col.conf.get(ank.SETTINGS.EVERNOTE_AUTH_TOKEN, False)
        self.keepEvernoteTags = mw.col.conf.get(ank.SETTINGS.KEEP_EVERNOTE_TAGS, ank.SETTINGS.KEEP_EVERNOTE_TAGS_DEFAULT_VALUE)
        self.tag_data = {}
        self.notebook_data = {}
        self.noteStore = None
        self.getNoteCount = 0
        
        if not auth_token:
            # First run of the Plugin we did not save the access key yet
            secrets = {'holycrepe': '36f46ea5dec83d4a', 'scriptkiddi-2682': '965f1873e4df583c'}
            client = EvernoteClient(
                consumer_key=ank.ANKNOTES.EVERNOTE_CONSUMER_KEY,
                consumer_secret=secrets[ank.ANKNOTES.EVERNOTE_CONSUMER_KEY],
                sandbox=ank.ANKNOTES.EVERNOTE_IS_SANDBOXED
            )
            request_token = client.get_request_token('https://fap-studios.de/anknotes/index.html')
            url = client.get_authorize_url(request_token)
            showInfo("We will open a Evernote Tab in your browser so you can allow access to your account")
            openLink(url)
            oauth_verifier = getText(prompt="Please copy the code that showed up, after allowing access, in here")[0]
            auth_token = client.get_access_token(
                request_token.get('oauth_token'),
                request_token.get('oauth_token_secret'),
                oauth_verifier)
            mw.col.conf[ank.SETTINGS.EVERNOTE_AUTH_TOKEN] = auth_token
        self.token = auth_token
        self.client = EvernoteClient(token=auth_token, sandbox=ank.ANKNOTES.EVERNOTE_IS_SANDBOXED)        

    def initialize_note_store(self):
        if self.noteStore: 
            return 0
        api_action_str = u'trying to initialize the Evernote Client.'
        log(" ank.EVERNOTE.API_CALL: get_note_store", 'api')
        try:            
            self.noteStore = self.client.get_note_store()                                  
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): 
                if DEBUG_RAISE_API_ERRORS: raise 
                return 1
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): 
                if DEBUG_RAISE_API_ERRORS: raise 
                return 2
            raise                         
        return 0
    
    def create_evernote_notes(self, evernote_guids = None):  
        if not hasattr(self, 'guids') or evernote_guids: self.evernote_guids = evernote_guids
        self.check_ancillary_data_up_to_date()        
        notes = []   
        fetcher = self.EvernoteNoteFetcher(self)
        fetcher.keepEvernoteTags = self.keepEvernoteTags
        local_count = 0
        for evernote_guid in self.evernote_guids:
            self.evernote_guid = evernote_guid 
            if not fetcher.getNote(evernote_guid): 
                return fetcher.result.status, local_count, notes     
            if fetcher.result.source is 1:
                local_count += 1
            notes.append(fetcher.result.note)
        return 0, local_count, notes
    
    def check_ancillary_data_up_to_date(self):
        if not self.check_tags_up_to_date(): 
            self.update_tags_db()
        if not self.check_notebooks_up_to_date(): 
            self.update_notebook_db()    
    
    def update_ancillary_data(self):
        self.update_tags_db()
        self.update_notebook_db()                
    
    def check_notebooks_up_to_date(self):        
        notebook_guids = []        
        for evernote_guid in self.evernote_guids:
            note_metadata = self.metadata[evernote_guid]
            notebookGuid = note_metadata.notebookGuid 
            if not notebookGuid:
                log_error("   > Notebook check: Unable to find notebook guid for '%s'. Returned '%s'. Metadata: %s" % (evernote_guid, str(notebookGuid), str(note_metadata)))
            elif not notebookGuid in notebook_guids and not notebookGuid in self.notebook_data:                
                notebook  = ankDB().first("SELECT name, stack FROM %s WHERE guid = '%s'" % (ank.TABLES.EVERNOTE.NOTEBOOKS, notebookGuid))
                if not notebook: 
                    log("   > Notebook check: Missing notebook guid '%s'. Will update with an API call." % notebookGuid)
                    return False
                notebook_name, notebook_stack = notebook
                self.notebook_data[notebookGuid] = {"stack": notebook_stack, "name": notebook_name}
                notebook_guids.append(notebookGuid)
        return True        
        
    def update_notebook_db(self):
        api_action_str = u'trying to update Evernote notebooks.'
        log(" ank.EVERNOTE.API_CALL: listNotebooks", 'api')
        try:            
            notebooks = self.noteStore.listNotebooks(self.token)                               
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): 
                if DEBUG_RAISE_API_ERRORS: raise 
                return None
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): 
                if DEBUG_RAISE_API_ERRORS: raise    
                return None
            raise       
        data = []
        for notebook in notebooks:
            self.notebook_data[notebook.guid] = {"stack": notebook.stack, "name": notebook.name}
            data.append([notebook.guid, notebook.name, notebook.updateSequenceNum, notebook.serviceUpdated, notebook.stack])
        ankDB().execute("DROP TABLE %s " % ank.TABLES.EVERNOTE.NOTEBOOKS)
        ankDB().InitNotebooks(True)
        log_dump(data, 'update_notebook_db table data')
        ankDB().executemany("INSERT INTO `%s`(`guid`,`name`,`updateSequenceNum`,`serviceUpdated`, `stack`) VALUES (?, ?, ?, ?, ?)" % ank.TABLES.EVERNOTE.NOTEBOOKS, data)  
        log_dump(ankDB().all("SELECT * FROM %s WHERE 1" % ank.TABLES.EVERNOTE.NOTEBOOKS), 'sql data')

    def check_tags_up_to_date(self):        
        tag_guids = []
        for evernote_guid in self.evernote_guids:
            if not evernote_guid in self.metadata:
                log_error('Could not find note metadata for Note ''%s''' % evernote_guid)
                return False
            else:            
                note_metadata = self.metadata[evernote_guid]            
                for tag_guid in note_metadata.tagGuids:                
                    if not tag_guid in tag_guids and not tag_guid in self.tag_data: 
                        tag_name = ankDB().scalar("SELECT name FROM %s WHERE guid = '%s'" % (ank.TABLES.EVERNOTE.TAGS, tag_guid))
                        if not tag_name: 
                            return False
                        self.tag_data[tag_guid] = tag_name 
                        tag_guids.append(tag_guid)   
        return True
       
    def update_tags_db(self):
        api_action_str = u'trying to update Evernote tags.'
        log(" ank.EVERNOTE.API_CALL: listTags", 'api')
        try:            
            tags = self.noteStore.listTags(self.token)                                
        except EDAMSystemException as e:
            if HandleEDAMRateLimitError(e, api_action_str): 
                if DEBUG_RAISE_API_ERRORS: raise 
                return None
            raise         
        except socket.error, v:
            if HandleSocketError(v, api_action_str): 
                if DEBUG_RAISE_API_ERRORS: raise 
                return None
            raise       
        data = []
        for tag in tags:
            self.tag_data[tag.guid] = tag.name
            data.append([tag.guid, tag.name, tag.parentGuid, tag.updateSequenceNum])
        ankDB().execute("DROP TABLE %s " % ank.TABLES.EVERNOTE.TAGS)
        ankDB().InitTags(True)
        ankDB().executemany("INSERT OR REPLACE INTO `%s`(`guid`,`name`,`parentGuid`,`updateSequenceNum`) VALUES (?, ?, ?, ?)" % ank.TABLES.EVERNOTE.TAGS, data)        
    
    def get_tag_names_from_evernote_guids(self, tag_guids_original):
        tagNames = []
        tagGuids = list(tag_guids_original)
        removeTagsToImport = mw.col.conf.get(ank.SETTINGS.DELETE_EVERNOTE_TAGS_TO_IMPORT, True)
        for tagGuid in tag_guids_original:
            tagName = self.tag_data[tagGuid]
            if removeTagsToImport and tagName in self.evernoteTags:
                tagGuids.remove(tagGuid)
            else:
                tagNames.append(tagName)                
        tagNames = sorted(tagNames, key=lambda s: s.lower())
        return tagGuids, tagNames     
        
class Controller:
    def __init__(self):
        self.evernoteTags = mw.col.conf.get(ank.SETTINGS.EVERNOTE_QUERY_TAGS, ank.SETTINGS.EVERNOTE_QUERY_TAGS_DEFAULT_VALUE).split(",")
        self.updateExistingNotes = mw.col.conf.get(ank.SETTINGS.UPDATE_EXISTING_NOTES, UpdateExistingNotes.UpdateNotesInPlace)
        self.anki = Anki()        
        self.anki.deck = mw.col.conf.get(ank.SETTINGS.DEFAULT_ANKI_DECK, ank.SETTINGS.DEFAULT_ANKI_DECK_DEFAULT_VALUE)
        self.anki.setup_ancillary_files()        
        self.anki.add_evernote_models()        
        ankDB().Init()
        self.evernote = Evernote()             
    
    def test_anki(self, title, evernote_guid, filename = ""):
        if not filename: filename = title 
        fields = {ank.FIELDS.TITLE: title, ank.FIELDS.CONTENT: file( os.path.join(ank.ANKNOTES.FOLDER_LOGS, filename.replace('.enex', '') + ".enex") , 'r').read(), ank.FIELDS.EVERNOTE_GUID: ank.FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid}
        tags = ['NoTags', 'NoTagsToRemove']
        en_tags = ['NoTagsToRemove']
        return AnkiNotePrototype(self.anki, fields, tags, en_tags)
   
    def process_toc(self):
        update_regex()
        anki_note_ids = self.anki.get_anknotes_note_ids_with_unadded_see_also()
        self.evernote.getNoteCount = 0        
        self.anki.process_see_also_content(anki_note_ids)
        self.anki.process_toc_and_outlines()        

    def update_ancillary_data(self):
        self.evernote.update_ancillary_data()
        
    def check_note_sync_status(self, evernote_guids):
        notes_already_up_to_date = []
        for evernote_guid in evernote_guids:
            db_usn = ankDB().scalar("SELECT updateSequenceNum FROM %s WHERE guid = ?" % ank.TABLES.EVERNOTE.NOTES, evernote_guid)            
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
        log("!  > Starting Evernote Import: Page #%d: %s" % (mw.col.conf.get(ank.SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE, 1), ankSettings.generate_evernote_query()))       
        if not auto_paging:
            if not hasattr(self.evernote, 'noteStore'):
                log("    > Note store does not exist. Aborting.")
                return False           
            self.anki.evernoteTags = self.evernoteTags 
            self.evernote.evernoteTags = self.evernoteTags
            self.evernote.getNoteCount = 0
        
        anki_note_ids = self.anki.get_anknotes_note_ids()
        anki_evernote_guids =  self.anki.get_evernote_guids_from_anki_note_ids(anki_note_ids)  
                
        status, counts, server_evernote_guids, self.evernote.metadata = self.get_evernote_metadata() 

        if status == 1:
            log("   > Aborting operation. Over the rate limit when getting Evernote metadata")
            return False
        elif status == 2:
            log("   > Delaying operation. Blocking thread for 30s then retrying. Socket error when getting Evernote metadata")            
            time.sleep(30)            
            return self.proceed(auto_paging)
        
        notes_to_add = set(server_evernote_guids) - set(anki_evernote_guids)
        notes_to_update = set(server_evernote_guids) - set(notes_to_add)
        
        notes_already_up_to_date = set(self.check_note_sync_status(notes_to_update))
        notes_to_update = notes_to_update - notes_already_up_to_date
        
        log ("          - New Notes (%d)" % len(notes_to_add) + "    > Existing Out-Of-Date Notes (%d)" % len(notes_to_update) + "    > Existing Up-To-Date Notes (%d)\n" % len(notes_already_up_to_date))
        log_dump(notes_to_add, "-    > New Notes (%d)" % len(notes_to_add), 'evernote_guids')
        log_dump(notes_to_update, "-    > Existing Out-Of-Date Notes (%d)" % len(notes_to_update), 'evernote_guids')
        log_dump(notes_already_up_to_date, "-    > Existing Up-To-Date Notes (%d)" % len(notes_already_up_to_date), 'evernote_guids')
        
        self.anki.start_editing()
        status, local_count_1, n = self.import_into_anki(notes_to_add)
        local_count_2 = 0
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
        if local_count_1 > 0:
            tooltip += "<BR> --- %d new note(s) were unexpectedly found in the local db and did not require an API call." % local_count_1
            tooltip += "<BR> --- %d new note(s) required an API call" % (n - local_count_1)
        if local_count_2 > 0:
            tooltip += "<BR> --- %d existing note(s) were unexpectedly found in the local db and did not require an API call." % local_count_2   
            tooltip += "<BR> --- %d existing note(s) required an API call" % (n2 - local_count_2)
        
        if len(notes_already_up_to_date) > 0:
                tooltip += "<BR>%d existing note(s) are already up-to-date with Evernote's servers, so they were not retrieved." % n3        
        
        show_tooltip(tooltip)
        log(("   > Import Complete: <BR>%s\n" % tooltip).replace('<BR><BR>', '<BR>').replace('<BR>', '\n   - ')) 
        self.anki.stop_editing()
        self.anki.collection().autosave()
        
        if mw.col.conf.get(ank.SETTINGS.EVERNOTE_AUTO_PAGING, True):         
            restart = 0
            restart_msg = ""
            suffix = ""
            if status == 1 or status2 == 1:
                log("   > Aborting Auto Paging: Over the rate limit when getting Evernote notes")
            elif status == 2 or status2 == 2:
                log("   > Delaying Auto Paging: Blocking thread for 30s then retrying. Socket error when getting Evernote notes")
                time.sleep(30)            
                return self.proceed(True)
            elif counts['remaining'] <= 0:
                mw.col.conf[ank.SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE] = 1
                if mw.col.conf.get(ank.EVERNOTE.PAGING_RESTART_WHEN_COMPLETE, True):                    
                    restart = ank.EVERNOTE.PAGING_RESTART_INTERVAL
                    restart_msg = "   > Restarting Auto Paging: All %d notes have been processed and ank.EVERNOTE.PAGING_RESTART_WHEN_COMPLETE is TRUE\n" % counts['total']
                    suffix = "   - Per ank.EVERNOTE.PAGING_RESTART_INTERVAL, "
                else:
                    log("   > Terminating Auto Paging: All %d notes have been processed and ank.EVERNOTE.PAGING_RESTART_WHEN_COMPLETE is FALSE" % counts['total'])
            else:
                mw.col.conf[ank.SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE] = counts['page'] + 1
                restart = ank.EVERNOTE.PAGING_TIMER_INTERVAL
                restart_msg = "   > Initiating Auto Paging: \n   - Page %d completed. \n   - %d notes remain. \n   - %d of %d notes have been processed\n" % (counts['page'], counts['remaining'], counts['completed'], counts['total'])
                suffix = "   - Delaying Auto Paging: Per ank.EVERNOTE.PAGING_TIMER_INTERVAL, "
            if restart_msg:                  
                if restart > 0:
                    m, s = divmod(restart, 60)
                    suffix += "will block thread for {} min before continuing\n".format("%d:%02d" %(m, s))     
                log(restart_msg + suffix)                
                if restart > 0:
                    time.sleep(restart)
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
    
    def get_evernote_metadata(self):
        notes_metadata = {}
        evernote_guids = []        
        query = ankSettings.generate_evernote_query()
        evernote_filter = NoteFilter(words=query, ascending=True, order=NoteSortOrder.UPDATED)
        counts = {'page': int(mw.col.conf.get(ank.SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE, 1)), 'total': -1, 'current': -1}
        counts['offset'] = (counts['page'] - 1) * 250        
        spec = NotesMetadataResultSpec(includeTitle = False, includeUpdated = False, includeUpdateSequenceNum = True, includeTagGuids = True, includeNotebookGuid = True)     
        api_action_str = u'trying to search for note metadata'
        log(" ank.EVERNOTE.API_CALL: findNotesMetadata: [Offset: %d]: Query: '%s'" % (counts['offset'], query), 'api')
        try:            
            result = self.evernote.noteStore.findNotesMetadata(self.evernote.token, evernote_filter, counts['offset'], ank.EVERNOTE.METADATA_QUERY_LIMIT, spec)                           
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

        log("          - Metadata Results: Total Notes: %d  |    Returned Notes: %d    |   Result Range: %d-%d    |   Notes Remaining: %d    |   Update Count: %d " % (counts['total'], counts['current'],  counts['offset'], counts['completed'], counts['remaining'], result.updateCount))
        for note in result.notes:
            evernote_guids.append(note.guid)
            notes_metadata[note.guid] = note
        return 3, counts, evernote_guids, notes_metadata

def show_tooltip(text, time_out=3000):
    aqt.utils.tooltip(text, time_out)

def main():
    controller = Controller()
    controller.evernote.initialize_note_store()
    controller.proceed()

def update_ancillary_data():
    controller = Controller()
    controller.evernote.initialize_note_store()
    controller.update_ancillary_data()    
    
def toc():
    controller = Controller()
    controller.process_toc()      
    

    
    
action = aqt.qt.QAction("&Import from Evernote", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), main)
aqt.mw.form.menuTools.addAction(action)

action = aqt.qt.QAction("Process Evernote &TOC [Power Users Only!]", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), toc)
aqt.mw.form.menuTools.addAction(action)

action = aqt.qt.QAction("Update Evernote Ancillary Data", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), update_ancillary_data)
aqt.mw.form.menuTools.addAction(action)

Preferences.setupOptions = wrap(Preferences.setupOptions, ankSettings.setup_evernote)