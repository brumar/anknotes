import os

from thrift.Thrift import *
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.api.client import EvernoteClient
from evernote.edam.type.ttypes import SavedSearch

import anki
import aqt
from anki.hooks import wrap
from aqt.preferences import Preferences
from aqt.utils import showInfo, getText, openLink, getOnlyText
from aqt.qt import QLineEdit, QLabel, QVBoxLayout, QGroupBox, SIGNAL, QCheckBox
from aqt import mw
from pprint import pprint


# Note: This class was adapted from the Real-Time_Import_for_use_with_the_Rikaisama_Firefox_Extension plug-in by cb4960@gmail.com
#.. itself adapted from Yomichan plugin by Alex Yatskov.

PATH = os.path.dirname(os.path.abspath(__file__))
ONLY_ADD_NEW = True
EVERNOTE_MODEL = "evernote_note"
TITLE_FIELD_NAME = "title"
CONTENT_FIELD_NAME = "content"
GUID_FIELD_NAME = "Evernote Guid"


class Anki:
    def add_evernote_cards(self, evernote_cards, deck, tag):
        count = 0
        model_name = EVERNOTE_MODEL
        for card in evernote_cards:
            anki_field_info = {TITLE_FIELD_NAME: card.front.decode('utf-8'),
                               CONTENT_FIELD_NAME: card.back.decode('utf-8'),
                               GUID_FIELD_NAME: card.guid}
            card.tags.append(tag)
            self.add_note(deck, model_name, anki_field_info, card.tags)
            count += 1
        self.stop_editing()
        return count

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
        tags = [tags]
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
            t = mm.newTemplate('EvernoteReview')
            t['qfmt'] = "{{"+TITLE_FIELD_NAME+"}}"
            t['afmt'] = "{{"+CONTENT_FIELD_NAME+"}}"
            mm.addTemplate(evernote_model, t)
            mm.add(evernote_model)
            return evernote_model
        else:
            fmap = mm.fieldMap(evernote_model)
            title_ord, title_field = fmap[TITLE_FIELD_NAME]
            text_ord, text_field = fmap[CONTENT_FIELD_NAME]
            source_ord, source_field = fmap[GUID_FIELD_NAME]
            source_field['sticky'] = False

    def get_guids_from_anki_id(self,ids):
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
        query = "tag:"+tag
        ids = self.collection().findCards(query)
        #show_tooltip(ids)
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
        if not mw.col.conf.get('evernoteToken', False):
            # First run of the Plugin we did not save the access key yet
            client = EvernoteClient(
                consumer_key='scriptkiddi-2682',
                consumer_secret='965f1873e4df583c',
                sandbox=False
            )
            request_token = client.get_request_token('https://fap-studios.de/anknotes/index.html')
            url = client.get_authorize_url(request_token)
            showInfo("We will open a Evernote Tab in your browser so you can allow access to your account")
            openLink(url)
            oauth_verifier = getText(prompt="Please copy the code that showed up, after allowing access, in here")[0]
            auth_token = client.get_access_token(
                request_token.get('oauth_token'),
                request_token.get('oauth_token_secret'),
                oauth_verifier)
            mw.col.conf['evernoteToken'] = auth_token
        else:
            auth_token = mw.col.conf.get('evernoteToken', False)
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
        for g in guid_set:
            title, content, tags = self.get_note_informations(g)
            cards.append(EvernoteCard(title, content, g, tags))
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

    def get_note_informations(self, note_guid):
        whole_note = self.noteStore.getNote(self.token, note_guid, True, True, False, False)
        tags = []
        if mw.col.conf.get('evernoteKeepTags', False):
            tags = self.noteStore.getNoteTagNames(self.token, note_guid)
        return whole_note.title, whole_note.content, tags


class Controller:
    def __init__(self):
        self.evernoteTags = mw.col.conf.get('evernoteTagsToImport', "").split(",")
        self.ankiTag = mw.col.conf.get('evernoteDefaultTag', "anknotes")
        self.deck = mw.col.conf.get('evernoteDefaultDeck', "Default")
        self.anki = Anki()
        self.anki.add_evernote_model()
        self.evernote = Evernote()

    def proceed(self):
        anki_ids = self.anki.get_cards_id_from_tag(self.ankiTag)
        anki_guids = self.anki.get_guids_from_anki_id(anki_ids)
        evernote_guids = self.get_evernote_guids_from_tag(self.evernoteTags)
        if ONLY_ADD_NEW:
            note_guids_to_import = set(evernote_guids)-set(anki_guids)
            n = self.import_into_anki(note_guids_to_import, self.deck, self.ankiTag)
            show_tooltip(str(n) + " cards have been imported")

    def import_into_anki(self, guid_set, deck, tag):
        cards = self.evernote.create_evernote_cards(guid_set)
        number = self.anki.add_evernote_cards(cards, deck, tag)
        return number

    def get_evernote_guids_from_tag(self, tags):
        note_guids = []
        for tag in tags:
            tag_guid = self.evernote.find_tag_guid(tag)
            if tag_guid is not None:
                note_guids = note_guids+self.evernote.find_notes_filter_by_tag_guids([tag_guid])
        return note_guids


def show_tooltip(text, time_out=3000):
    aqt.utils.tooltip(text, time_out)


def main():
    show_tooltip(str())
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

        layout_tab = self.form.tab_1.layout()
        group_box = QGroupBox("Evernote Importer")
        layout = QVBoxLayout()

        # Default Deck
        evernote_default_deck_label = QLabel("Default Deck:")
        evernote_default_deck = QLineEdit()
        evernote_default_deck.setText(mw.col.conf.get('evernoteDefaultDeck', ""))
        layout.insertWidget(int(layout.count())+1, evernote_default_deck_label)
        layout.insertWidget(int(layout.count())+2, evernote_default_deck)
        evernote_default_deck.connect(evernote_default_deck, SIGNAL("editingFinished()"), update_evernote_default_deck)

        # Default Tag
        evernote_default_tag_label = QLabel("Default Tag:")
        evernote_default_tag = QLineEdit()
        evernote_default_tag.setText(mw.col.conf.get('evernoteDefaultTag', ""))
        layout.insertWidget(int(layout.count())+1, evernote_default_tag_label)
        layout.insertWidget(int(layout.count())+2, evernote_default_tag)
        evernote_default_tag.connect(evernote_default_tag, SIGNAL("editingFinished()"), update_evernote_default_tag)

        # Tags to import
        evernote_tags_to_import_label = QLabel("Tags to import:")
        evernote_tags_to_import = QLineEdit()
        evernote_tags_to_import.setText(mw.col.conf.get('evernoteTagsToImport', ""))
        layout.insertWidget(int(layout.count())+1, evernote_tags_to_import_label)
        layout.insertWidget(int(layout.count())+2, evernote_tags_to_import)
        evernote_tags_to_import.connect(evernote_tags_to_import,
                                        SIGNAL("editingFinished()"),
                                        update_evernote_tags_to_import)

        # keep evernote tags
        keep_evernote_tags = QCheckBox("Keep Evernote Tags", self)
        keep_evernote_tags.setChecked(mw.col.conf.get('evernoteKeepTags', False))
        keep_evernote_tags.stateChanged.connect(update_evernote_keep_tags)
        layout.insertWidget(int(layout.count())+1, keep_evernote_tags)
        group_box.setLayout(layout)
        layout_tab.insertWidget(int(layout.count())+1, group_box)


def update_evernote_default_deck():
        mw.col.conf['evernoteDefaultDeck'] = evernote_default_deck.text()


def update_evernote_default_tag():
        mw.col.conf['evernoteDefaultTag'] = evernote_default_tag.text()


def update_evernote_tags_to_import():
        mw.col.conf['evernoteTagsToImport'] = evernote_tags_to_import.text()


def update_evernote_keep_tags():
        mw.col.conf['evernoteKeepTags'] = keep_evernote_tags.isChecked()

Preferences.setupOptions = wrap(Preferences.setupOptions, setup_evernote)
