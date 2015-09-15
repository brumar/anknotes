# -*- coding: utf-8 -*-
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
    Title = None
    """:type : EvernoteNoteTitle"""
    Note = None
    """:type : EvernoteNote.EvernoteNote"""
    Outline = None
    """:type : TOCHierarchyClass"""
    Number = 1
    Children = []
    """:type : list[TOCHierarchyClass]"""
    Parent = None
    """:type : TOCHierarchyClass"""
    __isSorted__ = False

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

    @property
    def IsOutline(self):
        if not self.Note: return False
        return EVERNOTE.TAG.OUTLINE in self.Note.Tags

    def sortIfNeeded(self):
        if self.__isSorted__: return
        self.sortChildren()

    @property
    def Level(self):
        return self.Title.Level

    @property
    def ChildrenCount(self):
        return len(self.Children)

    @property
    def TitleParts(self):
        return self.Title.TitleParts

    def addNote(self, note):
        tocHierarchy = TOCHierarchyClass(note=note)
        self.addHierarchy(tocHierarchy)

    def getChildIndex(self, tocChildHierarchy):
        if not tocChildHierarchy in self.Children: return -1
        self.sortIfNeeded()
        return self.Children.index(tocChildHierarchy)

    @property
    def ListPrefix(self):
        index = self.Index
        isSingleItem = self.IsSingleItem
        if isSingleItem is 0: return ""
        if isSingleItem is 1: return "*"
        return str(index) + "."

    @property
    def IsSingleItem(self):
        index = self.Index
        if index is 0: return 0
        if index is 1 and len(self.Parent.Children) is 1:
            return 1
        return -1

    @property
    def Index(self):
        if not self.Parent: return 0
        return self.Parent.getChildIndex(self) + 1

    def addTitle(self, title):
        self.addHierarchy(TOCHierarchyClass(title))

    def addHierarchy(self, tocHierarchy):
        tocNewTitle = tocHierarchy.Title
        tocNewLevel = tocNewTitle.Level
        selfLevel = self.Title.Level
        tocTestBase = tocHierarchy.Title.FullTitle.replace(self.Title.FullTitle, '')
        if tocTestBase[:2] == ': ':
                tocTestBase = tocTestBase[2:]

        print " \nAdd Hierarchy: %-70s --> %-40s\n-------------------------------------" % (self.Title.FullTitle, tocTestBase)

        if selfLevel > tocHierarchy.Title.Level:
            print "New Title Level is Below current level"
            return False

        selfTOCTitle = self.Title.TOCTitle
        tocSelfSibling = tocNewTitle.Parents(self.Title.Level)

        if tocSelfSibling.TOCTitle != selfTOCTitle:
            print "New Title doesn't match current path"
            return False
        
        if tocNewLevel is self.Title.Level:
            if tocHierarchy.IsOutline:
                tocHierarchy.Parent = self
                self.Outline = tocHierarchy
                print "SUCCESS: Outline added"
                return True
            print "New Title Level is current level, but New Title is not Outline"
            return False


        tocNewSelfChild =  tocNewTitle.Parents(self.Title.Level+1)
        tocNewSelfChildTOCName = tocNewSelfChild.TOCName
        isDirectChild = (tocHierarchy.Level == self.Level + 1)
        if isDirectChild:
            tocNewChildNamesTitle = "N/A"
            print "New Title is a direct child of the current title"
        else:
            tocNewChildNamesTitle = tocHierarchy.Title.Names(self.Title.Level+1).FullTitle
            print "New Title is a Grandchild or deeper of the current title "

        for tocChild in self.Children:
            assert(isinstance(tocChild, TOCHierarchyClass))
            if tocChild.Title.TOCName == tocNewSelfChildTOCName:
                print "%-60s Child %-20s Match Succeeded for %s." % (self.Title.FullTitle + ':', tocChild.Title.Name + ':', tocNewChildNamesTitle)
                success = tocChild.addHierarchy(tocHierarchy)
                if success:
                    return True
                print "%-60s Child %-20s Match Succeeded for %s: However, unable to add to matched child" % (self.Title.FullTitle + ':', tocChild.Title.Name + ':', tocNewChildNamesTitle)
        print "%-60s Child %-20s Search failed for %s" % (self.Title.FullTitle + ':', tocNewSelfChild.Name, tocNewChildNamesTitle)

        newChild = tocHierarchy if isDirectChild else TOCHierarchyClass(tocNewSelfChild)
        newChild.parent = self
        if isDirectChild:
            print "%-60s Child %-20s Created Direct Child for %s." % (self.Title.FullTitle + ':', newChild.Title.Name, tocNewChildNamesTitle)
            success = True
        else:
            print "%-60s Child %-20s Created Title-Only Child for %-40ss." % (self.Title.FullTitle + ':', newChild.Title.Name, tocNewChildNamesTitle)
            success = newChild.addHierarchy(tocHierarchy)
            print "%-60s Child %-20s Created Title-Only Child for %-40s: Match %s." % (self.Title.FullTitle + ':', newChild.Title.Name, tocNewChildNamesTitle, "succeeded" if success else "failed")
        self.__isSorted__ = False
        self.Children.append(newChild)

        print "%-60s Child %-20s Appended Child for %s. Operation was an overall %s." % (self.Title.FullTitle + ':', newChild.Title.Name + ':', tocNewChildNamesTitle, "success" if success else "failure")
        return success

    def sortChildren(self):
        self.Children = sorted(self.Children, self.TOCItemSort)
        self.__isSorted__ = True

    def __strsingle__(self, fullTitle=False):
        selfTitleStr = self.Title.FullTitle
        selfNameStr = self.Title.Name
        selfLevel = self.Title.Level
        selfDepth = self.Title.Depth
        selfListPrefix = self.ListPrefix
        strr = ''
        if selfLevel == 1:
            strr += '  [%d]           ' % len(self.Children)
        else:
            if len(self.Children):
                strr += '  [%d:%2d]       ' % (selfDepth, len(self.Children))
            else:
                strr += '  [%d]          ' % selfDepth
            strr += ' ' * (selfDepth * 3)
            strr += ' %s ' % selfListPrefix

        strr += '%-60s  %s' % (selfTitleStr if fullTitle else selfNameStr, '' if self.Note else '(No Note)')
        return strr

    def __str__(self, fullTitle=True, fullChildrenTitles=False):
        self.sortIfNeeded()
        lst = [self.__strsingle__(fullTitle)]
        for child in self.Children:
            lst.append(child.__str__(fullChildrenTitles, fullChildrenTitles))
        return '\n'.join(lst)

    def GetOrderedListItem(self, title=None):
        if not title: title = self.Title.FullTitle
        selfTitleStr = title
        selfLevel = self.Title.Level
        selfDepth = self.Title.Depth
        if selfLevel == 1:
            guid = 'guid-pending'
            if self.Note: guid = self.Note.guid
            link = generate_evernote_link(guid, generateTOCTitle(selfTitleStr), 'TOC')
            if self.Outline:
                link += ' ' + generate_evernote_link(self.Outline.note.guid,
                                                     '(<span style="color: rgb(255, 255, 255);">O</span>)', 'Outline',
                                                     escape=False)
            return link
        if self.Note:
            return self.Note.generateLevelLink(selfDepth)
        else:
            return generate_evernote_span(selfTitleStr, 'Levels', selfDepth)

    def GetOrderedList(self, title=None):
        self.sortIfNeeded()
        lst = []
        header = (self.GetOrderedListItem(title))
        if self.ChildrenCount > 0:
            for child in self.Children:
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

        if self.Level is 1:
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
        selfTitleStr = self.Title.FullTitle
        selfNameStr = self.Title.Name
        # selfLevel = self.title.Level
        # selfDepth = self.title.Depth
        selfListPrefix = self.ListPrefix
        strr = "<%s:%s[%d] %s%s>" % (
            self.__class__.__name__, selfListPrefix, len(self.Children), selfTitleStr if fullTitle else selfNameStr,
            '' if self.Note else ' *')
        return strr

    def __repr__(self, fullTitle=True, fullChildrenTitles=False):
        self.sortIfNeeded()
        lst = [self.__reprsingle__(fullTitle)]
        for child in self.Children:
            lst.append(child.__repr__(fullChildrenTitles, fullChildrenTitles))
        return '\n'.join(lst)

    def __init__(self, title=None, note=None, number=1):
        """
        :type title: EvernoteNoteTitle
        :type note: EvernoteNotePrototype.EvernoteNotePrototype
        """
        assert note or title
        self.Outline = None
        if note:
            self.Note = note
            self.Title = EvernoteNoteTitle(note)
        else:
            self.Title = EvernoteNoteTitle(title)
            self.Note = None
        self.Number = number
        self.Children = []
        self.__isSorted__ = False



#
# tocTest = TOCHierarchyClass("My Root Title")
# tocTest.addTitle("My Root Title: Somebody")
# tocTest.addTitle("My Root Title: Somebody: Else")
# tocTest.addTitle("My Root Title: Someone")
# tocTest.addTitle("My Root Title: Someone: Else")
# tocTest.addTitle("My Root Title: Someone: Else: Entirely")
# tocTest.addTitle("My Root Title: Z This: HasNo: Direct Parent")
# pass