# -*- coding: utf-8 -*-
### Python Imports
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite
import os
import re
import sys
from fnmatch import fnmatch
from bs4 import UnicodeDammit

### Check if in Anki
inAnki = 'anki' in sys.modules

### Anknotes Imports
from anknotes.constants import *
from anknotes.base import *
from anknotes.imports import *
from anknotes.logging import *
from anknotes.db import *
from anknotes.html import *
from anknotes.structs import *

if inAnki:
    from aqt import mw
    from aqt.qt import QIcon, QPixmap, QPushButton, QMessageBox
    from anknotes.evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode, EDAMUserException, \
        EDAMNotFoundException

class UpdateExistingNotes:
    IgnoreExistingNotes, UpdateNotesInPlace, DeleteAndReAddNotes = range(3)

class EvernoteQueryLocationType:
    RelativeDay, RelativeWeek, RelativeMonth, RelativeYear, AbsoluteDate, AbsoluteDateTime = range(6)
    
def get_tag_names_to_import(tagNames, evernoteQueryTags=None, evernoteTagsToDelete=None, keepEvernoteTags=None,
                            deleteEvernoteQueryTags=None):
    def check_tag_name(v, tags_to_delete):
        return v not in tags_to_delete and (not hasattr(v, 'Name') or getattr(v, 'Name') not in tags_to_delete) and (
            not hasattr(v, 'name') or getattr(v, 'name') not in tags_to_delete)
    if keepEvernoteTags is None:
        keepEvernoteTags = mw.col.conf.get(SETTINGS.ANKI.TAGS.KEEP_TAGS,
                                                                    SETTINGS.ANKI.TAGS.KEEP_TAGS_DEFAULT_VALUE)
    if not keepEvernoteTags:
        return {} if isinstance(tagNames, dict) else []
    if evernoteQueryTags is None:
        evernoteQueryTags = mw.col.conf.get(SETTINGS.EVERNOTE.QUERY.TAGS,
                                                                      SETTINGS.EVERNOTE.QUERY.TAGS_DEFAULT_VALUE).replace(
        ',', ' ').split()
    if deleteEvernoteQueryTags is None:
        deleteEvernoteQueryTags = mw.col.conf.get(
        SETTINGS.ANKI.TAGS.DELETE_EVERNOTE_QUERY_TAGS, False)
    if evernoteTagsToDelete is None:
        evernoteTagsToDelete = mw.col.conf.get(SETTINGS.ANKI.TAGS.TO_DELETE, "").replace(
        ',', ' ').split()
    tags_to_delete = evernoteQueryTags if deleteEvernoteQueryTags else [] + evernoteTagsToDelete
    if isinstance(tagNames, dict):
        return {k: v for k, v in tagNames.items() if check_tag_name(v, tags_to_delete)}
    return sorted([v for v in tagNames if check_tag_name(v, tags_to_delete)])


def find_evernote_guids(content):
    return [x.group('guid') for x in
            re.finditer(r'\b(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b', content)]


def find_evernote_links_as_guids(content):
    return [x.Guid for x in find_evernote_links(content)]


def replace_evernote_web_links(content):
    return re.sub(
        r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
        r'evernote:///view/\2/\1/\3/\3/', content)

def matches_list(item, lst):
    item = item.lower()
    for index, value in enumerate(item_to_list(lst)):
        value = value.lower()
        if fnmatch(item, value) or fnmatch(item + 's', value):
            return index 
    return -1 

def find_evernote_links(content):
    """

    :param content:
    :return:
    :rtype : list[EvernoteLink]
    """
    # .NET regex saved to regex.txt as 'Finding Evernote Links'
    content = replace_evernote_web_links(content)
    regex_str = r"""(?si)<a href=["'](?P<URL>evernote:///?view/(?P<uid>[\d]+?)/(?P<shard>s\d+)/(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/(?P=guid)/?)["''](?:[^>]+)?>(?P<title>.+?)</a>"""
    ids = get_evernote_account_ids()
    if not ids.Valid:
        match = re.search(regex_str, content)
        if match:
            ids.update(match.group('uid'), match.group('shard'))
    return [EvernoteLink(m) for m in re.finditer(regex_str, content)]


def check_evernote_guid_is_valid(guid):
    return ankDB().exists(where="guid = '%s'" % guid)


def escape_regex(str_): return re.sub(r"(?sx)(\(|\||\))", r"\\\1", str_)


def remove_evernote_link(link, html):
    html = UnicodeDammit(html, ['utf-8'], is_html=True).unicode_markup
    link_converted = UnicodeDammit(link.WholeRegexMatch, ['utf-8'], is_html=True).unicode_markup
    sep = u'<span style="color: rgb(105, 170, 53);"> | </span>'
    sep_regex = escape_regex(sep)
    no_start_tag_regex = r'[^<]*'
    regex_replace = r'<{0}[^>]*>[^<]*{1}[^<]*</{0}>'
    # html = re.sub(regex_replace.format('li', link.WholeRegexMatch), "", html)
    # Remove link 
    html = html.replace(link.WholeRegexMatch, "")
    # Remove empty li
    html = re.sub(regex_replace.format('li', no_start_tag_regex), "", html)
    # Remove dangling separator 
    
    regex_span = regex_replace.format('span', no_start_tag_regex) + no_start_tag_regex + sep_regex
    html = re.sub(regex_span, "", html)
    # Remove double separator 
    html = re.sub(sep_regex + no_start_tag_regex + sep_regex, sep_regex, html)
    return html


def get_dict_from_list(lst, keys_to_ignore=list()):
    dic = {}
    for key, value in lst:
        if not key in keys_to_ignore:
            dic[key] = value
    return dic


_regex_see_also = None


def update_regex():
    global _regex_see_also
    regex_str = file(os.path.join(FOLDERS.ANCILLARY, 'regex-see_also.txt'), 'r').read()
    regex_str = regex_str.replace('(?<', '(?P<')
    _regex_see_also = re.compile(regex_str, re.UNICODE | re.VERBOSE | re.DOTALL)


def regex_see_also():
    global _regex_see_also
    if not _regex_see_also:
        update_regex()
    return _regex_see_also
