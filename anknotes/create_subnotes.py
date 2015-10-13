# -*- coding: utf-8 -*-
# Python Imports
from bs4 import BeautifulSoup, NavigableString, Tag
from copy import copy

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite
# Anknotes Shared Imports
from anknotes.shared import *
from anknotes.imports import import_lxml
from anknotes.constants import *
from anknotes.counters import DictCaseInsensitive
from anknotes.logging import show_tooltip
from anknotes.base import matches_list, fmt

# Anknotes Main Imports
import anknotes.Controller
# from anknotes.Controller import Controller

# Anki Imports
from aqt.qt import SIGNAL, QMenu, QAction
from aqt import mw
from aqt.utils import getText

def create_subnotes(guids):
    def create_subnote(guid):
        def process_lists(note, lst, levels=None, names=None):                            
            def add_log_entry(title, content, filename=None, prefix_content=True, title_pad=16, **kw):
                names_padded = u''.join(map(lambda x: (x+':').ljust(33) + ' ', names[1:-1])) + names[-1]
                fmts = dict(levels_pad=u'\t' * level, levels=u'.'.join(map(str, levels)),
                            num_levels=len(levels), names=u': '.join(names[1:]).ljust(20),
                            names_padded=names_padded)
                fmts['levels_str'] = (fmts['levels'] + ':').ljust(6)
                if prefix_content:
                    fmts['content'] = content
                    content = u'{levels_pad}{levels_str} {content}'
                if isinstance(lst_items, Tag) and lst_items.name in list_tag_names:
                    fmts['list_name'] = list_tag_names[lst_items.name]
                content = fmt(content, 0, fmts)
                if title:
                    title = (fmt(title, 0, fmts) + u': ').ljust(title_pad)
                l.go(title + content, filename, **kw)

            def process_tag():
                def get_log_fn():
                    return u'.'.join(map(str, levels)) + u' - ' + u'-'.join(names[1:])
                def log_tag():                    
                    if not lst_items.contents:
                        add_log_entry('NO TOP TEXT', conv_unicode(lst_items.contents), crosspost='no_top_text')
                    if lst_items.name in list_tag_names:
                        add_log_entry('{list_name}', '{levels_pad}[{num_levels}] {levels}', prefix_content=False)
                    elif lst_items.name != 'li':
                        add_log_entry('OTHER TAG', conv_unicode(lst_items.contents[0]) if lst_items.contents else u'N/A')
                    elif not sublist.is_subnote:
                        add_log_entry('LIST ITEM', strip_tags(u''.join(sublist.list_items), True).strip())
                    else:
                        subnote_fn = u'..\\subnotes\\process_tag*\\' + get_log_fn()
                        subnote_shared = '*\\..\\..\\subnotes\\process_tag-all'
                        l.banner(u': '.join(names), subnote_fn)
                        if not create_subnote.logged_subnote:
                            l.blank(subnote_shared)
                            l.banner(title, subnote_shared, clear=False, append_newline=False)
                            l.banner(title, '..\\subnotes\\process_tag')
                            create_subnote.logged_subnote = True
                        add_log_entry('SUBNOTE', sublist.heading)
                        add_log_entry('', sublist.heading, '..\\subnotes\\process_tag', crosspost=subnote_fn)
                        add_log_entry('{levels}', '{names_padded}', subnote_shared, prefix_content=False, title_pad=13)
                        l.go(unicode(sublist.subnote), subnote_fn) 

                def add_note(sublist, new_levels, new_names):
                    subnote_html = unicode(sublist.subnote)
                    log_fn = u'..\\subnotes\\add_note*\\' + get_log_fn()
                    add_log_entry('SUBNOTE', '{levels_str} {names}: \n%s\n' % subnote_html, '..\\subnotes\\add_note', crosspost=log_fn, prefix_content=False)
                    myNotes.append([new_levels, new_names, subnote_html])                
                
                def process_list_item(contents):
                    def check_subnote(li, sublist):
                        def check_heading_flags():
                            if not isinstance(sublist.heading_flags, list):
                                sublist.heading_flags = []
                            for str_ in "`':":
                                if sublist.heading.endswith(str_):
                                    sublist.heading_flags.append(str_)
                                    sublist.heading = sublist.heading[:-1*len(str_)]
                                    check_heading_flags()
                                    return

                        #Begin check_subnote()
                        if not (isinstance(li, Tag) and (li.name in list_tag_names) and li.contents and li.contents[0]):
                            sublist.list_items.append(unicode(li))
                            return sublist
                        sublist.heading = strip_tags(unicode(''.join(sublist.list_items)), True).strip()
                        sublist.base_title = u': '.join(names).replace(title + ': ', '')
                        sublist.is_reversible = not matches_list(sublist.heading, HEADINGS.NOT_REVERSIBLE) 
                        check_heading_flags()
                        if "`" in sublist.heading_flags:
                            sublist.is_reversible = not sublist.is_reversible
                        sublist.use_descriptor = "'" in sublist.heading_flags or "`" in sublist.heading_flags
                        sublist.is_subnote = ':' in sublist.heading_flags or matches_list(sublist.heading, HEADINGS.TOP + '|' + HEADINGS.BOTTOM)
                        if not sublist.is_subnote:
                            return sublist
                        sublist.subnote = li
                        return sublist                    
                    
                    # Begin process_list_item()
                    sublist = DictCaseInsensitive(is_subnote=False, list_items=[])
                    for li in contents:
                        sublist = check_subnote(li, sublist)
                        if sublist.is_subnote:
                            break
                    return sublist                        
                
                # Begin process_tag()                
                new_levels = levels[:]
                new_names = names[:]
                if lst_items.name in list_tag_names:
                    new_levels.append(0)
                    new_names.append('CHILD ' + lst_items.name.upper())
                elif lst_items.name == 'li':
                    levels[-1] = new_levels[-1] = levels[-1] + 1
                    sublist = process_list_item(lst_items.contents)                    
                    if sublist.is_subnote:                        
                        names[-1] = new_names[-1] = sublist.heading
                        add_note(sublist, new_levels, new_names)
                    else:
                        names[-1] = new_names[-1] = sublist.heading if sublist.heading else 'Xx' + strip_tags(unicode(''.join(sublist.list_items)), True).strip()
                log_tag()
                if lst_items.name in list_tag_names or lst_items.name == 'li':
                    process_lists(note, lst_items.contents, new_levels, new_names)

            # Begin process_lists()
            if levels is None or names is None:
                levels = []
                names = [title]
            level = len(levels)
            for lst_items in lst:
                if isinstance(lst_items, Tag):
                    process_tag()
                elif isinstance(lst_items, NavigableString):
                    add_log_entry('NAV STRING', unicode(lst_items).strip(), crosspost=['nav_strings', '*\\..\\..\\nav_strings'])
                else:
                    add_log_entry('LST ITEMS', lst_items.__class__.__name__, crosspost=['unexpected-type', '*\\..\\..\\unexpected-type'])

        #Begin create_subnote()
        content = db.scalar("guid = ?", guid, columns='content')
        title = note_title = get_evernote_title_from_guid(guid)
        l.path_suffix = '\\' + title
        soup = BeautifulSoup(content)
        en_note = soup.find('en-note')
        note = DictCaseInsensitive(descriptor=None)
        first_div = en_note.find('div')
        if first_div:
            descriptor_text = first_div.text
            if descriptor_text.startswith('`'):
                note.descriptor = descriptor_text[1:]
        lists = en_note.find(['ol', 'ul'])
        lists_all = soup.findAll(['ol', 'ul'])
        l.banner(title, crosspost='strings')
        create_subnote.logged_subnote = False
        process_lists(note, [lists])
        l.go(unicode(lists), 'lists', clear=True)
        l.go(soup.prettify(), 'full', clear=True)

    #Begin create_subnotes()
    list_tag_names = {'ul': 'UNORDERED LIST', 'ol': 'ORDERED LIST'}
    db = ankDB()
    myNotes = []
    if import_lxml() is False:
        return False
    from anknotes.imports import lxml
    l = Logger('Create Subnotes\\', default_filename='bs4', timestamp=False, rm_path=True)
    l.base_path += 'notes\\'
    for guid in guids:
        create_subnote(guid)

