import os
from anknotes import stopwatch
from anknotes.imports import import_etree
import time

if import_etree():
    try:
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        from sqlite3 import dbapi2 as sqlite
    from anknotes.imports import lxml, etree

    ### Anknotes Module Imports for Stand Alone Scripts
    from anknotes import evernote as evernote
    ### Anknotes Shared Imports
    from anknotes.shared import *
    from anknotes.error import *
    from anknotes.toc import TOCHierarchyClass

    ### Anknotes Class Imports
    from anknotes.AnkiNotePrototype import AnkiNotePrototype
    from anknotes.EvernoteNoteTitle import generateTOCTitle

    ### Anknotes Main Imports
    from anknotes.Anki import Anki
    from anknotes.ankEvernote import Evernote
    # from anknotes.EvernoteNoteFetcher import EvernoteNoteFetcher
    # from anknotes.EvernoteNotes import EvernoteNotes
    # from anknotes.EvernoteNotePrototype import EvernoteNotePrototype
    # from anknotes.EvernoteImporter import EvernoteImporter
    #
    # ### Evernote Imports
    # from anknotes.evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
    # from anknotes.evernote.edam.type.ttypes import NoteSortOrder, Note as EvernoteNote
    from anknotes.evernote.edam.error.ttypes import EDAMSystemException, EDAMUserException, EDAMNotFoundException
    # from anknotes.evernote.api.client import EvernoteClient

    def mk_banner(fn, display_initial_info=False):
        l.default_filename = fn
        my_info_str = info_str % l.default_filename.upper()
        myTmr = stopwatch.Timer(len(queued_items[fn]), 10, infoStr=my_info_str, do_print=True, label=l.base_path,
                                display_initial_info=display_initial_info)
        l.go("------------------------------------------------", clear=True)
        l.go(my_info_str)
        l.go("------------------------------------------------")
        return myTmr

    ankDBSetLocal()
    db = ankDB(TABLES.NOTE_VALIDATION_QUEUE)
    db.Init()

    queued_items = {'Failed': db.all("validation_status = -1"),
                    'Pending': db.all("validation_status = 0"),
                    'Successful': db.all("validation_status = 1")}
    info_str = 'CHECKING {num} %s MAKE NOTE QUEUE ITEMS'

    l = Logger('Validation\\validate_notes\\', rm_path=True, do_print=True, timestamp=False)

    tmr = mk_banner('Successful')
    for result in queued_items[l.default_filename]:
        line = ("    [%-30s] " % ((result['guid']) + ':')) if result['guid'] else "NEW   [%-30s] " % ''
        line += result['title']
        l.go(line)

    tmr = mk_banner('Failed')
    for result in queued_items[l.default_filename]:
        line = '%-60s ' % (result['title'] + ':')
        line += ("       [%-30s] " % ((result['guid']) + ':')) if result['guid'] else "NEW"
        line += '\n' + result['validation_result']
        l.go(line)
        l.go("------------------------------------------------\n")
        l.go(result['contents'])
        l.go("------------------------------------------------\n")

    EN = Evernote()

    tmr = mk_banner('Pending', display_initial_info=True)
    timerFull = stopwatch.Timer()
    for result in queued_items[l.default_filename]:
        guid = result['guid']
        noteContents = result['contents']
        noteTitle = result['title']
        line = ("    [%-30s] " % ((result['guid']) + ':')) if result['guid'] else "NEW   [%-30s] " % ''
        errors = tmr.autoStep(EN.validateNoteContent(noteContents, noteTitle), noteTitle)
        validation_status = 1 if tmr.status.IsSuccess else -1

        line = " SUCCESS! " if tmr.status.IsSuccess else " FAILURE: "
        line += '     ' if result['guid'] else ' NEW '
        # line += ' %-60s ' % (result['title'] + ':')
        l.dump(errors, 'LXML ERRORS', 'lxml_errors', wrap_filename=False, crosspost_to_default=False)
        if not tmr.status.IsSuccess:
            if not is_str_type(errors):
                errors = '\n    * ' + '\n    * '.join(errors)
            l.go(line + errors)
        else:
            if not is_str_type(errors):
                errors = '\n'.join(errors)

        sql = "UPDATE {t} SET validation_status = ?, validation_result = ? WHERE "
        data = [validation_status, errors]
        if guid:
            sql += "guid = ?"
            data += [guid]
        else:
            sql += "title = ? AND contents = ?"
            data += [noteTitle, noteContents]

        db.execute(sql, data)

    timerFull.stop()
    l.go("Validation of %d results completed in %s" % (tmr.max, str(timerFull)))

    db.commit()
    db.close()
