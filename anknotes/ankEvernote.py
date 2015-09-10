# -*- coding: utf-8 -*-
import os, time
import copy
from ankEnums import AutoNumber, EvernoteTitleLevels
import ankShared, ankConsts as ank, ankEvernote as EN 
from ankShared import *
try:
	from pysqlite2 import dbapi2 as sqlite
except ImportError:
	from sqlite3 import dbapi2 as sqlite
     
class NoteProcessingFlags:
	delayProcessing=False
	populateRootTitlesList=True
	populateRootTitlesDict=True
	populateChildRootTitles=False
	def __init__(self, flags=None):
		if flags: self.update(flags)
			
	def update(self, flags):
		for flag_name, flag_value in flags:
			if hasattr(self, flag_name):
				self[flag_name]=flag_value
	
class NotesCollection:
	TitlesList = []
	TitlesDict = {}
	NotesDict = {}	

class Note:
	################## CLASS Note ################
	title = None
	content = ""
	guid = ""
	updateSequenceNum = -1
	tags = []
	notebookGuid = ""
	status = -1
	children = []
	
	def __repr__(self):
		return u"%s: '%s'" % (self.guid, self.title)
	
	def __init__(self, title=None, content=None, guid=None, tags=None, notebookGuid=None, updateSequenceNum=None, whole_note=None, db_note=None):
		self.status = -1
		self.tags = tags 
		if not whole_note is None:
			self.title = NoteTitle(whole_note.title)
			self.content = whole_note.content
			self.guid = whole_note.guid 
			self.notebookGuid = whole_note.notebookGuid
			self.updateSequenceNum = whole_note.updateSequenceNum                
			return
		if not db_note is None:
			if isinstance(db_note['tagNames'] , str):
				db_note['tagNames'] = unicode(db_note['tagNames'] , 'utf-8')   
			# print "Creating enNote: %s " % db_note['title']
			self.title = NoteTitle(title=db_note['title'])
			self.content = db_note['content']
			self.guid = db_note['guid'] 
			self.notebookGuid = db_note['notebookGuid']
			self.updateSequenceNum = db_note['updateSequenceNum']
			self.tags = db_note['tagNames'][1:-1].split(',')     
			if isinstance(self.content , str):
				self.content = unicode(self.content , 'utf-8')         
			if isinstance(self.title , str):
				self.title = unicode(self.title , 'utf-8')                                        
			return        
		self.title = NoteTitle(self)
		self.content = content
		self.guid = guid
		self.notebookGuid = notebookGuid
		self.updateSequenceNum = updateSequenceNum 
	
	def isRoot(self):
		return self.title.isRoot()
		
	def isChild(self):
		return self.title.isChild()
		
	def isParent(self):
		return self.title.isParent()
	
	def isLevel(self, level):
		return self.title.isLevel(level) 
	
	def isAboveLevel(self, level):
		return self.title.isAboveLevel()
	################## END CLASS Note ################
	
class NoteTitle:      
	################## CLASS Title ################
	full = ""
	base = ""
	name = ""
	count = 0
	exists = False 
	orphan = True 
	children = []	
	partsText = None
	Note = None
	
	def newLevel(self, titlePart):
		newLvl = copy.copy(self.Full())
		newLvl.currentPart = titlePart
		offset = self.offset_as_tuple(titlePart)	
		# newLvl.Parts()
		# newLvl.PartsText()
		newParts = []
		# print "newLevel offset %s - parts [%s]- partsText [%s]  " % (str(offset), 'na', str(newLvl.partsText))
		for i in range(1, self.Count() + 1):
			if i in range(offset[0], offset[1] + 1):
				newParts.append(newLvl.partsText[i - 1])
			# print "del A %d  ~ %s" % (i, newLvl.partsText[i - 1])
		# for i in range(1, offset[0]):
			# print "del A %d  ~ %s" % (i, newLvl.partsText[i - 1])
			# del newLvl.partsText[i - 1]
		
		# for i in range(offset[1], self.Count()):
			# # del newLvl.parts[i]
			# print "del B %d  ~ %s" % (i, newLvl.partsText[i - 1])
			# del newLvl.partsText[i - 1]
		# # print_safe(" newLevel %s Parts[%s] " % (newLvl.title, str_safe(self.PartsText())))
		# # newLvl.setTitle(newLvl.title)
		newLvl.partsText = newParts 
		newLvl.title = ': '.join(newParts)
		# print "newLevel done    partsText [%s]  " % ( str(newLvl.partsText))
		return newLvl
	
	def __init__(self, Note=None, title=None):					
		if Note:
			self.Note = Note
			if self.Note.title:
				# print "Init title, Note.title = %s" % Note.title()
				self.setTitle(self.Note.title())
			elif title:
				self.setTitle(title)
		else:
			# print "init with plain text title %s " % title
			self.setTitle(title)
		self.Lvl = EvernoteTitleLevels.Levels
		self.Section = EvernoteTitleLevels.Sections
		self.Part = EvernoteTitleLevels.Parts
		self.currentPart = self.Part.Full
		# print "Done init title, self.title = %s " % self.title 
	def isRoot(self):
		return self.isLevel(self.Lvl.Root)
		
	def isName(self):
		return self.isLevel(self.Part.Name)
		
	def isParent(self):
		return len(self.children) > 0
							
	def isChild(self):
		return self.isAboveLevel(self.Lvl.Root)
		
	def isSubject(self):
		return self.isLevel(self.Lvl.Subject)
		
	def hasSubject(self):
		return self.isAboveLevel(self.Lvl.Subject)
		
	def isTopic(self):
		return self.isLevel(self.Lvl.Topic)
		
	def hasTopic(self):
		return self.isAboveLevel(self.Lvl.Topic)
		
	def isSubtopic(self):
		return self.isLevel(self.Lvl.Subtopic)
		
	def hasSubtopic(self):
		return self.isAboveLevel(self.Lvl.Subtopic)
		
	def isSection(self):
		return self.isLevel(self.Lvl.Section)
		
	def hasSection(self):
		return self.isAboveLevel(self.Lvl.Section)
		
	def isHeading(self):
		return self.isLevel(self.Lvl.Heading)
		
	def hasHeading(self):
		return self.isAboveLevel(self.Lvl.Heading)
		
	def isEntry(self):
		return self.isLevel(self.Lvl.Entry)
	
	def isLevel(self, level):
		offset = self.offset_as_scalar(level)
		# print " Level check - Title %s Level (%s) - Offset (%d) - Count (%d) - Parts [%s] " % (self.title, level, offset, self.Count(), str_safe(self.PartsText()))
		return self.Count() is offset    
	
	def offset_as_tuple(self, part):
		o = part					
		if isinstance(o, int):
			return o, o
		try:
			os = part.offset(self.Count())	
			return os
		except:
			print_safe ("Fail - %s %s " % (part, part.offset(self.Count())))
						
	def offset_as_scalar(self, part):
		o = part
		if not isinstance(o, int):
			try:
				os = part.offset(self.Count())	
				if os[0] == os[1]:
					o = os[0]
				else:
					print "Unexpected range tuple for level offset for offset_as_scalar. Offset: %s " % str(os)
			except:
				print_safe ("Fail - %s %s " % (part, part.offset(self.Count())))
		return o
		
	def isAboveLevel(self, level):
		offset = self.offset_as_scalar(level)		
		return self.count > offset    

	def Level(self, level):
		return self.newLevel(level)
		
	def Part(self, part):
		level = part
		return self.Level(level)
		
	def Count(self):
		if not self.count: 
			self.count = len(self.PartsText())
		return self.count 
		
	def PartsText(self):
		if not self.partsText: 
			# strTitle = str_safe(self.title)
			# print_safe("Setting PartsText for %s to %s " % (self.title, strTitle))
			strTitle = self.title 
			self.partsText = strTitle.split(':')
			self.count = len(self.partsText)
			for i in range(1, self.Count() + 1):
				txt =  self.partsText[i-1]
				if txt[-1] == ' ': txt = txt[:-1]
				if txt[0] == ' ': txt = txt[1:]
				self.partsText[i-1] = txt
		return self.partsText 
	
	def __repr__(self):
		return self.full
		
	def __str__(self):
		return self.title 
	
	def Breakdown(self):
		output =    'Full:   ' + self.full
		if self.isRoot(): return output
		output += '\n Root:   ' + self.root
		output += '\n Base:   ' + self.base
		if self.isLevel(TitleSectionBase): return output
		if self.isAboveLevel(3): 
			output += '\n  Parent: ' + self.parent
		output += '\n  Name:   ' + self.name
		output += '\n'
		return output 
	
	def setTitle(self, title=None, force=False):
		# print "Setting title - %s [ s] " % (title)
		if title:
			if str_safe(title) != '':
				self.partsText = None						
				self.title = title
			return 					
		if not self.Note: return						
		self.partsText = None
		self.title = self.Note.fields[ank.FIELDS.TITLE]
	
	def Parent(self):
		if self.isRoot(): return None
		return self.Level(self.Part.Parent)
	
	def Full(self):
		return self
	
	def Root(self):
		if self.isRoot(): return full
		return self.Level(self.Part.Root)
		
	def Base(self):
		if self.isRoot(): return None
		return self.Level(self.Part.Base)
		
	def Name(self):
		return self.Level(self.Part.Name)
	################### END CLASS Title ################
		
class Notes:    
	################## CLASS Notes ################
	Notes = {}
	RootNotes = NotesCollection()
	RootNotesChildren = NotesCollection()
	processingFlags = NoteProcessingFlags()
	
	def __init__(self,delayProcessing=False):
		self.processingFlags.delayProcessing = delayProcessing
		RootNotes = NotesCollection()

	def addNoteSilently(self, enNote):
		self.Notes[enNote.guid] = enNote
		
	def addNote(self, enNote):
		self.addNoteSilently(enNote)
		if self.processingFlags.delayProcessing: return 
		self.processNote(enNote)
		
	def addDBNote(self, dbNote):
		enNote = Note(db_note=dbNote) 
		self.addNote(enNote)
		
	def addDBNotes(self, dbNotes):
		for dbNote in dbNotes:
			self.addDBNote(dbNote)

	def addDbQuery(self, sql_query):
		sql_query = "SELECT *  FROM %s WHERE %s " % (ank.TABLES.EVERNOTE.NOTES, sql_query)
		dbNotes = ankDB().execute(sql_query)
		self.addDBNotes(dbNotes)
	
	def processNote(self, enNote):
		if self.processingFlags.populateRootTitlesList or self.processingFlags.populateRootTitlesDict:
			if enNote.isChild():
				rootTitle = enNote.title.Root()
				if not rootTitle in self.RootTitles:
					self.RootNotes.TitlesList.append(rootTitle)
					if populateRootTitlesDict:
						self.RootNotes.TitlesDict[rootTitle][enNote.guid] = enNote.title.Base()
						self.RootNotesDict[rootTitle][enNote.guid] = enNote
		if self.processingFlags.populateChildRootTitles:
			if enNote.isRoot():
				rootTitle = enNote.title
				rootGuid = enNote.guid 
				# print_safe ("Processing Root Note %s" % rootTitle)
				childNotes = ankDB().execute("SELECT * FROM %s WHERE title LIKE '%s:%%' ORDER BY title ASC" % (ank.TABLES.EVERNOTE.NOTES, rootTitle.title.replace("'", "''")))
				child_count = 0
				for childDbNote in childNotes:
					child_count += 1
					childGuid = childDbNote['guid']
					childEnNote = Note(db_note=childDbNote)
					if child_count is 1:
						# count += 1
						self.RootNotesChildren.TitlesDict[rootGuid] = {}
						self.RootNotesChildren.NotesDict[rootGuid] = {}
						# is_toc = ank.EVERNOTE.TAG.TOC in root_note.tags
						# is_outline = ank.EVERNOTE.TAG.OUTLINE in root_note.tags
						# is_both = is_toc and is_outline 
						# is_none = not is_toc and not is_outline 
						# is_toc_outline_str = "BOTH ???" if is_both else "TOC" if is_toc else "OUTLINE" if is_outline else "N/A"
						# print_safe(root_note, ' TOP LEVEL: [%d] ' % count)
					# note = Note(db_note=childDbNote)
					# print "Setting childEnNote title %s " % childDbNote['title']
					# childEnNote.title.setTitle(childEnNote.title)
					# print_safe('Child EN title: %s;  db title: %s' % (childEnNote.title.PartsText(), childDbNote['title']))
					childBaseTitle = childEnNote.title.Base()
					# print_safe (childBaseTitle)
					self.RootNotesChildren.TitlesDict[rootGuid][childGuid] = childBaseTitle
					self.RootNotesChildren.NotesDict[rootGuid][childGuid] = childEnNote
					# print_safe(note, '         > CHILD NOTE #%d: ' % child_count)
				# if child_count > 1:
					# if is_none:
						# print_safe(root_note, ' TOP LEVEL: [%4d::%2d]: [%7s] ' % (count, child_count, is_toc_outline_str))  
				# RootNotesChildren.TitlesDict[rootTitle][]

	def processNotes(self, populateRootTitlesList=True, populateRootTitlesDict=True):
		if self.processingFlags.populateRootTitlesList or self.processingFlags.populateRootTitlesDict:
			RootNotes = NotesCollection()
		
		for guid, enNote in self.Notes:
			self.processNote(enNote, populateRootTitlesList=populateRootTitlesList, populateRootTitlesDict=populateRootTitlesDict)			
	
	def processAllChildNotes(self):
		self.processNotes(populateRootTitlesDict = True, populateRootTitlesList = True )
	
	def populateAllRootTitles(self):
		NoteDB.getChildNotes()
		NoteDB.processAllRootTitles()		

	def processAllRootTitles(self):
		count = 0
		for rootTitle, baseTitles in self.RootNotes.TitlesDict.items():
			count += 1
			baseNoteCount = len(baseTitles)
			rootNote = ankDB().fetchone("SELECT * FROM %s WHERE title = '%s'" % (ank.TABLES.EVERNOTE.NOTES, rootTitle))
			if rootNote:
				root_titles_existing.append(rootTitle)
			else:
				root_titles_missing.append(rootTitle)
				print_safe(rootNote, ' TOP LEVEL: [%4d::%2d]: [%7s] ' % (count, baseNoteCount, is_toc_outline_str))
				for baseGuid, baseTitle in baseTitles:
					pass				

	def getChildNotes(self):	
		self.addDbQuery("title LIKE '%%:%%' ORDER BY title ASC")
		
	def getRootNotes(self):	
		self.addDbQuery("title NOT LIKE '%%:%%' ORDER BY title ASC")

	def processAllRootNotesWithoutTOCOrOutlineDesignation(self):
		count = 0
		for rootGuid, childBaseTitleDicts in self.RootNotesChildren.TitlesDict.items():
			rootEnNote = self.Notes[rootGuid]				
			if len(childBaseTitleDicts.items()) > 0:
				is_toc = ank.EVERNOTE.TAG.TOC in rootEnNote.tags
				is_outline = ank.EVERNOTE.TAG.OUTLINE in rootEnNote.tags
				is_both = is_toc and is_outline 
				is_none = not is_toc and not is_outline 										
				is_toc_outline_str = "BOTH ???" if is_both else "TOC" if is_toc else "OUTLINE" if is_outline else "N/A"
				if is_none:
					count += 1
					print_safe(rootEnNote, ' TOP LEVEL: [%3d] %-8s: ' % (count, is_toc_outline_str))					
		
	def populateAllRootNotesWithoutTOCOrOutlineDesignation(self):
		processingFlags = NoteProcessingFlags()
		processingFlags.populateRootTitlesList=False
		processingFlags.populateRootTitlesDict=False
		processingFlags.populateChildRootTitles = True
		self.processingFlags = processingFlags
		self.getRootNotes()
		print len(self.Notes)
		self.processAllRootNotesWithoutTOCOrOutlineDesignation()    