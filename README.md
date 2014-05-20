# Evernote2Anki Importer (beta)
**Forks and suggestions are very welcome.**
## Description
An Anki plug-in aiming for syncing evernote account with anki directly from anki.
Very rudimentary for the moment. I wait for suggestions according to the needs of evernote/anki users.

## Users : How to use it
- download everything, move it to your Anki/addons directory
- get your developper token at [this page] (https://www.evernote.com/api/DeveloperToken.action). As this token provide a direct access to your evernote account, keep it private !
- right-click+edit options.cfg inside the folder evernoteLib  in your add-ons directory (can be open via Anki)
- paste your token to complete the evernote_token field
- edit the four other fields according to your preferences
## Features and further development

####Current feature :
- Import all the notes from evernote with selected tags
- Possibility to choose the name of the deck, as well as the default tag in anki (but should not be changed)
- Does not import twice a card (only new cards are imported)

####Desirable new features (?) :
- A window allowing the user to change the options (instead of manual edit of options.cfg)
- Updating anki cards accordingly the edit of evernote notes.

####Needed :
- Following the normal Oauth flowchart of evernote (asking the user its developper token is not a good practice) [something like this](https://gist.github.com/inkedmn/5041037)



