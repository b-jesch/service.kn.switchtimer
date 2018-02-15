#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import xbmc, xbmcaddon, xbmcgui
import json
import os
import re

import handler

addon = xbmcaddon.Addon()
addonid = addon.getAddonInfo('id')
addonname = addon.getAddonInfo('name')
path = xbmc.translatePath(addon.getAddonInfo('path'))
version = addon.getAddonInfo('version')
loc = addon.getLocalizedString

IconDefault = os.path.join(path, 'resources', 'media', 'default.png')
IconAlert = os.path.join(path, 'resources', 'media', 'alert.png')
IconOk = os.path.join(path, 'resources', 'media', 'ok.png')

INTERVAL = 10 # More than that will make switching too fuzzy because service isn't synchronized with real time
HOME = xbmcgui.Window(10000)

SKIN = xbmc.translatePath('special://skin').split(os.sep)[-2] + '.st_notification.xml'

def jsonrpc(query):
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    return json.loads(xbmc.executeJSONRPC(json.dumps(querystring, encoding='utf-8')))

class XBMCMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.SettingsChanged = False

    def onSettingsChanged(self):
        self.SettingsChanged = True


class cNotification(xbmcgui.WindowXMLDialog):

    TEXT = 1151
    PROGRESS = 1155
    THUMB = 1156
    BUTTON_LEFT = 1152
    BUTTON_RIGHT = 1153

    ACTION_SELECT = 7
    ACTION_NAV_BACK = 92


    def __init__(self, *args, **kwargs):

        self.timer = int(kwargs.get('timer', 5))
        self.text = kwargs.get('message', '')
        self.icon = kwargs.get('icon', '')

    def onInit(self):
        self.textControl = self.getControl(self.TEXT)  # Notification text field
        self.progressControl = self.getControl(self.PROGRESS)  # Notification progress bar
        self.imageControl = self.getControl(self.THUMB)  # Notification channel thumb
        self.buttonControl_1 = self.getControl(self.BUTTON_LEFT)  # Button 1 (switch)
        self.buttonControl_2 = self.getControl(self.BUTTON_RIGHT)  # Button 2 (close)

        self.isCanceled = False
        self.requestSwitch = False

        self.textControl.setText(self.text)
        self.imageControl.setImage(self.icon)

        for t in range(100, -1, -1):
            self.progressControl.setPercent(t)
            xbmc.sleep(self.timer * 10)

        self.close()

    def onClick(self, controlId):
        if controlId == self.BUTTON_LEFT:
            self.isCanceled = True
            self.close()
        elif controlId == self.BUTTON_RIGHT:
            self.requestSwitch = True
            self.close()

    def onAction(self, action):
        if action == self.ACTION_NAV_BACK: self.close()


    def set_text(self, p):
        self.textControl.setText(p)

    def close(self):
        xbmcgui.WindowXMLDialog.close(self)


class Service(XBMCMonitor):

    def __init__(self, *args):

        XBMCMonitor.__init__(self)
        self.skinPath = None

        self.getSettings()
        handler.notifyLog('Init Service %s %s' % (addonname, version))
        self.bootstrap = True
        self.timers = handler.getTimer()
        handler.setTimerProperties(self.timers)

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

    def resetTmr(cls, date):
        for prefix in ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']:
            if HOME.getProperty('%s:date' % (prefix)) == '': continue
            elif HOME.getProperty('%s:date' % (prefix)) == date: handler.clearTimerProperties(prefix)

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

        while not XBMCMonitor.abortRequested(self):

            if XBMCMonitor.waitForAbort(self, INTERVAL): break
            if self.SettingsChanged:
                self.getSettings()

            _now = time.time()
            _switchInstantly = False
            plrProps = self.getPlayer()

            for _timer in self.timers:

                if not _timer['utime']:
                    handler.notifyLog('Couldn\'t calculate timestamp, delete timer', xbmc.LOGERROR)
                    self.resetTmr(_timer['date'])
                    break

                # delete old/discarded timers
                if _timer['utime'] + self.__discardTmr < _now:
                    self.resetTmr(_timer['date'])
                    continue

                if _timer['utime'] - self.__leadOffset < _now: _switchInstantly = True
                if (_timer['utime'] - _now < INTERVAL + self.__dispMsgTime / 1000 + self.__leadOffset) or _switchInstantly:
                    chanIdTmr = self.channelName2channelId(_timer['channel'])
                    if chanIdTmr:

                        # compare with player properties, switch if necessary

                        if chanIdTmr == plrProps['id']:
                            handler.notifyLog('Channel switching unnecessary')
                            handler.notifyOSD(loc(30000), loc(30027) % (_timer['title'], _timer['channel']), time=self.__dispMsgTime)
                        else:
                            switchAborted = False
                            secs = 0
                            handler.notifyLog('Channel switch to %s required' % (_timer['channel']))

                            if _switchInstantly:
                                handler.notifyLog('immediate channel switching required')
                                handler.notifyOSD(loc(30000), loc(30027) % (_timer['title'], _timer['channel']), time=5000)

                            elif not self.__showNoticeBeforeSw: xbmc.sleep(self.__dispMsgTime)

                            elif self.__useCountdownTimer:
                                if os.path.exists(os.path.join(path, 'resources', 'skins', 'Default', '1080i', SKIN)):
                                    Popup = cNotification(SKIN, path, message=loc(30035) % (_timer['title'], _timer['channel']),
                                                          timer=self.__dispMsgTime/1000, icon=_timer['icon'])
                                    Popup.doModal()
                                    if Popup.isCanceled: switchAborted = True
                                else:
                                    handler.OSDProgress.create(loc(30028), loc(30026) %
                                                               (_timer['channel'], _timer['title']),
                                                               loc(30029) % (int(self.__dispMsgTime / 1000 - secs)))
                                    while secs < self.__dispMsgTime /1000:
                                        secs += 1
                                        percent = int((secs * 100000) / self.__dispMsgTime)
                                        handler.OSDProgress.update(percent, loc(30026) %
                                                                   (_timer['channel'], _timer['title']),
                                                                   loc(30029) % (int(self.__dispMsgTime / 1000 - secs)))
                                        xbmc.sleep(1000)
                                        if (handler.OSDProgress.iscanceled()):
                                            switchAborted = True
                                            break
                                    handler.OSDProgress.close()
                            else:
                                idleTime = xbmc.getGlobalIdleTime()
                                handler.notifyOSD(loc(30000), loc(30026) %
                                                  (_timer['channel'], _timer['title']), time=self.__dispMsgTime)
                                while secs < self.__dispMsgTime /1000:
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

                    self.resetTmr(_timer['date'])

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
                            handler.notifyLog('Channelswitch on startup is enabled, switch to \'%s\'' % (_channel['label']))
                            handler.notifyOSD(loc(30000), loc(30013) % (_channel['label']))
                            self.switchToChannelId(plrProps, _channel['channelid'], _channel['label'])
                            self.bootstrap = False
                            break

            self.timers = handler.getTimer()

        handler.notifyLog('Service kicks off')

service = Service()
service.poll()
del service
