import time
import datetime
import xbmc, xbmcaddon, xbmcgui
import json

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

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
        notifyLog('Init Service %s %s' % (__addonname__, __version__))

    def getSettings(self):
        timers = []
        for _timer in ['t0_', 't1_', 't2_', 't3_', 't4_', 't5_', 't6_', 't7_', 't8_', 't9_']:
            if __addon__.getSetting(_timer + 'active') == 'false':
                continue
            timers.append({'channel': __addon__.getSetting(_timer + 'channel'), 'date': __addon__.getSetting(_timer + 'date')})
        self.SettingsChanged = False
        notifyLog('switchtimer (re)loaded, currently %s active timer' % (len(timers)))
        return timers

    def resetSwitchTimer(self, channel, date):
        for _timer in ['t0_', 't1_', 't2_', 't3_', 't4_', 't5_', 't6_', 't7_', 't8_', 't9_']:
            if __addon__.getSetting(_timer + 'active') == 'false':
                continue
            elif __addon__.getSetting(_timer + 'channel') == channel and __addon__.getSetting(_timer + 'date') == date:
                __addon__.setSetting(_timer + 'channel', '')
                __addon__.setSetting(_timer + 'date', '')
                __addon__.setSetting(_timer + 'active', 'false')

    def channelName2channelId(self, channelname):
        res = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "PVR.GetChannels", "params": {"channelgroupid": "alltv"}, "id": "1"}')
        res = json.loads(unicode(res, 'utf-8', errors='ignore'))
        if 'result' in res and res['result'] is not None:
            for channeldict in res['result']['channels']:
                if channeldict['label'] == channelname: return str(channeldict['channelid'])
            return False

    def poll(self):

        timers = self.getSettings()
        while not XBMCMonitor.abortRequested(self):
            if XBMCMonitor.waitForAbort(self, 15):
                break
            if self.SettingsChanged:
                timers = self.getSettings()
            _now = time.time()
            for _timer in timers:
                if int(_timer['date']) - _now < 15:

                    # switch to channel, delete timer

                    channelid = self.channelName2channelId(_timer['channel'].decode('utf-8'))
                    if channelid:
                        res = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id":"1", "method": "Player.Open","params":{"item":{"channelid":%s}}}' % channelid)
                        res = json.loads(unicode(res, 'utf-8', errors='ignore'))
                        if 'result' in res and res['result'] == 'OK':
                            notifyLog('switched to channel %s' % (_timer['channel'].decode('utf-8')))
                            self.resetSwitchTimer(_timer['channel'], _timer['date'])
                            notifyLog('timer @%s deactivated' % (datetime.datetime.fromtimestamp(int(_timer['date'])).strftime('%d.%m.%Y %H:%M')))
                    else:
                        notifyLog('could not switch to channel %s' % (_timer['channel'].decode('utf-8')))

        notifyLog('Service kicks off')

service = Service()
service.poll()
del service
