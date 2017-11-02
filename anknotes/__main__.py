import os
import base64
# from thrift.Thrift import *
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode
from evernote.api.client import EvernoteClient
# from evernote.edam.type.ttypes import SavedSearch

import anki
import aqt
from anki.hooks import wrap
from aqt.preferences import Preferences
from aqt.utils import showInfo, getText, openLink, getOnlyText
from aqt.qt import QPushButton, QLineEdit, QLabel, QVBoxLayout, QGroupBox, SIGNAL, QCheckBox, QComboBox, QSpacerItem, QSizePolicy, QWidget
from aqt import mw
# from pprint import pprint


# Note: This class was adapted from the Real-Time_Import_for_use_with_the_Rikaisama_Firefox_Extension plug-in
# by cb4960@gmail.com
# .. itself adapted from Yomichan plugin by Alex Yatskov.

PATH = os.path.dirname(os.path.abspath(__file__))
EVERNOTE_MODEL = 'evernote_note'
EVERNOTE_TEMPLATE_NAME = 'EvernoteReview'
TITLE_FIELD_NAME = 'title'
CONTENT_FIELD_NAME = 'content'
GUID_FIELD_NAME = 'Evernote GUID'

SETTING_UPDATE_EXISTING_NOTES = 'evernoteUpdateExistingNotes'
SETTING_TOKEN = 'evernoteToken_encoded'
SETTING_KEEP_TAGS = 'evernoteKeepTags'
SETTING_TAGS_TO_IMPORT = 'evernoteTagsToImport'
SETTING_DEFAULT_TAG = 'evernoteDefaultTag'
SETTING_DEFAULT_DECK = 'evernoteDefaultDeck'

class UpdateExistingNotes:
    IgnoreExistingNotes, UpdateNotesInPlace, DeleteAndReAddNotes = range(3)

class Anki:
    def update_evernote_cards(self, evernote_cards, tag):
        return self.add_evernote_cards(evernote_cards, None, tag, True)

    def add_evernote_cards(self, evernote_cards, deck, tag, update=False):
        count = 0
        model_name = EVERNOTE_MODEL
        for card in evernote_cards:
            anki_field_info = {TITLE_FIELD_NAME: card.front.decode('utf-8'),
                               CONTENT_FIELD_NAME: card.back.decode('utf-8'),
                               GUID_FIELD_NAME: card.guid}
            card.tags.append(tag)
            if update:
                self.update_note(anki_field_info, card.tags)
            else:
                self.add_note(deck, model_name, anki_field_info, card.tags)
            count += 1
        return count

    def delete_anki_cards(self, guid_ids):
        col = self.collection()
        card_ids = []
        for guid in guid_ids:
            card_ids += mw.col.findCards(guid)
        col.remCards(card_ids)
        return len(card_ids)

    def update_note(self, fields, tags=list()):
        col = self.collection()
        note_id = col.findNotes(fields[GUID_FIELD_NAME])[0]
        note = anki.notes.Note(col, None, note_id)
        note.tags = tags
        for fld in note._model['flds']:
            if TITLE_FIELD_NAME in fld.get('name'):
                note.fields[fld.get('ord')] = fields[TITLE_FIELD_NAME]
            elif CONTENT_FIELD_NAME in fld.get('name'):
                note.fields[fld.get('ord')] = fields[CONTENT_FIELD_NAME]
            # we dont have to update the evernote guid because if it changes we wont find this note anyway
        note.flush()
        return note.id

    def add_note(self, deck_name, model_name, fields, tags=list()):
        note = self.create_note(deck_name, model_name, fields, tags)
        if note is not None:
            collection = self.collection()
            collection.addNote(note)
            collection.autosave()
            self.start_editing()
            return note.id

    def create_note(self, deck_name, model_name, fields, tags=list()):
        id_deck = self.decks().id(deck_name)
        model = self.models().byName(model_name)
        col = self.collection()
        note = anki.notes.Note(col, model)
        note.model()['did'] = id_deck
        note.tags = tags
        for name, value in fields.items():
            note[name] = value
        return note

    def add_evernote_model(self):  # adapted from the IREAD plug-in from Frank
        col = self.collection()
        mm = col.models
        evernote_model = mm.byName(EVERNOTE_MODEL)
        if evernote_model is None:
            evernote_model = mm.new(EVERNOTE_MODEL)
            # Field for title:
            model_field = mm.newField(TITLE_FIELD_NAME)
            mm.addField(evernote_model, model_field)
            # Field for text:
            text_field = mm.newField(CONTENT_FIELD_NAME)
            mm.addField(evernote_model, text_field)
            # Field for source:
            guid_field = mm.newField(GUID_FIELD_NAME)
            guid_field['sticky'] = True
            mm.addField(evernote_model, guid_field)
            # Add template
            t = mm.newTemplate(EVERNOTE_TEMPLATE_NAME)
            t['qfmt'] = "{{" + TITLE_FIELD_NAME + "}}"
            t['afmt'] = "{{" + CONTENT_FIELD_NAME + "}}"
            mm.addTemplate(evernote_model, t)
            mm.add(evernote_model)
            return evernote_model
        else:
            fmap = mm.fieldMap(evernote_model)
            title_ord, title_field = fmap[TITLE_FIELD_NAME]
            text_ord, text_field = fmap[CONTENT_FIELD_NAME]
            source_ord, source_field = fmap[GUID_FIELD_NAME]
            source_field['sticky'] = False

    def get_guids_from_anki_id(self, ids):
        guids = []
        for a_id in ids:
            card = self.collection().getCard(a_id)
            items = card.note().items()
            if len(items) == 3:
                guids.append(items[2][1])  # not a very smart access
        return guids

    def can_add_note(self, deck_name, model_name, fields):
        return bool(self.create_note(deck_name, model_name, fields))

    def get_cards_id_from_tag(self, tag):
        query = "tag:" + tag
        ids = self.collection().findCards(query)
        return ids

    def start_editing(self):
        self.window().requireReset()

    def stop_editing(self):
        if self.collection():
            self.window().maybeReset()

    def window(self):
        return aqt.mw

    def collection(self):
        return self.window().col

    def models(self):
        return self.collection().models

    def decks(self):
        return self.collection().decks


class EvernoteCard:
    front = ""
    back = ""
    guid = ""

    def __init__(self, q, a, g, tags):
        self.front = q
        self.back = a
        self.guid = g
        self.tags = tags


class Evernote:
    def __init__(self):
        if not mw.col.conf.get(SETTING_TOKEN, False):
            # First run of the Plugin we did not save the access key yet
            client = EvernoteClient(
                consumer_key='scriptkiddi-2682',
                consumer_secret='965f1873e4df583c',
                sandbox=False
            )
            request_token = client.get_request_token('http://brunomart.in/anknotes/index.html')
            url = client.get_authorize_url(request_token)
            showInfo("We will open a Evernote Tab in your browser so you can allow access to your account")
            openLink(url)
            oauth_verifier = getText(prompt="Please copy the code that showed up, after allowing access, in here")[0]
            secret_key = getText(prompt="protect your value with a password, it will be asked each time you import your notes")[0]
            auth_token = client.get_access_token(
                request_token.get('oauth_token'),
                request_token.get('oauth_token_secret'),
                oauth_verifier)
            mw.col.conf[SETTING_TOKEN] = encode(secret_key, auth_token)
        else:
            secret_key = getText(prompt="password")[0]
            auth_token_encoded = mw.col.conf.get(SETTING_TOKEN, False)
            auth_token = decode(secret_key, auth_token_encoded)
        self.token = auth_token
        self.client = EvernoteClient(token=auth_token, sandbox=False)
        self.noteStore = self.client.get_note_store()

    def find_tag_guid(self, tag):
        list_tags = self.noteStore.listTags()
        for evernote_tag in list_tags:
            if str(evernote_tag.name).strip() == str(tag).strip():
                return evernote_tag.guid

    def create_evernote_cards(self, guid_set):
        cards = []
        for guid in guid_set:
            note_info = self.get_note_information(guid)
            if note_info is None:
                return cards
            title, content, tags = note_info
            cards.append(EvernoteCard(title, content, guid, tags))
        return cards

    def find_notes_filter_by_tag_guids(self, guids_list):
        evernote_filter = NoteFilter()
        evernote_filter.ascending = False
        evernote_filter.tagGuids = guids_list
        spec = NotesMetadataResultSpec()
        spec.includeTitle = True
        note_list = self.noteStore.findNotesMetadata(self.token, evernote_filter, 0, 10000, spec)
        guids = []
        for note in note_list.notes:
            guids.append(note.guid)
        return guids

    def get_note_information(self, note_guid):
        tags = []
        try:
            whole_note = self.noteStore.getNote(self.token, note_guid, True, True, False, False)
            if mw.col.conf.get(SETTING_KEEP_TAGS, False):
                tags = self.noteStore.getNoteTagNames(self.token, note_guid)
        except EDAMSystemException, e:
            if e.errorCode == EDAMErrorCode.RATE_LIMIT_REACHED:
                m, s = divmod(e.rateLimitDuration, 60)
                showInfo("Rate limit has been reached. We will save the notes downloaded thus far.\r\n"
                         "Please retry your request in {} min".format("%d:%02d" % (m, s)))
                return None
            raise
        return whole_note.title, whole_note.content, tags


class Controller:
    def __init__(self):
        self.evernoteTags = mw.col.conf.get(SETTING_TAGS_TO_IMPORT, "").split(",")
        self.ankiTag = mw.col.conf.get(SETTING_DEFAULT_TAG, "anknotes")
        self.deck = mw.col.conf.get(SETTING_DEFAULT_DECK, "Default")
        self.updateExistingNotes = mw.col.conf.get(SETTING_UPDATE_EXISTING_NOTES,
                                                   UpdateExistingNotes.UpdateNotesInPlace)
        self.anki = Anki()
        self.anki.add_evernote_model()
        self.evernote = Evernote()

    def proceed(self):
        if self.evernoteTags=="":
            show_tooltip("Warning : No tag to import has been specified in the preferences, that may result into empty imports")
        anki_ids = self.anki.get_cards_id_from_tag(self.ankiTag)
        anki_guids = self.anki.get_guids_from_anki_id(anki_ids)
        evernote_guids = self.get_evernote_guids_from_tag(self.evernoteTags)
        cards_to_add = set(evernote_guids) - set(anki_guids)
        cards_to_update = set(evernote_guids) - set(cards_to_add)
        self.anki.start_editing()
        n = self.import_into_anki(cards_to_add, self.deck, self.ankiTag)
        if self.updateExistingNotes is UpdateExistingNotes.IgnoreExistingNotes:
            show_tooltip("{} new card(s) have been imported. Updating is disabled.".format(str(n)))
        else:
            n2 = len(cards_to_update)
            if self.updateExistingNotes is UpdateExistingNotes.UpdateNotesInPlace:
                update_str = "in-place"
                self.update_in_anki(cards_to_update, self.ankiTag)
            else:
                update_str = "(deleted and re-added)"
                self.anki.delete_anki_cards(cards_to_update)
                self.import_into_anki(cards_to_update, self.deck, self.ankiTag)
            show_tooltip("{} new card(s) have been imported and {} existing card(s) have been updated {}."
                         .format(str(n), str(n2), update_str))
        self.anki.stop_editing()
        self.anki.collection().autosave()

    def update_in_anki(self, guid_set, tag):
        cards = self.evernote.create_evernote_cards(guid_set)
        number = self.anki.update_evernote_cards(cards, tag)
        return number

    def import_into_anki(self, guid_set, deck, tag):
        cards = self.evernote.create_evernote_cards(guid_set)
        number = self.anki.add_evernote_cards(cards, deck, tag)
        return number

    def get_evernote_guids_from_tag(self, tags):
        note_guids = []
        for tag in tags:
            tag_guid = self.evernote.find_tag_guid(tag)
            if tag_guid is not None:
                note_guids += self.evernote.find_notes_filter_by_tag_guids([tag_guid])
        return note_guids


def show_tooltip(text, time_out=3000):
    aqt.utils.tooltip(text, time_out)

# Vigenere_cipher
# ref : https://stackoverflow.com/questions/2490334/simple-way-to-encode-a-string-according-to-a-password
def encode(key, clear):
    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))

def decode(key, enc):
    if not isinstance(enc, str):
        enc = enc.encode('ascii', 'ignore')
    dec = []
    enc = base64.urlsafe_b64decode(enc)
    for i in range(len(enc)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)


def main():
    controller = Controller()
    controller.proceed()


action = aqt.qt.QAction("Import from Evernote", aqt.mw)
aqt.mw.connect(action, aqt.qt.SIGNAL("triggered()"), main)
aqt.mw.form.menuTools.addAction(action)


def setup_evernote(self):
    global evernote_default_deck
    global evernote_default_tag
    global evernote_tags_to_import
    global keep_evernote_tags
    global update_existing_notes

    widget = QWidget()
    layout = QVBoxLayout()

    # Default Deck
    evernote_default_deck_label = QLabel("Default Deck:")
    evernote_default_deck = QLineEdit()
    evernote_default_deck.setText(mw.col.conf.get(SETTING_DEFAULT_DECK, ""))
    layout.insertWidget(int(layout.count()) + 1, evernote_default_deck_label)
    layout.insertWidget(int(layout.count()) + 2, evernote_default_deck)
    evernote_default_deck.connect(evernote_default_deck, SIGNAL("editingFinished()"), update_evernote_default_deck)

    # Default Tag
    evernote_default_tag_label = QLabel("Default Tag:")
    evernote_default_tag = QLineEdit()
    evernote_default_tag.setText(mw.col.conf.get(SETTING_DEFAULT_TAG, ""))
    layout.insertWidget(int(layout.count()) + 1, evernote_default_tag_label)
    layout.insertWidget(int(layout.count()) + 2, evernote_default_tag)
    evernote_default_tag.connect(evernote_default_tag, SIGNAL("editingFinished()"), update_evernote_default_tag)

    # Tags to Import
    evernote_tags_to_import_label = QLabel("Tags to Import:")
    evernote_tags_to_import = QLineEdit()
    evernote_tags_to_import.setText(mw.col.conf.get(SETTING_TAGS_TO_IMPORT, ""))
    layout.insertWidget(int(layout.count()) + 1, evernote_tags_to_import_label)
    layout.insertWidget(int(layout.count()) + 2, evernote_tags_to_import)
    evernote_tags_to_import.connect(evernote_tags_to_import,
                                    SIGNAL("editingFinished()"),
                                    update_evernote_tags_to_import)

    # Keep Evernote Tags
    keep_evernote_tags = QCheckBox("Keep Evernote Tags", self)
    keep_evernote_tags.setChecked(mw.col.conf.get(SETTING_KEEP_TAGS, False))
    keep_evernote_tags.stateChanged.connect(update_evernote_keep_tags)
    layout.insertWidget(int(layout.count()) + 1, keep_evernote_tags)

    # Update Existing Notes
    update_existing_notes = QComboBox()
    update_existing_notes.addItems(["Ignore Existing Notes", "Update Existing Notes In-Place",
                                    "Delete and Re-Add Existing Notes"])
    update_existing_notes.setCurrentIndex(mw.col.conf.get(SETTING_UPDATE_EXISTING_NOTES,
                                                          UpdateExistingNotes.UpdateNotesInPlace))
    update_existing_notes.activated.connect(update_evernote_update_existing_notes)
    layout.insertWidget(int(layout.count()) + 1, update_existing_notes)

    deletebutton = QPushButton(_("Reset Account"), clicked=remove_token)
    layout.insertWidget(int(layout.count()) + 1, deletebutton)


    # Vertical Spacer
    vertical_spacer = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
    layout.addItem(vertical_spacer)

    # Parent Widget
    widget.setLayout(layout)

    # New Tab
    self.form.tabWidget.addTab(widget, "Evernote Importer")

def update_evernote_default_deck():
    mw.col.conf[SETTING_DEFAULT_DECK] = evernote_default_deck.text()

def update_evernote_default_tag():
    mw.col.conf[SETTING_DEFAULT_TAG] = evernote_default_tag.text()

def update_evernote_tags_to_import():
    mw.col.conf[SETTING_TAGS_TO_IMPORT] = evernote_tags_to_import.text()

def update_evernote_keep_tags():
    mw.col.conf[SETTING_KEEP_TAGS] = keep_evernote_tags.isChecked()

def update_evernote_update_existing_notes(index):
    mw.col.conf[SETTING_UPDATE_EXISTING_NOTES] = index

def remove_token(*args, **kwargs):
    mw.col.conf[SETTING_TOKEN]=False
    show_tooltip("your token has been deleted")

Preferences.setupOptions = wrap(Preferences.setupOptions, setup_evernote)
