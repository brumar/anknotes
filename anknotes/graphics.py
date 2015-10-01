from anknotes.constants import *
### Anki Imports
try:
    from aqt.qt import QIcon, QPixmap
except:
    pass

try:
    icoEvernoteWeb = QIcon(FILES.GRAPHICS.ICON.EVERNOTE_WEB)
    icoEvernoteArtcore = QIcon(FILES.GRAPHICS.ICON.EVERNOTE_ARTCORE)
    icoTomato = QIcon(FILES.GRAPHICS.ICON.TOMATO)
    imgEvernoteWeb = QPixmap(FILES.GRAPHICS.IMAGE.EVERNOTE_WEB, "PNG")
    imgEvernoteWebMsgBox = imgEvernoteWeb.scaledToWidth(64)
except:
    pass
