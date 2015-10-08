import os
import imp
import sys

inAnki = 'anki' in sys.modules

### Anknotes Imports
from anknotes.constants import *


def import_module(name, path=None, sublevels=2, path_suffix=''):
    print "Import " + str(path) + " Level " + str(sublevels)
    if path is None:
        path = os.path.dirname(__file__)
        print "Auto Path " + path
        for i in range(0, sublevels):
            path = os.path.join(path, '..' + os.path.sep)
            print "Path Level " + str(i) + " - " + path
    if path_suffix:
        path = os.path.join(path, path_suffix)
    path = os.path.abspath(path)
    try:
        modfile, modpath, description = imp.find_module(name, [path + os.path.sep])
        modobject = imp.load_module(name, modfile, modpath, description)
    except ImportError as e:
        print path + '\n' + str(e)
        import pdb;
        import traceback;
        print traceback.format_exc();
        pdb.set_trace()
        return None
    try:
        modfile.close()
    except Exception:
        pass
    return modobject


def import_anki_module(name):
    return import_module(name, path_suffix='anki_master' + os.path.sep)


def import_etree():
    global etree
    global inAnki
    if not ANKNOTES.LXML.ENABLE_IN_ANKI and inAnki:
        return False
    if not import_lxml():
        return False
    try:
        from lxml import etree; return True
    except Exception:
        return False


def import_lxml():
    global lxml
    try:
        assert lxml; return True
    except Exception:
        pass
    try:
        import lxml; return True
    except ImportError as e:
        pass
    import os
    import imp
    lxml = import_module('lxml')
    return lxml is not None
