# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- 7oars.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import time
import re
import os
from anknotes.constants import ANKNOTES
from anknotes.base import is_str, item_to_list
from anknotes.structs import EvernoteAPIStatus
from anknotes.logging import caller_name, log, log_banner, log_blank, show_report, counts_as_str, get_log_full_path
from anknotes.counters import Counter, EvernoteCounter
from anknotes.dicts import DictCaseInsensitive

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


# class TimerCounts(object):
# Max, Current, Updated, Added, Queued, Error = (0) * 6

class ActionInfo(object):
    Status = EvernoteAPIStatus.Uninitialized
    __created_str = " Added to Anki"
    __updated_str = " Updated in Anki"
    __queued_str = " for Upload to Evernote"

    @property
    def ActionShort(self):
        try:
            if self.__action_short:
                return self.__action_short
        finally:
            return (self.ActionBase.upper() + 'ING').replace('INGING', 'ING').replace(' OFING', 'ING').replace(
                "TIONING", "TING").replace("CREATEING", "CREATING") + ' ' + self.RowItemBase.upper()

    @property
    def ActionShortSingle(self):
        return self.ActionShort.replace('(s)', '')

    @property
    def ActionTemplate(self):
        return self._action_template_()

    @property
    def ActionTemplateNumeric(self):
        return self._action_template_(True)

    def _action_template_(self, numeric=False, short_row=False):
        if self.__action_template:
            return self.__action_template
        return self.ActionBase + (' {num} ' if numeric else ' ') + (self.RowItemBase if short_row else self.RowItemFull)

    @property
    def ActionBase(self):
        return self.__action_base

    def _action_(self, **kw):
        strNum = '' if self.emptyResults else '%3d ' % self.Max
        template = re.sub(r'\(([sS])\)', '' if self.Max == 1 else r'\1', self._action_template_(**kw))
        return template.replace('{num} ', strNum)

    @property
    def Action(self):
        return self._action_()

    @property
    def ActionNumeric(self):
        return self._action_(numeric=True)

    @property
    def Automated(self):
        return self.__automated

    @property
    def RowItemFull(self):
        if self.__row_item_full:
            if self.RowItemBase in self.__row_item_full:
                return self.__row_item_full
            return self.RowItemBase + ' ' + self.__row_item_full
        return self.RowItemBase

    @property
    def RowItemBase(self):
        return self.__row_item_base

    @property
    def RowSource(self):
        if self.__row_source:
            return self.__row_source
        return self.RowItemFull

    @property
    def Label(self):
        return self.__label

    @Label.setter
    def Label(self, value):
        self.__label = value

    @property
    def Max(self):
        if not self.__max:
            return -1
        if isinstance(self.__max, Counter):
            return self.__max.val
        return self.__max

    @Max.setter
    def Max(self, value): self.__max = value

    @property
    def Interval(self):
        return self.__interval

    @property
    def emptyResults(self):
        return not self.Max or self.Max < 0

    @property
    def willReportProgress(self):
        if self.emptyResults:
            return False
        if not self.Interval or self.Interval < 1:
            return False
        return self.Max > self.Interval

    def FormatLine(self, text, num=None):
        if isinstance(num, Counter):
            num = num.val
        return text.format(num=('%' + str(len(str(self.Max))) + 'd ') % num if num else '',
                           row_sources=self.RowSource.replace('(s)', 's'),
                           rows=self.RowItemFull.replace('(s)', 's'),
                           row=self.RowItemFull.replace('(s)', ''),
                           row_=self.RowItemFull,
                           r=self.RowItemFull.replace('(s)', '' if num == 1 else 's'),
                           action=self.Action + ' '
                           )

    def ActionLine(self, title, text='', num=None, short_row=True, **kw):
        if num:
            kw['numeric'] = True
        kw['short_row'] = short_row
        action = self._action_(**kw)
        if action == action.upper():
            title = title.upper()
        if text:
            text = ': ' + self.FormatLine(text, num)
        return "   > %s %s%s" % (action, title, text)

    @property
    def Aborted(self):
        return self.ActionLine("Aborted", "No Qualifying {row_sources} Found")

    @property
    def Initiated(self):
        return self.ActionLine("Initiated", num=self.Max)

    def BannerHeader(self, append_newline=False, filename=None, crosspost=None, bh_wrap_filename=True, **kw):
        if filename is None:
            filename = ''
        if bh_wrap_filename:
            filename = self.Label + filename
            if crosspost is not None:
                crosspost = [self.Label + cp for cp in item_to_list(crosspost, False)]
        log_banner(self.ActionNumeric.upper(), do_print=self.__do_print, **DictCaseInsensitive(kw, locals(), delete='self kw bh_wrap_filename cp'))

    def setStatus(self, status):
        self.Status = status
        return status

    def displayInitialInfo(self, max=None, interval=None, automated=None, enabled=None, **kw):
        if max:
            self.__max = max
        if interval:
            self.__interval = interval
        if automated is not None:
            self.__automated = automated
        if enabled is not None:
            self.__enabled = enabled
        if self.emptyResults:
            if not self.Automated and self.__report_if_empty:
                log('report: ' + self.Aborted, self.Label)
                show_report(self.Aborted, blank_line_before=False)
            else:
                log('report: [automated] ' + self.Aborted, self.Label)
            return self.setStatus(EvernoteAPIStatus.EmptyRequest)
        if self.__enabled is False:
            log("Not starting - stopwatch.ActionInfo: enabled = false ", self.Label, do_print=self.__do_print)
            if not automated:
                show_report(self.ActionLine("Aborted", "Action has been disabled"),
                                          blank_line_before=False)
            return self.setStatus(EvernoteAPIStatus.Disabled)
        log(self.Initiated, do_print=self.__do_print)
        self.BannerHeader()
        return self.setStatus(EvernoteAPIStatus.Initialized)

    def str_value(self, str_name):
        return getattr(self, '_' + self.__class__.__name__ + '__' + str_name + '_str')

    def __init__(self, action_base='Upload of Validated Evernote Notes', row_item_base=None, row_item_full=None,
                 action_full=None, action_template=None, label=None, auto_label=True, max=None, automated=False, enabled=True,
                 interval=None, row_source=None, do_print=False, report_if_empty=True, **kw):
        self.__action_short = None
        if label is None and auto_label:
            label = caller_name(return_filename=True)
        if row_item_base is None:
            actions = action_base.split()
            action_base = actions[0]
            if len(actions) == 1:
                action_base = actions[0]
                row_item_base = action_base
            else:
                if actions[1].lower() == 'of':
                    action_base += ' ' + actions[1]
                    actions = actions[1:]
                    assert len(actions) > 1
                row_item_base = ' '.join(actions[1:])
                if row_item_full is None and len(actions) > 2:
                    row_item_base = actions[-1]
                    row_item_full = ' '.join(actions[1:])
        self.__action_base = action_base
        self.__action_full = action_full
        self.__row_item_base = row_item_base
        self.__row_item_full = row_item_full
        self.__row_source = row_source
        self.__action_template = action_template
        self.__automated = automated
        self.__enabled = enabled
        self.__label = label
        self.__max = max
        self.__interval = interval
        self.__do_print = do_print
        self.__report_if_empty = report_if_empty


class Timer(object):
    __times = []
    __stopped = None
    __start = None
    __status = EvernoteAPIStatus.Uninitialized
    __counts = None
    __did_break = True
    __laps = 0
    __interval = 100
    __parent_timer = None
    __caller = None
    __info = None
    """:type : Timer"""

    @property
    def counts(self):
        if self.__counts is None:
            log("Init counter from property: " + repr(self.__counts), "counters")
            self.__counts = EvernoteCounter()
        return self.__counts

    @counts.setter
    def counts(self, value):
        self.__counts = value

    @property
    def laps(self):
        return len(self.__times)

    @property
    def max(self): 
        return self.counts.max

    @max.setter
    def max(self, value): 
        self.counts.max = value
        if self.counts.max_allowed < 1:
            self.counts.max_allowed = value

    @property
    def is_success(self):
        return self.counts.success

    @property
    def parent(self):
        return self.__parent_timer

    @property
    def label(self):
        if self.info:
            return self.info.Label
        return ""

    @label.setter
    def label(self, value):
        if self.info and isinstance(self.info, ActionInfo):
            self.info.Label = value
            return
        self.__info = ActionInfo(value, label=value)

    @parent.setter
    def parent(self, value):
        """:type value : Timer"""
        self.__parent_timer = value

    @property
    def parentTotal(self):
        if not self.__parent_timer:
            return -1
        return self.__parent_timer.total

    @property
    def percentOfParent(self):
        if not self.__parent_timer:
            return -1
        return float(self.total) / float(self.parentTotal) * 100

    @property
    def percentOfParentStr(self):
        return str(int(round(self.percentOfParent))) + '%'

    @property
    def percentComplete(self):
        if not self.counts.max:
            return -1
        return float(self.count) / self.counts.max * 100

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
        if unit is None:
            unit = self.__interval
        return self.elapsed / self.count * unit

    def rateStrCustom(self, unit=None):
        if unit is None:
            unit = self.__interval
        return self.__timetostr(self.rateCustom(unit))

    @property
    def count(self):
        return max(self.counts.val, 1)

    @property
    def projectedTime(self):
        if not self.counts.max:
            return -1
        return self.counts.max * self.rateCustom(1)

    @property
    def projectedTimeStr(self):
        return self.__timetostr(self.projectedTime)

    @property
    def remainingTime(self):
        return self.projectedTime - self.elapsed

    @property
    def remainingTimeStr(self):
        return self.__timetostr(self.remainingTime)

    @property
    def progress(self):
        return '%5s (%3s): @ %3s/%d. %3s of %3s remain' % (
            self.__timetostr(short=False), self.percentCompleteStr, self.rateStr, self.__interval,
            self.remainingTimeStr,
            self.projectedTimeStr)

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
            strs.append('Active:  %s' % self.__timetostr())
        elif self.completed:
            strs.append('Latest:  %s' % self.__timetostr())
        elif self.laps > 0:
            strs.append('Last:    %s' % self.__timetostr(self.__times))
        if self.laps > 0 + 0 if self.active or self.completed else 1:
            strs.append('%2d Laps: %s' % (self.laps, self.__timetostr(self.history)))
            strs.append('Average: %s' % self.__timetostr(self.average))
        if self.__parent_timer:
            strs.append("Parent:  %s" % self.__timetostr(self.parentTotal))
            strs.append("   (%3s)   " % self.percentOfParentStr)
        return ' | '.join(strs)

    @property
    def isProgressCheck(self):
        if not self.counts.max:
            return False
        return self.count % max(self.__interval, 1) is 0

    @property
    def status(self):
        if self.hasActionInfo:
            return self.info.Status
        return self.__status

    @status.setter
    def status(self, value):
        if self.hasActionInfo:
            self.info.Status = value

    def autoStep(self, returned_tuple, title=None, update=None):
        retval = self.extractStatus(returned_tuple, update)
        self.step(title)
        return retval

    def extractStatus(self, returned_tuple, update=None):
        self.report_result = self.reportStatus(returned_tuple[0], update)
        if len(returned_tuple) == 2:
            return returned_tuple[1]
        return returned_tuple[1:]

    def checkLimits(self):
        if not -1 < self.counts.max_allowed <= self.counts.updated + self.counts.created:
            return True
        log("Count exceeded- Breaking with status " + str(self.status), self.label, do_print=self.__do_print)
        self.reportStatus(EvernoteAPIStatus.ExceededLocalLimit)
        return False

    def reportStatus(self, status, update=None, title=None, **kw):
        """
        :type status : EvernoteAPIStatus
        """
        self.status = status
        if status.IsError:
            retval = self.reportError(save_status=False)
        elif status == EvernoteAPIStatus.RequestQueued:
            retval = self.reportQueued(save_status=False)
        elif status.IsSuccess:
            retval = self.reportSuccess(update, save_status=False)
        elif status == EvernoteAPIStatus.ExceededLocalLimit:
            retval = status
        else:
            self.counts.unhandled.step()
            retval = False
        if title:
            self.step(title, **kw)
        return retval

    def reportSkipped(self, save_status=True):
        if save_status:
            self.status = EvernoteAPIStatus.RequestSkipped
        return self.counts.skipped.step()

    def reportSuccess(self, update=None, save_status=True):
        if save_status:
            self.status = EvernoteAPIStatus.Success
        if update:
            self.counts.updated.completed.step()
        else:
            self.counts.created.completed.step()
        return self.counts.success

    def reportError(self, save_status=True):
        if save_status:
            self.status = EvernoteAPIStatus.GenericError
        return self.counts.error.step()

    def reportQueued(self, save_status=True, update=None):
        if save_status:
            self.status = EvernoteAPIStatus.RequestQueued
        if update:
            return self.counts.updated.queued.step()
        return self.counts.created.queued.step()

    @property
    def ReportHeader(self):
        return None if not self.counts.total else self.info.FormatLine(
            "%s {r} were processed" % counts_as_str(self.counts.total, self.counts.max), self.counts.total)

    def ReportSingle(self, text, count, subtext='', queued_text='', queued=0, subcount=0, process_subcounts=True):
        if not count:
            return []
        if isinstance(count, Counter) and process_subcounts:
            if count.queued:
                queued = count.queued.val
            if count.completed.subcount:
                subcount = count.completed.subcount.val
        if not queued_text:
            queued_text = self.info.str_value('queued')
        strs = [self.info.FormatLine("%s {r} %s" % (counts_as_str(count), text), self.count)]
        if process_subcounts:
            if queued:
                strs.append("-%-3d of these were queued%s" % (queued, queued_text))
            if subcount:
                strs.append("-%-3d of these were successfully%s " % (subcount, subtext))
        return strs

    def Report(self, subcount_created=0, subcount_updated=0):
        str_tips = []
        self.counts.created.completed.subcount = subcount_created
        self.counts.updated.completed.subcount = subcount_updated
        str_tips += self.ReportSingle('were newly created', self.counts.created, self.info.str_value('created'))
        str_tips += self.ReportSingle('already exist and were updated', self.counts.updated, self.info.str_value('updated'))
        str_tips += self.ReportSingle('already exist but were unchanged', self.counts.skipped, process_subcounts=False)
        if self.counts.error:
            str_tips.append("%d Error(s) occurred " % self.counts.error.val)
        if self.status == EvernoteAPIStatus.ExceededLocalLimit:
            str_tips.append("Action was prematurely terminated because locally-defined limit of %d was exceeded." %
                            self.counts.max_allowed)
        report_title = "   > %s Complete" % self.info.Action
        if self.counts.total is 0:
            report_title += self.info.FormatLine(": No {r} were processed")
        show_report(report_title, self.ReportHeader, str_tips, blank_line_before=False, do_print=self.__do_print)
        log_blank('counters')
        log(self.counts.fullSummary(self.name + ': End'), 'counters')

    def increment(self, *a, **kw):
        self.counts.step(**kw)
        return self.step(*a, **kw)

    def step(self, title=None, **kw):
        if self.hasActionInfo and self.isProgressCheck and title:
            title_str = ("%" + str(len('#' + str(self.max))) + "s:   %s") % ('#' + str(self.count), title)
            progress_str = ' [%s]' % self.progress
            title_len = ANKNOTES.FORMATTING.LINE_LENGTH_TOTAL - 1 - 2 - len(progress_str)
            log_path = self.label + ('' if self.label.endswith('\\') else '-') + 'progress'
            if not self.__reported_progress:
                self.info.BannerHeader(filename=log_path, bh_wrap_filename=False)
                self.__reported_progress = True
            log(title_str.ljust(title_len) + progress_str, log_path, timestamp=False, do_print=self.__do_print, **kw)
        return self.isProgressCheck

    @property
    def info(self):
        """
        :rtype  : ActionInfo
        """
        return self.__info

    @property
    def did_break(self): return self.__did_break

    def reportNoBreak(self): self.__did_break = False

    @property
    def should_retry(self): return self.did_break and self.status != EvernoteAPIStatus.ExceededLocalLimit

    @property
    def automated(self):
        if self.info is None:
            return False
        return self.info.Automated

    def hasActionInfo(self):
        return self.info is not None and self.counts.max > 0

    def __init__(self, max=None, interval=100, info=None, infoStr=None, automated=None, begin=True,
                 label=None, display_initial_info=None, max_allowed=None, do_print=False, **kw):
        """
        :type info : ActionInfo
        """
        args = DictCaseInsensitive(kw, locals(), delete='kw infoStr info max self')
        simple_label = False
        self.counts = EvernoteCounter()
        self.__interval = interval
        self.__reported_progress = False
        if not isinstance(max, int):
            if hasattr(max, '__len__'):
                max = len(max)
            else:
                max = None
        self.counts.max = -1
        if max is not None:
            self.counts.max = max
            args.max = self.counts.max
        if is_str(info):
            # noinspection PyTypeChecker
            info = ActionInfo(info, **args)
        elif infoStr and not info:
            info = ActionInfo(infoStr, **args)
        elif label and not info:
            simple_label = True
            if display_initial_info is None:
                display_initial_info = False
            info = ActionInfo(label, **args)
        elif label:
            info.Label = label
        if self.counts.max > 0 and info and (info.Max is None or info.Max < 1):
            info.Max = max
        self.counts.max_allowed = self.counts.max if max_allowed is None else max_allowed
        self.__did_break = True
        self.__do_print = do_print
        self.__info = info
        self.__action_initialized = False
        self.__action_attempted = self.hasActionInfo and (display_initial_info is not False)
        if self.__action_attempted:
            if self.info is None:
                log("Unexpected; Timer '%s' has no ActionInfo instance" % label, do_print=True)
            else:
                self.__action_initialized = self.info.displayInitialInfo(**args) is EvernoteAPIStatus.Initialized
        if begin:
            self.reset(False)
        log_blank(filename='counters')
        log(self.counts.fullSummary(self.name + ': Start'), 'counters')

    @property
    def name(self):
        name = (self.label.strip('\\').replace('\\', ': ') if self.label else self.caller)
        return name.replace('.', ': ').replace('-', ': ').replace('_', ' ').capitalize()

    @property
    def base_name(self):
        return self.name.split(': ')[-1]

    @property
    def caller(self):
        if self.__caller is None:
            self.__caller = caller_name(return_filename=True)
        return self.__caller

    @property
    def willReportProgress(self):
        return self.counts.max and self.counts.max > self.interval

    @property
    def actionInitializationFailed(self):
        return self.__action_attempted and not self.__action_initialized

    @property
    def interval(self):
        return max(self.__interval, 1)

    def start(self):
        self.reset()

    def reset(self, reset_counter=True):
        # keep = []
        # if self.counts:
        # keep = [self.counts.max, self.counts.max_allowed]
        # del self.__counts
        if reset_counter:
            log("Resetting counter", 'counters')
            if self.counts is None:
                self.counts = EvernoteCounter()
            else:
                self.counts.reset()
            # if keep:
            # self.counts.max = keep[0]
            # self.counts.max_allowed = keep[1]
        if not self.__stopped:
            self.stop()
        self.__stopped = None
        self.__start = self.__time()

    def stop(self):
        """Stops the clock permanently for the instance of the Timer.
        Returns the time at which the instance was stopped.
        """
        if not self.__start:
            return -1
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
        if not self.__start:
            return -1
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

    @property
    def str_long(self):
        return self.__timetostr(short=False)

    def __timetostr(self, total_seconds=None, short=True, pad=True):
        if total_seconds is None:
            total_seconds = self.elapsed
        total_seconds = int(round(total_seconds))
        if total_seconds < 60:
            return ['%ds', '%2ds'][pad] % total_seconds
        m, s = divmod(total_seconds, 60)
        if short:
            # if total_seconds < 120: return '%dm' % (m, s)
            return ['%dm', '%2dm'][pad] % m
        return '%d:%02d' % (m, s)

    def __str__(self):
        """Nicely format the elapsed time
        """
        return self.__timetostr()

    def __repr__(self):
        return "<%s%s> %s" % (self.__class__.__name__, '' if not self.label else ':%s' % self.label, self.str_long)


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
        # print ('Function %s completed in %s\n     > %s' % (fn, all_clockit_timers[fn].__timetostr(short=False), all_clockit_timers[fn].lap_info))
        return retval

    return new
