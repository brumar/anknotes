class EvernoteNotePrototype:
    title = ""
    content = ""
    guid = ""
    updateSequenceNum = -1
    tags = []
    notebookGuid = ""
    status = -1

    def __init__(self, title=None, content=None, guid=None, tags=None, notebookGuid=None, updateSequenceNum=None,
                 whole_note=None):
        self.status = -1
        self.tags = tags
        if not whole_note is None:
            self.title = whole_note.title
            self.content = whole_note.content
            self.guid = whole_note.guid
            self.notebookGuid = whole_note.notebookGuid
            self.updateSequenceNum = whole_note.updateSequenceNum
            return
        self.title = title
        self.content = content
        self.guid = guid
        self.notebookGuid = notebookGuid
        self.updateSequenceNum = updateSequenceNum
