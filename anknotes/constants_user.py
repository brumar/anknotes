#!/usr/bin/env python
# INSTRUCTIONS:
# USE THIS FILE TO OVERRIDE THE MAIN SETTINGS FILE
# PREFIX ALL SETTINGS WITH THE constants MODULE REFERENCE AS SHOWN BELOW:
# DON'T FORGET TO REGENERATE ANY VARIABLES THAT DERIVE FROM THE ONES YOU ARE CHANGING

try:
    from anknotes import constants
except ImportError:
    import os
    import imp

    path = os.path.dirname(__file__)
    name = 'constants'

    try:

        modfile, modpath, description = imp.find_module(name, [path + '\\'])
        print(imp.find_module(name, [path + '\\']))
        constants = imp.load_module(name, modfile, modpath, description)
        modfile.close()
    except ImportError as e:
        print(path)
        print(e)


    # constants.EVERNOTE.API.IS_SANDBOXED = True
    # constants.SETTINGS.EVERNOTE.AUTH_TOKEN = 'anknotesEvernoteAuthToken_' + constants.EVERNOTE.API.CONSUMER_KEY + ("_SANDBOX" if constants.EVERNOTE.API.IS_SANDBOXED else "")