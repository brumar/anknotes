import os, sys, inspect
 # use this if you want to include modules from a subforder
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"evernoteLib")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

import re
import ConfigParser
import anki
import hashlib
import binascii
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.type.ttypes as Types
from evernote.api.client import EvernoteClient
import os, re, codecs
import PyQt4.QtNetwork
import aqt
from aqt.utils import showInfo



# Note: This class was adapted from the Real-Time_Import_for_use_with_the_Rikaisama_Firefox_Extension plug-in by cb4960@gmail.com
#.. itself adapted from Yomichan plugin by Alex Yatskov.

PATH=os.path.dirname(os.path.abspath(__file__))
ONLY_ADD_NEW=True
EVERNOTE_MODEL="evernote_note"
TITLE_FIELD_NAME="title"
CONTENT_FIELD_NAME="content"
GUID_FIELD_NAME="Evernote Guid"

class Options:
    def __init__(self,path):
        self.dictOptions={}
        self.config = ConfigParser.ConfigParser()
        self.config.read(path)

    def getOptions(self,i):
        section=self.config.sections()[i]
        options = self.config.options(section)
        for option in options:
            self.dictOptions[option] = self.config.get(section, option)
        self.formateFields()

    def formateFields(self):
        self.implodeTags("tags_to_import_from_evernote")
        self.turnAsBoolean("keep_evernote_tag_in_anki")

    def turnAsBoolean(self,key):
        self.dictOptions[key]=(self.dictOptions[key]=="true")

    def implodeTags(self,key):
        array=self.dictOptions[key].split(",")
        self.dictOptions[key]=array

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
        self.token=token
        self.client= EvernoteClient(token=token, sandbox=False)
        self.noteStore=self.client.get_note_store()

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
        self.options=Options(PATH+"/evernoteLib/options.cfg")
        self.options.getOptions(0)
        self.evernoteTags=self.options.dictOptions["tags_to_import_from_evernote"]
        self.ankiTag=self.options.dictOptions["default_tag_in_anki"]
        self.evernoteToken=self.options.dictOptions["evernote_token"]
        self.keepTags=self.options.dictOptions["keep_evernote_tag_in_anki"]
        self.deck=self.options.dictOptions["default_deck"]
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
