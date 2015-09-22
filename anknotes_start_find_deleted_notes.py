try:
    from aqt.utils import getText
    isAnki = True
except:
    isAnki = False

if not isAnki:
    from anknotes import find_deleted_notes
    from anknotes.db import ankDBSetLocal
    ankDBSetLocal()
    find_deleted_notes.do_find_deleted_notes()