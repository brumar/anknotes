# -*- coding: utf-8 -*-
import os

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

    if not os.path.isfile(FILES.USER.TABLE_OF_CONTENTS_ENEX):
        log_error('Unable to proceed with find_deleted_notes: TOC enex does not exist.', do_print=True)
        return False

    enTableOfContents = file(FILES.USER.TABLE_OF_CONTENTS_ENEX, 'r').read()
    # find = file(os.path.join(PATH, "powergrep-find.txt") , 'r').read().splitlines()
    # replace = file(os.path.join(PATH, "powergrep-replace.txt") , 'r').read().replace('https://www.evernote.com/shard/s175/nl/19775535/' , '').splitlines()

    all_anknotes_notes = ankDB().all("SELECT guid, title, tagNames FROM %s " % TABLES.EVERNOTE.NOTES)
    find_guids = {}
    log_banner(' FIND DELETED EVERNOTE NOTES: UNIMPORTED EVERNOTE NOTES ', FILES.LOGS.FDN.UNIMPORTED_EVERNOTE_NOTES)
    log_banner(' FIND DELETED EVERNOTE NOTES: ORPHAN ANKI NOTES ', FILES.LOGS.FDN.ANKI_ORPHANS)
    log_banner(' FIND DELETED EVERNOTE NOTES: ORPHAN ANKNOTES DB ENTRIES ', FILES.LOGS.FDN.ANKNOTES_ORPHANS)
    log_banner(' FIND DELETED EVERNOTE NOTES: ANKNOTES TITLE MISMATCHES ', FILES.LOGS.FDN.ANKNOTES_TITLE_MISMATCHES)
    log_banner(' FIND DELETED EVERNOTE NOTES: ANKI TITLE MISMATCHES ', FILES.LOGS.FDN.ANKI_TITLE_MISMATCHES)
    log_banner(' FIND DELETED EVERNOTE NOTES: POSSIBLE TOC NOTES MISSING TAG ',
               FILES.LOGS.FDN.ANKI_TITLE_MISMATCHES + '_possibletoc')
    anki_mismatch = 0
    is_toc_or_outline = []
    all_anki_notes = ankDB().all("SELECT n.sfld, n.flds FROM notes n WHERE n.flds LIKE ? || '%'",
                                 FIELDS.EVERNOTE_GUID_PREFIX)
    all_anki_notes = {get_evernote_guid_from_anki_fields(flds): clean_title(sfld) for sfld, flds in all_anki_notes}
    delete_title_mismatches = True
    for line in all_anknotes_notes:
        guid = line['guid']
        title = line['title']
        if not (',' + TAGS.TOC + ',' in line['tagNames']):
            if title.upper() == title:
                log_plain(guid + '::: %-50s: ' % line['tagNames'][1:-1] + title,
                          FILES.LOGS.FDN.ANKI_TITLE_MISMATCHES + '_possibletoc', do_print=True)

        title = clean_title(title)
        title_safe = str_safe(title)
        find_guids[guid] = title
        if guid in all_anki_notes:
            find_title = clean_title(all_anki_notes[guid])
            find_title_safe = str_safe(find_title)
            if find_title_safe == title_safe or find_title == title:
                del all_anki_notes[guid]
            else:
                log_plain(guid + '::: ' + title + '\n ' + ' ' * len(guid) + '::: ' + find_title,
                          FILES.LOGS.FDN.ANKI_TITLE_MISMATCHES)
                log_plain(repr(find_title) + '\n ' + repr(title), FILES.LOGS.FDN.ANKI_TITLE_MISMATCHES + '-2')
                anki_mismatch += 1
                if delete_title_mismatches: del all_anki_notes[guid]
    mismatch = 0
    missing_evernote_notes = []
    for enLink in find_evernote_links(enTableOfContents):
        guid = enLink.Guid
        title = clean_title(enLink.FullTitle)
        title_safe = str_safe(title)

        if guid in find_guids:
            find_title = clean_title(find_guids[guid])
            find_title_safe = str_safe(find_title)
            if find_title_safe == title_safe or find_title == title:
                del find_guids[guid]
            else:
                log_plain(guid + '::: ' + title + '\n ' + ' ' * len(guid) + '::: ' + find_title,
                          FILES.LOGS.FDN.ANKNOTES_TITLE_MISMATCHES)
                if delete_title_mismatches: del find_guids[guid]
                mismatch += 1
        else:
            log_plain(guid + '::: ' + title, FILES.LOGS.FDN.UNIMPORTED_EVERNOTE_NOTES)
            missing_evernote_notes.append(guid)

    anki_dels, anknotes_dels = [], []
    for guid, title in all_anki_notes.items():
        log_plain(guid + '::: ' + title, FILES.LOGS.FDN.ANKI_ORPHANS)
        anki_dels.append(guid)
    for guid, title in find_guids.items():
        log_plain(guid + '::: ' + title, FILES.LOGS.FDN.ANKNOTES_ORPHANS)
        anknotes_dels.append(guid)

    logs = [
        ["Orphan Anknotes DB Note(s)",

         len(anknotes_dels),
         FILES.LOGS.FDN.ANKNOTES_ORPHANS,
         "(not present in Evernote)"

         ],

        ["Orphan Anki Note(s)",

         len(anki_dels),
         FILES.LOGS.FDN.ANKI_ORPHANS,
         "(not present in Anknotes DB)"

         ],

        ["Unimported Evernote Note(s)",

         len(missing_evernote_notes),
         FILES.LOGS.FDN.UNIMPORTED_EVERNOTE_NOTES,
         "(not present in Anknotes DB"

         ],

        ["Anknotes DB Title Mismatches",

         mismatch,
         FILES.LOGS.FDN.ANKNOTES_TITLE_MISMATCHES

         ],

        ["Anki Title Mismatches",

         anki_mismatch,
         FILES.LOGS.FDN.ANKI_TITLE_MISMATCHES

         ]
    ]
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
