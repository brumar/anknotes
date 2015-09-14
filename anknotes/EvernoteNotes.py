# -*- coding: utf-8 -*-
### Python Imports
import copy
from operator import itemgetter
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
# from anknotes.shared import *
from anknotes.toc import *
     
class NoteProcessingFlags:
    delayProcessing=False
    populateRootTitlesList=True
    populateRootTitlesDict=True
    populateExistingRootTitlesList=False
    populateExistingRootTitlesDict=False
    populateMissingRootTitlesList=False
    populateMissingRootTitlesDict=False
    populateChildRootTitles=False
    ignoreAutoTOCAsRootTitle=False
    def __init__(self, flags=None):
        if isinstance(flags, bool):
            if not flags: self.set_default(False)
        if flags: self.update(flags)
            
    def set_default(self, flag):
        self.populateRootTitlesList = flag 
        self.populateRootTitlesDict = flag        
            
    def update(self, flags):
        for flag_name, flag_value in flags:
            if hasattr(self, flag_name):
                self[flag_name]=flag_value
    
class NotesCollection:
    TitlesList = []
    TitlesDict = {}
    NotesDict = {}  
    ChildNotesDict = {}
    ChildTitlesDict = {}
    def __init__(self):
        self.TitlesList = list()
        self.TitlesDict = {}
        self.NotesDict = {}  
        self.ChildNotesDict = {}
        self.ChildTitlesDict = {}

class Note:
    ################## CLASS Note ################
    title = None
    content = ""
    guid = ""
    updateSequenceNum = -1
    tags = []
    tagGuids = []
    notebookGuid = ""
    status = -1
    children = []
    
    def __repr__(self):
        return u"<EN Note: %s: '%s'>" % (self.guid, self.title)
    
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
            self.tagGuids = db_note['tagGuids'][1:-1].split(',')     
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
    
    def generateURL(self):
        return generate_evernote_url(self.guid)
    
    def generateLink(self, value=None):
        return generate_evernote_link(self.guid, self.title.Name().title, value)
        
    def generateLevelLink(self, type=None, value=None):
        return generate_evernote_link_by_level(self.guid, self.title.Name().title, value)
    
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
    
    def __repr__(self):
        return u"<EN Note Title: %s: '%s'>" % (self.Note.guid, self.title)    
    
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
        try: return part.offset(self.Count())  
        except: pass
        # try: return part.id()
        # except: pass
        # try: return part.value()
        # except: pass
        print_safe ("Fail Tuple - %s %s " % (part, part.offset(self.Count())))
                        
    def offset_as_scalar(self, part):
        o = part
        if not isinstance(o, int):
            try:
                os = part.offset(self.Count())  
                if os[0] == os[1]:
                    o = os[0]
                else:
                    print "Unexpected range tuple for level offset for offset_as_scalar. Offset: %s " % str(os)
                    raise 
            except:
                print_safe ("Fail Scalar - %s %s" % (part,  part.offset(self.Count())  ))
                raise
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
            self.partsText = generateTitleParts(self.title)
            self.count = len(self.partsText)
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
        self.title = self.Note.fields[FIELDS.TITLE]
    
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
    baseQuery = "1"
    
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

    def addDbQuery(self, sql_query, order=''):
        sql_query = "SELECT *  FROM %s WHERE (%s) AND (%s) " % (TABLES.EVERNOTE.NOTES, self.baseQuery, sql_query)
        if order: sql_query += ' ORDER BY ' + order 
        dbNotes = ankDB().execute(sql_query)
        self.addDBNotes(dbNotes)

    def getNoteFromDB(self, query):
        sql_query = "SELECT *  FROM %s WHERE %s " % (TABLES.EVERNOTE.NOTES, query)
        dbNote = ankDB().first(sql_query)
        if not dbNote: return None 
        
    def getNoteFromDBByGuid(self, guid):
        sql_query = "guid = '%s' " % guid
        return self.getNoteFromDB(sql_query)
        
    def addChildNoteHierarchically(self, enChildNotes, enChildNote):
        parts = enChildNote.title.PartsText()
        dict_updated = {}
        dict_building = {parts[len(parts)-1]: enChildNote}
        print_safe(parts)
        for i in range(len(parts), 1, -1):
            dict_building = {parts[i - 1]: dict_building}
        log_dump(dict_building)
        enChildNotes.update(dict_building)
        log_dump(enChildNotes)
        return enChildNotes    
            
    def processNote(self, enNote):
        if self.processingFlags.populateRootTitlesList or self.processingFlags.populateRootTitlesDict or self.processingFlags.populateMissingRootTitlesList or self.processingFlags.populateMissingRootTitlesDict:
            
            if enNote.isChild():
                rootTitle = enNote.title.Root()
                rootTitleStr = generateTOCTitle(rootTitle.title)
                if self.processingFlags.populateMissingRootTitlesList or self.processingFlags.populateMissingRootTitlesDict:
                    if not rootTitleStr in self.RootNotesExisting.TitlesList and not rootTitleStr in self.RootNotesExisting.TitlesList:
                        if not rootTitleStr in self.RootNotesMissing.TitlesList:
                            self.RootNotesMissing.TitlesList.append(rootTitleStr)
                            self.RootNotesMissing.ChildTitlesDict[rootTitleStr] = {}
                            self.RootNotesMissing.ChildNotesDict[rootTitleStr] = {}
                        childBaseTitleStr = enNote.title.Base().title
                        if childBaseTitleStr in self.RootNotesMissing.ChildTitlesDict[rootTitleStr]:
                            log_dump(self.RootNotesMissing.ChildTitlesDict[rootTitleStr], repr(enNote))
                        assert not childBaseTitleStr in self.RootNotesMissing.ChildTitlesDict[rootTitleStr]
                        self.RootNotesMissing.ChildTitlesDict[rootTitleStr][childBaseTitleStr] = enNote.guid 
                        self.RootNotesMissing.ChildNotesDict[rootTitleStr][enNote.guid] = enNote
                if self.processingFlags.populateRootTitlesList or self.processingFlags.populateRootTitlesDict:
                    if not rootTitleStr in self.RootNotes.TitlesList:
                        self.RootNotes.TitlesList.append(rootTitleStr)
                        if self.processingFlags.populateRootTitlesDict:
                            self.RootNotes.TitlesDict[rootTitleStr][enNote.guid] = enNote.title.Base()
                            self.RootNotes.NotesDict[rootTitleStr][enNote.guid] = enNote
        if self.processingFlags.populateChildRootTitles or self.processingFlags.populateExistingRootTitlesList or self.processingFlags.populateExistingRootTitlesDict:
            if enNote.isRoot():
                rootTitle = enNote.title
                rootTitleStr = generateTOCTitle(rootTitle.title)
                rootGuid = enNote.guid 
                if self.processingFlags.populateExistingRootTitlesList or self.processingFlags.populateExistingRootTitlesDict or  self.processingFlags.populateMissingRootTitlesList :
                    if not rootTitleStr in self.RootNotesExisting.TitlesList:
                        self.RootNotesExisting.TitlesList.append(rootTitleStr)
                if self.processingFlags.populateChildRootTitles:
                    childNotes = ankDB().execute("SELECT * FROM %s WHERE title LIKE '%s:%%' ORDER BY title ASC" % (TABLES.EVERNOTE.NOTES, rootTitleStr.replace("'", "''")))
                    child_count = 0
                    for childDbNote in childNotes:
                        child_count += 1
                        childGuid = childDbNote['guid']
                        childEnNote = Note(db_note=childDbNote)
                        if child_count is 1:
                            self.RootNotesChildren.TitlesDict[rootGuid] = {}
                            self.RootNotesChildren.NotesDict[rootGuid] = {}
                        childBaseTitle = childEnNote.title.Base()
                        self.RootNotesChildren.TitlesDict[rootGuid][childGuid] = childBaseTitle
                        self.RootNotesChildren.NotesDict[rootGuid][childGuid] = childEnNote

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
            query = "UPPER(title) = '%s'" % escape_text_sql(rootTitle).upper()
            if self.processingFlags.ignoreAutoTOCAsRootTitle:
                query += " AND tagNames NOT LIKE '%%,%s,%%'" % EVERNOTE.TAG.AUTO_TOC          
            rootNote = self.getNoteFromDB(query)
            if rootNote:
                root_titles_existing.append(rootTitle)
            else:
                root_titles_missing.append(rootTitle)
                print_safe(rootNote, ' TOP LEVEL: [%4d::%2d]: [%7s] ' % (count, baseNoteCount, is_toc_outline_str))
                for baseGuid, baseTitle in baseTitles:
                    pass                

    def getChildNotes(self):    
        self.addDbQuery("title LIKE '%%:%%'", 'title ASC')
        
    def getRootNotes(self): 
        query = "title NOT LIKE '%%:%%'"
        if self.processingFlags.ignoreAutoTOCAsRootTitle:
            query += " AND tagNames NOT LIKE '%%,%s,%%'" % EVERNOTE.TAG.AUTO_TOC
        self.addDbQuery(query, 'title ASC')
    
    def populateAllRootNotesMissingOrAutoTOC(self):
        return self.populateAllRootNotesMissing(True)
    
    def populateAllRootNotesMissing(self, ignoreAutoTOCAsRootTitle=False):
        processingFlags = NoteProcessingFlags(False)
        processingFlags.populateMissingRootTitlesList=True
        processingFlags.populateMissingRootTitlesDict=True
        processingFlags.populateExistingRootTitlesList=True
        processingFlags.populateExistingRootTitlesDict=True
        processingFlags.ignoreAutoTOCAsRootTitle = ignoreAutoTOCAsRootTitle
        self.processingFlags = processingFlags
        self.RootNotesExisting = NotesCollection()
        self.RootNotesMissing = NotesCollection()
        # log(', '.join(self.RootNotesMissing.TitlesList))
        self.getRootNotes()
        
        
        
        log (" CHECKING FOR MISSING ROOT TITLES "        , 'RootTitles-Missing', clear=True, timestamp=False)
        log ("------------------------------------------------"        , 'RootTitles-Missing', timestamp=False)
        log (" CHECKING FOR ISOLATED ROOT TITLES "        , 'RootTitles-Isolated', clear=True, timestamp=False)        
        log ("------------------------------------------------"        , 'RootTitles-Isolated', timestamp=False)
        log ("Total %d Existing Root Titles" % len(self.RootNotesExisting.TitlesList)        , 'RootTitles-Missing', timestamp=False)
        self.getChildNotes()
        log ( "Total %d Missing Root Titles" % len(self.RootNotesMissing.TitlesList), 'RootTitles-Missing', timestamp=False)
        self.RootNotesMissing.TitlesList = sorted(self.RootNotesMissing.TitlesList, key=lambda s: s.lower())
        
        
        return self.processAllRootNotesMissing()
        
   
        
    def processAllRootNotesMissing(self):
        count = 0
        count_isolated = 0
        # log (" CREATING TOC's "        , 'tocList', clear=True, timestamp=False)
        # log ("------------------------------------------------"        , 'tocList', timestamp=False)     
        ols = []
        dbRows = []
        ankDB().execute("DELETE FROM %s WHERE 1 " % TABLES.EVERNOTE.AUTO_TOC)   
        olsz = None
        for rootTitleStr in self.RootNotesMissing.TitlesList:
            count_child = 0
            childTitlesDictSortedKeys = sorted(self.RootNotesMissing.ChildTitlesDict[rootTitleStr], key=lambda s: s.lower())  
            total_child = len(childTitlesDictSortedKeys)      
            tags = []
            outline = self.getNoteFromDB("UPPER(title) = '%s' AND tagNames LIKE '%%,%s,%%'" % (escape_text_sql(rootTitleStr.upper()), EVERNOTE.TAG.OUTLINE))
            notebookGuids = {}
            if total_child is 1 and not outline:
                count_isolated += 1
                childBaseTitle = childTitlesDictSortedKeys[0]                
                childGuid = self.RootNotesMissing.ChildTitlesDict[rootTitleStr][childBaseTitle]
                enChildNote = self.RootNotesMissing.ChildNotesDict[rootTitleStr][childGuid]    
                tags = enChildNote.tags 
                log("  > ISOLATED ROOT TITLE: [%-3d]:  %-40s --> %-20s: %s %s" % (count_isolated, rootTitleStr + ':', childBaseTitle, childGuid, enChildNote), 'RootTitles-Isolated', timestamp=False)                
            else:
                count += 1     
                log("  [%-3d] %s %s" % (count, rootTitleStr, '(O)' if outline else '   '), 'RootTitles-Missing', timestamp=False)      
                # tocList = TOCList(rootTitleStr)
                tocHierarchy = TOCHierarchyClass(rootTitleStr)
                if outline:
                    tocHierarchy.outline = TOCHierarchyClass(note=outline)
                    tocHierarchy.outline.parent = tocHierarchy
                
                for childBaseTitle in childTitlesDictSortedKeys:                    
                    count_child += 1                    
                    childGuid = self.RootNotesMissing.ChildTitlesDict[rootTitleStr][childBaseTitle]
                    enChildNote = self.RootNotesMissing.ChildNotesDict[rootTitleStr][childGuid]                                              
                    if count_child == 1:
                        tags = enChildNote.tags
                    else: 
                        tags = [x for x in tags if x in enChildNote.tags]
                    if not enChildNote.notebookGuid in notebookGuids:
                        notebookGuids[enChildNote.notebookGuid] = 0
                    notebookGuids[enChildNote.notebookGuid] += 1
                    level = enChildNote.title.Count()
                    childName = enChildNote.title.Name().title
                    childTitle = enChildNote.title.title
                    log("              %2d: %d.  --> %-60s" % (count_child, level, childBaseTitle), 'RootTitles-Missing', timestamp=False)                                        
                    # tocList.generateEntry(childTitle, enChildNote)                    
                    tocHierarchy.addNote(enChildNote)
                realTitle = ankDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, childGuid))
                realTitle = realTitle[0:realTitle.index(':')]
                realTitleUTF8 = realTitle.encode('utf8')
                notebookGuid = sorted(notebookGuids.items(), key=itemgetter(1), reverse=True)[0][0]
                # if rootTitleStr.find('Antitrypsin') > -1:
                    # realTitleUTF8 = realTitle.encode('utf8')
                    # file_object = open('pytho2!nx_intro.txt', 'w')
                    # file_object.write(realTitleUTF8)
                    # file_object.close()       
                
                ol = tocHierarchy.GetOrderedList()
                dbRows.append([realTitle, ol, ',' + ','.join(tags) + ',', notebookGuid])
                # ol = realTitleUTF8
                # if olsz is None: olsz = ol
                # olsz += ol
                # ol = '<OL>\r\n%s</OL>\r\n' 
                olutf8 = ol.encode('utf8')
                # ols.append(olutf8)
                #strr = tocHierarchy.__str__()
                fn = 'toc-ols\\toc-' + str(count) + '-' + rootTitleStr.replace('\\', '_') + '.htm'
                full_path = os.path.join(ANKNOTES.FOLDER_LOGS, fn)
                if not os.path.exists(os.path.dirname(full_path)): 
                    os.mkdir(os.path.dirname(full_path))                                
                file_object = open(full_path, 'w')
                file_object.write(olutf8)
                file_object.close()                     
                
                # log(ol, 'toc-ols\\toc-' + str(count) + '-' + rootTitleStr.replace('\\', '_'), timestamp=False, clear=True, extension='htm')
                # log("Created TOC #%d:\n%s\n\n" % (count, strr), 'tocList', timestamp=False)
        # ols_html = u'\r\n<BR><BR><HR><BR><BR>\r\n'.join(ols)
        # fn = 'extra\\logs\\anknotes-toc-ols\\toc-index.htm'
        # file_object = open(fn, 'w')
        # file_object.write(ols_html)
        # file_object.close()       
        
        
        # print dbRows
        ankDB().executemany("INSERT INTO %s (root_title, contents, tagNames, notebookGuid) VALUES(?, ?, ?, ?)" % TABLES.EVERNOTE.AUTO_TOC, dbRows)
        ankDB().commit()
        
        
        
        return dbRows
    
    def populateAllRootNotesWithoutTOCOrOutlineDesignation(self):
        processingFlags = NoteProcessingFlags()
        processingFlags.populateRootTitlesList=False
        processingFlags.populateRootTitlesDict=False
        processingFlags.populateChildRootTitles = True
        self.processingFlags = processingFlags
        self.getRootNotes()
        self.processAllRootNotesWithoutTOCOrOutlineDesignation()    
        
    def processAllRootNotesWithoutTOCOrOutlineDesignation(self):
        count = 0
        for rootGuid, childBaseTitleDicts in self.RootNotesChildren.TitlesDict.items():
            rootEnNote = self.Notes[rootGuid]               
            if len(childBaseTitleDicts.items()) > 0:
                is_toc = EVERNOTE.TAG.TOC in rootEnNote.tags
                is_outline = EVERNOTE.TAG.OUTLINE in rootEnNote.tags
                is_both = is_toc and is_outline 
                is_none = not is_toc and not is_outline                                         
                is_toc_outline_str = "BOTH ???" if is_both else "TOC" if is_toc else "OUTLINE" if is_outline else "N/A"
                if is_none:
                    count += 1
                    print_safe(rootEnNote, ' TOP LEVEL: [%3d] %-8s: ' % (count, is_toc_outline_str))                