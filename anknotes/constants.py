# -*- coding: utf-8 -*-
import os
PATH = os.path.dirname(os.path.abspath(__file__))

class ANKNOTES:
    FOLDER_EXTRA = os.path.join(PATH, 'extra')
    FOLDER_ANCILLARY = os.path.join(FOLDER_EXTRA, 'ancillary')
    FOLDER_GRAPHICS = os.path.join(FOLDER_EXTRA, 'graphics')
    FOLDER_LOGS = os.path.join(FOLDER_EXTRA, 'logs')
    FOLDER_TESTING = os.path.join(FOLDER_EXTRA, 'testing')
    LOG_BASE_NAME = 'anknotes'
    TEMPLATE_FRONT = os.path.join(FOLDER_ANCILLARY, 'FrontTemplate.htm')
    CSS = u'_AviAnkiCSS.css'
    ICON_EVERNOTE_WEB = os.path.join(FOLDER_GRAPHICS, u'evernote_web.ico')
    IMAGE_EVERNOTE_WEB = ICON_EVERNOTE_WEB.replace('.ico', '.png')
    ICON_EVERNOTE_ARTCORE = os.path.join(FOLDER_GRAPHICS, u'evernote_artcore.ico')
    IMAGE_EVERNOTE_ARTCORE = ICON_EVERNOTE_ARTCORE.replace('.ico', '.png')
    EVERNOTE_CONSUMER_KEY = "holycrepe"
    EVERNOTE_IS_SANDBOXED = False
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    DEVELOPER_MODE = (os.path.isfile(os.path.join(FOLDER_TESTING, 'anknotes.developer')))
    DEVELOPER_MODE_AUTOMATE = (os.path.isfile(os.path.join(FOLDER_TESTING, 'anknotes.developer.automate')))
    UPLOAD_AUTO_TOC_NOTES = False  # Set false if debugging note creation
    AUTO_TOC_NOTES_MAX = 5  # Set to -1 for unlimited


class MODELS:
    EVERNOTE_DEFAULT = 'evernote_note'
    EVERNOTE_REVERSIBLE = 'evernote_note_reversible'
    EVERNOTE_REVERSE_ONLY = 'evernote_note_reverse_only'
    EVERNOTE_CLOZE = 'evernote_note_cloze'
    TYPE_CLOZE = 1


class TEMPLATES:
    EVERNOTE_DEFAULT = 'EvernoteReview'
    EVERNOTE_REVERSED = 'EvernoteReviewReversed'
    EVERNOTE_CLOZE = 'EvernoteReviewCloze'


class FIELDS:
    TITLE = 'Title'
    CONTENT = 'Content'
    SEE_ALSO = 'See_Also'
    TOC = 'TOC'
    OUTLINE = 'Outline'
    EXTRA = 'Extra'
    EVERNOTE_GUID = 'Evernote GUID'
    UPDATE_SEQUENCE_NUM = 'updateSequenceNum'
    EVERNOTE_GUID_PREFIX = 'evernote_guid='


FIELDS_LIST = [FIELDS.TITLE, FIELDS.CONTENT, FIELDS.SEE_ALSO, FIELDS.EXTRA, FIELDS.TOC, FIELDS.OUTLINE,
               FIELDS.UPDATE_SEQUENCE_NUM]


class DECKS:
    DEFAULT = "Evernote"
    TOC_SUFFIX = "::See Also::TOC"
    OUTLINE_SUFFIX = "::See Also::Outline"


class EVERNOTE:
    class TAG:
        TOC = '#TOC'
        AUTO_TOC = '#TOC.Auto'
        OUTLINE = '#Outline'
        OUTLINE_TESTABLE = '#Outline.Testable'
        REVERSIBLE = '#Reversible'
        REVERSE_ONLY = '#Reversible_Only'

    # Note that Evernote's API documentation says not to run API calls to findNoteMetadata with any less than a 15 minute interval
    PAGING_RESTART_INTERVAL = 60 * 15
    # Auto Paging is probably only useful in the first 24 hours, when API usage is unlimited,  or when executing a search that is likely to have most of the notes up-to-date locally
    # To keep from overloading Evernote's servers, and flagging our API key, I recommend pausing 5-15 minutes in between searches, the higher the better.
    PAGING_TIMER_INTERVAL = 60 * 15
    PAGING_RESTART_DELAY_MINIMUM_API_CALLS = 10
    PAGING_RESTART_WHEN_COMPLETE = False
    IMPORT_TIMER_INTERVAL = PAGING_RESTART_INTERVAL * 2 * 1000
    METADATA_QUERY_LIMIT = 10000
    GET_NOTE_LIMIT = 10000


class TABLES:
    SEE_ALSO = "anknotes_see_also"

    class EVERNOTE:
        NOTEBOOKS = "anknotes_evernote_notebooks"
        TAGS = "anknotes_evernote_tags"
        NOTES = u'anknotes_evernote_notes'
        NOTES_HISTORY = u'anknotes_evernote_notes_history'
        AUTO_TOC = u'anknotes_evernote_auto_toc'


class SETTINGS:
    EVERNOTE_LAST_IMPORT = "ankNotesEvernoteLastAutoImport"
    ANKNOTES_CHECKABLE_MENU_ITEMS_PREFIX = "ankNotesCheckableMenuItems"
    KEEP_EVERNOTE_TAGS_DEFAULT_VALUE = True
    EVERNOTE_QUERY_TAGS_DEFAULT_VALUE = "#Anki_Import"
    DEFAULT_ANKI_DECK_DEFAULT_VALUE = DECKS.DEFAULT
    EVERNOTE_ACCOUNT_UID = 'ankNotesEvernoteAccountUID'
    EVERNOTE_ACCOUNT_SHARD = 'ankNotesEvernoteAccountSHARD'
    EVERNOTE_ACCOUNT_UID_DEFAULT_VALUE = '19775535'
    EVERNOTE_ACCOUNT_SHARD_DEFAULT_VALUE = 's175'
    EVERNOTE_QUERY_TAGS = 'anknotesEvernoteQueryTags'
    EVERNOTE_QUERY_USE_TAGS = 'anknotesEvernoteQueryUseTags'
    EVERNOTE_QUERY_LAST_UPDATED_VALUE_RELATIVE = 'anknotesEvernoteQueryLastUpdatedValueRelative'
    EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE = 'anknotesEvernoteQueryLastUpdatedValueAbsoluteDate'
    EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME = 'anknotesEvernoteQueryLastUpdatedValueAbsoluteDateTime'
    EVERNOTE_QUERY_LAST_UPDATED_TYPE = 'anknotesEvernoteQueryLastUpdatedType'
    EVERNOTE_QUERY_USE_LAST_UPDATED = 'anknotesEvernoteQueryUseLastUpdated'
    EVERNOTE_QUERY_NOTEBOOK = 'anknotesEvernoteQueryNotebook'
    EVERNOTE_QUERY_NOTEBOOK_DEFAULT_VALUE = 'My Anki Notebook'
    EVERNOTE_QUERY_USE_NOTEBOOK = 'anknotesEvernoteQueryUseNotebook'
    EVERNOTE_QUERY_NOTE_TITLE = 'anknotesEvernoteQueryNoteTitle'
    EVERNOTE_QUERY_USE_NOTE_TITLE = 'anknotesEvernoteQueryUseNoteTitle'
    EVERNOTE_QUERY_SEARCH_TERMS = 'anknotesEvernoteQuerySearchTerms'
    EVERNOTE_QUERY_USE_SEARCH_TERMS = 'anknotesEvernoteQueryUseSearchTerms'
    EVERNOTE_QUERY_ANY = 'anknotesEvernoteQueryAny'
    DELETE_EVERNOTE_TAGS_TO_IMPORT = 'anknotesDeleteEvernoteTagsToImport'
    UPDATE_EXISTING_NOTES = 'anknotesUpdateExistingNotes'
    EVERNOTE_PAGINATION_CURRENT_PAGE = 'anknotesEvernotePaginationCurrentPage'
    EVERNOTE_AUTO_PAGING = 'anknotesEvernoteAutoPaging'
    EVERNOTE_AUTH_TOKEN = 'anknotesEvernoteAuthToken_' + ANKNOTES.EVERNOTE_CONSUMER_KEY + (
        "_SANDBOX" if ANKNOTES.EVERNOTE_IS_SANDBOXED else "")
    KEEP_EVERNOTE_TAGS = 'anknotesKeepEvernoteTags'
    EVERNOTE_TAGS_TO_DELETE = 'anknotesEvernoteTagsToDelete'
    ANKI_DECK_EVERNOTE_NOTEBOOK_INTEGRATION = 'anknotesUseNotebookNameForAnkiDeckName'
    DEFAULT_ANKI_DECK = 'anknotesDefaultAnkiDeck'
