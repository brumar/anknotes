# -*- coding: utf-8 -*-
import sys
import re
from datetime import datetime

### Check if in Anki
inAnki = 'anki' in sys.modules

### Anknotes Imports
from anknotes.constants import *
from anknotes.args import Args

if inAnki:
    from aqt import mw

def create_timer(delay, callback, *a, **kw):
    kw, repeat = Args(kw).get_kwargs(['repeat', False])
    if a or kw:
        def cb(): return callback(*a, **kw)
    else:
        cb = callback
    return mw.progress.timer(abs(delay) * 1000, cb, repeat)