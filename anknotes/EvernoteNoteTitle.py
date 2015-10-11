# -*- coding: utf-8 -*-
### Anknotes Shared Imports
from anknotes.shared import *
from sys import stderr


def generateTOCTitle(title):
    title = EvernoteNoteTitle.titleObjectToString(title).upper()
    for chr in u'αβδφḃ':
        title = title.replace(chr.upper(), chr)
    return title


class EvernoteNoteTitle:
    level = 0
    __title = ""
    """:type: str"""
    __titleParts = None
    """:type: list[str]"""

    # # Parent = None
    # def __str__(self):
    #     return "%d: %s" % (self.Level(), self.Title)

    def __repr__(self):
        return "<%s:%s>" % (self.__class__.__name__, self.FullTitle)

    @property
    def TitleParts(self):
        if not self.FullTitle:
            return []
        if not self.__titleParts:
            self.__titleParts = generateTitleParts(self.FullTitle)
        return self.__titleParts

    @property
    def Level(self):
        """
        :rtype: int
        :return: Current Level with 1 being the Root Title
        """
        if not self.level:
            self.level = len(self.TitleParts)
        return self.level

    @property
    def Depth(self):
        return self.Level - 1

    def Parts(self, level=-1):
        return self.Slice(level)

    def Part(self, level=-1):
        mySlice = self.Parts(level)
        if not mySlice:
            return None
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
        if not newParts:
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
    def titleObjectToString(title, recursion=0):
        """
        :param title: Title in string, unicode, dict, sqlite, TOCKey or NoteTitle formats. Note objects are also parseable
        :type title: None | str | unicode | dict[str,str] | sqlite.Row | EvernoteNoteTitle
        :return: string Title
        :rtype: str
        """
        # if recursion == 0:
        #     str_ = str_safe(title)
        #     try: log(u'\n---------------------------------%s' % str_, 'tOTS', timestamp=False)
        #     except Exception: log(u'\n---------------------------------%s' % '[UNABLE TO DISPLAY TITLE]', 'tOTS', timestamp=False)
        #     pass

        if title is None:
            # log('NoneType', 'tOTS', timestamp=False)
            return ""
        if is_str_type(title):
            # log('str/unicode', 'tOTS', timestamp=False)
            return title
        if hasattr(title, 'FullTitle'):
            # log('FullTitle', 'tOTS', timestamp=False)
            # noinspection PyCallingNonCallable
            title = title.FullTitle() if callable(title.FullTitle) else title.FullTitle
        elif hasattr(title, 'Title'):
            # log('Title', 'tOTS', timestamp=False)
            title = title.Title() if callable(title.Title) else title.Title
        elif hasattr(title, 'title'):
            # log('title', 'tOTS', timestamp=False)
            title = title.title() if callable(title.title) else title.title
        else:
            try:
                if hasattr(title, 'keys'):
                    keys = title.keys() if callable(title.keys) else title.keys
                    if 'title' in keys:
                        # log('keys[title]', 'tOTS', timestamp=False)
                        title = title['title']
                    elif 'Title' in keys:
                        # log('keys[Title]', 'tOTS', timestamp=False)
                        title = title['Title']
                    elif not keys:
                        # log('keys[empty dict?]', 'tOTS', timestamp=False)
                        raise
                    else:
                        log('keys[Unknown Attr]: %s' % str(keys), 'tOTS', timestamp=False)
                        return ""
                elif 'title' in title:
                    # log('[title]', 'tOTS', timestamp=False)
                    title = title['title']
                elif 'Title' in title:
                    # log('[Title]', 'tOTS', timestamp=False)
                    title = title['Title']
                elif FIELDS.TITLE in title:
                    # log('[FIELDS.TITLE]', 'tOTS', timestamp=False)
                    title = title[FIELDS.TITLE]
                else:
                    # log('Nothing Found', 'tOTS', timestamp=False)
                    # log(title)
                    # log(title.keys())
                    return title
            except Exception:
                log('except', 'tOTS', timestamp=False)
                log(title, 'toTS', timestamp=False)
                raise LookupError
        recursion += 1
        # log(u'recursing %d: ' % recursion, 'tOTS', timestamp=False)
        return EvernoteNoteTitle.titleObjectToString(title, recursion)

    @property
    def FullTitle(self):
        """:rtype: str"""
        return self.__title

    @property
    def HTML(self):
        return self.__html

    def __init__(self, titleObj=None):
        """:type titleObj: str | unicode | sqlite.Row | EvernoteNoteTitle | evernote.edam.type.ttypes.Note | EvernoteNotePrototype.EvernoteNotePrototype  """
        self.__html = self.titleObjectToString(titleObj)
        self.__title = strip_tags_and_new_lines(self.__html)


def generateTitleParts(title):
    title = EvernoteNoteTitle.titleObjectToString(title)
    try:
        strTitle = re.sub(':+', ':', title)
    except Exception:
        log('generateTitleParts Unable to re.sub')
        log(type(title))
        raise
    strTitle = strTitle.strip(':')
    partsText = strTitle.split(':')
    count = len(partsText)
    for i in range(1, count + 1):
        txt = partsText[i - 1]
        try:
            txt = txt.strip()
        except Exception:
            print_safe(title + ' -- ' + '"' + txt + '"')
            raise
        partsText[i - 1] = txt
    return partsText
