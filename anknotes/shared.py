# -*- coding: utf-8 -*-
### Python Imports
try:
	from pysqlite2 import dbapi2 as sqlite
except ImportError:
	from sqlite3 import dbapi2 as sqlite
import os
import re
import sys
### Check if in Anki
inAnki='anki' in sys.modules
### Anknotes Imports
from anknotes.constants import *
from anknotes.logging import *
from anknotes.html import *
from anknotes.structs import *
from anknotes.db import *

### Anki and Evernote Imports
if inAnki:
	from aqt import mw
	from aqt.qt import QIcon, QPixmap, QPushButton, QMessageBox
	from anknotes.evernote.edam.error.ttypes import EDAMSystemException, EDAMErrorCode, EDAMUserException, \
		EDAMNotFoundException

def get_friendly_interval_string(lastImport):
	if not lastImport: return ""
	td = (datetime.now() - datetime.strptime(lastImport, ANKNOTES.DATE_FORMAT))
	days = td.days
	hours, remainder = divmod(td.total_seconds(), 3600)
	minutes, seconds = divmod(remainder, 60)
	if days > 1:
		lastImportStr = "%d days" % td.days
	else:
		hours = round(hours)
		hours_str = '' if hours == 0 else ('1:%2d hr' % minutes) if hours == 1 else '%d Hours' % hours
		if days == 1:
			lastImportStr = "One Day%s" % ('' if hours == 0 else ', ' + hours_str)
		elif hours > 0:
			lastImportStr = hours_str
		else:
			lastImportStr = "%d:%02d min" % (minutes, seconds)
	return lastImportStr

def clean_evernote_css(strr):
	remove_style_attrs = '-webkit-text-size-adjust: auto|-webkit-text-stroke-width: 0px|background-color: rgb(255, 255, 255)|color: rgb(0, 0, 0)|font-family: Tahoma|font-size: medium;|font-style: normal|font-variant: normal|font-weight: normal|letter-spacing: normal|orphans: 2|text-align: -webkit-auto|text-indent: 0px|text-transform: none|white-space: normal|widows: 2|word-spacing: 0px|word-wrap: break-word|-webkit-nbsp-mode: space|-webkit-line-break: after-white-space'.replace(
		'(', '\\(').replace(')', '\\)')
	# 'margin: 0px; padding: 0px 0px 0px 40px; '
	return re.sub(r' ?(%s);? ?' % remove_style_attrs, '', strr).replace(' style=""', '')
class UpdateExistingNotes:
	IgnoreExistingNotes, UpdateNotesInPlace, DeleteAndReAddNotes = range(3)


class EvernoteQueryLocationType:
	RelativeDay, RelativeWeek, RelativeMonth, RelativeYear, AbsoluteDate, AbsoluteDateTime = range(6)

def __check_tag_name__(v, tags_to_delete):
	return v not in tags_to_delete and (not hasattr(v, 'Name') or getattr(v, 'Name') not in tags_to_delete) and (not hasattr(v, 'name') or getattr(v, 'name') not in tags_to_delete)

def get_tag_names_to_import(tagNames, evernoteQueryTags=None, evernoteTagsToDelete=None, keepEvernoteTags=None, deleteEvernoteQueryTags=None):
	if keepEvernoteTags is None: keepEvernoteTags =  mw.col.conf.get(SETTINGS.ANKI.TAGS.KEEP_TAGS, SETTINGS.ANKI.TAGS.KEEP_TAGS_DEFAULT_VALUE)
	if not keepEvernoteTags: return {} if isinstance(tagNames, dict) else []
	if evernoteQueryTags is None: evernoteQueryTags = mw.col.conf.get(SETTINGS.EVERNOTE.QUERY.TAGS, SETTINGS.EVERNOTE.QUERY.TAGS_DEFAULT_VALUE).replace(',', ' ').split()
	if deleteEvernoteQueryTags is None: deleteEvernoteQueryTags = mw.col.conf.get(SETTINGS.ANKI.TAGS.DELETE_EVERNOTE_QUERY_TAGS, False)
	if evernoteTagsToDelete is None: evernoteTagsToDelete = mw.col.conf.get(SETTINGS.ANKI.TAGS.TO_DELETE, "").replace(',', ' ').split()
	tags_to_delete = evernoteQueryTags if deleteEvernoteQueryTags else [] + evernoteTagsToDelete
	if isinstance(tagNames, dict):
		return {k: v for k, v in tagNames.items() if __check_tag_name__(v, tags_to_delete)}
	return sorted([v for v in tagNames if __check_tag_name__(v, tags_to_delete)])

def find_evernote_guids(content):
	return [x.group('guid') for x in re.finditer(r'\b(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b', content)]

def find_evernote_links_as_guids(content):
	return [x.Guid for x in find_evernote_links(content)]

def replace_evernote_web_links(content):
	return re.sub(r'https://www.evernote.com/shard/(s\d+)/[\w\d]+/(\d+)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
				 r'evernote:///view/\2/\1/\3/\3/', content)

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

def get_dict_from_list(lst, keys_to_ignore=list()):
	dic = {}
	for key, value in lst:
		if not key in keys_to_ignore: dic[key] = value
	return dic

_regex_see_also = None

def update_regex():
	global _regex_see_also
	regex_str = file(os.path.join(FOLDERS.ANCILLARY, 'regex-see_also.txt'), 'r').read()
	regex_str = regex_str.replace('(?<', '(?P<')
	_regex_see_also = re.compile(regex_str, re.UNICODE | re.VERBOSE | re.DOTALL)


def regex_see_also():
	global _regex_see_also
	if not _regex_see_also: update_regex()
	return _regex_see_also
