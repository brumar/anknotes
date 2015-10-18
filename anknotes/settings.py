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
QUERY_TEXTBOXES = ['TAGS', 'EXCLUDED_TAGS', 'SEARCH_TERMS', 'NOTE_TITLE', 'NOTEBOOK']

class EvernoteQueryLocationValueQSpinBox(QSpinBox):
    __prefix = ""

    def setPrefix(self, text):
        self.__prefix = text

    def prefix(self):
        return self.__prefix

    def valueFromText(self, text):
        if text is self.prefix():
            return 0
        return text[len(self.prefix()) + 1:]

    def textFromValue(self, value):
        return self.prefix() + ("-%d" % value if value else "") 

def get_conf(setting, default_value):
    
    return mw.col.conf.get(setting, default_value)
        
def setup_evernote(self):
    global icoEvernoteWeb
    global imgEvernoteWeb
    global elements
    global evernote_query_last_updated
    global evernote_pagination_current_page_spinner

    def update_checkbox(setting):
        if setting is DECKS.EVERNOTE_NOTEBOOK_INTEGRATION and not elements[DECKS.BASE].text():
            return        
        if setting.get.startswith(QUERY.get):
            update_evernote_query_visibilities()
        setting.save(elements[setting].isChecked())
        # mw.col.conf[setting] = 
        if setting is QUERY.USE_TAGS:
            update_evernote_query_visibilities()
        if setting is QUERY.LAST_UPDATED.USE:
            evernote_query_last_updated_value_set_visibilities()

    def create_checkbox(setting, label=" ", default_value=False, is_fixed_size=False, fixed_width=None):
        if isinstance(label, bool):
            default_value = label
            label = " "
        checkbox = QCheckBox(label, self)
        sval = setting.fetch()
        if not isinstance(sval, bool):
            sval = default_value
        checkbox.setChecked(sval)
        # noinspection PyUnresolvedReferences
        checkbox.stateChanged.connect(lambda: update_checkbox(setting))
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
        text = text.strip()
        setting.save(text)
        if setting is DECKS.BASE:
            update_anki_deck_visibilities()
        if setting.get.startswith(QUERY.get):
            if text:
                use_key = getattr(QUERY, 'USE_' + setting.label.name)
                elements[use_key].setChecked(True)
            evernote_query_text_changed()
            if setting is QUERY.SEARCH_TERMS:
                update_evernote_query_visibilities()

    def create_textbox(setting, default_value=""):
        textbox = QLineEdit()
        textbox.setText(setting.fetch(default_value))
        textbox.connect(textbox,
                        SIGNAL("textEdited(QString)"),
                        lambda text: update_text(setting, text))
        elements[setting] = textbox
        return textbox

    def add_query_row(setting, is_checked=False, **kw):
        try:
            default_value = setting.val
        except:
            default_value = ''
        row_label = ' '.join(x.capitalize() for x in setting.replace('_', ' ').split())
        hbox = QHBoxLayout()
        hbox.addWidget(create_checkbox(getattr(QUERY, 'USE_' + setting),
                       default_value=is_checked, **kw))
        hbox.addWidget(create_textbox(getattr(QUERY, setting), default_value))
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
    rm_log_path('Dicts\\')
    evernote_query_last_updated = DictCaseInsensitive()


    ########################## QUERY ##########################
    ##################### QUERY: TEXTBOXES ####################
    group = QGroupBox("EVERNOTE SEARCH OPTIONS:")
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
    form.addRow("<b>Search Parameters:</b>", hbox)

    # Add Form Rows for Evernote Query Textboxes
    for el in QUERY_TEXTBOXES:
        add_query_row(el, 'TAGS' in el)
    
    ################### QUERY: LAST UPDATED ###################
    # Evernote Query: Last Updated Type
    evernote_query_last_updated.type = QComboBox()
    evernote_query_last_updated.type.setStyleSheet(' QComboBox { color: rgb(45, 79, 201); font-weight: bold; } ')
    evernote_query_last_updated.type.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    evernote_query_last_updated.type.addItems([u"Δ Day", u"Δ Week", u"Δ Month", u"Δ Year", "Date", "+ Time"])
    evernote_query_last_updated.type.setCurrentIndex(QUERY.LAST_UPDATED.TYPE.fetch(EvernoteQueryLocationType.RelativeDay))
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
    label.setMinimumWidth(SETTINGS.FORM.LABEL_MINIMUM_WIDTH.val)
    hbox.addWidget(create_checkbox(QUERY.LAST_UPDATED.USE, is_fixed_size=True))
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
    evernote_pagination_current_page_spinner.setValue(EVERNOTE.PAGINATION_CURRENT_PAGE.fetch(1))
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
    label_deck.setMinimumWidth(SETTINGS.FORM.LABEL_MINIMUM_WIDTH.val)
    form.addRow(label_deck, hbox)

    # Add Form Row for Evernote Notebook Integration
    label_deck = QLabel("Evernote Notebook:")
    label_deck.setMinimumWidth(SETTINGS.FORM.LABEL_MINIMUM_WIDTH.val)
    form.addRow("", create_checked_checkbox(DECKS.EVERNOTE_NOTEBOOK_INTEGRATION, "      Append Evernote Notebook"))

    # Add Horizontal Row Separator
    form.addRow(gen_qt_hr())

    ############################ TAGS ##########################
    # Add Form Row for Evernote Tag Options
    label = QLabel("<b>Evernote Tags:</b>")
    label.setMinimumWidth(SETTINGS.FORM.LABEL_MINIMUM_WIDTH.val)

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
    sval = ANKI.UPDATE_EXISTING_NOTES.fetch()
    if not isinstance(sval, int):
        sval = ANKI.UPDATE_EXISTING_NOTES.val
    update_existing_notes.setCurrentIndex(sval)
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

    ######################### UPDATE VISIBILITIES #######################
    # Update Visibilities of Anki Deck Options
    update_anki_deck_visibilities()
    
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
            DECKS.EVERNOTE_NOTEBOOK_INTEGRATION.fetch(True))

def update_evernote_pagination_current_page_spinner(value):
    if value < 1:
        value = 1
        evernote_pagination_current_page_spinner.setValue(1)
    EVERNOTE.PAGINATION_CURRENT_PAGE.save(value)


def update_update_existing_notes(index):
    ANKI.UPDATE_EXISTING_NOTES.save(index)


def evernote_query_text_changed():
    for key in QUERY_TEXTBOXES:        
        setting_use = getattr(QUERY, 'USE_' + key)
        el_use = elements[setting_use]        
        is_enabled = is_checked = bool(elements[getattr(QUERY, key)].text())
        if is_checked:
            is_checked = setting_use.fetch(True)
        el_use.setEnabled(is_enabled)
        el_use.setChecked(is_checked)

def update_evernote_query_visibilities():
    for key in QUERY_TEXTBOXES:
        el_use = elements[getattr(QUERY, 'USE_' + key)]
        elements[getattr(QUERY, key)].setEnabled(el_use.isChecked() or not el_use.isEnabled())
    evernote_query_last_updated_value_set_visibilities()


def update_evernote_query_last_updated_type(index):
    QUERY.LAST_UPDATED.TYPE.save(index)
    evernote_query_last_updated_value_set_visibilities()


def evernote_query_last_updated_get_current_value():
    index = QUERY.LAST_UPDATED.TYPE.fetch(0)
    if index < EvernoteQueryLocationType.AbsoluteDate:
        spinner_text = ['day', 'week', 'month', 'year'][index]
        spinner_val = QUERY.LAST_UPDATED.VALUE.RELATIVE.fetch(0)
        if spinner_val > 0:
            spinner_text += "-" + str(spinner_val)
        return spinner_text

    absolute_date_str = QUERY.LAST_UPDATED.VALUE.ABSOLUTE.DATE.fetch().replace(' ', '')
    if index is EvernoteQueryLocationType.AbsoluteDate:
        return absolute_date_str
    absolute_time_str = QUERY.LAST_UPDATED.VALUE.ABSOLUTE.TIME.fetch("{:HH mm ss}".format(datetime.now())).replace(' ', '')
    return absolute_date_str + "'T'" + absolute_time_str


def evernote_query_last_updated_value_set_visibilities():
    index = QUERY.LAST_UPDATED.TYPE.fetch(0)
    use_last_updated = elements[QUERY.LAST_UPDATED.USE].isChecked()
    with evernote_query_last_updated as lu, lu.value as v, QUERY.LAST_UPDATED.VALUE as LUV:
        lu.type.setEnabled(use_last_updated)
        v.absolute.date.setEnabled(use_last_updated)
        v.absolute.time.setEnabled(use_last_updated)
        v.relative.spinner.setEnabled(use_last_updated)
        if not use_last_updated:
            return
        
        absolute_date = LUV.ABSOLUTE.DATE.fetch()
        absolute_date = QDate().fromString(absolute_date, 'yyyy MM dd')
        if index < EvernoteQueryLocationType.AbsoluteDate:
            v.absolute.date.setVisible(False)
            v.absolute.time.setVisible(False)
            spinner_prefix = ['day', 'week', 'month', 'year'][index]
            v.relative.spinner.setPrefix(spinner_prefix)
            v.relative.spinner.setValue(int(LUV.RELATIVE.fetch(0)))
            v.stacked_layout.setCurrentIndex(0)
        else:
            v.relative.spinner.setVisible(False)
            v.absolute.date.setDate(absolute_date)
            v.stacked_layout.setCurrentIndex(1)
            if index is EvernoteQueryLocationType.AbsoluteDate:
                v.absolute.time.setVisible(False)
                v.absolute.datetime.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            else:
                # absolute_time = "{:HH mm ss}".format(datetime.now())
                # absolute_time = QUERY.LAST_UPDATED_VALUE_ABSOLUTE_TIME.fetch(absolute_time)
                absolute_time = LUV.ABSOLUTE.TIME.fetch("{:HH mm ss}".format(datetime.now()))
                # absolute_time = QTime().fromString(absolute_time, 'HH mm ss')
                v.absolute.time.setTime(QTime().fromString(absolute_time, 'HH mm ss'))
                v.absolute.datetime.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


def update_evernote_query_last_updated_value_relative_spinner(value):
    if value < 0:
        value = 0
        evernote_query_last_updated.value.relative.spinner.setValue(0)
    QUERY.LAST_UPDATED.VALUE.RELATIVE.save(value)


def update_evernote_query_last_updated_value_absolute_date(date):
    QUERY.LAST_UPDATED.VALUE.ABSOLUTE.DATE.save(date.toString('yyyy MM dd'))


def update_evernote_query_last_updated_value_absolute_datetime(dt):
    QUERY.LAST_UPDATED.VALUE.ABSOLUTE.DATE.save(dt.toString('yyyy MM dd'))
    QUERY.LAST_UPDATED.VALUE.ABSOLUTE.TIME.save(dt.toString('HH mm ss'))


def update_evernote_query_last_updated_value_absolute_time(time_value):
    QUERY.LAST_UPDATED.VALUE.ABSOLUTE.TIME.save(time_value.toString('HH mm ss'))


def generate_evernote_query():
    def generate_tag_pred(tags, negate=False):
        pred = ''
        prefix = '-' if negate else ''
        if not isinstance(tags, list):
            tags = tags.replace(',', ' ').split()
        for tag in tags:
            tag = tag.strip()
            if ' ' in tag:
                tag = '"%s"' % tag
            pred += prefix + 'tag:%s ' % tag
        return pred
            
    # Begin generate_evernote_query()
    query = ""
    if QUERY.USE_NOTEBOOK.fetch(False):
        query_notebook = QUERY.NOTEBOOK.fetch(QUERY.NOTEBOOK_DEFAULT_VALUE).strip()
        query += 'notebook:"%s" ' % query_notebook
    if QUERY.ANY.fetch(True):
        query += "any: "
    if QUERY.USE_NOTE_TITLE.fetch(False):
        query_note_title = QUERY.NOTE_TITLE.fetch("")
        if not query_note_title.startswith('"') and query_note_title.endswith('"'):
            query_note_title = '"%s"' % query_note_title
        query += 'intitle:%s ' % query_note_title
    if QUERY.USE_TAGS.fetch(True):
        query += generate_tag_pred(QUERY.TAGS.fetch(QUERY.TAGS_DEFAULT_VALUE))
    if QUERY.USE_EXCLUDED_TAGS.fetch(True):
        query += generate_tag_pred(QUERY.EXCLUDED_TAGS.fetch(''), True)
    if QUERY.LAST_UPDATED.USE.fetch(False):
        query += " updated:%s " % evernote_query_last_updated_get_current_value()
    if QUERY.USE_SEARCH_TERMS.fetch(False):
        query += QUERY.SEARCH_TERMS.fetch("")
    if not query.replace('any:','').strip():
        query = '*'
    return query


def handle_show_generated_evernote_query():
    showInfo(
        "The Evernote search query for your current options is below. You can press copy the text to your clipboard by pressing the copy keyboard shortcut (CTRL+C in Windows) while this message box has focus.\n\nQuery: %s" % generate_evernote_query(),
        "Evernote Search Query")
