from anknotes.constants import *
### Anki Imports
try:
        from aqt.qt import QIcon, QPixmap
except:
    pass

try:
    icoEvernoteWeb = QIcon(ANKNOTES.ICON_EVERNOTE_WEB)
    icoEvernoteArtcore = QIcon(ANKNOTES.ICON_EVERNOTE_ARTCORE)
    imgEvernoteWeb = QPixmap(ANKNOTES.IMAGE_EVERNOTE_WEB, "PNG")
    imgEvernoteWebMsgBox = imgEvernoteWeb.scaledToWidth(64)
except:
    pass
