# -*- coding: utf-8 -*-
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

from anknotes.shared import *

Error = sqlite.Error
ankDBSetLocal()

PATH = os.path.dirname(os.path.abspath(__file__)) + '\\extra\\testing\\'
ENNotes = file(os.path.join(PATH, "^ Scratch Note.enex"), 'r').read()
# find = file(os.path.join(PATH, "powergrep-find.txt") , 'r').read().splitlines()
# replace = file(os.path.join(PATH, "powergrep-replace.txt") , 'r').read().replace('https://www.evernote.com/shard/s175/nl/19775535/' , '').splitlines()

all_notes = ankDB().execute("SELECT guid, title FROM %s " % TABLES.EVERNOTE.NOTES)
find_guids = {}


for line in all_notes:
    # line = line.split('::: ')
    # guid = line[0]
    # title = line[1]
    guid = line['guid']
    title = line['title']
    title = clean_title(title)
    find_guids[guid] = title

for match in find_evernote_links(ENNotes):
    guid = match.group('guid')
    title = match.group('Title')
    title = clean_title(title)
    title_safe = str_safe(title)
    if guid in find_guids:
        find_title = find_guids[guid]
        find_title_safe = str_safe(find_title)
        if find_title_safe == title_safe:
            del find_guids[guid]
        else:
            print("Found guid match, title mismatch for %s: \n - %s\n - %s" % (guid, title_safe, find_title_safe))
    else:
        title_safe = str_safe(title)
        print("COULD NOT FIND guid for %s: %s" % (guid, title_safe))

dels = []
with open(os.path.join(PATH, 'deleted-notes.txt'), 'w') as filesProgress:
    for guid, title in find_guids.items():
        print>> filesProgress, str_safe('%s::: %s' % (guid, title))
        dels.append([guid])

ankDB().executemany("DELETE FROM %s WHERE guid = ?" % TABLES.EVERNOTE.NOTES, dels)
ankDB().commit()
