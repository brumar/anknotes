# -*- coding: utf-8 -*-
# Python Imports
from subprocess import *

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

# Anknotes Shared Imports
from anknotes.shared import *
from anknotes.constants import *

# Anknotes Main Imports
from anknotes.Controller import Controller

# Anki Imports
from aqt.qt import SIGNAL, QMenu, QAction
from aqt import mw
from aqt.utils import getText
# from anki.storage import Collection

DEBUG_RAISE_API_ERRORS = False
# log('Checking for log at %s:\n%s' % (__name__, dir(log)), 'import')


# noinspection PyTypeChecker
def anknotes_setup_menu():
    menu_items = [
        [u"&Anknotes",
         [
             ["&Import from Evernote", import_from_evernote],
             ["&Enable Auto Import On Profile Load", {'action': anknotes_menu_auto_import_changed, 'checkable': True}],
             ["Note &Validation",
              [
                  ["Validate &And Upload Pending Notes", validate_pending_notes],
                  ["SEPARATOR", None],
                  ["&Validate Pending Notes", lambda: validate_pending_notes(True, False)],
                  ["&Upload Validated Notes", upload_validated_notes]
              ]
              ],
             ["Process &See Also Footer Links [Power Users Only!]",
              [
                  ["Complete All &Steps", see_also],
                  ["SEPARATOR", None],
                  ["Step &1: Process Anki Notes Without See Also Field", lambda: see_also(1)],
                  ["Step &2: Extract Links from TOC", lambda: see_also(2)],
                  ["SEPARATOR", None],
                  ["Step &3: Create Auto TOC Evernote Notes", lambda: see_also(3)],
                  ["Step &4: Validate and Upload Auto TOC Notes", lambda: see_also(4)],
                  ["Step &5: Rebuild TOC/Outline Link Database", lambda: see_also(6)],
                  ["SEPARATOR", None],
                  ["Step &6: Insert TOC/Outline Links Into Anki Notes", lambda: see_also(7)],
                  ["Step &7: Update See Also Footer In Evernote Notes", lambda: see_also(8)],
                  ["Step &8: Validate and Upload Modified Evernote Notes", lambda: see_also(9)],
                  ["SEPARATOR", None],
                  ["Step &9: Insert TOC and Outline Content Into Anki Notes", lambda: see_also(10)]
              ]
              ],
             ["&Maintenance Tasks",
              [
                  ["Find &Deleted Notes", find_deleted_notes],
                  ["Res&ync with Local DB", resync_with_local_db],
                  ["Update Evernote &Ancillary Data", update_ancillary_data]
              ]
              ]

         ]
         ]
    ]
    add_menu_items(menu_items)


def add_menu_items(menu_items, parent=None):
    if not parent: parent = mw.form.menubar
    for title, action in menu_items:
        if title == "SEPARATOR":
            parent.addSeparator()
        elif isinstance(action, list):
            menu = QMenu(_(title), parent)
            parent.insertMenu(mw.form.menuTools.menuAction(), menu)
            add_menu_items(action, menu)
        else:
            checkable = False
            if isinstance(action, dict):
                options = action
                action = options['action']
                if 'checkable' in options:
                    checkable = options['checkable']
            menu_action = QAction(_(title), mw, checkable=checkable)
            parent.addAction(menu_action)
            parent.connect(menu_action, SIGNAL("triggered()"), action)
            if checkable:
                anknotes_checkable_menu_items[title] = menu_action


def anknotes_menu_auto_import_changed():
    title = "&Enable Auto Import On Profile Load"
    doAutoImport = anknotes_checkable_menu_items[title].isChecked()
    mw.col.conf[
        SETTINGS.ANKNOTES_CHECKABLE_MENU_ITEMS_PREFIX + '_' + title.replace(' ', '_').replace('&', '')] = doAutoImport
    mw.col.setMod()
    mw.col.save()
    # import_timer_toggle()


def anknotes_load_menu_settings():
    global anknotes_checkable_menu_items
    for title, menu_action in anknotes_checkable_menu_items.items():
        menu_action.setChecked(mw.col.conf.get(
            SETTINGS.ANKNOTES_CHECKABLE_MENU_ITEMS_PREFIX + '_' + title.replace(' ', '_').replace('&', ''), False))


def import_from_evernote_manual_metadata(guids=None):
    if not guids:
        guids = find_evernote_guids(file(ANKNOTES.LOG_FDN_UNIMPORTED_EVERNOTE_NOTES, 'r').read())
    log("Manually downloading %d Notes" % len(guids))
    controller = Controller()
    controller.evernote.initialize_note_store()
    controller.forceAutoPage = True
    controller.currentPage = 1
    controller.ManualGUIDs = guids
    controller.proceed()


def import_from_evernote(auto_page_callback=None):
    controller = Controller()
    controller.evernote.initialize_note_store()
    controller.auto_page_callback = auto_page_callback
    if auto_page_callback:
        controller.forceAutoPage = True
        controller.currentPage = 1
    else:
        controller.forceAutoPage = False
        controller.currentPage = mw.col.conf.get(SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE, 1)
    controller.proceed()


def upload_validated_notes(automated=False):
    controller = Controller()
    controller.upload_validated_notes(automated)


def find_deleted_notes(automated=False):
    if not automated and False:
        showInfo("""In order for this to work, you must create a 'Table of Contents' Note using the Evernote desktop application. Include all notes that you want to sync with Anki.

Export this note to the following path: '%s'.

Press Okay to save and close your Anki collection, open the command-line deleted notes detection tool, and then re-open your Anki collection.

Once the command line tool is done running, you will get a summary of the results, and will be prompted to delete Anki Orphan Notes or download Missing Evernote Notes""" % ANKNOTES.TABLE_OF_CONTENTS_ENEX,
                 richText=True)

    # mw.col.save()
    # if not automated:
    #     mw.unloadCollection()
    # else:
    #     mw.col.close()
    # handle = Popen(['python',ANKNOTES.FIND_DELETED_NOTES_SCRIPT], stdin=PIPE, stderr=PIPE, stdout=PIPE, shell=True)
    # stdoutdata, stderrdata = handle.communicate()
    # err = ("ERROR: {%s}\n\n" % stderrdata) if stderrdata else ''
    # stdoutdata = re.sub(' +', ' ', stdoutdata)
    from anknotes import find_deleted_notes
    returnedData = find_deleted_notes.do_find_deleted_notes()
    lines = returnedData['Summary']
    info = tableify_lines(lines, '#|Type|Info')
    # info = '<table><tr class=tr0><td class=t1>#</td><td class=t2>Type</td><td class=t3></td></tr>%s</table>' % '\n'.join(lines)
    # info = info.replace('\n', '\n<BR>').replace('  ', '&nbsp; &nbsp; ')
    anknotes_dels = returnedData['AnknotesOrphans']
    anknotes_dels_count = len(anknotes_dels)
    anki_dels = returnedData['AnkiOrphans']
    anki_dels_count = len(anki_dels)
    missing_evernote_notes = returnedData['MissingEvernoteNotes']
    missing_evernote_notes_count = len(missing_evernote_notes)   
    showInfo(info, richText=True, minWidth=600)
    db_changed = False
    if anknotes_dels_count > 0:
        code = \
        getText("Please enter code 'ANKNOTES_DEL_%d' to delete your orphan Anknotes DB note(s)" % anknotes_dels_count)[
            0]
        if code == 'ANKNOTES_DEL_%d' % anknotes_dels_count:
            ankDB().executemany("DELETE FROM %s WHERE guid = ?" % TABLES.EVERNOTE.NOTES, [[x] for x in anknotes_dels])
            ankDB().executemany("DELETE FROM cards as c, notes as n WHERE c.nid = n.id AND n.flds LIKE '%' | ? | '%'",
                                [[FIELDS.EVERNOTE_GUID_PREFIX + x] for x in anknotes_dels])
            db_changed = True
            show_tooltip("Deleted all %d Orphan Anknotes DB Notes" % anknotes_dels_count, 5000, 3000)
    if anki_dels_count > 0:
        code = getText("Please enter code 'ANKI_DEL_%d' to delete your orphan Anki note(s)" % anki_dels_count)[0]
        if code == 'ANKI_DEL_%d' % anki_dels_count:
            ankDB().executemany("DELETE FROM cards as c, notes as n WHERE c.nid = n.id AND n.flds LIKE '%' | ? | '%'",
                                [[FIELDS.EVERNOTE_GUID_PREFIX + x] for x in anki_dels])
            db_changed = True
            show_tooltip("Deleted all %d Orphan Anki Notes" % anki_dels_count, 5000, 3000)
    if db_changed:
        ankDB().commit()
    if missing_evernote_notes_count > 0:
        evernote_confirm = "Would you like to import %d missing Evernote Notes?<BR><BR><a href='%s'>Click to view results</a>" % (
        missing_evernote_notes_count,
        convert_filename_to_local_link(get_log_full_path(ANKNOTES.LOG_FDN_UNIMPORTED_EVERNOTE_NOTES)))
        ret = showInfo(evernote_confirm, cancelButton=True, richText=True)
        if ret:
            import_from_evernote_manual_metadata(missing_evernote_notes)


def validate_pending_notes(showAlerts=True, uploadAfterValidation=True, callback=None):
    mw.unloadCollection()
    if showAlerts:
        showInfo("""Press Okay to save and close your Anki collection, open the command-line note validation tool, and then re-open your Anki collection.%s

Anki will be unresponsive until the validation tool completes. This will take at least 45 seconds.  The tool's output will be displayed upon completion. """
                 % (
                 ' You will be given the option of uploading successfully validated notes once your Anki collection is reopened.' if uploadAfterValidation else ''))
    handle = Popen(['python', ANKNOTES.VALIDATION_SCRIPT], stdin=PIPE, stderr=PIPE, stdout=PIPE, shell=True)
    stdoutdata, stderrdata = handle.communicate()
    stdoutdata = re.sub(' +', ' ', stdoutdata)
    info = ("ERROR: {%s}<HR>" % stderrdata) if stderrdata else ''
    allowUpload = True
    if showAlerts:        
        tds = [[str(count), '<a href="%s">VIEW %s VALIDATIONS LOG</a>' % (fn, key.upper())] for key, fn, count in [
            [key, get_log_full_path(key, as_url_link=True), int(re.search(r'CHECKING +(\d{1,3}) +' + key.upper() + ' MAKE NOTE QUEUE ITEMS', stdoutdata).group(1))]
            for key in ['Pending', 'Successful', 'Failed']] if count > 0]        
        if not tds:
            show_tooltip("No notes found in the validation queue.")
            allowUpload = False 
        else:
            info += tableify_lines(tds, '#|Result')
            successful = int(re.search(r'CHECKING +(\d{1,3}) +' + 'Successful'.upper() + ' MAKE NOTE QUEUE ITEMS', stdoutdata).group(1))
            allowUpload = (uploadAfterValidation and successful > 0) 
            allowUpload = allowUpload & showInfo("Completed: %s<BR>%s" % (
            'Press Okay to begin uploading %d successfully validated note(s) to the Evernote Servers' % successful if (uploadAfterValidation and successful > 0) else '',
            info), cancelButton=(successful > 0), richText=True)


    # mw.col.reopen()
    # mw.col.load()

    if callback is None and allowUpload:
        callback = upload_validated_notes
    external_tool_callback_timer(callback)


def reopen_collection(callback=None):
    # mw.setupProfile()
    mw.loadCollection()
    ankDB(True)
    if callback: callback()


def external_tool_callback_timer(callback=None):
    mw.progress.timer(3000, lambda: reopen_collection(callback), False)


def see_also(steps=None, showAlerts=None, validationComplete=False):
    controller = Controller()
    if not steps: steps = range(1, 10)
    if isinstance(steps, int): steps = [steps]
    multipleSteps = (len(steps) > 1)
    if showAlerts is None: showAlerts = not multipleSteps
    remaining_steps=steps
    if 1 in steps:
        # Should be unnecessary once See Also algorithms are finalized
        log(" > See Also: Step 1: Processing Un Added See Also Notes")
        controller.process_unadded_see_also_notes()
    if 2 in steps:
        log(" > See Also: Step 2: Extracting Links from TOC")
        controller.anki.extract_links_from_toc()
    if 3 in steps:
        log(" > See Also: Step 3: Creating Auto TOC Evernote Notes")
        controller.create_auto_toc()
    if 4 in steps:
        if validationComplete:
            log(" > See Also: Step 4: Validate and Upload Auto TOC Notes: Upload Validating Notes")
            upload_validated_notes(multipleSteps)
        else:
            steps = [-4]
    if 5 in steps:
        log(" > See Also: Step 5: Inserting TOC/Outline Links Into Anki Notes' See Also Field")
        controller.anki.insert_toc_into_see_also()
    if 6 in steps:
        log(" > See Also: Step 6: Update See Also Footer In Evernote Notes")
    if 7 in steps:
        if validationComplete:
            log(" > See Also: Step 7: Validate and Upload Modified Notes: Upload Validating Notes")
            upload_validated_notes(multipleSteps)
        else:
            steps = [-7]
    if 8 in steps:
        log(" > See Also: Step 8: Inserting TOC/Outline Contents Into Anki Notes")
        controller.anki.insert_toc_and_outline_contents_into_notes()

    do_validation = steps[0]*-1
    if do_validation>0:
        log(" > See Also: Step %d: Validate and Upload %s Notes: Validating Notes" % (do_validation, {4: 'Auto TOC', 7: 'Modified Evernote'}[do_validation]))
        remaining_steps = remaining_steps[remaining_steps.index(do_validation)+validationComplete and 1 or 0:]
        validate_pending_notes(showAlerts, callback=lambda: see_also(remaining_steps, False, True))

def update_ancillary_data():
    controller = Controller()
    controller.evernote.initialize_note_store()
    controller.update_ancillary_data()


def resync_with_local_db():
    controller = Controller()
    controller.resync_with_local_db()


anknotes_checkable_menu_items = {}
