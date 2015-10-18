# -*- coding: utf-8 -*-
import shutil
import sys

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

from anknotes.shared import *
from anknotes import stopwatch

from anknotes.EvernoteNotePrototype import EvernoteNotePrototype
from anknotes.AnkiNotePrototype import AnkiNotePrototype
from enum import Enum
from anknotes.enums import *
from anknotes.structs import EvernoteAPIStatus

Error = sqlite.Error
ankDBSetLocal()
from anknotes.ankEvernote import Evernote
from anknotes.Anki import Anki


class notes:
    class version(object):
        class pstrings:
            __updated = None
            __processed = None
            __original = None
            __regex_updated = None
            """: type : notes.version.see_also_match """
            __regex_processed = None
            """: type : notes.version.see_also_match """
            __regex_original = None
            """: type : notes.version.see_also_match """

            @property
            def regex_original(self):
                if self.original is None:
                    return None
                if self.__regex_original is None:
                    self.__regex_original = notes.version.see_also_match(self.original)
                return self.__regex_original

            @property
            def regex_processed(self):
                if self.processed is None:
                    return None
                if self.__regex_processed is None:
                    self.__regex_processed = notes.version.see_also_match(self.processed)
                return self.__regex_processed

            @property
            def regex_updated(self):
                if self.updated is None:
                    return None
                if self.__regex_updated is None:
                    self.__regex_updated = notes.version.see_also_match(self.updated)
                return self.__regex_updated

            @property
            def processed(self):
                if self.__processed is None:
                    self.__processed = str_process(self.original)
                return self.__processed

            @property
            def updated(self):
                if self.__updated is None:
                    return str_process(self.__original)
                return self.__updated

            @updated.setter
            def updated(self, value):
                self.__regex_updated = None
                self.__updated = value

            @property
            def final(self):
                return str_process_full(self.updated)

            @property
            def original(self):
                return self.__original

            def useProcessed(self):
                self.updated = self.processed

            def __init__(self, original=None):
                self.__original = original

        class see_also_match(object):
            __subject = None
            __content = None
            __matchobject = None
            """:type : anknotes._re.__Match """
            __match_attempted = 0

            @property
            def subject(self):
                if not self.__subject:
                    return self.content
                return self.__subject

            @subject.setter
            def subject(self, value):
                self.__subject = value
                self.__match_attempted = 0
                self.__matchobject = None

            @property
            def content(self):
                return self.__content

            def groups(self, group=0):
                """
                :param group:
                :type group : int | str | unicode
                :return:
                """
                if not self.successful_match:
                    return None
                return self.__matchobject.group(group)

            @property
            def successful_match(self):
                if self.__matchobject:
                    return True
                if self.__match_attempted is 0 and self.subject is not None:
                    self.__matchobject = notes.rgx.search(self.subject)
                    """:type : anknotes._re.__Match """
                    self.__match_attempted += 1
                return self.__matchobject is not None

            @property
            def main(self):
                return self.groups(0)

            @property
            def see_also(self):
                return self.groups('SeeAlso')

            @property
            def see_also_content(self):
                return self.groups('SeeAlsoContent')

            def __init__(self, content=None):
                """

                :type content: str | unicode
                """
                self.__content = content
                self.__match_attempted = 0
                self.__matchobject = None
                """:type : anknotes._re.__Match """

        content = pstrings()
        see_also = pstrings()

    old = version()
    new = version()
    rgx = regex_see_also()
    match_type = 'NA'


def str_process(str_):
    if not str_:
        return str_
    str_ = str_.replace(u"evernote:///", u"evernote://")
    str_ = re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([\w\d\-]+)',
                  r'evernote://view/\2/\1/\3/\3/', str_)
    str_ = str_.replace(u"evernote://", u"evernote:///").replace(u'<BR>', u'<br />')
    str_ = re.sub(r'<br ?/?>', u'<br/>', str_, 0, re.IGNORECASE)
    str_ = re.sub(r'(?s)&lt;&lt;(?P<PrefixKeep>(?:</div>)?)<div class="occluded">(?P<OccludedText>.+?)</div>&gt;&gt;',
                  r'&lt;&lt;\g<PrefixKeep>&gt;&gt;', str_)
    str_ = str_.replace('<span class="occluded">', '<span style="color: rgb(255, 255, 255);">')
    return str_


def str_process_full(str_):
    return clean_evernote_css(str_)


def main(evernote=None, anki=None):
    # @clockit
    def print_results(log_folder='Diff\\SeeAlso', full=False, final=False):
        if final:
            oldResults = n.old.content.final
            newResults = n.new.content.final
        elif full:
            oldResults = n.old.content.updated
            newResults = n.new.content.updated
        else:
            oldResults = n.old.see_also.updated
            newResults = n.new.see_also.updated
        diff = generate_diff(oldResults, newResults)
        if not 6 in FILES.LOGS.SEE_ALSO_DISABLED:
            log.plain(diff, log_folder + '\\Diff\\%s\\' % n.match_type + enNote.FullTitle, extension='htm', clear=True)
            log.plain(diffify(oldResults, split=False), log_folder + '\\Original\\%s\\' % n.match_type + enNote.FullTitle,
                      extension='htm', clear=True)
            log.plain(diffify(newResults, split=False), log_folder + '\\New\\%s\\' % n.match_type + enNote.FullTitle,
                      extension='htm', clear=True)
            if final:
                log.plain(oldResults, log_folder + '\\Final\\Old\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',
                          clear=True)
                log.plain(newResults, log_folder + '\\Final\\New\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',
                          clear=True)
        log.plain(diff + '\n', log_folder + '\\__All')

    # @clockit
    def process_note():
        n.old.content = notes.version.pstrings(enNote.Content)
        if not n.old.content.regex_original.successful_match:
            if n.new.see_also.original == "":
                n.new.content = notes.version.pstrings(n.old.content.original)
                return False
            n.new.content = notes.version.pstrings(n.old.content.original.replace('</en-note>',
                                                                                  '<div><span><br/></span></div>' + n.new.see_also.original + '\n</en-note>'))
            n.new.see_also.updated = str_process(n.new.content.original)
            n.old.see_also.updated = str_process(n.old.content.original)
            log.plain(enNote.Guid + '<BR>' + ', '.join(
                enNote.TagNames) + '<HR>' + enNote.Content + '<HR>' + n.new.see_also.updated,
                      'SeeAlsoMatchFail\\' + enNote.FullTitle, extension='htm', clear=True)
            n.match_type = 'V1'
        else:
            n.old.see_also = notes.version.pstrings(n.old.content.regex_original.main)
            n.match_type = 'V2'
            if n.old.see_also.regex_processed.successful_match:
                assert True or str_process(n.old.content.regex_original.main) is n.old.content.regex_processed.main
                n.old.content.updated = n.old.content.original.replace(n.old.content.regex_original.main,
                                                                       str_process(n.old.content.regex_original.main))
                n.old.see_also.useProcessed()
                n.match_type += 'V3'
            n.new.see_also.regex_original.subject = n.new.see_also.original + '</en-note>'
            if not n.new.see_also.regex_original.successful_match:
                log.plain(enNote.Guid + '\n' + ', '.join(enNote.TagNames) + '\n' + n.new.see_also.original,
                          'SeeAlsoNewMatchFail\\' + enNote.FullTitle, extension='htm', clear=True)
                # see_also_replace_old = n.old.content.original.match.processed.see_also.processed.content
                n.old.see_also.updated = n.old.content.regex_updated.see_also
                n.new.see_also.updated = n.new.see_also.processed
                n.match_type += 'V4'
            else:
                assert (n.old.content.regex_processed.see_also_content == notes.version.see_also_match(
                    str_process(n.old.content.regex_original.main)).see_also_content)
                n.old.see_also.updated = notes.version.see_also_match(
                    str_process(n.old.content.regex_original.main)).see_also_content
                n.new.see_also.updated = str_process(n.new.see_also.regex_original.see_also_content)
                n.match_type += 'V5'
            n.new.content.updated = n.old.content.updated.replace(n.old.see_also.updated, n.new.see_also.updated)

    def print_results_fail(title, status=None):
        log.go(title + ' for %s' % enNote.FullTitle, 'NoUpdate')
        print_results('NoMatch\\SeeAlso')
        print_results('NoMatch\\Contents', full=True)
        if status is None:
            status = EvernoteAPIStatus.GenericError
        tmr.reportStatus(status)

    noteType = 'SeeAlso-Step6'
    db = ankDB()
    db.delete("noteType = '%s'" % noteType, table=TABLES.NOTE_VALIDATION_QUEUE)
    results = db.all("SELECT DISTINCT s.target_evernote_guid, n.* FROM {s} as s, {n} as n  "
                     "WHERE s.target_evernote_guid = n.guid AND n.tagNames NOT LIKE '{t_toc}' "
                     "AND n.tagNames NOT LIKE '{t_out}' ORDER BY n.title ASC;")
    # count_queued = 0
    log = Logger('See Also\\6-update_see_also_footer_in_evernote_notes\\', rm_path=True)
    tmr = stopwatch.Timer(len(results), 25, infoStr='Updating Evernote See Also Notes',
                          label=log.base_path, do_print=True)
    # log.banner("UPDATING EVERNOTE SEE ALSO CONTENT: %d NOTES" % len(results), do_print=True)
    notes_updated = []
    # number_updated = 0
    for result in results:
        enNote = EvernoteNotePrototype(db_note=result)
        n = notes()
        tmr.step(enNote.FullTitle if enNote.Status.IsSuccess else '(%s)' % enNote.Guid)
        flds = get_anki_fields_from_evernote_guids(enNote.Guid)
        if not flds:
            print_results_fail('No Anki Note Found')
            continue
        flds = flds.split("\x1f")
        n.new.see_also = notes.version.pstrings(flds[FIELDS.ORD.SEE_ALSO])
        result = process_note()
        if result is False:
            print_results_fail('No Match')
            continue
        if n.match_type != 'V1' and str_process(n.old.see_also.updated) == n.new.see_also.updated:
            print_results_fail('Match but contents are the same', EvernoteAPIStatus.RequestSkipped)
            continue
        print_results()
        print_results('Diff\\Contents', final=True)
        enNote.Content = n.new.content.final
        if not EVERNOTE.UPLOAD.ENABLED:
            tmr.reportStatus(EvernoteAPIStatus.Disabled)
            continue
        if not evernote:
            evernote = Evernote()
        whole_note = tmr.autoStep(evernote.makeNote(enNote=enNote, noteType=noteType), update=True)
        if tmr.report_result is False:
            raise ValueError
        if tmr.status.IsDelayableError:
            break
        if tmr.status.IsSuccess:
            notes_updated.append(EvernoteNotePrototype(whole_note=whole_note))
    if tmr.is_success and not anki:
        anki = Anki()
    tmr.Report(0, anki.update_evernote_notes(notes_updated) if tmr.is_success else 0)

