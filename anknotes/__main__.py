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
from aqt import mw


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


def anknotes_profile_loaded():
    log("Profile Loaded", "load")
    menu.anknotes_load_menu_settings()
    import_timer_toggle()
    '''
     For testing purposes only:
    '''
    if ANKNOTES.DEVELOPER_MODE_AUTOMATE:
        # resync_with_local_db()
        # menu.see_also()
        # menu.import_from_evernote(auto_page_callback=lambda: lambda: menu.see_also(3))
        menu.see_also(3)


def anknotes_onload():
    addHook("profileLoaded", anknotes_profile_loaded)
    menu.anknotes_setup_menu()
    Preferences.setupOptions = wrap(Preferences.setupOptions, settings.setup_evernote)


anknotes_onload()
log("Anki Loaded", "load")
