# Python Imports
from datetime import datetime, timedelta
import difflib
import pprint
import re
import inspect
import shutil
import time
# Anknotes Shared Imports
from anknotes.constants import *
from anknotes.graphics import *
from anknotes.counters import DictCaseInsensitive
# from anknotes.stopwatch import clockit

# Anki Imports
try:
	from aqt import mw
	from aqt.utils import tooltip
	from aqt.qt import QMessageBox, QPushButton, QSizePolicy, QSpacerItem, QGridLayout, QLayout
except:
	pass


def str_safe(strr, prefix=''):
	try:
		strr = str((prefix + strr.__repr__()))
	except:
		strr = str((prefix + strr.__repr__().encode('utf8', 'replace')))
	return strr


def print_safe(strr, prefix=''):
	print str_safe(strr, prefix)


def show_tooltip(text, time_out=7000, delay=None, do_log=False):
	if do_log: log(text)
	if delay:
		try: return mw.progress.timer(delay, lambda: tooltip(text, time_out), False)
		except: pass
	tooltip(text, time_out)
def counts_as_str(count, max=None):
	from anknotes.counters import Counter
	if isinstance(count, Counter): count = count.val
	if isinstance(max, Counter): max = max.val
	if max is None or max <= 0: return str(count).center(3)
	if count == max: return "All  %s" % str(count).center(3)
	return "Total %s of %s" % (str(count).center(3), str(max).center(3))

def show_report(title, header=None, log_lines=None, delay=None, log_header_prefix = ' '*5, filename=None, blank_line_before=True, blank_line_after=True, hr_if_empty=False):
	if log_lines is None: log_lines = []
	if header is None: header = []
	lines = []
	for line in ('<BR>'.join(header) if isinstance(header, list) else header).split('<BR>') + ('<BR>'.join(log_lines).split('<BR>') if log_lines else []):
		level = 0
		while line and line[level] is '-': level += 1
		lines.append('\t'*level + ('\t\t- ' if lines else '') + line[level:])
	if len(lines) > 1: lines[0] += ': '
	log_text = '<BR>'.join(lines)
	if not header and not log_lines:
		i=title.find('> ')
		show_tooltip(title[0 if i < 0 else i + 2:], delay=delay)
	else: show_tooltip(log_text.replace('\t', '&nbsp; '*4), delay=delay)
	if blank_line_before: log_blank(filename=filename)
	log(title, filename=filename)
	if len(lines) == 1 and not lines[0]:
		if hr_if_empty: log(" " + "-" * ANKNOTES.FORMATTING.LINE_LENGTH, timestamp=False, filename=filename)
		return
	log(" " + "-" * ANKNOTES.FORMATTING.LINE_LENGTH + '\n' + log_header_prefix + log_text.replace('<BR>', '\n'), timestamp=False, replace_newline=True, filename=filename)
	if blank_line_after: log_blank(filename=filename)


def showInfo(message, title="Anknotes: Evernote Importer for Anki", textFormat=0, cancelButton=False, richText=False, minHeight=None, minWidth=400, styleSheet=None, convertNewLines=True):
	global imgEvernoteWebMsgBox, icoEvernoteArtcore, icoEvernoteWeb
	msgDefaultButton = QPushButton(icoEvernoteArtcore, "Okay!", mw)

	if not styleSheet:
		styleSheet = file(FILES.ANCILLARY.CSS_QMESSAGEBOX, 'r').read()

	if not isinstance(message, str) and not isinstance(message, unicode):
		message = str(message)

	if richText:
		textFormat = 1
		# message = message.replace('\n', '<BR>\n')
		message = '<style>\n%s</style>\n\n%s' % (styleSheet, message)
	global messageBox
	messageBox = QMessageBox()
	messageBox.addButton(msgDefaultButton, QMessageBox.AcceptRole)
	if cancelButton:
		msgCancelButton = QPushButton(icoTomato, "No Thanks", mw)
		messageBox.addButton(msgCancelButton, QMessageBox.RejectRole)
	messageBox.setDefaultButton(msgDefaultButton)
	messageBox.setIconPixmap(imgEvernoteWebMsgBox)
	messageBox.setTextFormat(textFormat)

	# message = ' %s %s' % (styleSheet, message)
	log_plain(message, 'showInfo',  clear=True)
	messageBox.setWindowIcon(icoEvernoteWeb)
	messageBox.setWindowIconText("Anknotes")
	messageBox.setText(message)
	messageBox.setWindowTitle(title)
	# if minHeight:
	#     messageBox.setMinimumHeight(minHeight)
	# messageBox.setMinimumWidth(minWidth)
	#
	# messageBox.setFixedWidth(1000)
	hSpacer = QSpacerItem(minWidth, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)

	layout = messageBox.layout()
	""":type : QGridLayout """
	# layout.addItem(hSpacer, layout.rowCount() + 1, 0, 1, layout.columnCount())
	layout.addItem(hSpacer, layout.rowCount() + 1, 0, 1, layout.columnCount())
	# messageBox.setStyleSheet(styleSheet)


	ret = messageBox.exec_()
	if not cancelButton:
		return True
	if messageBox.clickedButton() == msgCancelButton or messageBox.clickedButton() == 0:
		return False
	return True

def diffify(content, split=True):
	for tag in [u'div', u'ol', u'ul', u'li', u'span']:
		content = content.replace(u"<" + tag, u"\n<" + tag).replace(u"</%s>" % tag, u"</%s>\n" % tag)
	content = re.sub(r'[\r\n]+', u'\n', content)
	return content.splitlines() if split else content
def generate_diff(value_original, value):
	try: return '\n'.join(list(difflib.unified_diff(diffify(value_original), diffify(value), lineterm='')))
	except: pass
	try: return '\n'.join(
			list(difflib.unified_diff(diffify(value_original.decode('utf-8')), diffify(value), lineterm='')))
	except: pass
	try: return '\n'.join(
			list(difflib.unified_diff(diffify(value_original), diffify(value.decode('utf-8')), lineterm='')))
	except: pass
	try: return '\n'.join(list(
			difflib.unified_diff(diffify(value_original.decode('utf-8')), diffify(value.decode('utf-8')), lineterm='')))
	except: raise


def PadList(lst, length=ANKNOTES.FORMATTING.LIST_PAD):
	newLst = []
	for val in lst:
		if isinstance(val, list): newLst.append(PadList(val, length))
		else: newLst.append(val.center(length))
	return newLst
def JoinList(lst, joiners='\n', pad=0, depth=1):
	if isinstance(joiners, str) or isinstance(joiners, unicode): joiners = [joiners]
	strr = ''
	if pad and (isinstance(lst, str) or isinstance(lst, unicode)): return lst.center(pad)
	if not lst or not isinstance(lst, list): return lst
	delimit=joiners[min(len(joiners), depth)-1]
	for val in lst:
		if strr: strr += delimit
		strr += JoinList(val, joiners, pad, depth+1)
	return strr

def PadLines(content, line_padding=ANKNOTES.FORMATTING.LINE_PADDING_HEADER, line_padding_plus=0, line_padding_header='', pad_char=' ', **kwargs):
	if not line_padding and not line_padding_plus and not line_padding_header: return content
	if not line_padding: line_padding = line_padding_plus; line_padding_plus=True
	if str(line_padding).isdigit(): line_padding = pad_char * int(line_padding)
	if line_padding_header: content = line_padding_header + content; line_padding_plus = len(line_padding_header) + 1
	elif line_padding_plus is True: line_padding_plus = content.find('\n')
	if str(line_padding_plus).isdigit(): line_padding_plus = pad_char * int(line_padding_plus)
	return line_padding + content.replace('\n', '\n' + line_padding + line_padding_plus)

def item_to_list(item, list_from_unknown=True,chrs=''):
	if isinstance(item, list): return item
	if item and (isinstance(item, unicode) or isinstance(item, str)):
		for c in chrs: item=item.replace(c, '|')
		return item.split('|')
	if list_from_unknown: return [item]
	return item
def key_transform(keys, key):
	if keys is None: keys = self.keys()
	key = key.strip()
	for k in keys:
		if k.lower() == key.lower(): return k
	return key
	
def get_kwarg(func_kwargs, key, **kwargs):
	kwargs['update_kwargs'] = False
	return process_kwarg(func_kwargs, key, **kwargs)

def process_kwarg(kwargs, key, default=None, replace_none_type=True, update_kwargs=True, return_value=True):
	key = key_transform(kwargs.keys(), key)
	if key not in kwargs: return (kwargs, default) if update_kwargs else default
	val = kwargs[key]
	if val is None and replace_none_type: val = default
	if not update_kwargs: return val
	del kwargs[key]
	return kwargs, val
def process_kwargs(kwargs, get_args=None, set_dict=None, name=None, update_kwargs=True):
	keys = kwargs.keys()
	for key, value in set_dict.items() if set_dict else []:
		key = key_transform(keys, key)
		if not key in kwargs: kwargs[key]=value
	kwargs = DictCaseInsensitive(kwargs, label=name)
	if not get_args: return kwargs
	keys = kwargs.keys()
	gets = []
	for args in get_args:
		for arg in args:
			if len(arg) is 1 and isinstance(arg[0], list): arg = arg[0]
			result = process_kwarg(kwargs, arg[0], arg[1], update_kwargs=update_kwargs)
			if update_kwargs: kwargs = result[0]; result = result[1]
			gets += [result]
	if update_kwargs: return [kwargs] + gets
	return gets

def __get_args__(args, func_kwargs, *args_list, **kwargs_):
	kwargs = DictCaseInsensitive({'suffix_type_to_name':True, 'max_args':-1, 'default_value':None, 'return_expanded':True, 'return_values_only':False})
	kwargs.update(kwargs_)
	max_args = kwargs.max_args
	args = list(args)
	# names = item_to_list(names, False)
	# if isinstance(names, list): names = [[name, None] for name in names]
	# else: names = names.items()
	results = DictCaseInsensitive()
	max_args = len(args) if max_args < 1 else min(len(args), max_args)
	values=[]
	args_to_del=[]
	get_names = [[names[i*2:i*2+2] for i in range(0, len(names)/2)] if isinstance(names, list) else [[name, None] for name in item_to_list(names)] for names in args_list]

	for get_name in get_names:
		for get_name_item in get_name:
			if len(get_name_item) is 1 and isinstance(get_name_item[0], list): get_name_item = get_name_item[0]
			name = get_name_item[0]
			types=get_name_item[1]
			# print "Name: %s, Types: %s" % (name, str(types[0]))
			name = name.replace('*', '')
			types = item_to_list(types)
			is_none_type = types[0] is None
			key = name + ( '_' + types[0].__name__) if kwargs.suffix_type_to_name and not is_none_type else ''
			key = key_transform(func_kwargs.keys(), key)
			result = DictCaseInsensitive(Match=False, MatchedKWArg=False, MatchedArg=False, Name=key, value=kwargs.default_value)
			if key in func_kwargs:
				result.value = func_kwargs[key]
				del func_kwargs[key]
				result.Match = True
				result.MatchedKWArg =  True
				continue
			if is_none_type: continue
			for i in range(0, max_args):
				if i in args_to_del: continue
				arg = args[i]
				for t in types:
					if not isinstance(arg, t): continue
					result.value = arg
					result.Match = True
					result.MatchedArg = True
					args_to_del.append(i)
					break
				if result.Match: break
			values.append(result.value)
			results[name] = result
	args = [x for i, x in enumerate(args) if i not in args_to_del]
	results.func_kwargs = func_kwargs
	results.args = args
	if kwargs.return_values_only: return values
	if kwargs.return_expanded: return [args, func_kwargs] + values
	return results
def __get_default_listdict_args__(args, kwargs, name):
	results_expanded = __get_args__(args, kwargs, [name + '*', [list, str, unicode], name , [dict, DictCaseInsensitive]])
	results_expanded[2] = item_to_list(results_expanded[2], chrs=',')
	if results_expanded[2] is None: results_expanded[2] = []
	if results_expanded[3] is None: results_expanded[3] = {}
	return results_expanded

def get_kwarg_values(func_kwargs, *args, **kwargs):
	kwargs['update_kwargs'] = False
	return get_kwargs(func_kwargs, *args, **kwargs)

def get_kwargs(func_kwargs, *args_list, **kwargs):
	lst = [[args[i*2:i*2+2] for i in range(0, len(args)/2)] if isinstance(args, list) else [[arg, None] for arg in item_to_list(args)] for args in args_list]
	return process_kwargs(func_kwargs, get_args=lst, **kwargs)

def set_kwargs(func_kwargs, *args, **kwargs):
	kwargs, name, update_kwargs = get_kwargs(kwargs, ['name', None, 'update_kwargs', None])
	args, kwargs, list, dict = __get_default_listdict_args__(args, kwargs, 'set')
	new_args=[];
	for arg in args: new_args += item_to_list(arg, False)
	dict.update({key: None for key in list + new_args  })
	dict.update(kwargs)
	return DictCaseInsensitive(process_kwargs(func_kwargs, set_dict=dict, name=name, update_kwargs=update_kwargs))

def obj2log_simple(content):
	if not isinstance(content, str) and not isinstance(content, unicode):
		content = str(content)
	return content

def convert_filename_to_local_link(filename):
	return 'file:///' + filename.replace("\\", "//")

class Logger(object):
	base_path = None
	caller_info=None
	default_filename=None
	def wrap_filename(self, filename=None):
		if filename is None: filename = self.default_filename
		if self.base_path is not None:
			filename = os.path.join(self.base_path, filename if filename else '')
		return filename

	def dump(self, obj, title='', filename=None, *args, **kwargs):
		filename = self.wrap_filename(filename)
		log_dump(obj=obj, title=title, filename=filename, *args, **kwargs)

	def blank(self, filename=None, *args, **kwargs):
		filename = self.wrap_filename(filename)
		log_blank(filename=filename, *args, **kwargs)

	def banner(self, title, filename=None, *args, **kwargs):
		filename = self.wrap_filename(filename)
		log_banner(title=title, filename=filename, *args, **kwargs)

	def go(self, content=None, filename=None, wrap_filename=True, *args, **kwargs):
		if wrap_filename: filename = self.wrap_filename(filename)
		log(content=content, filename=filename, *args, **kwargs)

	def plain(self, content=None, filename=None, *args, **kwargs):
		filename=self.wrap_filename(filename)
		log_plain(content=content, filename=filename, *args, **kwargs)

	log = do = add = go

	def default(self, *args, **kwargs):
		self.log(wrap_filename=False, *args, **kwargs)

	def __init__(self, base_path=None, default_filename=None, rm_path=False):
		self.default_filename = default_filename
		if base_path:
			self.base_path = base_path
		else:
			self.caller_info = caller_name()
			if self.caller_info:
				self.base_path = create_log_filename(self.caller_info.Base)
		if rm_path:
			rm_log_path(self.base_path)



def log_blank(filename=None, *args, **kwargs):
	log(timestamp=False, content=None, filename=filename, *args, **kwargs)


def log_plain(*args, **kwargs):
	log(timestamp=False, *args, **kwargs)

def rm_log_path(filename='*', subfolders_only=False, retry_errors=0):
	path = os.path.dirname(os.path.abspath(get_log_full_path(filename)))
	if path is FOLDERS.LOGS or path in FOLDERS.LOGS: return
	rm_log_path.errors = []
	def del_subfolder(arg=None,dirname=None,filenames=None, is_subfolder=True):
		def rmtree_error(f, p, e):
			rm_log_path.errors += [p]
		if is_subfolder and dirname is path: return
		shutil.rmtree(dirname, onerror=rmtree_error)
	if not subfolders_only: del_subfolder(dirname=path, is_subfolder=False)
	else: os.path.walk(path, del_subfolder, None)
	if rm_log_path.errors:
		if retry_errors > 5:
			print "Unable to delete log path"
			log("Unable to delete log path as requested", filename)
			return
		time.sleep(1)
		rm_log_path(filename, subfolders_only, retry_errors + 1)

def log_banner(title, filename=None, length=ANKNOTES.FORMATTING.BANNER_MINIMUM, append_newline=True, timestamp=False, chr='-', center=True, clear=True, *args, **kwargs):
	if length is 0: length = ANKNOTES.FORMATTING.LINE_LENGTH+1
	if center: title = title.center(length-TIMESTAMP_PAD_LENGTH if timestamp else 0)
	log(chr * length, filename, clear=clear, timestamp=False, *args, **kwargs)
	log(title, filename, timestamp=timestamp, *args, **kwargs)
	log(chr * length, filename, timestamp=False, *args, **kwargs)
	if append_newline: log_blank(filename, *args, **kwargs)

_log_filename_history = []
def set_current_log(fn):
	global _log_filename_history
	_log_filename_history.append(fn)

def end_current_log(fn=None):
	global _log_filename_history
	if fn:
		_log_filename_history.remove(fn)
	else:
		_log_filename_history = _log_filename_history[:-1]

def get_log_full_path(filename=None, extension='log', as_url_link=False, prefix='', **kwargs):
	global _log_filename_history
	log_base_name = FILES.LOGS.BASE_NAME
	filename_suffix = ''
	if filename and filename[0] == '*':
		filename_suffix = '\\' + filename[1:]
		log_base_name = ''
		filename = None
	if filename is None:
		if FILES.LOGS.USE_CALLER_NAME:
			caller = caller_name()
			if caller:
				filename = caller.Base.replace('.', '\\')
		if filename is None:
			filename = _log_filename_history[-1] if _log_filename_history else FILES.LOGS.ACTIVE
	if not filename:
		filename = log_base_name
		if not filename: filename = FILES.LOGS.DEFAULT_NAME
	else:
		if filename[0] is '+':
			filename = filename[1:]
		filename = (log_base_name + '-' if log_base_name and log_base_name[-1] != '\\' else '') + filename

	filename += filename_suffix
	filename += ('.' if filename and filename[-1] is not '.' else '') + extension
	filename = re.sub(r'[^\w\-_\.\\]', '_',  filename)
	full_path = os.path.join(FOLDERS.LOGS, filename)
	if prefix:
		parent, fn = os.path.split(full_path)
		if fn != '.' + extension: fn = '-' + fn
		full_path = os.path.join(parent, prefix + fn)
	if not os.path.exists(os.path.dirname(full_path)):
		os.makedirs(os.path.dirname(full_path))
	if as_url_link: return convert_filename_to_local_link(full_path)
	return full_path

def encode_log_text(content, encode_text=True, **kwargs):
	if not encode_text or not isinstance(content, str) and not isinstance(content, unicode): return content
	try: return content.encode('utf-8')
	except Exception: return content

def parse_log_content(content, prefix='', **kwargs):
	if content is None: return '', prefix 
	content = obj2log_simple(content)
	if len(content) == 0: content = '{EMPTY STRING}'
	if content[0] == "!": content = content[1:]; prefix = '\n'	
	return content, prefix 
	
def process_log_content(content, prefix='', timestamp=None, do_encode=True, **kwargs):	
	content  = pad_lines_regex(content, timestamp=timestamp, **kwargs)	
	st = '[%s]:\t' % datetime.now().strftime(ANKNOTES.DATE_FORMAT) if timestamp else ''
	return prefix + ' ' + st + (encode_log_text(content, **kwargs) if do_encode else content), content
	
def crosspost_log(content, filename=None, crosspost_to_default=False, crosspost=None, **kwargs):
	if crosspost_to_default and filename:
		summary = " ** %s%s: " % ('' if filename.upper() == 'ERROR' else 'CROSS-POST TO ',  filename.upper()) + content		
		log(summary[:200], **kwargs)
	if not crosspost: return 
	for fn in item_to_list(crosspost): log(content, fn, **kwargs)
	
def pad_lines_regex(content, timestamp=None, replace_newline=None, try_decode=True, **kwargs):
	content = PadLines(content, **kwargs)
	if not (timestamp and replace_newline is not False) and not replace_newline: return content 
	try: return re.sub(r'[\r\n]+', u'\n'+ANKNOTES.FORMATTING.TIMESTAMP_PAD, content)
	except UnicodeDecodeError: 
		if not try_decode: raise 
	return re.sub(r'[\r\n]+', u'\n'+ANKNOTES.FORMATTING.TIMESTAMP_PAD, content.decode('utf-8'))	
	
def write_file_contents(content, full_path, clear=False, try_encode=True, do_print=False, print_timestamp=True, print_content=None, **kwargs):
	if not os.path.exists(os.path.dirname(full_path)): full_path = get_log_full_path(full_path)
	with open(full_path, 'w+' if clear else 'a+') as fileLog:
		try: print>> fileLog, content
		except UnicodeEncodeError: content = content.encode('utf-8'); print>> fileLog, content
	if do_print: print content if print_timestamp or not print_content else print_content
	
# @clockit
def log(content=None, filename=None, **kwargs):
	kwargs = set_kwargs(kwargs, 'line_padding, line_padding_plus, line_padding_header', timestamp=True)
	content, prefix = parse_log_content(content, **kwargs)
	crosspost_log(content, filename, **kwargs)	
	full_path = get_log_full_path(filename, **kwargs)	
	content, print_content = process_log_content(content, prefix, **kwargs)
	write_file_contents(content, full_path, print_content=print_content, **kwargs)

def log_sql(content, **kwargs):
	log(content, 'sql', **kwargs)

def log_error(content, **kwargs):
	log(content, 'error', **kwargs)

def print_dump(obj):
	content = pprint.pformat(obj, indent=4, width=ANKNOTES.FORMATTING.PPRINT_WIDTH)
	content = content.replace(', ', ', \n ')
	content = content.replace('\r', '\r                              ').replace('\n',
																				'\n                              ')
	content = encode_log_text(content)
	print content
	return content

def log_dump(obj, title="Object", filename='', timestamp=True, extension='log', crosspost_to_default=True, **kwargs):
	content = pprint.pformat(obj, indent=4, width=ANKNOTES.FORMATTING.PPRINT_WIDTH)
	try: content = content.decode('utf-8', 'ignore')
	except Exception: pass
	content = content.replace("\\n", '\n').replace('\\r', '\r')
	if filename and filename[0] is '+':
		summary = " ** CROSS-POST TO %s: " % filename[1:] + content
		log(summary[:200])
	# filename = 'dump' + ('-%s' % filename if filename else '')
	full_path = get_log_full_path(filename, extension, prefix='dump')
	st = '[%s]: ' % datetime.now().strftime(ANKNOTES.DATE_FORMAT) if timestamp else ''

	if title[0] == '-': crosspost_to_default = False; title = title[1:] 
	prefix = " **** Dumping %s" % title
	if crosspost_to_default: log(prefix)

	content = encode_log_text(content)

	try:
		prefix += '\r\n'
		content = prefix + content.replace(', ', ', \n ')
		content = content.replace("': {", "': {\n ")
		content = content.replace('\r', '\r' + ' ' * 30).replace('\n', '\n' + ' ' * 30)
	except:
		pass

	if not os.path.exists(os.path.dirname(full_path)):
		os.makedirs(os.path.dirname(full_path))
	try_print(full_path, content, prefix, **kwargs)

def try_print(full_path, content, prefix='', line_prefix=u'\n ', attempt=0, clear=False):			
	try:
		print_content = line_prefix + (u' <%d>' % attempt if attempt > 0 else u'') + u' ' + st
		if attempt is 0: print_content += content
		elif attempt is 1: print_content += content.decode('utf-8')
		elif attempt is 2: print_content += content.encode('utf-8')
		elif attempt is 3: print_content = print_content.encode('utf-8') + content.encode('utf-8')
		elif attempt is 4: print_content = print_content.decode('utf-8') + content.decode('utf-8')
		elif attempt is 5: print_content += "Error printing content: " + str_safe(content)
		elif attempt is 6: print_content += "Error printing content: " + content[:10]
		elif attempt is 7: print_content += "Unable to print content."
		with open(full_path, 'w+' if clear else 'a+') as fileLog:
			print>> fileLog, print_content
	except:
		if attempt < 8: try_print(full_path, content, prefix=prefix, line_prefix=line_prefix, attempt=attempt+1, clear=clear)
		
def log_api(method, content='', **kwargs):
	if content: content = ': ' + content
	log(" API_CALL [%3d]: %10s%s" % (get_api_call_count(), method, content), 'api', **kwargs)


def get_api_call_count():
	path = get_log_full_path('api')
	if not os.path.exists(path): return 0
	api_log = file(path, 'r').read().splitlines()
	count = 1
	for i in range(len(api_log), 0, -1):
		call = api_log[i - 1]
		if not "API_CALL" in call:
			continue
		ts = call.replace(':\t', ': ').split(': ')[0][2:-1]
		td = datetime.now() - datetime.strptime(ts, ANKNOTES.DATE_FORMAT)
		if td < timedelta(hours=1):
			count += 1
		else:
			return count
	return count

def caller_names(return_string=True,  simplify=True):
	return [c.Base if return_string else c for c in [__caller_name__(i,simplify) for i in range(0,20)] if c and c.Base]

class CallerInfo:
	Class=[]
	Module=[]
	Outer=[]
	Name=""
	simplify=True
	__keywords_exclude__=['pydevd', 'logging', 'stopwatch']
	__keywords_strip__=['__maxin__', 'anknotes', '<module>']
	__outer__ = []
	filtered=True
	@property
	def __trace__(self):
		return self.Module + self.Outer + self.Class + [self.Name]

	@property
	def Trace(self):
		t= self._strip_(self.__trace__)
		return t if not self.filtered or not [e for e in self.__keywords_exclude__ if e in t] else []

	@property
	def Base(self):
		return '.'.join(self._strip_(self.Module + self.Class + [self.Name])) if self.Trace else ''

	@property
	def Full(self):
		return '.'.join(self.Trace)

	def _strip_(self, lst):
		return [t for t in lst if t and t not in self.__keywords_strip__]

	def __init__(self, parentframe=None):
		"""

		:rtype : CallerInfo
		"""
		if not parentframe: return
		self.Class = parentframe.f_locals['self'].__class__.__name__.split('.') if 'self' in parentframe.f_locals else []
		module = inspect.getmodule(parentframe)
		self.Module = module.__name__.split('.') if module else []
		self.Name = parentframe.f_code.co_name if parentframe.f_code.co_name is not '<module>' else ''
		self.__outer__ = [[f[1], f[3]] for f in inspect.getouterframes(parentframe) if f]
		self.__outer__.reverse()
		self.Outer = [f[1] for f in self.__outer__ if f and f[1] and not [exclude for exclude in self.__keywords_exclude__ + [self.Name] if exclude in f[0] or exclude in f[1]]]
		del parentframe

def create_log_filename(strr):
	if strr is None: return ""
	strr = strr.replace('.', '\\')
	strr = re.sub(r"(^|\\)([^\\]+)\\\2(\b.|\\.|$)", r"\1\2\\", strr)
	strr = re.sub(r"^\\*(.+?)\\*$", r"\1", strr)
	return strr
# @clockit
def caller_name(skip=None, simplify=True, return_string=False, return_filename=False):
	if skip is None: names = [__caller_name__(i,simplify) for i in range(0,20)]
	else: names = [__caller_name__(skip, simplify=simplify)]
	for c in [c for c in names if c and c.Base]:
		return create_log_filename(c.Base) if return_filename else c.Base if return_string else c
	return "" if return_filename or return_string else None

def __caller_name__(skip=0, simplify=True):
	"""Get a name of a caller in the format module.class.method

	   `skip` specifies how many levels of stack to skip while getting caller
	   name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

	   An empty string is returned if skipped levels exceed stack height
	:rtype : CallerInfo
	"""
	stack = inspect.stack()
	start = 0 + skip
	if len(stack) < start + 1:
	  return None
	parentframe = stack[start][0]
	c_info = CallerInfo(parentframe)
	del parentframe
	return c_info

# log('completed %s' % __name__, 'import')