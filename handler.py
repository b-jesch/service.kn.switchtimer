#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import operator
import json

import resources.lib.knClasses as knClasses

addon = xbmcaddon.Addon()
addonid = xbmcaddon.Addon().getAddonInfo('id')
addonname = xbmcaddon.Addon().getAddonInfo('name')
path = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path'))
profiles = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
version = xbmcaddon.Addon().getAddonInfo('version')
loc = xbmcaddon.Addon().getLocalizedString

IconDefault = os.path.join(path, 'resources', 'media', 'default.png')
IconAlert = os.path.join(path, 'resources', 'media', 'alert.png')
IconOk = os.path.join(path, 'resources', 'media', 'ok.png')

confirmTmrAdded = True if xbmcaddon.Addon().getSetting('confirmTmrAdded').upper() == 'TRUE' else False

OSD = xbmcgui.Dialog()
OSDProgress = xbmcgui.DialogProgress()
HOME = xbmcgui.Window(10000)

if not os.path.exists(profiles): os.makedirs(profiles, 0o755)
__timer__ = os.path.join(profiles, 'timer.json')

__timerdict__ = {'channel': None, 'icon': None, 'date': None, 'title': None, 'plot': None}


def putTimer(timers):
    for timer in timers:
        if not timer['utime'] or timer['utime'] < time.time(): timers.remove(timer)
    with open(__timer__, 'w') as handle:
        json.dump(timers, handle, indent=4)
    HOME.setProperty('SwitchTimerActiveItems', str(len(timers)))
    notifyLog('%s timer(s) written' % (len(timers)), xbmc.LOGINFO)


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
    xbmc.log('[%s] %s' % (addonid, message), level)


def notifyOSD(header, message, icon=IconDefault, time=5000):
    OSD.notification(header, message, icon, time)


def setTimer(params):
    utime = knClasses.date2timeStamp(params['date'])
    if not utime: return False

    _now = int(time.time())
    if _now > utime:
        notifyLog('Timer date in the past', xbmc.LOGINFO)
        notifyOSD(loc(30000), loc(30022), icon=IconAlert)
        return False

    timers = getTimer()
    for timer in timers:
        if knClasses.date2timeStamp(timer['date']) == utime:
            notifyLog('Timer already set, ask for replace', xbmc.LOGINFO)
            _res = OSD.yesno(addonname, loc(30031) % (timer['channel'], timer['title']))

            if not _res: return False
            timers.remove(timer)

    # append timer and sort timerlist

    params['utime'] = utime
    timers.append(params)
    timers.sort(key=operator.itemgetter('utime'))

    # setTimerProperties(timers)
    putTimer(timers)

    notifyLog('Timer added @%s, %s, %s' % (params['date'], params['channel'], params['title']), xbmc.LOGINFO)
    if confirmTmrAdded: notifyOSD(loc(30000), loc(30021), icon=IconOk)
    return True


def clearTimer(date=None):
    if not date:
        timers = []
        notifyLog('all timers deleted, timer list cleared')
    else:
        timers = getTimer()
        for timer in timers:
            if timer['date'] == date: timer['utime'] = None
            notifyLog('Timer @%s deleted' % (date))
    putTimer(timers)
    return True


if __name__ ==  '__main__':

    notifyLog('Parameter handler called')
    try:
        if sys.argv[1]:
            args = {'action': None, 'channel': '', 'icon': '', 'date': '', 'title': '', 'plot': ''}
            pars = sys.argv[1:]
            for par in pars:
                try:
                    item, value = par.split('=')
                    args[item] = value.replace(',', '&comma;')
                    notifyLog('Provided parameter %s: %s' % (item, args[item]))
                except ValueError:
                    args[item] += ', ' + par

            if args['action'] == 'add':
                if not setTimer(args):
                    notifyLog('Timer couldn\'t or wouldn\'t set', xbmc.LOGERROR)
            elif args['action'] == 'del':
                clearTimer(args['timer'])
            elif args['action'] == 'delall':
                clearTimer()
    except IndexError:
        _tlist = []
        timers = getTimer()
        if len(timers) > 0:
            for timer in timers:
                liz = xbmcgui.ListItem(label='%s: %s' % (timer['date'], timer['channel']),
                                       label2=timer['title'])
                liz.setArt({'icon': timer['icon']})
                liz.setProperty('utime', str(timer['utime']))
                liz.setProperty('date', timer['date'])
                _tlist.append(liz)

            # set last entry for deleting all timers
            liz = xbmcgui.ListItem(label=loc(30042), label2=loc(30024))
            liz.setArt({'icon': IconDefault})
            liz.setProperty('utime', '')
            liz.setProperty('date', '')
            _tlist.append(liz)

            _idx = OSD.select(loc(30015), _tlist, useDetails=True)
            if _idx > -1:
                date = _tlist[_idx].getProperty('date')
                clearTimer(date=None if date == '' else date)
        else:
            notifyLog('No active timers yet', xbmc.LOGERROR)
            OSD.ok(loc(30000), loc(30030))
    except Exception as e:
        notifyLog('Script error: %s' % e, xbmc.LOGERROR)

