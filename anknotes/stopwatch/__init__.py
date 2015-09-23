# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- 7oars.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import time
# from anknotes.logging import log

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

class Timer(object):
    __times = []
    __stopped = None
    __start = None
    __count = 0
    __max = 0
    __laps = 0
    __interval = 100
    __parent_timer = None 
    """:type : Timer"""

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
    def parent(self):
        return self.__parent_timer
        
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
        return float(self.__count) / self.__max * 100

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
        return self.elapsed/self.__count * unit

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
        return '%4s (%3s): @ %3s/%d. %3s of %3s remain' % (self.__timetostr__(short=False), self.percentCompleteStr, self.rateStr, self.__interval,  self.remainingTimeStr, self.projectedTimeStr)
        
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

    def step(self, val=1):
        self.__count += val
        return self.isProgressCheck

    def __init__(self, begin=True, max=0, interval=100):
        if begin:
            self.reset()
        self.__max = max
        self.__interval = interval

    def start(self):
        self.reset()

    def reset(self):
        self.__count = 0        
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
