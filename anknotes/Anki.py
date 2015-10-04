# -*- coding: utf-8 -*-
### Python Imports
import shutil
import sys
import re

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
from anknotes.AnkiNotePrototype import AnkiNotePrototype
from anknotes.shared import *
from anknotes import stopwatch
### Evernote Imports
# from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
# from evernote.edam.type.ttypes import NoteSortOrder, Note
# from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode, EDAMUserException, EDAMNotFoundException
# from evernote.api.client import EvernoteClient

### Anki Imports
try:
    import anki
    from anki.notes import Note as AnkiNote
    import aqt
    from aqt import mw
except: pass


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
            notebook = EvernoteNotebook(fetch_guid=notebookGuid)
            if not notebook.success:
                log_error(
                    "   get_deck_name_from_evernote_notebook FATAL ERROR: UNABLE TO FIND NOTEBOOK '%s'. " % notebookGuid)
                return None
            # log("Getting notebook info: %s" % str(notebook))
            self.notebook_data[notebookGuid] = notebook
        notebook = self.notebook_data[notebookGuid]
        if notebook.Stack:
            deck += u'::' + notebook.Stack
        deck += "::" + notebook.Name
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
        new_nids=[]
        action_str = ['ADDING', 'UPDATING'][update]
        tmr = stopwatch.Timer(len(evernote_notes), 100,
                              infoStr=action_str + " EVERNOTE NOTE(S) %s ANKI" % ['TO', 'IN'][update],
                              label='AddEvernoteNotes')

        for ankiNote in evernote_notes:
            try:
                title = ankiNote.FullTitle
                content = ankiNote.Content
                if isinstance(content, str):
                    content = unicode(content, 'utf-8')
                anki_field_info = {
                    FIELDS.TITLE:               title,
                    FIELDS.CONTENT:             content,
                    FIELDS.EVERNOTE_GUID:       FIELDS.EVERNOTE_GUID_PREFIX + ankiNote.Guid,
                    FIELDS.UPDATE_SEQUENCE_NUM: str(ankiNote.UpdateSequenceNum),
                    FIELDS.SEE_ALSO:            u''
                }
            except:
                log_error("Unable to set field info for: Note '%s': '%s'" % (ankiNote.Title, ankiNote.Guid))
                log_dump(ankiNote.Content, " NOTE CONTENTS ")
                # log_dump(ankiNote.Content.encode('utf-8'), " NOTE CONTENTS ")
                raise
            if tmr.step():
                log(['Adding', 'Updating'][update] + " Note %5s: %s: %s" % ('#' + str(tmr.count), tmr.progress, title),
                    tmr.label)
            baseNote = None
            if update:
                baseNote = self.get_anki_note_from_evernote_guid(ankiNote.Guid)
                if not baseNote:
                    log_error('Updating note %s: COULD NOT FIND BASE NOTE FOR ANKI NOTE ID' % ankiNote.Guid)
                    tmr.reportStatus(EvernoteAPIStatus.MissingDataError)
                    continue
            if ankiNote.Tags is None:
                log_error("Could note find tags object for note %s: %s. " % (ankiNote.Guid, ankiNote.FullTitle))
                tmr.reportStatus(EvernoteAPIStatus.MissingDataError)
                continue
            anki_note_prototype = AnkiNotePrototype(self, anki_field_info, ankiNote.TagNames, baseNote,
                                                    notebookGuid=ankiNote.NotebookGuid, count=tmr.count,
                                                    count_update=tmr.counts.success, max_count=tmr.max)
            anki_note_prototype._log_update_if_unchanged_ = log_update_if_unchanged
            anki_result = anki_note_prototype.update_note() if update else anki_note_prototype.add_note()
            if anki_result != -1: 
                tmr.reportSuccess(update, True)
                if not update:
                    new_nids.append([anki_result, ankiNote.Guid])
            else:
                tmr.reportError(True)
                log("ANKI ERROR WHILE %s EVERNOTE NOTES: " % action_str + str(anki_result), 'AddEvernoteNotes-Error')
        tmr.Report()
        if len(new_nids) > 0:
            ankDB().executemany("UPDATE %s SET nid = ? WHERE guid = ?" % TABLES.EVERNOTE.NOTES, new_nids)
        return tmr.counts.success

    def delete_anki_cards(self, evernote_guids):
        col = self.collection()
        card_ids = []
        for evernote_guid in evernote_guids:
            card_ids += mw.col.findCards(FIELDS.EVERNOTE_GUID_PREFIX + evernote_guid)
        col.remCards(card_ids)
        return len(card_ids)

    @staticmethod
    def get_evernote_model_styles():
        if MODELS.OPTIONS.IMPORT_STYLES: return '@import url("%s");' % FILES.ANCILLARY.CSS
        return file(os.path.join(FOLDERS.ANCILLARY, FILES.ANCILLARY.CSS), 'r').read()

    def add_evernote_model(self, mm, modelName, forceRebuild=False, cloze=False, allowForceRebuild=True):
        model = mm.byName(modelName)
        model_css = self.get_evernote_model_styles()
        templates = self.get_templates(modelName == MODELS.DEFAULT)
        if model and modelName is MODELS.DEFAULT and allowForceRebuild:
            front = model['tmpls'][0]['qfmt']
            evernote_account_info = get_evernote_account_ids()
            if not evernote_account_info.Valid:
                info = ankDB().first(
                    "SELECT uid, shard, COUNT(uid) as c1, COUNT(shard) as c2 from %s GROUP BY uid, shard ORDER BY c1 DESC, c2 DESC LIMIT 1" % TABLES.SEE_ALSO)
                if info and evernote_account_info.update(info[0], info[1]): forceRebuild = True
            if evernote_account_info.Valid:
                if not "evernote_uid = '%s'" % evernote_account_info.uid in front or not "evernote_shard = '%s'" % evernote_account_info.shard in front: forceRebuild = True
            if model['css'] != model_css: forceRebuild = True
            if model['tmpls'][0]['qfmt'] != templates['Front']: forceRebuild = True
        if not model or forceRebuild:
            if model:
                for t in model['tmpls']:
                    t['qfmt'] = templates['Front']
                    t['afmt'] = templates['Back']
                model['css'] = model_css
                mm.update(model)
            else:
                model = mm.new(modelName)
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

                if modelName is MODELS.DEFAULT or modelName is MODELS.REVERSIBLE:
                    # Add Default Template
                    default_template = mm.newTemplate(TEMPLATES.DEFAULT)
                    default_template['qfmt'] = templates['Front']
                    default_template['afmt'] = templates['Back']
                    mm.addTemplate(model, default_template)
                if modelName is MODELS.REVERSE_ONLY or modelName is MODELS.REVERSIBLE:
                    # Add Reversed Template
                    reversed_template = mm.newTemplate(TEMPLATES.REVERSED)
                    reversed_template['qfmt'] = templates['Front']
                    reversed_template['afmt'] = templates['Back']
                    mm.addTemplate(model, reversed_template)
                if modelName is MODELS.CLOZE:
                    # Add Cloze Template
                    cloze_template = mm.newTemplate(TEMPLATES.CLOZE)
                    cloze_template['qfmt'] = templates['Front']
                    cloze_template['afmt'] = templates['Back']
                    mm.addTemplate(model, cloze_template)

                # Update Sort field to Title (By default set to GUID since it is the first field)
                model['sortf'] = 1

                # Update Model CSS
                model['css'] = model_css

                # Set Type to Cloze
                if cloze:
                    model['type'] = MODELS.TYPES.CLOZE

                # Add Model to Collection
                mm.add(model)

                # Add Model id to list
        self.evernoteModels[modelName] = model['id']
        return forceRebuild

    def get_templates(self, forceRebuild=False):
        if not self.templates or forceRebuild:
            evernote_account_info = get_evernote_account_ids()
            field_names = {
                "Title":                FIELDS.TITLE, "Content": FIELDS.CONTENT, "Extra": FIELDS.EXTRA,
                "See Also":             FIELDS.SEE_ALSO, "TOC": FIELDS.TOC, "Outline": FIELDS.OUTLINE,
                "Evernote GUID Prefix": FIELDS.EVERNOTE_GUID_PREFIX, "Evernote GUID": FIELDS.EVERNOTE_GUID,
                "Evernote UID":         evernote_account_info.uid, "Evernote shard": evernote_account_info.shard
            }
            # Generate Front and Back Templates from HTML Template in anknotes' addon directory
            self.templates = {"Front": file(FILES.ANCILLARY.TEMPLATE, 'r').read() % field_names}
            self.templates["Back"] = self.templates["Front"].replace("<div id='Side-Front'>", "<div id='Side-Back'>")
        return self.templates

    def add_evernote_models(self, allowForceRebuild=True):
        col = self.collection()
        mm = col.models
        self.evernoteModels = {}

        forceRebuild = self.add_evernote_model(mm, MODELS.DEFAULT, allowForceRebuild=allowForceRebuild)
        self.add_evernote_model(mm, MODELS.REVERSE_ONLY, forceRebuild)
        self.add_evernote_model(mm, MODELS.REVERSIBLE, forceRebuild)
        self.add_evernote_model(mm, MODELS.CLOZE, forceRebuild, True)

    def setup_ancillary_files(self):
        # Copy CSS file from anknotes addon directory to media directory
        media_dir = re.sub("(?i)\.(anki2)$", ".media", self.collection().path)
        if isinstance(media_dir, str):
            media_dir = unicode(media_dir, sys.getfilesystemencoding())
        shutil.copy2(os.path.join(FOLDERS.ANCILLARY, FILES.ANCILLARY.CSS), os.path.join(media_dir, FILES.ANCILLARY.CSS))

    def get_anki_fields_from_anki_note_id(self, a_id, fields_to_ignore=list()):
        note = self.collection().getNote(a_id)
        try:
            items = note.items()
        except:
            log_error("Unable to get note items for Note ID: %d" % a_id)
            raise
        return get_dict_from_list(items, fields_to_ignore)

    def get_evernote_guids_from_anki_note_ids(self, ids=None):
        if ids is None:
            ids = self.get_anknotes_note_ids()
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

    def get_evernote_guids_and_anki_fields_from_anki_note_ids(self, ids=None):
        if ids is None:
            ids = self.get_anknotes_note_ids()
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
                    log(u" :::   %s " % strip_tags_and_new_lines(fields[FIELDS.SEE_ALSO]))
                    if anki_note_prototype.update_note():
                        count_update += 1
            count += 1

    def process_toc_and_outlines(self):
        self.extract_links_from_toc()
        self.insert_toc_into_see_also()
        self.insert_toc_and_outline_contents_into_notes()

    def update_evernote_note_contents(self):
        see_also_notes = ankDB().all("SELECT DISTINCT target_evernote_guid FROM %s WHERE 1" % TABLES.SEE_ALSO)

    def insert_toc_into_see_also(self):
        log = Logger(rm_path=True)
        db = ankDB()
        db._db.row_factory = None
        results = db.all(
            "SELECT s.target_evernote_guid, s.source_evernote_guid, target_note.title, toc_note.title FROM %s as s, %s as target_note, %s as toc_note WHERE s.source_evernote_guid != s.target_evernote_guid AND target_note.guid = s.target_evernote_guid AND toc_note.guid = s.source_evernote_guid AND s.from_toc == 1 AND (target_note.title LIKE '%%Cervicitis%%' OR 1) ORDER BY target_note.title ASC" % (
                TABLES.SEE_ALSO, TABLES.EVERNOTE.NOTES, TABLES.EVERNOTE.NOTES))
        # results_bad = db.all(
        # "SELECT s.target_evernote_guid, s.source_evernote_guid FROM {t_see} as s WHERE s.source_evernote_guid COUNT(SELECT * FROM {tn} WHERE guid = s.source_evernote_guid) )" % (
        # TABLES.SEE_ALSO, TABLES.EVERNOTE.NOTES, TABLES.EVERNOTE.NOTES))
        all_child_guids = db.list(
            "SELECT guid FROM %s WHERE tagNames NOT LIKE '%%,%s,%%'" % (TABLES.EVERNOTE.NOTES, TAGS.TOC))
        all_toc_guids = db.list(
            "SELECT guid FROM %s WHERE tagNames LIKE '%%,%s,%%'" % (TABLES.EVERNOTE.NOTES, TAGS.TOC))
        grouped_results = {}
        # assert [x for x in results if x[0] == 'f78e4dca-3b20-41f2-a4f9-ab6cb4b0c8e3']
        toc_titles = {}
        for row in results:
            target_guid = row[0]
            toc_guid = row[1]
            if toc_guid not in all_toc_guids: continue
            if target_guid not in all_toc_guids and target_guid not in all_child_guids: continue
            if target_guid not in grouped_results: grouped_results[target_guid] = [row[2], []]
            toc_titles[toc_guid] = row[3]
            grouped_results[target_guid][1].append(toc_guid)
        tmr = stopwatch.Timer(len(grouped_results), label='insert_toc')
        action_title = 'INSERT TOCS INTO ANKI NOTES'
        log.banner(action_title + ': %d TARGET ANKI NOTES' % tmr.max, tmr.label,
                   crosspost=[tmr.label + '-new', tmr.label + '-invalid'], clear=True)
        toc_separator = generate_evernote_span(u' | ', u'Links', u'See Also', bold=False)
        count = 0
        count_update = 0
        log.add('           <h1>%s: %d TOTAL NOTES</h1> <HR><BR><BR>' % (action_title, tmr.max), 'see_also',
                timestamp=False, clear=True,
                extension='htm')
        logged_missing_anki_note = False
        # sorted_results = sorted(grouped_results.items(), key=lambda s: s[1][0])
        # log.add(sorted_results)
        for target_guid, target_guid_info in sorted(grouped_results.items(), key=lambda s: s[1][0]):
            note_title, toc_guids = target_guid_info
            ankiNote = self.get_anki_note_from_evernote_guid(target_guid)
            if not ankiNote:
                log.dump(toc_guids, 'Missing Anki Note for ' + target_guid, tmr.label, timestamp=False,
                         crosspost_to_default=False)
                if not logged_missing_anki_note:
                    log_error(
                        '%s: Missing Anki Note(s) for TOC entry. See insert_toc log for more details' % action_title)
                    logged_missing_anki_note = True
                continue
            fields = get_dict_from_list(ankiNote.items())
            see_also_html = fields[FIELDS.SEE_ALSO]
            content_links = find_evernote_links_as_guids(fields[FIELDS.CONTENT])
            see_also_whole_links = find_evernote_links(see_also_html)
            see_also_links = {x.Guid for x in see_also_whole_links}
            invalid_see_also_links = {x for x in see_also_links if x not in all_child_guids and x not in all_toc_guids}
            new_tocs = set(toc_guids) - see_also_links - set(content_links)
            log.dump([new_tocs, toc_guids, invalid_see_also_links, see_also_links, content_links],
                     'TOCs for %s' % fields[FIELDS.TITLE] + ' vs ' + note_title, 'insert_toc_new_tocs',
                     crosspost_to_default=False)
            new_toc_count = len(new_tocs)
            invalid_see_also_links_count = len(invalid_see_also_links)
            if invalid_see_also_links_count > 0:
                for link in see_also_whole_links:
                    if link.Guid not in invalid_see_also_links: continue
                    see_also_html = remove_evernote_link(link, see_also_html)
            see_also_links -= invalid_see_also_links
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
                    find_div_end = see_also_html.rfind('</div>')
                    if find_div_end > -1:
                        see_also_html = see_also_html[:find_div_end] + see_also_new + '\n' + see_also_html[
                                                                                             find_div_end:]
                        see_also_new = ''
                else:
                    see_also_toc_headers = {
                        'ol': u'<br><div style="margin-top:5px;">\n%s</div><ol style="margin-top:3px;">' % generate_evernote_span(
                            '<u>TABLE OF CONTENTS</u>:', 'Levels', 'Auto TOC', escape=False)
                    }
                    see_also_toc_headers['ul'] = see_also_toc_headers['ol'].replace('<ol ', '<ul ')

                    if see_also_toc_headers['ul'] in see_also_html:
                        find_ul_end = see_also_html.rfind('</ul>')
                        see_also_html = see_also_html[:find_ul_end] + '</ol>' + see_also_html[find_ul_end + 5:]
                        see_also_html = see_also_html.replace(see_also_toc_headers['ul'], see_also_toc_headers['ol'])
                    if see_also_toc_headers['ol'] in see_also_html:
                        find_ol_end = see_also_html.rfind('</ol>')
                        see_also_html = see_also_html[:find_ol_end] + see_also_new + '\n' + see_also_html[find_ol_end:]
                        see_also_new = ''
                    else:
                        header_type = 'ul' if new_toc_count is 1 else 'ol'
                        see_also_new = see_also_toc_headers[header_type] + u'%s\n</%s>' % (see_also_new, header_type)
                if see_also_count == 0:
                    see_also_html = generate_evernote_span(u'See Also:', 'Links', 'See Also')
                see_also_html += see_also_new
            see_also_html = see_also_html.replace('<ol>', '<ol style="margin-top:3px;">')
            log.add('<h3>%s</h3><br>' % generate_evernote_span(fields[FIELDS.TITLE], 'Links',
                                                               'TOC') + see_also_html + u'<HR>', 'see_also',
                    crosspost='see_also\\' + note_title, timestamp=False, extension='htm')
            see_also_html = see_also_html.replace('evernote:///', 'evernote://')
            changed = see_also_html != fields[FIELDS.SEE_ALSO]
            crosspost = []
            if new_toc_count: crosspost.append(tmr.label + '-new')
            if invalid_see_also_links: crosspost.append(tmr.label + '-invalid')
            log.go('  %s  |  %2d TOTAL TOC''s  |  %s  |  %s  |    %s%s' % (
                format_count('%2d NEW TOC''s', new_toc_count), len(toc_guids),
                format_count('%2d EXISTING LINKS', see_also_count),
                format_count('%2d INVALID LINKS', invalid_see_also_links_count), ('*' if changed else ' ') * 3,
                note_title),
                   tmr.label, crosspost=crosspost, timestamp=False)

            fields[FIELDS.SEE_ALSO] = see_also_html
            anki_note_prototype = AnkiNotePrototype(self, fields, ankiNote.tags, ankiNote, count=count,
                                                    count_update=count_update, max_count=tmr.max)
            anki_note_prototype._log_update_if_unchanged_ = (
                changed or new_toc_count + invalid_see_also_links_count > 0)
            if anki_note_prototype.update_note(): count_update += 1
            count += 1
        db._db.row_factory = sqlite.Row

    def extract_links_from_toc(self):
        db = ankDB()
        db.setrowfactory()
        toc_entries = db.all(
            "SELECT * FROM %s WHERE tagNames LIKE '%%,%s,%%' ORDER BY title ASC" % (TABLES.EVERNOTE.NOTES, TAGS.TOC))
        db.execute("DELETE FROM %s WHERE from_toc = 1" % TABLES.SEE_ALSO)
        l = Logger(timestamp=False, crosspost_to_default=False)
        l.banner('EXTRACTING LINKS FROM %3d TOC ENTRIES' % len(toc_entries), clear=True, crosspost='error')
        toc_guids = []
        for i, toc_entry in enumerate(toc_entries):
            toc_evernote_guid, toc_link_title = toc_entry['guid'], toc_entry['title']
            toc_guids.append("'%s'" % toc_evernote_guid)
            toc_link_html = generate_evernote_span(toc_link_title, 'Links', 'TOC')
            enLinks = find_evernote_links(toc_entry['content'])
            for enLink in enLinks:
                target_evernote_guid = enLink.Guid
                if not check_evernote_guid_is_valid(target_evernote_guid): l.go(
                    "Invalid Target GUID for %-50s %s" % (toc_link_title + ':', target_evernote_guid),
                    'error'); continue
                base = {
                    't':        TABLES.SEE_ALSO, 'child_guid': target_evernote_guid, 'uid': enLink.Uid,
                    'shard':    enLink.Shard, 'toc_guid': toc_evernote_guid, 'l1': 'source', 'l2': 'source',
                    'from_toc': 0, 'is_toc': 0
                }
                query_count = "select COUNT(*) from {t} WHERE source_evernote_guid = '{%s_guid}'"
                toc = {
                    'num':      1 + db.scalar((query_count % 'toc').format(**base)),
                    'html':     enLink.HTML.replace(u'\'', u'\'\''),
                    'title':    enLink.FullTitle.replace(u'\'', u'\'\''),
                    'l1':       'target',
                    'from_toc': 1
                }
                # child = {'num': 1 + db.scalar((query_count % 'child').format(**base)),
                # 'html': toc_link_html.replace(u'\'', u'\'\''),
                # 'title': toc_link_title.replace(u'\'', u'\'\''),
                # 'l2': 'target',
                # 'is_toc': 1
                # }
                query = u"INSERT OR REPLACE INTO `{t}`(`{l1}_evernote_guid`, `number`, `uid`, `shard`, `{l2}_evernote_guid`, `html`, `title`, `from_toc`, `is_toc`) VALUES('{child_guid}', {num}, {uid}, '{shard}', '{toc_guid}', '{html}', '{title}', {from_toc}, {is_toc})"
                query_toc = query.format(**DictCaseInsensitive(base, toc))
                db.execute(query_toc)
                # db.execute(query.format(**DictCaseInsensitive(base, child)))
            l.go("\t\t - Added %2d child link(s) from TOC %s" % (len(enLinks), toc_link_title.encode('utf-8')))
        db.execute(
            "UPDATE %s SET is_toc = 1 WHERE target_evernote_guid IN (%s)" % (TABLES.SEE_ALSO, ', '.join(toc_guids)))
        db.commit()

    def insert_toc_and_outline_contents_into_notes(self):
        linked_notes_fields = {}
        source_guids = ankDB().list(
            "select DISTINCT source_evernote_guid from %s WHERE is_toc = 1 OR is_outline = 1 ORDER BY source_evernote_guid ASC" % TABLES.SEE_ALSO)
        source_guids_count = len(source_guids)
        i = 0
        for source_guid in source_guids:
            i += 1
            note = self.get_anki_note_from_evernote_guid(source_guid)
            if not note: continue
            if TAGS.TOC in note.tags: continue
            for fld in note._model['flds']:
                if FIELDS.TITLE in fld.get('name'): note_title = note.fields[fld.get('ord')]; continue
            if not note_title: log_error(
                "Could not find note title for %s for insert_toc_and_outline_contents_into_notes" % note.guid); continue
            note_toc = ""
            note_outline = ""
            toc_header = ""
            outline_header = ""
            toc_count = 0
            outline_count = 0
            toc_and_outline_links = ankDB().execute(
                "select target_evernote_guid, is_toc, is_outline from %s WHERE source_evernote_guid = '%s' AND (is_toc = 1 OR is_outline = 1) ORDER BY number ASC" % (
                    TABLES.SEE_ALSO, source_guid))
            for target_evernote_guid, is_toc, is_outline in toc_and_outline_links:
                if target_evernote_guid in linked_notes_fields:
                    linked_note_contents = linked_notes_fields[target_evernote_guid][FIELDS.CONTENT]
                    linked_note_title = linked_notes_fields[target_evernote_guid][FIELDS.TITLE]
                else:
                    linked_note = self.get_anki_note_from_evernote_guid(target_evernote_guid)
                    if not linked_note: continue
                    linked_note_contents = u""
                    for fld in linked_note._model['flds']:
                        if FIELDS.CONTENT in fld.get('name'): linked_note_contents = linked_note.fields[fld.get('ord')]
                        elif FIELDS.TITLE in fld.get('name'): linked_note_title = linked_note.fields[fld.get('ord')]
                    if linked_note_contents:
                        linked_notes_fields[target_evernote_guid] = {
                            FIELDS.TITLE:   linked_note_title,
                            FIELDS.CONTENT: linked_note_contents
                        }
                if linked_note_contents:
                    if isinstance(linked_note_contents, str):
                        linked_note_contents = unicode(linked_note_contents, 'utf-8')
                    if (is_toc or is_outline) and (toc_count + outline_count is 0):
                        log("  > [%3d/%3d]  Found TOC/Outline for Note '%s': %s" % (
                            i, source_guids_count, source_guid, note_title), 'See Also')
                    if is_toc:
                        toc_count += 1
                        if toc_count is 1: toc_header = "<span class='header'>TABLE OF CONTENTS</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else: note_toc += "<br><hr>"; toc_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (
                            toc_count, linked_note_title)
                        note_toc += linked_note_contents
                        log("   > Appending TOC #%d contents" % toc_count, 'See Also')
                    else:
                        outline_count += 1
                        if outline_count is 1: outline_header = "<span class='header'>OUTLINE</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else: note_outline += "<BR><HR>";  outline_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (
                            outline_count, linked_note_title)
                        note_outline += linked_note_contents
                        log("   > Appending Outline #%d contents" % outline_count, 'See Also')
            if outline_count + toc_count is 0: continue
            if outline_count > 1: note_outline = "<span class='Outline'>%s</span><BR><BR>" % outline_header + note_outline
            if toc_count > 1: note_toc = "<span class='TOC'>%s</span><BR><BR>" % toc_header + note_toc
            for fld in note._model['flds']:
                if FIELDS.TOC in fld.get('name'): note.fields[fld.get('ord')] = note_toc
                elif FIELDS.OUTLINE in fld.get('name'): note.fields[fld.get('ord')] = note_outline
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
