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
import ankShared, ankConsts as ank, ankEvernote as EN 
from ankShared import *
try: from aqt import mw
except: pass

def get_self_referential_fmap():
    fmap = {}
    for i in range(0, len(ank.FIELDS_LIST)):
        fmap[i] = i
    return fmap     
    
class AnkiNotePrototype:
    fields = {}
    tags = []
    evernoteTagsToRemove = []
    model_name = ""    
    evernote_guid = ""
    cloze_count = 0
    original_evernote_guid = None
                
    def __init__(self, anki, fields, tags, evernoteTagsToRemove = None, baseNote = None, notebookGuid = None):
        self.anki = anki 
        self.fields = fields
        self.baseNote = baseNote        
        self.initialize_fields()                
        self.evernote_guid = get_evernote_guid_from_anki_fields(fields)
        self.notebookGuid = notebookGuid
        
        if not self.notebookGuid:
            self.notebookGuid = self.anki.get_notebook_guid_from_ankdb(self.evernote_guid)
        assert self.evernote_guid and self.notebookGuid
        self.deck_parent = self.anki.deck
        self.tags = tags 
        if not evernoteTagsToRemove: 
            self.evernoteTagsToRemove = self.anki.evernoteTags
        else:
            self.evernoteTagsToRemove = evernoteTagsToRemove
        self.cloze_count = 0
        self.model_name = ank.MODELS.EVERNOTE_DEFAULT         
        self.process_note()
    
    def initialize_fields(self):
        if self.baseNote:           
            self.originalFields = get_dict_from_list(self.baseNote.items())  
        for field in ank.FIELDS_LIST:
            if not field in self.fields:
                self.fields[field] = self.originalFields[field] if self.baseNote else u''
                
    def deck(self):
        if ank.EVERNOTE.TAG.TOC in self.tags:
            deck = self.deck_parent + DECK_TOC     
        elif ank.EVERNOTE.TAG.OUTLINE in self.tags and ank.EVERNOTE.TAG.OUTLINE_TESTABLE not in self.tags:
            deck = self.deck_parent + DECK_OUTLINE
        elif not self.deck_parent or mw.col.conf.get(ank.SETTINGS.USE_EVERNOTE_NOTEBOOK_NAME_FOR_ANKI_DECK_NAME, True):  
                deck = self.anki.get_deck_name_from_evernote_notebook(self.notebookGuid, self.deck_parent)        
                if not deck: return None
        if deck[:2] == '::':
            deck = deck[2:]    
        return deck 
    
    def evernote_cloze_regex(self, match):
        matchText = match.group(1)    
        if matchText[0] == "#":
            matchText = matchText[1:]
        else:
            self.cloze_count += 1    
        if self.cloze_count == 0:
            self.cloze_count = 1
        return "{{c%d::%s}}" % (self.cloze_count, matchText)

    def process_note_see_also(self):
        if not ank.FIELDS.SEE_ALSO in self.fields or not ank.FIELDS.EVERNOTE_GUID in self.fields:
            return         
        ankDB().execute("DELETE FROM %s WHERE source_evernote_guid = '%s' " % (ank.TABLES.SEE_ALSO, self.evernote_guid))
        link_num = 0
        for match in find_evernote_links(self.fields[ank.FIELDS.SEE_ALSO]):
            link_num += 1
            title_text = strip_tags(match.group('Title'))
            is_toc = 1 if (title_text == "TOC") else 0
            is_outline = 1 if (title_text is "O" or title_text is "Outline") else 0
            ankDB().execute("INSERT INTO %s (source_evernote_guid, number, uid, shard, target_evernote_guid, html, title, from_toc, is_toc, is_outline) VALUES('%s', %d, %d, '%s', '%s', '%s', '%s', 0, %d, %d)" % (ank.TABLES.SEE_ALSO, self.evernote_guid,link_num, int(match.group('uid')), match.group('shard'), match.group('guid'), match.group('Title'), title_text, is_toc, is_outline))
            
    def process_note_content(self):    
        if not ank.FIELDS.CONTENT in self.fields:
            return 
        content = self.fields[ank.FIELDS.CONTENT]
        if not ankShared.regex_see_also:
            update_regex()
        
        ################################### Step 0: Correct weird Evernote formatting 
        content = content.replace('margin: 0px; padding: 0px 0px 0px 40px; color: rgb(0, 0, 0); font-family: Tahoma; font-style: normal; font-variant: normal; font-weight: normal; letter-spacing: normal; orphans: 2; text-align: -webkit-auto; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-size-adjust: auto; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); font-size: medium;', '').replace('color: rgb(0, 0, 0); font-family: Tahoma; font-style: normal; font-variant: normal; letter-spacing: normal; orphans: 2; text-align: -webkit-auto; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-size-adjust: auto; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); font-size: medium;', '').replace(' style=""', '')
        
        ################################### Step 1: Modify Evernote Links
        # We need to modify Evernote's "Classic" Style Note Links due to an Anki bug with executing the evernote command with three forward slashes.
        # For whatever reason, Anki cannot handle evernote links with three forward slashes, but *can* handle links with two forward slashes.
        content = content.replace("evernote:///", "evernote://")
        
        # Modify Evernote's "New" Style Note links that point to the Evernote website. Normally these links open the note using Evernote's web client.
        # The web client then opens the local Evernote executable. Modifying the links as below will skip this step and open the note directly using the local Evernote executable
        content = re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([\w\d\-]+)', r'evernote://view/\2/\1/\3/\3/', content)
        
        ################################### Step 2: Modify Image Links        
        # Currently anknotes does not support rendering images embedded into an Evernote note. 
        # As a work around, this code will convert any link to an image on Dropbox, to an embedded <img> tag. 
        # This code modifies the Dropbox link so it links to a raw image file rather than an interstitial web page
        # Step 2.1: Modify HTML links to Dropbox images
        dropbox_image_url_regex = r'(?P<URL>https://www.dropbox.com/s/[\w\d]+/.+\.(jpg|png|jpeg|gif|bmp))(?P<QueryString>(?:\?dl=(?:0|1))?)'
        dropbox_image_src_subst = r'<a href="\g<URL>}\g<QueryString>}" shape="rect"><img src="\g<URL>?raw=1" alt="Dropbox Link %s Automatically Generated by Anknotes" /></a>'
        content = re.sub(r'<a href="%s".*?>(?P<Title>.+?)</a>' % dropbox_image_url_regex, dropbox_image_src_subst % "'\g<Title>'", content)
        
        # Step 2.2: Modify Plain-text links to Dropbox images
        try:
            dropbox_image_url_regex = dropbox_image_url_regex.replace('(?P<QueryString>(?:\?dl=(?:0|1))?)', '(?P<QueryString>\?dl=(?:0|1))')
            content = re.sub(dropbox_image_url_regex, dropbox_image_src_subst % "From Plain-Text Link", content)
        except:
            log_error("\nERROR processing note, Step 2.2.  Content: %s" % content)
        
        # Step 2.3: Modify HTML links with the inner text of exactly "(Image Link)"
        content = re.sub(r'<a href="(?P<URL>.+)"[^>]+>(?P<Title>\(Image Link.*\))</a>', 
        r'''<img src="\g<URL>" alt="'\g<Title>' Automatically Generated by Anknotes" /> <BR><a href="\g<URL>">\g<Title></a>''', content)
        
        ################################### Step 3: Change white text to transparent 
        # I currently use white text in Evernote to display information that I want to be initially hidden, but visible when desired by selecting the white text.
        # We will change the white text to a special "occluded" CSS class so it can be visible on the back of cards, and also so we can adjust the color for the front of cards when using night mode
        content = content.replace('<span style="color: rgb(255, 255, 255);">', '<span class="occluded">')
        
        ################################### Step 4: Automatically Occlude Text in <<Double Angle Brackets>>
        content = re.sub(r'&lt;&lt;(.+?)&gt;&gt;', r'&lt;&lt;<span class="occluded">$1</span>&gt;&gt;', content)    

        ################################### Step 5: Create Cloze fields from shorthand. Syntax is {Text}. Optionally {#Text} will prevent the Cloze # from incrementing.
        content = re.sub(r'{(.+?)}', self.evernote_cloze_regex, content)
        
        ################################### Step 6: Process "See Also: " Links
        see_also_match = ankShared.regex_see_also.search(content)        
        if see_also_match:
            log_dump(see_also_match.group('SeeAlso'), "-See Also match for Note '%s': %s" % (self.evernote_guid, self.fields[ank.FIELDS.TITLE]))
            content = content.replace(see_also_match.group(0), see_also_match.group('Suffix'))
            see_also = see_also_match.group('SeeAlso')
            see_also_header = see_also_match.group('SeeAlsoHeader')     
            see_also_header_stripme = see_also_match.group('SeeAlsoHeaderStripMe')
            if see_also_header_stripme:
                see_also = see_also.replace(see_also_header, see_also_header.replace(see_also_header_stripme, ''))
            if self.fields[ank.FIELDS.SEE_ALSO]:
                self.fields[ank.FIELDS.SEE_ALSO] += "<BR><BR>\r\n"
            self.fields[ank.FIELDS.SEE_ALSO] += see_also 
            self.process_note_see_also()
        
        # TODO: Add support for extracting an 'Extra' field from the Evernote Note contents        
        ################################### Note Processing complete. 
        self.fields[ank.FIELDS.CONTENT] = content
    
    def detect_note_model(self):
        delete_evernoteTagsToRemove = mw.col.conf.get(ank.SETTINGS.DELETE_EVERNOTE_TAGS_TO_IMPORT, True)
        if ank.FIELDS.CONTENT in self.fields and "{{c1::" in self.fields[ank.FIELDS.CONTENT]: 
            self.model_name = ank.MODELS.EVERNOTE_CLOZE
        elif ank.EVERNOTE.TAG.REVERSIBLE in self.tags: 
            self.model_name = ank.MODELS.EVERNOTE_REVERSIBLE
            if delete_evernoteTagsToRemove: self.tags.remove(ank.EVERNOTE.TAG.REVERSIBLE)
        elif ank.EVERNOTE.TAG.REVERSE_ONLY in self.tags: 
            model_name = ank.MODELS.EVERNOTE_REVERSE_ONLY
            if delete_evernoteTagsToRemove: self.tags.remove(ank.EVERNOTE.TAG.REVERSE_ONLY)    
    
    def model_id(self):
        return self.anki.models().byName(self.model_name)['id']
    
    def process_note(self):   
        self.process_note_content()                
        self.detect_note_model()

    def update_note_model(self):
        model_id = self.model_id()
        if self.note.mid is model_id:
            return False 
        mm = self.anki.models()
        modelOld =  self.note.model()
        modelNew =  mm.get(model_id)
        if modelOld['id'] == modelNew['id']:
            return False
        model_name = self.model_name   
        model_name_old = modelOld['name']
        fmap = get_self_referential_fmap()
        cmap = {0: 1 if model_name_old is ank.MODELS.EVERNOTE_REVERSE_ONLY and self.model_name is ank.MODELS.EVERNOTE_REVERSIBLE else 0}
        log("NID %d  cmap- %s" % (self.note.id, str(cmap)))
        log("Changing model:\n From: '%s' \n To:   '%s'" % (model_name_old, model_name  ), 'AddUpdateNote')    
        mm.change(modelOld, [self.note.id], modelNew, fmap, cmap)
        return True 
        
    def update_note_tags(self):
        value = u','.join(self.tags)
        value_original = u','.join(self.baseNote.tags)
        if str(value) == str(value_original):
            return False 
        log("Changing tags:\n From: '%s' \n To:   '%s'" % (value_original, value  ), 'AddUpdateNote')
        self.baseNote.tags = self.tags      
        return True 
        
    def update_note_deck(self):
        id_deck = self.anki.decks().id(self.deck())
        if id_deck is self.note.model()['did']:
            return False 
        flag_changed = True 
        log("Changing deck:\n From: '%s' \n To:   '%s'" % (self.anki.decks().nameOrNone(self.note.model()['did']), self.deck()  ), 'AddUpdateNote')
        # Not sure if this is necessary or Anki does it by itself:
        ankDB().execute("UPDATE cards SET did = ? WHERE nid = ?", id_deck, self.note.id)      
        return True 
       
    def update_note_fields(self):
        fields_to_update = [ank.FIELDS.TITLE, ank.FIELDS.CONTENT, ank.FIELDS.SEE_ALSO, ank.FIELDS.UPDATE_SEQUENCE_NUM]
        fld_content_ord = -1
        # log_dump({'self.note.fields': self.note.fields, 'self.note._model.flds': self.note._model['flds']}, "-      > UPDATE_NOTE → anki.notes.Note: _model: flds")        
        for fld in self.note._model['flds']:
            flag_changed = False
            if ank.FIELDS.EVERNOTE_GUID in fld.get('name'):
                self.original_evernote_guid = self.note.fields[fld.get('ord')].replace(ank.FIELDS.EVERNOTE_GUID_PREFIX, '')             
            for field_to_update in fields_to_update:                
                if field_to_update in fld.get('name') and field_to_update in self.fields:
                    if field_to_update is ank.FIELDS.CONTENT:
                        fld_content_ord = fld.get('ord')                
                    try:
                        value = self.fields[field_to_update]
                        value_original = self.note.fields[fld.get('ord')]                        
                        if isinstance(value , str):
                            value = unicode(value , 'utf-8')  
                        if isinstance(value_original , str):
                            value_original = unicode(value_original , 'utf-8')  
                        if not value == value_original:
                            flag_changed = True
                            self.note.fields[fld.get('ord')] = value
                            log("Changing field #%d %s:\n From: '%s' \n To:   '%s'" % (fld.get('ord'), field_to_update, value_original, value  ), 'AddUpdateNote')
                    except:
                        log_error("ERROR: UPDATE_NOTE: Note '%s': %s: Unable to set self.note.fields for field '%s'. Ord: %s. Note fields count: %d" % (self.evernote_guid, self.fields[ank.FIELDS.TITLE], field_to_update, str(fld.get('ord')), len(self.note.fields)) )
                        raise        
        if not fld_content_ord is -1:
            debug_fields = list(self.note.fields)
            del debug_fields[fld_content_ord]
            log_dump(debug_fields, "-      > UPDATE_NOTE → anki.notes.Note: ank.FIELDS ") 
        return flag_changed
    
    def update_note(self):
        col = self.anki.collection()
        self.note = self.baseNote
        
        if not self.update_note_tags() and not self.update_note_fields():
            log("Not updating Note '%s': no fields or tags have been changed" % self.evernote_guid)        
            return False 
        if not self.original_evernote_guid:
            flds = get_dict_from_list(self.baseNote.items())
            self.original_evernote_guid = get_evernote_guid_from_anki_fields(flds)
        db_title = ankDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (ank.TABLES.EVERNOTE.NOTES, self.original_evernote_guid))            
        log(' %s: UPDATE: ' % self.fields[ank.FIELDS.EVERNOTE_GUID].replace(ank.FIELDS.EVERNOTE_GUID_PREFIX, '') +'    ' + self.fields[ank.FIELDS.TITLE], 'AddUpdateNote')   
        if self.fields[ank.FIELDS.EVERNOTE_GUID].replace(ank.FIELDS.EVERNOTE_GUID_PREFIX, '') != self.original_evernote_guid or self.fields[ank.FIELDS.TITLE] != db_title:
            log(' %s:     DB: ' % self.original_evernote_guid +'    ' + db_title, 'AddUpdateNote')   
        self.note.flush()            
        self.update_note_model()
        return True
        
    def add_note(self):
        self.create_note()
        if self.note is not None:
            collection = self.anki.collection()
            db_title = ankDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (ank.TABLES.EVERNOTE.NOTES, self.fields[ank.FIELDS.EVERNOTE_GUID].replace(ank.FIELDS.EVERNOTE_GUID_PREFIX, '')))
            log(' %s:    ADD: ' % self.fields[ank.FIELDS.EVERNOTE_GUID].replace(ank.FIELDS.EVERNOTE_GUID_PREFIX, '') + '    ' + self.fields[ank.FIELDS.TITLE], 'AddUpdateNote')            
            if self.fields[ank.FIELDS.TITLE] != db_title:
                log(' %s:     DB: ' % re.sub(r'.', ' ', self.fields[ank.FIELDS.EVERNOTE_GUID].replace(ank.FIELDS.EVERNOTE_GUID_PREFIX, '')) + '    ' + db_title, 'AddUpdateNote')            
            try:
                collection.addNote(self.note)
            except:
                log_error("Unable to collection.addNote for Note %s:    %s" % (self.fields[ank.FIELDS.EVERNOTE_GUID].replace(ank.FIELDS.EVERNOTE_GUID_PREFIX, ''), db_title))
                log_dump(self.note.fields, '- FAILED collection.addNote: ')
                return -1
            collection.autosave()
            self.anki.start_editing()
            return self.note.id

    def create_note(self):
        id_deck = self.anki.decks().id(self.deck())
        model = self.anki.models().byName(self.model_name)
        col = self.anki.collection()
        self.note = anki.notes.Note(col, model)
        self.note.model()['did'] = id_deck
        self.note.tags = self.tags
        for name, value in self.fields.items():
            self.note[name] = value
