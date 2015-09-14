from anknotes.EvernoteNoteTitle import EvernoteNoteTitle as NoteTitleKey
from anknotes.html import generate_evernote_url, generate_evernote_link, generate_evernote_link_by_level
from anknotes.structs import upperFirst

class EvernoteNote:
    ################## CLASS Note ################
    Title = None
    """:type: NoteTitleKey"""
    Content = ""
    Guid = ""
    UpdateSequenceNum = -1
    """:type: int"""
    TagNames = []
    TagGuids = []
    NotebookGuid = ""
    Status = -1
    Children = []

    @property
    def Tags(self): return self.TagNames

    def process_tags(self):
        if isinstance(self.TagNames, str) or isinstance(self.TagNames, unicode):
            self.TagNames = self.TagNames[1:-1].split(',')
        if isinstance(self.TagGuids, str) or isinstance(self.TagGuids, unicode):
            self.TagGuids = self.TagGuids[1:-1].split(',')

    def __repr__(self):
        return u"<EN Note: %s: '%s'>" % (self.Guid, self.Title)

    def __init__(self, title=None, content=None, guid=None, tags=None, notebookGuid=None, updateSequenceNum=None,
                 whole_note=None, db_note=None):
        """

        :type whole_note: evernote.edam.type.ttypes.Note
        :type db_note: sqlite.Row
        """
        self.Status = -1
        self.TagNames = tags
        if whole_note is not None:
            self.Title = NoteTitleKey(whole_note)
            self.Content = whole_note.content
            self.Guid = whole_note.guid
            self.NotebookGuid = whole_note.notebookGuid
            self.UpdateSequenceNum = whole_note.updateSequenceNum
            return
        if db_note is not None:
            self.Title = NoteTitleKey(db_note)
            if isinstance(db_note['tagNames'], str):
                db_note['tagNames'] = unicode(db_note['tagNames'], 'utf-8')
            for key in ['content', 'guid', 'notebookGuid', 'updateSequenceNum', 'tagNames', 'tagGuids']:
                setattr(self, upperFirst(key), db_note[key])
            if isinstance(self.Content, str):
                self.Content = unicode(self.Content, 'utf-8')
            self.process_tags()
            return
        self.Title = NoteTitleKey(title)
        self.Content = content
        self.Guid = guid
        self.NotebookGuid = notebookGuid
        self.UpdateSequenceNum = updateSequenceNum

    def generateURL(self):
        return generate_evernote_url(self.Guid)

    def generateLink(self, value=None):
        return generate_evernote_link(self.Guid, self.Title.Name().title, value)

    def generateLevelLink(self, value=None):
        return generate_evernote_link_by_level(self.Guid, self.Title.Name().title, value)

    def isRoot(self):
        return self.Title.isRoot

    def isChild(self):
        return self.Title.isChild

    def isParent(self):
        return self.Title.isParent()

    def isLevel(self, level):
        return self.Title.isLevel(level)

    def isAboveLevel(self, level):
        return self.Title.isAboveLevel(level)
        ################## END CLASS Note ################
