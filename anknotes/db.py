### Python Imports
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite
from datetime import datetime
import time
import os
import sys

inAnki = 'anki' in sys.modules

### Anki Shared Imports
from anknotes.constants import *
from anknotes.logging import log_sql, log, log_blank

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


def ankDB(reset=False):
    global ankNotesDBInstance, dbLocal
    if not ankNotesDBInstance or reset:
        if dbLocal:
            ankNotesDBInstance = ank_DB(
            os.path.abspath(os.path.join(anki_profile_path_root(), last_anki_profile_name(), 'collection.anki2')))
        else:
            ankNotesDBInstance = ank_DB()
    return ankNotesDBInstance


def escape_text_sql(title):
    return title.replace("'", "''")


def delete_anki_notes_and_cards_by_guid(evernote_guids):
    data = [[FIELDS.EVERNOTE_GUID_PREFIX + x] for x in evernote_guids]
    db = ankDB()
    db.executemany("DELETE FROM cards WHERE nid in (SELECT id FROM notes WHERE flds LIKE  ? || '%')", data)
    db.executemany("DELETE FROM notes WHERE flds LIKE ? || '%'", data)


def get_evernote_title_from_guid(guid):
    return ankDB().scalar("SELECT title FROM %s WHERE guid = '%s'" % (TABLES.EVERNOTE.NOTES, guid))


def get_evernote_title_from_nids(nids):
    return get_evernote_title_from_guids(nids, 'nid')


def get_evernote_title_from_guids(guids, column='guid'):
    return ankDB().list("SELECT title FROM %s WHERE %s IN (%s) ORDER BY title ASC" % (
        TABLES.EVERNOTE.NOTES, column, ', '.join(["'%s'" % x for x in guids])))


def get_anki_deck_id_from_note_id(nid):
    return long(ankDB().scalar("SELECT did FROM cards WHERE nid = ? LIMIT 1", nid))


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
    sql = "SELECT %s FROM %s WHERE UPPER(title) IN {pred}" % (column, TABLES.EVERNOTE.NOTES)
    data_key = column
    if tag:
        sql += " AND tagNames LIKE '%%,%s,%%'" % tag; data_key += '-' + tag
    return get_cached_data(get_anknotes_root_notes_guids, lambda: execute_sqlite_in_query(sql,
                                                                                          get_anknotes_potential_root_titles(
                                                                                              upper_case=False,
                                                                                              encode=False),
                                                                                          pred='UPPER(?)'), data_key)
    # return 
    # for query, data in queries: results += db.list(base % query, *data)
    # return results 
    # data = ["'%s'" % escape_text_sql(x.upper() for x in get_anknotes_potential_root_titles()]    
    # return ankDB().list("SELECT guid FROM %s WHERE UPPER(title) IN (%s) AND tagNames LIKE '%%,%s,%%'" % (TABLES.EVERNOTE.NOTES, ', '.join(root_titles), TAGS.TOC))


def get_anknotes_root_notes_titles():
    return get_cached_data(get_anknotes_root_notes_titles,
                           lambda: get_evernote_title_from_guids(get_anknotes_root_notes_guids()))


def get_anknotes_potential_root_titles(upper_case=False, encode=False, **kwargs):
    global generateTOCTitle
    from anknotes.EvernoteNoteTitle import generateTOCTitle
    def mapper(x): return generateTOCTitle(x)
    if upper_case:
        mapper = lambda x, f=mapper: f(x).upper()
    if encode:
        mapper = lambda x, f=mapper: f(x).encode('utf-8')
    data = get_cached_data(get_anknotes_potential_root_titles, lambda: ankDB().list(
        "SELECT DISTINCT SUBSTR(title, 0, INSTR(title, ':')) FROM %s WHERE title LIKE '%%:%%'" % TABLES.EVERNOTE.NOTES))
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
        log_sql('FROM execute_sqlite_query ' + sql.format(pred=query),
                ['Data [%d]: ' % len(data), data, db.list(sql.format(pred=query), *data)[:3]])
        results += db.list(sql.format(pred=query), *data)
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
    if isinstance(fields, str) or isinstance(fields, unicode):
        fields = splitFields(fields)
        return fields[FIELDS.ORD.EVERNOTE_GUID].replace(FIELDS.EVERNOTE_GUID_PREFIX, '')


def get_all_local_db_guids(filter=None):
    if filter is None:
        filter = "1"
    return ankDB().list("SELECT guid FROM %s WHERE %s ORDER BY title ASC" % (TABLES.EVERNOTE.NOTES, filter))


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
    count = db.count(TABLES.EVERNOTE.NOTES, 'nid <= 0')
    if not count:
        return count 
    paired_data = db.all("SELECT n.id, n.flds FROM notes n WHERE " + get_evernote_model_ids(True))
    paired_data = [[nid, get_evernote_guid_from_anki_fields(flds)] for nid, flds in paired_data]
    db.executemany('UPDATE %s SET nid = ? WHERE guid = ?' % TABLES.EVERNOTE.NOTES, paired_data)
    db.commit()
    return count 


class ank_DB(object):
    def __init__(self, path=None, text=None, timeout=0):
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
            self._path = mw.col.db._path
            self._db.row_factory = sqlite.Row
        self.echo = os.environ.get("DBECHO")
        self.mod = False

    def setrowfactory(self):
        self._db.row_factory = sqlite.Row    
        
    def execute(self, sql, *a, **ka):
        log_sql(sql, a, ka, self=self)
        self.ankdb_lastquery = sql 
        s = sql.strip().lower()
        # mark modified?
        for stmt in "insert", "update", "delete":
            if s.startswith(stmt):
                self.mod = True
        t = time.time()
        if ka:
            # execute("...where id = :id", id=5)
            res = self._db.execute(sql, ka)
        elif a:
            # execute("...where id = ?", 5)
            res = self._db.execute(sql, a)
        else:
            res = self._db.execute(sql)
        if self.echo:
            # print a, ka
            print sql, "%0.3fms" % ((time.time() - t) * 1000)
            if self.echo == "2":
                print a, ka
        return res

    def executemany(self, sql, l):
        log_sql(sql, l)
        self.mod = True
        t = time.time()
        self._db.executemany(sql, l)
        if self.echo:
            print sql, "%0.3fms" % ((time.time() - t) * 1000)
            if self.echo == "2":
                print l

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

    def exists(self, table, where):
        count = self.count(table, where)
        return count is not None and count > 0
        
    def count(self, table, where=None, *a, **kw):
        if where is None:
            where = '1'
        sql = 'SELECT COUNT(*) FROM ' + table + ' WHERE ' + where
        return self.scalar(sql)
        
    def scalar(self, sql, *a, **kw):
        log_text = 'Call to DB.ankdb_scalar():'
        if not isinstance(self, ank_DB): 
            log_text += '\n   - Self:       ' + pf(self)
        if len(a)>0:
            log_text += '\n   - Args:       ' + pf(a)
        if len(kw)>0:
            log_text += '\n   - KWArgs:     ' + pf(kw)    
        last_query='<None>'
        if hasattr(self, 'ankdb_lastquery'):
            last_query = self.ankdb_lastquery
            if isinstance(last_query, str) or isinstance(last_query, unicode):
                last_query = last_query[:50]
            else:
                last_query = pf(last_query)
            log_text += '\n   - Last Query: ' + last_query
        log(log_text + '\n', 'sql\\ankdb_scalar')    
        try:
            res = self.execute(sql, *a, **kw)
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

    def all(self, sql, *a, **kw):
        return self.execute(sql, *a, **kw).fetchall()

    def first(self, sql, *a, **kw):
        c = self.execute(sql, *a, **kw)
        res = c.fetchone()
        c.close()
        return res

    def list(self, sql, *a, **kw):
        return [x[0] for x in self.execute(sql, *a, **kw)]

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
            self.execute("DROP TABLE %s " % TABLES.SEE_ALSO)
            self.commit()
            if_exists = ""
        self.execute(
            """CREATE TABLE %s `%s` ( `id` INTEGER, `source_evernote_guid` TEXT NOT NULL, `number` INTEGER NOT NULL DEFAULT 100, `uid` INTEGER NOT NULL DEFAULT -1, `shard` TEXT NOT NULL DEFAULT -1, `target_evernote_guid` TEXT NOT NULL, `html` TEXT NOT NULL, `title` TEXT NOT NULL, `from_toc` INTEGER DEFAULT 0, `is_toc` INTEGER DEFAULT 0, `is_outline` INTEGER DEFAULT 0, PRIMARY KEY(id), unique(source_evernote_guid, target_evernote_guid) );""" % (
                if_exists, TABLES.SEE_ALSO))

    def Init(self):
        self.execute(
            """CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL UNIQUE, `nid`    INTEGER NOT NULL DEFAULT -1, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL, PRIMARY KEY(guid) );""" % TABLES.EVERNOTE.NOTES)
        self.execute(
            """CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT NOT NULL, `title` TEXT NOT NULL, `content` TEXT NOT NULL, `updated` INTEGER NOT NULL, `created` INTEGER NOT NULL, `updateSequenceNum` INTEGER NOT NULL, `notebookGuid` TEXT NOT NULL, `tagGuids` TEXT NOT NULL, `tagNames` TEXT NOT NULL)""" % TABLES.EVERNOTE.NOTES_HISTORY)
        self.execute(
            """CREATE TABLE IF NOT EXISTS `%s` (     `root_title`    TEXT NOT NULL UNIQUE,     `contents`    TEXT NOT NULL,     `tagNames`    TEXT NOT NULL,     `notebookGuid`    TEXT NOT NULL,     PRIMARY KEY(root_title) );""" % TABLES.TOC_AUTO)
        self.execute(
            """CREATE TABLE IF NOT EXISTS `%s` ( `guid` TEXT, `title` TEXT NOT NULL, `contents` TEXT NOT NULL, `tagNames` TEXT NOT NULL DEFAULT ',,', `notebookGuid` TEXT, `validation_status` INTEGER NOT NULL DEFAULT 0, `validation_result` TEXT, `noteType` TEXT);""" % TABLES.NOTE_VALIDATION_QUEUE)
        self.InitSeeAlso()
        self.InitTags()
        self.InitNotebooks()
