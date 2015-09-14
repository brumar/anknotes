# from anknotes.EvernoteNoteTitle import NoteTitle
from anknotes.toc import TOCKey as NoteTitleKey
from anknotes.html import generate_evernote_url, generate_evernote_link, generate_evernote_link_by_level


class EvernoteNote:
    ################## CLASS Note ################
    title = None
    content = ""
    guid = ""
    updateSequenceNum = -1
    tags = []
    tagGuids = []
    notebookGuid = ""
    status = -1
    children = []

    def __repr__(self):
        return u"<EN Note: %s: '%s'>" % (self.guid, self.title)

    def __init__(self, title=None, content=None, guid=None, tags=None, notebookGuid=None, updateSequenceNum=None,
                 whole_note=None, db_note=None):
        self.status = -1
        self.tags = tags
        if not whole_note is None:
            self.title = NoteTitleKey(whole_note.title)
            self.content = whole_note.content
            self.guid = whole_note.guid
            self.notebookGuid = whole_note.notebookGuid
            self.updateSequenceNum = whole_note.updateSequenceNum
            return
        if not db_note is None:
            if isinstance(db_note['tagNames'], str):
                db_note['tagNames'] = unicode(db_note['tagNames'], 'utf-8')
                # print "Creating enNote: %s " % db_note['title']
            self.title = NoteTitleKey(title=db_note['title'])
            self.content = db_note['content']
            self.guid = db_note['guid']
            self.notebookGuid = db_note['notebookGuid']
            self.updateSequenceNum = db_note['updateSequenceNum']
            self.tags = db_note['tagNames'][1:-1].split(',')
            self.tagGuids = db_note['tagGuids'][1:-1].split(',')
            if isinstance(self.content, str):
                self.content = unicode(self.content, 'utf-8')
            if isinstance(self.title, str):
                self.title = unicode(self.title, 'utf-8')
                self.title = NoteTitleKey(self.title)
            return
        self.title = NoteTitleKey(title)
        self.content = content
        self.guid = guid
        self.notebookGuid = notebookGuid
        self.updateSequenceNum = updateSequenceNum

    def generateURL(self):
        return generate_evernote_url(self.guid)

    def generateLink(self, value=None):
        return generate_evernote_link(self.guid, self.title.Name().title, value)

    def generateLevelLink(self, value=None):
        return generate_evernote_link_by_level(self.guid, self.title.Name().title, value)

    def isRoot(self):
        return self.title.isRoot()

    def isChild(self):
        return self.title.isChild()

    def isParent(self):
        return self.title.isParent()

    def isLevel(self, level):
        return self.title.isLevel(level)

    def isAboveLevel(self, level):
        return self.title.isAboveLevel(level)
        ################## END CLASS Note ################
