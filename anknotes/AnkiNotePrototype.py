# -*- coding: utf-8 -*-
### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.EvernoteNoteTitle import EvernoteNoteTitle

### Anki Imports
import anki
from anki.notes import Note as AnkiNote

try:
        from aqt import mw
except:
    pass


def get_self_referential_fmap():
    fmap = {}
    for i in range(0, len(FIELDS_LIST)):
        fmap[i] = i
    return fmap


class AnkiNotePrototype:
    Anki = None
    """:type : anknotes.Anki.Anki """
    BaseNote = None
    """:type : AnkiNote """
    Title = None
    """:type : EvernoteNoteTitle.EvernoteNoteTitle """
    Fields = {}
    """:type : dict[str, str]"""
    Tags = []
    """:type : list[str]"""
    ModelName = None
    """:type : str"""
    Guid = ""
    """:type : str"""
    NotebookGuid = ""
    """:type : str"""
    __cloze_count__ = 0
    class Counts:
        Updated = 0
        Current = 0
        Max = 1
    OriginalGuid = None
    """:type : str"""
    Changed = False
    _log_update_if_unchanged_ = True

    def __init__(self, anki, fields, tags, base_note=None, notebookGuid=None, count=-1, count_update=0,
                 max_count=1, counts=None):
        """
        Create Anki Note Prototype Class from fields or Base Anki Note
        :param anki: Anki: Anknotes Main Class Instance
        :type anki: anknotes.Anki.Anki
        :param fields: Dict of Fields
        :param tags: List of Tags
        :type tags : list[str]
        :param base_note: Base Anki Note if Updating an Existing Note
        :type base_note : anki.notes.Note
        :param notebookGuid:
        :param count:
        :param count_update:
        :param max_count:
        :param counts: AnkiNotePrototype.Counts if being used to add/update multiple notes
        :type counts :  AnkiNotePrototype.Counts
        :return: AnkiNotePrototype
        """

        self.Anki = anki
        self.Fields = fields
        self.BaseNote = base_note
        self.Changed = False
        self.logged = False
        if counts:
            self.Counts = counts
        else:
            self.Counts.Updated = count_update
            self.Counts.Current = count + 1
            self.Counts.Max = max_count
        self.initialize_fields()
        self.Guid = get_evernote_guid_from_anki_fields(fields)
        self.NotebookGuid = notebookGuid
        self.ModelName = None  # MODELS.EVERNOTE_DEFAULT
        self.Title = EvernoteNoteTitle()
        if not self.NotebookGuid:
            self.NotebookGuid = self.Anki.get_notebook_guid_from_ankdb(self.Guid)
        assert self.Guid and self.NotebookGuid
        self._deck_parent_ = self.Anki.deck
        self.Tags = tags
        self.__cloze_count__ = 0
        self.process_note()

    def initialize_fields(self):
        if self.BaseNote:
            self.originalFields = get_dict_from_list(self.BaseNote.items())
        for field in FIELDS_LIST:
            if not field in self.Fields:
                self.Fields[field] = self.originalFields[field] if self.BaseNote else u''
        self.Title = EvernoteNoteTitle(self.Fields)

    def deck(self):
        if EVERNOTE.TAG.TOC in self.Tags or EVERNOTE.TAG.AUTO_TOC in self.Tags:
            deck = self._deck_parent_ + DECKS.TOC_SUFFIX
        elif EVERNOTE.TAG.OUTLINE in self.Tags and EVERNOTE.TAG.OUTLINE_TESTABLE not in self.Tags:
            deck = self._deck_parent_ + DECKS.OUTLINE_SUFFIX
        elif not self._deck_parent_ or mw.col.conf.get(SETTINGS.ANKI_DECK_EVERNOTE_NOTEBOOK_INTEGRATION, True):
            deck = self.Anki.get_deck_name_from_evernote_notebook(self.NotebookGuid, self._deck_parent_)
            if not deck: return None
        if deck[:2] == '::':
            deck = deck[2:]
        return deck

    def evernote_cloze_regex(self, match):
        matchText = match.group(2)
        if matchText[0] == "#":
            matchText = matchText[1:]
        else:
            self.__cloze_count__ += 1
        if self.__cloze_count__ == 0:
            self.__cloze_count__ = 1
        return "%s{{c%d::%s}}%s" % (match.group(1), self.__cloze_count__, matchText, match.group(2))

    def process_note_see_also(self):
        if not FIELDS.SEE_ALSO in self.Fields or not FIELDS.EVERNOTE_GUID in self.Fields:
            return
        ankDB().execute("DELETE FROM %s WHERE source_evernote_guid = '%s' " % (TABLES.SEE_ALSO, self.Guid))
        link_num = 0
        for match in find_evernote_links(self.Fields[FIELDS.SEE_ALSO]):
            link_num += 1
            title_text = strip_tags(match.group('Title'))
            is_toc = 1 if (title_text == "TOC") else 0
            is_outline = 1 if (title_text is "O" or title_text is "Outline") else 0
            ankDB().execute(
                "INSERT INTO %s (source_evernote_guid, number, uid, shard, target_evernote_guid, html, title, from_toc, is_toc, is_outline) VALUES('%s', %d, %d, '%s', '%s', '%s', '%s', 0, %d, %d)" % (
                    TABLES.SEE_ALSO, self.Guid, link_num, int(match.group('uid')), match.group('shard'),
                    match.group('guid'), match.group('Title'), title_text, is_toc, is_outline))

    def process_note_content(self):
        if not FIELDS.CONTENT in self.Fields:
            return
        content = self.Fields[FIELDS.CONTENT]
        self.unprocessed_content = content
        self.unprocessed_see_also = self.Fields[FIELDS.SEE_ALSO]

        ################################### Step 0: Correct weird Evernote formatting 
        remove_style_attrs = '-webkit-text-size-adjust: auto|-webkit-text-stroke-width: 0px|background-color: rgb(255, 255, 255)|color: rgb(0, 0, 0)|font-family: Tahoma|font-size: medium;|font-style: normal|font-variant: normal|font-weight: normal|letter-spacing: normal|orphans: 2|text-align: -webkit-auto|text-indent: 0px|text-transform: none|white-space: normal|widows: 2|word-spacing: 0px'.replace(
            '(', '\\(').replace(')', '\\)')
        # 'margin: 0px; padding: 0px 0px 0px 40px; '
        content = re.sub(r' ?(%s);? ?' % remove_style_attrs, '', content)
        content = content.replace(' style=""', '')

        ################################### Step 1: Modify Evernote Links
        # We need to modify Evernote's "Classic" Style Note Links due to an Anki bug with executing the evernote command with three forward slashes.
        # For whatever reason, Anki cannot handle evernote links with three forward slashes, but *can* handle links with two forward slashes.
        content = content.replace("evernote:///", "evernote://")

        # Modify Evernote's "New" Style Note links that point to the Evernote website. Normally these links open the note using Evernote's web client.
        # The web client then opens the local Evernote executable. Modifying the links as below will skip this step and open the note directly using the local Evernote executable
        content = re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([\w\d\-]+)',
                         r'evernote://view/\2/\1/\3/\3/', content)

        ################################### Step 2: Modify Image Links        
        # Currently anknotes does not support rendering images embedded into an Evernote note. 
        # As a work around, this code will convert any link to an image on Dropbox, to an embedded <img> tag. 
        # This code modifies the Dropbox link so it links to a raw image file rather than an interstitial web page
        # Step 2.1: Modify HTML links to Dropbox images
        dropbox_image_url_regex = r'(?P<URL>https://www.dropbox.com/s/[\w\d]+/.+\.(jpg|png|jpeg|gif|bmp))(?P<QueryString>(?:\?dl=(?:0|1))?)'
        dropbox_image_src_subst = r'<a href="\g<URL>}\g<QueryString>}" shape="rect"><img src="\g<URL>?raw=1" alt="Dropbox Link %s Automatically Generated by Anknotes" /></a>'
        content = re.sub(r'<a href="%s".*?>(?P<Title>.+?)</a>' % dropbox_image_url_regex,
                         dropbox_image_src_subst % "'\g<Title>'", content)

        # Step 2.2: Modify Plain-text links to Dropbox images
        try:
            dropbox_image_url_regex = dropbox_image_url_regex.replace('(?P<QueryString>(?:\?dl=(?:0|1))?)',
                                                                      '(?P<QueryString>\?dl=(?:0|1))')
            content = re.sub(dropbox_image_url_regex, dropbox_image_src_subst % "From Plain-Text Link", content)
        except:
            log_error("\nERROR processing note, Step 2.2.  Content: %s" % content)

        # Step 2.3: Modify HTML links with the inner text of exactly "(Image Link)"
        content = re.sub(r'<a href="(?P<URL>.+)"[^>]+>(?P<Title>\(Image Link.*\))</a>',
                         r'''<img src="\g<URL>" alt="'\g<Title>' Automatically Generated by Anknotes" /> <BR><a href="\g<URL>">\g<Title></a>''',
                         content)

        ################################### Step 3: Change white text to transparent 
        # I currently use white text in Evernote to display information that I want to be initially hidden, but visible when desired by selecting the white text.
        # We will change the white text to a special "occluded" CSS class so it can be visible on the back of cards, and also so we can adjust the color for the front of cards when using night mode
        content = content.replace('<span style="color: rgb(255, 255, 255);">', '<span class="occluded">')

        ################################### Step 4: Automatically Occlude Text in <<Double Angle Brackets>>
        content = re.sub(r'&lt;&lt;(.+?)&gt;&gt;', r'&lt;&lt;<span class="occluded">$1</span>&gt;&gt;', content)

        ################################### Step 5: Create Cloze fields from shorthand. Syntax is {Text}. Optionally {#Text} will prevent the Cloze # from incrementing.
        content = re.sub(r'([^{]){(.+?)}([^}])', self.evernote_cloze_regex, content)

        ################################### Step 6: Process "See Also: " Links
        see_also_match = regex_see_also().search(content)
        if see_also_match:
            # log_dump(see_also_match.group('SeeAlso'), "-See Also match for Note '%s': %s" % (self.evernote_guid, self.fields[FIELDS.TITLE]))
            content = content.replace(see_also_match.group(0), see_also_match.group('Suffix'))
            see_also = see_also_match.group('SeeAlso')
            see_also_header = see_also_match.group('SeeAlsoHeader')
            see_also_header_stripme = see_also_match.group('SeeAlsoHeaderStripMe')
            if see_also_header_stripme:
                see_also = see_also.replace(see_also_header, see_also_header.replace(see_also_header_stripme, ''))
            if self.Fields[FIELDS.SEE_ALSO]:
                self.Fields[FIELDS.SEE_ALSO] += "<BR><BR>\r\n"
            self.Fields[FIELDS.SEE_ALSO] += see_also
            self.process_note_see_also()

        # TODO: Add support for extracting an 'Extra' field from the Evernote Note contents        
        ################################### Note Processing complete. 
        self.Fields[FIELDS.CONTENT] = content

    def detect_note_model(self):
        log('\nTitle, self.model_name, tags, self.model_name', 'detectnotemodel')
        log(self.Fields[FIELDS.TITLE], 'detectnotemodel')
        log(self.ModelName, 'detectnotemodel')
        if FIELDS.CONTENT in self.Fields and "{{c1::" in self.Fields[FIELDS.CONTENT]:
            self.ModelName = MODELS.EVERNOTE_CLOZE
        if len(self.Tags) > 0:
            reverse_override = (EVERNOTE.TAG.TOC in self.Tags or EVERNOTE.TAG.AUTO_TOC in self.Tags)
            if EVERNOTE.TAG.REVERSIBLE in self.Tags:
                self.ModelName = MODELS.EVERNOTE_REVERSIBLE
                self.Tags.remove(EVERNOTE.TAG.REVERSIBLE)
            elif EVERNOTE.TAG.REVERSE_ONLY in self.Tags:
                self.ModelName = MODELS.EVERNOTE_REVERSE_ONLY
                self.Tags.remove(EVERNOTE.TAG.REVERSE_ONLY)
            if reverse_override:
                self.ModelName = MODELS.EVERNOTE_DEFAULT

        log(self.Tags, 'detectnotemodel')
        log(self.ModelName, 'detectnotemodel')

    def model_id(self):
        if not self.ModelName: return None
        return long(self.Anki.models().byName(self.ModelName)['id'])

    def process_note(self):
        self.process_note_content()
        self.detect_note_model()

        # def _changeCards(self, nids, oldModel, newModel, map):
        # d = []
        # deleted = []
        # for (cid, ord) in mw.col.db.execute(
        # "select id, ord from cards where nid in "+ids2str(nids)):
        # # if the src model is a cloze, we ignore the map, as the gui
        # # doesn't currently support mapping them
        # if oldModel['type'] == MODEL_CLOZE:
        # new = ord
        # if newModel['type'] != MODEL_CLOZE:
        # # if we're mapping to a regular note, we need to check if
        # # the destination ord is valid
        # if len(newModel['tmpls']) <= ord:
        # new = None
        # else:
        # # mapping from a regular note, so the map should be valid
        # new = map[ord] # Line 460
        # if new is not None:
        # d.append(dict(
        # cid=cid,new=new,u=mw.col.usn(),m=intTime()))
        # else:
        # deleted.append(cid)
        # mw.col.db.executemany(
        # "update cards set ord=:new,usn=:u,mod=:m where id=:cid",
        # d)
        # mw.col.remCards(deleted)        

    def update_note_model(self):
        modelNameNew = self.ModelName
        if not modelNameNew: return False
        modelIdOld = self.note.mid
        modelIdNew = self.model_id()
        if modelIdOld == modelIdNew:
            return False
        mm = self.Anki.models()
        modelOld = self.note.model()
        modelNew = mm.get(modelIdNew)
        modelNameOld = modelOld['name']
        fmap = get_self_referential_fmap()
        cmap = {0: 0}
        if modelNameOld == MODELS.EVERNOTE_REVERSE_ONLY and modelNameNew == MODELS.EVERNOTE_REVERSIBLE:
            cmap[0] = 1
        elif modelNameOld == MODELS.EVERNOTE_REVERSIBLE:
            if modelNameNew == MODELS.EVERNOTE_REVERSE_ONLY:
                cmap = {0: None, 1: 0}
            else:
                cmap[1] = None
                # log("Changing model:\n From: '%s' \n To:   '%s'" % (modelNameOld, modelNameNew  ))
        # log("NID %d  cmap- %s" % (self.note.id, str(cmap)))
        self.log_update("Changing model:\n From: '%s' \n To:   '%s'" % (modelNameOld, modelNameNew))
        # self.log_update("NID %d  cmap- %s" % (self.note.id, str(cmap)))
        mm.change(modelOld, [self.note.id], modelNew, fmap, cmap)
        self.Changed = True
        return True

    def log_update(self, content=''):
        if not self.logged:
            count_updated_new = (self.Counts.Updated + 1 if content else 0)
            count_str = ''
            if self.Counts.Current > 0:
                count_str = ' ['
                if self.Counts.Current - count_updated_new > 0 and count_updated_new > 0:
                    count_str += '%3d/' % count_updated_new
                    count_str += '%-4d]/[' % self.Counts.Current
                else:
                    count_str += '%4d/' % self.Counts.Current
                count_str += '%-4d]' % self.Counts.Max
                count_str += ' (%2d%%)' % (float(self.Counts.Current) / self.Counts.Max * 100)
            log_title = '!' if content else ''
            log_title += 'UPDATING NOTE%s: %-80s: %s' % (count_str, self.Fields[FIELDS.TITLE],
                                                         self.Fields[FIELDS.EVERNOTE_GUID].replace(
                                                             FIELDS.EVERNOTE_GUID_PREFIX, ''))
            log(log_title, 'AddUpdateNote', timestamp=(content is ''),
                clear=((self.Counts.Current == 1 or self.Counts.Current == 100) and not self.logged))
            self.logged = True
        if not content: return
        content = obj2log_simple(content)
        content = content.replace('\n', '\n        ')
        log(' > %s\n' % content, 'AddUpdateNote', timestamp=False)

    def update_note_tags(self):
        if len(self.Tags) == 0: return False
        self.Tags = get_tag_names_to_import(self.Tags)
        if not self.BaseNote:
            self.log_update("Error with unt")
            self.log_update(self.Tags)
            self.log_update(self.Fields)
            self.log_update(self.BaseNote)
        assert self.BaseNote
        baseTags = sorted(self.BaseNote.tags, key=lambda s: s.lower())
        value = u','.join(self.Tags)
        value_original = u','.join(baseTags)
        if str(value) == str(value_original):
            return False
        self.log_update("Changing tags:\n From: '%s' \n To:   '%s'" % (value_original, value))
        self.BaseNote.tags = self.Tags
        self.Changed = True
        return True

    def update_note_deck(self):
        deckNameNew = self.deck()
        if not deckNameNew: return False
        deckIDNew = self.Anki.decks().id(deckNameNew)
        deckIDOld = get_anki_deck_id_from_note_id(self.note.id)
        if deckIDNew == deckIDOld:
            return False
        self.log_update(
            "Changing deck:\n From: '%s' \n To:   '%s'" % (self.Anki.decks().nameOrNone(deckIDOld), self.deck()))
        # Not sure if this is necessary or Anki does it by itself:
        ankDB().execute("UPDATE cards SET did = ? WHERE nid = ?", deckIDNew, self.note.id)
        return True

    def update_note_fields(self):
        fields_to_update = [FIELDS.TITLE, FIELDS.CONTENT, FIELDS.SEE_ALSO, FIELDS.UPDATE_SEQUENCE_NUM]
        fld_content_ord = -1
        flag_changed = False
        # log_dump({'self.note.fields': self.note.fields, 'self.note._model.flds': self.note._model['flds']}, "-      > UPDATE_NOTE → anki.notes.Note: _model: flds")        
        field_updates = []
        fields_updated = {}
        for fld in self.note._model['flds']:
            if FIELDS.EVERNOTE_GUID in fld.get('name'):
                self.OriginalGuid = self.note.fields[fld.get('ord')].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')
            for field_to_update in fields_to_update:
                if field_to_update in fld.get('name') and field_to_update in self.Fields:
                    if field_to_update is FIELDS.CONTENT:
                        fld_content_ord = fld.get('ord')
                    try:
                        value = self.Fields[field_to_update]
                        value_original = self.note.fields[fld.get('ord')]
                        if isinstance(value, str):
                            value = unicode(value, 'utf-8')
                        if isinstance(value_original, str):
                            value_original = unicode(value_original, 'utf-8')
                        if not value == value_original:
                            flag_changed = True
                            self.note.fields[fld.get('ord')] = value
                            fields_updated[field_to_update] = value_original
                            if field_to_update is FIELDS.CONTENT or field_to_update is FIELDS.SEE_ALSO:
                                diff = generate_diff(value_original, value)
                            else:
                                diff = 'From: \n%s \n\n To:   \n%s' % (value_original, value)
                            field_updates.append("Changing field #%d %s:\n%s" % (fld.get('ord'), field_to_update, diff))
                    except:
                        self.log_update(field_updates)
                        log_error(
                            "ERROR: UPDATE_NOTE: Note '%s': %s: Unable to set self.note.fields for field '%s'. Ord: %s. Note fields count: %d" % (
                                self.Guid, self.Fields[FIELDS.TITLE], field_to_update, str(fld.get('ord')),
                                len(self.note.fields)))
                        raise
        if len(field_updates) == 2:
            if FIELDS.SEE_ALSO in fields_updated and FIELDS.CONTENT in fields_updated:
                fc_test1 = (self.unprocessed_content == fields_updated[FIELDS.CONTENT])
                fc_test2 = (self.unprocessed_see_also == fields_updated[FIELDS.SEE_ALSO])
                fc_test = fc_test1 and fc_test2
                if fc_test:
                    field_updates = []
                    self.log_update('(Detected See Also Contents)')
                elif fc_test1:
                    del field_updates[0]
                else:
                    log_dump([fc_test1, fc_test2, self.unprocessed_content, '-' + fields_updated[FIELDS.CONTENT]],
                             'AddUpdateNoteTest')
        for update in field_updates:
            self.log_update(update)
        if not fld_content_ord is -1:
            debug_fields = list(self.note.fields)
            del debug_fields[fld_content_ord]
            log_dump(debug_fields, "-      > UPDATE_NOTE → anki.notes.Note: FIELDS ")
        if flag_changed: self.Changed = True
        return flag_changed

    def update_note(self):
        # col = self.anki.collection()
        self.note = self.BaseNote
        self.logged = False
        if not self.BaseNote:
            self.log_update("Not updating Note: Could not find base note")
            return False
        self.Changed = False
        self.update_note_tags()
        self.update_note_fields()
        if not (self.Changed or self.update_note_deck()):
            if self._log_update_if_unchanged_:
                self.log_update("Not updating Note: The fields, tags, and deck are the same")
            elif (self.Counts.Updated is 0 or self.Counts.Current / self.Counts.Updated > 9) and self.Counts.Current % 100 is 0:
                self.log_update()
            return False
            # i.e., the note deck has been changed but the tags and fields have not
        if not self.Changed:
            self.Counts.Updated += 1
            return True
        if not self.OriginalGuid:
            flds = get_dict_from_list(self.BaseNote.items())
            self.OriginalGuid = get_evernote_guid_from_anki_fields(flds)
        db_title = ankDB().scalar(
            "SELECT title FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, self.OriginalGuid))
        if self.Fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '') != self.OriginalGuid or \
                        self.Fields[FIELDS.TITLE] != db_title:
            self.log_update(' %s:     DB: ' % self.OriginalGuid + '    ' + db_title)
        self.note.flush()
        self.update_note_model()
        # self.           
        self.Counts.Updated += 1
        return True

    def Title(self):
        if FIELDS.TITLE in self.Fields:
            return self.Fields[FIELDS.TITLE]
        if self.BaseNote:
            return self.originalFields[FIELDS.TITLE]

    def add_note(self):
        self.create_note()
        if self.note is not None:
            collection = self.Anki.collection()
            db_title = ankDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (
                TABLES.EVERNOTE.NOTES, self.Fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')))
            log(' %s:    ADD: ' % self.Fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '') + '    ' +
                self.Fields[FIELDS.TITLE], 'AddUpdateNote')
            if self.Fields[FIELDS.TITLE] != db_title:
                log(' %s:     DB TITLE: ' % re.sub(r'.', ' ', self.Fields[FIELDS.EVERNOTE_GUID].replace(
                    FIELDS.EVERNOTE_GUID_PREFIX, '')) + '    ' + db_title, 'AddUpdateNote')
            try:
                collection.addNote(self.note)
            except:
                log_error("Unable to collection.addNote for Note %s:    %s" % (
                    self.Fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, ''), db_title))
                log_dump(self.note.fields, '- FAILED collection.addNote: ')
                return -1
            collection.autosave()
            self.Anki.start_editing()
            return self.note.id

    def create_note(self):
        id_deck = self.Anki.decks().id(self.deck())
        if not self.ModelName: self.ModelName = MODELS.EVERNOTE_DEFAULT
        model = self.Anki.models().byName(self.ModelName)
        col = self.Anki.collection()
        self.note = AnkiNote(col, model)
        self.note.model()['did'] = id_deck
        self.note.tags = self.Tags
        for name, value in self.Fields.items():
            self.note[name] = value
