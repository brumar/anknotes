import copy
from anknotes.shared import *
from anknotes.toc import generateTitleParts
from anknotes.enums import *


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
        if hasattr(self.Note, 'guid'):
            guid = self.Note.guid
        else:
            guid = "N/A"
            log("No guid for Note in NoteTitle.__repr__")
            log(self.Note)
        return u"<%s: %s: '%s'>" % (self.__class__.__name__, guid, self.title)

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
        self.title = None
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
        print "Done init title, self.title = %s " % self.title

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
            return part.offset(self.Count())
        except:
            pass
        # try: return part.id()
        # except: pass
        # try: return part.value()
        # except: pass
        print_safe("Fail Tuple - %s %s " % (part, part.offset(self.Count())))

    def offset_as_scalar(self, part):
        o = part
        if not isinstance(o, int):
            try:
                oss = part.offset(self.Count())
                if oss[0] == oss[1]:
                    o = oss[0]
                else:
                    print "Unexpected range tuple for level offset for offset_as_scalar. Offset: %s " % str(oss)
                    raise
            except:
                print_safe("Fail Scalar - %s %s" % (part, part.offset(self.Count())))
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

    def __str__(self):
        if self.title is None: return ""
        return self.title

    def Breakdown(self):
        output = 'Full:   ' + self.full
        if self.isRoot(): return output
        output += '\n Root:   ' + self.Root()
        output += '\n Base:   ' + self.base
        # if self.isLevel(TitleSectionBase): return output
        if self.isAboveLevel(3):
            output += '\n  Parent: ' + self.Parent()
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
        if self.isRoot(): return self.Full()
        return self.Level(self.Part.Root)

    def Base(self):
        if self.isRoot(): return None
        return self.Level(self.Part.Base)

    def Name(self):
        return self.Level(self.Part.Name)
        ################### END CLASS Title ################