import os, sys, inspect
 # use this if you want to include modules from a subforder


import re
import ConfigParser
import anki
import hashlib
import binascii
import thrift
from thrift.Thrift import *
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.type.ttypes as Types
from evernote.api.client import EvernoteClient
import os, re, codecs
import PyQt4.QtNetwork
import aqt
from anki.hooks import wrap
from aqt.preferences import Preferences
from aqt.utils import showInfo, getText, openLink, getOnlyText
from aqt.qt import *
from aqt import mw
from anki import db


# Note: This class was adapted from the Real-Time_Import_for_use_with_the_Rikaisama_Firefox_Extension plug-in by cb4960@gmail.com
#.. itself adapted from Yomichan plugin by Alex Yatskov.

PATH=os.path.dirname(os.path.abspath(__file__))
ONLY_ADD_NEW=True
EVERNOTE_MODEL="evernote_note"
TITLE_FIELD_NAME="title"
CONTENT_FIELD_NAME="content"
GUID_FIELD_NAME="Evernote Guid"

class Anki:
    def addEvernoteCards(self, evernoteCards,deck,tag):
        count=0
        modelName=EVERNOTE_MODEL
        for card in evernoteCards:
            ankiFieldInfo = {}
            ankiFieldInfo[TITLE_FIELD_NAME] = card.front.decode('utf-8')
            ankiFieldInfo[CONTENT_FIELD_NAME] = card.back.decode('utf-8')
            ankiFieldInfo[GUID_FIELD_NAME]=card.guid
            noteId = self.addNote(deck, modelName,ankiFieldInfo, tag)
            count+=1
        self.stopEditing()
        return count

    def addNote(self, deckName, modelName, fields, tags=list()):
        note = self.createNote(deckName, modelName, fields, tags)
        if note is not None:
            collection = self.collection()
            collection.addNote(note)
            collection.autosave()
            self.startEditing()
            showTooltip("Note added.", 1000);
            return note.id

    def createNote(self, deckName, modelName, fields, tags=list()):
        idDeck=self.decks().id(deckName)
        model=self.models().byName(modelName)
        col=self.collection()
        note = anki.notes.Note(col,model)
        note.model()['did'] = idDeck
        tags=[tags]
        note.tags = tags
        for name, value in fields.items():
            note[name] = value
        return note

    def add_evernote_model(self): #adapted from the IREAD plug-in from Frank
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

    def getGuidsFromAnkiId(self,ids):
        guids=[]
        for a_id in ids:
            card = self.collection().getCard(a_id)
            items=card.note().items()
            if(len(items)==3):
                guids.append(items[2][1])#not a very smart access
        return guids

    def canAddNote(self, deckName, modelName, fields):
        return bool(self.createNote(deckName, modelName, fields))




    def getCardsIdFromTag(self,tag):
        query="tag:"+tag
        ids = self.collection().findCards(query)
        showTooltip(ids)
        return ids


    def startEditing(self):
        self.window().requireReset()


    def stopEditing(self):
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
    front=""
    back=""
    guid=""
    def __init__(self, q, a,g):
        self.front=q
        self.back=a
        self.guid=g

class Evernote:

    def __init__(self,token):
        if not mw.col.conf.get('evernoteToken', False):
            #First run of the Plugin we did not save the access key yet
            client = EvernoteClient(
                consumer_key='scriptkiddi-2682',
                consumer_secret='965f1873e4df583c',
                sandbox=True
            )
            request_token = client.get_request_token('https://fap-studios.de/anknotes/index.html')
            url = client.get_authorize_url(request_token)
            showInfo("We will open a Evernote Tab in your browser so you can allow acces to your account")
            openLink(url)
            oauth_verifier = getText(prompt="Please copy the code that showed up, after allowing access, in here")[0]
            auth_token = client.get_access_token(
                        request_token.get('oauth_token'),
                        request_token.get('oauth_token_secret'),
                        oauth_verifier
                    )
            mw.col.conf['evernoteToken'] = auth_token
        else:
            auth_token = mw.col.conf.get('evernoteToken', False)
        self.client= EvernoteClient(token=auth_token, sandbox=True)
        self.noteStore=self.client.get_note_store()

    def parse_query_string(self, authorize_url):
        """Extract the oauth_verifier from the passed url."""
        uargs = authorize_url.split('?')
        vals = {}
        if len(uargs) == 1:
            raise Exception('Invalid Authorization URL')
        for pair in uargs[1].split('&'):
            key, value = pair.split('=', 1)
            vals.update({key:value})
        return vals

    def findTagGuid(self,tag):
        listtags = self.noteStore.listTags()
        for evtag in listtags:
            if(evtag.name==tag):
                return evtag.guid

    def createEvernoteCards(self,guidSet):
        cards=[]
        for g in guidSet:
            title,content=self.getNoteInformations(g)
            cards.append(EvernoteCard(title,content,g))
        return cards


    def findNotesFilterByTagGuids(self,guidsList):
        Evfilter = NoteFilter()
        Evfilter.ascending = False
        Evfilter.tagGuids = guidsList
        spec = NotesMetadataResultSpec()
        spec.includeTitle = True
        noteList=self.noteStore.findNotesMetadata(self.token, Evfilter, 0, 10000, spec)
        guids=[]
        for note in noteList.notes:
            guids.append(note.guid)
            print(note.guid)
        return guids

    def getNoteInformations(self,noteguid):
        wholeNote = self.noteStore.getNote(self.token, noteguid,True,True,False,False)
        return wholeNote.title, wholeNote.content


class Controller:
    def __init__(self):
        self.evernoteTags=mw.col.conf.get('evernoteTagsToImport', "").split(",")
        self.ankiTag=mw.col.conf.get('evernoteDefaultTag', "")
        self.evernoteToken=mw.col.conf.get('evernoteDevKey', "")
        self.keepTags= mw.col.conf.get('evernoteKeepTags', False)=="True"
        self.deck = mw.col.conf.get('evernoteDefaultDeck', "")
        self.anki = Anki()
        self.anki.add_evernote_model()
        self.evernote = Evernote(self.evernoteToken)

    def proceed(self):
        anki_ids=self.anki.getCardsIdFromTag(self.ankiTag)
        anki_guids=self.anki.getGuidsFromAnkiId(anki_ids)
        evernote_guids=self.getEvernoteGuidsFromTag(self.evernoteTags)
        if (ONLY_ADD_NEW):
            noteGuidsToImport=set(evernote_guids)-set(anki_guids)
            n=self.ImportIntoAnki(noteGuidsToImport,self.deck,self.ankiTag)
            showTooltip(str(n) +" cards have been imported")


    def ImportIntoAnki(self,guidSet,deck,tag):
        cards=self.evernote.createEvernoteCards(guidSet)
        number=self.anki.addEvernoteCards(cards,deck,tag)
        return number


    def getEvernoteGuidsFromTag(self,tags):
        noteGuids=[]
        for tag in tags:
            tagGuid=self.evernote.findTagGuid(tag)
            if(tagGuid is not None):
                noteGuids=noteGuids+self.evernote.findNotesFilterByTagGuids([tagGuid])
        return noteGuids

def showTooltip(text, timeOut=3000):
    aqt.utils.tooltip(text, timeOut)

def main():
    showTooltip(str())
    controller=Controller()
    controller.proceed()

action = aqt.qt.QAction("Import from Evernote", aqt.mw)
aqt.mw.connect(action,  aqt.qt.SIGNAL("triggered()"), main)
aqt.mw.form.menuTools.addAction(action)

def setupEverNote(self):
        global evernoteDefaultDeck
        global evernoteDefaultTag
        global evernoteTagsToImport
        global keepEvernoteTags

        layoutTab = self.form.tab_1.layout()
        groupBox = QGroupBox("Evernote Importer")
        layout = QVBoxLayout()

        #Default Deck
        evernoteDefaultDeckLabel = QLabel("Default Deck:")
        evernoteDefaultDeck = QLineEdit()
        evernoteDefaultDeck.setText(mw.col.conf.get('evernoteDefaultDeck', ""))
        layout.insertWidget(int(layout.count())+1, evernoteDefaultDeckLabel)
        layout.insertWidget(int(layout.count())+2, evernoteDefaultDeck)
        evernoteDefaultDeck.connect(evernoteDefaultDeck, SIGNAL("editingFinished()"), updateEvernoteDefaultDeck)

        #Default Tag
        evernoteDefaultTagLabel = QLabel("Default Tag:")
        evernoteDefaultTag = QLineEdit()
        evernoteDefaultTag.setText(mw.col.conf.get('evernoteDefaultTag', ""))
        layout.insertWidget(int(layout.count())+1, evernoteDefaultTagLabel)
        layout.insertWidget(int(layout.count())+2, evernoteDefaultTag)
        evernoteDefaultTag.connect(evernoteDefaultTag, SIGNAL("editingFinished()"), updateEvernoteDefaultTag)

        #Tags to import
        evernoteTagsToImportLabel = QLabel("Tags to import:")
        evernoteTagsToImport = QLineEdit()
        evernoteTagsToImport.setText(mw.col.conf.get('evernoteTagsToImport', ""))
        layout.insertWidget(int(layout.count())+1, evernoteTagsToImportLabel)
        layout.insertWidget(int(layout.count())+2, evernoteTagsToImport)
        evernoteTagsToImport.connect(evernoteTagsToImport, SIGNAL("editingFinished()"), updateEvernoteTagsToImport)

        #keep evernote tags
        keepEvernoteTags = QCheckBox("Keep Evernote Tags", self)
        keepEvernoteTags.setChecked(mw.col.conf.get('evernoteKeepTags', False))
        keepEvernoteTags.stateChanged.connect(updateEvernoteKeepTags)
        layout.insertWidget(int(layout.count())+1, keepEvernoteTags)
        groupBox.setLayout(layout)
        layoutTab.insertWidget(int(layout.count())+1, groupBox)

def updateEvernoteDefaultDeck():
        mw.col.conf['evernoteDefaultDeck'] = evernoteDefaultDeck.text()

def updateEvernoteDefaultTag():
        mw.col.conf['evernoteDefaultTag'] = evernoteDefaultTag.text()

def updateEvernoteTagsToImport():
        mw.col.conf['evernoteTagsToImport'] = evernoteTagsToImport.text()

def updateEvernoteKeepTags():
        mw.col.conf['evernoteKeepTags'] = keepEvernoteTags.isChecked()

Preferences.setupOptions = wrap(Preferences.setupOptions, setupEverNote)
