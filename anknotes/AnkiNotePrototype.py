# -*- coding: utf-8 -*-
### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.error import HandleUnicodeError
from anknotes.EvernoteNoteTitle import EvernoteNoteTitle

### Anki Imports


try:
    import anki
    from anki.notes import Note as AnkiNote
    from aqt import mw
except:
    pass


def get_self_referential_fmap():
    fmap = {}
    for i in range(0, len(FIELDS.LIST)):
        fmap[i] = i
    return fmap


class AnkiNotePrototype:
    Anki = None
    """:type : anknotes.Anki.Anki """
    BaseNote = None
    """:type : AnkiNote """
    enNote = None
    """:type: EvernoteNotePrototype.EvernoteNotePrototype"""
    Fields = {}
    """:type : dict[str, str]"""
    Tags = []
    """:type : list[str]"""
    ModelName = None
    """:type : str"""
    # Guid = ""
    # """:type : str"""
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
    _unprocessed_content_ = ""
    _unprocessed_see_also_ = ""
    _log_update_if_unchanged_ = True

    @property
    def Guid(self):
        return get_evernote_guid_from_anki_fields(self.Fields)

    def __init__(self, anki=None, fields=None, tags=None, base_note=None, notebookGuid=None, count=-1, count_update=0,
                 max_count=1, counts=None, light_processing=False, enNote=None):
        """
        Create Anki Note Prototype Class from fields or Base Anki Note
        :param anki: Anki: Anknotes Main Class Instance
        :type anki: anknotes.Anki.Anki
        :param fields: Dict of Fields
        :param tags: List of Tags
        :type tags : list[str]
        :param base_note: Base Anki Note if Updating an Existing Note
        :type base_note : anki.notes.Note
        :param enNote: Base Evernote Note Prototype from Anknotes DB, usually used just to process a note's contents
        :type enNote : EvernoteNotePrototype.EvernoteNotePrototype
        :param notebookGuid:
        :param count:
        :param count_update:
        :param max_count:
        :param counts: AnkiNotePrototype.Counts if being used to add/update multiple notes
        :type counts :  AnkiNotePrototype.Counts
        :return: AnkiNotePrototype
        """
        self.light_processing = light_processing
        self.Anki = anki
        self.Fields = fields
        self.BaseNote = base_note
        if enNote and light_processing and not fields:
            self.Fields = {
                FIELDS.TITLE:         enNote.FullTitle, FIELDS.CONTENT: enNote.Content, FIELDS.SEE_ALSO: u'',
                FIELDS.EVERNOTE_GUID: FIELDS.EVERNOTE_GUID_PREFIX + enNote.Guid
                }
            self.enNote = enNote
        self.Changed = False
        self.logged = False
        if counts:
            self.Counts = counts
        else:
            self.Counts.Updated = count_update
            self.Counts.Current = count + 1
            self.Counts.Max = max_count
        self.initialize_fields()
        # self.Guid = get_evernote_guid_from_anki_fields(self.Fields)
        self.NotebookGuid = notebookGuid
        self.ModelName = None  # MODELS.DEFAULT
        # self.Title = EvernoteNoteTitle()
        if not self.NotebookGuid and self.Anki:
            self.NotebookGuid = self.Anki.get_notebook_guid_from_ankdb(self.Guid)
        if not self.Guid and (self.light_processing or self.NotebookGuid):
            log('Guid/Notebook Guid missing for: ' + self.FullTitle)
            log(self.Guid)
            log(self.NotebookGuid)
            raise ValueError
        self._deck_parent_ = self.Anki.deck if self.Anki else ''
        assert tags is not None
        self.Tags = tags
        self.__cloze_count__ = 0
        self.process_note()

    def initialize_fields(self):
        if self.BaseNote:
            self.originalFields = get_dict_from_list(self.BaseNote.items())
        for field in FIELDS.LIST:
            if not field in self.Fields:
                self.Fields[field] = self.originalFields[field] if self.BaseNote else u''
                # self.Title = EvernoteNoteTitle(self.Fields)

    def deck(self):
        deck = self._deck_parent_
        if TAGS.TOC in self.Tags or TAGS.AUTO_TOC in self.Tags:
            deck += DECKS.TOC_SUFFIX
        elif TAGS.OUTLINE in self.Tags and TAGS.OUTLINE_TESTABLE not in self.Tags:
            deck += DECKS.OUTLINE_SUFFIX
        elif not self._deck_parent_ or mw.col.conf.get(SETTINGS.ANKI.DECKS.EVERNOTE_NOTEBOOK_INTEGRATION, True):
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
        return "%s{{c%d::%s}}%s" % (match.group(1), self.__cloze_count__, matchText, match.group(3))

    def regex_occlude_match(self, match):
        matchText = match.group(0)
        if 'class="Occluded"' in matchText or "class='Occluded'" in matchText: return matchText
        return r'&lt;&lt;' + match.group('PrefixKeep') + ' <div class="occluded">' + match.group(
            'OccludedText') + '</div>&gt;&gt;'

    def process_note_see_also(self):
        if not FIELDS.SEE_ALSO in self.Fields or not FIELDS.EVERNOTE_GUID in self.Fields: return
        db = ankDB()
        db.execute("DELETE FROM %s WHERE source_evernote_guid = '%s' " % (TABLES.SEE_ALSO, self.Guid))
        link_num = 0
        for enLink in find_evernote_links(self.Fields[FIELDS.SEE_ALSO]):
            if not check_evernote_guid_is_valid(enLink.Guid): self.Fields[FIELDS.SEE_ALSO] = remove_evernote_link(
                enLink, self.Fields[FIELDS.SEE_ALSO]); continue
            link_num += 1
            title_text = enLink.FullTitle.replace(u'\'', u'\'\'')
            from_toc = 1 if ',%s,' % TAGS.TOC in self.Tags else 0
            is_toc = 1 if (title_text == "TOC" or title_text == "TABLE OF CONTENTS") else 0
            is_outline = 1 if (title_text == "O" or title_text == "Outline") else 0
            db.execute(
                "INSERT OR REPLACE INTO %s (source_evernote_guid, number, uid, shard, target_evernote_guid, html, title, from_toc, is_toc, is_outline) VALUES('%s', %d, %d, '%s', '%s', '%s', '%s', %d, %d, %d)" % (
                    TABLES.SEE_ALSO, self.Guid, link_num, enLink.Uid, enLink.Shard,
                    enLink.Guid, enLink.HTML, title_text, from_toc, is_toc, is_outline))
        if link_num is 0: self.Fields[FIELDS.SEE_ALSO] = ""
        db.commit()

    def process_note_content(self):
        def step_0_remove_evernote_css_attributes():
            ################################### Step 0: Correct weird Evernote formatting
            self.Fields[FIELDS.CONTENT] = clean_evernote_css(self.Fields[FIELDS.CONTENT])

        def step_1_modify_evernote_links():
            ################################### Step 1: Modify Evernote Links
            # We need to modify Evernote's "Classic" Style Note Links due to an Anki bug with executing the evernote command with three forward slashes.
            # For whatever reason, Anki cannot handle evernote links with three forward slashes, but *can* handle links with two forward slashes.
            self.Fields[FIELDS.CONTENT] = self.Fields[FIELDS.CONTENT].replace("evernote:///", "evernote://")

            # Modify Evernote's "New" Style Note links that point to the Evernote website. Normally these links open the note using Evernote's web client.
            # The web client then opens the local Evernote executable. Modifying the links as below will skip this step and open the note directly using the local Evernote executable
            self.Fields[FIELDS.CONTENT] = re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([\w\d\-]+)',
                                                 r'evernote://view/\2/\1/\3/\3/', self.Fields[FIELDS.CONTENT])

            # If we are converting back to Evernote format 
            if self.light_processing: self.Fields[FIELDS.CONTENT] = self.Fields[FIELDS.CONTENT].replace("evernote://",
                                                                                                        "evernote:///")

        def step_2_modify_image_links():
            ################################### Step 2: Modify Image Links
            # Currently anknotes does not support rendering images embedded into an Evernote note.
            # As a work around, this code will convert any link to an image on Dropbox, to an embedded <img> tag.
            # This code modifies the Dropbox link so it links to a raw image file rather than an interstitial web page
            # Step 2.1: Modify HTML links to Dropbox images
            dropbox_image_url_base_regex = r'(?P<URLPrefix>[^"''])(?P<URL>https://www.dropbox.com/s/[\w\d]+/.+\.(jpg|png|jpeg|gif|bmp))'
            dropbox_image_url_html_link_regex = dropbox_image_url_base_regex + r'(?P<QueryString>(?:\?dl=(?:0|1))?)'
            dropbox_image_url_suffix = r'(?P<URLSuffix>[^"''])'
            dropbox_image_src_subst = r'\g<URLPrefix><a href="\g<URL>\g<QueryString>"><img src="\g<URL>?raw=1" alt="Dropbox Link %s Automatically Generated by Anknotes" /></a>\g<URLSuffix>'
            self.Fields[FIELDS.CONTENT] = re.sub(r'<a href="%s"[^>]*>(?P<Title>.+?)</a>' % (
                dropbox_image_url_html_link_regex + dropbox_image_url_suffix),
                                                 dropbox_image_src_subst % "'\g<Title>'", self.Fields[FIELDS.CONTENT])

            # Step 2.2: Modify Plain-text links to Dropbox images
            try:
                dropbox_image_url_regex = dropbox_image_url_base_regex + r'(?P<QueryString>\?dl=(?:0|1))' + dropbox_image_url_suffix
                self.Fields[FIELDS.CONTENT] = re.sub(dropbox_image_url_regex,
                                                     r'\g<URLPrefix>' + dropbox_image_src_subst % "From Plain-Text Link" + r'\g<URLSuffix>',
                                                     self.Fields[FIELDS.CONTENT])
            except:
                log_error("\nERROR processing note, Step 2.2.  Content: %s" % self.Fields[FIELDS.CONTENT])

            # Step 2.3: Modify HTML links with the inner text of exactly "(Image Link*)"
            self.Fields[FIELDS.CONTENT] = re.sub(
                r'<a href=["''](?P<URL>.+?)["''][^>]*>(?P<Title>\(Image Link[^<]*\))</a>',
                r'''<img src="\g<URL>" alt="'\g<Title>' Automatically Generated by Anknotes" /> <BR><a href="\g<URL>">\g<Title></a>''',
                self.Fields[FIELDS.CONTENT])

        def step_3_occlude_text():
            ################################### Step 3: Change white text to transparent
            # I currently use white text in Evernote to display information that I want to be initially hidden, but visible when desired by selecting the white text.
            # We will change the white text to a special "occluded" CSS class so it can be visible on the back of cards, and also so we can adjust the color for the front of cards when using night mode
            self.Fields[FIELDS.CONTENT] = self.Fields[FIELDS.CONTENT].replace(
                '<span style="color: rgb(255, 255, 255);">', '<span class="occluded">')

            ################################### Step 4: Automatically Occlude Text in <<Double Angle Brackets>>
            self.Fields[FIELDS.CONTENT] = re.sub(
                "(?s)(?P<Prefix>&lt;|<) ?(?P=Prefix) ?(?P<PrefixKeep>(?:</div>)?)(?P<OccludedText>.+?)(?P<Suffix>&gt;|>) ?(?P=Suffix) ?",
                self.regex_occlude_match, self.Fields[FIELDS.CONTENT])

        def step_5_create_cloze_fields():
            ################################### Step 5: Create Cloze fields from shorthand. Syntax is {Text}. Optionally {#Text} will prevent the Cloze # from incrementing.
            self.Fields[FIELDS.CONTENT] = re.sub(r'([^{]){([^{].*?)}([^}])', self.evernote_cloze_regex,
                                                 self.Fields[FIELDS.CONTENT])

        def step_6_process_see_also_links():
            ################################### Step 6: Process "See Also: " Links
            see_also_match = regex_see_also().search(self.Fields[FIELDS.CONTENT])
            if not see_also_match:
                i_see_also = self.Fields[FIELDS.CONTENT].find("See Also")
                if i_see_also > -1:
                    self.loggedSeeAlsoError = self.Guid
                    i_div = self.Fields[FIELDS.CONTENT].rfind("<div", 0, i_see_also)
                    if i_div is -1: i_div = i_see_also
                    log_error(
                        "No See Also Content Found, but phrase 'See Also' exists in " + self.Guid + ": " + self.FullTitle,
                        crosspost_to_default=False)
                    log(
                        "No See Also Content Found, but phrase 'See Also' exists: \n" + self.Guid + ": " + self.FullTitle + " \n" +
                        self.Fields[FIELDS.CONTENT][i_div:i_see_also + 50] + '\n', 'SeeAlso\\MatchExpected')
                    log(self.Fields[FIELDS.CONTENT], 'SeeAlso\\MatchExpected\\' + self.FullTitle)
                    # raise ValueError
                return
            self.Fields[FIELDS.CONTENT] = self.Fields[FIELDS.CONTENT].replace(see_also_match.group(0),
                                                                              see_also_match.group('Suffix'))
            self.Fields[FIELDS.CONTENT] = self.Fields[FIELDS.CONTENT].replace('<div><b><br/></b></div></en-note>',
                                                                              '</en-note>')
            see_also = see_also_match.group('SeeAlso')
            see_also_header = see_also_match.group('SeeAlsoHeader')
            see_also_header_stripme = see_also_match.group('SeeAlsoHeaderStripMe')
            if see_also_header_stripme:
                see_also = see_also.replace(see_also_header, see_also_header.replace(see_also_header_stripme, ''))
            if self.Fields[FIELDS.SEE_ALSO]:
                self.Fields[FIELDS.SEE_ALSO] += "<br><br>\r\n"
            self.Fields[FIELDS.SEE_ALSO] += see_also
            if self.light_processing:
                self.Fields[FIELDS.CONTENT] = self.Fields[FIELDS.CONTENT].replace(see_also_match.group('Suffix'),
                                                                                  self.Fields[
                                                                                      FIELDS.SEE_ALSO] + see_also_match.group(
                                                                                      'Suffix'))
                return
            self.process_note_see_also()

        if not FIELDS.CONTENT in self.Fields:
            return
        self._unprocessed_content_ = self.Fields[FIELDS.CONTENT]
        self._unprocessed_see_also_ = self.Fields[FIELDS.SEE_ALSO]
        steps = [0, 1, 6] if self.light_processing else range(0, 7)
        if self.light_processing and not ANKI.NOTE_LIGHT_PROCESSING_INCLUDE_CSS_FORMATTING:
            steps.remove(0)
        if 0 in steps: step_0_remove_evernote_css_attributes()
        step_1_modify_evernote_links()
        if 2 in steps:
            step_2_modify_image_links()
            step_3_occlude_text()
            step_5_create_cloze_fields()
        step_6_process_see_also_links()
        # TODO: Add support for extracting an 'Extra' field from the Evernote Note contents
        ################################### Note Processing complete.

    def detect_note_model(self):
        # log('Title, self.model_name, tags, self.model_name', 'detectnotemodel')
        # log(self.FullTitle, 'detectnotemodel')
        # log(self.ModelName, 'detectnotemodel')
        if FIELDS.CONTENT in self.Fields and "{{c1::" in self.Fields[FIELDS.CONTENT]:
            self.ModelName = MODELS.CLOZE
        if len(self.Tags) > 0:
            reverse_override = (TAGS.TOC in self.Tags or TAGS.AUTO_TOC in self.Tags)
            if TAGS.REVERSIBLE in self.Tags:
                self.ModelName = MODELS.REVERSIBLE
                self.Tags.remove(TAGS.REVERSIBLE)
            elif TAGS.REVERSE_ONLY in self.Tags:
                self.ModelName = MODELS.REVERSE_ONLY
                self.Tags.remove(TAGS.REVERSE_ONLY)
            if reverse_override:
                self.ModelName = MODELS.DEFAULT

                # log(self.Tags, 'detectnotemodel')
                # log(self.ModelName, 'detectnotemodel')

    def model_id(self):
        if not self.ModelName: return None
        return long(self.Anki.models().byName(self.ModelName)['id'])

    def process_note(self):
        self.process_note_content()
        if not self.light_processing:
            self.detect_note_model()

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
        if modelNameOld == MODELS.REVERSE_ONLY and modelNameNew == MODELS.REVERSIBLE:
            cmap[0] = 1
        elif modelNameOld == MODELS.REVERSIBLE:
            if modelNameNew == MODELS.REVERSE_ONLY:
                cmap = {0: None, 1: 0}
            else:
                cmap[1] = None
        self.log_update("Changing model:\n From: '%s' \n To:   '%s'" % (modelNameOld, modelNameNew))
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
            log_title += 'UPDATING NOTE%s: %-80s %s' % (count_str, self.FullTitle + ':', self.Guid)
            log(log_title, 'AddUpdateNote', timestamp=(content is ''),
                clear=((self.Counts.Current == 1 or self.Counts.Current == 100) and not self.logged))
            self.logged = True
        if not content: return
        content = obj2log_simple(content)
        content = content.replace('\n', '\n        ')
        if content.lstrip()[:1] != '>': content = '> ' + content
        log(' %s\n' % content, 'AddUpdateNote', timestamp=False)

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
        field_updates = []
        fields_updated = {}
        for fld in self.note._model['flds']:
            if FIELDS.EVERNOTE_GUID in fld.get('name'):
                self.OriginalGuid = self.note.fields[fld.get('ord')].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')
            for field_to_update in fields_to_update:
                if field_to_update == fld.get('name') and field_to_update in self.Fields:
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
                                self.Guid, self.FullTitle, field_to_update, str(fld.get('ord')),
                                len(self.note.fields)))
                        raise
        for update in field_updates:
            self.log_update(update)
        if flag_changed: self.Changed = True
        return flag_changed

    def update_note(self):
        self.note = self.BaseNote
        self.logged = False
        if not self.BaseNote:
            self.log_update("Not updating Note: Could not find base note")
            return -1
        self.Changed = False
        self.update_note_tags()
        self.update_note_fields()
        i_see_also = self.Fields[FIELDS.CONTENT].find("See Also")
        if i_see_also > -1:
            i_div = self.Fields[FIELDS.CONTENT].rfind("<div", 0, i_see_also)
            if i_div is -1: i_div = i_see_also
            if not hasattr(self, 'loggedSeeAlsoError') or self.loggedSeeAlsoError != self.Guid:
                log_error(
                    "No See Also Content Found, but phrase 'See Also' exists in " + self.Guid + ": " + self.FullTitle,
                    crosspost_to_default=False)
            log(
                "No See Also Content Found, but phrase 'See Also' exists: \n" + self.Guid + ": " + self.FullTitle + " \n" +
                self.Fields[FIELDS.CONTENT][i_div:i_see_also + 50] + '\n', 'SeeAlso\\MatchExpectedUpdate')
            log(self.Fields[FIELDS.CONTENT], 'SeeAlso\\MatchExpectedUpdate\\' + self.FullTitle)
        if not (self.Changed or self.update_note_deck()):
            if self._log_update_if_unchanged_:
                self.log_update("Not updating Note: The fields, tags, and deck are the same")
            elif (
                            self.Counts.Updated is 0 or self.Counts.Current / self.Counts.Updated > 9) and self.Counts.Current % 100 is 0:
                self.log_update()
            return 0
        if not self.Changed:
            # i.e., the note deck has been changed but the tags and fields have not
            self.Counts.Updated += 1
            return 1
        if not self.OriginalGuid:
            flds = get_dict_from_list(self.BaseNote.items())
            self.OriginalGuid = get_evernote_guid_from_anki_fields(flds)
        db_title = get_evernote_title_from_guid(self.OriginalGuid)
        new_guid = self.Guid
        new_title = self.FullTitle
        self.check_titles_equal(db_title, new_title, new_guid)
        self.note.flush()
        self.log_update("  > Flushing Note")
        self.update_note_model()
        self.Counts.Updated += 1
        return 1

    def check_titles_equal(self, old_title, new_title, new_guid, log_title='DB INFO UNEQUAL'):
        do_log_title = False
        if not isinstance(new_title, unicode):
            try: new_title = unicode(new_title, 'utf-8')
            except: do_log_title = True
        if not isinstance(old_title, unicode):
            try: old_title = unicode(old_title, 'utf-8')
            except: do_log_title = True
        guid_text = '' if self.OriginalGuid is None else '     ' + self.OriginalGuid + (
            '' if new_guid == self.OriginalGuid else ' vs %s' % new_guid) + ':'
        if do_log_title or new_title != old_title or (self.OriginalGuid and new_guid != self.OriginalGuid):
            log_str = ' %s: %s%s' % (
                '*' if do_log_title else ' ' + log_title, guid_text, '    ' + new_title + ' vs ' + old_title)
            log_error(log_str, crosspost_to_default=False)
            self.log_update(log_str)
            return False
        return True

    @property
    def Title(self):
        """:rtype : EvernoteNoteTitle.EvernoteNoteTitle """
        title = ""
        if FIELDS.TITLE in self.Fields:
            title = self.Fields[FIELDS.TITLE]
        if self.BaseNote:
            title = self.originalFields[FIELDS.TITLE]
        return EvernoteNoteTitle(title)

    @property
    def FullTitle(self): return self.Title.FullTitle

    def save_anki_fields_decoded(self, attempt, from_anp_fields=False, do_decode=None):
        title = self.db_title if hasattr(self, 'db_title') else self.FullTitle
        e_return = False
        log_header = 'ANKI-->ANP-->'
        if from_anp_fields:
            log_header += 'CREATE ANKI FIELDS'
            base_values = self.Fields.items()
        else:
            log_header += 'SAVE ANKI FIELDS (DECODED)'
            base_values = enumerate(self.note.fields)
        for key, value in base_values:
            name = key if from_anp_fields else FIELDS.LIST[key - 1] if key > 0 else FIELDS.EVERNOTE_GUID
            if isinstance(value, unicode) and not do_decode is True: action = 'ENCODING'
            elif isinstance(value, str) and not do_decode is False: action = 'DECODING'
            else: action = 'DOING NOTHING'
            log('\t - %s for %s field %s' % (action, value.__class__.__name__, name), 'unicode', timestamp=False)
            if action is not 'DOING NOTHING':
                try:
                    new_value = value.encode('utf-8') if action == 'ENCODED' else value.decode('utf-8')
                    if from_anp_fields: self.note[key] = new_value
                    else: self.note.fields[key] = new_value
                except (UnicodeDecodeError, UnicodeEncodeError, UnicodeTranslateError, UnicodeError, Exception), e:
                    e_return = HandleUnicodeError(log_header, e, self.Guid, title, action, attempt, value, field=name)
                    if e_return is not 1: raise
        if e_return is not False: log_blank('unicode')
        return 1

    def add_note_try(self, attempt=1):
        title = self.db_title if hasattr(self, 'db_title') else self.FullTitle
        col = self.Anki.collection()
        log_header = 'ANKI-->ANP-->ADD NOTE FAILED'
        action = 'DECODING?'
        try:
            col.addNote(self.note)
        except (UnicodeDecodeError, UnicodeEncodeError, UnicodeTranslateError, UnicodeError, Exception), e:
            e_return = HandleUnicodeError(log_header, e, self.Guid, title, action, attempt, self.note[FIELDS.TITLE])
            if e_return is not 1: raise
            self.save_anki_fields_decoded(attempt + 1)
            return self.add_note_try(attempt + 1)
        return 1

    def add_note(self):
        self.create_note()
        if self.note is None: return -1
        collection = self.Anki.collection()
        db_title = get_evernote_title_from_guid(self.Guid)
        log(' %s:    ADD: ' % self.Guid + '    ' + self.FullTitle, 'AddUpdateNote')
        self.check_titles_equal(db_title, self.FullTitle, self.Guid, 'NEW NOTE TITLE UNEQUAL TO DB ENTRY')
        if self.add_note_try() is not 1: return -1
        collection.autosave()
        self.Anki.start_editing()
        return self.note.id

    def create_note(self, attempt=1):
        id_deck = self.Anki.decks().id(self.deck())
        if not self.ModelName: self.ModelName = MODELS.DEFAULT
        model = self.Anki.models().byName(self.ModelName)
        col = self.Anki.collection()
        self.note = AnkiNote(col, model)
        self.note.model()['did'] = id_deck
        self.note.tags = self.Tags
        title = self.db_title if hasattr(self, 'db_title') else self.FullTitle
        self.save_anki_fields_decoded(attempt, True, True)
