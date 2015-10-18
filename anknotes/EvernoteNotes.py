# -*- coding: utf-8 -*-
### Python Imports
from operator import itemgetter

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Main Imports
from anknotes.base import encode
from anknotes.shared import *
from anknotes.EvernoteNoteTitle import *
from anknotes.EvernoteNotePrototype import EvernoteNotePrototype
from anknotes.toc import TOCHierarchyClass
from anknotes.db import ankDB
from anknotes import stopwatch

### Anknotes Class Imports
from anknotes.EvernoteNoteTitle import generateTOCTitle

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
    ignoreOutlineAsRootTitle = False

    def __init__(self, flags=None):
        if isinstance(flags, bool):
            if not flags:
                self.set_default(False)
        if flags:
            self.update(flags)

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
    """:type : dict[str, EvernoteNote.EvernoteNote]"""
    ChildNotesDict = {}
    """:type : dict[str, EvernoteNote.EvernoteNote]"""
    ChildTitlesDict = {}

    def __init__(self):
        self.TitlesList = []
        self.TitlesDict = {}
        self.NotesDict = {}
        self.ChildNotesDict = {}
        self.ChildTitlesDict = {}


class EvernoteNotes:
    ################## CLASS Notes ################
    Notes = {}
    """:type : dict[str, EvernoteNote.EvernoteNote]"""
    RootNotes = EvernoteNotesCollection()
    RootNotesChildren = EvernoteNotesCollection()
    processingFlags = EvernoteNoteProcessingFlags()
    baseQuery = "1"

    def __init__(self, delayProcessing=False):
        self.processingFlags.delayProcessing = delayProcessing
        self.RootNotes = EvernoteNotesCollection()

    def addNoteSilently(self, enNote):
        """:type enNote: EvernoteNote.EvernoteNote"""
        assert enNote
        self.Notes[enNote.Guid] = enNote

    def addNote(self, enNote):
        """:type enNote: EvernoteNote.EvernoteNote"""
        assert enNote
        self.addNoteSilently(enNote)
        if self.processingFlags.delayProcessing:
            return
        self.processNote(enNote)

    def addDBNote(self, dbNote):
        """:type dbNote: sqlite.Row"""
        enNote = EvernoteNotePrototype(db_note=dbNote)
        if not enNote:
            log(dbNote)
            log(dbNote.keys)
            log(dir(dbNote))
        assert enNote
        self.addNote(enNote)

    def addDBNotes(self, dbNotes):
        """:type dbNotes: list[sqlite.Row]"""
        for dbNote in dbNotes:
            self.addDBNote(dbNote)

    def addDbQuery(self, sql_query, order=''):
        if not sql_query:
            sql_query = '1'
        if self.baseQuery and self.baseQuery != '1':
            if sql_query == '1':
                sql_query = self.baseQuery
            else:
                sql_query = "(%s) AND (%s) " % (self.baseQuery, sql_query)
        if order:
            sql_query += ' ORDER BY ' + order
        dbNotes = ankDB().execute(sql_query)
        self.addDBNotes(dbNotes)

    @staticmethod
    def getNoteFromDB(query):
        """

        :param query:
        :return:
        :rtype : sqlite.Row
        """
        dbNote = ankDB().first(query)
        if not dbNote:
            return None
        return dbNote

    def getNoteFromDBByGuid(self, guid):
        sql_query = "guid = '%s' " % guid
        return self.getNoteFromDB(sql_query)

    def getEnNoteFromDBByGuid(self, guid):
        return EvernoteNotePrototype(db_note=self.getNoteFromDBByGuid(guid))

    # def addChildNoteHierarchically(self, enChildNotes, enChildNote):
    #     parts = enChildNote.Title.TitleParts
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
        """:type enNote: EvernoteNote.EvernoteNote"""
        db = ankDB()
        if self.processingFlags.populateRootTitlesList or self.processingFlags.populateRootTitlesDict or self.processingFlags.populateMissingRootTitlesList or self.processingFlags.populateMissingRootTitlesDict:
            if enNote.IsChild:
                # log([enNote.Title, enNote.Level, enNote.Title.TitleParts, enNote.IsChild])
                rootTitle = enNote.Title.Root
                rootTitleStr = generateTOCTitle(rootTitle)
                if self.processingFlags.populateMissingRootTitlesList or self.processingFlags.populateMissingRootTitlesDict:
                    if not rootTitleStr in self.RootNotesExisting.TitlesList:
                        if not rootTitleStr in self.RootNotesMissing.TitlesList:
                            self.RootNotesMissing.TitlesList.append(rootTitleStr)
                            self.RootNotesMissing.ChildTitlesDict[rootTitleStr] = {}
                            self.RootNotesMissing.ChildNotesDict[rootTitleStr] = {}
                        if not enNote.Title.Base:
                            log(enNote.Title)
                            log(enNote.Base)
                        assert enNote.Title.Base
                        childBaseTitleStr = enNote.Title.Base.FullTitle
                        if childBaseTitleStr in self.RootNotesMissing.ChildTitlesDict[rootTitleStr]:
                            log_error("Duplicate Child Base Title String. \n%-18s%s\n%-18s%s: %s\n%-18s%s" % (
                                'Root Note Title: ', rootTitleStr, 'Child Note: ', enNote.Guid, childBaseTitleStr,
                                'Duplicate Note: ',
                                self.RootNotesMissing.ChildTitlesDict[rootTitleStr][childBaseTitleStr]),
                                      crosspost_to_default=False)
                            if not hasattr(self, 'loggedDuplicateChildNotesWarning'):
                                log(
                                    "     > WARNING: Duplicate Child Notes found when processing Root Notes. See error log for more details")
                                self.loggedDuplicateChildNotesWarning = True
                        self.RootNotesMissing.ChildTitlesDict[rootTitleStr][childBaseTitleStr] = enNote.Guid
                        self.RootNotesMissing.ChildNotesDict[rootTitleStr][enNote.Guid] = enNote
                if self.processingFlags.populateRootTitlesList or self.processingFlags.populateRootTitlesDict:
                    if not rootTitleStr in self.RootNotes.TitlesList:
                        self.RootNotes.TitlesList.append(rootTitleStr)
                        if self.processingFlags.populateRootTitlesDict:
                            self.RootNotes.TitlesDict[rootTitleStr][enNote.Guid] = enNote.Title.Base
                            self.RootNotes.NotesDict[rootTitleStr][enNote.Guid] = enNote
        if self.processingFlags.populateChildRootTitles or self.processingFlags.populateExistingRootTitlesList or self.processingFlags.populateExistingRootTitlesDict:
            if enNote.IsRoot:
                rootTitle = enNote.Title
                rootTitleStr = generateTOCTitle(rootTitle)
                rootGuid = enNote.Guid
                if self.processingFlags.populateExistingRootTitlesList or self.processingFlags.populateExistingRootTitlesDict or self.processingFlags.populateMissingRootTitlesList:
                    if not rootTitleStr in self.RootNotesExisting.TitlesList:
                        self.RootNotesExisting.TitlesList.append(rootTitleStr)
                if self.processingFlags.populateChildRootTitles:
                    childNotes = db.execute("title LIKE ? || ':%' ORDER BY title ASC", rootTitleStr)
                    child_count = 0
                    for childDbNote in childNotes:
                        child_count += 1
                        childGuid = childDbNote['guid']
                        childEnNote = EvernoteNotePrototype(db_note=childDbNote)
                        if child_count is 1:
                            self.RootNotesChildren.TitlesDict[rootGuid] = {}
                            self.RootNotesChildren.NotesDict[rootGuid] = {}
                        childBaseTitle = childEnNote.Title.Base
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
                query += " AND tagNames NOT LIKE '%%,%s,%%'" % TAGS.TOC_AUTO
            if self.processingFlags.ignoreOutlineAsRootTitle:
                query += " AND tagNames NOT LIKE '%%,%s,%%'" % TAGS.OUTLINE
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
            query += " AND tagNames NOT LIKE '%%,%s,%%'" % TAGS.TOC_AUTO
        if self.processingFlags.ignoreOutlineAsRootTitle:
            query += " AND tagNames NOT LIKE '%%,%s,%%'" % TAGS.OUTLINE
        self.addDbQuery(query, 'title ASC')

    def populateAllPotentialRootNotes(self):
        self.RootNotesMissing = EvernoteNotesCollection()
        processingFlags = EvernoteNoteProcessingFlags(False)
        processingFlags.populateMissingRootTitlesList = True
        processingFlags.populateMissingRootTitlesDict = True
        self.processingFlags = processingFlags

        log_banner(" CHECKING FOR ALL POTENTIAL ROOT TITLES ", 'RootTitles\\TOC', clear=True, timestamp=False)
        log_banner(" CHECKING FOR ISOLATED ROOT TITLES ", 'RootTitles\\Isolated', clear=True, timestamp=False)
        self.getChildNotes()
        log("Total %d Missing Root Titles" % len(self.RootNotesMissing.TitlesList), 'RootTitles\\TOC',
            timestamp=False)
        self.RootNotesMissing.TitlesList = sorted(self.RootNotesMissing.TitlesList, key=lambda s: s.lower())

        return self.processAllRootNotesMissing()

    def populateAllNonCustomRootNotes(self):
        return self.populateAllRootNotesMissing(True, True)

    def populateAllRootNotesMissing(self, ignoreAutoTOCAsRootTitle=False, ignoreOutlineAsRootTitle=False):
        processingFlags = EvernoteNoteProcessingFlags(False)
        processingFlags.populateMissingRootTitlesList = True
        processingFlags.populateMissingRootTitlesDict = True
        processingFlags.populateExistingRootTitlesList = True
        processingFlags.populateExistingRootTitlesDict = True
        processingFlags.ignoreAutoTOCAsRootTitle = ignoreAutoTOCAsRootTitle
        processingFlags.ignoreOutlineAsRootTitle = ignoreOutlineAsRootTitle
        self.processingFlags = processingFlags
        self.RootNotesExisting = EvernoteNotesCollection()
        self.RootNotesMissing = EvernoteNotesCollection()
        # log(', '.join(self.RootNotesMissing.TitlesList))
        self.getRootNotes()

        log_banner(" CHECKING FOR MISSING ROOT TITLES ", 'RootTitles\\Missing', clear=True, timestamp=False)
        log_banner(" CHECKING FOR ISOLATED ROOT TITLES ", 'RootTitles\\Isolated', clear=True, timestamp=False)
        log("Total %d Existing Root Titles" % len(self.RootNotesExisting.TitlesList), 'RootTitles\\Missing',
            timestamp=False)
        self.getChildNotes()
        log("Total %d Missing Root Titles" % len(self.RootNotesMissing.TitlesList), 'RootTitles\\Missing',
            timestamp=False)
        self.RootNotesMissing.TitlesList = sorted(self.RootNotesMissing.TitlesList, key=lambda s: s.lower())

        return self.processAllRootNotesMissing()

    def processAllRootNotesMissing(self):
        """:rtype : list[EvernoteTOCEntry]"""
        DEBUG_HTML = False
        # log (" CREATING TOC's "        , 'tocList', clear=True, timestamp=False)
        # log ("------------------------------------------------"        , 'tocList', timestamp=False)
        # if DEBUG_HTML: log('<h1>CREATING TOCs</h1>', 'extra\\logs\\toc-ols\\toc-index.htm', timestamp=False, clear=True, extension='htm')
        ols = []
        dbRows = []
        returns = []
        """:type : list[EvernoteTOCEntry]"""
        db = ankDB(TABLES.TOC_AUTO)
        db.delete("1", table=db.table)
        db.commit()
        # olsz = None
        tmr = stopwatch.Timer(self.RootNotesMissing.TitlesList, infoStr='Processing Root Notes', label='RootTitles\\')
        for rootTitleStr in self.RootNotesMissing.TitlesList:
            count_child = 0
            childTitlesDictSortedKeys = sorted(self.RootNotesMissing.ChildTitlesDict[rootTitleStr],
                                               key=lambda s: s.lower())
            total_child = len(childTitlesDictSortedKeys)
            tags = []
            outline = self.getNoteFromDB("UPPER(title) = '%s' AND tagNames LIKE '%%,%s,%%'" % (
                escape_text_sql(rootTitleStr.upper()), TAGS.OUTLINE))
            currentAutoNote = self.getNoteFromDB("UPPER(title) = '%s' AND tagNames LIKE '%%,%s,%%'" % (
                escape_text_sql(rootTitleStr.upper()), TAGS.TOC_AUTO))
            notebookGuids = {}
            childGuid = None
            is_isolated = total_child is 1 and not outline
            if is_isolated:
                tmr.counts.isolated.step()
                childBaseTitle = childTitlesDictSortedKeys[0]
                childGuid = self.RootNotesMissing.ChildTitlesDict[rootTitleStr][childBaseTitle]
                enChildNote = self.RootNotesMissing.ChildNotesDict[rootTitleStr][childGuid]
                # tags = enChildNote.Tags
                log("  > ISOLATED ROOT TITLE: [%-3d]:  %-60s --> %-40s: %s" % (
                    tmr.counts.isolated.val, rootTitleStr + ':', childBaseTitle, childGuid), tmr.label + 'Isolated',
                    timestamp=False)
            else:
                tmr.counts.created.completed.step()
                log_blank(tmr.label + 'TOC')
                log("  [%-3d] %s %s" % (tmr.count, rootTitleStr, '(O)' if outline else '   '), tmr.label + 'TOC',
                    timestamp=False)

            tmr.step(rootTitleStr)

            if is_isolated:
                continue

            tocHierarchy = TOCHierarchyClass(rootTitleStr)
            if outline:
                tocHierarchy.Outline = TOCHierarchyClass(note=outline)
                tocHierarchy.Outline.parent = tocHierarchy

            for childBaseTitle in childTitlesDictSortedKeys:
                count_child += 1
                childGuid = self.RootNotesMissing.ChildTitlesDict[rootTitleStr][childBaseTitle]
                enChildNote = self.RootNotesMissing.ChildNotesDict[rootTitleStr][childGuid]
                if count_child == 1:
                    tags = enChildNote.Tags
                else:
                    tags = [x for x in tags if x in enChildNote.Tags]
                if not enChildNote.NotebookGuid in notebookGuids:
                    notebookGuids[enChildNote.NotebookGuid] = 0
                notebookGuids[enChildNote.NotebookGuid] += 1
                level = enChildNote.Title.Level
                # childName = enChildNote.Title.Name
                # childTitle = enChildNote.FullTitle
                log("              %2d: %d.  --> %-60s" % (count_child, level, childBaseTitle),
                    tmr.label + 'TOC', timestamp=False)
                # tocList.generateEntry(childTitle, enChildNote)
                tocHierarchy.addNote(enChildNote)
            realTitle = get_evernote_title_from_guid(childGuid)
            realTitle = realTitle[0:realTitle.index(':')]
            # realTitleUTF8 = realTitle.encode('utf8')
            notebookGuid = sorted(notebookGuids.items(), key=itemgetter(1), reverse=True)[0][0]

            real_root_title = generateTOCTitle(realTitle)

            ol = tocHierarchy.GetOrderedList()
            tocEntry = EvernoteTOCEntry(real_root_title, ol, ',' + ','.join(tags) + ',', notebookGuid)
            returns.append(tocEntry)
            dbRows.append(tocEntry.items())

            if not DEBUG_HTML:
                continue

            # ols.append(ol)
            # olutf8 = encode(ol)
            # fn = 'toc-ols\\toc-' + str(tmr.count) + '-' + rootTitleStr.replace('\\', '_') + '.htm'
            # full_path = os.path.join(FOLDERS.LOGS, fn)
            # if not os.path.exists(os.path.dirname(full_path)):
                # os.mkdir(os.path.dirname(full_path))
            # file_object = open(full_path, 'w')
            # file_object.write(olutf8)
            # file_object.close()

            # if DEBUG_HTML: log(ol, 'toc-ols\\toc-' + str(count) + '-' + rootTitleStr.replace('\\', '_'), timestamp=False, clear=True, extension='htm')
            # log("Created TOC #%d:\n%s\n\n" % (count, str_), 'tocList', timestamp=False)
        if DEBUG_HTML:
            ols_html = u'\r\n<BR><BR><HR><BR><BR>\r\n'.join(ols)
            fn = 'toc-ols\\toc-index.htm'
            file_object = open(os.path.join(FOLDERS.LOGS, fn), 'w')
            try:
                file_object.write(u'<h1>CREATING TOCs</h1>\n\n' + ols_html)
            except Exception:
                try:
                    file_object.write(u'<h1>CREATING TOCs</h1>\n\n' + encode(ols_html))
                except Exception:
                    pass

            file_object.close()

        db.executemany("INSERT INTO {t} (root_title, contents, tagNames, notebookGuid) VALUES(?, ?, ?, ?)", dbRows)
        db.commit()

        return returns

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
                is_toc = TAGS.TOC in rootEnNote.Tags
                is_outline = TAGS.OUTLINE in rootEnNote.Tags
                is_both = is_toc and is_outline
                is_none = not is_toc and not is_outline
                is_toc_outline_str = "BOTH ???" if is_both else "TOC" if is_toc else "OUTLINE" if is_outline else "N/A"
                if is_none:
                    count += 1
                    print_safe(rootEnNote, ' TOP LEVEL: [%3d] %-8s: ' % (count, is_toc_outline_str))
