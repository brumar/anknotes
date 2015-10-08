import os
import re
from HTMLParser import HTMLParser

PATH = os.path.dirname(os.path.abspath(__file__))
ANKNOTES_TEMPLATE_FRONT = 'FrontTemplate.htm'
MODEL_EVERNOTE_DEFAULT = 'evernote_note'
MODEL_EVERNOTE_REVERSIBLE = 'evernote_note_reversible'
MODEL_EVERNOTE_REVERSE_ONLY = 'evernote_note_reverse_only'
MODEL_EVERNOTE_CLOZE = 'evernote_note_cloze'
MODEL_TYPE_CLOZE = 1

TEMPLATE_EVERNOTE_DEFAULT = 'EvernoteReview'
TEMPLATE_EVERNOTE_REVERSED = 'EvernoteReviewReversed'
TEMPLATE_EVERNOTE_CLOZE = 'EvernoteReviewCloze'
FIELD_TITLE = 'title'
FIELD_CONTENT = 'content'
FIELD_SEE_ALSO = 'See Also'
FIELD_EXTRA = 'Extra'
FIELD_EVERNOTE_GUID = 'Evernote GUID'

EVERNOTE_TAG_REVERSIBLE = '#Reversible'
EVERNOTE_TAG_REVERSE_ONLY = '#Reversible_Only'

TABLE_SEE_ALSO = "anknotes_see_also"
TABLE_TOC = "anknotes_toc"

SETTING_KEEP_EVERNOTE_TAGS_DEFAULT_VALUE = True
SETTING_EVERNOTE_TAGS_TO_IMPORT_DEFAULT_VALUE = "#Anki_Import"
SETTING_DEFAULT_ANKI_TAG_DEFAULT_VALUE = "#Evernote"
SETTING_DEFAULT_ANKI_DECK_DEFAULT_VALUE = "Evernote"

SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT = 'anknotesDeleteEvernoteTagsToImport'
SETTING_UPDATE_EXISTING_NOTES = 'anknotesUpdateExistingNotes'
SETTING_EVERNOTE_AUTH_TOKEN = 'anknotesEvernoteAuthToken'
SETTING_KEEP_EVERNOTE_TAGS = 'anknotesKeepEvernoteTags'
SETTING_EVERNOTE_TAGS_TO_IMPORT = 'anknotesEvernoteTagsToImport'
# Deprecated
# SETTING_DEFAULT_ANKI_TAG = 'anknotesDefaultAnkiTag'
SETTING_DEFAULT_ANKI_DECK = 'anknotesDefaultAnkiDeck'

evernote_cloze_count = 0


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


class AnkiNotePrototype:
    fields = {}
    tags = []
    evernote_tags_to_import = []
    model_name = MODEL_EVERNOTE_DEFAULT

    def __init__(self, fields, tags, evernote_tags_to_import=list()):
        self.fields = fields
        self.tags = tags
        self.evernote_tags_to_import = evernote_tags_to_import

        self.process_note()

    @staticmethod
    def evernote_cloze_regex(match):
        global evernote_cloze_count
        matchText = match.group(1)
        if matchText[0] == "#":
            matchText = matchText[1:]
        else:
            evernote_cloze_count += 1
        if evernote_cloze_count == 0:
            evernote_cloze_count = 1

        # print "Match: Group #%d: %s" % (evernote_cloze_count, matchText)
        return "{{c%d::%s}}" % (evernote_cloze_count, matchText)

    def process_note_see_also(self):
        if not FIELD_SEE_ALSO in self.fields or not FIELD_EVERNOTE_GUID in self.fields:
            return

        note_guid = self.fields[FIELD_EVERNOTE_GUID]
        # mw.col.db.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY, note_guid TEXT, uid INTEGER, shard TEXT, guid TEXT, html TEXT, text TEXT ) " % TABLE_SEE_ALSO)  
        # mw.col.db.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY, note_guid TEXT, uid INTEGER, shard TEXT, guid TEXT, title TEXT ) " % TABLE_TOC)        
        # mw.col.db.execute("DELETE FROM %s WHERE note_guid = '%s' " % (TABLE_SEE_ALSO, note_guid))
        # mw.col.db.execute("DELETE FROM %s WHERE note_guid = '%s' " % (TABLE_TOC, note_guid))


        print "Running See Also"
        iter = re.finditer(
            r'<a href="(?P<URL>evernote:///?view/(?P<uid>[\d]+)/(?P<shard>s\d+)/(?P<guid>[\w\-]+)/(?P=guid)/?)"(?: shape="rect")?>(?P<Title>.+?)</a>',
            self.fields[FIELD_SEE_ALSO])
        for match in iter:
            title_text = strip_tags(match.group('Title'))
            print "Link: %s: %s" % (match.group('guid'), title_text)
            # for id, ivl in mw.col.db.execute("select id, ivl from cards limit 3"):




            # .NET Regex: <a href="(?<URL>evernote:///?view/(?<uid>[\d]+)/(?<shard>s\d+)/(?<guid>[\w\-]+)/\k<guid>/?)"(?: shape="rect")?>(?<Title>.+?)</a>
            # links_match

    def process_note_content(self):
        if not FIELD_CONTENT in self.fields:
            return
        content = self.fields[FIELD_CONTENT]
        ################################## Step 1: Modify Evernote Links
        # We need to modify Evernote's "Classic" Style Note Links due to an Anki bug with executing the evernote command with three forward slashes.
        # For whatever reason, Anki cannot handle evernote links with three forward slashes, but *can* handle links with two forward slashes.
        content = content.replace("evernote:///", "evernote://")

        # Modify Evernote's "New" Style Note links that point to the Evernote website. Normally these links open the note using Evernote's web client.
        # The web client then opens the local Evernote executable. Modifying the links as below will skip this step and open the note directly using the local Evernote executable
        content = re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([\w\d\-]+)',
                         r'evernote://view/\2/\1/\3/\3/', content)

        ################################## Step 2: Modify Image Links        
        # Currently anknotes does not support rendering images embedded into an Evernote note. 
        # As a work around, this code will convert any link to an image on Dropbox, to an embedded <img> tag. 
        # This code modifies the Dropbox link so it links to a raw image file rather than an interstitial web page
        # Step 2.1: Modify HTML links to Dropbox images
        dropbox_image_url_regex = r'(?P<URL>https://www.dropbox.com/s/[\w\d]+/.+\.(jpg|png|jpeg|gif|bmp))(?P<QueryString>\?dl=(?:0|1))?'
        dropbox_image_src_subst = r'<a href="\g<URL>}\g<QueryString>}" shape="rect"><img src="\g<URL>?raw=1" alt="Dropbox Link %s Automatically Generated by Anknotes" /></a>'
        content = re.sub(r'<a href="%s".*?>(?P<Title>.+?)</a>' % dropbox_image_url_regex,
                         dropbox_image_src_subst % "'\g<Title>'", content)

        # Step 2.2: Modify Plain-text links to Dropbox images
        content = re.sub(dropbox_image_url_regex, dropbox_image_src_subst % "From Plain-Text Link", content)

        # Step 2.3: Modify HTML links with the inner text of exactly "(Image Link)"
        content = re.sub(r'<a href="(?P<URL>.+)"[^>]+>(?P<Title>\(Image Link.*\))</a>',
                         r'''<img src="\g<URL>" alt="'\g<Title>' Automatically Generated by Anknotes" /> <BR><a href="\g<URL>">\g<Title></a>''',
                         content)

        ################################## Step 3: Change white text to transparent 
        # I currently use white text in Evernote to display information that I want to be initially hidden, but visible when desired by selecting the white text.
        # We will change the white text to a special "occluded" CSS class so it can be visible on the back of cards, and also so we can adjust the color for the front of cards when using night mode
        content = content.replace('<span style="color: rgb(255, 255, 255);">', '<span class="occluded">')

        ################################## Step 4: Automatically Occlude Text in <<Double Angle Brackets>>
        content = re.sub(r'&lt;&lt;(.+?)&gt;&gt;', r'&lt;&lt;<span class="occluded">$1</span>&gt;&gt;', content)

        ################################## Step 5: Create Cloze fields from shorthand. Syntax is {Text}. Optionally {#Text} will prevent the Cloze # from incrementing.
        content = re.sub(r'{(.+?)}', self.evernote_cloze_regex, content)

        ################################## Step 6: Process "See Also: " Links
        # .NET regex: (?<PrefixStrip><div><b><span style="color: rgb\(\d{1,3}, \d{1,3}, \d{1,3}\);"><br/></span></b></div>)?(?<SeeAlso>(?<SeeAlsoPrefix><div>)(?<SeeAlsoHeader><span style="color: rgb\(45, 79, 201\);"><b>See Also:(?:&nbsp;)?</b></span>|<b><span style="color: rgb\(45, 79, 201\);">See Also:</span></b>)(?<SeeAlsoContents>.+))(?<Suffix></en-note>)
        see_also_match = re.search(
            r'(?:<div><b><span style="color: rgb\(\d{1,3}, \d{1,3}, \d{1,3}\);"><br/></span></b></div>)?(?P<SeeAlso>(?:<div>)(?:<span style="color: rgb\(45, 79, 201\);"><b>See Also:(?:&nbsp;)?</b></span>|<b><span style="color: rgb\(45, 79, 201\);">See Also:</span></b>) ?(?P<SeeAlsoLinks>.+))(?P<Suffix></en-note>)',
            content)
        # see_also_match = re.search(r'(?P<PrefixStrip><div><b><span style="color: rgb\(\d{1,3}, \d{1,3}, \d{1,3}\);"><br/></span></b></div>)?(?P<SeeAlso>(?:<div>)(?P<SeeAlsoHeader><span style="color: rgb\(45, 79, 201\);">(?:See Also|<b>See Also:</b>).*?</span>).+?)(?P<Suffix></en-note>)', content) 

        if see_also_match:
            content = content.replace(see_also_match.group(0), see_also_match.group('Suffix'))
            self.fields[FIELD_SEE_ALSO] = see_also_match.group('SeeAlso')
            self.process_note_see_also()

        ################################## Note Processing complete. 
        self.fields[FIELD_CONTENT] = content

    def process_note(self):
        self.model_name = MODEL_EVERNOTE_DEFAULT
        # Process Note Content 
        self.process_note_content()

        # Dynamically determine Anki Card Type 
        if FIELD_CONTENT in self.fields and "{{c1:
            :" in self.fields[FIELD_CONTENT]:
            self.model_name = MODEL_EVERNOTE_CLOZE
        elif EVERNOTE_TAG_REVERSIBLE in self.tags:
            self.model_name = MODEL_EVERNOTE_REVERSIBLE
            if True:  # if mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True):
                self.tags.remove(EVERNOTE_TAG_REVERSIBLE)
        elif EVERNOTE_TAG_REVERSE_ONLY in self.tags:
            model_name = MODEL_EVERNOTE_REVERSE_ONLY
            if True:  # if mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True):
                self.tags.remove(EVERNOTE_TAG_REVERSE_ONLY)

        # Remove Evernote Tags to Import
        if True:  # if mw.col.conf.get(SETTING_DELETE_EVERNOTE_TAGS_TO_IMPORT, True):
            for tag in self.evernote_tags_to_import:
                self.tags.remove(tag)


def test_anki(title, guid, filename=""):
    if not filename:
        filename = title
    fields = {
        FIELD_TITLE:         title, FIELD_CONTENT: file(os.path.join(PATH, filename + ".enex"), 'r').read(),
        FIELD_EVERNOTE_GUID: guid
    }
    tags = ['NoTags', 'NoTagsToRemove']
    en_tags = ['NoTagsToRemove']
    return AnkiNotePrototype(fields, tags, en_tags)


title = "Test title"
content = file(os.path.join(PATH, ANKNOTES_TEMPLATE_FRONT), 'r').read()
anki_note_prototype = test_anki("CNS Lesions Presentations Neuromuscular", '301a42d6-7ce5-4850-a365-cd1f0e98939d')
print "EN GUID: " + anki_note_prototype.fields[FIELD_EVERNOTE_GUID]
