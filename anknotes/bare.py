# -*- coding: utf-8 -*-
import os
import os.path
import re
import pprint
from HTMLParser import HTMLParser
from datetime import datetime, timedelta
import shutil
import time
import errno
import socket
import copy
from ankEnums import AutoNumber, EvernoteTitleLevels
from ankAnki import AnkiNotePrototype
import ankShared, ankConsts as ank, ankEvernote as EN 
from ankShared import *
try:    from pysqlite2 import dbapi2 as sqlite
except ImportError: from sqlite3 import dbapi2 as sqlite

Error = sqlite.Error 
ankShared.dbLocal = True 
			     		
ankShared.testMethodAvi()
testMethodAvi()

# Parts = EvernoteTitleLevels.Parts 
NoteDB = EN.Notes() 

# NoteDB.populateAllRootTitles()
NoteDB.populateAllRootNotesWithoutTOCOrOutlineDesignation()