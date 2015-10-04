# -*- coding: utf-8 -*-
### Python Imports
import os
import re
import sre_constants

try:
    from pysqlite2 import dbapi2 as sqlite

    is_pysqlite = True
except ImportError:
    from sqlite3 import dbapi2 as sqlite

    is_pysqlite = False
### Anknotes Shared Imports
from anknotes.shared import *

### Anknotes Main Imports
from anknotes import menu, settings

### Evernote Imports

### Anki Imports
from anki.find import Finder
from anki.hooks import wrap, addHook
from aqt.preferences import Preferences
from aqt import mw, browser
# from aqt.qt import QIcon, QTreeWidget, QTreeWidgetItem
from aqt.qt import Qt, QIcon, QTreeWidget, QTreeWidgetItem, QDesktopServices, QUrl
from aqt.webview import AnkiWebView
from anki.utils import ids2str, splitFields
# from aqt.qt.Qt import MatchFlag
# from aqt.qt.qt import MatchFlag

def import_timer_toggle():
    title = "&Enable Auto Import On Profile Load"
    doAutoImport = mw.col.conf.get(
        SETTINGS.ANKNOTES_CHECKABLE_MENU_ITEMS_PREFIX + '_' + title.replace(' ', '_').replace('&', ''), False)
    if not doAutoImport: return
    lastImport = mw.col.conf.get(SETTINGS.EVERNOTE.LAST_IMPORT, None)
    importDelay = 0
    if lastImport:
        td = (datetime.now() - datetime.strptime(lastImport, ANKNOTES.DATE_FORMAT))
        minimum = timedelta(seconds=max(EVERNOTE.IMPORT.INTERVAL, 20 * 60))
        if td < minimum:
            importDelay = (minimum - td).total_seconds() * 1000
    if importDelay is 0:
        menu.import_from_evernote()
    else:
        m, s = divmod(importDelay / 1000, 60)
        log("> Starting Auto Import, Triggered by Profile Load, in %d:%02d min" % (m, s))
        mw.progress.timer(importDelay, menu.import_from_evernote, False)


def _findEdited((val, args)):
    try:
        days = int(val)
    except ValueError:
        return
    return "c.mod > %d" % (time.time() - days * 86400)


def _findHierarchy((val, args)):
    if val == 'root':
        return "n.sfld NOT LIKE '%:%' AND ank.title LIKE '%' || n.sfld || ':%'"
    if val == 'sub':
        return 'n.sfld like "%:%"'
    if val == 'child':
        return "UPPER(SUBSTR(n.sfld, 0, INSTR(n.sfld, ':'))) IN (SELECT UPPER(title) FROM %s WHERE title NOT LIKE '%%:%%' AND tagNames LIKE '%%,%s,%%') " % (
        TABLES.EVERNOTE.NOTES, TAGS.TOC)
    if val == 'orphan':
        return "n.sfld LIKE '%%:%%' AND UPPER(SUBSTR(n.sfld, 0, INSTR(n.sfld, ':'))) NOT IN (SELECT UPPER(title) FROM %s WHERE title NOT LIKE '%%:%%' AND tagNames LIKE '%%,%s,%%') " % (
        TABLES.EVERNOTE.NOTES, TAGS.TOC)
    # showInfo(val)


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
    tags = [
        (_("Edited This Week"), "view-pim-calendar.png", "edited:7"),
        (_("Root Notes"), "hierarchy:root"),
        (_("Sub Notes"), "hierarchy:sub"),
        (_("Child Notes"), "hierarchy:child"),
        (_("Orphan Notes"), "hierarchy:orphan")
    ]
    # tags.reverse()
    root = _old(self, root)
    indices = root.findItems(_("Added Today"), Qt.MatchFixedString)
    index = (root.indexOfTopLevelItem(indices[0]) + 1) if indices else 3
    from anknotes.graphics import icoEvernoteWeb

    for name, icon, cmd in tags[:1]:
        onclick = lambda c=cmd: self.setFilter(c)
        widgetItem = QTreeWidgetItem([name])
        widgetItem.onclick = onclick
        widgetItem.setIcon(0, QIcon(":/icons/" + icon))
        root.insertTopLevelItem(index, widgetItem)
    root = self.CallbackItem(root, _("Anknotes Hierarchy"), None)
    root.setExpanded(True)
    root.setIcon(0, icoEvernoteWeb)
    for name, cmd in tags[1:]:
        item = self.CallbackItem(root, name, lambda c=cmd: self.setFilter(c))
        item.setIcon(0, icoEvernoteWeb)
    return root


def _findField(self, field, val, _old=None):
    def doCheck(self, field, val):
        field = field.lower()
        val = val.replace("*", "%")
        # find models that have that field
        mods = {}
        for m in self.col.models.all():
            for f in m['flds']:
                if f['name'].lower() == field:
                    mods[str(m['id'])] = (m, f['ord'])

        if not mods:
            # nothing has that field
            return
        # gather nids

        regex = re.escape(val).replace("\\_", ".").replace("\\%", ".*")
        sql = """
select id, mid, flds from notes
where mid in %s and flds like ? escape '\\'""" % (
        ids2str(mods.keys()))
        nids = []
        for (id, mid, flds) in self.col.db.execute(sql, "%" + val + "%"):
            flds = splitFields(flds)
            ord = mods[str(mid)][1]
            strg = flds[ord]
            try:
                if re.search("(?si)^" + regex + "$", strg): nids.append(id)
            except sre_constants.error:
                return
        if not nids: return "0"
        return "n.id in %s" % ids2str(nids)

    # val = doCheck(field, val)
    vtest = doCheck(self, field, val)
    log("FindField for %s: %s: Total %d matches " % (field, str(val), len(vtest.split(','))), 'sql-finder')
    return vtest


# return _old(self, field, val)

def anknotes_finder_findCards_wrap(self, query, order=False, _old=None):
    log("Searching with text " + query, 'sql-finder')
    "Return a list of card ids for QUERY."
    tokens = self._tokenize(query)
    preds, args = self._where(tokens)
    log("Tokens: %-20s Preds: %-20s Args: %-20s " % (str(tokens), str(preds), str(args)), 'sql-finder')
    if preds is None:
        return []
    order, rev = self._order(order)
    sql = self._query(preds, order)
    # showInfo(sql)
    try:
        res = self.col.db.list(sql, *args)
    except Exception as ex:
        # invalid grouping
        log("Error with query %s: %s.\n%s" % (query, str(ex), [sql, args]), 'sql-finder')
        return []
    if rev:
        res.reverse()
    return res
    return _old(self, query, order)


def anknotes_finder_query_wrap(self, preds=None, order=None, _old=None):
    if _old is None or not isinstance(self, Finder):
        log_dump([self, preds, order], 'Finder Query Wrap Error', 'finder')
        return
    sql = _old(self, preds, order)
    if "ank." in preds:
        sql = sql.replace("select c.id", "select distinct c.id").replace("from cards c",
                                                                         "from cards c, %s ank" % TABLES.EVERNOTE.NOTES)
        log('Custom anknotes finder SELECT query: \n%s' % sql, 'sql-finder')
    elif TABLES.EVERNOTE.NOTES in preds:
        log('Custom anknotes finder alternate query: \n%s' % sql, 'sql-finder')
    else:
        log("Anki finder query: %s" % sql, 'sql-finder')
    return sql


def anknotes_search_hook(search):
    if not 'edited' in search:
        search['edited'] = _findEdited
    if not 'hierarchy' in search:
        search['hierarchy'] = _findHierarchy


def reset_everything():
    ankDB().InitSeeAlso(True)
    menu.resync_with_local_db()
    menu.see_also([1, 2, 5, 6, 7])


def anknotes_profile_loaded():
    if not os.path.exists(os.path.dirname(FILES.USER.LAST_PROFILE_LOCATION)): os.makedirs(
        os.path.dirname(FILES.USER.LAST_PROFILE_LOCATION))
    with open(FILES.USER.LAST_PROFILE_LOCATION, 'w+') as myFile:
        print >> myFile, mw.pm.name
    menu.anknotes_load_menu_settings()
    if EVERNOTE.UPLOAD.VALIDATION.ENABLED and EVERNOTE.UPLOAD.VALIDATION.AUTOMATED:
        menu.upload_validated_notes(True)
    import_timer_toggle()

    if ANKNOTES.DEVELOPER_MODE.AUTOMATED:
        '''
         For testing purposes only!
         Add a function here and it will automatically run on profile load
         You must create the files 'anknotes.developer' and 'anknotes.developer.automate' in the /extra/dev/ folder
        '''
        # reset_everything()
        menu.see_also([7])

        # menu.resync_with_local_db()
        # menu.see_also([1, 2, 5, 6, 7])
        # menu.see_also([6, 7])
        # menu.resync_with_local_db()
        # menu.see_also()
        # menu.import_from_evernote(auto_page_callback=lambda: lambda: menu.see_also(3))
        # menu.see_also(3)
        # menu.see_also(4)
        # mw.progress.timer(20000, lambda : menu.find_deleted_notes(True), False)
        # menu.see_also([3,4])
        # menu.resync_with_local_db()
        pass


def anknotes_onload():
    addHook("profileLoaded", anknotes_profile_loaded)
    addHook("search", anknotes_search_hook)
    Finder._query = wrap(Finder._query, anknotes_finder_query_wrap, "around")
    Finder._findField = wrap(Finder._findField, _findField, "around")
    Finder.findCards = wrap(Finder.findCards, anknotes_finder_findCards_wrap, "around")
    browser.Browser._systemTagTree = wrap(browser.Browser._systemTagTree, anknotes_browser_tagtree_wrap, "around")
    menu.anknotes_setup_menu()
    Preferences.setupOptions = wrap(Preferences.setupOptions, settings.setup_evernote)


anknotes_onload()
# log("Anki Loaded", "load")
