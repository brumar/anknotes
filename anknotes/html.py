from HTMLParser import HTMLParser
from anknotes.constants import SETTINGS
from anknotes.db import get_evernote_title_from_guid


class MLStripper(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
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


def strip_tags_and_new_lines(html):
    return strip_tags(html).replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

__text_escape_phrases__ = u'&|&amp;|\'|&apos;|"|&quot;|>|&gt;|<|&lt;'.split('|')
def escape_text(title):
    global __text_escape_phrases__
    for i in range(0, len(__text_escape_phrases__), 2):
        title = title.replace(__text_escape_phrases__[i], __text_escape_phrases__[i + 1])
    return title


def unescape_text(title):
    global __text_escape_phrases__
    for i in range(0, len(__text_escape_phrases__), 2):
        title = title.replace(__text_escape_phrases__[i + 1], __text_escape_phrases__[i])
    title = title.replace("&nbsp;", " ")
    return title

def clean_title(title):
    title = unescape_text(title)
    if isinstance(title, str):
        title = unicode(title, 'utf-8')
    title = title.replace(u'\xa0', ' ')
    return title

def generate_evernote_url(guid):
    ids = get_evernote_account_ids()
    return u'evernote:///view/%s/%s/%s/%s/' % (ids.uid, ids.shard, guid, guid)


def generate_evernote_link_by_type(guid, title=None, link_type=None, value=None, escape=True):
    url = generate_evernote_url(guid)
    if not title: title = get_evernote_title_from_guid(guid)
    if escape: title = escape_text(title)
    style = generate_evernote_html_element_style_attribute(link_type, value)
    html = u"""<a href='%s'><span style='%s'>%s</span></a>""" % (url, style, title)
    # print html
    return html


def generate_evernote_link(guid, title=None, value=None, escape=True):
    return generate_evernote_link_by_type(guid, title, 'Links', value, escape=escape)


def generate_evernote_link_by_level(guid, title=None, value=None, escape=True):
    return generate_evernote_link_by_type(guid, title, 'Levels', value, escape=escape)


def generate_evernote_html_element_style_attribute(link_type, value, bold=True, group=None):
    global evernote_link_colors
    colors = None
    if link_type in evernote_link_colors:
        color_types = evernote_link_colors[link_type]
        if link_type is 'Levels':
            if not value: value = 1
            if not group: group = 'OL' if isinstance(value, int) else 'Modifiers'
            if not value in color_types[group]: group = 'Headers'
            if value in color_types[group]:
                colors = color_types[group][value]
        elif link_type is 'Links':
            if not value: value = 'Default'
            if value in color_types:
                colors = color_types[value]
    if not colors:
        colors = evernote_link_colors['Default']
    colorDefault = colors
    if not isinstance(colorDefault, str) and not isinstance(colorDefault, unicode):
        colorDefault = colorDefault['Default']
    if not colorDefault[-1] is ';': colorDefault += ';'
    style = 'color: ' + colorDefault
    if bold: style += 'font-weight:bold;'
    return style


def generate_evernote_span(title=None, element_type=None, value=None, guid=None, bold=True, escape=True):
    assert title or guid
    if not title: title = get_evernote_title_from_guid(guid)
    if escape: title = escape_text(title)
    style = generate_evernote_html_element_style_attribute(element_type, value, bold)
    html = u"<span style='%s'>%s</span>" % (style, title)
    return html


evernote_link_colors = {
    'Levels': {
        'OL': {
            1: {
                'Default': 'rgb(106, 0, 129);',
                'Hover': 'rgb(168, 0, 204);'
            },
            2: {
                'Default': 'rgb(235, 0, 115);',
                'Hover': 'rgb(255, 94, 174);'
            },
            3: {
                'Default': 'rgb(186, 0, 255);',
                'Hover': 'rgb(213, 100, 255);'
            },
            4: {
                'Default': 'rgb(129, 182, 255);',
                'Hover': 'rgb(36, 130, 255);'
            },
            5: {
                'Default': 'rgb(232, 153, 220);',
                'Hover': 'rgb(142, 32, 125);'
            },
            6: {
                'Default': 'rgb(201, 213, 172);',
                'Hover': 'rgb(130, 153, 77);'
            },
            7: {
                'Default': 'rgb(231, 179, 154);',
                'Hover': 'rgb(215, 129, 87);'
            },
            8: {
                'Default': 'rgb(249, 136, 198);',
                'Hover': 'rgb(215, 11, 123);'
            }
        },
        'Headers': {
            'Auto TOC': 'rgb(11, 59, 225);'
        },
        'Modifiers': {
            'Orange': 'rgb(222, 87, 0);',
            'Orange (Light)': 'rgb(250, 122, 0);',
            'Dark Red/Pink': 'rgb(164, 15, 45);',
            'Pink Alternative LVL1:': 'rgb(188, 0, 88);'
        }
    },
    'Titles': {
        'Field Title Prompt': 'rgb(169, 0, 48);'
    },
    'Links': {
        'See Also': {
            'Default': 'rgb(45, 79, 201);',
            'Hover': 'rgb(108, 132, 217);'
        },
        'TOC': {
            'Default': 'rgb(173, 0, 0);',
            'Hover': 'rgb(196, 71, 71);'
        },
        'Outline': {
            'Default': 'rgb(105, 170, 53);',
            'Hover': 'rgb(135, 187, 93);'
        },
        'AnkNotes': {
            'Default': 'rgb(30, 155, 67);',
            'Hover': 'rgb(107, 226, 143);'
        }
    }
}

evernote_link_colors['Default'] = evernote_link_colors['Links']['Outline']
evernote_link_colors['Links']['Default'] = evernote_link_colors['Default']

enAccountIDs = None


def get_evernote_account_ids():
    global enAccountIDs
    if not enAccountIDs:
        enAccountIDs = EvernoteAccountIDs()
    return enAccountIDs


class EvernoteAccountIDs:
    uid = '0'
    shard = 's100'
    valid = False

    def __init__(self, uid=None, shard=None):
        self.valid = False
        if uid and shard:
            if self.update(uid, shard): return
        try:
            self.uid = mw.col.conf.get(SETTINGS.EVERNOTE_ACCOUNT_UID, SETTINGS.EVERNOTE_ACCOUNT_UID_DEFAULT_VALUE)
            self.shard = mw.col.conf.get(SETTINGS.EVERNOTE_ACCOUNT_SHARD, SETTINGS.EVERNOTE_ACCOUNT_SHARD_DEFAULT_VALUE)
        except:
            self.uid = SETTINGS.EVERNOTE_ACCOUNT_UID_DEFAULT_VALUE
            self.shard = SETTINGS.EVERNOTE_ACCOUNT_SHARD_DEFAULT_VALUE
            return

    def update(self, uid, shard):
        if not uid or not shard: return False
        if uid == '0' or shard == 's100': return False
        try:
            mw.col.conf[SETTINGS.EVERNOTE_ACCOUNT_UID] = uid
            mw.col.conf[SETTINGS.EVERNOTE_ACCOUNT_SHARD] = shard
        except:
            return False
        self.uid = uid
        self.shard = shard
        self.valid = True
