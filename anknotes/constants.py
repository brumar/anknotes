# -*- coding: utf-8 -*-
import os

PATH = os.path.dirname(os.path.abspath(__file__))
class FOLDERS:
	ADDONS = os.path.dirname(PATH)
	EXTRA = os.path.join(PATH, 'extra')
	ANCILLARY = os.path.join(EXTRA, 'ancillary')
	GRAPHICS = os.path.join(EXTRA, 'graphics')
	LOGS = os.path.join(EXTRA, 'logs')
	DEVELOPER = os.path.join(EXTRA, 'dev')
	USER = os.path.join(EXTRA, 'user')

class FILES:
	class LOGS:
		class FDN:
			ANKI_ORPHANS = 'Find Deleted Notes\\'
			UNIMPORTED_EVERNOTE_NOTES = ANKI_ORPHANS + 'UnimportedEvernoteNotes'
			ANKI_TITLE_MISMATCHES = ANKI_ORPHANS + 'AnkiTitleMismatches'
			ANKNOTES_TITLE_MISMATCHES = ANKI_ORPHANS + 'AnknotesTitleMismatches'
			ANKNOTES_ORPHANS = ANKI_ORPHANS + 'AnknotesOrphans'
			ANKI_ORPHANS += 'AnkiOrphans'		
		BASE_NAME = ''
		DEFAULT_NAME = 'anknotes'
		MAIN = DEFAULT_NAME
		ACTIVE = DEFAULT_NAME
		USE_CALLER_NAME = False	
	class ANCILLARY:
		TEMPLATE = os.path.join(FOLDERS.ANCILLARY, 'FrontTemplate.htm')
		CSS = u'_AviAnkiCSS.css'
		CSS_QMESSAGEBOX = os.path.join(FOLDERS.ANCILLARY, 'QMessageBox.css')
		ENML_DTD = os.path.join(FOLDERS.ANCILLARY, 'enml2.dtd')
	class SCRIPTS:
		VALIDATION = os.path.join(FOLDERS.ADDONS, 'anknotes_start_note_validation.py') 
		FIND_DELETED_NOTES = os.path.join(FOLDERS.ADDONS, 'anknotes_start_find_deleted_notes.py')  
	class GRAPHICS:
		class ICON:
			EVERNOTE_WEB = os.path.join(FOLDERS.GRAPHICS, u'evernote_web.ico')		
			EVERNOTE_ARTCORE = os.path.join(FOLDERS.GRAPHICS, u'evernote_artcore.ico')
			TOMATO = os.path.join(FOLDERS.GRAPHICS, u'Tomato-icon.ico')
		class IMAGE:
			pass 
		IMAGE.EVERNOTE_WEB = ICON.EVERNOTE_WEB.replace('.ico', '.png')
		IMAGE.EVERNOTE_ARTCORE = ICON.EVERNOTE_ARTCORE.replace('.ico', '.png')
	class USER:
		TABLE_OF_CONTENTS_ENEX = os.path.join(FOLDERS.USER, "Table of Contents.enex")
		LAST_PROFILE_LOCATION = os.path.join(FOLDERS.USER, 'anki.profile')
	
class ANKNOTES:
	DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
	class DEVELOPER_MODE:
		ENABLED = (os.path.isfile(os.path.join(FOLDERS.DEVELOPER, 'anknotes.developer')))
		AUTOMATED = ENABLED and (os.path.isfile(os.path.join(FOLDERS.DEVELOPER, 'anknotes.developer.automate')))
		AUTO_RELOAD_MODULES = True
	class HIERARCHY:
		ROOT_TITLES_BASE_QUERY = "notebookGuid != 'fdccbccf-ee70-4069-a587-82772a96d9d3'"

class MODELS:
	class TYPES:
		CLOZE = 1	
	class OPTIONS:
		IMPORT_STYLES = True 
	DEFAULT = 'evernote_note'
	REVERSIBLE = 'evernote_note_reversible'
	REVERSE_ONLY = 'evernote_note_reverse_only'
	CLOZE = 'evernote_note_cloze'

class TEMPLATES:
	DEFAULT = 'EvernoteReview'
	REVERSED = 'EvernoteReviewReversed'
	CLOZE = 'EvernoteReviewCloze'


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
	LIST = [TITLE, CONTENT, SEE_ALSO, EXTRA, TOC, OUTLINE,
			   UPDATE_SEQUENCE_NUM]
	class ORD:
		pass
	ORD.CONTENT = LIST.index(CONTENT) + 1
	ORD.SEE_ALSO = LIST.index(SEE_ALSO) + 1
	
class DECKS:
	DEFAULT = "Evernote"
	TOC_SUFFIX = "::See Also::TOC"
	OUTLINE_SUFFIX = "::See Also::Outline"

class ANKI:
	PROFILE_NAME = ''
	NOTE_LIGHT_PROCESSING_INCLUDE_CSS_FORMATTING = False

class TAGS:
	TOC = '#TOC'
	AUTO_TOC = '#TOC.Auto'
	OUTLINE = '#Outline'
	OUTLINE_TESTABLE = '#Outline.Testable'
	REVERSIBLE = '#Reversible'
	REVERSE_ONLY = '#Reversible_Only'	
	
class EVERNOTE:
	class IMPORT:
		class PAGING:
			# Note that Evernote's API documentation says not to run API calls to findNoteMetadata with any less than a 15 minute interval
			# Auto Paging is probably only useful in the first 24 hours, when API usage is unlimited, or when executing a search that is likely to have most of the notes up-to-date locally
			# To keep from overloading Evernote's servers, and flagging our API key, I recommend pausing 5-15 minutes in between searches, the higher the better.			
			class RESTART:	
				DELAY_MINIMUM_API_CALLS = 10
				ENABLED = False		
			INTERVAL = 60 * 15
			RESTART.INTERVAL = INTERVAL * 2		
		INTERVAL = PAGING.INTERVAL * 4 / 3
		METADATA_RESULTS_LIMIT = 10000
		API_CALLS_LIMIT = 300
	class UPLOAD:
		ENABLED = True  # Set False if debugging note creation
		MAX = -1  # Set to -1 for unlimited
		RESTART_INTERVAL = 30 # In seconds 
		class VALIDATION:
			ENABLED = True 
			AUTOMATED = True 	
	class API:
		class RateLimitErrorHandling:
			IgnoreError, ToolTipError, AlertError = range(3)
		CONSUMER_KEY = "holycrepe"
		IS_SANDBOXED = False	
		EDAM_RATE_LIMIT_ERROR_HANDLING = RateLimitErrorHandling.ToolTipError
		DEBUG_RAISE_ERRORS = False 
		
class TABLES:
	SEE_ALSO = "anknotes_see_also"
	NOTE_VALIDATION_QUEUE = "anknotes_note_validation_queue"
	AUTO_TOC = u'anknotes_auto_toc'	
	class EVERNOTE:
		NOTEBOOKS = "anknotes_evernote_notebooks"
		TAGS = "anknotes_evernote_tags"
		NOTES = u'anknotes_evernote_notes'
		NOTES_HISTORY = u'anknotes_evernote_notes_history'

class SETTINGS:
	class EVERNOTE:
		class QUERY:
			TAGS_DEFAULT_VALUE = "#Anki_Import"
			TAGS = 'anknotesEvernoteQueryTags'
			USE_TAGS = 'anknotesEvernoteQueryUseTags'
			EXCLUDED_TAGS = 'anknotesEvernoteQueryExcludedTags'
			USE_EXCLUDED_TAGS = 'anknotesEvernoteQueryUseExcludedTags'
			LAST_UPDATED_VALUE_RELATIVE = 'anknotesEvernoteQueryLastUpdatedValueRelative'
			LAST_UPDATED_VALUE_ABSOLUTE_DATE = 'anknotesEvernoteQueryLastUpdatedValueAbsoluteDate'
			LAST_UPDATED_VALUE_ABSOLUTE_TIME = 'anknotesEvernoteQueryLastUpdatedValueAbsoluteDateTime'
			LAST_UPDATED_TYPE = 'anknotesEvernoteQueryLastUpdatedType'
			USE_LAST_UPDATED = 'anknotesEvernoteQueryUseLastUpdated'
			NOTEBOOK = 'anknotesEvernoteQueryNotebook'
			NOTEBOOK_DEFAULT_VALUE = 'My Anki Notebook'
			USE_NOTEBOOK = 'anknotesEvernoteQueryUseNotebook'
			NOTE_TITLE = 'anknotesEvernoteQueryNoteTitle'
			USE_NOTE_TITLE = 'anknotesEvernoteQueryUseNoteTitle'
			SEARCH_TERMS = 'anknotesEvernoteQuerySearchTerms'
			USE_SEARCH_TERMS = 'anknotesEvernoteQueryUseSearchTerms'
			ANY = 'anknotesEvernoteQueryAny'
		class ACCOUNT:
			UID = 'ankNotesEvernoteAccountUID'
			SHARD = 'ankNotesEvernoteAccountSHARD'
			UID_DEFAULT_VALUE = '0'
			SHARD_DEFAULT_VALUE = 'x999'
		LAST_IMPORT = "ankNotesEvernoteLastAutoImport"		
		PAGINATION_CURRENT_PAGE = 'anknotesEvernotePaginationCurrentPage'
		AUTO_PAGING = 'anknotesEvernoteAutoPaging'
		AUTH_TOKEN = 'anknotesEvernoteAuthToken_' + EVERNOTE.API.CONSUMER_KEY + (
		"_SANDBOX" if EVERNOTE.API.IS_SANDBOXED else "")				
	class ANKI:				
		class DECKS:
			EVERNOTE_NOTEBOOK_INTEGRATION = 'anknotesUseNotebookNameForAnkiDeckName'
			BASE = 'anknotesDefaultAnkiDeck'	
			BASE_DEFAULT_VALUE = DECKS.DEFAULT			
		class TAGS:
			TO_DELETE = 'anknotesTagsToDelete'	
			KEEP_TAGS_DEFAULT_VALUE = True	
			KEEP_TAGS = 'anknotesTagsKeepEvernoteTags'
			DELETE_EVERNOTE_QUERY_TAGS = 'anknotesTagsDeleteEvernoteQueryTags'
		UPDATE_EXISTING_NOTES = 'anknotesUpdateExistingNotes'	
	ANKNOTES_CHECKABLE_MENU_ITEMS_PREFIX = "ankNotesCheckableMenuItems"
