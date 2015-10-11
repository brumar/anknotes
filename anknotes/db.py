### For PyCharm code completion
# import sqlite3

### Python Imports
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite
import time
from datetime import datetime
from copy import copy
import os
import sys

inAnki = 'anki' in sys.modules

### Anki Shared Imports
from anknotes.constants import *
from anknotes.base import is_str_type, item_to_list, fmt
from anknotes.args import Args
from anknotes.logging import log_sql, log, log_error, log_blank, pf
from anknotes.dicts import DictCaseInsensitive

### For PyCharm code completion
# from anknotes import _sqlite3

if inAnki:
    from aqt import mw
    from anki.utils import ids2str, splitFields

ankNotesDBInstance = None
dbLocal = False

lastHierarchyUpdate = datetime.now()


def anki_profile_path_root():
    return os.path.abspath(os.path.join(os.path.dirname(PATH), '..' + os.path.sep))


def last_anki_profile_name():
    root = anki_profile_path_root()
    name = ANKI.PROFILE_NAME
    if name and os.path.isdir(os.path.join(root, name)):
        return name
    if os.path.isfile(FILES.USER.LAST_PROFILE_LOCATION):
        name = file(FILES.USER.LAST_PROFILE_LOCATION, 'r').read().strip()
        if name and os.path.isdir(os.path.join(root, name)):
            return name
    dirs = [x for x in os.listdir(root) if os.path.isdir(os.path.join(root, x)) and x is not 'addons']
    if not dirs:
        return ""
    return dirs[0]


def ankDBSetLocal():
    global dbLocal
    dbLocal = True


def ankDBIsLocal():
    global dbLocal
    return dbLocal


def ankDB(table=None,reset=False):
    global ankNotesDBInstance, dbLocal
    if not ankNotesDBInstance or reset:
        path = None
        if dbLocal:
            path = os.path.abspath(os.path.join(anki_profile_path_root(), last_anki_profile_name(), 'collection.anki2'))
        ankNotesDBInstance = ank_DB(path)
    if table:
        db_copy = ank_DB(init_db=False, table=table)
        db_copy._db = ankNotesDBInstance._db
        db_copy._path = ankNotesDBInstance._path
        return db_copy
    return ankNotesDBInstance


def escape_text_sql(title):
    return title.replace("'", "''")


def delete_anki_notes_and_cards_by_guid(evernote_guids):
    data = [[FIELDS.EVERNOTE_GUID_PREFIX + x] for x in evernote_guids]
    db = ankDB()
    db.executemany("DELETE FROM cards WHERE nid in (SELECT id FROM notes WHERE flds LIKE  ? || '%')", data)
    db.executemany("DELETE FROM notes WHERE flds LIKE ? || '%'", data)


def get_evernote_title_from_guid(guid):
    return ankDB().scalar("SELECT title FROM {n} WHERE guid = '%s'" % guid)


def get_evernote_titles_from_nids(nids):
    return get_evernote_titles(nids, 'nid')


def get_evernote_titles(guids, column='guid'):
    return ankDB().list("SELECT title FROM {n} WHERE %s IN (%s) ORDER BY title ASC" %
                        (column, ', '.join(["'%s'" % x for x in guids])))


def get_anki_deck_id_from_note_id(nid):
    return long(ankDB().scalar("SELECT did FROM cards WHERE nid = ? LIMIT 1", nid))


def get_anki_fields_from_evernote_guids(guids):
    lst = isinstance(guids, list)
    if not lst:
        guids = [guids]
    db = ankDB()
    results = [db.scalar("SELECT flds FROM notes WHERE flds LIKE '{guid_prefix}' || ? || '%'", guid) for guid in guids]
    if not lst:
        return results[0] if results else None
    return results

def get_anki_card_ids_from_evernote_guids(guids, sql=None):
    pred = "n.flds LIKE '%s' || ? || '%%'" % FIELDS.EVERNOTE_GUID_PREFIX
    if sql is None:
        sql = "SELECT c.id FROM cards c, notes n WHERE c.nid = n.id AND ({pred})"
    return execute_sqlite_query(sql, guids, pred=pred)


def get_anki_note_id_from_evernote_guid(guid):
    return ankDB().scalar("SELECT n.id FROM notes n WHERE n.flds LIKE '%s' || ? || '%%'" % FIELDS.EVERNOTE_GUID_PREFIX,
                          guid)


def get_anki_note_ids_from_evernote_guids(guids):
    return get_anki_card_ids_from_evernote_guids(guids, "SELECT n.id FROM notes n WHERE {pred}")


def get_paired_anki_note_ids_from_evernote_guids(guids):
    return get_anki_card_ids_from_evernote_guids([[x, x] for x in guids],
                                                 "SELECT n.id, n.flds FROM notes n WHERE {pred}")


def get_anknotes_root_notes_nids():
    return get_cached_data(get_anknotes_root_notes_nids, lambda: get_anknotes_root_notes_guids('nid'))


def get_cached_data(func, data_generator, subkey=''):
    if not ANKNOTES.CACHE_SEARCHES:
        return data_generator()
    if subkey:
        subkey += '_'
    if not hasattr(func, subkey + 'data') or getattr(func, subkey + 'update') < lastHierarchyUpdate:
        setattr(func, subkey + 'data', data_generator())
        setattr(func, subkey + 'update', datetime.now())
    return getattr(func, subkey + 'data')


def get_anknotes_root_notes_guids(column='guid', tag=None):
    sql = "SELECT %s FROM {n} WHERE UPPER(title) IN {pred}" % column
    data_key = column
    if tag:
        sql += " AND tagNames LIKE '%%,%s,%%'" % tag; data_key += '-' + tag

    def cmd():
        titles = get_anknotes_potential_root_titles(upper_case=False, encode=False)
        return execute_sqlite_in_query(sql, titles, pred='UPPER(?)')
    return get_cached_data(get_anknotes_root_notes_guids, cmd, data_key)


def get_anknotes_root_notes_titles():
    return get_cached_data(get_anknotes_root_notes_titles,
                           lambda: get_evernote_titles(get_anknotes_root_notes_guids()))


def get_anknotes_potential_root_titles(upper_case=False, encode=False, **kwargs):
    global generateTOCTitle
    from anknotes.EvernoteNoteTitle import generateTOCTitle
    def mapper(x): return generateTOCTitle(x)
    if upper_case:
        mapper = lambda x, f=mapper: f(x).upper()
    if encode:
        mapper = lambda x, f=mapper: f(x).encode('utf-8')
    data = get_cached_data(get_anknotes_potential_root_titles, lambda: ankDB().list(
        "SELECT DISTINCT SUBSTR(title, 0, INSTR(title, ':')) FROM {n} WHERE title LIKE '%:%'"))
    return map(mapper, data)


# def __get_anknotes_root_notes_titles_query(): 
# return '(%s)' % ' OR '.join(["title LIKE '%s'" % (escape_text_sql(x) + ':%') for x in get_anknotes_root_notes_titles()])

def __get_anknotes_root_notes_pred(base=None, column='guid', **kwargs):
    if base is None:
        base = "SELECT %(column)s FROM %(table)s WHERE {pred} "
    base = base % {'column': column, 'table': TABLES.EVERNOTE.NOTES}
    pred = "title LIKE ? || ':%'"
    return execute_sqlite_query(base, get_anknotes_root_notes_titles(), pred=pred)


def execute_sqlite_in_query(sql, data, in_query=True, **kwargs):
    return execute_sqlite_query(sql, data, in_query=True, **kwargs)


def execute_sqlite_query(sql, data, in_query=False, **kwargs):
    queries = generate_sqlite_in_predicate(data, **kwargs) if in_query else generate_sqlite_predicate(data, **kwargs)
    results = []
    db = ankDB()
    for query, data in queries:
        sql = fmt(sql, pred=query)
        result = db.list(sql, *data)
        log_sql('FROM execute_sqlite_query ' + sql,
                ['Data [%d]: ' % len(data), data,result[:3]])
        results += result
    return results


def generate_sqlite_predicate(data, pred='?', pred_delim=' OR ', query_base='(%s)', max_round=990):
    if not query_base:
        query_base = '%s'
    length = len(data)
    rounds = float(length) / max_round
    rounds = int(rounds) + 1 if int(rounds) < rounds else 0
    queries = []
    for i in range(0, rounds):
        start = max_round * i
        end = min(length, start + max_round)
        # log_sql('FROM generate_sqlite_predicate ' + query_base, ['gen sql #%d of %d: %d-%d' % (i, rounds, start, end) , pred_delim, 'Data [%d]: ' % len(data), data[:3]])
        queries.append([query_base % (pred + (pred_delim + pred) * (end - start - 1)), data[start:end]])
    return queries


def generate_sqlite_in_predicate(data, pred='?', pred_delim=', ', query_base='(%s)'):
    return generate_sqlite_predicate(data, pred=pred, query_base=query_base, pred_delim=pred_delim)


def get_sql_anki_cids_from_evernote_guids(guids):
    return "c.nid IN " + ids2str(get_anki_note_ids_from_evernote_guids(guids))


def get_anknotes_child_notes_nids(**kwargs):
    if 'column' in kwargs:
        del kwargs['column']
    return get_anknotes_child_notes(column='nid', **kwargs)


def get_anknotes_child_notes(column='guid', **kwargs):
    return get_cached_data(get_anknotes_child_notes, lambda: __get_anknotes_root_notes_pred(column=column, **kwargs),
                           column)


def get_anknotes_orphan_notes_nids(**kwargs):
    if 'column' in kwargs:
        del kwargs['column']
    return get_anknotes_orphan_notes(column='nid', **kwargs)


def get_anknotes_orphan_notes(column='guid', **kwargs):
    return get_cached_data(get_anknotes_orphan_notes, lambda: __get_anknotes_root_notes_pred(
        "SELECT %(column)s FROM %(table)s WHERE title LIKE '%%:%%' AND NOT {pred}", column=column, **kwargs), column)


def get_evernote_guid_from_anki_fields(fields):
    if isinstance(fields, dict):
        if not FIELDS.EVERNOTE_GUID in fields:
            return None
        return fields[FIELDS.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')
    if is_str_type(fields):
        fields = splitFields(fields)
        return fields[FIELDS.ORD.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')


def get_all_local_db_guids(filter=None):
    if filter is None:
        filter = "1"
    return ankDB().list("SELECT guid FROM {n} WHERE %s ORDER BY title ASC" % filter)


def get_evernote_model_ids(sql=False):
    if not hasattr(get_evernote_model_ids, 'model_ids'):
        from anknotes.Anki import Anki
        anki = Anki()
        anki.add_evernote_models(allowForceRebuild=False)
        get_evernote_model_ids.model_ids = anki.evernoteModels
        del anki
        del Anki
    if sql:
        return 'n.mid IN (%s)' % ', '.join(get_evernote_model_ids.model_ids.values())
    return get_evernote_model_ids.model_ids


def update_anknotes_nids():
    db = ankDB()
    count = db.count('nid <= 0')
    if not count:
        return count 
    paired_data = db.all("SELECT n.id, n.flds FROM notes n WHERE " + get_evernote_model_ids(True))
    paired_data = [[nid, get_evernote_guid_from_anki_fields(flds)] for nid, flds in paired_data]
    db.executemany('UPDATE {n} SET nid = ? WHERE guid = ?', paired_data)
    db.commit()
    return count 


class ank_DB(object):
    echo = False

    def __init__(self, path=None, text=None, timeout=0, init_db=True, table=None):
        self._table_ = table
        self.ankdb_lastquery = None
        self.echo = False
        if not init_db:
            return
        encpath = path
        if isinstance(encpath, unicode):
            encpath = path.encode("utf-8")
        if path:
            log('Creating local ankDB instance from path: ' + path, 'sql\\ankDB')
            self._db = sqlite.connect(encpath, timeout=timeout)
            self._db.row_factory = sqlite.Row
            if text:
                self._db.text_factory = text
            self._path = path
        else:
            log('Creating local ankDB instance from Anki DB instance at: ' + mw.col.db._path, 'sql\\ankDB')
            self._db = mw.col.db._db
            """
            :type : sqlite.Connection
            """
            self._db.row_factory = sqlite.Row
            self._path = mw.col.db._path
        # self._db = self._get_db_(**kw)

    @property
    def table(self):
        return self._table_ if self._table_ else TABLES.EVERNOTE.NOTES

    def setrowfactory(self):
        self._db.row_factory = sqlite.Row

    def drop(self, table):
        self.execute("DROP TABLE IF EXISTS " + table)

    @staticmethod
    def _is_stmt_(sql, stmts=None):
        s = sql.strip().lower()
        stmts = ["insert", "update", "delete", "drop", "create", "replace"] + item_to_list(stmts)
        for stmt in stmts:
            if s.startswith(stmt):
                return True
        return False

    def update(self, sql=None, *a, **ka):
        if 'where' in ka:
            ka['columns'] = sql
            sql = None
        if sql is None:
            sql = '{columns} WHERE {where}'
        sql = "UPDATE {t} SET " + sql
        self.execute(sql, a, ka)

    def delete(self, sql, *a, **ka):
        sql = "DELETE FROM {t} WHERE " + sql
        self.execute(sql, a, ka)

    def insert(self, auto, replace_into=False, **kw):
        keys = auto.keys()
        values = [":%s" % key for key in keys]
        keys = ["'%s'" % key for key in keys]
        sql = 'INSERT%s INTO {t}(%s) VALUES(%s)' % (' OR REPLACE' if replace_into else '',
                                                    ', '.join(keys), ', '.join(values))
        self.execute(sql, auto=auto, kw=kw)

    def insert_or_replace(self, *a, **kw):
        kw['replace_into'] = True
        self.insert(*a, **kw)

    def execute(self, sql, a=None, kw=None, auto=None, **kwargs):
        if isinstance(a, dict) or isinstance(a, DictCaseInsensitive):
            kw, a = a, kw
        if not isinstance(a, list) and not isinstance(a, tuple):
            a = item_to_list(a)
        if isinstance(sql, dict) or isinstance(sql, DictCaseInsensitive):
            auto = sql
            sql = ' AND '.join(["`{0}` = :{0}".format(key) for key in auto.keys()])
        if kw is None:
            kw = {}
        kwargs.update(kw)
        sql = self._fmt_query_(sql, **kwargs)
        if auto:
            kw = auto
        log_sql(sql, a, kw, self=self)
        self.ankdb_lastquery = sql
        if self._is_stmt_(sql):
            self.mod = True
        t = time.time()
        try:
            if a:
                # execute("...where id = ?", 5)
                res = self._db.execute(sql, a)
            elif kw:
                # execute("...where id = :id", id=5)
                res = self._db.execute(sql, kw)
            else:
                res = self._db.execute(sql)
        except (sqlite.OperationalError, sqlite.ProgrammingError, sqlite.Error, Exception) as e:
            log_sql(sql, a, kw, self=self, filter_disabled=False)
            import traceback
            log_error('Error with ankDB().execute(): %s\n Query: %s\n Trace: %s' %
                      (str(e), sql, traceback.format_exc()))
            raise
        if self.echo:
            # print a, ka
            print sql, "%0.3fms" % ((time.time() - t) * 1000)
            if self.echo == "2":
                print a, kw
        return res

    def _fmt_query_(self, sql, **kw):
        if not self._is_stmt_(sql, 'select'):
            sql = 'SELECT {columns} FROM {t} WHERE ' + sql
        formats = dict(table=self.table, where='1', columns='*')
        override = dict(n=TABLES.EVERNOTE.NOTES, s=TABLES.SEE_ALSO, a=TABLES.TOC_AUTO,
                        nv=TABLES.NOTE_VALIDATION_QUEUE, nb=TABLES.EVERNOTE.NOTEBOOKS, tt=TABLES.EVERNOTE.TAGS,
                        t_toc='%%,%s,%%' % TAGS.TOC, t_tauto='%%,%s,%%' % TAGS.TOC_AUTO,
                        t_out='%%,%s,%%' % TAGS.OUTLINE, anki_guid='{guid_prefix}{guid}%',
                        guid_prefix=FIELDS.EVERNOTE_GUID_PREFIX)
        keys = formats.keys()
        formats.update(kw)
        formats['t'] = formats['table']
        formats.update(override)        
        sql = fmt(sql, formats)
        if 'order' in kw and 'order by' not in sql.lower():
            sql += ' ORDER BY ' + kw['order']
            del kw['order']
        for key in keys:
            if key in kw:
                del kw[key]
        return sql

    def executemany(self, sql, data, **kw):
        sql = self._fmt_query_(sql, **kw)
        log_sql(sql, data, self=self)
        self.mod = True
        t = time.time()
        try:
            self._db.executemany(sql, data)
        except (sqlite.OperationalError, sqlite.ProgrammingError, sqlite.Error, Exception) as e:
            log_sql(sql, data, self=self, filter_disabled=False)
            import traceback
            log_error('Error with ankDB().executemany(): %s\n Query: %s\n Trace: %s' % (str(e), sql, traceback.format_exc()))
            raise
        if self.echo:
            print sql, "%0.3fms" % ((time.time() - t) * 1000)
            if self.echo == "2":
                print data

    def commit(self):
        t = time.time()
        self._db.commit()
        if self.echo:
            print "commit %0.3fms" % ((time.time() - t) * 1000)

    def executescript(self, sql):
        self.mod = True
        if self.echo:
            print sql
        self._db.executescript(sql)

    def rollback(self):
        self._db.rollback()

    def exists(self, *a, **kw):
        count = self.count(*a, **kw)
        return count is not None and count > 0

    def count(self, *a, **kw):
        return self.scalar('SELECT COUNT(*) FROM {t} WHERE {where}', *a, **kw)
        
    def scalar(self, sql='1', *a, **kw):
        log_text = 'Call to DB.ankdb_scalar():'
        if not isinstance(self, ank_DB): 
            log_text += '\n   - Self:       ' + pf(self)
        if a:
            log_text += '\n   - Args:       ' + pf(a)
        if kw:
            log_text += '\n   - KWArgs:     ' + pf(kw)    
        last_query='<None>'
        if hasattr(self, 'ankdb_lastquery'):
            last_query = self.ankdb_lastquery
            if is_str_type(last_query):
                last_query = last_query[:50]
            else:
                last_query = pf(last_query)
            log_text += '\n   - Last Query: ' + last_query
        log(log_text + '\n', 'sql\\ankdb_scalar')    
        try:
            res = self.execute(sql, a, kw)
        except TypeError as e:
            log(" > ERROR with ankdb_scalar while executing query: %s\n >  LAST QUERY: %s" % (str(e), last_query), 'sql\\ankdb_scalar', crosspost='sql\\ankdb_scalar-error') 
            raise 
        if not isinstance(res, sqlite.Cursor):
            log(' > Cursor: %s' % pf(res), 'sql\\ankdb_scalar')    
        try:
            res = res.fetchone()
        except TypeError as e:
            log(" > ERROR with ankdb_scalar while fetching result: %s\n >  LAST QUERY: %s" % (str(e), last_query), 'sql\\ankdb_scalar', crosspost='sql\\ankdb_scalar-error') 
            raise     
        log_blank('sql\\ankdb_scalar')
        if res:
            return res[0]
        return None  

    def all(self, sql='1', *a, **kw):
        return self.execute(sql, a, kw).fetchall()

    def first(self, sql='1', *a, **kw):
        c = self.execute(sql, a, kw)
        res = c.fetchone()
        c.close()
        return res

    def list(self, sql='1', *a, **kw):
        return [x[0] for x in self.execute(sql, a, kw)]

    def close(self):
        self._db.close()

    def set_progress_handler(self, *args):
        self._db.set_progress_handler(*args)

    def __enter__(self):
        self._db.execute("begin")
        return self

    def __exit__(self, exc_type, *args):
        self._db.close()

    def totalChanges(self):
        return self._db.total_changes

    def interrupt(self):
        self._db.interrupt()

    def recreate(self, force=True, t='{t}'):
        self.Init(t, force)

    def InitTags(self, force=False):
        if_exists = " IF NOT EXISTS" if not force else ""
        self.execute(
            """CREATE TABLE %s `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `parentGuid` TEXT, `updateSequenceNum` INTEGER NOT NULL, PRIMARY KEY(guid) );""" % (
                if_exists, TABLES.EVERNOTE.TAGS))

    def InitNotebooks(self, force=False):
        if_exists = " IF NOT EXISTS" if not force else ""
        self.execute(
            """CREATE TABLE %s `%s` ( `guid` TEXT NOT NULL UNIQUE, `name` TEXT NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `serviceUpdated` INTEGER NOT NULL, `stack` TEXT, PRIMARY KEY(guid) );""" % (
                if_exists, TABLES.EVERNOTE.NOTEBOOKS))

    def InitSeeAlso(self, forceRebuild=False):
        if_exists = "IF NOT EXISTS"
        if forceRebuild:
            self.drop(TABLES.SEE_ALSO)
            self.commit()
            if_exists = ""
        self.execute(
            """CREATE TABLE %s `%s` ( `id` INTEGER, `source_evernote_guid` TEXT NOT NULL, `number` INTEGER NOT NULL DEFAULT 100, `uid` INTEGER NOT NULL DEFAULT -1, `shard` TEXT NOT NULL DEFAULT -1, `target_evernote_guid` TEXT NOT NULL, `html` TEXT NOT NULL, `title` TEXT NOT NULL, `from_toc` INTEGER DEFAULT 0, `is_toc` INTEGER DEFAULT 0, `is_outline` INTEGER DEFAULT 0, PRIMARY KEY(id), unique(source_evernote_guid, target_evernote_guid) );""" % (
                if_exists, TABLES.SEE_ALSO))

    def Init(self, table='*', force=False):
        if table is '*' or table is TABLES.EVERNOTE.NOTES:
            self.execute(
                """CREATE TABLE IF NOT EXISTS `{n}` ( `guid` TEXT NOT NULL UNIQUE, `nid`    INTEGER NOT NULL DEFAULT -1, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL, PRIMARY KEY(guid) );""")
        if table is '*' or table is TABLES.EVERNOTE.NOTES_HISTORY:
            self.execute(
                """CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL)""" % TABLES.EVERNOTE.NOTES_HISTORY)
        if table is '*' or table is TABLES.TOC_AUTO:
            self.execute(
                """CREATE TABLE IF NOT EXISTS `%s` (     `root_title`    TEXT NOT NULL UNIQUE,     `contents`    TEXT NOT NULL,     `tagNames`    TEXT NOT NULL,     `notebookGuid`    TEXT NOT NULL,     PRIMARY KEY(root_title) );""" % TABLES.TOC_AUTO)
        if table is '*' or table is TABLES.NOTE_VALIDATION_QUEUE:
            self.execute(
                """CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT, `title` TEXT NOT NULL, `contents` TEXT NOT NULL, `tagNames` TEXT NOT NULL DEFAULT ',,', `notebookGuid` TEXT, `validation_status` INTEGER NOT NULL DEFAULT 0, `validation_result` TEXT, `noteType` TEXT);""" % TABLES.NOTE_VALIDATION_QUEUE)
        if table is '*' or table is TABLES.SEE_ALSO:
            self.InitSeeAlso(force)
        if table is '*' or table is TABLES.EVERNOTE.TAGS:
            self.InitTags(force)
        if table is '*' or table is TABLES.EVERNOTE.NOTEBOOKS:
            self.InitNotebooks(force)
