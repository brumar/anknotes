### Anknotes Shared Imports
from anknotes.shared import *



class EvernoteNoteTitle:
    level = 0
    __title__ = ""
    """:type: str"""
    __titleParts__ = None

    # # Parent = None
    # def __str__(self):
    #     return "%d: %s" % (self.Level(), self.Title)

    def __repr__(self):
        return "<%s:%d.%s>" % (self.__class__.__name__, self.Level, self.Name())

    @property
    def TitleParts(self):
        if not self.FullTitle: return []
        if not self.__titleParts__: self.__titleParts__ = generateTitleParts(self.FullTitle)
        return self.__titleParts__

    @property
    def Level(self):
        """
        :rtype: int
        :return: Current Level with 1 being the Root Title
        """
        if not self.level: self.level = len(self.TitleParts)
        return self.level

    @property
    def Depth(self):
        return self.Level - 1

    def Names(self, level=-1):
        return self.Slice(level)

    def Name(self, level=-1):
        mySlice = self.Slice(level)
        if not mySlice: return None
        return mySlice.FullTitle

    @property
    def Root(self):
        return self.Parent(1)

    def Base(self, level=None):
        return self.Slice(1, level)

    def Slice(self, start=0, end=None):
        # print "Slicing: <%s> %s ~ %d,%d" % (type(self.Title), self.Title, start, end)
        oldParts = self.TitleParts
        # print "Slicing: %s ~ %d,%d from parts %s" % (self.Title, start, end, str(oldParts))
        if not self.FullTitle: return None
        if not oldParts: return None
        assert start or end
        newParts = oldParts[start:end]
        if len(newParts) == 0:
            # print "Slice failed for %s-%s of %s" % (str(start), str(end), self.Title)
            return None
            assert False
        newStr = ': '.join(newParts)
        # print "Slice: Just created new title %s from %s" % (newStr , self.Title)
        return EvernoteNoteTitle(newStr)

    def Parent(self, level=-1):
        # noinspection PyTypeChecker
        return self.Slice(None, level)

    def isAboveLevel(self, level_check):
        return self.Level > level_check

    def isBelowLevel(self, level_check):
        return self.Level < level_check

    def isLevel(self, level_check):
        return self.Level == level_check

    @property
    def isChild(self):
        return self.isAboveLevel(1)

    @property
    def isRoot(self):
        return self.isLevel(1)

    @staticmethod
    def titleObjectToString(title):
        """
        :param title: Title in string, unicode, dict, sqlite, TOCKey or NoteTitle formats. Note objects are also parseable
        :type title: str | unicode | dict[str,str] | sqlite.Row | EvernoteNoteTitle
        :return: string Title
        :rtype: str
        """
        if isinstance(title, str) or isinstance((title, unicode)):
            return title
        if hasattr(title, 'FullTitle'): title = title.FullTitle() if callable(title.FullTitle) else title.FullTitle
        elif hasattr(title, 'Title'): title = title.Title() if callable(title.Title) else title.Title
        elif hasattr(title, 'title'): title = title.title() if callable(title.title) else title.title
        else:
            try:
                if 'title' in title: title = title['title']
                elif 'Title' in title: title = title['Title']
            except: return ""
        return EvernoteNoteTitle.titleObjectToString(title)

    @property
    def FullTitle(self):
        """:rtype: str"""
        return self.__title__

    def __init__(self, title):
        self.__title__ = self.titleObjectToString(title)



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
        txt = partsText[i - 1]
        try:
            if txt[-1] == ' ': txt = txt[:-1]
            if txt[0] == ' ': txt = txt[1:]
        except:
            print_safe(title + ' -- ' + '"' + txt + '"')
            raise
        partsText[i - 1] = txt
    return partsText

