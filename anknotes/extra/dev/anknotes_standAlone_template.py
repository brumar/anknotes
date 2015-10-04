import os
from anknotes import stopwatch
import time

try:
    from lxml import etree

    eTreeImported = True
except:
    eTreeImported = False
if eTreeImported:
    try:
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        from sqlite3 import dbapi2 as sqlite

    # Anknotes Module Imports for Stand Alone Scripts
    from anknotes import evernote as evernote

    # Anknotes Shared Imports
    from anknotes.shared import *
    from anknotes.error import *
    from anknotes.toc import TOCHierarchyClass

    # Anknotes Class Imports
    from anknotes.AnkiNotePrototype import AnkiNotePrototype
    from anknotes.EvernoteNoteTitle import generateTOCTitle

    # Anknotes Main Imports
    from anknotes.Anki import Anki
    from anknotes.ankEvernote import Evernote
    from anknotes.EvernoteNoteFetcher import EvernoteNoteFetcher
    from anknotes.EvernoteNotes import EvernoteNotes
    from anknotes.EvernoteNotePrototype import EvernoteNotePrototype
    from anknotes.EvernoteImporter import EvernoteImporter

    # Evernote Imports
    from anknotes.evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
    from anknotes.evernote.edam.type.ttypes import NoteSortOrder, Note as EvernoteNote
    from anknotes.evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException, EDAMNotFoundException
    from anknotes.evernote.api.client import EvernoteClient

    ankDBSetLocal()
    db = ankDB()
    db.Init()

    failed_queued_items = db.all("SELECT * FROM %s WHERE validation_status = 1 " % TABLES.MAKE_NOTE_QUEUE)
    pending_queued_items = db.all("SELECT * FROM %s WHERE validation_status = 0" % TABLES.MAKE_NOTE_QUEUE)
    success_queued_items = db.all("SELECT * FROM %s WHERE validation_status = -1 " % TABLES.MAKE_NOTE_QUEUE)

    currentLog = 'Successful'
    log("------------------------------------------------", 'MakeNoteQueue-' + currentLog, timestamp=False,
        do_print=True, clear=True)
    log(" CHECKING %3d SUCCESSFUL MAKE NOTE QUEUE ITEMS " % len(success_queued_items), 'MakeNoteQueue-' + currentLog,
        timestamp=False, do_print=True)
    log("------------------------------------------------", 'MakeNoteQueue-' + currentLog, timestamp=False,
        do_print=True)

    for result in success_queued_items:
        line = ("    [%-30s] " % ((result['guid']) + ':')) if result['guid'] else "NEW   [%-30s] " % ''
        line += result['title']
        log(line, 'MakeNoteQueue-' + currentLog, timestamp=False, do_print=False)

    currentLog = 'Failed'
    log("------------------------------------------------", 'MakeNoteQueue-' + currentLog, timestamp=False,
        do_print=True, clear=True)
    log(" CHECKING %3d FAILED MAKE NOTE QUEUE ITEMS " % len(failed_queued_items), 'MakeNoteQueue-' + currentLog,
        clear=False, timestamp=False, do_print=True)
    log("------------------------------------------------", 'MakeNoteQueue-' + currentLog, timestamp=False,
        do_print=True)

    for result in failed_queued_items:
        line = '%-60s ' % (result['title'] + ':')
        line += ("       [%-30s] " % ((result['guid']) + ':')) if result['guid'] else "NEW"
        line += result['validation_result']
        log(line, 'MakeNoteQueue-' + currentLog, timestamp=False, do_print=True)
        log("------------------------------------------------\n", 'MakeNoteQueue-' + currentLog, timestamp=False)
        log(result['contents'], 'MakeNoteQueue-' + currentLog, timestamp=False)
        log("------------------------------------------------\n", 'MakeNoteQueue-' + currentLog, timestamp=False)

    EN = Evernote()

    currentLog = 'Pending'
    log("------------------------------------------------", 'MakeNoteQueue-' + currentLog, timestamp=False,
        do_print=True, clear=True)
    log(" CHECKING %3d PENDING MAKE NOTE QUEUE ITEMS " % len(pending_queued_items), 'MakeNoteQueue-' + currentLog,
        clear=False, timestamp=False, do_print=True)
    log("------------------------------------------------", 'MakeNoteQueue-' + currentLog, timestamp=False,
        do_print=True)

    timerFull = stopwatch.Timer()
    for result in pending_queued_items:
        guid = result['guid']
        noteContents = result['contents']
        noteTitle = result['title']
        line = ("    [%-30s] " % ((result['guid']) + ':')) if result['guid'] else "NEW   [%-30s] " % ''

        success, errors = EN.validateNoteContent(noteContents, noteTitle)
        validation_status = 1 if success else -1

        line = " SUCCESS! " if success else " FAILURE: "
        line += '     ' if result['guid'] else ' NEW '
        # line += ' %-60s ' % (result['title'] + ':')
        if not success:
            errors = '\n    * ' + '\n    * '.join(errors)
            log(line, 'MakeNoteQueue-' + currentLog, timestamp=False, do_print=True)
        else:
            errors = '\n'.join(errors)

        sql = "UPDATE %s SET validation_status = %d, validation_result = '%s' WHERE " % (
            TABLES.MAKE_NOTE_QUEUE, validation_status, escape_text_sql(errors))
        if guid:
            sql += "guid = '%s'" % guid
        else:
            sql += "title = '%s' AND contents = '%s'" % (escape_text_sql(noteTitle), escape_text_sql(noteContents))

        db.execute(sql)

    timerFull.stop()
    log("Validation of %d results completed in %s" % (len(pending_queued_items), str(timerFull)),
        'MakeNoteQueue-' + currentLog, timestamp=False, do_print=True)

    db.commit()
    db.close()
