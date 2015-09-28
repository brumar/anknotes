# -*- coding: utf-8 -*-

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

try:
    from aqt.utils import getText
    isAnki = True
except:
    isAnki = False

if not isAnki:        
    from anknotes.shared import *

    Error = sqlite.Error
    ankDBSetLocal()

    tags = ',#Imported,#Anki_Import,#Anki_Import_High_Priority,'
    # ankDB().setrowfactory()
    dbRows = ankDB().all("SELECT * FROM %s WHERE  ? LIKE '%%,' || name || ',%%' " % TABLES.EVERNOTE.TAGS, tags)

    for dbRow in dbRows:
        ankDB().execute("UPDATE %s SET tagNames = REPLACE(tagNames, ',%s,', ','), tagGuids = REPLACE(tagGuids, ',%s,', ',') WHERE tagGuids LIKE '%%,%s,%%'" % (TABLES.EVERNOTE.NOTES, dbRow['name'], dbRow['guid'],dbRow['guid'] ))
    ankDB().commit()
