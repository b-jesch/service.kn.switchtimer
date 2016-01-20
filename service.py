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

INTERVAL = 10
OSD = xbmcgui.Dialog()

def notifyLog(message, level=xbmc.LOGNOTICE):
    xbmc.log('[%s] %s' % (__addonid__, message.encode('utf-8')), level)

def notifyOSD(header, message, icon=__IconDefault__, time=5000):
    OSD.notification(header.encode('utf-8'), message.encode('utf-8'), icon, time)

def jsonrpc(query):
    return json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))

def date2timeStamp(date, format):
    try:
        dtime = datetime.datetime.strptime(date, format)
    except TypeError:
        try:
            dtime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, format)))
        except ValueError:
            notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
            notifyOSD(__LS__(30000), __LS__(30020), icon=__IconAlert__)
            return False
    except Exception:
        notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
        notifyOSD(__LS__(30000), __LS__(30020), icon=__IconAlert__)
        return False
    return int(time.mktime(dtime.timetuple()))

class XBMCMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.SettingsChanged = False

    def onSettingsChanged(self):
        self.SettingsChanged = True

class Service(XBMCMonitor):

    def __init__(self, *args):
        XBMCMonitor.__init__(self)
        self.__dateFormat = None
        self.activeTimers = 0
        self.getSettings()
        notifyLog('Init Service %s %s' % (__addonname__, __version__))

    def getSettings(self):
        self.__showNoticeBeforeSw = True if __addon__.getSetting('showNoticeBeforeSw').upper() == 'TRUE' else False
        self.__dispMsgTime = int(re.match('\d+', __addon__.getSetting('dispTime')).group())*1000
        self.__discardTmr = int(re.match('\d+', __addon__.getSetting('discardOldTmr')).group())*60
        self.__confirmTmrAdded = True if __addon__.getSetting('confirmTmrAdded').upper() == 'TRUE' else False
        
        df = xbmc.getRegion('dateshort')
        tf = xbmc.getRegion('time').split(':')
        
        self.__dateFormat = df + ' ' + tf[0][0:2] + ':' + tf[1]
                
        notifyLog('settings (re)loaded')
        self.SettingsChanged = False

    def getSwitchTimer(self):
        timers = []
        for _prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
            if xbmc.getInfoLabel('Skin.String(%s)' % (_prefix + 'date')) == '' or None: continue
            timers.append({'channel': xbmc.getInfoLabel('Skin.String(%s)' % (_prefix + 'channel')), 'date': xbmc.getInfoLabel('Skin.String(%s)' % (_prefix + 'date'))})

        if self.activeTimers != len(timers):
            __addon__.setSetting('cntTmr', str(len(timers)))
            self.activeTimers = len(timers)
            xbmc.executebuiltin('Skin.SetString(SwitchTimerActiveItems,%s)' % (str(len(timers))))
            notifyLog('timer (re)loaded, currently %s active timer' % (len(timers)))
        return timers

    def resetSwitchTimer(self, channel, date):
        for _prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
            if xbmc.getInfoLabel('Skin.String(%s)' % (_prefix + 'date')) == '': continue
            elif xbmc.getInfoLabel('Skin.String(%s)' % (_prefix + 'date')) == date and xbmc.getInfoLabel('Skin.String(%s)' % (_prefix + 'channel')) == channel:

                # Reset the skin strings

                xbmc.executebuiltin('Skin.Reset(%s)' % (_prefix + 'channel'))
                xbmc.executebuiltin('Skin.Reset(%s)' % (_prefix + 'date'))
                xbmc.executebuiltin('Skin.Reset(%s)' % (_prefix + 'title'))
                xbmc.executebuiltin('Skin.Reset(%s)' % (_prefix + 'icon'))

    def channelName2channelId(self, channelname):
        query = {
                "jsonrpc": "2.0",
                "method": "PVR.GetChannels",
                "params": {"channelgroupid": "alltv"},
                "id": 1
                }
        res = jsonrpc(query)
        if 'result' in res and 'channels' in res['result']:
            res = res['result'].get('channels')
            for channels in res:
                if channels['label'] == channelname: return channels['channelid']
        return False

    def getPlayer(self):
        props = {'player': None, 'playerid': None, 'media': None, 'id': None}
        query = {
                "jsonrpc": "2.0",
                "method": "Player.GetActivePlayers",
                "id": 1
                }
        res = jsonrpc(query)
        if 'result' in res and res['result']:
            res = res['result'][0]
            props['player'] = res['type']
            props['playerid'] = res['playerid']

            query = {
                    "jsonrpc": "2.0",
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

    def poll(self):

        while not XBMCMonitor.abortRequested(self):
            if XBMCMonitor.waitForAbort(self, INTERVAL): break
            if self.SettingsChanged: self.getSettings()
            _now = time.time()
            timers = self.getSwitchTimer()
            for _timer in timers:
                timestamp = date2timeStamp(_timer['date'], self.__dateFormat)

                if not timestamp:
                    notifyLog('couldn\'t calculate timestamp, delete timer', xbmc.LOGERROR)
                    self.resetSwitchTimer(_timer['channel'], _timer['date'])
                    break

                # delete old/discarded timers
                if timestamp + self.__discardTmr < _now:
                    self.resetSwitchTimer(_timer['channel'], _timer['date'])
                    continue

                _timediff = INTERVAL
                if timestamp - _now < _timediff:
                    chanIdTmr = self.channelName2channelId(_timer['channel'].decode('utf-8'))
                    if chanIdTmr:

                        # switch to channel, delete timer
                        plrProps = self.getPlayer()
                        if plrProps['player'] == 'audio' or (plrProps['player'] == 'video' and plrProps['media'] != 'channel'):
                            # stop the media player
                            notifyLog('player:%s media:%s @id:%s is running' % (plrProps['player'], plrProps['media'], plrProps['playerid']))
                            query = {
                                    "jsonrpc": "2.0",
                                    "method": "Player.Stop",
                                    "params": {"playerid": plrProps['playerid']},
                                    "id": 1
                                    }
                            res = jsonrpc(query)
                            if 'result' in res and res['result'] == "OK":
                                notifyLog('player stopped')

                        # is the current playing channel different from the one we will switch to?

                        if chanIdTmr != plrProps['id']:
                            notifyLog('currently playing channelid %s, switch to id %s' % (plrProps['id'], chanIdTmr))
                            notifyOSD(__LS__(30000), __LS__(30026) % (_timer['channel'].decode('utf-8')), time=self.__dispMsgTime)
                            query = {
                                    "jsonrpc": "2.0",
                                    "id": 1,
                                    "method": "Player.Open",
                                    "params": {"item": {"channelid": chanIdTmr}}
                                    }
                            res = jsonrpc(query)
                            if 'result' in res and res['result'] == 'OK':
                                notifyLog('switched to channel \'%s\'' % (_timer['channel'].decode('utf-8')))
                            else:
                                notifyLog('could not switch to channel \'%s\'' % (_timer['channel'].decode('utf-8')))
                                notifyOSD(__LS__(30000), __LS__(30025) % (_timer['channel'].decode('utf-8')), icon=__IconAlert__)
                        else:
                            notifyLog('channel switching not required')
                            notifyOSD(__LS__(30000), __LS__(30027) % (_timer['channel'].decode('utf-8')), time=self.__dispMsgTime)

                        self.resetSwitchTimer(_timer['channel'], _timer['date'])
                        notifyLog('timer @%s deactivated' % (_timer['date']))

        notifyLog('Service kicks off')

service = Service()
service.poll()
del service
