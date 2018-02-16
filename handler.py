#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time
import xbmc, xbmcaddon, xbmcgui
import os
import operator
import json

import resources.lib.knClasses as knClasses

addon = xbmcaddon.Addon()
addonid = xbmcaddon.Addon().getAddonInfo('id')
addonname = xbmcaddon.Addon().getAddonInfo('name')
path = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path'))
profiles = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
version = xbmcaddon.Addon().getAddonInfo('version')
loc = xbmcaddon.Addon().getLocalizedString

IconDefault = os.path.join(path, 'resources', 'media', 'default.png')
IconAlert = os.path.join(path, 'resources', 'media', 'alert.png')
IconOk = os.path.join(path, 'resources', 'media', 'ok.png')

confirmTmrAdded = True if xbmcaddon.Addon().getSetting('confirmTmrAdded').upper() == 'TRUE' else False

OSD = xbmcgui.Dialog()
OSDProgress = xbmcgui.DialogProgress()
HOME = xbmcgui.Window(10000)

if not os.path.exists(profiles): os.makedirs(profiles, 0755)
__timer__ = os.path.join(profiles, 'timer.json')

__timerdict__ = {'channel': None, 'icon': None, 'date': None, 'title': None, 'plot': None}

def putTimer(timers):
    for timer in timers:
        if not timer['utime'] or timer['utime'] < time.time(): timers.remove(timer)
    with open(__timer__, 'w') as handle:
        json.dump(timers, handle)
    HOME.setProperty('SwitchTimerActiveItems', str(len(timers)))
    notifyLog('%s timer(s) written' % (len(timers)), xbmc.LOGNOTICE)

def getTimer():
    try:
        with open(__timer__, 'r') as handle:
            timers = json.load(handle)
    except IOError:
        timers = []
    HOME.setProperty('SwitchTimerActiveItems', str(len(timers)))
    return timers

def getSetting(setting):
    return xbmcaddon.Addon().getSetting(setting)

def notifyLog(message, level=xbmc.LOGDEBUG):
    xbmc.log('[%s] %s' % (addonid, message.encode('utf-8')), level)

def notifyOSD(header, message, icon=IconDefault, time=5000):
    OSD.notification(header.encode('utf-8'), message.encode('utf-8'), icon, time)

def setTimer(params):
    utime = knClasses.date2timeStamp(params['date'])
    if not utime: return False

    _now = int(time.time())
    if _now > utime:
        notifyLog('Timer date in the past', xbmc.LOGNOTICE)
        notifyOSD(loc(30000), loc(30022), icon=IconAlert)
        return False

    timers = getTimer()
    for timer in timers:
        if knClasses.date2timeStamp(timer['date']) == utime:
            notifyLog('Timer already set, ask for replace', xbmc.LOGNOTICE)
            _res = OSD.yesno(addonname, loc(30031) % (timer['channel'], timer['title']))

            if not _res: return False
            timers.remove(timer)

    if len(timers) > 9:
        notifyLog('Timer limit exceeded, no free slot', xbmc.LOGFATAL)
        notifyOSD(loc(30000), loc(30024), icon=IconAlert)
        return False

    # append timer and sort timerlist

    params['utime'] = utime
    timers.append(params)
    timers.sort(key=operator.itemgetter('utime'))

    setTimerProperties(timers)
    putTimer(timers)

    notifyLog('Timer added @%s, %s, %s' % (params['date'], params['channel'].decode('utf-8'), params['title'].decode('utf-8')), xbmc.LOGNOTICE)
    if confirmTmrAdded: notifyOSD(loc(30000), loc(30021), icon=IconOk)
    return True

def setTimerProperties(timerlist):
    _idx = 0
    for prefix in ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']:

        if _idx < len(timerlist):
            # Set timer properties
            for element in __timerdict__:
                try:
                    HOME.setProperty('%s:%s' % (prefix, element), timerlist[_idx][element])
                except KeyError:
                    pass
            _idx += 1
        else:
            # Clear remaining properties
            clearTimerProperties(prefix)

def clearTimerProperties(prefix=None):
    if not prefix:
        for prefix in ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']:
            for element in __timerdict__: HOME.clearProperty('%s:%s' % (prefix, element))
        timers = []
        notifyLog('Properties of all timers deleted, timerlist cleared')
    else:
        _date = HOME.getProperty('%s:date' % (prefix))
        if _date == '': return False
        timers = getTimer()
        for timer in timers:
            if timer['date'] == _date: timer['utime'] = None
            for element in __timerdict__: HOME.clearProperty('%s:%s' % (prefix, element))
            notifyLog('Properties for timer %s @%s deleted' % (prefix, _date))

    putTimer(timers)
    return True

if __name__ ==  '__main__':

    notifyLog('Parameter handler called')
    try:
        if sys.argv[1]:
            args = {'action':None, 'channel':'', 'icon': '', 'date':'', 'title':'', 'plot': ''}
            pars = sys.argv[1:]
            for par in pars:
                try:
                    item, value = par.split('=')
                    args[item] = value.replace(',', '&comma;').decode('utf-8')
                    notifyLog('Provided parameter %s: %s' % (item, args[item]))
                except ValueError:
                    args[item] += ', ' + par

            if args['action'] == 'add':
                if not setTimer(args):
                    notifyLog('Timer couldn\'t or wouldn\'t set', xbmc.LOGERROR)
            elif args['action'] == 'del':
                clearTimerProperties(args['timer'])
            elif args['action'] == 'delall':
                for prefix in ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']: clearTimerProperties()
    except IndexError:
        _tlist = []
        timers = getTimer()
        if len(timers) > 0:
            for timer in timers:
                liz = xbmcgui.ListItem(label='%s: %s' % (timer['date'], timer['channel']),
                                       label2=timer['title'], iconImage=timer['icon'])
                liz.setProperty('utime', str(timer['utime']))
                liz.setProperty('date', timer['date'])
                _tlist.append(liz)

            _idx = OSD.select(loc(30015), _tlist, useDetails=True)
            if _idx > -1:
                timers[_idx].update({'utime': None})
                _date = timers[_idx].get('date', '')
                for element in __timerdict__: HOME.clearProperty('t%s:%s' % (_idx, element))
                putTimer(timers)
                notifyLog('Properties for timer t%s @%s deleted' % (_idx, _date))

        else:
            notifyLog('No active timers yet', xbmc.LOGERROR)
            OSD.ok(loc(30000), loc(30030))
    except Exception, e:
        notifyLog('Script error: %s' % (e.message), xbmc.LOGERROR)

