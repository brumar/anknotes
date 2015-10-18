# -*- coding: utf-8 -*-
import os

PATH = os.path.dirname(os.path.abspath(__file__))
if os.path.isfile(os.path.join(PATH, 'constants_user.py')):
    from anknotes.constants_user import *
else:
    from anknotes.constants_default import *