# -*- coding: utf-8 -*-
import shutil

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

from anknotes.shared import *
from anknotes import stopwatch
from anknotes.stopwatch import clockit
import re
from anknotes._re import __Match

from anknotes.EvernoteNotes import EvernoteNotes
from anknotes.AnkiNotePrototype import AnkiNotePrototype
from enum import Enum
from anknotes.enums import *
from anknotes.structs import EvernoteAPIStatus

Error = sqlite.Error
ankDBSetLocal()
NotesDB = EvernoteNotes()


class notes:
    class version(object):
        class pstrings:
            __updated__ = None
            __processed__ = None
            __original__ = None
            __regex_updated__ = None
            """: type : notes.version.see_also_match """
            __regex_processed__ = None
            """: type : notes.version.see_also_match """
            __regex_original__ = None
            """: type : notes.version.see_also_match """
            
            @property 
            def regex_original(self):
                if self.original is None: return None
                if self.__regex_original__ is None:
                    self.__regex_original__ = notes.version.see_also_match(self.original)
                return self.__regex_original__
            
            @property 
            def regex_processed(self):
                if self.processed is None: return None
                if self.__regex_processed__ is None:
                    self.__regex_processed__ = notes.version.see_also_match(self.processed)
                return self.__regex_processed__
                
            @property 
            def regex_updated(self):
                if self.updated is None: return None
                if self.__regex_updated__ is None:
                    self.__regex_updated__ = notes.version.see_also_match(self.updated)
                return self.__regex_updated__

            @property
            def processed(self):
                if self.__processed__ is None:
                    self.__processed__ = str_process(self.original)
                return self.__processed__

            @property
            def updated(self):
                if self.__updated__ is None: return self.__original__
                return self.__updated__

            @updated.setter
            def updated(self, value):
                self.__regex_updated__ = None
                self.__updated__ = value

            @property
            def original(self):
                return self.__original__
                
            def useProcessed(self):
                self.updated = self.processed

            def __init__(self, original=None):
                self.__original__ = original

        class see_also_match(object):
            __subject__ = None
            __content__ = None
            __matchobject__ = None
            """:type : __Match """
            __match_attempted__ = 0

            @property
            def subject(self):
                if not self.__subject__: return self.content
                return self.__subject__

            @subject.setter
            def subject(self, value):
                self.__subject__ = value
                self.__match_attempted__ = 0
                self.__matchobject__ = None

            @property
            def content(self):
                return self.__content__

            def groups(self, group=0):
                """
                :param group:
                :type group : int | str | unicode
                :return:
                """
                if not self.successful_match:
                    return None
                return self.__matchobject__.group(group)

            @property
            def successful_match(self):
                if self.__matchobject__: return True
                if self.__match_attempted__ is 0 and self.subject is not None:
                    self.__matchobject__ = notes.rgx.search(self.subject)
                    """:type : __Match """
                    self.__match_attempted__ += 1
                return self.__matchobject__ is not None

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
                self.__content__ = content
                self.__match_attempted__ = 0
                self.__matchobject__ = None
                """:type : __Match """       
        content = pstrings()
        see_also = pstrings()
    old = version()
    new = version()
    rgx = regex_see_also()
    match_type = 'NA'


def str_process(strr):
    strr = strr.replace(u"evernote:///", u"evernote://")
    strr = re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([\w\d\-]+)',
                  r'evernote://view/\2/\1/\3/\3/', strr)
    strr = strr.replace(u"evernote://", u"evernote:///").replace(u'<BR>', u'<br />')
    strr = re.sub(r'<br ?/?>', u'<br/>', strr, 0, re.IGNORECASE)
    strr = re.sub(r'&lt;&lt;<span class="occluded">(.+?)</span>&gt;&gt;', r'&lt;&lt;\1&gt;&gt;', strr)
    strr = strr.replace('<span class="occluded">', '<span style="color: rgb(255, 255, 255);">')
    return strr

def main_bare():
    @clockit
    def print_results():        
        diff = generate_diff(n.old.see_also.updated, n.new.see_also.updated)
        log.plain(diff, 'SeeAlsoDiff\\Diff\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',  clear=True)
        log.plain(diffify(n.old.see_also.updated,split=False), 'SeeAlsoDiff\\Original\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',  clear=True)
        log.plain(diffify(n.new.see_also.updated,split=False), 'SeeAlsoDiff\\New\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',  clear=True)
        log.plain(diff + '\n', 'SeeAlsoDiff\\__All')
        # diff = generate_diff(see_also_replace_old, see_also_replace_new)
        # log_plain(diff, 'SeeAlsoDiff\\Diff\\' + enNote.FullTitle, clear=True)
        # log_plain(see_also_replace_old, 'SeeAlsoDiff\\Original\\' + enNote.FullTitle, clear=True)
        # log_plain(see_also_replace_new, 'SeeAlsoDiff\\New\\' + enNote.FullTitle, clear=True)
        # log_plain(diff + '\n' , logall)

    @clockit
    def process_note():
        n.old.content = notes.version.pstrings(enNote.Content)
        # xx = n.old.content.original.match
        # see_also_match_old = rgx.search(old_content)
        # see_also_match_old = n.old.content.regex_original.__matchobject__
        # if not see_also_match_old:
        if not n.old.content.regex_original.successful_match:
            # log.go("Could not get see also match for %s" % target_evernote_guid)
            
            # new_content = old_content.replace('</en-note>', '<div><span><br/></span></div>' + n.new.see_also + '\n</en-note>')
            n.new.content = notes.version.pstrings(n.old.content.original.replace('</en-note>', '<div><span><br/></span></div>' + n.new.see_also.original + '\n</en-note>'))
            # see_also_replace_new = new_content
            # see_also_replace_old = old_content
            # ????????????n.new.see_also.updated = str_process(n.new.content.original)
            n.new.see_also.updated = str_process(n.new.content.original)
            n.old.see_also.updated = str_process(n.old.content.original)
            log.plain((target_evernote_guid + '<BR>' if target_evernote_guid != enNote.Guid else '') +  enNote.Guid + '<BR>' + ', '.join(enNote.TagNames) + '<HR>' + enNote.Content + '<HR>' + n.new.see_also.updated, 'SeeAlsoMatchFail\\' + enNote.FullTitle, extension='htm', clear=True)
            n.match_type = 'V1'
        else:
            # see_also_old = see_also_match_old.group(0)
            # see_also_old = n.old.content.regex_original.main
            n.old.see_also = notes.version.pstrings(n.old.content.regex_original.main)
            n.match_type = 'V2'
            # see_also_old_processed = str_process(see_also_old)
            # see_also_old_processed = n.old.see_also.processed 
            
            # see_also_match_old_processed = rgx.search(see_also_old_processed)
            # see_also_match_old_processed = n.old.content.original.match.processed.__matchobject__
            # see_also_match_old_processed = n.old.see_also.regex_processed
            # if n.old.content.original.match.processed.successful_match:
            if n.old.see_also.regex_processed.successful_match:
                # n.old.content.processed.content = n.old.content.original.subject.replace(n.old.content.original.match.original.subject, n.old.content.original.match.processed.subject)
                assert True or str_process(n.old.content.regex_original.main) is n.old.content.regex_processed.main
                n.old.content.updated = n.old.content.original.replace(n.old.content.regex_original.main, str_process(n.old.content.regex_original.main))
                # old_content = old_content.replace(see_also_old, see_also_old_processed)
                # see_also_match_old = see_also_match_old_processed
                n.old.see_also.useProcessed()
                # log.go("Able to use processed old see also content")
                n.match_type += 'V3' 
                # see_also_match_old = n.old.see_also.updated
                # xxx =  n.old.content.original.match.processed
            
            # see_also_old_group_only = see_also_match_old.group('SeeAlso')
            # see_also_old_group_only = n.old.content.original.match.processed.see_also.original.content 
            # see_also_old_group_only = n.old.see_also.regex_updated.see_also 
            # see_also_old_group_only_processed = str_process(see_also_old_group_only)
            # see_also_old_group_only_processed =  n.old.content.original.match.processed.see_also.processed.content 
            # see_also_old = str_process(see_also_match.group(0))
            n.new.see_also.regex_original.subject = n.new.see_also.original + '</en-note>'
            # see_also_match_new = rgx.search(see_also_new + '</en-note>')
            # if not see_also_match_new:
            if not n.new.see_also.regex_original.successful_match:
                # log.go("Could not get see also new match for %s" % target_evernote_guid)
                # log_plain(enNote.Guid + '\n' + ', '.join(enNote.TagNames) + '\n' + see_also_new, 'SeeAlsoNewMatchFail\\' + enNote.FullTitle, clear=True)
                log.plain(enNote.Guid + '\n' + ', '.join(enNote.TagNames) + '\n' + n.new.see_also.original.content, 'SeeAlsoNewMatchFail\\' + enNote.FullTitle, extension='htm', clear=True)
                # see_also_replace_old = see_also_old_group_only_processed
                see_also_replace_old = n.old.content.original.match.processed.see_also.processed.content 
                n.old.see_also.updated = n.old.content.regex_updated.see_also
                # see_also_replace_new = see_also_new_processed
                # see_also_replace_new = n.new.see_also.processed.content
                n.new.see_also.updated = n.new.see_also.processed 
                n.match_type + 'V4'
            else:
                # see_also_replace_old = see_also_match_old.group('SeeAlsoContent')
                # see_also_replace_old  = n.old.content.original.match.processed.see_also_content                
                assert (n.old.content.regex_processed.see_also_content == notes.version.see_also_match(str_process(n.old.content.regex_original.main)).see_also_content)
                n.old.see_also.updated = notes.version.see_also_match(str_process(n.old.content.regex_original.main)).see_also_content
                # see_also_replace_new = see_also_match_new.group('SeeAlsoContent')
                # see_also_replace_new = n.new.see_also.original.see_also_content
                # n.new.see_also.updated = n.new.see_also.regex_original.see_also_content
                n.new.see_also.updated = str_process(n.new.see_also.regex_original.see_also_content)
                n.match_type += 'V5'
            n.new.content.updated = n.old.content.updated.replace(n.old.see_also.updated, n.new.see_also.updated)
            # new_content = old_content.replace(see_also_replace_old, see_also_replace_new)
            # n.new.content = notes.version.pmatches()
    log = Logger(default_filename='SeeAlsoDiff\\__ALL', rm_path=True)
    results = [x[0] for x in ankDB().all(
        "SELECT DISTINCT target_evernote_guid FROM %s WHERE 1 ORDER BY title ASC " % TABLES.SEE_ALSO)]
    changed = 0
    # rm_log_path(subfolders_only=True)
    log.banner("UPDATING EVERNOTE SEE ALSO CONTENT", do_print=True)
    tmr = stopwatch.Timer(max=len(results), interval=25)
    tmr.max = len(results)
    for target_evernote_guid in results:
        enNote = NotesDB.getEnNoteFromDBByGuid(target_evernote_guid)
        n = notes()
        if tmr.step():
            print "Note %5s: %s: %s" % ('#' + str(tmr.count), tmr.progress, enNote.FullTitle if enNote.Status.IsSuccess else '(%s)' % target_evernote_guid)
        if not enNote.Status.IsSuccess:
            log.go("Could not get    en note     for %s" % target_evernote_guid)
            continue
        for tag in [EVERNOTE.TAG.TOC, EVERNOTE.TAG.OUTLINE]:
            if tag in enNote.TagNames: break
        else:
            flds = ankDB().scalar("SELECT flds FROM notes WHERE flds LIKE '%%%s%s%%'" % (FIELDS.EVERNOTE_GUID_PREFIX, target_evernote_guid))
            n.new.see_also = notes.version.pstrings(flds.split("\x1f")[FIELDS.SEE_ALSO_FIELDS_ORD])
            process_note()
            if n.match_type != 'V1' and str_process(n.old.see_also.updated) == n.new.see_also.updated: continue 
            # if see_also_replace_old == see_also_replace_new: continue
            print_results()
            changed += 1
            enNote.Content = n.new.content.updated 
    print "Total %d changed out of %d " % (changed, tmr.max)

    
## HOCM/MVP