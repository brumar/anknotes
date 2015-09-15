# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 John Paulett (john -at- 7oars.com)
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import unittest
import doctest
import stopwatch
from stopwatch import clockit

class TimeControlledTimer(stopwatch.Timer):
    def __init__(self):
        self.__count = 0
        super(TimeControlledTimer, self).__init__()
        
    def __time(self):
        retval = self.__count
        self.__count += 1
        return retval       


class TimerTestCase(unittest.TestCase):
    def setUp(self):
        self.timer = stopwatch.Timer()
        
    def test_simple(self):
        point1 = self.timer.elapsed
        self.assertTrue(point1 > 0)
        
        point2 = self.timer.elapsed
        self.assertTrue(point2 > point1)
        
        point3 = self.timer.elapsed
        self.assertTrue(point3 > point2)
    
    def test_stop(self):
        point1 = self.timer.elapsed
        self.assertTrue(point1 > 0)
        
        self.timer.stop()
        point2 = self.timer.elapsed
        self.assertTrue(point2 > point1)
        
        point3 = self.timer.elapsed
        self.assertEqual(point2, point3)

@clockit
def timed_multiply(a, b):
    return a * b
    
class DecoratorTestCase(unittest.TestCase):
    def test_clockit(self):
        self.assertEqual(6, timed_multiply(2, b=3))
        
def suite():
    suite = unittest.TestSuite()  
    suite.addTest(unittest.makeSuite(TimerTestCase))
    suite.addTest(unittest.makeSuite(DecoratorTestCase))
    #suite.addTest(doctest.DocTestSuite(stopwatch))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')