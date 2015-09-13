# -*- coding: utf-8 -*-
import re
import pprint
from HTMLParser import HTMLParser
from datetime import datetime, timedelta
import difflib
import time
import errno

from constants import *

try:  from aqt import mw
except: pass
try:    from pysqlite2 import dbapi2 as sqlite
except ImportError: from sqlite3 import dbapi2 as sqlite
try:  from aqt.qt import QIcon, QPixmap, QPushButton, QMessageBox
except: pass 
try:  from aqt.utils import tooltip
except: pass 
try: from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode, EDAMUserException, EDAMNotFoundException
except: pass 
class RateLimitErrorHandling:
    IgnoreError, ToolTipError, AlertError = range(3)  
EDAM_RATE_LIMIT_ERROR_HANDLING = RateLimitErrorHandling.ToolTipError 

def show_tooltip(text, time_out=3000,delay=None):
    if delay:
        try: return mw.progress.timer(delay, lambda: tooltip(text, time_out), False)
        except: pass 
    tooltip(text, time_out)
    
def report_tooltip(log_title, str_tip=None,delay=None):
    if not str_tip:
        str_tip = log_title
        log_title = None 
    
    show_tooltip(str_tip,delay=delay)        
    
    if log_title:
        log_title += ": "
        delimit = "-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------"
        str_tip = delimit + "<BR>%s\n" % str_tip 
        log(log_title)
    str_tip = str_tip.replace('<BR><BR>', '<BR>').replace('<BR>', '\n   - ')    
    log(str_tip, timestamp=False, replace_newline=True)    

def generateTitleParts(title):
    try:
        strTitle = re.sub(':+', ':', title)
    except:
        print type(title)
        raise 
    if strTitle[-1] == ':': strTitle = strTitle[:-1]
    if strTitle[0] == ':': strTitle = strTitle[1:]    
    partsText = strTitle.split(':')
    count = len(partsText)            
    for i in range(1, count + 1):
        txt =  partsText[i-1]
        try:
            if txt[-1] == ' ': txt = txt[:-1]
            if txt[0] == ' ': txt = txt[1:]                
        except:
            print_safe(title  + ' -- ' + '"' + txt + '"')
            raise
        partsText[i-1] = txt
    return partsText 
    
class hashabledict(dict):
    def Level(self):
        return self['Level']
    def Title(self):
        return self['Title']

    def TitleParts(self):
        return generateTitleParts(self.Title())

    def __key(self):
        return tuple((k,self[k]) for k in sorted(self))
    def __hash__(self):
        return hash(self.__key())
    def __eq__(self, other):
        return self.__key() == other.__key()
    
def get_friendly_interval_string(lastImport):
    if not lastImport: return ""
    td = (datetime.now() - datetime.strptime(lastImport, ANKNOTES.DATE_FORMAT))
    days = td.days
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 1:
        lastImportStr = "%d days" % td.days()
    else:
        hours = round(hours)
        hours_str = '' if hours == 0 else 'One Hour' if hours == 1 else '%d Hours' % hours 
        if days == 1:
            lastImportStr = "One Day%s" % ('' if hours == 0 else ', ' + hours)
        elif hours > 0:
            lastImportStr = hours_str                 
        else:
            lastImportStr = "%d:%02d min" % (minutes, seconds)    
    return lastImportStr
    
class TOCKey:
    level = 0
    Title = ""
    titleParts=None
    
    # # Parent = None
    def __str__(self):
        return "%d: %s" % (self.Level(), self.Title)
        
    def __repl__(self):
        return "<TOCKey:%d.%s>" % (self.Level(), self.Name())
    
    def TitleParts(self):
        if not self.Title: return []
        
        if not self.titleParts: self.titleParts = generateTitleParts(self.Title)
        return self.titleParts
    
    def isRoot(self):
        return self.Level() is 1
    
    def Level(self):
        if not self.level: self.level = len(self.TitleParts())
        return self.level
    
    def Depth(self):
        return self.Level() - 1
    
    def Names(self, level=-1):
        return self.Slice(level)        
    
    def Name(self, level=-1):
        slice = self.Slice(level)
        if not slice: return None 
        return slice.Title
    
    def Hash(self):
        return hashabledict({'Level': self.Level(), 'Title': self.Title, 'Parent': self.Parent()})
    
    def Root(self):
        return self.Parent(1)    
    
    def Slice(self, start=0, end=None):      
        # print "Slicing: <%s> %s ~ %d,%d" % (type(self.Title), self.Title, start, end)
        oldParts = self.TitleParts()
        # print "Slicing: %s ~ %d,%d from parts %s" % (self.Title, start, end, str(oldParts))
        if not self.Title: return None
        if not oldParts: return None
        assert start or end 
        newParts = oldParts[start:end]
        if len(newParts) == 0: 
            # print "Slice failed for %s-%s of %s" % (str(start), str(end), self.Title)
            return None 
            assert False 
        newStr = ': '.join(newParts)
        # print "Slice: Just created new title %s from %s" % (newStr , self.Title)
        return TOCKey(newStr)
    
    def Parent(self, level = -1):
        return self.Slice(None, level)
        
    def __init__(self, title):
        if hasattr(title, 'Title'): title = title.Title() if callable(title.Title) else title.Title 
        self.Title=title 
        # print "New TocKey: %s: %s" % (type(title), title)
        
def generateTOCTitle(title):
    return title.upper().replace(u'Α', u'α').replace(u'Β', u'β')
        
class TOCValue:
    Key = None 
    Note = None 
    Children = None 
    def isBlank(self):
        return not self.Note
    def isRoot(self):
        return self.Key.isRoot()
    def __init__(self, tocKey, note = None, children = None):        
        self.Key = tocKey
        self.Note = note
        if children:
            self.Children = children 
        else:
            self.Children = None

def TOCNamePriority(title):
    for index, value in enumerate(['Summary', 'Definition', 'Classification', 'Types', 'Presentation', 'Organ Involvement', 'Age of Onset', 'Si/Sx', 'Sx', 'Sign', 'MCC\'s', 'MCC', 'Inheritance', 'Incidence', 'Prognosis', 'Mechanism', 'MOA', 'Pathophysiology', 'Indications', 'Examples', 'Cause', 'Causes', 'Causative Organisms', 'Risk Factors', 'Complication', 'Complications', 'Side Effects', 'Drug S/E', 'Associated Conditions', 'A/w', 'Dx', 'Physical Exam', 'Labs', 'Hemodynamic Parameters', 'Lab Findings', 'Imaging', 'Screening Test', 'Confirmatory Test']):
        if title == value: return -1, index
    for index, value in enumerate(['Management', 'Work Up', 'Tx']):
        if title == value: return 1, index    
    return 0, 0
    
def TOCNameSort(title1, title2):
    priority1 = TOCNamePriority(title1)
    priority2 = TOCNamePriority(title2)
    #Lower value for item 1 = item 1 placed BEFORE item 2
    if priority1[0] != priority2[0]: return priority1[0] - priority2[0]
    if priority1[1] != priority2[1]: return priority1[1] - priority2[1]
    return cmp(title1, title2)
            
def TOCSort(hash1, hash2):
    lvl1 = hash1.Level()
    lvl2 = hash2.Level()
    names1 = hash1.TitleParts()
    names2 = hash2.TitleParts()
    for i in range(0, min(lvl1,lvl2)):
        name1= names1[i]
        name2= names2[i]
        if name1 != name2: return TOCNameSort(name1, name2)
    #Lower value for item 1 = item 1 placed BEFORE item 2
    return lvl1 - lvl2           

class TOCHierarchicalItem:
    title = ""
    note = ""
    children = []    
           
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
        lvl1 = tocHierarchy1.Level()
        lvl2 = tocHierarchy2.Level()
        names1 = tocHierarchy1.TitleParts()
        names2 = tocHierarchy2.TitleParts()
        for i in range(0, min(lvl1,lvl2)):
            name1= names1[i]
            name2= names2[i]
            if name1 != name2: return TOCNameSort(name1, name2)
        #Lower value for item 1 = item 1 placed BEFORE item 2
        return lvl1 - lvl2    
    
    def isOutline(self):
        if not self.note: return False 
        return EVERNOTE.TAG.OUTLINE in self.note.tags
    
    def sortIfNeeded(self):
        if self.isSorted: return 
        self.sortChildren()
        
    def Level(self): 
        return self.title.Level()
        
    def ChildrenCount(self):
        return len(self.children)
        
    def TitleParts(self):
        return self.title.TitleParts()
    
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
        tocNewLevel = tocNewTitle.Level()
        selfLevel = self.title.Level()    
        selfTitleStr = self.title.Title
        tocTitleStr = tocNewTitle.Title
        
        if selfLevel is 1 and tocNewLevel is 1:
            log_dump(self.title.Title)
            log_dump(parentTitle.Title)      
            log_dump(tocHierarchy.note.tags)      
            assert tocHierarchy.isOutline()
            tocHierarchy.parent = self
            self.outline = tocHierarchy
            return True        
        
        parentTitle = tocNewTitle.Parent()
        parentTitleStr = parentTitle.Title
        parentLevel = parentTitle.Level()             
        
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
                childTitleName = child.title.Name()
                if child.title.Name() == baseTitleName:
                    success = child.addHierarchy(tocHierarchy)        
                    if not success: print "Failed searching %s for child %s to add %s " % (selfTitleStr, baseTitle.Name(), baseTitleChildrenStr)
                    return success
            newChild = TOCHierarchyClass(baseTitleStr)
            newChild.addHierarchy(tocHierarchy)
            newChild.parent = self 
            self.isSorted = False 
            self.children.append(newChild)     
            return True 
        else:
            print "baseTitleParentTitle Fail:  %s for child %s to add %s " % (selfTitleStr, baseTitle.Name(), baseTitleChildrenStr)    
        
        print "Total Fail:  %s for child %s to add %s " % (selfTitleStr, baseTitle.Name(), baseTitleChildrenStr)    
        return False     
    
    def sortChildren(self):    
        self.children = sorted(self.children, self.TOCItemSort)  
        self.isSorted = True 
    
    def __strsingle__(self, fullTitle=False):
        selfTitleStr = self.title.Title
        selfNameStr = self.title.Name()
        selfLevel = self.title.Level() 
        selfDepth = self.title.Depth() 
        selfListPrefix = self.getListPrefix()
        strr = ''        
        if selfLevel == 1:
            strr += '  [%d]           ' % len(self.children)
        else:
            if len(self.children):
                strr += '  [%d:%2d]       ' % (selfDepth, len(self.children))
            else:  
                strr += '  [%d]          ' % (selfDepth)
            strr += ' '*(selfDepth*3)
            strr += ' %s ' % selfListPrefix
        
        strr += '%-60s  %s' % ( selfTitleStr if fullTitle else selfNameStr, '' if self.note else '(No Note)' )
        return strr
        
    def __str__(self, fullTitle=True, fullChildrenTitles=False):
        self.sortIfNeeded()
        lst = []
        lst.append(self.__strsingle__(fullTitle))        
        for child in self.children:
            lst.append(child.__str__(fullChildrenTitles, fullChildrenTitles))
        return '\n'.join(lst)
    
    
    
    def GetOrderedListItem(self, title=None):
        if not title: title = self.title.Title
        selfTitleStr = title 
        selfLevel = self.title.Level() 
        selfDepth = self.title.Depth() 
        if selfLevel == 1:
            guid = 'guid-pending'
            if self.note: guid = self.note.guid 
            link = generate_evernote_link(guid, generateTOCTitle(selfTitleStr), 'TOC') 
            if self.outline:
                link += ' ' + generate_evernote_link(self.outline.note.guid, '(<span style="color: rgb(255, 255, 255);">O</span>)', 'Outline', escape_text=False)
            return link 
        if self.note: return self.note.generateLevelLink(selfDepth)
        else: return generate_evernote_span(selfTitleStr, 'Levels', selfDepth)
        
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
        selfTitleStr = self.title.Title
        selfNameStr = self.title.Name()
        selfLevel = self.title.Level() 
        selfDepth = self.title.Depth() 
        selfListPrefix = self.getListPrefix()
        strr = "<%s:%s[%d] %s%s>" % (self.__class__.__name__, selfListPrefix, len(self.children) , selfTitleStr if fullTitle else selfNameStr, '' if self.note else ' *')
        return strr        
        
    def __repr__(self, fullTitle=True, fullChildrenTitles=False):
        self.sortIfNeeded()
        lst = []
        lst.append(self.__reprsingle__(fullTitle))        
        for child in self.children:
            lst.append(child.__repr__(fullChildrenTitles, fullChildrenTitles))
        return '\n'.join(lst)
    
    def __init__(self, title=None, note=None, number=1):
        assert note or title 
        self.outline = None 
        if note:
            self.note = note 
            self.title = TOCKey(note.title.title)
        else:
            self.title = TOCKey(title)
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

class UpdateExistingNotes:
    IgnoreExistingNotes, UpdateNotesInPlace, DeleteAndReAddNotes = range(3)
    
class EvernoteQueryLocationType:
    RelativeDay, RelativeWeek, RelativeMonth, RelativeYear, AbsoluteDate, AbsoluteDateTime = range(6)
    
    
ankNotesDBInstance = None
dbLocal = False     

def ankDBSetLocal():
    global dbLocal
    dbLocal = True

def ankDB():
    global ankNotesDBInstance, dbLocal
    if not ankNotesDBInstance: 
        if dbLocal: ankNotesDBInstance = ank_DB(os.path.join(PATH, '..\\..\\Evernote\\collection.anki2'))        
        else:  ankNotesDBInstance = ank_DB()        
    return ankNotesDBInstance

def showInfo(message, title="Anknotes: Evernote Importer for Anki", textFormat = 0):
    global imgEvernoteWebMsgBox, icoEvernoteArtcore
    msgDefaultButton = QPushButton(icoEvernoteArtcore, "Okay!", mw) 
    
    if not isinstance(message, str) and not isinstance(message, unicode):
        message = str(message)
    
    messageBox = QMessageBox()       
    messageBox.addButton(msgDefaultButton, QMessageBox.AcceptRole)
    messageBox.setDefaultButton(msgDefaultButton)
    messageBox.setIconPixmap(imgEvernoteWebMsgBox)
    messageBox.setTextFormat(textFormat)
    messageBox.setText(message)
    messageBox.setWindowTitle(title)
    messageBox.exec_()


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def str_safe(strr, prefix=''):
    try: strr= str((prefix + strr.__repr__()))
    except: strr= str((prefix + strr.__repr__().encode('utf8', 'replace')))
    return strr
    
def print_safe(strr, prefix=''):
    print str_safe(strr, prefix)            
        
def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()
    
def strip_tags_and_new_lines(html):
    return strip_tags(html).replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

class EvernoteAccountIDs:
    uid = '0'
    shard = 's100'
    valid = False 
    def __init__(self, uid=None,shard=None):
        self.valid = False 
        if uid and shard:
            if self.update(uid, shard): return 
        try:
            self.uid =  mw.col.conf.get(SETTINGS.EVERNOTE_ACCOUNT_UID, EVERNOTE_ACCOUNT_UID_DEFAULT_VALUE)
            self.shard = mw.col.conf.get(SETTINGS.EVERNOTE_ACCOUNT_SHARD, EVERNOTE_ACCOUNT_SHARD_DEFAULT_VALUE)
        except:
            self.uid = SETTINGS.EVERNOTE_ACCOUNT_UID_DEFAULT_VALUE
            self.shard = SETTINGS.EVERNOTE_ACCOUNT_SHARD_DEFAULT_VALUE
            return 
        
    def update(self, uid, shard):        
        if not uid or not shard: return False 
        if uid == '0' or shard == 's100': return False 
        try:
            mw.col.conf[SETTINGS.EVERNOTE_ACCOUNT_UID] = uid
            mw.col.conf[SETTINGS.EVERNOTE_ACCOUNT_SHARD] = shard
        except:
            return False 
        self.uid = uid 
        self.shard = shard 
        self.valid = True 
    
enAccountIDs = None     
  
def get_evernote_account_ids():
    global enAccountIDs 
    if not enAccountIDs:
        enAccountIDs = EvernoteAccountIDs()
    return enAccountIDs

def get_tag_names_to_import(tagNames, evernoteTags=None, evernoteTagsToDelete=None):
    if not evernoteTags:
        evernoteTags = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_TAGS, SETTINGS.EVERNOTE_QUERY_TAGS_DEFAULT_VALUE).split(",") if mw.col.conf.get(SETTINGS.DELETE_EVERNOTE_TAGS_TO_IMPORT, True) else []
    if not evernoteTagsToDelete:
        evernoteTagsToDelete = mw.col.conf.get(SETTINGS.EVERNOTE_TAGS_TO_DELETE, "").split(",")                  
    if isinstance(tagNames, dict):
        return {k: v for k, v in tagNames.items() if v not in evernoteTags and v not in evernoteTagsToDelete}           
    return sorted([v for v in tagNames if v not in evernoteTags and v not in evernoteTagsToDelete], key=lambda s: s.lower())
    
    
def find_evernote_links_as_guids(content):
    return [x.group('guid') for x in find_evernote_links(content)]
    
def find_evernote_links(content):
    # .NET regex saved to regex.txt as 'Finding Evernote Links'
    
    regex_str = r'<a href="(?P<URL>evernote:///?view/(?P<uid>[\d]+?)/(?P<shard>s\d+)/(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/(?P=guid)/?)"(?: shape="rect")?(?: style="[^\"].+?")?(?: shape="rect")?>(?P<Title>.+?)</a>'
    ids = get_evernote_account_ids()
    if not ids.valid:
        match = re.search(regex_str, content)
        if match:
            ids.update(match.group('uid'), match.group('shard'))
    return re.finditer(regex_str, content)        
    
def escape_text(title):
    repl = [u'&', u'&nbsp;', u'>', u'&gt;', u'<', u'&lt;']
    for i in range(0, len(repl), 2):
        title = title.replace(repl[i], repl[i+1])
    return title
    
def escape_text_sql(title):
    return title.replace("'", "''")
    
def diffify(content):
    for tag in ['div', 'ol', 'ul', 'li']:
        content = content.replace("<"+tag, "\n<"+tag).replace("</%s>" % tag, "</%s>\n" % tag)
    content = re.sub(r'[\r\n]+', '\n', content)
    return content.splitlines()
    
def generate_diff(value_original, value):
    try: return '\n'.join(list(difflib.unified_diff(diffify(value_original), diffify(value), lineterm='')))      
    except: pass
    try: return '\n'.join(list(difflib.unified_diff(diffify(value_original.decode('utf-8')), diffify(value), lineterm='')))      
    except: pass
    try: return '\n'.join(list(difflib.unified_diff(diffify(value_original), diffify(value.decode('utf-8')), lineterm='')))      
    except: pass
    try: return '\n'.join(list(difflib.unified_diff(diffify(value_original.decode('utf-8')), diffify(value.decode('utf-8')), lineterm='')))      
    except: raise
    
def generate_evernote_url(guid):
    ids = get_evernote_account_ids()
    return u'evernote:///view/%s/%s/%s/%s/' % (ids.uid, ids.shard, guid, guid)
    
def generate_evernote_link_by_type(guid, title=None, type=None, value=None, escape=True):
    url = generate_evernote_url(guid)
    if not title: title = get_evernote_title_from_guid(guid)
    if escape: title = escape_text(title)
    style = generate_evernote_html_element_style_attribute(type, value)
    html = u"""<a href='%s'><span style='%s'>%s</span></a>""" % (url, style, title)
    # print html
    return html       
    
def generate_evernote_link(guid, title=None, value=None, escape=True):
    return generate_evernote_link_by_type(guid, title, 'Links', value)   
    
def generate_evernote_link_by_level(guid, title=None, value=None, escape=True):
    return generate_evernote_link_by_type(guid, title, 'Levels', value)   

def generate_evernote_html_element_style_attribute(type, value, bold=True, group=None):
    global evernote_link_colors
    colors = None 
    if type in evernote_link_colors:
        color_types = evernote_link_colors[type]
        if type is 'Levels':
            if not value: value = 1
            if not group: group = 'OL' if isinstance(value, int) else 'Modifiers'
            if not value in color_types[group]: group = 'Headers'
            if value in color_types[group]:
                colors = color_types[group][value]
        elif type is 'Links':
            if not value: value='Default'
            if value in color_types:
                colors = color_types[value]
    if not colors:
        colors = evernote_link_colors['Default']
    colorDefault = colors
    if not isinstance(colorDefault, str) and not isinstance(colorDefault, unicode):
        colorDefault = colorDefault['Default']
    if not colorDefault[-1] is ';': colorDefault += ';'
    style = 'color: ' + colorDefault
    if bold: style += 'font-weight:bold;'
    return style 

def generate_evernote_span(title=None, type=None, value=None, guid=None, bold=True, escape=True):
    assert title or guid 
    if not title: title = get_evernote_title_from_guid(guid)
    if escape: title = escape_text(title)
    style = generate_evernote_html_element_style_attribute(type, value, bold)
    html = u"<span style='%s'>%s</span>" % (style, title)
    return html         
    
def get_evernote_title_from_guid(guid):
    return ankDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, guid))
    
def obj2log_simple(content):
    if not isinstance(content, str) and not isinstance(content, unicode):
        content = str(content)     
    return content 
    
def get_anki_deck_id_from_note_id(nid):
    return long(ankDB().scalar("SELECT did FROM cards WHERE nid = ?", nid))
    
def log(content='', filename='', prefix='', clear=False, timestamp=True, extension='log', blank=False, replace_newline=None):    
    if blank: 
        filename = content
        content = ''
        timestamp=False
    else:
        content = obj2log_simple(content)
        if len(content) == 0: content = '{EMPTY STRING}'        
        if content[0] == "!":
            content = content[1:]
            prefix = '\n'        
    if not filename: 
        filename = ANKNOTES.LOG_BASE_NAME + '.' + extension
    else: 
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = ANKNOTES.LOG_BASE_NAME + '-%s.%s' % (filename        , extension)
    try: content = content.encode('utf-8')
    except Exception: pass 
    if timestamp or replace_newline is True:
        content = content.replace('\r', '\r                              ').replace('\n', '\n                              ')    
    if timestamp:         
        st = '[%s]: ' % datetime.now().strftime(ANKNOTES.DATE_FORMAT)
    else: 
        st = ''
    full_path = os.path.join(ANKNOTES.FOLDER_LOGS, filename)    
    if not os.path.exists(os.path.dirname(full_path)): 
        os.mkdir(os.path.dirname(full_path))
    with open(full_path , 'w+' if clear else 'a+') as fileLog:
        print>>fileLog, prefix + ' ' + st + content 
    
def log_sql(value):
    log(value, 'sql')

def log_error(value):
    log(value, '+error')    
    
def print_dump(obj):
    content = pprint.pformat(obj, indent=4, width=80)  
    content = content.replace(', ', ', \n ')
    content = content.replace('\r', '\r                              ').replace('\n', '\n                              ')
    if isinstance(content , str):
        content = unicode(content , 'utf-8')       
    print content 
    
def log_dump(obj, title="Object", filename='', clear=False, timestamp=True):
    if not filename: filename = ANKNOTES.LOG_BASE_NAME + '-dump.log'
    else: 
        if filename[0] is '+':
            filename = filename[1:]
            summary = " ** CROSS-POST TO %s: " % filename + content
            if len(summary) > 200: summary = summary[:200]
            log(summary)
        filename = ANKNOTES.LOG_BASE_NAME + '-dump-%s.log' % filename
    content = pprint.pformat(obj, indent=4, width=80)
    try:
        content=content.encode('ascii', 'ignore') 
    except Exception:
        pass
    st = ''
    if timestamp:
        st = datetime.now().strftime(ANKNOTES.DATE_FORMAT)
        st = '[%s]: ' % st
    
    if title[0] == '-':
        prefix = " **** Dumping %s" % title[1:]
    else:        
        prefix = " **** Dumping %s" % title
        log(prefix)
    prefix += '\r\n' 
    content = prefix + content.replace(', ', ', \n ')
    content = content.replace("': {", "': {\n ")
    content = content.replace('\r', '\r                              ').replace('\n', '\n                              ')
    full_path = os.path.join(ANKNOTES.FOLDER_LOGS, filename)
    if isinstance(content , str):
        content = unicode(content , 'utf-8')          
    if not os.path.exists(os.path.dirname(full_path)): 
        os.mkdir(os.path.dirname(full_path))
    with open(full_path, 'w+' if clear else 'a+') as fileLog:
        try: 
            print>>fileLog, (u'\n %s%s' % (st, content))
            return
        except: pass
        try: 
            print>>fileLog, (u'\n <1> %s%s' % (st, content.decode('utf-8')))
            return
        except: pass
        try: 
            print>>fileLog, (u'\n <2> %s%s' % (st, content.encode('utf-8')))
        except: pass 
        try: 
            print>>fileLog, ('\n <3> %s%s' % (st, content.decode('utf-8')))
            return
        except: pass
        try: 
            print>>fileLog, ('\n <4> %s%s' % (st, content.encode('utf-8')))
            return
        except: pass 
        try:
            print>>fileLog, (u'\n %s%s' % (st, "Error printing content: " + str_safe(content)))
            return 
        except: pass
        print>>fileLog, (u'\n %s%s' % (st, "Error printing content: " + content[:10]))

def log_api(method, content=''):
    if content: content = ': ' + content
    log(" API_CALL [%3d]: %10s%s" % (get_api_call_count(), method, content), 'api')        
        
def get_api_call_count():
    api_log = file( os.path.join(ANKNOTES.FOLDER_LOGS, ANKNOTES.LOG_BASE_NAME + '-api.log') , 'r').read().splitlines()
    count = 1
    for i in range(len(api_log), 0, -1):
        call = api_log[i-1]
        if not "API_CALL" in call: 
            continue 
        ts = call.split(': ')[0][2:-1]
        td = datetime.now() - datetime.strptime(ts, ANKNOTES.DATE_FORMAT)            
        if (td < timedelta(hours=1)):
            count += 1 
        else:
            return count 
    return count             
            
def get_dict_from_list(list, keys_to_ignore=list()):
    dict = {}
    for key, value in list: 
        if not key in keys_to_ignore: dict[key] = value  
    return dict 
    
def get_evernote_guid_from_anki_fields(fields):        
    if not FIELDS.EVERNOTE_GUID in fields: return None
    return fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')        

def get_all_local_db_guids():
        return [x[0] for x in ankDB().all("SELECT guid FROM %s WHERE 1" % TABLES.EVERNOTE.NOTES)]
    
class ank_DB(object):
    def __init__(self, path = None, text=None, timeout=0):
        encpath = path
        if isinstance(encpath, unicode):
            encpath = path.encode("utf-8")
        if path:
            self._db = sqlite.connect(encpath, timeout=timeout)
            self._db.row_factory = sqlite.Row
            if text:
                self._db.text_factory = text
            self._path = path
        else:
            self._db = mw.col.db._db
            self._path = mw.col.db._path
            self._db.row_factory = sqlite.Row
        self.echo = os.environ.get("DBECHO")
        self.mod = False

    def execute(self, sql, *a, **ka):
        s = sql.strip().lower()
        # mark modified?
        for stmt in "insert", "update", "delete":
            if s.startswith(stmt):
                self.mod = True
        t = time.time()
        if ka:
            # execute("...where id = :id", id=5)
            res = self._db.execute(sql, ka)
        elif a:
            # execute("...where id = ?", 5)
            res = self._db.execute(sql, a)
        else:
            res = self._db.execute(sql)
        if self.echo:
            #print a, ka
            print sql, "%0.3fms" % ((time.time() - t)*1000)
            if self.echo == "2":
                print a, ka
        return res

    def executemany(self, sql, l):
        self.mod = True
        t = time.time()
        self._db.executemany(sql, l)
        if self.echo:
            print sql, "%0.3fms" % ((time.time() - t)*1000)
            if self.echo == "2":
                print l

    def commit(self):
        t = time.time()
        self._db.commit()
        if self.echo:
            print "commit %0.3fms" % ((time.time() - t)*1000)

    def executescript(self, sql):
        self.mod = True
        if self.echo:
            print sql
        self._db.executescript(sql)

    def rollback(self):
        self._db.rollback()

    def scalar(self, *a, **kw):
        res = self.execute(*a, **kw).fetchone()
        if res:
            return res[0]
        return None

    def all(self, *a, **kw):
        return self.execute(*a, **kw).fetchall()

    def first(self, *a, **kw):
        c = self.execute(*a, **kw)
        res = c.fetchone()
        c.close()
        return res

    def list(self, *a, **kw):
        return [x[0] for x in self.execute(*a, **kw)]

    def close(self):
        self._db.close()

    def set_progress_handler(self, *args):
        self._db.set_progress_handler(*args)

    def __enter__(self):
        self._db.execute("begin")
        return self

    def __exit__(self, exc_type, *args):
        self._db.close()

    def totalChanges(self):
        return self._db.total_changes

    def interrupt(self):
        self._db.interrupt()
        
    def InitTags(self, force = False):
        if_exists = " IF NOT EXISTS" if not force else ""
        self.execute("""CREATE TABLE %s `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `parentGuid` TEXT, `updateSequenceNum` INTEGER NOT NULL, PRIMARY KEY(guid) );""" % (if_exists,TABLES.EVERNOTE.TAGS)) 
        
    def InitNotebooks(self, force = False):
        if_exists = " IF NOT EXISTS" if not force else ""
        self.execute("""CREATE TABLE %s `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `serviceUpdated` INTEGER NOT NULL, `stack` TEXT, PRIMARY KEY(guid) );""" % (if_exists, TABLES.EVERNOTE.NOTEBOOKS))
        
    def Init(self):
        self.execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL, PRIMARY KEY(guid) );""" % TABLES.EVERNOTE.NOTES)
        self.execute("""CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL)""" % TABLES.EVERNOTE.NOTES_HISTORY)
        self.execute( """CREATE TABLE IF NOT EXISTS `%s` ( `id` INTEGER, `source_evernote_guid` TEXT NOT NULL, `number` INTEGER NOT NULL DEFAULT 100, `uid` INTEGER NOT NULL DEFAULT -1, `shard` TEXT NOT NULL DEFAULT -1, `target_evernote_guid` TEXT NOT NULL, `html` TEXT NOT NULL, `title` TEXT NOT NULL, `from_toc` INTEGER DEFAULT 0, `is_toc` INTEGER DEFAULT 0, `is_outline` INTEGER DEFAULT 0, PRIMARY KEY(id) );""" % TABLES.SEE_ALSO) 
        self.execute( """CREATE TABLE IF NOT EXISTS `%s` ( 	`root_title`	TEXT NOT NULL UNIQUE, 	`contents`	TEXT NOT NULL, 	`tagNames`	TEXT NOT NULL, 	`notebookGuid`	TEXT NOT NULL, 	PRIMARY KEY(root_title) );""" % TABLES.EVERNOTE.AUTO_TOC) 
        self.InitTags()
        self.InitNotebooks()        
        
def HandleSocketError(e, strError):
    errorcode = e[0]
    if errorcode==errno.ECONNREFUSED:
        strError = "Error: Connection was refused while %s\r\n" % strError
        "Please retry your request a few minutes"
        log_prefix = 'ECONNREFUSED'
    elif errorcode==10060:
        strError = "Error: Connection timed out while %s\r\n" % strError
        "Please retry your request a few minutes"
        log_prefix = 'ETIMEDOUT'    
    else: return False
    log_error( " SocketError.%s:  "  % log_prefix + strError)    
    log( " SocketError.%s:  "  % log_prefix + strError, 'api')         
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
        show_tooltip(strError)
    return True

latestEDAMRateLimit = 0
    
def HandleEDAMRateLimitError(e, strError):
    global latestEDAMRateLimit
    if not e.errorCode is EDAMErrorCode.RATE_LIMIT_REACHED:
        return False
    latestEDAMRateLimit = e.rateLimitDuration
    m, s = divmod(e.rateLimitDuration, 60)
    strError = "Error: Rate limit has been reached while %s\r\n" % strError
    strError += "Please retry your request in {} min".format("%d:%02d" %(m, s))
    log_strError = " EDAMErrorCode.RATE_LIMIT_REACHED:  " + strError.replace('\r\n', '\n')
    log_error(log_strError)    
    log(log_strError, 'api')    
    if EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.AlertError:
        showInfo(strError)
    elif EDAM_RATE_LIMIT_ERROR_HANDLING is RateLimitErrorHandling.ToolTipError:
        show_tooltip(strError)
    return True

_regex_see_also = None 
def update_regex():
    global _regex_see_also    
    regex_str = file( os.path.join(ANKNOTES.FOLDER_ANCILLARY, 'regex-see_also.txt'), 'r').read()    
    regex_str = regex_str.replace('(?<', '(?P<')
    _regex_see_also = re.compile(regex_str, re.UNICODE | re.VERBOSE | re.DOTALL)

def regex_see_also():
    global _regex_see_also
    if not _regex_see_also: update_regex()
    return _regex_see_also
    
try:
    icoEvernoteWeb = QIcon(ANKNOTES.ICON_EVERNOTE_WEB)
    icoEvernoteArtcore = QIcon(ANKNOTES.ICON_EVERNOTE_ARTCORE)
    imgEvernoteWeb = QPixmap(ANKNOTES.IMAGE_EVERNOTE_WEB, "PNG")
    imgEvernoteWebMsgBox = imgEvernoteWeb.scaledToWidth(64)                
except: pass 

 
evernote_link_colors = {
 'Levels': {
             'OL':   {
                    1: {
						'Default': 'rgb(106, 0, 129);',
						'Hover': 'rgb(168, 0, 204);'
						},
                    2: {
						'Default': 'rgb(235, 0, 115);',
						'Hover': 'rgb(255, 94, 174);'
						},
                    3: {
						'Default': 'rgb(186, 0, 255);',
						'Hover': 'rgb(213, 100, 255);'
						},
                    4: {
						'Default': 'rgb(129, 182, 255);',
						'Hover': 'rgb(36, 130, 255);'
						},
                    5: {
						'Default': 'rgb(232, 153, 220);',
						'Hover': 'rgb(142, 32, 125);'
						},
                    6: {
						'Default': 'rgb(201, 213, 172);',
						'Hover': 'rgb(130, 153, 77);'
						},
                    7: {
						'Default': 'rgb(231, 179, 154);',
						'Hover': 'rgb(215, 129, 87);'
						},
                    8: {
						'Default': 'rgb(249, 136, 198);',
						'Hover': 'rgb(215, 11, 123);'
						}
              },
              'Headers': {
                    'Auto TOC': 'rgb(11, 59, 225);'
              },
              'Modifiers': {
                    'Orange': 'rgb(222, 87, 0);',
                    'Orange (Light)': 'rgb(250, 122, 0);',
                    'Dark Red/Pink': 'rgb(164, 15, 45);',			
                    'Pink Alternative LVL1:': 'rgb(188, 0, 88);'
               }
            },
  'Titles': {
     'Field Title Prompt': 'rgb(169, 0, 48);'
    },
  'Links': {
    'See Also': {
        'Default': 'rgb(45, 79, 201);',
        'Hover': 'rgb(108, 132, 217);'       
    },
    'TOC': {
		'Default': 'rgb(173, 0, 0);',
		'Hover': 'rgb(196, 71, 71);'       
    },
    'Outline': {
        'Default': 'rgb(105, 170, 53);',
        'Hover': 'rgb(135, 187, 93);'        
    },
    'AnkNotes': {
        'Default': 'rgb(30, 155, 67);',
        'Hover': 'rgb(107, 226, 143);'     
    }
  }
}
 
evernote_link_colors['Default'] = evernote_link_colors['Links']['Outline']
evernote_link_colors['Links']['Default'] = evernote_link_colors['Default']