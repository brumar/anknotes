# -*- coding: utf-8 -*-
import shutil

try:
	from pysqlite2 import dbapi2 as sqlite
except ImportError:
	from sqlite3 import dbapi2 as sqlite

from anknotes.shared import *
from anknotes import stopwatch
# from anknotes.stopwatch import clockit
import re
from anknotes._re import __Match

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
				if self.__updated__ is None: return str_process(self.__original__)
				return self.__updated__

			@updated.setter
			def updated(self, value):
				self.__regex_updated__ = None
				self.__updated__ = value

			@property
			def final(self):
				return str_process_full(self.updated)
				
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
	if not strr: return strr
	strr = strr.replace(u"evernote:///", u"evernote://")
	strr = re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([\w\d\-]+)',
				  r'evernote://view/\2/\1/\3/\3/', strr)
	strr = strr.replace(u"evernote://", u"evernote:///").replace(u'<BR>', u'<br />')
	strr = re.sub(r'<br ?/?>', u'<br/>', strr, 0, re.IGNORECASE)
	strr = re.sub(r'(?s)&lt;&lt;(?P<PrefixKeep>(?:</div>)?)<div class="occluded">(?P<OccludedText>.+?)</div>&gt;&gt;', r'&lt;&lt;\g<PrefixKeep>&gt;&gt;', strr)
	strr = strr.replace('<span class="occluded">', '<span style="color: rgb(255, 255, 255);">')
	return strr

def str_process_full(strr):
	return clean_evernote_css(strr)
	
def main(evernote=None, anki=None):
	# @clockit
	def print_results(log_folder='Diff\\SeeAlso',full=False, final=False):        
		if final:
			oldResults=n.old.content.final
			newResults=n.new.content.final
		elif full:
			oldResults=n.old.content.updated
			newResults=n.new.content.updated
		else:
			oldResults=n.old.see_also.updated
			newResults=n.new.see_also.updated
		diff = generate_diff(oldResults, newResults)
		log.plain(diff, log_folder+'\\Diff\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',  clear=True)
		log.plain(diffify(oldResults,split=False), log_folder+'\\Original\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',  clear=True)
		log.plain(diffify(newResults,split=False), log_folder+'\\New\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',  clear=True)
		if final:
			log.plain(oldResults, log_folder+'\\Final\\Old\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',  clear=True)
			log.plain(newResults, log_folder+'\\Final\\New\\%s\\' % n.match_type + enNote.FullTitle, extension='htm',  clear=True)
		log.plain(diff + '\n', log_folder+'\\__All')

	# @clockit
	def process_note():
		n.old.content = notes.version.pstrings(enNote.Content)
		if not n.old.content.regex_original.successful_match:            
			if n.new.see_also.original == "":                 
				n.new.content =  notes.version.pstrings(n.old.content.original)
				return False 
			n.new.content = notes.version.pstrings(n.old.content.original.replace('</en-note>', '<div><span><br/></span></div>' + n.new.see_also.original + '\n</en-note>'))
			n.new.see_also.updated = str_process(n.new.content.original)
			n.old.see_also.updated = str_process(n.old.content.original)
			log.plain(enNote.Guid + '<BR>' + ', '.join(enNote.TagNames) + '<HR>' + enNote.Content + '<HR>' + n.new.see_also.updated, 'SeeAlsoMatchFail\\' + enNote.FullTitle, extension='htm', clear=True)
			n.match_type = 'V1'
		else:
			n.old.see_also = notes.version.pstrings(n.old.content.regex_original.main)
			n.match_type = 'V2'            
			if n.old.see_also.regex_processed.successful_match:
				assert True or str_process(n.old.content.regex_original.main) is n.old.content.regex_processed.main
				n.old.content.updated = n.old.content.original.replace(n.old.content.regex_original.main, str_process(n.old.content.regex_original.main))
				n.old.see_also.useProcessed()
				n.match_type += 'V3'             
			n.new.see_also.regex_original.subject = n.new.see_also.original + '</en-note>'
			if not n.new.see_also.regex_original.successful_match:
				log.plain(enNote.Guid + '\n' + ', '.join(enNote.TagNames) + '\n' + n.new.see_also.original.content, 'SeeAlsoNewMatchFail\\' + enNote.FullTitle, extension='htm', clear=True)
				see_also_replace_old = n.old.content.original.match.processed.see_also.processed.content 
				n.old.see_also.updated = n.old.content.regex_updated.see_also
				n.new.see_also.updated = n.new.see_also.processed 
				n.match_type + 'V4'
			else:
				assert (n.old.content.regex_processed.see_also_content == notes.version.see_also_match(str_process(n.old.content.regex_original.main)).see_also_content)
				n.old.see_also.updated = notes.version.see_also_match(str_process(n.old.content.regex_original.main)).see_also_content
				n.new.see_also.updated = str_process(n.new.see_also.regex_original.see_also_content)
				n.match_type += 'V5'
			n.new.content.updated = n.old.content.updated.replace(n.old.see_also.updated, n.new.see_also.updated)
	log = Logger(default_filename='SeeAlsoDiff\\__ALL', rm_path=True)
	# SELECT DISTINCT s.target_evernote_guid FROM anknotes_see_also as s, anknotes_evernote_notes as n  WHERE s.target_evernote_guid = n.guid   ORDER BY n.title ASC
	# SELECT DISTINCT s.target_evernote_guid, n.* FROM anknotes_see_also as s, anknotes_evernote_notes as n  WHERE s.target_evernote_guid = n.guid   ORDER BY n.title ASC;
	# SELECT DISTINCT s.target_evernote_guid, n.* FROM anknotes_see_also as s, anknotes_evernote_notes as n  WHERE s.target_evernote_guid = n.guid AND n.tagNames NOT LIKE '%,#TOC,%' AND n.tagNames NOT LIKE '%,#Outline,%'  ORDER BY n.title ASC;
	sql = "SELECT DISTINCT s.target_evernote_guid, n.* FROM %s as s, %s as n  WHERE s.target_evernote_guid = n.guid AND n.tagNames NOT LIKE '%%,%s,%%' AND n.tagNames NOT LIKE '%%,%s,%%' ORDER BY n.title ASC;"
	results = ankDB().all(sql % (TABLES.SEE_ALSO, TABLES.EVERNOTE.NOTES, TAGS.TOC, TAGS.OUTLINE))
	count_queued = 0
	tmr = stopwatch.Timer(len(results), 25, label='SeeAlso-Step7')
	log.banner("UPDATING EVERNOTE SEE ALSO CONTENT: %d NOTES" % len(results), do_print=True)
	log.banner("UPDATING EVERNOTE SEE ALSO CONTENT: %d NOTES" % len(results), tmr.label)	
	notes_updated=[]
	number_updated = 0
	for result in results:
		enNote = EvernoteNotePrototype(db_note=result)
		n = notes()
		if tmr.step():
			log.go("Note %5s: %s: %s" % ('#' + str(tmr.count), tmr.progress, enNote.FullTitle if enNote.Status.IsSuccess else '(%s)' % enNote.Guid), , do_print=True, print_timestamp=False)
		flds = ankDB().scalar("SELECT flds FROM notes WHERE flds LIKE '%%%s%s%%'" % (FIELDS.EVERNOTE_GUID_PREFIX, enNote.Guid)).split("\x1f")
		n.new.see_also = notes.version.pstrings(flds[FIELDS.ORD.SEE_ALSO])            
		result = process_note()
		if result is False:
			log.go('No match for %s' % enNote.FullTitle, tmr.label + '-NoUpdate')
			print_results('NoMatch\\SeeAlso')
			print_results('NoMatch\\Contents', full=True)
			continue
		if n.match_type != 'V1' and str_process(n.old.see_also.updated) == n.new.see_also.updated:
			log.go('Match but contents are the same for %s' % enNote.FullTitle, tmr.label + '-NoUpdate')			
			print_results('Same\\SeeAlso')
			print_results('Same\\Contents', full=True)
			continue
		print_results()
		print_results('Diff\\Contents', final=True)			
		enNote.Content = n.new.content.final 
		if not evernote: evernote = Evernote()
		status, whole_note = evernote.makeNote(enNote=enNote)
		if tmr.reportStatus(status) == False: raise ValueError
		if status.IsDelayableError: break 
		if status.IsSuccess: notes_updated.append(EvernoteNotePrototype(whole_note=whole_note))
	if tmr.count_success > 0: 
		if not anki: anki = Anki()
		number_updated = anki.update_evernote_notes(notes_updated)
	log.go("Total %d of %d note(s) successfully uploaded to Evernote" % (tmr.count_success, tmr.max), tmr.label, do_print=True)
	if number_updated > 0: log.go("  > %4d updated in Anki" % number_updated, tmr.label, do_print=True)
	if tmr.count_queued > 0: log.go("  > %4d queued for validation" % tmr.count_queued, tmr.label, do_print=True)
	if tmr.count_error > 0:  log.go("  > %4d error(s) occurred" % tmr.count_error, tmr.label, do_print=True)

	
## HOCM/MVP