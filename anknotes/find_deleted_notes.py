# -*- coding: utf-8 -*-
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

from anknotes.shared import *


Error = sqlite.Error
ankDBSetLocal()

ENNotes = file(ANKNOTES.TABLE_OF_CONTENTS_ENEX, 'r').read()
# find = file(os.path.join(PATH, "powergrep-find.txt") , 'r').read().splitlines()
# replace = file(os.path.join(PATH, "powergrep-replace.txt") , 'r').read().replace('https://www.evernote.com/shard/s175/nl/19775535/' , '').splitlines()

all_notes = ankDB().all("SELECT guid, title FROM %s " % TABLES.EVERNOTE.NOTES)
ankDB().close()
find_guids = {}

log1='Find Deleted Notes\\MissingFromAnki'
log2='Find Deleted Notes\\MissingFromEvernote'
log3='Find Deleted Notes\\TitleMismatch'
log_banner(' FIND DELETED EVERNOTE NOTES: EVERNOTE NOTES MISSING FROM ANKI ', log1)
log_banner(' FIND DELETED EVERNOTE NOTES: ANKI NOTES DELETED FROM EVERNOTE ', log2)
log_banner(' FIND DELETED EVERNOTE NOTES: TITLE MISMATCHES ', log3)

for line in all_notes:
    # line = line.split('::: ')
    # guid = line[0]
    # title = line[1]
    guid = line['guid']
    title = line['title']
    title = clean_title(title)
    find_guids[guid] = title
mismatch=0
missingfromanki=0
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
            # print("Found guid match, title mismatch for %s: \n - %s\n - %s" % (guid, title_safe, find_title_safe))
            log_plain(guid + ': ' + title_safe, log3)
            mismatch += 1
    else:
        title_safe = str_safe(title)
        # print("COULD NOT FIND Anknotes database GUID for Evernote Server GUID %s: %s" % (guid, title_safe))
        log_plain(guid + ': ' + title_safe, log1)
        missingfromanki += 1

dels = []
for guid, title in find_guids.items():
    title_safe = str_safe(title)
    log_plain(guid + ': ' + title_safe, log2)
    dels.append(guid)
print "\nTotal %3d notes deleted from Evernote but still present in Anki" % len(dels)
print "Total %3d notes present in Evernote but not present in Anki" % missingfromanki
print "Total %3d title mismatches" % mismatch

# confirm = raw_input("Please type in the total number of results (%d) to confirm deletion from the Anknotes DB. Note that the notes will not be deleted from Anknotes' Notes History database.\n   >> " % len(dels))
#
# if confirm == str(len(dels)):
#     print "Confirmed!"
#     ankDB().executemany("DELETE FROM %s WHERE guid = ?" % TABLES.EVERNOTE.NOTES, dels)
#     ankDB().commit()
#
