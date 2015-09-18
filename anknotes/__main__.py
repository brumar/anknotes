# -*- coding: utf-8 -*-
### Python Imports
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

### Anknotes Shared Imports
from anknotes.shared import *

### Anknotes Main Imports
from anknotes import menu, settings

### Evernote Imports

### Anki Imports
from anki.hooks import wrap, addHook
from aqt.preferences import Preferences
from aqt import mw, browser
# from aqt.qt import QIcon, QTreeWidget, QTreeWidgetItem
from aqt.qt import Qt, QIcon, QTreeWidget, QTreeWidgetItem
# from aqt.qt.Qt import MatchFlag
# from aqt.qt.qt import MatchFlag

def import_timer_toggle():
    title = "&Enable Auto Import On Profile Load"
    doAutoImport = mw.col.conf.get(
        SETTINGS.ANKNOTES_CHECKABLE_MENU_ITEMS_PREFIX + '_' + title.replace(' ', '_').replace('&', ''), False)
    if doAutoImport:
        lastImport = mw.col.conf.get(SETTINGS.EVERNOTE_LAST_IMPORT, None)
        importDelay = 0
        if lastImport:
            td = (datetime.now() - datetime.strptime(lastImport, ANKNOTES.DATE_FORMAT))
            minimum = timedelta(seconds=EVERNOTE.IMPORT_TIMER_INTERVAL / 1000)
            if td < minimum:
                importDelay = (minimum - td).total_seconds() * 1000
        if importDelay is 0:
            menu.import_from_evernote()
        else:
            m, s = divmod(importDelay / 1000, 60)
            log("> Starting Auto Import, Triggered by Profile Load, in %d:%02d min" % (m, s))
            mw.progress.timer(importDelay, menu.import_from_evernote, False)


def _findEdited((val, args)):
    try: days = int(val)
    except ValueError: return
    return "c.mod > %d" % (time.time() - days * 86400)

class CallbackItem(QTreeWidgetItem):
    def __init__(self, root, name, onclick, oncollapse=None):
        QTreeWidgetItem.__init__(self, root, [name])
        self.onclick = onclick
        self.oncollapse = oncollapse

def anknotes_browser_tagtree_wrap(self, root, _old):
    """

    :param root:
    :type root : QTreeWidget
    :param _old:
    :return:
    """
    tags = [(_("Edited This Week"), "view-pim-calendar.png", "edited:7")]
    for name, icon, cmd in tags:
        onclick = lambda c=cmd: self.setFilter(c)
        widgetItem = QTreeWidgetItem([name])
        widgetItem.onclick = onclick
        widgetItem.setIcon(0, QIcon(":/icons/" + icon))
        root = _old(self, root)
        indices = root.findItems(_("Added Today"), Qt.MatchFixedString)
        index = (root.indexOfTopLevelItem(indices[0]) + 1) if indices else 3
        root.insertTopLevelItem(index, widgetItem)
    return root

def anknotes_search_hook(search):
    if not 'edited' in search:
        search['edited'] = _findEdited

def anknotes_profile_loaded():
    menu.anknotes_load_menu_settings()
    if ANKNOTES.ENABLE_VALIDATION and ANKNOTES.AUTOMATE_VALIDATION:
        menu.upload_validated_notes(True)
    import_timer_toggle()
    '''
     For testing purposes only:
    '''
    if ANKNOTES.DEVELOPER_MODE_AUTOMATE:
        # resync_with_local_db()
        # menu.see_also()
        # menu.import_from_evernote(auto_page_callback=lambda: lambda: menu.see_also(3))
        # menu.see_also(3)
        # menu.see_also(4)
        # mw.progress.timer(20000, lambda : menu.find_deleted_notes(True), False)
        menu.see_also([3,4])
        pass


def anknotes_onload():
    addHook("profileLoaded", anknotes_profile_loaded)
    addHook("search", anknotes_search_hook)
    browser.Browser._systemTagTree = wrap(browser.Browser._systemTagTree, anknotes_browser_tagtree_wrap, "around")
    menu.anknotes_setup_menu()
    Preferences.setupOptions = wrap(Preferences.setupOptions, settings.setup_evernote)


anknotes_onload()
# log("Anki Loaded", "load")
