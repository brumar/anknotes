#Python Imports 
from datetime import datetime, timedelta


#Anki Main Imports
from anknotes.constants_standard import EVERNOTE, DECKS

#Anki Class Imports
from anknotes.structs_base import UpdateExistingNotes
from anknotes.dicts import DictSettings

SETTINGS = DictSettings(key='anknotes')
with SETTINGS as s:
    s.FORM.LABEL_MINIMUM_WIDTH = 100
    with s.EVERNOTE as e:
        e.AUTH_TOKEN.setDefault(lambda dct: dct.key.name + '_' + EVERNOTE.API.CONSUMER_KEY.upper() + ("_SANDBOX" if EVERNOTE.API.IS_SANDBOXED else ""))
        e.AUTO_PAGING = True
        with e.QUERY as q:
            q.TAGS = '#Anki_Import'
            q.NOTEBOOK = 'My Anki Notebook'
            with q.LAST_UPDATED.VALUE.ABSOLUTE as a:
                a.DATE = "{:%Y %m %d}".format(datetime.now() - timedelta(days=7))
        with e.ACCOUNT as a:
            a.UID = '0'
            a.SHARD = 'x999'
    with s.ANKI as a, a.DECKS as d, a.TAGS as t:
        a.UPDATE_EXISTING_NOTES = UpdateExistingNotes.UpdateNotesInPlace
        d.BASE = DECKS.DEFAULT
        d.EVERNOTE_NOTEBOOK_INTEGRATION = True
        t.KEEP_TAGS = True    
        t.DELETE_EVERNOTE_QUERY_TAGS = False
        