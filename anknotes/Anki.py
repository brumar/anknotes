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
from anknotes.base import fmt, encode, decode
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
    from anki.utils import intTime
    import aqt
    from aqt import mw
except Exception:
    pass


class Anki:
    def __init__(self):
        self.deck = None
        self.templates = None

    @staticmethod
    def get_notebook_guid_from_ankdb(evernote_guid):
        return ankDB().scalar("SELECT notebookGuid FROM {n} WHERE guid = '%s'" % evernote_guid)

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
        if deck[:
            2] == '::':
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
        action_str_base = ['Add', 'Update'][update]
        action_str = ['Adding', 'Updating'][update]
        action_preposition = ['To', 'In'][update]
        info = stopwatch.ActionInfo(action_str + ' Of', 'Evernote Notes', action_preposition + ' Anki', report_if_empty=False)
        tmr = stopwatch.Timer(evernote_notes, 10, info=info, 
                              label='Add\\Anki-%sEvernoteNotes' % action_str_base)

        for ankiNote in evernote_notes:
            try:
                title = ankiNote.FullTitle
                content = decode(ankiNote.Content)
                anki_field_info = {
                    FIELDS.TITLE:               title,
                    FIELDS.CONTENT:             content,
                    FIELDS.EVERNOTE_GUID:       FIELDS.EVERNOTE_GUID_PREFIX + ankiNote.Guid,
                    FIELDS.UPDATE_SEQUENCE_NUM: str(ankiNote.UpdateSequenceNum),
                    FIELDS.SEE_ALSO:            u''
                }
            except Exception:
                log_error("Unable to set field info for: Note '%s': '%s'" % (ankiNote.FullTitle, ankiNote.Guid))
                log_dump(ankiNote.Content, " NOTE CONTENTS ")
                # log_dump(encode(ankiNote.Content), " NOTE CONTENTS ")
                raise
            tmr.step(title)
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
                                                    count_update=tmr.counts.updated.completed.val, max_count=tmr.max)
            anki_note_prototype._log_update_if_unchanged_ = log_update_if_unchanged
            nid = tmr.autoStep(anki_note_prototype.update_note() if update else anki_note_prototype.add_note(),
                               ankiNote.FullTitle, update)
            if tmr.status.IsSuccess and not update:
                new_nids.append([nid, ankiNote.Guid])
            elif tmr.status.IsError:
                log("ANKI ERROR WHILE %s EVERNOTE NOTES: " % action_str.upper() + str(tmr.status), tmr.label + '-Error')
        tmr.Report()
        if new_nids:
            ankDB().executemany("UPDATE {n} SET nid = ? WHERE guid = ?", new_nids)
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
        if MODELS.OPTIONS.IMPORT_STYLES:
            return '@import url("%s");' % FILES.ANCILLARY.CSS
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
                    "SELECT uid, shard, COUNT(uid) as c1, COUNT(shard) as c2 from {s} GROUP BY uid, shard ORDER BY c1 DESC, c2 DESC LIMIT 1")
                if info and evernote_account_info.update(info[0], info[1]):
                    forceRebuild = True
            if evernote_account_info.Valid:
                if not "evernote_uid = '%s'" % evernote_account_info.uid in front or not "evernote_shard = '%s'" % evernote_account_info.shard in front:
                    forceRebuild = True
            if model['css'] != model_css:
                forceRebuild = True
            if model['tmpls'][0]['qfmt'] != templates['Front']:
                forceRebuild = True
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
        except Exception:
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
            if not evernote_guid:
                continue
            evernote_guids.append(evernote_guid)
            # log('Anki USN for Note %s is %s' % (evernote_guid, fields[FIELDS.UPDATE_SEQUENCE_NUM]), 'anki-usn')
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
            if evernote_guid:
                evernote_guids[evernote_guid] = fields
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
        if not ids or not ids[0]:
            return None
        note = AnkiNote(col, None, ids[0])
        return note

    def get_anknotes_note_ids_by_tag(self, tag):
        return self.get_anknotes_note_ids("tag:" + tag)

    def get_anknotes_note_ids_with_unadded_see_also(self):
        return self.get_anknotes_note_ids('"See Also" "See_Also:"')

    def process_see_also_content(self, anki_note_ids):
        log = Logger('See Also\\1-process_unadded_see_also_notes\\', rm_path=True)
        tmr = stopwatch.Timer(anki_note_ids, infoStr='Processing Unadded See Also Notes', label=log.base_path)
        tmr.info.BannerHeader('error')
        for a_id in anki_note_ids:
            ankiNote = self.collection().getNote(a_id)
            try:
                items = ankiNote.items()
            except Exception:
                log.error("Unable to get note items for Note ID: %d for %s" % (a_id, tmr.base_name))
                raise
            fields = {}
            for key, value in items:
                fields[key] = value
            if fields[FIELDS.SEE_ALSO]:
                tmr.reportSkipped()
                continue
            anki_note_prototype = AnkiNotePrototype(self, fields, ankiNote.tags, ankiNote, count=tmr.count,
                                                    count_update=tmr.counts.updated.completed.val,
                                                    max_count=tmr.max, light_processing=True)
            if not anki_note_prototype.Fields[FIELDS.SEE_ALSO]:
                tmr.reportSkipped()
                continue
            log.go("Detected see also contents for Note '%s': %s" % (
                get_evernote_guid_from_anki_fields(fields), fields[FIELDS.TITLE]))
            log.go(u" :::   %s " % strip_tags_and_new_lines(fields[FIELDS.SEE_ALSO]))
            tmr.autoStep(anki_note_prototype.update_note(), fields[FIELDS.TITLE], update=True)

    def process_toc_and_outlines(self):
        self.extract_links_from_toc()
        self.insert_toc_into_see_also()
        self.insert_toc_and_outline_contents_into_notes()

    def insert_toc_into_see_also(self):
        db = ankDB()
        db._db.row_factory = None
        results = db.all(
            "SELECT s.target_evernote_guid, s.source_evernote_guid, target_note.title, toc_note.title "
            "FROM {s} as s, {n} as target_note, {n} as toc_note "
            "WHERE s.source_evernote_guid != s.target_evernote_guid AND target_note.guid = s.target_evernote_guid "
            "AND toc_note.guid = s.source_evernote_guid AND s.from_toc == 1 "
            "ORDER BY target_note.title ASC")
        # results_bad = db.all(
        # "SELECT s.target_evernote_guid, s.source_evernote_guid FROM {t_see} as s WHERE s.source_evernote_guid COUNT(SELECT * FROM {tn} WHERE guid = s.source_evernote_guid) )" % (
        # TABLES.SEE_ALSO, TABLES.EVERNOTE.NOTES, TABLES.EVERNOTE.NOTES))
        all_child_guids = db.list("tagNames NOT LIKE '{t_toc}'", columns='guid')
        all_toc_guids = db.list("tagNames LIKE '{t_toc}'", columns='guid')
        grouped_results = {}
        toc_titles = {}
        for row in results:
            target_guid = row[0]
            toc_guid = row[1]
            if toc_guid not in all_toc_guids:
                continue
            if target_guid not in all_toc_guids and target_guid not in all_child_guids:
                continue
            if target_guid not in grouped_results:
                grouped_results[target_guid] = [row[2], []]
            toc_titles[toc_guid] = row[3]
            grouped_results[target_guid][1].append(toc_guid)
        action_title = 'INSERT TOCS INTO ANKI NOTES'
        info = stopwatch.ActionInfo('Inserting TOC Links into', 'Anki Notes', 'Anki Notes\' See Only Field')
        log = Logger('See Also\\5-insert_toc_links_into_see_also\\', rm_path=True)
        tmr = stopwatch.Timer(len(grouped_results), info=info, label=log.base_path)
        tmr.info.BannerHeader('new', crosspost=['invalid', 'error'])
        toc_separator = generate_evernote_span(u' | ', u'Links', u'See Also', bold=False)
        log.add('           <h1>%s: %d TOTAL NOTES</h1> <HR><BR><BR>' % (action_title, tmr.max), 'see_also_html',
                timestamp=False, clear=True,
                extension='htm')
        logged_missing_anki_note = False
        sorted_results = sorted(grouped_results.items(), key=lambda s: s[1][0])
        for target_guid, target_guid_info in sorted_results:
            note_title, toc_guids = target_guid_info
            ankiNote = self.get_anki_note_from_evernote_guid(target_guid)
            # if tmr.step():
            #     log.add("INSERTING TOC LINKS INTO NOTE %5s: %s: %s" % ('#' + str(tmr.count), tmr.progress, note_title),
            #         'progress')
            if not ankiNote:
                log.dump(toc_guids, 'Missing Anki Note for ' + target_guid, tmr.label, timestamp=False,
                         crosspost_to_default=False)
                if not logged_missing_anki_note:
                    log.error('%s: Missing Anki Note(s) for TOC entry. See %s dump log for more details' %
                              (action_title, tmr.label))
                    logged_missing_anki_note = True
                tmr.reportStatus(EvernoteAPIStatus.NotFoundError, title=note_title)
                continue
            fields = get_dict_from_list(ankiNote.items())
            see_also_html = fields[FIELDS.SEE_ALSO]
            content_links = find_evernote_links_as_guids(fields[FIELDS.CONTENT])
            see_also_whole_links = find_evernote_links(see_also_html)
            see_also_links = {x.Guid for x in see_also_whole_links}
            invalid_see_also_links = {x for x in see_also_links if x not in all_child_guids and x not in all_toc_guids}
            new_tocs = set(toc_guids) - see_also_links
            if TAGS.TOC_AUTO in ankiNote.tags:
                new_tocs -= set(content_links)
            log.dump([new_tocs, toc_guids, invalid_see_also_links, see_also_links, content_links],
                     'TOCs for %s' % fields[FIELDS.TITLE] + ' vs ' + note_title, 'new_tocs',
                     crosspost_to_default=False)
            new_toc_count = len(new_tocs)
            invalid_see_also_links_count = len(invalid_see_also_links)
            if invalid_see_also_links_count > 0:
                for link in see_also_whole_links:
                    if link.Guid in invalid_see_also_links:
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
                        'ol': u'<br><div style="margin-top:5px;">\n%s</div><ol style="margin-top:3px;">' %
                              generate_evernote_span('<u>TABLE OF CONTENTS</u>:', 'Levels', 'Auto TOC', escape=False)
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
                                                               'TOC') + see_also_html + u'<HR>', 'see_also_html',
                    crosspost='see_also_html\\' + note_title, timestamp=False, extension='htm')
            see_also_html = see_also_html.replace('evernote:///', 'evernote://')
            changed = see_also_html != fields[FIELDS.SEE_ALSO]

            fields[FIELDS.SEE_ALSO] = see_also_html
            anki_note_prototype = AnkiNotePrototype(self, fields, ankiNote.tags, ankiNote, count=tmr.counts.handled,
                                                    count_update=tmr.counts.updated.completed.val, max_count=tmr.max,
                                                    light_processing=True, steps=[0, 1, 7])
            anki_note_prototype._log_update_if_unchanged_ = (
                changed or new_toc_count + invalid_see_also_links_count > 0)
            tmr.autoStep(anki_note_prototype.update_note(error_if_unchanged=changed), note_title, True)

            crosspost = []
            if new_toc_count:
                crosspost.append('new')
            if invalid_see_also_links:
                crosspost.append('invalid')
            if tmr.status.IsError:
                crosspost.append('error')
            log.go('  %s  |  %2d TOTAL TOC''s  |  %s  |  %s  |    %s%s' % (
                format_count('%2d NEW TOC''s', new_toc_count), len(toc_guids),
                format_count('%2d EXISTING LINKS', see_also_count),
                format_count('%2d INVALID LINKS', invalid_see_also_links_count),
                ('*' if changed else ' ') * 3, note_title), crosspost=crosspost, timestamp=False)

        db._db.row_factory = sqlite.Row

    def extract_links_from_toc(self):
        db = ankDB(TABLES.SEE_ALSO)
        db.setrowfactory()
        toc_entries = db.all("SELECT * FROM {n} WHERE tagNames LIKE '{t_toc}' ORDER BY title ASC")
        db.execute("DELETE FROM {t} WHERE from_toc = 1")
        log = Logger('See Also\\4-extract_links_from_toc\\', timestamp=False, crosspost_to_default=False, rm_path=True)
        tmr = stopwatch.Timer(toc_entries, 20, infoStr='Extracting Links', label=log.base_path)
        tmr.info.BannerHeader('error')
        toc_guids = []
        for toc_entry in toc_entries:
            toc_evernote_guid, toc_link_title = toc_entry['guid'], toc_entry['title']
            toc_guids.append("'%s'" % toc_evernote_guid)
            # toc_link_html = generate_evernote_span(toc_link_title, 'Links', 'TOC')
            enLinks = find_evernote_links(toc_entry['content'])
            tmr.increment(toc_link_title)
            for enLink in enLinks:
                target_evernote_guid = enLink.Guid
                if not check_evernote_guid_is_valid(target_evernote_guid):
                    log.go("Invalid Target GUID for %-70s %s" % (toc_link_title + ':', target_evernote_guid), 'error')
                    continue
                base = {
                    'child_guid': target_evernote_guid, 'uid': enLink.Uid,
                    'shard':    enLink.Shard, 'toc_guid': toc_evernote_guid, 'l1': 'source', 'l2': 'source',
                    'from_toc': 0, 'is_toc': 0
                }
                query_count = "select COUNT(*) from {t} WHERE source_evernote_guid = '{%s_guid}'"
                toc = {
                    'num':      1 + db.scalar(fmt(query_count % 'toc', base)),
                    'html':     enLink.HTML.replace(u'\'', u'\'\''),
                    'title':    enLink.FullTitle.replace(u'\'', u'\'\''),
                    'l1':       'target',
                    'from_toc': 1
                }
                # child = {1 + db.scalar(fmt(query_count % 'child', base)),
                # 'html': toc_link_html.replace(u'\'', u'\'\''),
                # 'title': toc_link_title.replace(u'\'', u'\'\''),
                # 'l2': 'target',
                # 'is_toc': 1
                # }
                query = (u"INSERT OR REPLACE INTO `{t}`(`{l1}_evernote_guid`, `number`, `uid`, `shard`, "
                         u"`{l2}_evernote_guid`, `html`, `title`, `from_toc`, `is_toc`) "
                         u"VALUES('{child_guid}', {num}, {uid}, '{shard}', "
                         u"'{toc_guid}', '{html}', '{title}', {from_toc}, {is_toc})")
                query_toc = fmt(query, base, toc)
                db.execute(query_toc)
            log.go("\t\t - Added %2d child link(s) from TOC %s" % (len(enLinks), encode(toc_link_title)))
        db.update("is_toc = 1", where="target_evernote_guid IN (%s)" % ', '.join(toc_guids))
        db.commit()

    def insert_toc_and_outline_contents_into_notes(self):
        linked_notes_fields = {}
        db = ankDB(TABLES.SEE_ALSO)
        source_guids = db.list("SELECT DISTINCT s.source_evernote_guid FROM {s} s, {n} n WHERE (s.is_toc = 1 OR "
                               "s.is_outline = 1) AND s.source_evernote_guid = n.guid ORDER BY n.title ASC")
        info = stopwatch.ActionInfo('Insertion of', 'TOC/Outline Contents', 'Into Target Anki Notes')
        log = Logger('See Also\\8-insert_toc_contents\\', rm_path=True, timestamp=False)
        tmr = stopwatch.Timer(source_guids, 25, info=info, label=log.base_path)
        tmr.info.BannerHeader('error')
        for source_guid in source_guids:
            note = self.get_anki_note_from_evernote_guid(source_guid)
            if not note:
                tmr.reportStatus(EvernoteAPIStatus.NotFoundError)
                log.error("Could not find note for %s for %s" % (note.guid, tmr.base_name))
                continue
            # if TAGS.TOC in note.tags:
                # tmr.reportSkipped()
                # continue
            for fld in note._model['flds']:
                if FIELDS.TITLE in fld.get('name'):
                    note_title = note.fields[fld.get('ord')]
                    continue
            if not note_title:
                tmr.reportStatus(EvernoteAPIStatus.NotFoundError)
                log.error("Could not find note title for %s for %s" % (note.guid, tmr.base_name))
                continue
            tmr.step(note_title)
            note_toc = ""
            note_outline = ""
            toc_header = ""
            outline_header = ""
            toc_count = 0
            outline_count = 0
            toc_and_outline_links = db.execute("source_evernote_guid = '%s' AND (is_toc = 1 OR is_outline = 1) "
                                               "ORDER BY number ASC" % source_guid,
                                               columns='target_evernote_guid, is_toc, is_outline')
            for target_evernote_guid, is_toc, is_outline in toc_and_outline_links:
                if target_evernote_guid in linked_notes_fields:
                    linked_note_contents = linked_notes_fields[target_evernote_guid][FIELDS.CONTENT]
                    linked_note_title = linked_notes_fields[target_evernote_guid][FIELDS.TITLE]
                else:
                    linked_note = self.get_anki_note_from_evernote_guid(target_evernote_guid)
                    if not linked_note:
                        continue
                    linked_note_contents = u""
                    for fld in linked_note._model['flds']:
                        if FIELDS.CONTENT in fld.get('name'):
                            linked_note_contents = linked_note.fields[fld.get('ord')]
                        elif FIELDS.TITLE in fld.get('name'):
                            linked_note_title = linked_note.fields[fld.get('ord')]
                    if linked_note_contents:
                        linked_notes_fields[target_evernote_guid] = {
                            FIELDS.TITLE:   linked_note_title,
                            FIELDS.CONTENT: linked_note_contents
                        }
                if linked_note_contents:
                    linked_note_contents = decode(linked_note_contents)
                    if is_toc:
                        toc_count += 1
                        if toc_count is 1:
                            toc_header = "<span class='header'>TABLE OF CONTENTS</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:
                            note_toc += "<br><hr>"; toc_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (
                            toc_count, linked_note_title)
                        note_toc += linked_note_contents
                    else:
                        outline_count += 1
                        if outline_count is 1:
                            outline_header = "<span class='header'>OUTLINE</span>: 1. <span class='header'>%s</span>" % linked_note_title
                        else:
                            note_outline += "<BR><HR>";  outline_header += "<span class='See_Also'> | </span> %d. <span class='header'>%s</span>" % (
                            outline_count, linked_note_title)
                        note_outline += linked_note_contents
            if outline_count + toc_count is 0:
                tmr.reportError(EvernoteAPIStatus.MissingDataError)
                log.error(" No Valid TOCs or Outlines Found: %s" % note_title)
                continue
            tmr.reportSuccess()

            def makestr(title, count):
                return '' if not count else 'One %s ' % title if count is 1 else '%s %ss' % (str(count).center(3), title)

            toc_str = makestr('TOC', toc_count).rjust(8) #if toc_count else ''
            outline_str = makestr('Outline', outline_count).ljust(12) #if outline_count else ''
            toc_str += ' &  ' if toc_count and outline_count else '    '

            log.go(" [%4d/%4d]  +   %s   for Note %s:   %s" % (
                            tmr.count, tmr.max, toc_str + outline_str, source_guid.split('-')[0], note_title))

            if outline_count > 1:
                note_outline = "<span class='Outline'>%s</span><BR><BR>" % outline_header + note_outline
            if toc_count > 1:
                note_toc = "<span class='TOC'>%s</span><BR><BR>" % toc_header + note_toc
            for fld in note._model['flds']:
                if FIELDS.TOC in fld.get('name'):
                    note.fields[fld.get('ord')] = note_toc
                elif FIELDS.OUTLINE in fld.get('name'):
                    note.fields[fld.get('ord')] = note_outline
            # log.go(' '*16 + "> Flushing Note \r\n")
            note.flush(intTime())
        tmr.Report()

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
