# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- 7oars.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import time
from anknotes.structs import EvernoteAPIStatus
from anknotes.logging import caller_name, log, log_banner, show_report, counts_as_str
from anknotes.counters import Counter 

"""stopwatch is a very simple Python module for measuring time.
Great for finding out how long code takes to execute.

>>> import stopwatch
>>> t = stopwatch.Timer()
>>> t.elapsed
3.8274309635162354
>>> print t
15.9507198334 sec
>>> t.stop()
30.153270959854126
>>> print t
30.1532709599 sec

Decorator exists for printing out execution times:
>>> from stopwatch import clockit
>>> @clockit
	def mult(a, b):
		return a * b
>>> print mult(2, 6)
mult in 1.38282775879e-05 sec
6

"""

__version__ = '0.5'
__author__ = 'Avinash Puchalapalli <http://www.github.com/holycrepe/>'
__info__ = 'Forked from stopwatch 0.3.1 by John Paulett <http://blog.7oars.com>'

class TimerCounts(object):
	Max, Current, Updated, Added, Queued, Error = (0) * 6

class ActionInfo(object):
	Label = ""
	Status = EvernoteAPIStatus.Uninitialized
	__created_str__ = "Added to Anki"
	__updated_str__ = "Updated in Anki"
	@property
	def ActionShort(self):
		if self.__action_short: return self.__action_short
		return (self.ActionBase.upper() + 'ING').replace(' OFING', 'ING').replace("CREATEING", "CREATING") + ' ' + self.RowItemBase.upper()

	@property
	def ActionShortSingle(self):
		return self.ActionShort.replace('(s)','')

	@property
	def ActionTemplate(self):
		if self.__action_template: return self.__action_template
		return self.ActionBase + ' of {num} ' + self.RowItemFull.replace('(s)','')

	@property
	def ActionBase(self):
		return self.ActionTemplate.replace('{num} ', '')

	@property
	def Action(self):
		strNum = ''
		if self.Max:
			strNum = '%3d ' % self.Max
		return self.ActionTemplate.replace('(s)', '' if self.Max == 1 else 's').replace('{num} ', strNum)

	@property
	def Automated(self):
		return self.__automated

	@property
	def RowItemFull(self):
		if self.__row_item_full: return self.__row_item_full
		return self.RowItemBase

	@property
	def RowItemBase(self):
		return self.__row_item_base

	def RowSource(self):
		if self.__row_source: return self.__row_source
		return self.RowItemFull

	@property
	def Label(self):
		return self.__label

	@property
	def Max(self):
		return self.__max

	@property
	def Interval(self):
		return self.__interval

	@property
	def emptyResults(self):
		return (not self.Max)

	@property
	def willReportProgress(self):
		if not self.Max: return False
		if not self.Interval or self.Interval < 1: return False
		return self.Max > self.Interval

	def FormatLine(self, text, num=None):
		return text.format(num=('%'+len(str(self.Max))+'d ') % num if num else '',
		row_sources=self.RowSource.replace('(s)', 's'),
		rows=self.RowItemFull.replace('(s)', 's'),
		row=self.RowItemFull.replace('(s)', ''),
		row_=self.RowItemFull,
		r=self.RowItemFull.replace('(s)', '' if num == 1 else 's'),
		action=self.Action + ' '
		)

	def ActionLine(self, title, text,num=None):
		return "   > %s %s: %s" % (self.Action, title, self.FormatLine(text, num))

	def Aborted(self):
		return self.ActionLine("Aborted", "No Qualifying {row_sources} Found")

	def Initiated(self):
		return self.ActionLine("Initiated", "{num}{r} Found", self.Max)

	def BannerHeader(self,  append_newline=False):
		log_banner(self.Action.upper(), self.Label, append_newline=False)

	def setStatus(self, status):
		self.Status = status 
		return status 
		
	def displayInitialInfo(self,max=None,interval=None, automated=None):
		if max: self.__max = max
		if interval: self.__interval = interval
		if automated is not None: self.__automated = automated
		if self.emptyResults:
			if not self.automated:
				show_report(self.Aborted)
			return self.setStatus(EvernoteAPIStatus.EmptyRequest)
		log (self.Initiated)
		if self.willReportProgress:
			log_banner(self.Action.upper(), self.Label, append_newline=False)
		return self.setStatus(EvernoteAPIStatus.Initialized)
		
	def __init__(self, action_base='Upload of Validated Evernote Notes', row_item_base=None, row_item_full=None,action_template=None,  label=None, auto_label=True, max=None, automated=False, interval=None, row_source=None):
		if label is None and auto_label is True:
			label = caller_name()
			showInfo(label)
		if row_item_base is None:
			actions = action_base.split()
			assert len(actions) > 1
			action_base = actions[0]
			if actions[1] == 'of':
				action_base += ' of'
				actions = actions[1:]
				assert len(actions) > 1
			row_item_base = ' '.join(actions[1:])
			if row_item_full is None and len(actions)>2:
				row_item_base = actions[-1]
				row_item_full = ' '.join(actions[1:])
		self.__action_base = action_base
		self.__row_item_base = row_item_base
		self.__row_item_full = row_item_full
		self.__row_source = row_source
		self.__action_template = action_template
		self.__action = self.__action_template.replace('{num} ', '')
		self.__automated=automated
		self.__label = label
		self.__max = max
		self.__interval = interval


class Timer(object):
	__times = []
	__stopped = None
	__start = None
	__status = EvernoteAPIStatus.Uninitialized
	__counts = Counter()
	__count = 0
	__count_queued = 0
	__count_error = 0
	__count_created = 0
	__count_updated = 0
	__max = 0
	__laps = 0
	__interval = 100
	__parent_timer = None
	__info = None
	""":type : Timer"""

	@property 
	def counts(self):
		return self.__counts__
	
	@counts.setter
	def counts(self, value):
		self.__counts__ = value 
	
	@property
	def laps(self):
		return len(self.__times)

	@property
	def max(self):
		return self.__max

	@max.setter
	def max(self, value):
		self.__max = int(value)

	@property
	def count_success(self):
		return self.count_updated + self.count_created

	@property
	def count_queued(self):
		return self.__count_queued
	@property
	def count_created(self):
		return self.__count_created

	@property
	def count_updated(self):
		return self.__count_updated
		
	@property
	def subcount_created(self):
		return self.__subcount_created

	@property
	def subcount_updated(self):
		return self.__subcount_updated		

	@property
	def count_error(self):
		return self.__count_error

	@property
	def is_success(self):
		return self.count_success > 0

	@property
	def parent(self):
		return self.__parent_timer

	@property
	def label(self):
		if self.info: return self.info.Label
		return ""

	@parent.setter
	def parent(self, value):
		""":type value : Timer"""
		self.__parent_timer = value

	@property
	def parentTotal(self):
		if not self.__parent_timer: return -1
		return self.__parent_timer.total

	@property
	def percentOfParent(self):
		if not self.__parent_timer: return -1
		return float(self.total) / float(self.parentTotal) * 100

	@property
	def percentOfParentStr(self):
		return str(int(round(self.percentOfParent))) + '%'

	@property
	def percentComplete(self):
		return float(self.count) / self.__max * 100

	@property
	def percentCompleteStr(self):
		return str(int(round(self.percentComplete))) + '%'

	@property
	def rate(self):
		return self.rateCustom()

	@property
	def rateStr(self):
		return self.rateStrCustom()

	def rateCustom(self, unit=None):
		if unit is None: unit = self.__interval
		return self.elapsed/self.count * unit

	def rateStrCustom(self, unit=None):
		if unit is None: unit = self.__interval
		return self.__timetostr__(self.rateCustom(unit))

	@property
	def count(self):
		return self.__count

	@property
	def projectedTime(self):
		return self.__max * self.rateCustom(1)

	@property
	def projectedTimeStr(self):
		return self.__timetostr__(self.projectedTime)

	@property
	def remainingTime(self):
		return self.projectedTime - self.elapsed

	@property
	def remainingTimeStr(self):
		return self.__timetostr__(self.remainingTime)

	@property
	def progress(self):
		return '%5s (%3s): @ %3s/%d. %3s of %3s remain' % (self.__timetostr__(short=False), self.percentCompleteStr, self.rateStr, self.__interval,  self.remainingTimeStr, self.projectedTimeStr)

	@property
	def active(self):
		return self.__start and not self.__stopped

	@property
	def completed(self):
		return self.__start and self.__stopped

	@property
	def lap_info(self):
		strs = []
		if self.active:
			strs.append('Active:  %s' % self.__timetostr__())
		elif self.completed:
			strs.append('Latest:  %s' % self.__timetostr__())
		elif self.laps>0:
			strs.append('Last:    %s' % self.__timetostr__(self.__times) )
		if self.laps > 0 + 0 if self.active or self.completed else 1:
			strs.append('%2d Laps: %s' % (self.laps, self.__timetostr__(self.history)))
			strs.append('Average: %s' % self.__timetostr__(self.average))
		if self.__parent_timer:
			strs.append("Parent:  %s" % self.__timetostr__(self.parentTotal))
			strs.append("   (%3s)   " % self.percentOfParentStr)
		return ' | '.join(strs)

	@property
	def isProgressCheck(self):
		return self.count % max(self.__interval, 1) is 0

	@property 
	def status(self):
		if self.hasActionInfo: return self.info.Status 
		return self.__status 
		
	@status.setter
	def status(self, value):
		if self.hasActionInfo: self.info.Status = value 
	
	def autoStep(self, returned_tuple, title=None, update=None, val=None)
		self.step(title, val)
		return self.extractStatus(returned_tuple, update)
	
	def extractStatus(self, returned_tuple, update=None):
		self.report_result = self.reportStatus(returned_tuple[0], None)
		if len(returned_tuple) == 2: return returned_tuple[1]
		return returned_tuple[1:]
	
	def reportStatus(self, status, update=None):
		"""
		:type status : EvernoteAPIStatus
		"""
		self.status = status  
		if status.IsError: return self.reportError(save_status=False)
		if status == EvernoteAPIStatus.RequestQueued: return self.reportQueued(save_status=False)
		if status.IsSuccess: return self.reportSuccess(update, save_status=False)
		return False

	def reportSuccess(self, update=None, save_status=True):
		if save_status: self.status = EvernoteAPIStatus.Success
		if update: self.__count_updated += 1
		else: self.__count_created += 1
		return self.count_success

	def reportError(self, save_status=True):
		if save_status: self.status = EvernoteAPIStatus.GenericError
		self.__count_error += 1
		return self.count_error

	def reportQueued(self, save_status=True):
		if save_status: self.status = EvernoteAPIStatus.RequestQueued
		self.__count_queued += 1
		return self.count_queued

	def ReportHeader(self):
		return self.info.FormatLine("%s {r} successfully completed" % counts_as_str(self.count, self.max), self.count)

	def ReportSingle(self, text, count, subtext='', subcount=0)
		if not count: return []
		strs = [self.info.FormatLine("%s {r} %s" % (counts_as_str(count), text), self.count)]
		if subcount: strs.append("-%-3d of these were successfully %s " % (subcount, subtext))
		return strs

	def Report(self, subcount_created=0, subcount_updated=0):
		str_tips = []
		self.__subcount_created = subcount_created
		self.__subcount_updated = subcount_updated
		str_tips += self.ReportSingle('were newly created', self.count_created, self.info.__created_str__, subcount_created)
		str_tips += self.ReportSingle('already exist and were updated', self.count_updated, self.info.__updated_str__, subcount_updated)
		str_tips += self.ReportSingle('were queued', self.count_queued)
		if self.count_error: str_tips.append("%d Error(s) occurred " % self.count_error)
		show_report("   > %s Complete" % self.info.Action, self.ReportHeader, str_tips)

	def step(self, title=None, val=None):
		if val is None and unicode(title, 'utf-8', 'ignore').isnumeric():
			val = title
			title = None
		self.__count += val
		if self.hasActionInfo and self.isProgressCheck and title:
			log( self.info.ActionShortSingle + " %"+str(len('#'+str(self.max)))+"s: %s: %s" % ('#' + str(self.count), self.progress, title), self.label)
		return self.isProgressCheck


	@property
	def info(self):
		"""
		:rtype  : ActionInfo
		"""
		return self.__info

	@property
	def automated(self):
		if not self.info: return False
		return self.info.Automated

	@property
	def emptyResults(self)
		return (not max)

	def hasActionInfo(self):
		return self.info and self.max

	def __init__(self, max=None interval=100, info=None, infoStr=None, automated=None, begin=True, label=None):
		"""
		:type info : ActionInfo
		"""
		simple_label = False
		self.__max = 0 if max is None else max
		self.__interval = interval
		if infoStr and not info: info = ActionInfo(infoStr)
		if label and not info:
			simple_label = True
			info = ActionInfo(label, label=label)
		elif label: info.__label = label
		self.__info = info
		self.__action_initialized = False
		self.__action_attempted =  self.hasActionInfo and not simple_label
		if self.__action_attempted:
			self.__action_initialized = info.displayInitialInfo(max=max,interval=interval, automated=automated)
		if begin:
			self.reset()

	@property
	def willReportProgress(self):
		return self.max > self.interval

	@property
	def actionInitializationFailed(self):
		return self.__action_attempted and not self.__action_initialized

	@property
	def interval(self):
		return max(self.__interval, 1)

	def start(self):
		self.reset()

	def reset(self):
		self.__count =  self.__count_queued = self.__count_error = self.__count_created = self.__count_updated = 0
		if not self.__stopped: self.stop()
		self.__stopped = None
		self.__start = self.__time()

	def stop(self):
		"""Stops the clock permanently for the instance of the Timer.
		Returns the time at which the instance was stopped.
		"""
		if not self.__start: return -1
		self.__stopped = self.__last_time()
		self.__times.append(self.elapsed)
		return self.elapsed

	@property
	def history(self):
		return sum(self.__times)

	@property
	def total(self):
		return self.history + self.elapsed

	@property
	def average(self):
		return float(self.history) / self.laps

	def elapsed(self):
		"""The number of seconds since the current time that the Timer
		object was created.  If stop() was called, it is the number
		of seconds from the instance creation until stop() was called.
		"""
		if not self.__start: return -1
		return self.__last_time() - self.__start

	elapsed = property(elapsed)

	def start_time(self):
		"""The time at which the Timer instance was created.
		"""
		return self.__start

	start_time = property(start_time)

	def stop_time(self):
		"""The time at which stop() was called, or None if stop was
		never called.
		"""
		return self.__stopped

	stop_time = property(stop_time)

	def __last_time(self):
		"""Return the current time or the time at which stop() was call,
		if called at all.
		"""
		if self.__stopped is not None:
			return self.__stopped
		return self.__time()

	def __time(self):
		"""Wrapper for time.time() to allow unit testing.
		"""
		return time.time()

	def __timetostr__(self, total_seconds=None, short = True, pad=True):
		if total_seconds is None: total_seconds=self.elapsed
		total_seconds = int(round(total_seconds))
		if total_seconds < 60:
			return ['%ds','%2ds'][pad] % total_seconds
		m, s = divmod(total_seconds, 60)
		if short:
			# if total_seconds < 120: return '%dm' % (m, s)
			return ['%dm','%2dm'][pad] % m
		return '%d:%02d' % (m, s)

	def __str__(self):
		"""Nicely format the elapsed time
		"""
		return self.__timetostr__()


all_clockit_timers = {}
def clockit(func):
	"""Function decorator that times the evaluation of *func* and prints the
	execution time.
	"""
	def new(*args, **kw):
		# fn = func.__name__
		# print "Request to clock %s" % fn
		# return func(*args, **kw)
		global all_clockit_timers
		fn = func.__name__
		if fn not in all_clockit_timers:
			all_clockit_timers[fn] = Timer()
		else:
			all_clockit_timers[fn].reset()
		retval = func(*args, **kw)
		all_clockit_timers[fn].stop()
		# print ('Function %s completed in %s\n     > %s' % (fn, all_clockit_timers[fn].__timetostr__(short=False), all_clockit_timers[fn].lap_info))
		return retval
	return new
