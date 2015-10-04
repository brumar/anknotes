# -*- coding: utf-8 -*-
### Python Imports
import os
import re, sre_constants
import sys

inAnki = 'anki' in sys.modules
try:
    from pysqlite2 import dbapi2 as sqlite

    is_pysqlite = True
except ImportError:
    from sqlite3 import dbapi2 as sqlite

    is_pysqlite = False
### Anknotes Shared Imports
from anknotes.shared import *
from anknotes import stopwatch

### Anknotes Main Imports
from anknotes import menu, settings

### Anki Imports
from anki.find import Finder
from anki.db import DB
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
    try: days = int(val)
    except ValueError: return
    return "c.mod > %d" % (time.time() - days * 86400)


def _findAnknotes((val, args)):
    tmr = stopwatch.Timer(label='finder\\findAnknotes', begin=False)
    log_banner("FINDANKNOTES SEARCH: " + val.upper().replace('_', ' '), tmr.label, append_newline=False, clear=False)
    if not hasattr(_findAnknotes, 'note_ids'): _findAnknotes.note_ids = {}
    if val == 'hierarchical' or val == 'hierarchical_alt':
        if val not in _findAnknotes.note_ids or not ANKNOTES.CACHE_SEARCHES:
            tmr.reset()
            val_root = val.replace('hierarchical', 'root')
            val_child = val.replace('hierarchical', 'child')
            _findAnknotes((val_root, None), );
            _findAnknotes((val_child, None), )
            _findAnknotes.note_ids[val] = _findAnknotes.note_ids[val_root] + _findAnknotes.note_ids[val_child]
            log("  > %s Search Complete: ".ljust(25) % val.upper().replace('_', ' ') + "%-5s --> %3d results" % (
                tmr.str_long, len(_findAnknotes.note_ids[val])), tmr.label)
            # return "c.nid IN (%s)" % ids2str(_findAnknotes.note_ids[val])

    if not hasattr(_findAnknotes, 'queries'):
        _findAnknotes.queries = {
            'all':        get_evernote_model_ids(True),
            'sub':        'n.sfld like "%:%"',
            'root_alt':   "n.sfld NOT LIKE '%:%' AND ank.title LIKE n.sfld || ':%'",
            'child_alt':  "n.sfld LIKE '%%:%%' AND UPPER(SUBSTR(n.sfld, 0, INSTR(n.sfld, ':'))) IN (SELECT UPPER(title) FROM %s WHERE title NOT LIKE '%%:%%' AND tagNames LIKE '%%,%s,%%') " % (
                TABLES.EVERNOTE.NOTES, TAGS.TOC),
            'orphan_alt': "n.sfld LIKE '%%:%%' AND UPPER(SUBSTR(n.sfld, 0, INSTR(n.sfld, ':'))) NOT IN (SELECT UPPER(title) FROM %s WHERE title NOT LIKE '%%:%%' AND tagNames LIKE '%%,%s,%%') " % (
                TABLES.EVERNOTE.NOTES, TAGS.TOC)
        }
        # _findAnknotes.queries['hierarchical'] = '(%s) OR (%s)' % (_findAnknotes.queries['root'], _findAnknotes.queries['child'])    

        # if not val in _findAnknotes.queries and not val in _findAnknotes.note_ids:
        # if val == 'child_alt' or val == 'root_alt':
        # if 'root_alt' not in _findAnknotes.note_ids:
        # tmr.reset()
        # _findAnknotes.note_ids['root_alt'] = get_anknotes_root_notes_nids()
        # log("  > Cached Root TOC Notes NIDs: ".ljust(25) + "%-5s --> %3d results" % (tmr.str_long, len(_findAnknotes.note_ids['root_alt'])), tmr.label)
        # if val == 'child_alt':
        # if  not in _findAnknotes.note_ids:
        # tmr.reset()
        # _findAnknotes.root_titles=["'%s'" % escape_text_sql(x.upper()) for x in get_evernote_title_from_nids(_findAnknotes.note_ids['root_alt'])]
        # log("  > Cached Root Titles: ".ljust(25) + "%-5s --> %3d results" % (val, tmr.str_long, len(_findAnknotes.root_titles)), tmr.label)
        # _findAnknotes.note_ids[val] =
        # _findAnknotes.queries['child_alt'] = "n.sfld LIKE '%%:%%' AND UPPER(SUBSTR(n.sfld, 0, INSTR(n.sfld, ':'))) IN (%s) " % ', '.join(_findAnknotes.root_titles)
        # elif val == 'root_alt':
        # pass
        # else: return None     
    if val not in _findAnknotes.note_ids or (not ANKNOTES.CACHE_SEARCHES and 'hierarchical' not in val):
        tmr.reset()
        if val == 'root':
            _findAnknotes.note_ids[val] = get_anknotes_root_notes_nids()
        elif val == 'child':
            _findAnknotes.note_ids[val] = get_anknotes_child_notes_nids()
        elif val == 'orphan':
            _findAnknotes.note_ids[val] = get_anknotes_orphan_notes_nids()
        elif val in _findAnknotes.queries:
            pred = _findAnknotes.queries[val]
            col = 'n.id'
            table = 'notes n'
            if 'ank.' in pred:
                col = 'DISTINCT ' + col
                table += ', %s ank' % TABLES.EVERNOTE.NOTES
            sql = 'select %s from %s where ' % (col, table) + pred
            _findAnknotes.note_ids[val] = ankDB().list(sql)
        else: return None
        log("  > Cached %s Note IDs: ".ljust(25) % val + "%-5s --> %3d results" % (
            tmr.str_long, len(_findAnknotes.note_ids[val])), tmr.label)
    else:
        log("  > Retrieving %3d %s Note IDs from Cache" % (len(_findAnknotes.note_ids[val]), val), tmr.label)
    log_blank(tmr.label)
    return "c.nid IN %s" % ids2str(_findAnknotes.note_ids[val])


class CallbackItem(QTreeWidgetItem):
    def __init__(self, root, name, onclick, oncollapse=None):
        QTreeWidgetItem.__init__(self, root, [name])
        self.onclick = onclick
        self.oncollapse = oncollapse


def anknotes_browser_get_icon(icon=None):
    if icon: return QIcon(":/icons/" + icon)
    if not hasattr(anknotes_browser_get_icon, 'default_icon'):
        from anknotes.graphics import icoEvernoteWeb
        anknotes_browser_get_icon.default_icon = icoEvernoteWeb
    return anknotes_browser_get_icon.default_icon


def anknotes_browser_add_treeitem(self, tree, name, cmd, icon=None, index=None, root=None):
    if root is None: root = tree
    onclick = lambda c=cmd: self.setFilter(c)
    if index:
        widgetItem = QTreeWidgetItem([_(name)])
        widgetItem.onclick = onclick
        widgetItem.setIcon(0, anknotes_browser_get_icon(icon))
        root.insertTopLevelItem(index, widgetItem)
        return root, tree
    item = self.CallbackItem(tree, _(name), onclick)
    item.setIcon(0, anknotes_browser_get_icon(icon))
    return root, tree


def anknotes_browser_add_tree(self, tree, items, root=None, name=None, icon=None):
    if root is None: root = tree
    for item in items:
        if isinstance(item[1], list):
            new_name = item[0]
            # log('Tree: Name: %s: \n' % str(new_name) + repr(item))            
            new_tree = self.CallbackItem(tree, _(new_name), None)
            new_tree.setExpanded(True)
            new_tree.setIcon(0, anknotes_browser_get_icon(icon))
            root = anknotes_browser_add_tree(self, new_tree, item[1], root, new_name, icon);
        else:
            # log('Tree Item: Name: %s: \n' % str(name) + repr(item))
            root, tree = anknotes_browser_add_treeitem(self, tree, *item, root=root)
    return root


def anknotes_browser_tagtree_wrap(self, root, _old):
    """

    :param root:
    :type root : QTreeWidget
    :param _old:
    :return:
    """
    root = _old(self, root)
    indices = root.findItems(_("Added Today"), Qt.MatchFixedString)
    index = (root.indexOfTopLevelItem(indices[0]) + 1) if indices else 3
    tags = \
        [
            ["Edited This Week", "edited:7", "view-pim-calendar.png", index],
            ["Anknotes",
             [
                 ["All Anknotes", "anknotes:all"],
                 ["Hierarchy",
                  [
                      ["All Hierarchical Notes", "anknotes:hierarchical"],
                      ["Root Notes", "anknotes:root"],
                      ["Sub Notes", "anknotes:sub"],
                      ["Child Notes", "anknotes:child"],
                      ["Orphan Notes", "anknotes:orphan"]
                  ]
                  ],
                 # ["Hierarchy: Alt",
                 # [
                 # ["All Hierarchical Notes", "anknotes:hierarchical_alt"],
                 # ["Root Notes", "anknotes:root_alt"],
                 # ["Child Notes", "anknotes:child_alt"],
                 # ["Orphan Notes", "anknotes:orphan_alt"]
                 # ]
                 # ],
                 ["Front Cards", "card:1"]
             ]
             ]
        ]

    return anknotes_browser_add_tree(self, root, tags)


def anknotes_finder_findCards_wrap(self, query, order=False, _old=None):
    tmr = stopwatch.Timer(label='finder\\findCards')
    log_banner("FINDCARDS SEARCH: " + query, tmr.label, append_newline=False, clear=False)
    tokens = self._tokenize(query)
    preds, args = self._where(tokens)
    log('Tokens: '.ljust(25) + ', '.join(tokens), tmr.label)
    if args: log('Args: '.ljust(25) + ', '.join(tokens), tmr.label)
    if preds is None:
        log('Preds: '.ljust(25) + '<NONE>', tmr.label)
        log_blank(tmr.label)
        return []
    line_prefix = ' > ' + ' ' * 7
    # pred_str = preds
    # pred_str = re.sub(r'(?si)\) (IN) \(',  r')\n      >   \1   (', pred_str)
    # pred_str = re.sub(r'(?si)\) (OR|AND) \(',  r')\n  >   \1   (', pred_str)
    # log('Preds: '.ljust(25) + pred_str , tmr.label)

    order, rev = self._order(order)
    sql = self._query(preds, order)
    # pred_str = sql
    # pred_str = re.sub(r'(?si)\) (IN) \(',  r')\n      >   \1   (', pred_str)
    # pred_str = re.sub(r'(?si)(FROM|WHERE|ORDER|SELECT)',  r'\n>  \1  ', pred_str)
    # pred_str = re.sub(r'(?si)\) (OR|AND) \(',  r')\n  >   \1   (', pred_str)
    # log('SQL: '.ljust(25) + pred_str , tmr.label)    
    # log('SQL: '.ljust(25) + pred_str , 'finder\\findCards')    
    # showInfo(sql)
    try:
        res = self.col.db.list(sql, *args)
    except Exception as ex:
        # invalid grouping
        log_error("Error with findCards Query %s: %s.\n%s" % (query, str(ex), [sql, args]), crosspost=tmr.label)
        return []
    if rev:
        res.reverse()
    log("FINDCARDS DONE: ".ljust(25) + "%-5s --> %3d results" % (tmr.str_long, len(res)), tmr.label)
    log_blank(tmr.label)
    return res
    return _old(self, query, order)


def anknotes_finder_query_wrap(self, preds=None, order=None, _old=None):
    if _old is None or not isinstance(self, Finder):
        log_dump([self, preds, order], 'Finder Query Wrap Error', 'finder\\error', crosspost_to_default=False)
        return
    sql = _old(self, preds, order)
    if "ank." in preds:
        sql = sql.replace("select c.id", "select distinct c.id").replace("from cards c",
                                                                         "from cards c, %s ank" % TABLES.EVERNOTE.NOTES)
        log('Custom anknotes finder SELECT query: \n%s' % sql, 'finder\\ank-query')
    elif TABLES.EVERNOTE.NOTES in preds:
        log('Custom anknotes finder alternate query: \n%s' % sql, 'finder\\ank-query')
    else:
        log("Anki finder query: %s" % sql[:100], 'finder\\query')
    return sql


def anknotes_search_hook(search):
    anknotes_search = {'edited': _findEdited, 'anknotes': _findAnknotes}
    for key, value in anknotes_search.items():
        if key not in search: search[key] = anknotes_search[key]
        # search = anknotes_search


def reset_everything():
    ankDB().InitSeeAlso(True)
    menu.resync_with_local_db()
    menu.see_also([1, 2, 4, 5, 6, 8])


def anknotes_profile_loaded():
    if not os.path.exists(os.path.dirname(FILES.USER.LAST_PROFILE_LOCATION)): os.makedirs(
        os.path.dirname(FILES.USER.LAST_PROFILE_LOCATION))
    with open(FILES.USER.LAST_PROFILE_LOCATION, 'w+') as myFile:
        print>> myFile, mw.pm.name
    menu.anknotes_load_menu_settings()
    if EVERNOTE.UPLOAD.VALIDATION.ENABLED and EVERNOTE.UPLOAD.VALIDATION.AUTOMATED: menu.upload_validated_notes(True)
    import_timer_toggle()

    if ANKNOTES.DEVELOPER_MODE.AUTOMATED:
        '''
         For testing purposes only!
         Add a function here and it will automatically run on profile load
         You must create the files 'anknotes.developer' and 'anknotes.developer.automate' in the /extra/dev/ folder
        '''
        reset_everything()
        return
        # menu.see_also(set(range(0,10)) - {3,4,8})
        ankDB().InitSeeAlso(True)
        # menu.resync_with_local_db()
        menu.see_also([1, 2, 6, 7, 9])
        menu.lxml_test()
        # menu.see_also()
        # reset_everything()
        # menu.see_also([7])

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

def anknotes_scalar(self, *a, **kw):
    log('Call to DB.scalar(). Self should be instance of cursor: %s\n   - Self:   %s\n   - Args:   %s\n   - KWArgs: %s' % (str(type(self)), pf(self), pf(a), pf(kw)), 'sql\\scalar')
    last_query = self.ank_lastquery if hasattr(self, 'ank_lastquery') else '<None>'
    try:
        res = self.execute(*a, **kw)
    except TypeError:
        log(" > ERROR with scalar while executing query: " + str(e), 'sql\\scalar') 
        log(" >  LAST QUERY: " + last_query, 'sql\\scalar') 
        raise 
    log(' > Result: %s' % pf(res), 'sql\\scalar')    
    try:
        res = res.fetchone()
    except TypeError:
        log(" > ERROR with scalar while fetching result: " + str(e), 'sql\\scalar') 
        log(" >  LAST QUERY: " + last_query, 'sql\\scalar') 
        raise     
    if res:
        return res[0]
    return None        
    
def anknotes_execute(self, sql, *a, **ka):
    log('Call to DB.execute(). Self should be instance of cursor: %s\n   - Self:   %s\n   - SQL:    %s\n   - Args:   %s\n   - KWArgs: %s' % (str(type(self)), pf(self), pf(sql), pf(a), pf(kw)), 'sql\\execute')
    self.ank_lastquery = sql     

def anknotes_onload():
    global inAnki
    addHook("profileLoaded", anknotes_profile_loaded)
    addHook("search", anknotes_search_hook)
    rm_log_path('sql\\')
    if inAnki:
        DB.scalar = anknotes_scalar # wrap(DB.scalar, anknotes_scalar, "before")
        DB.execute = wrap(DB.execute, anknotes_scalar, "before")
    Finder._query = wrap(Finder._query, anknotes_finder_query_wrap, "around")
    Finder.findCards = wrap(Finder.findCards, anknotes_finder_findCards_wrap, "around")
    browser.Browser._systemTagTree = wrap(browser.Browser._systemTagTree, anknotes_browser_tagtree_wrap, "around")
    menu.anknotes_setup_menu()
    Preferences.setupOptions = wrap(Preferences.setupOptions, settings.setup_evernote)


anknotes_onload()
# log("Anki Loaded", "load")
