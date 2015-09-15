### Anknotes Shared Imports
from anknotes.shared import *

def generateTOCTitle(title):
    title = EvernoteNoteTitle.titleObjectToString(title).upper()
    for chr in u'?????':
        title = title.replace(chr.upper(), chr)
    return title

class EvernoteNoteTitle:
    level = 0
    __title__ = ""
    """:type: str"""
    __titleParts__ = None
    """:type: list[str]"""

    # # Parent = None
    # def __str__(self):
    #     return "%d: %s" % (self.Level(), self.Title)

    def __repr__(self):
        return "<%s:%s>" % (self.__class__.__name__, self.FullTitle)

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

    def Parts(self, level=-1):
        return self.Slice(level)    
            
    def Part(self, level=-1):
        mySlice = self.Parts(level)
        if not mySlice: return None
        return mySlice.Root
        
    def BaseParts(self, level=None):
        return self.Slice(1, level)

    def Parents(self, level=-1):
        # noinspection PyTypeChecker
        return self.Slice(None, level)
    
    def Names(self, level=-1):
        return self.Parts(level)
    
    @property
    def TOCTitle(self):
        return generateTOCTitle(self.FullTitle)

    @property
    def TOCName(self):
        return generateTOCTitle(self.Name)

    @property
    def TOCRootTitle(self):
        return generateTOCTitle(self.Root)

    @property
    def Name(self):
        return self.Part()

    @property
    def Root(self):
        return self.Parents(1).FullTitle

    @property
    def Base(self):
        return self.BaseParts()

    def Slice(self, start=0, end=None):
        # print "Slicing: <%s> %s ~ %d,%d" % (type(self.Title), self.Title, start, end)
        oldParts = self.TitleParts
        # print "Slicing: %s ~ %d,%d from parts %s" % (self.Title, start, end, str(oldParts))
        assert self.FullTitle and oldParts 
        if start is None and end is None:
            print "Slicing: %s ~ %d,%d from parts %s" % (self.FullTitle, start, end, str(oldParts))
        assert start is not None or end is not None
        newParts = oldParts[start:end]
        if len(newParts) == 0:
            log_error("Slice failed for %s-%s of %s" % (str(start), str(end), self.FullTitle))
            # return None
        assert len(newParts) > 0
        newStr = ': '.join(newParts)
        # print "Slice: Just created new title %s from %s" % (newStr , self.Title)
        return EvernoteNoteTitle(newStr)

    @property
    def Parent(self):
        return self.Parents()

    def IsAboveLevel(self, level_check):
        return self.Level > level_check

    def IsBelowLevel(self, level_check):
        return self.Level < level_check

    def IsLevel(self, level_check):
        return self.Level == level_check

    @property
    def IsChild(self):
        return self.IsAboveLevel(1)

    @property
    def IsRoot(self):
        return self.IsLevel(1)

    @staticmethod
    def titleObjectToString(title):
        """
        :param title: Title in string, unicode, dict, sqlite, TOCKey or NoteTitle formats. Note objects are also parseable
        :type title: None | str | unicode | dict[str,str] | sqlite.Row | EvernoteNoteTitle
        :return: string Title
        :rtype: str
        """
        if title is None:
            #log('titleObjectToString: NoneType', 'tOTS')
            return ""
        if isinstance(title, str) or isinstance(title, unicode):
            #log('titleObjectToString: str/unicode', 'tOTS')
            return title
        if hasattr(title, 'FullTitle'): 
            #log('titleObjectToString: FullTitle', 'tOTS')
            title = title.FullTitle() if callable(title.FullTitle) else title.FullTitle
        elif hasattr(title, 'Title'): 
            #log('titleObjectToString: Title', 'tOTS')
            title = title.Title() if callable(title.Title) else title.Title
        elif hasattr(title, 'title'): 
            #log('titleObjectToString: title', 'tOTS')
            title = title.title() if callable(title.title) else title.title
        else:
            try:
                if hasattr(title, 'keys'):
                    keys = title.keys() if callable(title.keys) else title.keys
                    if 'title' in keys: 
                        #log('titleObjectToString: keys[title]', 'tOTS')
                        title = title['title']
                    elif 'Title' in keys: 
                        #log('titleObjectToString: keys[Title]', 'tOTS')
                        title = title['Title']                              
                elif 'title' in title: 
                    #log('titleObjectToString: [title]', 'tOTS')
                    title = title['title']
                elif 'Title' in title: 
                    #log('titleObjectToString: [Title]', 'tOTS')
                    title = title['Title']          
                elif FIELDS.TITLE in title:
                    #log('titleObjectToString: [FIELDS.TITLE]', 'tOTS')
                    title = title[FIELDS.TITLE] 
                else:
                    #log('titleObjectToString: Nothing Found', 'tOTS')
                    #log(title)
                    #log(title.keys())
                    return title
            except: 
                #log('titleObjectToString: except', 'tOTS')
                #log(title)
                return title
        return EvernoteNoteTitle.titleObjectToString(title)

    @property
    def FullTitle(self):
        """:rtype: str"""
        return self.__title__

    def __init__(self, titleObj=None):
        """:type titleObj: str | unicode | sqlite.Row | EvernoteNoteTitle | evernote.edam.type.ttypes.Note | EvernoteNotePrototype.EvernoteNotePrototype  """
        self.__title__ = self.titleObjectToString(titleObj)

def generateTitleParts(title):
    title = EvernoteNoteTitle.titleObjectToString(title)    
    try:
        strTitle = re.sub(':+', ':', title)
    except:
        log('generateTitleParts Unable to re.sub')
        log(type(title))
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

