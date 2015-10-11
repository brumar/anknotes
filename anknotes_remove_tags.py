# -*- coding: utf-8 -*-
import sys
inAnki='anki' in sys.modules

if not inAnki:
    from anknotes.shared import *
    try:
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        from sqlite3 import dbapi2 as sqlite

    Error = sqlite.Error
    ankDBSetLocal()

    tags = ',#Imported,#Anki_Import,#Anki_Import_High_Priority,'
    # ankDB().setrowfactory()
    db = ankDB(TABLES.EVERNOTE.TAGS)
    dbRows = db.all("SELECT * FROM {t} WHERE  ? LIKE '%%,' || name || ',%%' ", tags)

    for dbRow in dbRows:
        db.execute(fmt("UPDATE {n} SET tagNames = REPLACE(tagNames, ',{row[name]},', ','), tagGuids = "
                            "REPLACE(tagGuids, ',{row[guid]},', ',') WHERE tagGuids LIKE '%,{row[guid]},%'", row=dbRow))
    db.commit()
