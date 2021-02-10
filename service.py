#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import json
import os
import re

import handler
import resources.lib.knClasses as knClasses

addon = xbmcaddon.Addon()
addonid = addon.getAddonInfo('id')
addonname = addon.getAddonInfo('name')
path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
version = addon.getAddonInfo('version')
loc = addon.getLocalizedString

IconDefault = os.path.join(path, 'resources', 'media', 'default.png')
IconAlert = os.path.join(path, 'resources', 'media', 'alert.png')
IconOk = os.path.join(path, 'resources', 'media', 'ok.png')

INTERVAL = 10  # More than that will make switching too fuzzy because service isn't synchronized with real time
HOME = xbmcgui.Window(10000)


def jsonrpc(query):
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    return json.loads(xbmc.executeJSONRPC(json.dumps(querystring)))


class Service(knClasses.XBMCMonitor):

    def __init__(self, *args):

        knClasses.XBMCMonitor.__init__(self)
        self.skinPath = None

        self.getSettings()
        handler.notifyLog('Init Service %s %s' % (addonname, version))
        self.bootstrap = True
        self.timers = handler.getTimer()

    def getSettings(self):

        # There seems to be a bug in kodi as sometimes changed properties wasn't read/update properly even if
        # monitor signaled a change.
        # Reading of settings is now outsourced to handler as a workaround.

        self.__showNoticeBeforeSw = True if handler.getSetting('showNoticeBeforeSw').upper() == 'TRUE' else False
        self.__useCountdownTimer = True if handler.getSetting('useCountdownTimer').upper() == 'TRUE' else False
        self.__leadOffset = int(re.match('\d+', handler.getSetting('leadOffset')).group())
        self.__dispMsgTime = int(re.match('\d+', handler.getSetting('dispTime')).group())*1000
        self.__discardTmr = int(re.match('\d+', handler.getSetting('discardOldTmr')).group())*60
        self.__confirmTmrAdded = True if handler.getSetting('confirmTmrAdded').upper() == 'TRUE' else False

        self.__switchOnInit = True if handler.getSetting('switchOnInit').upper() == 'TRUE' else False
        try:
            self.__channel = int(re.match('\d+', handler.getSetting('channel')).group())
        except AttributeError:
            self.__channel = 0

        self.SettingsChanged = False

    @classmethod
    def channelName2channelId(cls, channelname):
        query = {
                "method": "PVR.GetChannels",
                "params": {"channelgroupid": "alltv"},
                }
        res = jsonrpc(query)
        if 'result' in res and 'channels' in res['result']:
            res = res['result'].get('channels')
            for channels in res:
                if channels['label'] == channelname: return channels['channelid']
        return False

    @classmethod
    def getPlayer(cls):
        props = {'player': None, 'playerid': None, 'media': None, 'id': None}
        query = {
                "method": "Player.GetActivePlayers",
                }
        res = jsonrpc(query)
        if 'result' in res and res['result']:
            res = res['result'][0]
            props['player'] = res['type']
            props['playerid'] = res['playerid']

            query = {
                    "method": "Player.GetItem",
                    "params": {"properties": ["title", "season", "episode", "file"],
                               "playerid": props['playerid']},
                    "id": "VideoGetItem"
                    }
            res = jsonrpc(query)
            if 'result' in res:
                res = res['result'].get('item')
                props['media'] = res['type']
                if 'id' in res: props['id'] = res['id']
        return props

    @classmethod
    def switchToChannelId(cls, playerProperties, channelId, channel):

        if playerProperties['player'] == 'audio' or (playerProperties['player'] == 'video' and playerProperties['media'] != 'channel'):

            # stop all other players except pvr

            handler.notifyLog('player:%s media:%s @id:%s is running' %
                              (playerProperties['player'], playerProperties['media'], playerProperties['playerid']))
            query = {
                "method": "Player.Stop",
                "params": {"playerid": playerProperties['playerid']},
            }
            res = jsonrpc(query)
            if 'result' in res and res['result'] == "OK":
                handler.notifyLog('Player stopped')

        handler.notifyLog('Currently playing channelid %s, switch to id %s' % (playerProperties['id'], channelId))
        query = {
            "method": "Player.Open",
            "params": {"item": {"channelid": channelId}}
        }
        res = jsonrpc(query)
        if 'result' in res and res['result'] == 'OK':
            handler.notifyLog('Switched to channel \'%s\'' % (channel))
        else:
            handler.notifyLog('Couldn\'t switch to channel \'%s\'' % (channel))
            handler.notifyOSD(loc(30000), loc(30025) % (channel), icon=IconAlert)

    def poll(self):

        while not knClasses.XBMCMonitor.abortRequested(self):

            if knClasses.XBMCMonitor.waitForAbort(self, INTERVAL): break
            if self.SettingsChanged:
                self.getSettings()

            _now = time.time()
            _switchInstantly = False
            plrProps = self.getPlayer()

            for _timer in self.timers:

                if not _timer['utime']:
                    handler.notifyLog('Couldn\'t calculate timestamp, delete timer', xbmc.LOGERROR)
                    handler.putTimer(self.timers)
                    break

                # delete old/discarded timers
                if _timer['utime'] + self.__discardTmr < _now:
                    self.timers.remove(_timer)
                    handler.putTimer(self.timers)
                    continue

                if _timer['utime'] - self.__leadOffset < _now: _switchInstantly = True
                if (_timer['utime'] - _now < INTERVAL + self.__dispMsgTime / 1000 + self.__leadOffset) or _switchInstantly:
                    chanIdTmr = self.channelName2channelId(_timer['channel'])
                    if chanIdTmr:

                        # compare with player properties, switch if necessary

                        if chanIdTmr == plrProps['id']:
                            handler.notifyLog('Channel switching unnecessary')
                            handler.notifyOSD(loc(30000), loc(30027) % (_timer['title'], _timer['channel']),
                                              time=self.__dispMsgTime)
                        else:
                            switchAborted = False
                            secs = 0
                            handler.notifyLog('Channel switch to %s required' % (_timer['channel']))

                            if _switchInstantly:
                                handler.notifyLog('immediate channel switching required')
                                handler.notifyOSD(loc(30000), loc(30027) % (_timer['title'], _timer['channel']),
                                                  time=5000)
                            elif not self.__showNoticeBeforeSw: xbmc.sleep(self.__dispMsgTime)
                            elif self.__useCountdownTimer:

                                # check for skin XML
                                skin_id = xbmc.translatePath('special://skin').split(os.sep)[-2] + '.st_notification.xml'
                                if os.path.exists(os.path.join(path, 'resources', 'skins', 'Default', '1080i', skin_id)):

                                    pvr = knClasses.cPvrProperties()
                                    try:
                                        pvrprops = dict()
                                        recEnabled = True
                                        pvrprops.update(pvr.getRecordingCapabilities(
                                            self.channelName2channelId(_timer['channel']), _timer['utime']))
                                        if pvrprops['hastimer']: recEnabled = False
                                    except (pvr.PvrAddTimerException, pvr.JsonExecException) as e:
                                        handler.notifyLog(str(e), xbmc.LOGERROR)
                                        recEnabled = False

                                    Popup = knClasses.cNotification(skin_id, path,
                                                                    message=loc(30035) % (_timer['title'],
                                                                                          _timer['channel']),
                                                                    timer=self.__dispMsgTime/1000, icon=_timer['icon'],
                                                                    recEnabled=recEnabled)
                                    Popup.doModal()
                                    if Popup.isCanceled: switchAborted = True
                                    elif Popup.initRecording:
                                        try:
                                            pvr.setTimer(pvrprops['broadcastid'])
                                            handler.notifyLog('Recording schedule set for %s: %s' % (_timer['channel'],
                                                                                                     _timer['title']),
                                                              xbmc.LOGINFO)
                                            switchAborted = True
                                        except (pvr.PvrAddTimerException, pvr.JsonExecException) as e:
                                            handler.notifyOSD(loc(30000), loc(30036) % (_timer['title'],
                                                                                        _timer['channel']),
                                                              icon=IconAlert)
                                            handler.notifyLog(str(e), xbmc.LOGERROR)
                                    elif Popup.requestSwitch:
                                        handler.notifyLog('immediate channel switch initate by user')
                                    else:
                                        handler.notifyLog('Window countdown completed without user action')
                                else:
                                    handler.OSDProgress.create(loc(30028),
                                                               loc(30026) % (_timer['channel'],
                                                                             _timer['title'],
                                                                             self.__dispMsgTime // 1000 - secs))

                                    while secs < self.__dispMsgTime / 1000:
                                        percent = int((secs * 100000) / self.__dispMsgTime)
                                        handler.OSDProgress.update(percent,
                                                                   loc(30026) % (_timer['channel'],
                                                                                 _timer['title'],
                                                                                 self.__dispMsgTime // 1000 - secs))
                                        xbmc.sleep(1000)
                                        secs += 1
                                        if handler.OSDProgress.iscanceled():
                                            switchAborted = True
                                            break
                                    handler.OSDProgress.close()
                            else:
                                idleTime = xbmc.getGlobalIdleTime()
                                handler.notifyOSD(loc(30000), loc(30026) %
                                                  (_timer['channel'], _timer['title']), time=self.__dispMsgTime)
                                while secs < self.__dispMsgTime / 1000:
                                    if idleTime > xbmc.getGlobalIdleTime():
                                        switchAborted = True
                                        break

                                    xbmc.sleep(1000)
                                    idleTime += 1
                                    secs += 1
                                if switchAborted: handler.notifyOSD(loc(30000), loc(30032))

                            if switchAborted: handler.notifyLog('Channelswitch cancelled by user')
                            else:
                                self.bootstrap = False
                                self.switchToChannelId(plrProps, chanIdTmr, _timer['channel'])

                    handler.clearTimer(_timer['date'])

            if self.bootstrap and self.__switchOnInit and self.__channel > 0:
                handler.notifyLog('Channelswitch on startup enabled')
                query = {
                        "method": "PVR.GetChannels",
                        "params": {"channelgroupid": "alltv", "properties": ["channelnumber"]}
                        }
                res = jsonrpc(query)
                if 'result' in res:
                    for _channel in res['result']['channels']:
                        if _channel['channelnumber'] == self.__channel:
                            handler.notifyLog('Channelswitch on startup is enabled, switch to \'%s\'' % _channel['label'])
                            handler.notifyOSD(loc(30000), loc(30013) % (_channel['label']))
                            self.switchToChannelId(plrProps, _channel['channelid'], _channel['label'])
                            self.bootstrap = False
                            break

            self.timers = handler.getTimer()

        handler.notifyLog('Service kicks off')


service = Service()
service.poll()
del service
