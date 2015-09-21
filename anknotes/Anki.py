# -*- coding: utf-8 -*-
### Python Imports
import shutil
import sys

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
from anknotes.AnkiNotePrototype import AnkiNotePrototype
from anknotes.shared import *

### Evernote Imports 
# from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
# from evernote.edam.type.ttypes import NoteSortOrder, Note
# from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode, EDAMUserException, EDAMNotFoundException
# from evernote.api.client import EvernoteClient

### Anki Imports
import anki
from anki.notes import Note as AnkiNote
import aqt
from aqt import mw

DEBUG_RAISE_API_ERRORS = False


class Anki:
    def __init__(self):
        self.deck = None
        self.templates = None

    @staticmethod
    def get_notebook_guid_from_ankdb(evernote_guid):
        return ankDB().scalar("SELECT notebookGuid FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, evernote_guid))

    def get_deck_name_from_evernote_notebook(self, notebookGuid, deck=None):
        if not deck:
            deck = self.deck if self.deck else ""
        if not hasattr(self, 'notebook_data'):
            self.notebook_data = {}
        if not notebookGuid in self.notebook_data:
            # log_error("Unexpected error: Notebook GUID '%s' could not be found in notebook data: %s" % (notebookGuid, str(self.notebook_data)))
            notebook = ankDB().first(
                "SELECT name, stack FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTEBOOKS, notebookGuid))
            if not notebook:
                log_error(
                    "   get_deck_name_from_evernote_notebook FATAL ERROR: UNABLE TO FIND NOTEBOOK '%s'. " % notebookGuid)
                return None
            # log("Getting notebook info: %s" % str(notebook))
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

    def update_evernote_notes(self, evernote_notes, log_update_if_unchanged=True):
        """
        Update Notes in Anki Database
        :type evernote_notes: list[EvernoteNotePrototype.EvernoteNotePrototype]
        :rtype : int
        :param evernote_notes: List of EvernoteNote returned from server or local db
        :param log_update_if_unchanged:
        :return: Count of notes successfully updated
        """
        return self.add_evernote_notes(evernote_notes, True, log_update_if_unchanged=log_update_if_unchanged)

    def add_evernote_notes(self, evernote_notes, update=False, log_update_if_unchanged=True):
        """
        Add Notes to or Update Notes in Anki Database
        :param evernote_notes:
        :param update:
        :param log_update_if_unchanged:
        :type evernote_notes: list[EvernoteNotePrototype.EvernoteNotePrototype]
        :type update: bool
        :return: Count of notes successfully added or updated
        """
        count_update = 0
        count = 0
        max_count = len(evernote_notes)
        for ankiNote in evernote_notes:
            try:
                title = ankiNote.Title.FullTitle
                content = ankiNote.Content
                if isinstance(content, str):
                    content = unicode(content, 'utf-8')
                anki_field_info = {
                    FIELDS.TITLE: title,
                    FIELDS.CONTENT: content,
                    FIELDS.EVERNOTE_GUID: FIELDS.EVERNOTE_GUID_PREFIX + ankiNote.Guid,
                    FIELDS.UPDATE_SEQUENCE_NUM: str(ankiNote.UpdateSequenceNum),
                    FIELDS.SEE_ALSO: u''
                }
            except:
                log_error("Unable to set field info for: Note '%s': '%s'" % (ankiNote.Title, ankiNote.Guid))
                log_dump(ankiNote.Content, " NOTE CONTENTS ")
                log_dump(ankiNote.Content.encode('utf-8'), " NOTE CONTENTS ")
                raise
            baseNote = None
            if update:
                baseNote = self.get_anki_note_from_evernote_guid(ankiNote.Guid)
                if not baseNote: log('Updating note %s: COULD NOT FIND ANKI NOTE ID' % ankiNote.Guid)
            anki_note_prototype = AnkiNotePrototype(self, anki_field_info, ankiNote.TagNames, baseNote,
                                                    notebookGuid=ankiNote.NotebookGuid, count=count,
                                                    count_update=count_update, max_count=max_count)
            anki_note_prototype._log_update_if_unchanged_ = log_update_if_unchanged
            if update:
                debug_fields = anki_note_prototype.Fields.copy()
                del debug_fields[FIELDS.CONTENT]
                log_dump(debug_fields,
                         "-      > UPDATE_evernote_notes → ADD_evernote_notes: anki_note_prototype: FIELDS ")
                if anki_note_prototype.update_note(): count_update += 1
            else:
                if not -1 == anki_note_prototype.add_note(): count_update += 1
            count += 1
        return count_update

    def delete_anki_cards(self, evernote_guids):
        col = self.collection()
        card_ids = []
        for evernote_guid in evernote_guids:
            card_ids += mw.col.findCards(FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid)
        col.remCards(card_ids)
        return len(card_ids)

    def add_evernote_model(self, mm, modelName, cloze=False):
        model = mm.byName(modelName)
        if not model:
            model = mm.new(modelName)
            templates = self.get_templates()

            # Add Field for Evernote GUID:
            #  Note that this field is first because Anki requires the first field to be unique
            evernote_guid_field = mm.newField(FIELDS.EVERNOTE_GUID)
            evernote_guid_field['sticky'] = True
            evernote_guid_field['font'] = 'Consolas'
            evernote_guid_field['size'] = 10
            mm.addField(model, evernote_guid_field)

            # Add Standard Fields:
            mm.addField(model, mm.newField(FIELDS.TITLE))

            evernote_content_field = mm.newField(FIELDS.CONTENT)
            evernote_content_field['size'] = 14
            mm.addField(model, evernote_content_field)

            evernote_see_also_field = mm.newField(FIELDS.SEE_ALSO)
            evernote_see_also_field['size'] = 14
            mm.addField(model, evernote_see_also_field)

            evernote_extra_field = mm.newField(FIELDS.EXTRA)
            evernote_extra_field['size'] = 12
            mm.addField(model, evernote_extra_field)

            evernote_toc_field = mm.newField(FIELDS.TOC)
            evernote_toc_field['size'] = 10
            mm.addField(model, evernote_toc_field)

            evernote_outline_field = mm.newField(FIELDS.OUTLINE)
            evernote_outline_field['size'] = 10
            mm.addField(model, evernote_outline_field)

            # Add USN to keep track of changes vs Evernote's servers 
            evernote_usn_field = mm.newField(FIELDS.UPDATE_SEQUENCE_NUM)
            evernote_usn_field['font'] = 'Consolas'
            evernote_usn_field['size'] = 10
            mm.addField(model, evernote_usn_field)

            # Add Templates

            if modelName is MODELS.EVERNOTE_DEFAULT or modelName is MODELS.EVERNOTE_REVERSIBLE:
                # Add Default Template
                default_template = mm.newTemplate(TEMPLATES.EVERNOTE_DEFAULT)
                default_template['qfmt'] = templates['Front']
                default_template['afmt'] = templates['Back']
                mm.addTemplate(model, default_template)
            if modelName is MODELS.EVERNOTE_REVERSE_ONLY or modelName is MODELS.EVERNOTE_REVERSIBLE:
                # Add Reversed Template
                reversed_template = mm.newTemplate(TEMPLATES.EVERNOTE_REVERSED)
                reversed_template['qfmt'] = templates['Front']
                reversed_template['afmt'] = templates['Back']
                mm.addTemplate(model, reversed_template)
            if modelName is MODELS.EVERNOTE_CLOZE:
                # Add Cloze Template        
                cloze_template = mm.newTemplate(TEMPLATES.EVERNOTE_CLOZE)
                cloze_template['qfmt'] = templates['Front']
                cloze_template['afmt'] = templates['Back']
                mm.addTemplate(model, cloze_template)

            # Update Sort field to Title (By default set to GUID since it is the first field)
            model['sortf'] = 1

            # Update Model CSS
            model['css'] = '@import url("_AviAnkiCSS.css");'

            # Set Type to Cloze 
            if cloze:
                model['type'] = MODELS.TYPE_CLOZE

            # Add Model to Collection
            mm.add(model)

            # Add Model id to list
        self.evernoteModels[modelName] = model['id']

    def get_templates(self):
        field_names = {"Title": FIELDS.TITLE, "Content": FIELDS.CONTENT, "Extra": FIELDS.EXTRA,
                       "See Also": FIELDS.SEE_ALSO, "TOC": FIELDS.TOC, "Outline": FIELDS.OUTLINE,
                       "Evernote GUID Prefix": FIELDS.EVERNOTE_GUID_PREFIX, "Evernote GUID": FIELDS.EVERNOTE_GUID}
        if not self.templates:
            # Generate Front and Back Templates from HTML Template in anknotes' addon directory
            self.templates = {"Front": file(ANKNOTES.TEMPLATE_FRONT, 'r').read() % field_names}
            self.templates["Back"] = self.templates["Front"].replace("<div id='Side-Front'>", "<div id='Side-Back'>")
        return self.templates

    def add_evernote_models(self):
        col = self.collection()
        mm = col.models
        self.evernoteModels = {}
        self.add_evernote_model(mm, MODELS.EVERNOTE_DEFAULT)
        self.add_evernote_model(mm, MODELS.EVERNOTE_REVERSE_ONLY)
        self.add_evernote_model(mm, MODELS.EVERNOTE_REVERSIBLE)
        self.add_evernote_model(mm, MODELS.EVERNOTE_CLOZE, True)

    def setup_ancillary_files(self):
        # Copy CSS file from anknotes addon directory to media directory 
        media_dir = re.sub("(?i)\.(anki2)$", ".media", self.collection().path)
        if isinstance(media_dir, str):
            media_dir = unicode(media_dir, sys.getfilesystemencoding())
        shutil.copy2(os.path.join(ANKNOTES.FOLDER_ANCILLARY, ANKNOTES.CSS), os.path.join(media_dir, ANKNOTES.CSS))

    def get_anki_fields_from_anki_note_id(self, a_id, fields_to_ignore=list()):
        note = self.collection().getNote(a_id)
        try:
            items = note.items()
        except:
            log_error("Unable to get note items for Note ID: %d" % a_id)
            raise
        return get_dict_from_list(items, fields_to_ignore)

    def get_evernote_guids_from_anki_note_ids(self, ids):
        evernote_guids = []
        self.usns = {}
        for a_id in ids:
            fields = self.get_anki_fields_from_anki_note_id(a_id, [FIELDS.CONTENT])
            evernote_guid = get_evernote_guid_from_anki_fields(fields)
            if not evernote_guid: continue
            evernote_guids.append(evernote_guid)
            log('Anki USN for Note %s is %s' % (evernote_guid, fields[FIELDS.UPDATE_SEQUENCE_NUM]), 'anki-usn')
            if FIELDS.UPDATE_SEQUENCE_NUM in fields:
                self.usns[evernote_guid] = fields[FIELDS.UPDATE_SEQUENCE_NUM]
            else:
                log("   ! get_evernote_guids_from_anki_note_ids: Note '%s' is missing USN!" % evernote_guid)
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
        ids = col.findNotes(FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid)
        # TODO: Ugly work around for a bug. Fix this later
        if not ids: return None
        if not ids[0]: return None
        note = AnkiNote(col, None, ids[0])
        return note

    def get_anknotes_note_ids_by_tag(self, tag):
        return self.get_anknotes_note_ids("tag:" + tag)

    def get_anknotes_note_ids_with_unadded_see_also(self):
        return self.get_anknotes_note_ids('"See Also" "See_Also:"')

    def process_see_also_content(self, anki_note_ids):
        count = 0
        count_update = 0
        max_count = len(anki_note_ids)
        for a_id in anki_note_ids:
            ankiNote = self.collection().getNote(a_id)
            try:
                items = ankiNote.items()
            except:
                log_error("Unable to get note items for Note ID: %d" % a_id)
                raise
            fields = {}
            for key, value in items:
                fields[key] = value
            if not fields[FIELDS.SEE_ALSO]:
                anki_note_prototype = AnkiNotePrototype(self, fields, ankiNote.tags, ankiNote, count=count,
                                                        count_update=count_update, max_count=max_count)
                if anki_note_prototype.Fields[FIELDS.SEE_ALSO]:
                    log("Detected see also contents for Note '%s': %s" % (
                        get_evernote_guid_from_anki_fields(fields), fields[FIELDS.TITLE]))
                    log(u" → %s " % strip_tags_and_new_lines(fields[FIELDS.SEE_ALSO]))
                    if anki_note_prototype.update_note():
                        count_update += 1
            count += 1

    def process_toc_and_outlines(self):
        self.extract_links_from_toc()
        self.insert_toc_into_see_also()
        self.insert_toc_and_outline_contents_into_notes()

    def insert_toc_into_see_also(self):
        db = ankDB()
        db._db.row_factory = None
        # db._db.row_factory = lambda cursor, row: showInfo(str(row))
        results = db.all(
            "SELECT s.source_evernote_guid, s.target_evernote_guid, n.title FROM %s as s, %s as n WHERE n.guid = s.target_evernote_guid AND s.source_evernote_guid != s.target_evernote_guid AND s.from_toc == 1 ORDER BY s.source_evernote_guid ASC, n.title ASC" % (
                TABLES.SEE_ALSO, TABLES.EVERNOTE.NOTES))
        grouped_results = {}
        # log('           INSERT TOCS INTO ANKI NOTES ', 'dump-insert_toc', timestamp=False, clear=True)
        # log('------------------------------------------------', 'dump-insert_toc', timestamp=False)        
        log('           <h1>INSERT TOCS INTO ANKI NOTES</h1> <HR><BR><BR>', 'see_also', timestamp=False, clear=True,
            extension='htm')
        toc_titles = {}
        for row in results:
            key = row[0]
            value = row[1]
            toc_titles[value] = row[2]
            if not key in grouped_results: grouped_results[key] = []
            grouped_results[key].append(value)
        # log_dump(grouped_results, 'grouped_results', 'insert_toc', timestamp=False)     
        toc_separator = generate_evernote_span(u' | ', u'Links', u'See Also', bold=False)
        count = 0
        count_update = 0
        max_count = len(grouped_results)
        for source_guid, toc_guids in grouped_results.items():
            ankiNote = self.get_anki_note_from_evernote_guid(source_guid)
            if not ankiNote:
                log_dump(toc_guids, 'Missing Anki Note for ' + source_guid, 'insert_toc', timestamp=False)
            else:
                fields = get_dict_from_list(ankiNote.items())
                see_also_html = fields[FIELDS.SEE_ALSO]
                see_also_links = find_evernote_links_as_guids(see_also_html)
                new_tocs = set(toc_guids) - set(see_also_links)
                new_toc_count = len(new_tocs)
                see_also_count = len(see_also_links)
                if new_toc_count > 0:
                    has_ol = u'<ol' in see_also_html
                    has_ul = u'<ul' in see_also_html
                    has_list = has_ol or has_ul
                    see_also_new = " "
                    flat_links = (new_toc_count + see_also_count < 3 and not has_list)
                    toc_delimiter = u' ' if see_also_count is 0 else toc_separator
                    for toc_guid in toc_guids:
                        toc_title = toc_titles[toc_guid]
                        if flat_links:
                            toc_title = u'[%s]' % toc_title
                        toc_link = generate_evernote_link(toc_guid, toc_title, value='TOC')
                        see_also_new += (toc_delimiter + toc_link) if flat_links else (u'\n<li>%s</li>' % toc_link)
                        toc_delimiter = toc_separator
                    if flat_links:
                        find_div_end = see_also_html.rfind('</div>') - 1
                        if find_div_end > 0:
                            see_also_html = see_also_html[:find_div_end] + see_also_new + '\n' + see_also_html[
                                                                                                 find_div_end:]
                            see_also_new = ''
                    else:
                        see_also_toc_header = u'<br><div style="margin-top:5px;">\n%s</div><ol style="margin-top:3px;">' % generate_evernote_span(
                            '<u>TABLE OF CONTENTS</u>:', 'Levels', 'Auto TOC', escape=False)
                        see_also_toc_header_ul = see_also_toc_header.replace('<ol ', '<ul ')

                        if see_also_toc_header_ul in see_also_html:
                            find_ul_end = see_also_html.rfind('</ul>') - 1
                            see_also_html = see_also_html[:find_ul_end] + '</ol>' + see_also_html[find_ul_end + 5:]
                            see_also_html = see_also_html.replace(see_also_toc_header_ul, see_also_toc_header)
                        if see_also_toc_header in see_also_html:
                            find_ol_end = see_also_html.rfind('</ol>') - 1
                            see_also_html = see_also_html[:find_ol_end] + see_also_new + '\n' + see_also_html[
                                                                                                find_ol_end:]
                            see_also_new = ''
                        else:
                            if new_toc_count is 1:
                                see_also_new = see_also_toc_header_ul + u'%s\n</ul>' % see_also_new
                            else:
                                see_also_new = see_also_toc_header + u'%s\n</ol>' % see_also_new
                                # log('\n\nWould like to add the following to %s: \n-----------------------\n%s\n-----------------------\n%s\n' % (fields[FIELDS.TITLE], see_also_new, see_also_html), 'dump-insert_toc', timestamp=False)
                    if see_also_count == 0:
                        see_also_html = generate_evernote_span(u'See Also:', 'Links', 'See Also')
                    see_also_html += see_also_new
                see_also_html = see_also_html.replace('<ol>', '<ol style="margin-top:3px;">')
                log('<h3>%s</h3><BR>' % generate_evernote_span(fields[FIELDS.TITLE], 'Links',
                                                               'TOC') + see_also_html + u'<HR>', 'see_also',
                    timestamp=False, extension='htm')
                fields[FIELDS.SEE_ALSO] = see_also_html.replace('evernote:///', 'evernote://')
                anki_note_prototype = AnkiNotePrototype(self, fields, ankiNote.tags, ankiNote, count=count,
                                                        count_update=count_update, max_count=max_count)
                anki_note_prototype._log_update_if_unchanged_ = (new_toc_count > 0)
                if anki_note_prototype.update_note():
                    count_update += 1
                count += 1
        db._db.row_factory = sqlite.Row

    def extract_links_from_toc(self):
        toc_anki_ids = self.get_anknotes_note_ids_by_tag(EVERNOTE.TAG.TOC)
        toc_evernote_guids = self.get_evernote_guids_and_anki_fields_from_anki_note_ids(toc_anki_ids)
        query_update_toc_links = "UPDATE %s SET is_toc = 1 WHERE " % TABLES.SEE_ALSO
        delimiter = ""
        # link_exists = 0
        for toc_evernote_guid, fields in toc_evernote_guids.items():
            for match in find_evernote_links(fields[FIELDS.CONTENT]):
                target_evernote_guid = match.group('guid')
                uid = int(match.group('uid'))
                shard = match.group('shard')
                # link_title = strip_tags(match.group('Title'))
                link_number = 1 + ankDB().scalar("select COUNT(*) from %s WHERE source_evernote_guid = '%s' " % (
                    TABLES.SEE_ALSO, target_evernote_guid))
                toc_link_title = fields[FIELDS.TITLE]
                toc_link_html = '<span style="color: rgb(173, 0, 0);"><b>%s</b></span>' % toc_link_title
                query = """INSERT INTO `%s`(`source_evernote_guid`, `number`, `uid`, `shard`, `target_evernote_guid`, `html`, `title`, `from_toc`, `is_toc`) SELECT '%s', %d, %d, '%s', '%s', '%s', '%s', 1, 1 FROM `%s`  WHERE NOT EXISTS (SELECT * FROM `%s` WHERE `source_evernote_guid`='%s' AND `target_evernote_guid`='%s') LIMIT 1 """ % (
                    TABLES.SEE_ALSO, target_evernote_guid, link_number, uid, shard, toc_evernote_guid,
                    toc_link_html.replace(u'\'', u'\'\''), toc_link_title.replace(u'\'', u'\'\''), TABLES.SEE_ALSO,
                    TABLES.SEE_ALSO, target_evernote_guid, toc_evernote_guid)
                log_sql('UPDATE_ANKI_DB: Add See Also Link: SQL Query: ' + query)
                ankDB().execute(query)
            query_update_toc_links += delimiter + "target_evernote_guid = '%s'" % toc_evernote_guid
            delimiter = " OR "
        ankDB().execute(query_update_toc_links)

    def insert_toc_and_outline_contents_into_notes(self):
        linked_notes_fields = {}
        for source_evernote_guid in ankDB().list(
                        "select DISTINCT source_evernote_guid from %s WHERE is_toc = 1 ORDER BY source_evernote_guid ASC" % TABLES.SEE_ALSO):
            note = self.get_anki_note_from_evernote_guid(source_evernote_guid)
            if not note: continue
            if EVERNOTE.TAG.TOC in note.tags: continue
            for fld in note._model['flds']:
                if FIELDS.TITLE in fld.get('name'):
                    note_title = note.fields[fld.get('ord')]
                    continue
            note_toc = ""
            note_outline = ""
            toc_header = ""
            outline_header = ""
            toc_count = 0
            outline_count = 0
            toc_and_outline_links = ankDB().execute(
                            "select target_evernote_guid, is_toc, is_outline from %s WHERE source_evernote_guid = '%s' AND (is_toc = 1 OR is_outline = 1) ORDER BY number ASC" % (
                            TABLES.SEE_ALSO, source_evernote_guid))
            for target_evernote_guid, is_toc, is_outline in toc_and_outline_links:
                if target_evernote_guid in linked_notes_fields:
                    linked_note_contents = linked_notes_fields[target_evernote_guid][FIELDS.CONTENT]
                    linked_note_title = linked_notes_fields[target_evernote_guid][FIELDS.TITLE]
                else:
                    linked_note = self.get_anki_note_from_evernote_guid(target_evernote_guid)
                    if not linked_note: continue
                    linked_note_contents = u""
                    for fld in linked_note._model['flds']:
                        if FIELDS.CONTENT in fld.get('name'):
                            linked_note_contents = linked_note.fields[fld.get('ord')]
                        elif FIELDS.TITLE in fld.get('name'):
                            linked_note_title = linked_note.fields[fld.get('ord')]
                    if linked_note_contents:
                        linked_notes_fields[target_evernote_guid] = {FIELDS.TITLE: linked_note_title,
                                                                     FIELDS.CONTENT: linked_note_contents}
                if linked_note_contents:
                    if isinstance(linked_note_contents, str):
                        linked_note_contents = unicode(linked_note_contents, 'utf-8')
                    if (is_toc or is_outline) and (toc_count + outline_count is 0):
                        log("  > Found TOC/Outline for Note '%s': %s" % (source_evernote_guid, note_title), 'See Also')
                    if is_toc:
                        toc_count += 1
                        if toc_count is 1:
                            toc_header = "<span class='header'>TABLE OF CONTENTS</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:
                            toc_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (
                                toc_count, linked_note_title)
                            note_toc += "<BR><HR>"

                        note_toc += linked_note_contents
                        log("   > Appending TOC #%d contents" % toc_count, 'See Also')
                    else:
                        outline_count += 1
                        if outline_count is 1:
                            outline_header = "<span class='header'>OUTLINE</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:
                            outline_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (
                                outline_count, linked_note_title)
                            note_outline += "<BR><HR>"

                        note_outline += linked_note_contents
                        log("   > Appending Outline #%d contents" % outline_count, 'See Also')

            if outline_count + toc_count > 0:
                if outline_count > 1:
                    note_outline = "<span class='Outline'>%s</span><BR><BR>" % outline_header + note_outline
                if toc_count > 1:
                    note_toc = "<span class='TOC'>%s</span><BR><BR>" % toc_header + note_toc
                for fld in note._model['flds']:
                    if FIELDS.TOC in fld.get('name'):
                        note.fields[fld.get('ord')] = note_toc
                    elif FIELDS.OUTLINE in fld.get('name'):
                        note.fields[fld.get('ord')] = note_outline
                log(" > Flushing Note \r\n", 'See Also')
                note.flush()

    def start_editing(self):
        self.window().requireReset()

    def stop_editing(self):
        if self.collection():
            self.window().maybeReset()

    @staticmethod
    def window():
        """
        :rtype : AnkiQt
        :return:
        """
        return aqt.mw

    def collection(self):
        return self.window().col

    def models(self):
        return self.collection().models

    def decks(self):
        return self.collection().decks
