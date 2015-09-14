from anknotes.constants import *
from anknotes.html import generate_evernote_link, generate_evernote_span
from anknotes.logging import log_dump
from anknotes.EvernoteNoteTitle import EvernoteNoteTitle

def TOCNamePriority(title):
    for index, value in enumerate(
            ['Summary', 'Definition', 'Classification', 'Types', 'Presentation', 'Organ Involvement', 'Age of Onset',
             'Si/Sx', 'Sx', 'Sign', 'MCC\'s', 'MCC', 'Inheritance', 'Incidence', 'Prognosis', 'Mechanism', 'MOA',
             'Pathophysiology', 'Indications', 'Examples', 'Cause', 'Causes', 'Causative Organisms', 'Risk Factors',
             'Complication', 'Complications', 'Side Effects', 'Drug S/E', 'Associated Conditions', 'A/w', 'Dx',
             'Physical Exam', 'Labs', 'Hemodynamic Parameters', 'Lab Findings', 'Imaging', 'Screening Test',
             'Confirmatory Test']):
        if title == value: return -1, index
    for index, value in enumerate(['Management', 'Work Up', 'Tx']):
        if title == value: return 1, index
    return 0, 0


def TOCNameSort(title1, title2):
    priority1 = TOCNamePriority(title1)
    priority2 = TOCNamePriority(title2)
    # Lower value for item 1 = item 1 placed BEFORE item 2
    if priority1[0] != priority2[0]: return priority1[0] - priority2[0]
    if priority1[1] != priority2[1]: return priority1[1] - priority2[1]
    return cmp(title1, title2)


def TOCSort(hash1, hash2):
    lvl1 = hash1.Level
    lvl2 = hash2.Level
    names1 = hash1.TitleParts
    names2 = hash2.TitleParts
    for i in range(0, min(lvl1, lvl2)):
        name1 = names1[i]
        name2 = names2[i]
        if name1 != name2: return TOCNameSort(name1, name2)
    # Lower value for item 1 = item 1 placed BEFORE item 2
    return lvl1 - lvl2


class TOCHierarchyClass:
    title = None
    note = None
    outline = None
    number = 1
    children = []
    parent = None
    isSorted = False

    @staticmethod
    def TOCItemSort(tocHierarchy1, tocHierarchy2):
        lvl1 = tocHierarchy1.Level
        lvl2 = tocHierarchy2.Level
        names1 = tocHierarchy1.TitleParts
        names2 = tocHierarchy2.TitleParts
        for i in range(0, min(lvl1, lvl2)):
            name1 = names1[i]
            name2 = names2[i]
            if name1 != name2: return TOCNameSort(name1, name2)
        # Lower value for item 1 = item 1 placed BEFORE item 2
        return lvl1 - lvl2

    def isOutline(self):
        if not self.note: return False
        return EVERNOTE.TAG.OUTLINE in self.note.tags

    def sortIfNeeded(self):
        if self.isSorted: return
        self.sortChildren()

    def Level(self):
        return self.title.Level

    def ChildrenCount(self):
        return len(self.children)

    def TitleParts(self):
        return self.title.TitleParts

    def addNote(self, note):
        tocHierarchy = TOCHierarchyClass(note=note)
        self.addHierarchy(tocHierarchy)

    def getChildIndex(self, tocChildHierarchy):
        if not tocChildHierarchy in self.children: return -1
        self.sortIfNeeded()
        return self.children.index(tocChildHierarchy)

    def getListPrefix(self):
        index = self.getIndex()
        isSingleItem = self.getIsSingleItem()
        if isSingleItem is 0: return ""
        if isSingleItem is 1: return "*"
        return str(index) + "."

    def getIsSingleItem(self):
        index = self.getIndex()
        if index is 0: return 0
        if index is 1 and len(self.parent.children) is 1:
            return 1
        return -1

    def getIndex(self):
        if not self.parent: return 0
        return self.parent.getChildIndex(self) + 1

    def addTitle(self, title):
        self.addHierarchy(TOCHierarchyClass(title))

    def addHierarchy(self, tocHierarchy):
        tocNewTitle = tocHierarchy.title
        tocNewLevel = tocNewTitle.Level
        selfLevel = self.title.Level
        selfTitleStr = self.title.FullTitle
        # tocTitleStr = tocNewTitle.Title

        if selfLevel is 1 and tocNewLevel is 1:
            log_dump(self.title.FullTitle)
            log_dump(tocHierarchy.note.tags)
            assert tocHierarchy.isOutline()
            tocHierarchy.parent = self
            self.outline = tocHierarchy
            return True

        parentTitle = tocNewTitle.Parent()
        parentTitleStr = parentTitle.Title
        parentLevel = parentTitle.Level

        if selfTitleStr == parentTitleStr or parentTitleStr.upper() == selfTitleStr:
            tocHierarchy.parent = self
            self.isSorted = False
            self.children.append(tocHierarchy)
            return True

        assert parentLevel > selfLevel

        baseTitle = parentTitle.Parent(selfLevel + 1)
        baseTitleStr = baseTitle.Title
        baseTitleName = baseTitle.Name()
        baseTitleChildren = tocNewTitle.Names(selfLevel + 1)
        baseTitleChildrenStr = baseTitleChildren.Title
        baseTitleParentTitle = baseTitle.Parent().Title
        if selfTitleStr == baseTitleParentTitle:
            for child in self.children:
                # childTitleName = child.title.Name()
                if child.title.Name() == baseTitleName:
                    success = child.addHierarchy(tocHierarchy)
                    if not success: print "Failed searching %s for child %s to add %s " % (
                        selfTitleStr, baseTitle.Name(), baseTitleChildrenStr)
                    return success
            newChild = TOCHierarchyClass(baseTitleStr)
            newChild.addHierarchy(tocHierarchy)
            newChild.parent = self
            self.isSorted = False
            self.children.append(newChild)
            return True
        else:
            print "baseTitleParentTitle Fail:  %s for child %s to add %s " % (
                selfTitleStr, baseTitle.Name(), baseTitleChildrenStr)

        print "Total Fail:  %s for child %s to add %s " % (selfTitleStr, baseTitle.Name(), baseTitleChildrenStr)
        return False

    def sortChildren(self):
        self.children = sorted(self.children, self.TOCItemSort)
        self.isSorted = True

    def __strsingle__(self, fullTitle=False):
        selfTitleStr = self.title.FullTitle
        selfNameStr = self.title.Name()
        selfLevel = self.title.Level
        selfDepth = self.title.Depth
        selfListPrefix = self.getListPrefix()
        strr = ''
        if selfLevel == 1:
            strr += '  [%d]           ' % len(self.children)
        else:
            if len(self.children):
                strr += '  [%d:%2d]       ' % (selfDepth, len(self.children))
            else:
                strr += '  [%d]          ' % selfDepth
            strr += ' ' * (selfDepth * 3)
            strr += ' %s ' % selfListPrefix

        strr += '%-60s  %s' % (selfTitleStr if fullTitle else selfNameStr, '' if self.note else '(No Note)')
        return strr

    def __str__(self, fullTitle=True, fullChildrenTitles=False):
        self.sortIfNeeded()
        lst = [self.__strsingle__(fullTitle)]
        for child in self.children:
            lst.append(child.__str__(fullChildrenTitles, fullChildrenTitles))
        return '\n'.join(lst)

    def GetOrderedListItem(self, title=None):
        if not title: title = self.title.FullTitle
        selfTitleStr = title
        selfLevel = self.title.Level
        selfDepth = self.title.Depth
        if selfLevel == 1:
            guid = 'guid-pending'
            if self.note: guid = self.note.guid
            link = generate_evernote_link(guid, generateTOCTitle(selfTitleStr), 'TOC')
            if self.outline:
                link += ' ' + generate_evernote_link(self.outline.note.guid,
                                                     '(<span style="color: rgb(255, 255, 255);">O</span>)', 'Outline',
                                                     escape=False)
            return link
        if self.note:
            return self.note.generateLevelLink(selfDepth)
        else:
            return generate_evernote_span(selfTitleStr, 'Levels', selfDepth)

    def GetOrderedList(self, title=None):
        self.sortIfNeeded()
        lst = []
        header = (self.GetOrderedListItem(title))
        if self.ChildrenCount() > 0:
            for child in self.children:
                lst.append(child.GetOrderedList())
            childHTML = '\n'.join(lst)
        else:
            childHTML = ''
        if childHTML:
            tag = 'ol' if self.ChildrenCount > 1 else 'ul'
            base = '<%s>\r\n%s\r\n</%s>\r\n'
            # base = base.encode('utf8')
            # tag = tag.encode('utf8')
            # childHTML = childHTML.encode('utf8')
            childHTML = base % (tag, childHTML, tag)

        if self.Level() is 1:
            base = '<div> %s </div>\r\n %s \r\n'
            # base = base.encode('utf8')
            # childHTML = childHTML.encode('utf8')
            # header = header.encode('utf8')
            base = base % (header, childHTML)
            return base
        base = '<li> %s \r\n %s \r\n</li> \r\n'
        # base = base.encode('utf8')
        # header = header.encode('utf8')
        # childHTML = childHTML.encode('utf8')
        base = base % (header, childHTML)
        return base

    def __reprsingle__(self, fullTitle=True):
        selfTitleStr = self.title.FullTitle
        selfNameStr = self.title.Name()
        # selfLevel = self.title.Level()
        # selfDepth = self.title.Depth()
        selfListPrefix = self.getListPrefix()
        strr = "<%s:%s[%d] %s%s>" % (
            self.__class__.__name__, selfListPrefix, len(self.children), selfTitleStr if fullTitle else selfNameStr,
            '' if self.note else ' *')
        return strr

    def __repr__(self, fullTitle=True, fullChildrenTitles=False):
        self.sortIfNeeded()
        lst = [self.__reprsingle__(fullTitle)]
        for child in self.children:
            lst.append(child.__repr__(fullChildrenTitles, fullChildrenTitles))
        return '\n'.join(lst)

    def __init__(self, title=None, note=None, number=1):
        assert note or title
        self.outline = None
        if note:
            self.note = note
            self.title = EvernoteNoteTitle(note.title.title)
        else:
            self.title = EvernoteNoteTitle(title)
            self.note = None
        self.number = number
        self.children = []
        self.isSorted = False
        return

        # class TOCListItem:
        # tocHash = None
        # tocValue = None
        # def Level(self): return self.tocHash.Level()
        # def __init__(self, tocHash, tocValue):
        # self.tocHash = tocHash
        # self.tocValue = tocValue

        # class TOCList:
        # toc = {}
        # # tocKeyRoot = tocKey
        # # tocKeyLast = tocKey
        # tocKeyParents = {}

        # def populateTOCValueWithChildren(self, tocValue, recursive=False):
        # tocKey = tocValue.Key
        # if not tocValue.Children:
        # tocValue.Children = self.getChildren(tocKey)
        # return tocValue

        # def getChildrenRecursive(self, parentTitleOrTOCHash):
        # tocKeyParent = TOCKey(parentTitleOrTOCHash)
        # return {tocHash: self.populateTOCValueWithChildren(self.tocValue) for tocHash, tocValue in self.toc.iterItems() if tocHash['Level'] == tocKeyParent.Level() + 1 and tocHash['Parent'] == tocKeyParent.Title }

        # def getChildren(self, parentTitleOrTOCHash, recursive=False):
        # tocKeyParent = TOCKey(parentTitleOrTOCHash)
        # return {tocHash: self.populateTOCValueWithChildren(tocValue, True) if recursive else tocValue for tocHash, tocValue in self.toc.iterItems() if tocHash['Level'] == tocKeyParent.Level() + 1 and tocHash['Parent'] == tocKeyParent.Title }

        # def getTOCListItem(self, titleOrTOCHash):
        # return TOCListItem(TOCKey(titleOrTOCHash), self.toc[titleOrTOCHash])

        # def sortedKeys(self):
        # return sorted(self.toc, TOCSort)

        # def getTOCListItems(self):
        # return [self.getTOCListItem(x) for x in self.sortedKeys()]

        # def __str__(self):
        # lst = []
        # for tocListItem in self.getTOCListItems():
        # tocHash = tocListItem.tocHash
        # tocValue = tocListItem.tocValue
        # lvl = tocListItem.Level()
        # title = tocHash #.Title()
        # if tocHash.Level() > 1:
        # if not tocValue.Note:
        # print "No Note for %d. %s" % (lvl, title)
        # else: guid = tocValue.Note.guid
        # note_str = '(+ Note)' if tocValue.Note else ' ** BLANK ENTRY WITHOUT NOTE **' if lvl> 1 else ''
        # if not tocValue.Children:
        # children_str = '(Children N/A)'
        # else:
        # children_str = '(%d Children)' % len(tocValue.Children) if len(tocValue.Children) > 1 else 'One Child' if len(tocValue.Children) is 1 else ''

        # lst.append("%d: %-100s %-10s %-10s" % (lvl, title, note_str, children_str ))
        # return '\n'.join(lst)

        # def __repl__(self):
        # lst = []
        # for tocHash in self.sortedKeys():
        # tocValue = self.toc[tocHash]
        # lst.append("<TOCListItem:%d.%s" % (tocHash.Level(), tocHash.Title()))
        # return "\n".join(lst)

        # def __init__(self, title, note=None):
        # self.toc = {}
        # self.generateEntry(title, note)

        # def generateParents(self, tocKeyParent):
        # tocValueParent = TOCValue(tocKeyParent)
        # self.addEntry(tocKeyParent, tocValueParent)

        # def addEntry(self, tocKey, tocValue):
        # # log_dump(tocKey)
        # # log_dump(tocKey.Parent())
        # # print "TOCList-> AddEntry %s " % (tocKey)
        # parent = tocKey.Parent()
        # if parent and not parent.Hash() in self.toc:
        # # print "Adding Parent: %s " % parent.Title
        # self.generateEntry(parent.Title)

        # self.toc[tocKey.Hash()] = tocValue

        # def generateEntry(self, title, note=None):
        # tocKey = TOCKey(title)
        # tocValue = TOCValue(tocKey, note)
        # # print "TOCList -> Gen Entry %s = %s " % (title, tocKey )
        # self.addEntry(tocKey, tocValue)

        # class TOC:
        # Key = None
        # def __init__(self, name):
        # self.Key = TOCList(name)


def generateTOCTitle(title):
    return EvernoteNoteTitle.titleObjectToString(title).upper().replace(u'?', u'?').replace(u'?', u'?')