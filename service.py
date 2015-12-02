import time
import datetime
import xbmc, xbmcaddon, xbmcgui
import json
import os
import re

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

__IconDefault__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'default.png'))
__IconAlert__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'alert.png'))
__IconOk__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'ok.png'))

INTERVAL = 15

OSD = xbmcgui.Dialog()

def notifyLog(message, level=xbmc.LOGNOTICE):
    xbmc.log('[%s] %s' % (__addonid__, message.encode('utf-8')), level)

class XBMCMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.SettingsChanged = False

    def onSettingsChanged(self):
        self.SettingsChanged = True

class Service(XBMCMonitor):

    def __init__(self, *args):
        XBMCMonitor.__init__(self)
        self.getSettings()
        notifyLog('Init Service %s %s' % (__addonname__, __version__))
        
    def notifyOSD(self, header, message, icon=__IconDefault__, dur=5000):
        OSD.notification(header.encode('utf-8'), message.encode('utf-8'), icon, dur)

    def getSettings(self):
        self.__showNoticeBeforeSw = True if __addon__.getSetting('showNoticeBeforeSw').upper() == 'TRUE' else False
        self.__dispMsgTime = int(re.match('\d+', __addon__.getSetting('dispTime')).group())
        self.__discardTmr = int(re.match('\d+', __addon__.getSetting('discardOldTmr')).group())*60
        self.__confirmTmrAdded = True if __addon__.getSetting('confirmTmrAdded').upper() == 'TRUE' else False

    def getSwitchTimer(self):
        timers = []
        for _prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
            if __addon__.getSetting(_prefix + 'date') == '' or None: continue
            timers.append({'channel': __addon__.getSetting(_prefix + 'channel'), 'date': int(__addon__.getSetting(_prefix + 'date'))})
        self.SettingsChanged = False
        notifyLog('timer (re)loaded, currently %s active timer' % (len(timers)))
        return timers

    def resetSwitchTimer(self, channel, date):
        for _prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
            if __addon__.getSetting(_prefix + 'date') == '': continue
            elif __addon__.getSetting(_prefix + 'channel') == channel and int(__addon__.getSetting(_prefix + 'date')) == date:
                __addon__.setSetting(_prefix + 'channel', '')
                __addon__.setSetting(_prefix + 'date', '')

    def channelName2channelId(self, channelname):
        res = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "PVR.GetChannels", "params": {"channelgroupid": "alltv"}, "id": "1"}')
        res = json.loads(unicode(res, 'utf-8', errors='ignore'))
        if 'result' in res and res['result'] is not None:
            for channeldict in res['result']['channels']:
                if channeldict['label'] == channelname: return str(channeldict['channelid'])
            return False

    def poll(self):

        timers = self.getSwitchTimer()

        while not XBMCMonitor.abortRequested(self):
            if XBMCMonitor.waitForAbort(self, INTERVAL): break
            if self.SettingsChanged: timers = self.getSwitchTimer()
            _now = time.time()
            for _timer in timers:
                # delete discarded times
                if int(_timer['date']) + self.__discardTmr < _now:
                    self.resetSwitchTimer(_timer['channel'], _timer['date'])
                    continue
                _timediff = INTERVAL
                if self.__showNoticeBeforeSw: _timediff += self.__dispMsgTime
                if int(_timer['date']) - _now < _timediff:
                    # switch to channel, delete timer

                    channelid = self.channelName2channelId(_timer['channel'].decode('utf-8'))
                    if channelid:
                        self.notifyOSD(__LS__(30000), __LS__(30026) % (_timer['channel'].decode('utf-8')), dur=self.__dispMsgTime * 1000)
                        xbmc.sleep(self.__dispMsgTime * 1000)
                        res = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id":"1", "method": "Player.Open","params":{"item":{"channelid":%s}}}' % channelid)
                        res = json.loads(unicode(res, 'utf-8', errors='ignore'))
                        if 'result' in res and res['result'] == 'OK':
                            notifyLog('switched to channel %s' % (_timer['channel'].decode('utf-8')))
                            self.resetSwitchTimer(_timer['channel'], _timer['date'])
                            notifyLog('timer @%s deactivated' % (datetime.datetime.fromtimestamp(int(_timer['date'])).strftime('%d.%m.%Y %H:%M')))
                    else:
                        notifyLog('could not switch to channel %s' % (_timer['channel'].decode('utf-8')))
                        self.notifyOSD(__LS__(30000), __LS__(30025) % (_timer['channel'].decode('utf-8')),icon=__IconAlert__)

        notifyLog('Service kicks off')

service = Service()
service.poll()
del service
