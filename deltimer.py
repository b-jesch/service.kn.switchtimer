#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc
import handler

if __name__ ==  '__main__':

    handler.notifyLog('Parameter handler called: Delete Timerlist')
    handler.clearTimerProperties()
