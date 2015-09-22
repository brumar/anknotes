# -*- coding: utf-8 -*-
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

from anknotes.shared import *


def do_find_deleted_notes(all_anki_notes=None):
    """
    :param all_anki_notes: from Anki.get_evernote_guids_and_anki_fields_from_anki_note_ids()
    :type : dict[str, dict[str, str]]
    :return:
    """

    Error = sqlite.Error

    enTableOfContents = file(ANKNOTES.TABLE_OF_CONTENTS_ENEX, 'r').read()
    # find = file(os.path.join(PATH, "powergrep-find.txt") , 'r').read().splitlines()
    # replace = file(os.path.join(PATH, "powergrep-replace.txt") , 'r').read().replace('https://www.evernote.com/shard/s175/nl/19775535/' , '').splitlines()
    
    all_anknotes_notes = ankDB().all("SELECT guid, title, tagNames FROM %s " % TABLES.EVERNOTE.NOTES)
    find_guids = {}
    log_banner(' FIND DELETED EVERNOTE NOTES: UNIMPORTED EVERNOTE NOTES ', ANKNOTES.LOG_FDN_UNIMPORTED_EVERNOTE_NOTES)
    log_banner(' FIND DELETED EVERNOTE NOTES: ORPHAN ANKI NOTES ', ANKNOTES.LOG_FDN_ANKI_ORPHANS)
    log_banner(' FIND DELETED EVERNOTE NOTES: ORPHAN ANKNOTES DB ENTRIES ', ANKNOTES.LOG_FDN_ANKNOTES_ORPHANS)
    log_banner(' FIND DELETED EVERNOTE NOTES: ANKNOTES TITLE MISMATCHES ', ANKNOTES.LOG_FDN_ANKNOTES_TITLE_MISMATCHES)
    log_banner(' FIND DELETED EVERNOTE NOTES: ANKI TITLE MISMATCHES ', ANKNOTES.LOG_FDN_ANKI_TITLE_MISMATCHES)
    log_banner(' FIND DELETED EVERNOTE NOTES: POSSIBLE TOC NOTES MISSING TAG ', ANKNOTES.LOG_FDN_ANKI_TITLE_MISMATCHES + '_possibletoc')
    anki_mismatch = 0
    is_toc_or_outline=[]
    for line in all_anknotes_notes:
        guid = line['guid']
        title = line['title']
        if  not (',' + EVERNOTE.TAG.TOC + ',' in line['tagNames']):
            if title.upper() == title:
                log_plain(guid + '::: %-50s: ' % line['tagNames'][1:-1] + title, ANKNOTES.LOG_FDN_ANKI_TITLE_MISMATCHES + '_possibletoc', do_print=True)
            
        title = clean_title(title)
        title_safe = str_safe(title)
        find_guids[guid] = title
        if all_anki_notes:
            if guid in all_anki_notes:
                find_title = all_anki_notes[guid][FIELDS.TITLE]
                find_title_safe = str_safe(find_title)
                if find_title_safe == title_safe:
                    del all_anki_notes[guid]
                else:
                    log_plain(guid + '::: ' + title, ANKNOTES.LOG_FDN_ANKI_TITLE_MISMATCHES)
                    anki_mismatch += 1
    mismatch = 0
    missing_evernote_notes = []
    for enLink in find_evernote_links(enTableOfContents):
        guid = enLink.Guid
        title = clean_title(enLink.FullTitle)
        title_safe = str_safe(title)
        
        if guid in find_guids:            
            find_title = find_guids[guid]
            find_title_safe = str_safe(find_title)
            if find_title_safe == title_safe:
                del find_guids[guid]
            else:
                log_plain(guid + '::: ' + title, ANKNOTES.LOG_FDN_ANKNOTES_TITLE_MISMATCHES)
                mismatch += 1
        else:
            log_plain(guid + '::: ' + title, ANKNOTES.LOG_FDN_UNIMPORTED_EVERNOTE_NOTES)
            missing_evernote_notes.append(guid)

    anki_dels = []
    anknotes_dels = []
    if all_anki_notes:
        for guid, fields in all_anki_notes.items():
            log_plain(guid + '::: ' + fields[FIELDS.TITLE], ANKNOTES.LOG_FDN_ANKI_ORPHANS)
            anki_dels.append(guid)
    for guid, title in find_guids.items():
        log_plain(guid + '::: ' + title, ANKNOTES.LOG_FDN_ANKNOTES_ORPHANS)
        anknotes_dels.append(guid)

    logs = [
        ["Orphan Anknotes DB Note(s)",

         len(anknotes_dels),
         ANKNOTES.LOG_FDN_ANKNOTES_ORPHANS,
         "(not present in Evernote)"

         ],

        ["Orphan Anki Note(s)",

         len(anki_dels),
         ANKNOTES.LOG_FDN_ANKI_ORPHANS,
         "(not present in Anknotes DB)"

         ],

        ["Unimported Evernote Note(s)",

         len(missing_evernote_notes),
         ANKNOTES.LOG_FDN_UNIMPORTED_EVERNOTE_NOTES,
         "(not present in Anknotes DB"

         ],

        ["Anknotes DB Title Mismatches",

         mismatch,
         ANKNOTES.LOG_FDN_ANKNOTES_TITLE_MISMATCHES

         ],

        ["Anki Title Mismatches",

         anki_mismatch,
         ANKNOTES.LOG_FDN_ANKI_TITLE_MISMATCHES

         ]
    ]
    # '<tr class=tr{:d}><td class=t1>{val[0]}</td><td class=t2><a href="{fn}">{title}</a></td><td class=t3>{val[1]}</td></tr>'.format(i, title=log[0], val=log[1], fn=convert_filename_to_local_link(log[1][1]))
    results = [
        [
            log[1],
            log[0] if log[1] == 0 else '<a href="%s">%s</a>' % (get_log_full_path(log[2], as_url_link=True), log[0]),
            log[3] if len(log) > 3 else ''
        ]
        for log in logs]

    # showInfo(str(results))

    return {
        "Summary":              results, "AnknotesOrphans": anknotes_dels, "AnkiOrphans": anki_dels,
        "MissingEvernoteNotes": missing_evernote_notes
    }
