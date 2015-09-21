# -*- coding: utf-8 -*-

### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.graphics import *

### Anki Imports
try:
        import anki
        import aqt
        from aqt.preferences import Preferences
        from aqt.utils import getText, openLink, getOnlyText
        from aqt.qt import QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, SIGNAL, QCheckBox, \
        QComboBox, QSpacerItem, QSizePolicy, QWidget, QSpinBox, QFormLayout, QGridLayout, QFrame, QPalette, \
        QRect, QStackedLayout, QDateEdit, QDateTimeEdit, QTimeEdit, QDate, QDateTime, QTime, QPushButton, QIcon, \
        QMessageBox, QPixmap
        from aqt import mw
except:
    pass


class EvernoteQueryLocationValueQSpinBox(QSpinBox):
    __prefix = ""

    def setPrefix(self, text):
        self.__prefix = text

    def prefix(self):
        return self.__prefix

    def valueFromText(self, text):
        if text == self.prefix():
            return 0
        return text[len(self.prefix()) + 1:]

    def textFromValue(self, value):
        if value == 0:
            return self.prefix()
        return self.prefix() + "-" + str(value)


def setup_evernote(self):
    global icoEvernoteWeb
    global imgEvernoteWeb
    global evernote_default_tag
    global evernote_query_any
    global evernote_query_use_tags
    global evernote_query_tags
    global evernote_query_use_notebook
    global evernote_query_notebook
    global evernote_query_use_note_title
    global evernote_query_note_title
    global evernote_query_use_search_terms
    global evernote_query_search_terms
    global evernote_query_use_last_updated
    global evernote_query_last_updated_type
    global evernote_query_last_updated_value_stacked_layout
    global evernote_query_last_updated_value_relative_spinner
    global evernote_query_last_updated_value_absolute_date
    global evernote_query_last_updated_value_absolute_datetime
    global evernote_query_last_updated_value_absolute_time
    global default_anki_deck
    global anki_deck_evernote_notebook_integration
    global keep_evernote_tags
    global delete_evernote_query_tags
    global evernote_pagination_current_page_spinner
    global evernote_pagination_auto_paging

    widget = QWidget()
    layout = QVBoxLayout()


    ########################## QUERY ##########################
    group = QGroupBox("EVERNOTE SEARCH OPTIONS:")
    group.setStyleSheet('QGroupBox{    font-size: 10px;    font-weight: bold;  color: rgb(105, 170, 53);}')
    form = QFormLayout()

    form.addRow(gen_qt_hr())

    # Evernote Query: Match Any Terms
    evernote_query_any = QCheckBox("     Match Any Terms", self)
    evernote_query_any.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_ANY, True))
    evernote_query_any.stateChanged.connect(update_evernote_query_any)
    evernote_query_any.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    button_show_generated_evernote_query = QPushButton(icoEvernoteWeb, "Show Full Query", self)
    button_show_generated_evernote_query.setAutoDefault(False)
    button_show_generated_evernote_query.connect(button_show_generated_evernote_query,
                                                 SIGNAL("clicked()"),
                                                 handle_show_generated_evernote_query)


    # Add Form Row for Match Any Terms
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_any)
    hbox.addWidget(button_show_generated_evernote_query)
    form.addRow("<b>Search Query:</b>", hbox)

    # Evernote Query: Tags
    evernote_query_tags = QLineEdit()
    evernote_query_tags.setText(
        mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_TAGS, SETTINGS.EVERNOTE_QUERY_TAGS_DEFAULT_VALUE))
    evernote_query_tags.connect(evernote_query_tags,
                                SIGNAL("textEdited(QString)"),
                                update_evernote_query_tags)

    # Evernote Query: Use Tags
    evernote_query_use_tags = QCheckBox(" ", self)
    evernote_query_use_tags.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_TAGS, True))
    evernote_query_use_tags.stateChanged.connect(update_evernote_query_use_tags)

    # Add Form Row for Tags
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_use_tags)
    hbox.addWidget(evernote_query_tags)
    form.addRow("Tags:", hbox)

    # Evernote Query: Search Terms
    evernote_query_search_terms = QLineEdit()
    evernote_query_search_terms.setText(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_SEARCH_TERMS, ""))
    evernote_query_search_terms.connect(evernote_query_search_terms,
                                        SIGNAL("textEdited(QString)"),
                                        update_evernote_query_search_terms)

    # Evernote Query: Use Search Terms
    evernote_query_use_search_terms = QCheckBox(" ", self)
    evernote_query_use_search_terms.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_SEARCH_TERMS, False))
    evernote_query_use_search_terms.stateChanged.connect(update_evernote_query_use_search_terms)

    # Add Form Row for Search Terms
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_use_search_terms)
    hbox.addWidget(evernote_query_search_terms)
    form.addRow("Search Terms:", hbox)

    # Evernote Query: Notebook
    evernote_query_notebook = QLineEdit()
    evernote_query_notebook.setText(
        mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_NOTEBOOK, SETTINGS.EVERNOTE_QUERY_NOTEBOOK_DEFAULT_VALUE))
    evernote_query_notebook.connect(evernote_query_notebook,
                                    SIGNAL("textEdited(QString)"),
                                    update_evernote_query_notebook)

    # Evernote Query: Use Notebook
    evernote_query_use_notebook = QCheckBox(" ", self)
    evernote_query_use_notebook.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_NOTEBOOK, False))
    evernote_query_use_notebook.stateChanged.connect(update_evernote_query_use_notebook)

    # Add Form Row for Notebook
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_use_notebook)
    hbox.addWidget(evernote_query_notebook)
    form.addRow("Notebook:", hbox)

    # Evernote Query: Note Title
    evernote_query_note_title = QLineEdit()
    evernote_query_note_title.setText(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_NOTE_TITLE, ""))
    evernote_query_note_title.connect(evernote_query_note_title,
                                      SIGNAL("textEdited(QString)"),
                                      update_evernote_query_note_title)

    # Evernote Query: Use Note Title
    evernote_query_use_note_title = QCheckBox(" ", self)
    evernote_query_use_note_title.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_NOTE_TITLE, False))
    evernote_query_use_note_title.stateChanged.connect(update_evernote_query_use_note_title)

    # Add Form Row for Note Title
    hbox = QHBoxLayout()
    hbox.addWidget(evernote_query_use_note_title)
    hbox.addWidget(evernote_query_note_title)
    form.addRow("Note Title:", hbox)

    # Evernote Query: Last Updated Type
    evernote_query_last_updated_type = QComboBox()
    evernote_query_last_updated_type.setStyleSheet(' QComboBox { color: rgb(45, 79, 201); font-weight: bold; } ')
    evernote_query_last_updated_type.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    evernote_query_last_updated_type.addItems([u"Δ Day", u"Δ Week", u"Δ Month", u"Δ Year", "Date", "+ Time"])
    evernote_query_last_updated_type.setCurrentIndex(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_TYPE,
                                                                     EvernoteQueryLocationType.RelativeDay))
    evernote_query_last_updated_type.activated.connect(update_evernote_query_last_updated_type)


    # Evernote Query: Last Updated Type: Relative Date
    evernote_query_last_updated_value_relative_spinner = EvernoteQueryLocationValueQSpinBox()
    evernote_query_last_updated_value_relative_spinner.setVisible(False)
    evernote_query_last_updated_value_relative_spinner.setStyleSheet(
        " QSpinBox, EvernoteQueryLocationValueQSpinBox { font-weight: bold;  color: rgb(173, 0, 0); } ")
    evernote_query_last_updated_value_relative_spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_query_last_updated_value_relative_spinner.connect(evernote_query_last_updated_value_relative_spinner,
                                                               SIGNAL("valueChanged(int)"),
                                                               update_evernote_query_last_updated_value_relative_spinner)

    # Evernote Query: Last Updated Type: Absolute Date
    evernote_query_last_updated_value_absolute_date = QDateEdit()
    evernote_query_last_updated_value_absolute_date.setDisplayFormat('M/d/yy')
    evernote_query_last_updated_value_absolute_date.setCalendarPopup(True)
    evernote_query_last_updated_value_absolute_date.setVisible(False)
    evernote_query_last_updated_value_absolute_date.setStyleSheet(
        "QDateEdit { font-weight: bold;  color: rgb(173, 0, 0); } ")
    evernote_query_last_updated_value_absolute_date.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_query_last_updated_value_absolute_date.connect(evernote_query_last_updated_value_absolute_date,
                                                            SIGNAL("dateChanged(QDate)"),
                                                            update_evernote_query_last_updated_value_absolute_date)

    # Evernote Query: Last Updated Type: Absolute DateTime
    evernote_query_last_updated_value_absolute_datetime = QDateTimeEdit()
    evernote_query_last_updated_value_absolute_datetime.setDisplayFormat('M/d/yy h:mm AP')
    evernote_query_last_updated_value_absolute_datetime.setCalendarPopup(True)
    evernote_query_last_updated_value_absolute_datetime.setVisible(False)
    evernote_query_last_updated_value_absolute_datetime.setStyleSheet(
        "QDateTimeEdit { font-weight: bold;  color: rgb(173, 0, 0); } ")
    evernote_query_last_updated_value_absolute_datetime.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_query_last_updated_value_absolute_datetime.connect(evernote_query_last_updated_value_absolute_datetime,
                                                                SIGNAL("dateTimeChanged(QDateTime)"),
                                                                update_evernote_query_last_updated_value_absolute_datetime)



    # Evernote Query: Last Updated Type: Absolute Time
    evernote_query_last_updated_value_absolute_time = QTimeEdit()
    evernote_query_last_updated_value_absolute_time.setDisplayFormat('h:mm AP')
    evernote_query_last_updated_value_absolute_time.setVisible(False)
    evernote_query_last_updated_value_absolute_time.setStyleSheet(
        "QTimeEdit { font-weight: bold;  color: rgb(143, 0, 30); } ")
    evernote_query_last_updated_value_absolute_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_query_last_updated_value_absolute_time.connect(evernote_query_last_updated_value_absolute_time,
                                                            SIGNAL("timeChanged(QTime)"),
                                                            update_evernote_query_last_updated_value_absolute_time)

    hbox_datetime = QHBoxLayout()
    hbox_datetime.addWidget(evernote_query_last_updated_value_absolute_date)
    hbox_datetime.addWidget(evernote_query_last_updated_value_absolute_time)

    # Evernote Query: Last Updated Type
    evernote_query_last_updated_value_stacked_layout = QStackedLayout()
    evernote_query_last_updated_value_stacked_layout.addWidget(evernote_query_last_updated_value_relative_spinner)
    evernote_query_last_updated_value_stacked_layout.addItem(hbox_datetime)

    # Evernote Query: Use Last Updated
    evernote_query_use_last_updated = QCheckBox(" ", self)
    evernote_query_use_last_updated.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    evernote_query_use_last_updated.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_LAST_UPDATED, False))
    evernote_query_use_last_updated.stateChanged.connect(update_evernote_query_use_last_updated)

    # Add Form Row for Last Updated
    hbox = QHBoxLayout()
    label = QLabel("Last Updated: ")
    label.setMinimumWidth(100)
    hbox.addWidget(evernote_query_use_last_updated)
    hbox.addWidget(evernote_query_last_updated_type)
    hbox.addWidget(evernote_query_last_updated_value_relative_spinner)
    hbox.addWidget(evernote_query_last_updated_value_absolute_date)
    hbox.addWidget(evernote_query_last_updated_value_absolute_time)
    form.addRow(label, hbox)

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    ############################ PAGINATION ##########################    
    # Evernote Pagination: Current Page                                                                                                   
    evernote_pagination_current_page_spinner = QSpinBox()
    evernote_pagination_current_page_spinner.setStyleSheet("QSpinBox { font-weight: bold;  color: rgb(173, 0, 0);  } ")
    evernote_pagination_current_page_spinner.setPrefix("PAGE: ")
    evernote_pagination_current_page_spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_pagination_current_page_spinner.setValue(mw.col.conf.get(SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE, 1))
    evernote_pagination_current_page_spinner.connect(evernote_pagination_current_page_spinner,
                                                     SIGNAL("valueChanged(int)"),
                                                     update_evernote_pagination_current_page_spinner)

    # Evernote Pagination: Auto Paging
    evernote_pagination_auto_paging = QCheckBox("     Automate", self)
    evernote_pagination_auto_paging.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    evernote_pagination_auto_paging.setFixedWidth(105)
    evernote_pagination_auto_paging.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_AUTO_PAGING, True))
    evernote_pagination_auto_paging.stateChanged.connect(update_evernote_pagination_auto_paging)

    hbox = QHBoxLayout()
    hbox.addWidget(evernote_pagination_auto_paging)
    hbox.addWidget(evernote_pagination_current_page_spinner)

    # Add Form Row for Evernote Pagination
    form.addRow("<b>Pagination:</b>", hbox)

    # Add Query Form to Group Box  
    group.setLayout(form)

    # Add Query Group Box to Main Layout 
    layout.addWidget(group)

    ########################## DECK ##########################
    # label = QLabel("<span style='background-color: #bf0060;'><B><U>ANKI NOTE OPTIONS</U>:</B></span>")
    group = QGroupBox("ANKI NOTE OPTIONS:")
    group.setStyleSheet('QGroupBox{    font-size: 10px;    font-weight: bold;  color: rgb(105, 170, 53);}')
    form = QFormLayout()

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    # Default Anki Deck
    default_anki_deck = QLineEdit()
    default_anki_deck.setText(mw.col.conf.get(SETTINGS.DEFAULT_ANKI_DECK, SETTINGS.DEFAULT_ANKI_DECK_DEFAULT_VALUE))
    default_anki_deck.connect(default_anki_deck, SIGNAL("textEdited(QString)"), update_default_anki_deck)

    # Add Form Row for Default Anki Deck 
    hbox = QHBoxLayout()
    hbox.insertSpacing(0, 33)
    hbox.addWidget(default_anki_deck)
    label_deck = QLabel("<b>Anki Deck:</b>")
    label_deck.setMinimumWidth(100)
    form.addRow(label_deck, hbox)

    # Evernote Notebook Integration
    anki_deck_evernote_notebook_integration = QCheckBox("      Append Evernote Notebook", self)
    anki_deck_evernote_notebook_integration.setChecked(
        mw.col.conf.get(SETTINGS.ANKI_DECK_EVERNOTE_NOTEBOOK_INTEGRATION, True))
    anki_deck_evernote_notebook_integration.stateChanged.connect(update_anki_deck_evernote_notebook_integration)

    # Change Visibility of Deck Options 
    update_anki_deck_visibilities()

    # Add Form Row for Evernote Notebook Integration
    label_deck = QLabel("Evernote Notebook:")
    label_deck.setMinimumWidth(100)
    form.addRow("", anki_deck_evernote_notebook_integration)

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    ############################ TAGS ##########################
    # Keep Evernote Tags
    keep_evernote_tags = QCheckBox("     Save To Anki Note", self)
    keep_evernote_tags.setChecked(
        mw.col.conf.get(SETTINGS.KEEP_EVERNOTE_TAGS, SETTINGS.KEEP_EVERNOTE_TAGS_DEFAULT_VALUE))
    keep_evernote_tags.stateChanged.connect(update_keep_evernote_tags)

    # Evernote Tags: Tags to Delete
    evernote_tags_to_delete = QLineEdit()
    evernote_tags_to_delete.setText(mw.col.conf.get(SETTINGS.EVERNOTE_TAGS_TO_DELETE, ""))
    evernote_tags_to_delete.connect(evernote_tags_to_delete,
                                    SIGNAL("textEdited(QString)"),
                                    update_evernote_tags_to_delete)

    # Delete Tags To Import 
    delete_evernote_query_tags = QCheckBox("     Also Delete Search Tags", self)
    delete_evernote_query_tags.setChecked(mw.col.conf.get(SETTINGS.DELETE_EVERNOTE_TAGS_TO_IMPORT, True))
    delete_evernote_query_tags.stateChanged.connect(update_delete_evernote_query_tags)

    # Add Form Row for Evernote Tag Options
    label = QLabel("<b>Evernote Tags:</b>")
    label.setMinimumWidth(100)
    form.addRow(label, keep_evernote_tags)
    hbox = QHBoxLayout()
    hbox.insertSpacing(0, 33)
    hbox.addWidget(evernote_tags_to_delete)
    form.addRow("Tags to Delete:", hbox)
    form.addRow(" ", delete_evernote_query_tags)

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    ############################ NOTE UPDATING ##########################
    # Note Update Method
    update_existing_notes = QComboBox()
    update_existing_notes.setStyleSheet(
        ' QComboBox { color: #3b679e; font-weight: bold; } QComboBoxItem { color: #A40F2D; font-weight: bold; } ')
    update_existing_notes.addItems(["Ignore Existing Notes", "Update In-Place",
                                    "Delete and Re-Add"])
    update_existing_notes.setCurrentIndex(mw.col.conf.get(SETTINGS.UPDATE_EXISTING_NOTES,
                                                          UpdateExistingNotes.UpdateNotesInPlace))
    update_existing_notes.activated.connect(update_update_existing_notes)

    # Add Form Row for Note Update Method
    hbox = QHBoxLayout()
    hbox.insertSpacing(0, 33)
    hbox.addWidget(update_existing_notes)
    form.addRow("<b>Note Updating:</b>", hbox)

    # Add Note Update Method Form to Group Box  
    group.setLayout(form)

    # Add Note Update Method Group Box to Main Layout 
    layout.addWidget(group)

    # Update Visibilities of Query Options 
    evernote_query_text_changed()
    update_evernote_query_visibilities()


    # Vertical Spacer
    vertical_spacer = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
    layout.addItem(vertical_spacer)

    # Parent Widget
    widget.setLayout(layout)

    # New Tab
    self.form.tabWidget.addTab(widget, "Anknotes")


def gen_qt_hr():
    vbox = QVBoxLayout()
    hr = QFrame()
    hr.setAutoFillBackground(True)
    hr.setFrameShape(QFrame.HLine)
    hr.setStyleSheet("QFrame { background-color: #0060bf; color: #0060bf; }")
    hr.setFixedHeight(2)
    vbox.addWidget(hr)
    vbox.addSpacing(4)
    return vbox


def update_anki_deck_visibilities():
    if not default_anki_deck.text():
        anki_deck_evernote_notebook_integration.setChecked(True)
        anki_deck_evernote_notebook_integration.setEnabled(False)
    else:
        anki_deck_evernote_notebook_integration.setEnabled(True)
        anki_deck_evernote_notebook_integration.setChecked(
            mw.col.conf.get(SETTINGS.ANKI_DECK_EVERNOTE_NOTEBOOK_INTEGRATION, True))


def update_default_anki_deck(text):
    mw.col.conf[SETTINGS.DEFAULT_ANKI_DECK] = text
    update_anki_deck_visibilities()


def update_anki_deck_evernote_notebook_integration():
    if default_anki_deck.text():
        mw.col.conf[
            SETTINGS.ANKI_DECK_EVERNOTE_NOTEBOOK_INTEGRATION] = anki_deck_evernote_notebook_integration.isChecked()


def update_evernote_tags_to_delete(text):
    mw.col.conf[SETTINGS.EVERNOTE_TAGS_TO_DELETE] = text


def update_evernote_query_tags(text):
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_TAGS] = text
    if text: evernote_query_use_tags.setChecked(True)
    evernote_query_text_changed()


def update_evernote_query_use_tags():
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_USE_TAGS] = evernote_query_use_tags.isChecked()
    update_evernote_query_visibilities()


def update_evernote_query_notebook(text):
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_NOTEBOOK] = text
    if text: evernote_query_use_notebook.setChecked(True)
    evernote_query_text_changed()


def update_evernote_query_use_notebook():
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_USE_NOTEBOOK] = evernote_query_use_notebook.isChecked()
    update_evernote_query_visibilities()


def update_evernote_query_note_title(text):
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_NOTE_TITLE] = text
    if text: evernote_query_use_note_title.setChecked(True)
    evernote_query_text_changed()


def update_evernote_query_use_note_title():
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_USE_NOTE_TITLE] = evernote_query_use_note_title.isChecked()
    update_evernote_query_visibilities()


def update_evernote_query_use_last_updated():
    update_evernote_query_visibilities()
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_USE_LAST_UPDATED] = evernote_query_use_last_updated.isChecked()


def update_evernote_query_search_terms(text):
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_SEARCH_TERMS] = text
    if text: evernote_query_use_search_terms.setChecked(True)
    evernote_query_text_changed()
    update_evernote_query_visibilities()


def update_evernote_query_use_search_terms():
    update_evernote_query_visibilities()
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_USE_SEARCH_TERMS] = evernote_query_use_search_terms.isChecked()


def update_evernote_query_any():
    update_evernote_query_visibilities()
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_ANY] = evernote_query_any.isChecked()


def update_keep_evernote_tags():
    mw.col.conf[SETTINGS.KEEP_EVERNOTE_TAGS] = keep_evernote_tags.isChecked()
    evernote_query_text_changed()


def update_delete_evernote_query_tags():
    mw.col.conf[SETTINGS.DELETE_EVERNOTE_TAGS_TO_IMPORT] = delete_evernote_query_tags.isChecked()


def update_evernote_pagination_auto_paging():
    mw.col.conf[SETTINGS.EVERNOTE_AUTO_PAGING] = evernote_pagination_auto_paging.isChecked()


def update_evernote_pagination_current_page_spinner(value):
    if value < 1:
        value = 1
        evernote_pagination_current_page_spinner.setValue(1)
    mw.col.conf[SETTINGS.EVERNOTE_PAGINATION_CURRENT_PAGE] = value


def update_update_existing_notes(index):
    mw.col.conf[SETTINGS.UPDATE_EXISTING_NOTES] = index


def evernote_query_text_changed():
    tags = evernote_query_tags.text()
    search_terms = evernote_query_search_terms.text()
    note_title = evernote_query_note_title.text()
    notebook = evernote_query_notebook.text()
    # tags_active = tags and evernote_query_use_tags.isChecked()
    search_terms_active = search_terms and evernote_query_use_search_terms.isChecked()
    note_title_active = note_title and evernote_query_use_note_title.isChecked()
    notebook_active = notebook and evernote_query_use_notebook.isChecked()
    all_inactive = not (
        search_terms_active or note_title_active or notebook_active or evernote_query_use_last_updated.isChecked())

    if not search_terms:
        evernote_query_use_search_terms.setEnabled(False)
        evernote_query_use_search_terms.setChecked(False)
    else:
        evernote_query_use_search_terms.setEnabled(True)
        evernote_query_use_search_terms.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_SEARCH_TERMS, True))

    if not note_title:
        evernote_query_use_note_title.setEnabled(False)
        evernote_query_use_note_title.setChecked(False)
    else:
        evernote_query_use_note_title.setEnabled(True)
        evernote_query_use_note_title.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_NOTE_TITLE, True))

    if not notebook:
        evernote_query_use_notebook.setEnabled(False)
        evernote_query_use_notebook.setChecked(False)
    else:
        evernote_query_use_notebook.setEnabled(True)
        evernote_query_use_notebook.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_NOTEBOOK, True))

    if not tags and not all_inactive:
        evernote_query_use_tags.setEnabled(False)
        evernote_query_use_tags.setChecked(False)
    else:
        evernote_query_use_tags.setEnabled(True)
        evernote_query_use_tags.setChecked(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_TAGS, True))
        if all_inactive and not tags:
            evernote_query_tags.setText(SETTINGS.EVERNOTE_QUERY_TAGS_DEFAULT_VALUE)


def update_evernote_query_visibilities():
    # is_any =  evernote_query_any.isChecked()
    is_tags = evernote_query_use_tags.isChecked()
    is_terms = evernote_query_use_search_terms.isChecked()
    is_title = evernote_query_use_note_title.isChecked()
    is_notebook = evernote_query_use_notebook.isChecked()
    is_updated = evernote_query_use_last_updated.isChecked()

    # is_disabled_any = not evernote_query_any.isEnabled()
    is_disabled_tags = not evernote_query_use_tags.isEnabled()
    is_disabled_terms = not evernote_query_use_search_terms.isEnabled()
    is_disabled_title = not evernote_query_use_note_title.isEnabled()
    is_disabled_notebook = not evernote_query_use_notebook.isEnabled()
    # is_disabled_updated = not evernote_query_use_last_updated.isEnabled()

    override = (not is_tags and not is_terms and not is_title and not is_notebook and not is_updated)
    if override:
        is_tags = True
        evernote_query_use_tags.setChecked(True)
    evernote_query_tags.setEnabled(is_tags or is_disabled_tags)
    evernote_query_search_terms.setEnabled(is_terms or is_disabled_terms)
    evernote_query_note_title.setEnabled(is_title or is_disabled_title)
    evernote_query_notebook.setEnabled(is_notebook or is_disabled_notebook)
    evernote_query_last_updated_value_set_visibilities()


def update_evernote_query_last_updated_type(index):
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_TYPE] = index
    evernote_query_last_updated_value_set_visibilities()


def evernote_query_last_updated_value_get_current_value():
    index = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_TYPE, 0)
    if index < EvernoteQueryLocationType.AbsoluteDate:
        spinner_text = ['day', 'week', 'month', 'year'][index]
        spinner_val = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_RELATIVE, 0)
        if spinner_val > 0: spinner_text += "-" + str(spinner_val)
        return spinner_text

    absolute_date_str = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE,
                                        "{:%Y %m %d}".format(datetime.now() - timedelta(days=7))).replace(' ', '')
    if index == EvernoteQueryLocationType.AbsoluteDate:
        return absolute_date_str
    absolute_time_str = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME,
                                        "{:HH mm ss}".format(datetime.now())).replace(' ', '')
    return absolute_date_str + "'T'" + absolute_time_str


def evernote_query_last_updated_value_set_visibilities():
    index = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_TYPE, 0)
    if not evernote_query_use_last_updated.isChecked():
        evernote_query_last_updated_type.setEnabled(False)
        evernote_query_last_updated_value_absolute_date.setEnabled(False)
        evernote_query_last_updated_value_absolute_time.setEnabled(False)
        evernote_query_last_updated_value_relative_spinner.setEnabled(False)
        return

    evernote_query_last_updated_type.setEnabled(True)
    evernote_query_last_updated_value_absolute_date.setEnabled(True)
    evernote_query_last_updated_value_absolute_time.setEnabled(True)
    evernote_query_last_updated_value_relative_spinner.setEnabled(True)

    absolute_date = QDate().fromString(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE,
                                                       "{:%Y %m %d}".format(datetime.now() - timedelta(days=7))),
                                       'yyyy MM dd')
    if index < EvernoteQueryLocationType.AbsoluteDate:
        evernote_query_last_updated_value_absolute_date.setVisible(False)
        evernote_query_last_updated_value_absolute_time.setVisible(False)
        evernote_query_last_updated_value_relative_spinner.setVisible(True)
        spinner_prefix = ['day', 'week', 'month', 'year'][index]
        evernote_query_last_updated_value_relative_spinner.setPrefix(spinner_prefix)
        evernote_query_last_updated_value_relative_spinner.setValue(
            int(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_RELATIVE, 0)))
        evernote_query_last_updated_value_stacked_layout.setCurrentIndex(0)
    else:
        evernote_query_last_updated_value_relative_spinner.setVisible(False)
        evernote_query_last_updated_value_absolute_date.setVisible(True)
        evernote_query_last_updated_value_absolute_date.setDate(absolute_date)
        evernote_query_last_updated_value_stacked_layout.setCurrentIndex(1)
        if index == EvernoteQueryLocationType.AbsoluteDate:
            evernote_query_last_updated_value_absolute_time.setVisible(False)
            evernote_query_last_updated_value_absolute_datetime.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            absolute_time = QTime().fromString(mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME,
                                                               "{:HH mm ss}".format(datetime.now())), 'HH mm ss')
            evernote_query_last_updated_value_absolute_time.setTime(absolute_time)
            evernote_query_last_updated_value_absolute_time.setVisible(True)
            evernote_query_last_updated_value_absolute_datetime.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


def update_evernote_query_last_updated_value_relative_spinner(value):
    if value < 0:
        value = 0
        evernote_query_last_updated_value_relative_spinner.setValue(0)
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_RELATIVE] = value


def update_evernote_query_last_updated_value_absolute_date(date):
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE] = date.toString('yyyy MM dd')


def update_evernote_query_last_updated_value_absolute_datetime(dt):
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_DATE] = dt.toString('yyyy MM dd')
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME] = dt.toString('HH mm ss')


def update_evernote_query_last_updated_value_absolute_time(time_value):
    mw.col.conf[SETTINGS.EVERNOTE_QUERY_LAST_UPDATED_VALUE_ABSOLUTE_TIME] = time_value.toString('HH mm ss')


def generate_evernote_query():
    query = ""
    tags = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_TAGS, SETTINGS.EVERNOTE_QUERY_TAGS_DEFAULT_VALUE).split(",")
    if mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_NOTEBOOK, False):
        query += 'notebook:"%s" ' % mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_NOTEBOOK,
                                                    SETTINGS.EVERNOTE_QUERY_NOTEBOOK_DEFAULT_VALUE).strip()
    if mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_ANY, True):
        query += "any: "
    if mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_NOTE_TITLE, False):
        query_note_title = mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_NOTE_TITLE, "")
        if not query_note_title[:1] + query_note_title[-1:] == '""':
            query_note_title = '"%s"' % query_note_title
        query += 'intitle:%s ' % query_note_title
    if mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_TAGS, True):
        for tag in tags:
            query += "tag:%s " % tag.strip()
    if mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_LAST_UPDATED, False):
        query += " updated:%s " % evernote_query_last_updated_value_get_current_value()
    if mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_USE_SEARCH_TERMS, False):
        query += mw.col.conf.get(SETTINGS.EVERNOTE_QUERY_SEARCH_TERMS, "")
    return query


def handle_show_generated_evernote_query():
    showInfo(
        "The Evernote search query for your current options is below. You can press copy the text to your clipboard by pressing the copy keyboard shortcut (CTRL+C in Windows) while this message box has focus.\n\nQuery: %s" % generate_evernote_query(),
        "Evernote Search Query")
