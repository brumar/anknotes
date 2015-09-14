# -*- coding: utf-8 -*-
from EvernoteNotes import EvernoteNotes
from shared import *

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

Error = sqlite.Error
ankDBSetLocal()

# from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
# from evernote.edam.type.ttypes import NoteSortOrder
# from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode
# from evernote.api.client import EvernoteClient

title = unicode(
    ankDB().scalar("SELECT title FROM anknotes_evernote_notes WHERE guid = '13398462-7129-48bb-b13d-4139e324119a'"))
title_utf8 = title.encode('utf8')
# file_object = open('pytho2!n_intro.txt', 'w')
# file_object.write(title_utf8)
# file_object.close()     

# import sys 
# import locale
# encoding = locale.getpreferredencoding()
# print encoding 
# for x in range(945, 969):
# u = unichr(x)
# print(("%d %x "+"%s %s %s  ") % (x, x, u.encode('utf-8'), repr(u.encode('utf-8')), repr(u.encode('cp737'))))

# text=u'The \u03c0 number was known to Greeks.'
# full_path = u'test2-output.txt'
# with open(full_path , 'w+') as fileLog:
# print>>fileLog, text

# title = unicode(ankDB().scalar("SELECT title FROM anknotes_evernote_notes WHERE guid = '13398462-7129-48bb-b13d-4139e324119a'"))
# title_utf8 = title.encode('utf8')
# file_object = open('pytho2!n_intro.txt', 'w')
# file_object.write(title_utf8)
# file_object.close()     

# full_path = u'test-output.txt'
# with open(full_path , 'w+') as fileLog:
# print>>fileLog, title_utf8

# if isinstance(title , str):
# title = unicode(title , 'utf-8')

# # title_decode = title.decode('utf-8')    


# file_object = open('pytho2n_intro.txt', 'w')
# file_object.write(text.encode('utf8'))
# file_object.close()        

# motto=u'''The Plato's Academy motto was:
# '\u1f00\u03b3\u03b5\u03c9\u03bc\u03ad\u03c4\u03c1\u03b7\u03c4\u03bf\u03c2 \u03bc\u03b7\u03b4\u03b5\u1f76\u03c2 \u03b5\u1f30\u03c3\u03af\u03c4\u03c9'
# '''
# file_object = open('python_intro.txt', 'w')
# file_object.write(motto.encode('utf8'))
# file_object.close()    

# print(text)
# e_str = '\xc3\xa9'
# print(e_str)
# quit
# # full_path = u'test-output.txt'
# # with open(full_path , 'w+') as fileLog:
# # print>>fileLog, title_decode


# exit 

NoteDB = EvernoteNotes()
NoteDB.baseQuery = "notebookGuid != 'fdccbccf-ee70-4069-a587-82772a96d9d3' AND notebookGuid != 'faabcd80-918f-49ca-a349-77fd0036c051'"
# NoteDB.populateAllRootNotesWithoutTOCOrOutlineDesignation()
NoteDB.populateAllRootNotesMissing()
# enNote = NoteDB.getNoteFromDBByGuid('bb490d9c-722a-48f2-a678-6a14919dd3ea')
# NoteDB.addChildNoteHierarchically(dict, enNote)
