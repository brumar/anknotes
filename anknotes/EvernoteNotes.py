# -*- coding: utf-8 -*-
### Python Imports
from operator import itemgetter
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Imports
# from anknotes.shared import *
from anknotes.toc import *
from anknotes.EvernoteNote import EvernoteNote



class EvernoteNoteProcessingFlags:
    delayProcessing = False
    populateRootTitlesList = True
    populateRootTitlesDict = True
    populateExistingRootTitlesList = False
    populateExistingRootTitlesDict = False
    populateMissingRootTitlesList = False
    populateMissingRootTitlesDict = False
    populateChildRootTitles = False
    ignoreAutoTOCAsRootTitle = False

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
                setattr(self, flag_name, flag_value)


class EvernoteNotesCollection:
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


class EvernoteNotes:
    ################## CLASS Notes ################
    Notes = {}
    RootNotes = EvernoteNotesCollection()
    RootNotesChildren = EvernoteNotesCollection()
    processingFlags = EvernoteNoteProcessingFlags()
    baseQuery = "1"

    def __init__(self, delayProcessing=False):
        self.processingFlags.delayProcessing = delayProcessing
        self.RootNotes = EvernoteNotesCollection()

    def addNoteSilently(self, enNote):
        self.Notes[enNote.guid] = enNote

    def addNote(self, enNote):
        self.addNoteSilently(enNote)
        if self.processingFlags.delayProcessing: return
        self.processNote(enNote)

    def addDBNote(self, dbNote):
        enNote = EvernoteNote(db_note=dbNote)
        self.addNote(enNote)

    def addDBNotes(self, dbNotes):
        for dbNote in dbNotes:
            self.addDBNote(dbNote)

    def addDbQuery(self, sql_query, order=''):
        sql_query = "SELECT *  FROM %s WHERE (%s) AND (%s) " % (TABLES.EVERNOTE.NOTES, self.baseQuery, sql_query)
        if order: sql_query += ' ORDER BY ' + order
        dbNotes = ankDB().execute(sql_query)
        self.addDBNotes(dbNotes)

    @staticmethod
    def getNoteFromDB(query):
        sql_query = "SELECT *  FROM %s WHERE %s " % (TABLES.EVERNOTE.NOTES, query)
        dbNote = ankDB().first(sql_query)
        if not dbNote: return None
        return dbNote

    def getNoteFromDBByGuid(self, guid):
        sql_query = "guid = '%s' " % guid
        return self.getNoteFromDB(sql_query)

    # def addChildNoteHierarchically(self, enChildNotes, enChildNote):
    #     parts = enChildNote.title.PartsText()
    #     dict_updated = {}
    #     dict_building = {parts[len(parts)-1]: enChildNote}
    #     print_safe(parts)
    #     for i in range(len(parts), 1, -1):
    #         dict_building = {parts[i - 1]: dict_building}
    #     log_dump(dict_building)
    #     enChildNotes.update(dict_building)
    #     log_dump(enChildNotes)
    #     return enChildNotes

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
                if self.processingFlags.populateExistingRootTitlesList or self.processingFlags.populateExistingRootTitlesDict or self.processingFlags.populateMissingRootTitlesList:
                    if not rootTitleStr in self.RootNotesExisting.TitlesList:
                        self.RootNotesExisting.TitlesList.append(rootTitleStr)
                if self.processingFlags.populateChildRootTitles:
                    childNotes = ankDB().execute("SELECT * FROM %s WHERE title LIKE '%s:%%' ORDER BY title ASC" % (
                    TABLES.EVERNOTE.NOTES, rootTitleStr.replace("'", "''")))
                    child_count = 0
                    for childDbNote in childNotes:
                        child_count += 1
                        childGuid = childDbNote['guid']
                        childEnNote = EvernoteNote(db_note=childDbNote)
                        if child_count is 1:
                            self.RootNotesChildren.TitlesDict[rootGuid] = {}
                            self.RootNotesChildren.NotesDict[rootGuid] = {}
                        childBaseTitle = childEnNote.title.Base()
                        self.RootNotesChildren.TitlesDict[rootGuid][childGuid] = childBaseTitle
                        self.RootNotesChildren.NotesDict[rootGuid][childGuid] = childEnNote

    def processNotes(self, populateRootTitlesList=True, populateRootTitlesDict=True):
        if self.processingFlags.populateRootTitlesList or self.processingFlags.populateRootTitlesDict:
            self.RootNotes = EvernoteNotesCollection()

        self.processingFlags.populateRootTitlesList = populateRootTitlesList
        self.processingFlags.populateRootTitlesDict = populateRootTitlesDict

        for guid, enNote in self.Notes:
            self.processNote(enNote)

    def processAllChildNotes(self):
        self.processingFlags.populateRootTitlesList = True
        self.processingFlags.populateRootTitlesDict = True
        self.processNotes()

    def populateAllRootTitles(self):
        self.getChildNotes()
        self.processAllRootTitles()

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
                self.RootNotesExisting.TitlesList.append(rootTitle)
            else:
                self.RootNotesMissing.TitlesList.append(rootTitle)
                print_safe(rootNote, ' TOP LEVEL: [%4d::%2d]: [%7s] ' % (count, baseNoteCount, 'is_toc_outline_str'))
                # for baseGuid, baseTitle in baseTitles:
                #     pass

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
        processingFlags = EvernoteNoteProcessingFlags(False)
        processingFlags.populateMissingRootTitlesList = True
        processingFlags.populateMissingRootTitlesDict = True
        processingFlags.populateExistingRootTitlesList = True
        processingFlags.populateExistingRootTitlesDict = True
        processingFlags.ignoreAutoTOCAsRootTitle = ignoreAutoTOCAsRootTitle
        self.processingFlags = processingFlags
        self.RootNotesExisting = EvernoteNotesCollection()
        self.RootNotesMissing = EvernoteNotesCollection()
        # log(', '.join(self.RootNotesMissing.TitlesList))
        self.getRootNotes()

        log(" CHECKING FOR MISSING ROOT TITLES ", 'RootTitles-Missing', clear=True, timestamp=False)
        log("------------------------------------------------", 'RootTitles-Missing', timestamp=False)
        log(" CHECKING FOR ISOLATED ROOT TITLES ", 'RootTitles-Isolated', clear=True, timestamp=False)
        log("------------------------------------------------", 'RootTitles-Isolated', timestamp=False)
        log("Total %d Existing Root Titles" % len(self.RootNotesExisting.TitlesList), 'RootTitles-Missing',
            timestamp=False)
        self.getChildNotes()
        log("Total %d Missing Root Titles" % len(self.RootNotesMissing.TitlesList), 'RootTitles-Missing',
            timestamp=False)
        self.RootNotesMissing.TitlesList = sorted(self.RootNotesMissing.TitlesList, key=lambda s: s.lower())

        return self.processAllRootNotesMissing()

    def processAllRootNotesMissing(self):
        count = 0
        count_isolated = 0
        # log (" CREATING TOC's "        , 'tocList', clear=True, timestamp=False)
        # log ("------------------------------------------------"        , 'tocList', timestamp=False)     
        # ols = []
        dbRows = []
        ankDB().execute("DELETE FROM %s WHERE 1 " % TABLES.EVERNOTE.AUTO_TOC)
        # olsz = None
        for rootTitleStr in self.RootNotesMissing.TitlesList:
            count_child = 0
            childTitlesDictSortedKeys = sorted(self.RootNotesMissing.ChildTitlesDict[rootTitleStr],
                                               key=lambda s: s.lower())
            total_child = len(childTitlesDictSortedKeys)
            tags = []
            outline = self.getNoteFromDB("UPPER(title) = '%s' AND tagNames LIKE '%%,%s,%%'" % (
            escape_text_sql(rootTitleStr.upper()), EVERNOTE.TAG.OUTLINE))
            notebookGuids = {}
            childGuid = None
            if total_child is 1 and not outline:
                count_isolated += 1
                childBaseTitle = childTitlesDictSortedKeys[0]
                childGuid = self.RootNotesMissing.ChildTitlesDict[rootTitleStr][childBaseTitle]
                enChildNote = self.RootNotesMissing.ChildNotesDict[rootTitleStr][childGuid]
                # tags = enChildNote.tags
                log("  > ISOLATED ROOT TITLE: [%-3d]:  %-40s --> %-20s: %s %s" % (
                count_isolated, rootTitleStr + ':', childBaseTitle, childGuid, enChildNote), 'RootTitles-Isolated',
                    timestamp=False)
            else:
                count += 1
                log("  [%-3d] %s %s" % (count, rootTitleStr, '(O)' if outline else '   '), 'RootTitles-Missing',
                    timestamp=False)
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
                    # childName = enChildNote.title.Name().title
                    # childTitle = enChildNote.title.title
                    log("              %2d: %d.  --> %-60s" % (count_child, level, childBaseTitle),
                        'RootTitles-Missing', timestamp=False)
                    # tocList.generateEntry(childTitle, enChildNote)                    
                    tocHierarchy.addNote(enChildNote)
                realTitle = ankDB().scalar(
                    "SELECT title FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, childGuid))
                realTitle = realTitle[0:realTitle.index(':')]
                # realTitleUTF8 = realTitle.encode('utf8')
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
                # strr = tocHierarchy.__str__()
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
        ankDB().executemany(
            "INSERT INTO %s (root_title, contents, tagNames, notebookGuid) VALUES(?, ?, ?, ?)" % TABLES.EVERNOTE.AUTO_TOC,
            dbRows)
        ankDB().commit()

        return dbRows

    def populateAllRootNotesWithoutTOCOrOutlineDesignation(self):
        processingFlags = EvernoteNoteProcessingFlags()
        processingFlags.populateRootTitlesList = False
        processingFlags.populateRootTitlesDict = False
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
