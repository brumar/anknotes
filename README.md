# Anknotes     
Import Evernote notes into Anki. The user page lives there : https://ankiweb.net/shared/info/999519295.

## Features   
- Imports all the notes from evernote given one or various chosen tags.
- Cards are put in the deck chosen by the user, with a specific tag.
- No redundancy. If the user launchs again the import process, only new cards are imported.
- To some extent (see known bugs), the content of the cards can also be kept in sync (Evernote -> Anki).

## Installation   
### Steps to install it normally :   
- In Anki, Tool>Add-ons>Browse and Install. Enter the code `999519295`.   
- Restart anki.   
- In your preferences (within tools), choose the tag of the cards you want to import (if you do not change this value, it will import nothing).   
- Within tools again, click on "import from evernote", and follows the instructions. You will have to give your authorization and get a token in return to paste in a given field. At the end, if anki freezes a bit, it's perfectly normal as it imports your cards.

### Steps to install manually :  
- Open your anki addons. You can find it in anki with tools > addons > open addons folder.   
- Download the zip release of the repository and unzip its content here. Warning : `anknote_start.py` and the anknotes directory must be at the root of your addons folder.  
- Restart anki.   
- In your preferences (within tools), choose the tag of the cards you want to import (if you do not change this value, it will import nothing).   
- Within tools again, click on "import from evernote", and follows the instructions. You will have to give your authorization and get a token in return to paste in a given field. At the end, if anki freezes a bit, it's perfectly normal as it imports your cards.

## Security   
In the previous version, the token granting read access to the user evernote account was stored in the settings of the collection. This was bad practice. Now this token is protected with a password chosen by the user when launching "import from evernote".

## Known bugs to fix      
- If the token expires (after one year), the user is not alerted and the import may fail silently.
- If the token or the user password is wrong, the program fails silently.
- When the user collection is too big, and the user imports with the option "Update", the API usage may reach its limits. The list of cards that are updated is not stored. This list of ids should be kept somewhere to update the cards in an incremental fashion. This is apparently not a problem for classic import because the day of the authorization, a large (or unlimited) number of API calls is authorized.

## Interesting forks:   
- https://github.com/holycrepe/anknotes. Could bring up improvements, but probably buggy.
- https://github.com/rbuc/Evernote2AnkiMac. Works along the evernote MacOS Desktop app and seems to implement nice features.

