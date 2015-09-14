# -*- coding: utf-8 -*-
### Anknotes Shared Imports
from anknotes.shared import *

### Anki Imports
import anki

try:
    # noinspection PyUnresolvedReferences
    from aqt import mw
except:
    pass


def get_self_referential_fmap():
    fmap = {}
    for i in range(0, len(FIELDS_LIST)):
        fmap[i] = i
    return fmap


class AnkiNotePrototype:
    fields = {}
    tags = []
    model_name = None
    evernote_guid = ""
    cloze_count = 0
    count_update = 0
    count = 0
    max_count = 1
    original_evernote_guid = None
    flag_changed = False
    log_update_if_unchanged = True

    def __init__(self, anki, fields, tags, base_anki_note=None, notebookGuid=None, count=-1, count_update=0,
                 max_count=1):
        self.anki = anki
        self.fields = fields
        self.baseAnkiNote = base_anki_note
        self.flag_changed = False
        self.logged = False
        self.count_update = count_update
        self.count = count + 1
        self.max_count = max_count
        self.initialize_fields()
        self.evernote_guid = get_evernote_guid_from_anki_fields(fields)
        self.notebookGuid = notebookGuid
        self.model_name = None  # MODELS.EVERNOTE_DEFAULT
        self.title = ""
        if not self.notebookGuid:
            self.notebookGuid = self.anki.get_notebook_guid_from_ankdb(self.evernote_guid)
        assert self.evernote_guid and self.notebookGuid
        self.deck_parent = self.anki.deck
        self.tags = tags
        self.cloze_count = 0
        self.process_note()

    def initialize_fields(self):
        if self.baseAnkiNote:
            self.originalFields = get_dict_from_list(self.baseAnkiNote.items())
        for field in FIELDS_LIST:
            if not field in self.fields:
                self.fields[field] = self.originalFields[field] if self.baseAnkiNote else u''
        title = self.fields[FIELDS.TITLE]
        if hasattr(title, 'title'):
            title = title.title() if callable(title.title) else title.title
        if hasattr(title, 'Title'):
            title = title.Title() if callable(title.Title) else title.Title
        self.title = title

    def deck(self):
        if EVERNOTE.TAG.TOC in self.tags or EVERNOTE.TAG.AUTO_TOC in self.tags:
            deck = self.deck_parent + DECKS.TOC_SUFFIX
        elif EVERNOTE.TAG.OUTLINE in self.tags and EVERNOTE.TAG.OUTLINE_TESTABLE not in self.tags:
            deck = self.deck_parent + DECKS.OUTLINE_SUFFIX
        elif not self.deck_parent or mw.col.conf.get(SETTINGS.ANKI_DECK_EVERNOTE_NOTEBOOK_INTEGRATION, True):
            deck = self.anki.get_deck_name_from_evernote_notebook(self.notebookGuid, self.deck_parent)
            if not deck: return None
        if deck[:2] == '::':
            deck = deck[2:]
        return deck

    def evernote_cloze_regex(self, match):
        matchText = match.group(2)
        if matchText[0] == "#":
            matchText = matchText[1:]
        else:
            self.cloze_count += 1
        if self.cloze_count == 0:
            self.cloze_count = 1
        return "%s{{c%d::%s}}%s" % (match.group(1), self.cloze_count, matchText, match.group(2))

    def process_note_see_also(self):
        if not FIELDS.SEE_ALSO in self.fields or not FIELDS.EVERNOTE_GUID in self.fields:
            return
        ankDB().execute("DELETE FROM %s WHERE source_evernote_guid = '%s' " % (TABLES.SEE_ALSO, self.evernote_guid))
        link_num = 0
        for match in find_evernote_links(self.fields[FIELDS.SEE_ALSO]):
            link_num += 1
            title_text = strip_tags(match.group('Title'))
            is_toc = 1 if (title_text == "TOC") else 0
            is_outline = 1 if (title_text is "O" or title_text is "Outline") else 0
            ankDB().execute(
                "INSERT INTO %s (source_evernote_guid, number, uid, shard, target_evernote_guid, html, title, from_toc, is_toc, is_outline) VALUES('%s', %d, %d, '%s', '%s', '%s', '%s', 0, %d, %d)" % (
                    TABLES.SEE_ALSO, self.evernote_guid, link_num, int(match.group('uid')), match.group('shard'),
                    match.group('guid'), match.group('Title'), title_text, is_toc, is_outline))

    def process_note_content(self):
        if not FIELDS.CONTENT in self.fields:
            return
        content = self.fields[FIELDS.CONTENT]
        self.unprocessed_content = content
        self.unprocessed_see_also = self.fields[FIELDS.SEE_ALSO]

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
            if self.fields[FIELDS.SEE_ALSO]:
                self.fields[FIELDS.SEE_ALSO] += "<BR><BR>\r\n"
            self.fields[FIELDS.SEE_ALSO] += see_also
            self.process_note_see_also()

        # TODO: Add support for extracting an 'Extra' field from the Evernote Note contents        
        ################################### Note Processing complete. 
        self.fields[FIELDS.CONTENT] = content

    def detect_note_model(self):
        log('\n', 'detectnotemodel')
        log(self.fields[FIELDS.TITLE], 'detectnotemodel')
        log(self.model_name, 'detectnotemodel')
        if FIELDS.CONTENT in self.fields and "{{c1::" in self.fields[FIELDS.CONTENT]:
            self.model_name = MODELS.EVERNOTE_CLOZE
        if len(self.tags) > 0:
            reverse_override = (EVERNOTE.TAG.TOC in self.tags or EVERNOTE.TAG.AUTO_TOC in self.tags)
            if EVERNOTE.TAG.REVERSIBLE in self.tags:
                self.model_name = MODELS.EVERNOTE_REVERSIBLE
                self.tags.remove(EVERNOTE.TAG.REVERSIBLE)
            elif EVERNOTE.TAG.REVERSE_ONLY in self.tags:
                self.model_name = MODELS.EVERNOTE_REVERSE_ONLY
                self.tags.remove(EVERNOTE.TAG.REVERSE_ONLY)
            if reverse_override:
                self.model_name = MODELS.EVERNOTE_DEFAULT

        log(self.tags, 'detectnotemodel')
        log(self.model_name, 'detectnotemodel')

    def model_id(self):
        if not self.model_name: return None
        return long(self.anki.models().byName(self.model_name)['id'])

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
        modelNameNew = self.model_name
        if not modelNameNew: return False
        modelIdOld = self.note.mid
        modelIdNew = self.model_id()
        if modelIdOld == modelIdNew:
            return False
        mm = self.anki.models()
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
        self.flag_changed = True
        return True

    def log_update(self, content=''):
        if not self.logged:
            count_updated_new = (self.count_update + 1 if content else 0)
            count_str = ''
            if self.count > 0:
                count_str = ' ['
                if self.count - count_updated_new > 0 and count_updated_new > 0:
                    count_str += '%3d/' % count_updated_new
                    count_str += '%-4d]/[' % self.count
                else:
                    count_str += '%4d/' % self.count
                count_str += '%-4d]' % self.max_count
                count_str += ' (%2d%%)' % (float(self.count) / self.max_count * 100)
            log_title = '!' if content else ''
            log_title += 'UPDATING NOTE%s: %-80s: %s' % (count_str, self.fields[FIELDS.TITLE],
                                                         self.fields[FIELDS.EVERNOTE_GUID].replace(
                                                             FIELDS.EVERNOTE_GUID_PREFIX, ''))
            log(log_title, 'AddUpdateNote', timestamp=(content is ''),
                clear=((self.count == 1 or self.count == 100) and not self.logged))
            self.logged = True
        if not content: return
        content = obj2log_simple(content)
        content = content.replace('\n', '\n        ')
        log(' > %s\n' % content, 'AddUpdateNote', timestamp=False)

    def update_note_tags(self):
        if len(self.tags) == 0: return False
        self.tags = get_tag_names_to_import(self.tags)
        if not self.baseAnkiNote:
            self.log_update("Error with unt")
            self.log_update(self.tags)
            self.log_update(self.fields)
            self.log_update(self.baseAnkiNote)
        assert self.baseAnkiNote
        baseTags = sorted(self.baseAnkiNote.tags, key=lambda s: s.lower())
        value = u','.join(self.tags)
        value_original = u','.join(baseTags)
        if str(value) == str(value_original):
            return False
        self.log_update("Changing tags:\n From: '%s' \n To:   '%s'" % (value_original, value))
        self.baseAnkiNote.tags = self.tags
        self.flag_changed = True
        return True

    def update_note_deck(self):
        deckNameNew = self.deck()
        if not deckNameNew: return False
        deckIDNew = self.anki.decks().id(deckNameNew)
        deckIDOld = get_anki_deck_id_from_note_id(self.note.id)
        if deckIDNew == deckIDOld:
            return False
        self.log_update(
            "Changing deck:\n From: '%s' \n To:   '%s'" % (self.anki.decks().nameOrNone(deckIDOld), self.deck()))
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
                self.original_evernote_guid = self.note.fields[fld.get('ord')].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')
            for field_to_update in fields_to_update:
                if field_to_update in fld.get('name') and field_to_update in self.fields:
                    if field_to_update is FIELDS.CONTENT:
                        fld_content_ord = fld.get('ord')
                    try:
                        value = self.fields[field_to_update]
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
                                self.evernote_guid, self.fields[FIELDS.TITLE], field_to_update, str(fld.get('ord')),
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
        if flag_changed: self.flag_changed = True
        return flag_changed

    def update_note(self):
        # col = self.anki.collection()
        self.note = self.baseAnkiNote
        self.logged = False
        if not self.baseAnkiNote:
            self.log_update("Not updating Note: Could not find base note")
            return False
        self.flag_changed = False
        self.update_note_tags()
        self.update_note_fields()
        if not (self.flag_changed or self.update_note_deck()):
            if self.log_update_if_unchanged:
                self.log_update("Not updating Note: The fields, tags, and deck are the same")
            elif (self.count_update is 0 or self.count / self.count_update > 9) and self.count % 100 is 0:
                self.log_update()
            return False
            # i.e., the note deck has been changed but the tags and fields have not
        if not self.flag_changed:
            self.count_update += 1
            return True
        if not self.original_evernote_guid:
            flds = get_dict_from_list(self.baseAnkiNote.items())
            self.original_evernote_guid = get_evernote_guid_from_anki_fields(flds)
        db_title = ankDB().scalar(
            "SELECT title FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, self.original_evernote_guid))
        if self.fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '') != self.original_evernote_guid or \
                        self.fields[FIELDS.TITLE] != db_title:
            self.log_update(' %s:     DB: ' % self.original_evernote_guid + '    ' + db_title)
        self.note.flush()
        self.update_note_model()
        # self.           
        self.count_update += 1
        return True

    def Title(self):
        if FIELDS.TITLE in self.fields:
            return self.fields[FIELDS.TITLE]
        if self.baseAnkiNote:
            return self.originalFields[FIELDS.TITLE]

    def add_note(self):
        self.create_note()
        if self.note is not None:
            collection = self.anki.collection()
            db_title = ankDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (
                TABLES.EVERNOTE.NOTES, self.fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')))
            log(' %s:    ADD: ' % self.fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '') + '    ' +
                self.fields[FIELDS.TITLE], 'AddUpdateNote')
            if self.fields[FIELDS.TITLE] != db_title:
                log(' %s:     DB TITLE: ' % re.sub(r'.', ' ', self.fields[FIELDS.EVERNOTE_GUID].replace(
                    FIELDS.EVERNOTE_GUID_PREFIX, '')) + '    ' + db_title, 'AddUpdateNote')
            try:
                collection.addNote(self.note)
            except:
                log_error("Unable to collection.addNote for Note %s:    %s" % (
                    self.fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, ''), db_title))
                log_dump(self.note.fields, '- FAILED collection.addNote: ')
                return -1
            collection.autosave()
            self.anki.start_editing()
            return self.note.id

    def create_note(self):
        id_deck = self.anki.decks().id(self.deck())
        if not self.model_name: self.model_name = MODELS.EVERNOTE_DEFAULT
        model = self.anki.models().byName(self.model_name)
        col = self.anki.collection()
        self.note = anki.notes.Note(col, model)
        self.note.model()['did'] = id_deck
        self.note.tags = self.tags
        for name, value in self.fields.items():
            self.note[name] = value
