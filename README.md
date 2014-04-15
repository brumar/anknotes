# Evernote2Anki Importer (beta)
## Description
An Anki plug-in aiming for syncing evernote account with anki directly from anki.
Very rudimentary for the moment. I wait for suggestions according to the needs of evernote/anki users.

## How to use it
- download everything, move it to your Anki/addons directory
- go get your developper token at [this page] (https://www.evernote.com/api/DeveloperToken.action). As this token provide a direct access to your evernote account, keep it private !
- right-click edit options.cfg inside the folder evernoteLib  
- paste your token to complete the evernote_token field
- edit the other files according to your preferences

**Forks and suggestions are very welcome.**

####Current feature :
- Import all the notes from evernote with selected tags
- Possibility to choose the name of the deck, as well as the default tag in anki (but should not be changed)
- Does not import twice a card (only new cards are imported)

####Desirable new features (?) :
- A window to change the options (instead of manual edit of options.cfg)
- Updating anki cards accordingly the edit of evernote notes.

####Needed :
- Following the normal Oauth flowchart of evernote (asking the user its developper token is not a good practice) [something like this](https://gist.github.com/inkedmn/5041037)



