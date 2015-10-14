# -*- coding: utf-8 -*-

### Anknotes Shared Imports
from anknotes.shared import *
from anknotes.graphics import *
from anknotes.imports import in_anki
from anknotes.dicts import DictCaseInsensitive

### Anki Imports
if in_anki():
    import anki
    import aqt
    from aqt.preferences import Preferences
    from aqt.utils import getText, openLink, getOnlyText
    from aqt.qt import QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox, SIGNAL, QCheckBox, \
        QComboBox, QSpacerItem, QSizePolicy, QWidget, QSpinBox, QFormLayout, QGridLayout, QFrame, QPalette, \
        QRect, QStackedLayout, QDateEdit, QDateTimeEdit, QTimeEdit, QDate, QDateTime, QTime, QPushButton, QIcon, \
        QMessageBox, QPixmap
    from aqt import mw

ANKI = SETTINGS.ANKI
DECKS = ANKI.DECKS
TAGS = ANKI.TAGS
EVERNOTE = SETTINGS.EVERNOTE
QUERY = EVERNOTE.QUERY

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
    global elements
    global evernote_query_last_updated
    global evernote_pagination_current_page_spinner

    def update_checkbox(setting, checkbox):
        if setting == DECKS.EVERNOTE_NOTEBOOK_INTEGRATION and not elements[DECKS.BASE].text():
            return
        if setting.startswith(QUERY.KEY_BASE):
            update_evernote_query_visibilities()
        mw.col.conf[setting] = checkbox.isChecked()

    def create_checkbox(setting, label=" ", default_value=False, is_fixed_size=False, fixed_width=None):
        if isinstance(label, bool):
            default_value = label
            label = " "
        checkbox = QCheckBox(label, self)
        checkbox.setChecked(mw.col.conf.get(setting, default_value))
        # noinspection PyUnresolvedReferences
        checkbox.stateChanged.connect(lambda: update_checkbox(setting, checkbox))
        if is_fixed_size or fixed_width:
            checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            if fixed_width:
                checkbox.setFixedWidth(fixed_width)
        elements[setting] = checkbox
        return checkbox

    def create_checked_checkbox(*a, **kw):
        kw['default_value'] = True
        return create_checkbox(*a, **kw)

    def update_text(setting, text):
        mw.col.conf[setting] = text
        if setting == DECKS.BASE:
            update_anki_deck_visibilities()
        if setting.startswith(QUERY.KEY_BASE):
            if text:
                use_key = setting.replace(QUERY.KEY_BASE, QUERY.KEY_BASE + 'Use')
                elements[use_key].setChecked(True)
            evernote_query_text_changed()
            if setting == QUERY.SEARCH_TERMS:
                update_evernote_query_visibilities()

    def create_textbox(setting, default_value=""):
        textbox = QLineEdit()
        textbox.setText(mw.col.conf.get(setting, default_value))
        textbox.connect(textbox,
                        SIGNAL("textEdited(QString)"),
                        lambda text: update_text(setting, text))
        elements[setting] = textbox
        return textbox

    def add_query_row(setting, is_checked=False, **kw):
        try:
            default_value = getattr(EVERNOTE.QUERY, setting + '_DEFAULT_VALUE')
        except:
            default_value = ''
        row_label = setting.replace('_', ' ').capitalize()
        hbox = QHBoxLayout()
        hbox.addWidget(create_checkbox(getattr(EVERNOTE.QUERY, 'USE_' + setting),
                       default_value=is_checked, **kw))
        hbox.addWidget(create_textbox(getattr(EVERNOTE.QUERY, setting), default_value))
        form.addRow(row_label, hbox)

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

    # Begin setup_evernote()
    widget = QWidget()
    layout = QVBoxLayout()
    elements = {}
    evernote_query_last_updated = DictCaseInsensitive()


    ########################## QUERY ##########################
    ##################### QUERY: TEXTBOXES ####################
    group = QGroupBox("EVERNOTE SEARCH PARAMETERS:")
    group.setStyleSheet('QGroupBox{    font-size: 10px;    font-weight: bold;  color: rgb(105, 170, 53);}')
    form = QFormLayout()

    form.addRow(gen_qt_hr())

    # Show Generated Evernote Query Button
    button_show_generated_evernote_query = QPushButton(icoEvernoteWeb, "Show Full Query", self)
    button_show_generated_evernote_query.setAutoDefault(False)
    button_show_generated_evernote_query.connect(button_show_generated_evernote_query,
                                                 SIGNAL("clicked()"),
                                                 handle_show_generated_evernote_query)


    # Add Form Row for Match Any Terms
    hbox = QHBoxLayout()
    hbox.addWidget(create_checked_checkbox(QUERY.ANY, "     Match Any Terms", is_fixed_size=True))
    hbox.addWidget(button_show_generated_evernote_query)
    form.addRow("<b>Search Query:</b>", hbox)

    # Add Form Rows for Evernote Query Textboxes
    add_query_row('TAGS', True)
    add_query_row('EXCLUDED_TAGS', True)
    add_query_row('SEARCH_TERMS')
    add_query_row('NOTEBOOK')
    add_query_row('NOTE_TITLE')

    ################### QUERY: LAST UPDATED ###################
    # Evernote Query: Last Updated Type
    evernote_query_last_updated.type = QComboBox()
    evernote_query_last_updated.type.setStyleSheet(' QComboBox { color: rgb(45, 79, 201); font-weight: bold; } ')
    evernote_query_last_updated.type.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    evernote_query_last_updated.type.addItems([u"Δ Day", u"Δ Week", u"Δ Month", u"Δ Year", "Date", "+ Time"])
    evernote_query_last_updated.type.setCurrentIndex(mw.col.conf.get(QUERY.LAST_UPDATED_TYPE,
                                                                     EvernoteQueryLocationType.RelativeDay))
    evernote_query_last_updated.type.activated.connect(update_evernote_query_last_updated_type)


    # Evernote Query: Last Updated Type: Relative Date
    evernote_query_last_updated.value.relative.spinner = EvernoteQueryLocationValueQSpinBox()
    evernote_query_last_updated.value.relative.spinner.setVisible(False)
    evernote_query_last_updated.value.relative.spinner.setStyleSheet(
        " QSpinBox, EvernoteQueryLocationValueQSpinBox { font-weight: bold;  color: rgb(173, 0, 0); } ")
    evernote_query_last_updated.value.relative.spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_query_last_updated.value.relative.spinner.connect(evernote_query_last_updated.value.relative.spinner,
                                                               SIGNAL("valueChanged(int)"),
                                                               update_evernote_query_last_updated_value_relative_spinner)

    # Evernote Query: Last Updated Type: Absolute Date
    evernote_query_last_updated.value.absolute.date = QDateEdit()
    evernote_query_last_updated.value.absolute.date.setDisplayFormat('M/d/yy')
    evernote_query_last_updated.value.absolute.date.setCalendarPopup(True)
    evernote_query_last_updated.value.absolute.date.setVisible(False)
    evernote_query_last_updated.value.absolute.date.setStyleSheet(
        "QDateEdit { font-weight: bold;  color: rgb(173, 0, 0); } ")
    evernote_query_last_updated.value.absolute.date.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_query_last_updated.value.absolute.date.connect(evernote_query_last_updated.value.absolute.date,
                                                            SIGNAL("dateChanged(QDate)"),
                                                            update_evernote_query_last_updated_value_absolute_date)

    # Evernote Query: Last Updated Type: Absolute DateTime
    evernote_query_last_updated.value.absolute.datetime = QDateTimeEdit()
    evernote_query_last_updated.value.absolute.datetime.setDisplayFormat('M/d/yy h:mm AP')
    evernote_query_last_updated.value.absolute.datetime.setCalendarPopup(True)
    evernote_query_last_updated.value.absolute.datetime.setVisible(False)
    evernote_query_last_updated.value.absolute.datetime.setStyleSheet(
        "QDateTimeEdit { font-weight: bold;  color: rgb(173, 0, 0); } ")
    evernote_query_last_updated.value.absolute.datetime.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_query_last_updated.value.absolute.datetime.connect(evernote_query_last_updated.value.absolute.datetime,
                                                                SIGNAL("dateTimeChanged(QDateTime)"),
                                                                update_evernote_query_last_updated_value_absolute_datetime)



    # Evernote Query: Last Updated Type: Absolute Time
    evernote_query_last_updated.value.absolute.time = QTimeEdit()
    evernote_query_last_updated.value.absolute.time.setDisplayFormat('h:mm AP')
    evernote_query_last_updated.value.absolute.time.setVisible(False)
    evernote_query_last_updated.value.absolute.time.setStyleSheet(
        "QTimeEdit { font-weight: bold;  color: rgb(143, 0, 30); } ")
    evernote_query_last_updated.value.absolute.time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_query_last_updated.value.absolute.time.connect(evernote_query_last_updated.value.absolute.time,
                                                            SIGNAL("timeChanged(QTime)"),
                                                            update_evernote_query_last_updated_value_absolute_time)

    # Create HBox for Separated Date & Time
    hbox_datetime = QHBoxLayout()
    hbox_datetime.addWidget(evernote_query_last_updated.value.absolute.date)
    hbox_datetime.addWidget(evernote_query_last_updated.value.absolute.time)

    # Evernote Query: Last Updated Type
    evernote_query_last_updated.value.stacked_layout = QStackedLayout()
    evernote_query_last_updated.value.stacked_layout.addWidget(evernote_query_last_updated.value.relative.spinner)
    evernote_query_last_updated.value.stacked_layout.addItem(hbox_datetime)

    # Add Form Row for Evernote Query: Last Updated
    hbox = QHBoxLayout()
    label = QLabel("Last Updated: ")
    label.setMinimumWidth(100)
    hbox.addWidget(create_checkbox(QUERY.USE_LAST_UPDATED, is_fixed_size=True))
    hbox.addWidget(evernote_query_last_updated.type)
    hbox.addWidget(evernote_query_last_updated.value.relative.spinner)
    hbox.addWidget(evernote_query_last_updated.value.absolute.date)
    hbox.addWidget(evernote_query_last_updated.value.absolute.time)
    form.addRow(label, hbox)

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    ############################ PAGINATION ##########################
    # Evernote Pagination: Current Page
    evernote_pagination_current_page_spinner = QSpinBox()
    evernote_pagination_current_page_spinner.setStyleSheet("QSpinBox { font-weight: bold;  color: rgb(173, 0, 0);  } ")
    evernote_pagination_current_page_spinner.setPrefix("PAGE: ")
    evernote_pagination_current_page_spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    evernote_pagination_current_page_spinner.setValue(mw.col.conf.get(EVERNOTE.PAGINATION_CURRENT_PAGE, 1))
    evernote_pagination_current_page_spinner.connect(evernote_pagination_current_page_spinner,
                                                     SIGNAL("valueChanged(int)"),
                                                     update_evernote_pagination_current_page_spinner)

    # Evernote Pagination: Automation
    hbox = QHBoxLayout()
    hbox.addWidget(create_checked_checkbox(EVERNOTE.AUTO_PAGING, "     Automate", fixed_width=105))
    hbox.addWidget(evernote_pagination_current_page_spinner)

    # Add Form Row for Evernote Pagination
    form.addRow("<b>Pagination:</b>", hbox)

    # Add Query Form to Group Box
    group.setLayout(form)

    # Add Query Group Box to Main Layout
    layout.addWidget(group)

    ########################## DECK ##########################
    # Setup Group Box and Form
    group = QGroupBox("ANKI NOTE OPTIONS:")
    group.setStyleSheet('QGroupBox{    font-size: 10px;    font-weight: bold;  color: rgb(105, 170, 53);}')
    form = QFormLayout()

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    # Add Form Row for Default Anki Deck
    hbox = QHBoxLayout()
    hbox.insertSpacing(0, 33)
    hbox.addWidget(create_textbox(DECKS.BASE, DECKS.BASE_DEFAULT_VALUE))
    label_deck = QLabel("<b>Anki Deck:</b>")
    label_deck.setMinimumWidth(100)
    form.addRow(label_deck, hbox)

    # Change Visibility of Deck Options
    update_anki_deck_visibilities()

    # Add Form Row for Evernote Notebook Integration
    label_deck = QLabel("Evernote Notebook:")
    label_deck.setMinimumWidth(100)
    form.addRow("", create_checked_checkbox(DECKS.EVERNOTE_NOTEBOOK_INTEGRATION, "      Append Evernote Notebook"))

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    ############################ TAGS ##########################
    # Add Form Row for Evernote Tag Options
    label = QLabel("<b>Evernote Tags:</b>")
    label.setMinimumWidth(100)

    # Tags: Save To Anki Note
    form.addRow(label, create_checkbox(TAGS.KEEP_TAGS, "     Save To Anki Note", TAGS.KEEP_TAGS_DEFAULT_VALUE))
    hbox = QHBoxLayout()
    hbox.insertSpacing(0, 33)
    hbox.addWidget(create_textbox(TAGS.TO_DELETE))

    # Tags: Tags To Delete
    form.addRow("Tags to Delete:", hbox)
    form.addRow(" ", create_checkbox(TAGS.DELETE_EVERNOTE_QUERY_TAGS, "     Also Delete Search Tags"))

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    ############################ NOTE UPDATING ##########################
    # Note Update Method
    update_existing_notes = QComboBox()
    update_existing_notes.setStyleSheet(
        ' QComboBox { color: #3b679e; font-weight: bold; } QComboBoxItem { color: #A40F2D; font-weight: bold; } ')
    update_existing_notes.addItems(["Ignore Existing Notes", "Update In-Place",
                                    "Delete and Re-Add"])
    update_existing_notes.setCurrentIndex(mw.col.conf.get(ANKI.UPDATE_EXISTING_NOTES,
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

    ###################### UPDATE QUERY VISIBILITIES ####################
    # Update Visibilities of Query Options
    evernote_query_text_changed()
    update_evernote_query_visibilities()

    ######################## ADD TO SETTINGS PANEL ######################
    # Vertical Spacer
    vertical_spacer = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
    layout.addItem(vertical_spacer)

    # Parent Widget
    widget.setLayout(layout)

    # New Tab
    self.form.tabWidget.addTab(widget, "Anknotes")

def update_anki_deck_visibilities():
    if not elements[DECKS.BASE].text():
        elements[DECKS.EVERNOTE_NOTEBOOK_INTEGRATION].setChecked(True)
        elements[DECKS.EVERNOTE_NOTEBOOK_INTEGRATION].setEnabled(False)
    else:
        elements[DECKS.EVERNOTE_NOTEBOOK_INTEGRATION].setEnabled(True)
        elements[DECKS.EVERNOTE_NOTEBOOK_INTEGRATION].setChecked(
            mw.col.conf.get(DECKS.EVERNOTE_NOTEBOOK_INTEGRATION, True))

def update_evernote_pagination_current_page_spinner(value):
    if value < 1:
        value = 1
        evernote_pagination_current_page_spinner.setValue(1)
    mw.col.conf[EVERNOTE.PAGINATION_CURRENT_PAGE] = value


def update_update_existing_notes(index):
    mw.col.conf[ANKI.UPDATE_EXISTING_NOTES] = index


def evernote_query_text_changed():
    tags = elements[QUERY.TAGS].text()
    excluded_tags = elements[QUERY.EXCLUDED_TAGS].text()
    search_terms = elements[QUERY.SEARCH_TERMS].text()
    note_title = elements[QUERY.NOTE_TITLE].text()
    notebook = elements[QUERY.NOTEBOOK].text()
    # tags_active = tags and elements[QUERY.USE_TAGS].isChecked()
    search_terms_active = search_terms and elements[QUERY.USE_SEARCH_TERMS].isChecked()
    note_title_active = note_title and elements[QUERY.USE_NOTE_TITLE].isChecked()
    notebook_active = notebook and elements[QUERY.USE_NOTEBOOK].isChecked()
    excluded_tags_active = excluded_tags and elements[QUERY.USE_EXCLUDED_TAGS].isChecked()
    all_inactive = not (
        search_terms_active or note_title_active or notebook_active or excluded_tags_active or elements[QUERY.USE_LAST_UPDATED].isChecked())

    if not search_terms:
        elements[QUERY.USE_SEARCH_TERMS].setEnabled(False)
        elements[QUERY.USE_SEARCH_TERMS].setChecked(False)
    else:
        elements[QUERY.USE_SEARCH_TERMS].setEnabled(True)
        elements[QUERY.USE_SEARCH_TERMS].setChecked(mw.col.conf.get(QUERY.USE_SEARCH_TERMS, True))

    if not note_title:
        elements[QUERY.USE_NOTE_TITLE].setEnabled(False)
        elements[QUERY.USE_NOTE_TITLE].setChecked(False)
    else:
        elements[QUERY.USE_NOTE_TITLE].setEnabled(True)
        elements[QUERY.USE_NOTE_TITLE].setChecked(mw.col.conf.get(QUERY.USE_NOTE_TITLE, True))

    if not notebook:
        elements[QUERY.USE_NOTEBOOK].setEnabled(False)
        elements[QUERY.USE_NOTEBOOK].setChecked(False)
    else:
        elements[QUERY.USE_NOTEBOOK].setEnabled(True)
        elements[QUERY.USE_NOTEBOOK].setChecked(mw.col.conf.get(QUERY.USE_NOTEBOOK, True))

    if not excluded_tags:
        elements[QUERY.USE_EXCLUDED_TAGS].setEnabled(False)
        elements[QUERY.USE_EXCLUDED_TAGS].setChecked(False)
    else:
        elements[QUERY.USE_EXCLUDED_TAGS].setEnabled(True)
        elements[QUERY.USE_EXCLUDED_TAGS].setChecked(mw.col.conf.get(QUERY.USE_EXCLUDED_TAGS, True))
    if not tags and not all_inactive:
        elements[QUERY.USE_TAGS].setEnabled(False)
        elements[QUERY.USE_TAGS].setChecked(False)
    else:
        elements[QUERY.USE_TAGS].setEnabled(True)
        elements[QUERY.USE_TAGS].setChecked(mw.col.conf.get(QUERY.USE_TAGS, True))
        if all_inactive and not tags:
            elements[QUERY.TAGS].setText(QUERY.TAGS_DEFAULT_VALUE)


def update_evernote_query_visibilities():
    # is_any =  elements[QUERY.ANY].isChecked()
    is_tags = elements[QUERY.USE_TAGS].isChecked()
    is_excluded_tags = elements[QUERY.USE_EXCLUDED_TAGS].isChecked()
    is_terms = elements[QUERY.USE_SEARCH_TERMS].isChecked()
    is_title = elements[QUERY.USE_NOTE_TITLE].isChecked()
    is_notebook = elements[QUERY.USE_NOTEBOOK].isChecked()
    is_updated = elements[QUERY.USE_LAST_UPDATED].isChecked()

    # is_disabled_any = not elements[QUERY.ANY].isEnabled()
    is_disabled_tags = not elements[QUERY.USE_TAGS].isEnabled()
    is_disabled_excluded_tags = not elements[QUERY.USE_EXCLUDED_TAGS].isEnabled()
    is_disabled_terms = not elements[QUERY.USE_SEARCH_TERMS].isEnabled()
    is_disabled_title = not elements[QUERY.USE_NOTE_TITLE].isEnabled()
    is_disabled_notebook = not elements[QUERY.USE_NOTEBOOK].isEnabled()
    # is_disabled_updated = not elements[QUERY.USE_LAST_UPDATED].isEnabled()

    override = (
        not is_tags and not is_excluded_tags and not is_terms and not is_title and not is_notebook and not is_updated)
    if override:
        is_tags = True
        elements[QUERY.USE_TAGS].setChecked(True)
    elements[QUERY.TAGS].setEnabled(is_tags or is_disabled_tags)
    elements[QUERY.EXCLUDED_TAGS].setEnabled(is_excluded_tags or is_disabled_excluded_tags)
    elements[QUERY.SEARCH_TERMS].setEnabled(is_terms or is_disabled_terms)
    elements[QUERY.NOTE_TITLE].setEnabled(is_title or is_disabled_title)
    elements[QUERY.NOTEBOOK].setEnabled(is_notebook or is_disabled_notebook)
    evernote_query_last_updated_value_set_visibilities()


def update_evernote_query_last_updated_type(index):
    mw.col.conf[QUERY.LAST_UPDATED_TYPE] = index
    evernote_query_last_updated_value_set_visibilities()


def evernote_query_last_updated_get_current_value():
    index = mw.col.conf.get(QUERY.LAST_UPDATED_TYPE, 0)
    if index < EvernoteQueryLocationType.AbsoluteDate:
        spinner_text = ['day', 'week', 'month', 'year'][index]
        spinner_val = mw.col.conf.get(QUERY.LAST_UPDATED_VALUE_RELATIVE, 0)
        if spinner_val > 0:
            spinner_text += "-" + str(spinner_val)
        return spinner_text

    absolute_date_str = mw.col.conf.get(QUERY.LAST_UPDATED_VALUE_ABSOLUTE_DATE,
                                        "{:%Y %m %d}".format(datetime.now() - timedelta(days=7))).replace(' ', '')
    if index == EvernoteQueryLocationType.AbsoluteDate:
        return absolute_date_str
    absolute_time_str = mw.col.conf.get(QUERY.LAST_UPDATED_VALUE_ABSOLUTE_TIME,
                                        "{:HH mm ss}".format(datetime.now())).replace(' ', '')
    return absolute_date_str + "'T'" + absolute_time_str


def evernote_query_last_updated_value_set_visibilities():
    index = mw.col.conf.get(QUERY.LAST_UPDATED_TYPE, 0)
    if not elements[QUERY.USE_LAST_UPDATED].isChecked():
        evernote_query_last_updated.type.setEnabled(False)
        evernote_query_last_updated.value.absolute.date.setEnabled(False)
        evernote_query_last_updated.value.absolute.time.setEnabled(False)
        evernote_query_last_updated.value.relative.spinner.setEnabled(False)
        return

    evernote_query_last_updated.type.setEnabled(True)
    evernote_query_last_updated.value.absolute.date.setEnabled(True)
    evernote_query_last_updated.value.absolute.time.setEnabled(True)
    evernote_query_last_updated.value.relative.spinner.setEnabled(True)

    absolute_date = QDate().fromString(mw.col.conf.get(QUERY.LAST_UPDATED_VALUE_ABSOLUTE_DATE,
                                                       "{:%Y %m %d}".format(datetime.now() - timedelta(days=7))),
                                       'yyyy MM dd')
    if index < EvernoteQueryLocationType.AbsoluteDate:
        evernote_query_last_updated.value.absolute.date.setVisible(False)
        evernote_query_last_updated.value.absolute.time.setVisible(False)
        evernote_query_last_updated.value.relative.spinner.setVisible(True)
        spinner_prefix = ['day', 'week', 'month', 'year'][index]
        evernote_query_last_updated.value.relative.spinner.setPrefix(spinner_prefix)
        evernote_query_last_updated.value.relative.spinner.setValue(
            int(mw.col.conf.get(QUERY.LAST_UPDATED_VALUE_RELATIVE, 0)))
        evernote_query_last_updated.value.stacked_layout.setCurrentIndex(0)
    else:
        evernote_query_last_updated.value.relative.spinner.setVisible(False)
        evernote_query_last_updated.value.absolute.date.setVisible(True)
        evernote_query_last_updated.value.absolute.date.setDate(absolute_date)
        evernote_query_last_updated.value.stacked_layout.setCurrentIndex(1)
        if index == EvernoteQueryLocationType.AbsoluteDate:
            evernote_query_last_updated.value.absolute.time.setVisible(False)
            evernote_query_last_updated.value.absolute.datetime.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            absolute_time = QTime().fromString(mw.col.conf.get(QUERY.LAST_UPDATED_VALUE_ABSOLUTE_TIME,
                                                               "{:HH mm ss}".format(datetime.now())), 'HH mm ss')
            evernote_query_last_updated.value.absolute.time.setTime(absolute_time)
            evernote_query_last_updated.value.absolute.time.setVisible(True)
            evernote_query_last_updated.value.absolute.datetime.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


def update_evernote_query_last_updated_value_relative_spinner(value):
    if value < 0:
        value = 0
        evernote_query_last_updated.value.relative.spinner.setValue(0)
    mw.col.conf[QUERY.LAST_UPDATED_VALUE_RELATIVE] = value


def update_evernote_query_last_updated_value_absolute_date(date):
    mw.col.conf[QUERY.LAST_UPDATED_VALUE_ABSOLUTE_DATE] = date.toString('yyyy MM dd')


def update_evernote_query_last_updated_value_absolute_datetime(dt):
    mw.col.conf[QUERY.LAST_UPDATED_VALUE_ABSOLUTE_DATE] = dt.toString('yyyy MM dd')
    mw.col.conf[QUERY.LAST_UPDATED_VALUE_ABSOLUTE_TIME] = dt.toString('HH mm ss')


def update_evernote_query_last_updated_value_absolute_time(time_value):
    mw.col.conf[QUERY.LAST_UPDATED_VALUE_ABSOLUTE_TIME] = time_value.toString('HH mm ss')


def generate_evernote_query():
    query = ""
    if mw.col.conf.get(QUERY.USE_NOTEBOOK, False):
        query += 'notebook:"%s" ' % mw.col.conf.get(QUERY.NOTEBOOK,
                                                    QUERY.NOTEBOOK_DEFAULT_VALUE).strip()
    if mw.col.conf.get(QUERY.ANY, True):
        query += "any: "
    if mw.col.conf.get(QUERY.USE_NOTE_TITLE, False):
        query_note_title = mw.col.conf.get(QUERY.NOTE_TITLE, "")
        if not query_note_title[:
            1] + query_note_title[-1:] == '""':
            query_note_title = '"%s"' % query_note_title
        query += 'intitle:%s ' % query_note_title
    if mw.col.conf.get(QUERY.USE_TAGS, True):
        tags = mw.col.conf.get(QUERY.TAGS, QUERY.TAGS_DEFAULT_VALUE).replace(',',
                                                                                                                 ' ').split()
        for tag in tags:
            tag = tag.strip()
            if ' ' in tag:
                tag = '"%s"' % tag
            query += 'tag:%s ' % tag
    if mw.col.conf.get(QUERY.USE_EXCLUDED_TAGS, True):
        tags = mw.col.conf.get(QUERY.EXCLUDED_TAGS, '').replace(',', ' ').split()
        for tag in tags:
            tag = tag.strip()
            if ' ' in tag:
                tag = '"%s"' % tag
            query += '-tag:%s ' % tag
    if mw.col.conf.get(QUERY.USE_LAST_UPDATED, False):
        query += " updated:%s " % evernote_query_last_updated_get_current_value()
    if mw.col.conf.get(QUERY.USE_SEARCH_TERMS, False):
        query += mw.col.conf.get(QUERY.SEARCH_TERMS, "")
    return query


def handle_show_generated_evernote_query():
    showInfo(
        "The Evernote search query for your current options is below. You can press copy the text to your clipboard by pressing the copy keyboard shortcut (CTRL+C in Windows) while this message box has focus.\n\nQuery: %s" % generate_evernote_query(),
        "Evernote Search Query")
