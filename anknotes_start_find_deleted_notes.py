import sys

inAnki = 'anki' in sys.modules

if not inAnki:
    from anknotes import find_deleted_notes
    from anknotes.db import ankDBSetLocal

    ankDBSetLocal()
    find_deleted_notes.do_find_deleted_notes()
