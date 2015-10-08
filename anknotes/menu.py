# -*- coding: utf-8 -*-
# Python Imports
from subprocess import *
from datetime import datetime

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite
# Anknotes Shared Imports
from anknotes.shared import *
from anknotes.constants import *
from anknotes.counters import DictCaseInsensitive

# Anknotes Main Imports
import anknotes.Controller
# from anknotes.Controller import Controller

# Anki Imports
from aqt.qt import SIGNAL, QMenu, QAction
from aqt import mw
from aqt.utils import getText


# from anki.storage import Collection

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
                  ["SEPARATOR", None],
                  ["Step &2: Create Auto TOC Evernote Notes", lambda: see_also(2)],
                  ["Step &3: Validate and Upload Auto TOC Notes", lambda: see_also(3)],
                  ["Step &4: Extract Links from TOC Notes", lambda: see_also(4)],
                  ["SEPARATOR", None],
                  ["Step &5: Insert TOC/Outline Links Into Anki Notes", lambda: see_also(5)],
                  ["Step &6: Update See Also Footer In Evernote Notes", lambda: see_also(6)],
                  ["Step &7: Validate and Upload Modified Evernote Notes", lambda: see_also(7)],
                  ["SEPARATOR", None],
                  ["Step &8: Insert TOC and Outline Content Into Anki Notes", lambda: see_also(8)]
              ]
              ],
             ["&Maintenance Tasks",
              [
                  ["Find &Deleted Notes", find_deleted_notes],
                  ["Res&ync with Local DB", resync_with_local_db],
                  ["Update Evernote &Ancillary Data", update_ancillary_data],
                  ["&lxml Test", lxml_test]
              ]
              ]

         ]
         ]
    ]
    add_menu_items(menu_items)


def auto_reload_wrapper(function): return lambda: auto_reload_modules(function)


def auto_reload_modules(function):
    if ANKNOTES.DEVELOPER_MODE.ENABLED and ANKNOTES.DEVELOPER_MODE.AUTO_RELOAD_MODULES:
        log_banner('AUTO RELOAD MODULES - RELOADING', 'automation', claar=True)
        anknotes.shared = reload(anknotes.shared)
        if not anknotes.Controller: importlib.import_module('anknotes.Controller')
        reload(anknotes.Controller)
    else:
        log_banner('AUTO RELOAD MODULES - SKIPPING RELOAD', 'automation', clear=True)
    function()


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
            # if ANKNOTES.DEVELOPER_MODE.ENABLED and ANKNOTES.DEVELOPER_MODE.AUTO_RELOAD_MODULES:
            action = auto_reload_wrapper(action)
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
        guids = find_evernote_guids(file(FILES.LOGS.FDN.UNIMPORTED_EVERNOTE_NOTES, 'r').read())
    log("Manually downloading %d Notes" % len(guids))
    controller = anknotes.Controller.Controller()
    controller.forceAutoPage = True
    controller.currentPage = 1
    controller.ManualGUIDs = guids
    controller.proceed()


def import_from_evernote(auto_page_callback=None):
    controller = anknotes.Controller.Controller()
    controller.auto_page_callback = auto_page_callback
    if auto_page_callback:
        controller.forceAutoPage = True
        controller.currentPage = 1
    else:
        controller.forceAutoPage = False
        controller.currentPage = mw.col.conf.get(SETTINGS.EVERNOTE.PAGINATION_CURRENT_PAGE, 1)
    controller.proceed()


def create_subnotes(guids):
    def create_subnote(guid):
        def process_lists(lst, names=None, levels=None, under_ul=False):
            def check_subnote(li, sublist):
                if not (li.name == "ol" or li.name == "ul") or not li.contents or not li.contents[0]:
                    return sublist #None, sublist_options  
                # heading = strip_tags(unicode(li.contents[0]), True).strip()
                sublist.heading = strip_tags(unicode(''.join(sublist.list_items)), True).strip()
                sublist.is_reversible = matches_list(sublist.heading, HEADINGS.NOT_REVERSIBLE) is -1                 
                last_char = sublist.heading[-1:]
                sublist.use_descriptor = last_char in ["'", '`']
                if sublist.use_descriptor:
                    sublist.is_reversible = not sublist.is_reversible
                    sublist.heading = sublist.heading[:-1]
                    last_char = sublist.heading[-1:]
                sublist.is_subnote = matches_list(sublist.heading, HEADINGS.TOP) > -1 or matches_list(sublist.heading, HEADINGS.BOTTOM) > -1
                if last_char == ':':
                    sublist.is_subnote = True 
                    sublist.heading = sublist.heading[:-1]
                if not sublist.is_subnote:
                    return sublist #None, sublist_options  
                sublist.sublist = li
                return sublist
                # return li, [heading, is_reversible, use_descriptor]
            
            def add_note(contents, names, levels):
                l.go("NOTE:".ljust(16) + '%-6s %-20s %s' % (
                    '.'.join(map(str, levels)) + ':', ': '.join(names), contents), 'notes',
                     crosspost=('.'.join(map(str, levels)) + ' - ' + '-'.join(names)))
                myNotes.append([levels, names, contents])

            def process_list_item(contents, under_ul=False):
                list_items_full = []
                sublist = DictCaseInsensitive(is_subnote=False, list_items=[])
                for li in contents:
                    if not isinstance(li, Tag): 
                        sublist.list_items.append(unicode(li))
                        continue
                    sublist = check_subnote(li, sublist): 
                    if sublist.is_subnote:
                        break
                    sublist.list_items.append(unicode(li))
                return sublist

            if levels is None or names is None: levels = []; names = [title]
            level = len(levels)
            for lst_items in lst:
                if isinstance(lst_items, Tag):
                    full_text = unicode(str(lst_items.contents), 'utf-8')
                    if len(lst_items.contents) is 0:
                        l.go('NO TOP TEXT:'.ljust(16) + '%s%s: %s' % (
                            '\t' * level, '.'.join(map(str, levels)), full_text), crosspost=['notoptext'])
                        top_text = "N/A"
                    else: 
                        top_text = unicode(str(lst_items.contents[0]),
                                             'utf-8')  # strip_tags(str(lst_items.contents[0])).strip()
                    if lst_items.name == 'ol' or lst_items.name == 'ul':
                        # levels[-1] += 1            
                        new_levels = levels[:]
                        new_levels.append(0)
                        new_names = names[:]
                        new_names.append('CHILD ' + lst_items.name.upper())
                        tag_names = {'ul': 'UNORDERED LIST', 'ol': 'ORDERED LIST'}
                        l.go((tag_names[lst_items.name] + ':').ljust(16) + '[%d] %s: <%s>' % (
                            len(levels), '.'.join(map(str, levels)), ''))
                        process_lists(lst_items.contents, new_names, new_levels, under_ul or lst_items.name == 'ul')
                    elif lst_items.name == 'li':
                        levels[-1] += 1
                        top_text = strip_tags(top_text, True).strip()
                        sublist = process_list_item(lst_items.contents, under_ul)                        
                        if sublist.is_subnote:
                            names[-1] = sublist.heading
                            add_note(sublist, names[:], levels[:])
                            subnote_fn = 'subnotes*\\' + '.'.join(map(str, levels))
                            subnote_shared = '*\\..\\subnotes-all'
                            l.banner(': '.join(names), subnote_fn, clear=True)
                            if not create_subnote.logged_subnote:
                                l.blank(subnote_shared)
                                l.banner(title, subnote_shared, clear=False, append_newline=False)
                                l.banner(title, 'subnotes', clear=True)
                                create_subnote.logged_subnote = True
                            sub_txt = '%s%s: %s' % ('\t' * level, '.'.join(map(str, levels)), sublist.heading)
                            l.go('SUBLIST:'.ljust(16) + sub_txt)
                            l.go(sub_txt, 'subnotes', crosspost=[subnote_fn, subnote_shared])
                            l.go(unicode(sublist.sublist), subnote_fn)
                        else:
                            l.go('LIST ITEM:      %s%s: %s' % (
                                '\t' * level, '.'.join(map(str, levels)), strip_tags(u''.join(sublist.list_items), True).strip()))
                        process_lists(lst_items.contents, names[:], levels[:], under_ul)
                    else:
                        l.go('OTHER TAG:      %s%s: %s' % ('\t' * level, '.'.join(map(str, levels)), top_text))
                elif isinstance(lst_items, NavigableString):
                    this_name = unicode(lst_items).strip()
                    l.go('STRING:'.ljust(16) + '%s%s: %s' % ('\t' * level, '.'.join(map(str, levels)), this_name),
                         crosspost='strings')
                else:
                    l.go('LST ITEMS:'.ljust(16) + lst_items.__class__.__name__, crosspost='*\\..\\unexpected-type')

        content = ankDB().scalar("SELECT content FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, guid))
        title = note_title = get_evernote_title_from_guid(guid)
        l.path_suffix = '\\' + title
        soup = BeautifulSoup(content)
        en_note = soup.find('en-note')
        descriptor = None
        first_div = en_note.find('div')
        if first_div:
            descriptor_text = first_div.text
            if descriptor_text[:1] == '`':
                descriptor = descriptor_text[1:]
                
        lists = en_note.find(['ol', 'ul'])
        lists_all = soup.findAll(['ol', 'ul'])
        l.banner(title, clear=True, crosspost='strings')
        create_subnote.logged_subnote = False
        process_lists([lists])
        # process_lists(lists_all)
        l.go(str(lists), filename='lists', clear=True)
        l.go(soup.prettify(), filename='full', clear=True)

    myNotes = []
    if import_lxml() is False: return False
    from anknotes.shared import lxml
    from BeautifulSoup import BeautifulSoup, NavigableString, Tag
    from copy import copy
    l = Logger(default_filename='bs4', timestamp=False, rm_path=True)
    for guid in guids: 
        create_subnote(guid)


def lxml_test():
    guids = ankDB().list("SELECT guid FROM %s WHERE tagNames LIKE '%%,%s,%%' ORDER BY title ASC " % (
        TABLES.EVERNOTE.NOTES, TAGS.OUTLINE))
    create_subnotes(guids)


def upload_validated_notes(automated=False, **kwargs):
    controller = anknotes.Controller.Controller()
    controller.upload_validated_notes(automated)


def find_deleted_notes(automated=False):
    if not automated:
        showInfo("""In order for this to work, you must create a 'Table of Contents' Note using the Evernote desktop application. Include all notes that you want to sync with Anki.

Export this note to the following path: 
<b>%s</b>

Press Okay to save and close your Anki collection, open the command-line deleted notes detection tool, and then re-open your Anki collection.

Once the command line tool is done running, you will get a summary of the results, and will be prompted to delete Anki Orphan Notes or download Missing Evernote Notes""".replace(
            '\n', '\n<br />') % FILES.USER.TABLE_OF_CONTENTS_ENEX,
                 richText=True)

    # mw.col.save()
    # if not automated:
    #     mw.unloadCollection()
    # else:
    #     mw.col.close() 
    # handle = Popen(['python',FILES.SCRIPTS.FIND_DELETED_NOTES], stdin=PIPE, stderr=PIPE, stdout=PIPE, shell=True)
    # stdoutdata, stderrdata = handle.communicate()
    # err = ("ERROR: {%s}\n\n" % stderrdata) if stderrdata else ''
    # stdoutdata = re.sub(' +', ' ', stdoutdata)
    from anknotes import find_deleted_notes
    returnedData = find_deleted_notes.do_find_deleted_notes()
    if returnedData is False:
        showInfo(
            "An error occurred while executing the script. Please ensure you created the TOC note and saved it as instructed in the previous dialog.")
        return
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
            getText(
                "Please enter code 'ANKNOTES_DEL_%d' to delete your orphan Anknotes DB note(s)" % anknotes_dels_count)[
                0]
        if code == 'ANKNOTES_DEL_%d' % anknotes_dels_count:
            ankDB().executemany("DELETE FROM %s WHERE guid = ?" % TABLES.EVERNOTE.NOTES, [[x] for x in anknotes_dels])
            delete_anki_notes_and_cards_by_guid(anknotes_dels)
            db_changed = True
            show_tooltip("Deleted all %d Orphan Anknotes DB Notes" % anknotes_dels_count, 5000, 3000)
    if anki_dels_count > 0:
        code = getText("Please enter code 'ANKI_DEL_%d' to delete your orphan Anki note(s)" % anki_dels_count)[0]
        if code == 'ANKI_DEL_%d' % anki_dels_count:
            delete_anki_notes_and_cards_by_guid(anki_dels)
            db_changed = True
            show_tooltip("Deleted all %d Orphan Anki Notes" % anki_dels_count, 5000, 6000)
    if db_changed: ankDB().commit()
    if missing_evernote_notes_count > 0:
        if showInfo(
                        "Would you like to import %d missing Evernote Notes?<BR><BR><a href='%s'>Click to view results</a>" % (
                        missing_evernote_notes_count,
                        convert_filename_to_local_link(get_log_full_path(FILES.LOGS.FDN.UNIMPORTED_EVERNOTE_NOTES, filter_disabled=False))),
                cancelButton=True, richText=True):
            import_from_evernote_manual_metadata(missing_evernote_notes)


def validate_pending_notes(showAlerts=True, uploadAfterValidation=True, callback=None, unloadedCollection=False,
                           reload_delay=10):
    if not unloadedCollection: return unload_collection(
        lambda *xargs, **xkwargs: validate_pending_notes(showAlerts, uploadAfterValidation, callback(*xargs, **xkwargs),
                                                         True))
    log("Validating Notes", 'automation')
    if showAlerts:
        showInfo("""Press Okay to save and close your Anki collection, open the command-line note validation tool, and then re-open your Anki collection.%s

Anki will be unresponsive until the validation tool completes. This will take at least 45 seconds.  The tool's output will be displayed upon completion. """
                 % (
                     ' You will be given the option of uploading successfully validated notes once your Anki collection is reopened.' if uploadAfterValidation else ''))
    handle = Popen(['python', FILES.SCRIPTS.VALIDATION], stdin=PIPE, stderr=PIPE, stdout=PIPE, shell=True)
    stdoutdata, stderrdata = handle.communicate()
    stdoutdata = re.sub(' +', ' ', stdoutdata)
    info = ("ERROR: {%s}<HR>" % stderrdata) if stderrdata else ''
    allowUpload = True
    if showAlerts:
        tds = [[str(count), '<a href="%s">VIEW %s VALIDATIONS LOG</a>' % (fn, key.upper())] for key, fn, count in [
            [key, get_log_full_path('MakeNoteQueue\\' + key, filter_disabled=False, as_url_link=True),
             int(re.search(r'CHECKING +(\d{1,3}) +' + key.upper() + ' MAKE NOTE QUEUE ITEMS', stdoutdata).group(1))]
            for key in ['Pending', 'Successful', 'Failed']] if count > 0]
        if not tds:
            show_tooltip("No notes found in the validation queue.")
            allowUpload = False
        else:
            info += tableify_lines(tds, '#|Results')
            successful = int(
                re.search(r'CHECKING +(\d{1,3}) +' + 'Successful'.upper() + ' MAKE NOTE QUEUE ITEMS', stdoutdata).group(
                    1))
            allowUpload = (uploadAfterValidation and successful > 0)
            allowUpload = allowUpload & showInfo("Completed: %s<BR>%s" % (
                'Press Okay to begin uploading %d successfully validated note(s) to the Evernote Servers' % successful if (
                    uploadAfterValidation and successful > 0) else '',
                info), cancelButton=(successful > 0), richText=True)


    # mw.col.reopen()
    # mw.col.load()
    log("Validate Notes completed", 'automation')
    if callback is None and allowUpload: callback = lambda *xargs, **xkwargs: upload_validated_notes()
    mw.progress.timer(reload_delay * 1000, lambda: reload_collection(callback), False)


def modify_collection(collection_operation, action_str='modifying collection', callback=None, callback_failure=False,
                      callback_delay=0, delay=30, attempt=1, max_attempts=5, **kwargs):
    passed = False
    retry = (
        "Will try again in %ds" % delay + ' (Attempt #%d)' % attempt if attempt > 0 else '') if attempt <= max_attempts else "Max attempts of %d exceeded... Aborting operation" % max_attempts
    try:
        return_val = collection_operation()
        passed = True
    except (sqlite.OperationalError, sqlite.ProgrammingError, Exception), e:
        if e.message.replace(".", "") == 'database is locked': friendly_message = 'sqlite database is locked'
        elif e.message == "Cannot operate on a closed database.": friendly_message = 'sqlite database is closed'
        else:
            if e.message.replace('.', '') == 'database is locked': log_error('**locked', crosspost='automation',
                                                                             crosspost_to_default=False)
            import traceback
            type = str(e.__class__);
            type = type[type.find("'") + 1:type.rfind("'")]
            friendly_message = ('Unhandled Error' if type == 'Exception' else type) + ':\n Full Error: ' + ' '.join(
                str(e).split()) + '\n Message: "%s"' % e.message + '\n Trace: ' + traceback.format_exc() + '\n'
        log_error("   > Modify Collection: Error %s: %s. %s" % (action_str, retry, friendly_message), time_out=10000,
                  do_show_tooltip=True, crosspost='automation', crosspost_to_default=False)
    if not passed: return (
        False if callback_failure is False else callback(None,
                                                         **kwargs)) if attempt > max_attempts else mw.progress.timer(
        delay * 1000,
        lambda: modify_collection(collection_operation, action_str, callback, callback_failure, callback_delay, delay,
                                  attempt + 1, **kwargs), False)
    if not callback: log("   > Modify Collection: Completed %s" % action_str, 'automation'); return
    log("   > Modify Collection: Completed %s" % action_str + ': %s Initiated' % (
        '%ds Callback Timer' % callback_delay if callback_delay > 0 else 'Callback'), 'automation')
    if not callback: return  # return_val
    if callback_delay > 0: mw.progress.timer(callback_delay * 1000, lambda: callback(return_val, **kwargs),
                                             False); return  # return return_val
    callback(return_val, **kwargs)
    # return return_val


def reload_collection(callback=None, reopen_delay=0, callback_delay=30, *args, **kwargs):
    if not mw.col is None:
        try:
            myDB = ankDB(True)
            db = myDB._db
            cur = db.execute("SELECT title FROM %s WHERE 1 ORDER BY RANDOM() LIMIT 1" % TABLES.EVERNOTE.NOTES)
            result = cur.fetchone()
            log(" > Reload Collection: Not needed: ankDB exists and cursor created: %s" % (str_safe(result[0])),
                'automation')
            if callback: callback(True)
            return True
        except (sqlite.ProgrammingError, Exception), e:
            if e.message == "Cannot operate on a closed database":
                # mw.loadCollection()
                log(" > Reloading Collection Check: DB is Closed. Proceed with reload. Col: " + str(mw.col),
                    'automation')
            else:
                import traceback
                log(" > Reloading Collection Check Failed : " + str(e) + '\n   - Trace: ' + traceback.format_exc(),
                    'automation')
    log(" > Initiating Reload: %sInitiated: %s" % (
        '%ds Timer ' % reopen_delay if reopen_delay > 0 else '', str(mw.col)), 'automation')
    # if callback and reopen_callback_delay > 0: 
    # log("Reload Collection: Callback Timer Set To %ds" % reopen_callback_delay, 'automation')
    # callback = lambda: mw.progress.timer(reopen_callback_delay*1000, callback, False)
    if reopen_delay > 0: return mw.progress.timer(reopen_delay * 1000,
                                                  lambda *xargs, **xkwargs: modify_collection(do_load_collection,
                                                                                              'reload collection',
                                                                                              lambda *xargs,
                                                                                                     **xkwargs: callback(
                                                                                                  *args, **kwargs),
                                                                                              callback_delay=callback_delay,
                                                                                              *args, **kwargs), False)
    modify_collection(do_load_collection, 'Reloading Collection', callback, callback_delay=callback_delay, *args,
                      **kwargs)


def do_load_collection():
    log("    > Do Load Collection: Attempting mw.loadCollection()", 'automation')
    mw.loadCollection()
    log("    > Do Load Collection: Attempting ankDB(True)", 'automation')
    ankDB(True)


def do_unload_collection():
    mw.unloadCollection()


def unload_collection(*args, **kwargs):
    log("Initiating Unload Collection:", 'automation')
    modify_collection(mw.unloadCollection, 'Unload Collection', *args, **kwargs)


def load_controller(callback=None, callback_failure=True, *args, **kwargs):
    # log('Col: ' + str(mw.col), 'automation')
    # log('Col db: ' + str(mw.col.db), 'automation')
    modify_collection(anknotes.Controller.Controller, 'Loading Controller', callback, callback_failure=callback_failure)
    # return anknotes.Controller.Controller()


def see_also(steps=None, showAlerts=None, validationComplete=False, controller=None):
    if controller is None:
        check = reload_collection()
        if check:
            log("See Also --> 2. Loading Controller", 'automation')
            callback = lambda x, *xargs, **xkwargs: see_also(steps, showAlerts, validationComplete, x)
            load_controller(callback)
        else:
            log("See Also --> 1. Loading Collection", 'automation')
            callback = lambda *xargs, **xkwargs: see_also(steps, showAlerts, validationComplete)
            reload_collection(callback)
        return False
    if not steps: steps = range(1, 10)
    if isinstance(steps, int): steps = [steps]
    steps = list(steps)
    log("See Also --> 3. Proceeding: " + ', '.join(map(str, steps)), 'automation')
    multipleSteps = (len(steps) > 1)
    if showAlerts is None: showAlerts = not multipleSteps
    remaining_steps = steps
    if 1 in steps:
        # Should be unnecessary once See Also algorithms are finalized
        log(" > See Also: Step 1:  Process Un Added See Also Notes", crosspost='automation')
        controller.process_unadded_see_also_notes()
    if 2 in steps:
        log(" > See Also: Step 2:  Create Auto TOC Evernote Notes", crosspost='automation')
        controller.create_auto_toc()
    if 3 in steps:
        if validationComplete:
            log(" > See Also: Step 3B: Validate and Upload Auto TOC Notes: Upload Validated Notes",
                crosspost='automation')
            upload_validated_notes(multipleSteps)
            validationComplete = False
        else: steps = [-3]
    if 4 in steps:
        log(" > See Also: Step 4:  Extract Links from TOC", crosspost='automation')
        controller.anki.extract_links_from_toc()
    if 5 in steps:
        log(" > See Also: Step 5:  Insert TOC/Outline Links Into Anki Notes' See Also Field", crosspost='automation')
        controller.anki.insert_toc_into_see_also()
    if 6 in steps:
        log(" > See Also: Step 6:  Update See Also Footer In Evernote Notes", crosspost='automation')
        from anknotes import detect_see_also_changes
        detect_see_also_changes.main()
    if 7 in steps:
        if validationComplete:
            log(" > See Also: Step 7B: Validate and Upload Modified Evernote Notes: Upload Validated Notes",
                crosspost='automation')
            upload_validated_notes(multipleSteps)
        else: steps = [-7]
    if 8 in steps:
        log(" > See Also: Step 8:  Insert TOC/Outline Contents Into Anki Notes", crosspost='automation')
        controller.anki.insert_toc_and_outline_contents_into_notes()

    do_validation = steps[0] * -1
    if do_validation > 0:
        log(" > See Also: Step %dA: Validate and Upload %s Notes: Validate Notes" % (
            do_validation, {3: 'Auto TOC', 7: 'Modified Evernote'}[do_validation]), crosspost='automation')
        remaining_steps = remaining_steps[remaining_steps.index(do_validation):]
        validate_pending_notes(showAlerts, callback=lambda *xargs, **xkwargs: see_also(remaining_steps, False, True))


def update_ancillary_data():
    controller = anknotes.Controller.Controller()
    log("Ancillary data - loaded controller - " + str(controller.evernote) + " - " + str(controller.evernote.client),
        'client')
    controller.update_ancillary_data()


def resync_with_local_db():
    controller = anknotes.Controller.Controller()
    controller.resync_with_local_db()


anknotes_checkable_menu_items = {}
