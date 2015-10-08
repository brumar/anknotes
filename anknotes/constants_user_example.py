#!/usr/bin/env python
# INSTRUCTIONS:
# USE THIS FILE TO OVERRIDE THE MAIN SETTINGS FILE
# RENAME FILE TO constants_user.py
# PREFIX ALL SETTINGS WITH THE constants MODULE REFERENCE AS SHOWN BELOW:
# DON'T FORGET TO REGENERATE ANY VARIABLES THAT DERIVE FROM THE ONES YOU ARE CHANGING

try: 
    from anknotes import constants
except Exception:
    import os
    import imp

    path = os.path.dirname(__file__)
    name = 'constants'
    modfile, modpath, description = imp.find_module(name, [path + '\\'])
    constants = imp.load_module(name, modfile, modpath, description)
    modfile.close()

constants.EVERNOTE.API.IS_SANDBOXED = True 
constants.SETTINGS.EVERNOTE.AUTH_TOKEN = 'anknotesEvernoteAuthToken_' + constants.EVERNOTE.API.CONSUMER_KEY + ("_SANDBOX" if constants.EVERNOTE.API.IS_SANDBOXED else "")                
constants.EVERNOTE.UPLOAD.VALIDATION.AUTOMATED = False
constants.EVERNOTE.UPLOAD.ENABLED = False