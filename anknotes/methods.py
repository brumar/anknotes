# -*- coding: utf-8 -*-
import re
from datetime import datetime

### Anknotes Imports
from anknotes.constants import *
from anknotes.args import Args
from anknotes.imports import in_anki

### Anki Imports
if in_anki():
    from aqt import mw

def create_timer(delay, callback, *a, **kw):
    kw, repeat = Args(kw).get_kwargs(['repeat', False])
    if a or kw:
        def cb(): return callback(*a, **kw)
    else:
        cb = callback
    return mw.progress.timer(abs(delay) * 1000, cb, repeat)