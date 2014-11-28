# Evernote2Anki Importer (beta)
**Forks and suggestions are very welcome.**

## Description
An Anki plug-in aiming for syncing evernote account with anki directly from anki. It aims to replace a Java standalone application [available here] (https://code.google.com/p/evernote2anki/)
Very rudimentary for the moment. I wait for suggestions according to the needs of evernote/anki users.

## Users : How to use it
- download everything, move it to your Anki/addons directory
- start Anki, fill in the Infromation in the prefrences tap and then press Import from Evernote
-When you run it the first Time a browser tab will open on the evernote site asking you for access to your account
- when you click ok you are taken to a website where the oauth verification key is displayed you paste that key into the open anki windows and click ok with that you are set.

## Features and further development
####Current feature :
- Import all the notes from evernote with selected tags
- Possibility to choose the name of the deck, as well as the default tag in anki (but should not be changed)
- Does not import twice a card (only new cards are imported)
- - A window allowing the user to change the options (instead of manual edit of options.cfg)

####Desirable new features (?) :

- Updating anki cards accordingly the edit of evernote notes.
