import xbmc
import xbmcgui
import json
import time
import datetime

EPOCH = datetime.datetime(1970, 1, 1)
JSON_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
UTC_OFFSET = int(round((datetime.datetime.now() - datetime.datetime.utcnow()).seconds, -1))

def date2timeStamp(date, dFormat=None, utc=False):
    # Kodi bug: returns '%H%H' or '%I%I'

    if dFormat is None:
        # use Kodi's own dateformat provided by setup
        df = xbmc.getRegion('dateshort') + ' ' + xbmc.getRegion('time').replace('%H%H', '%H').replace('%I%I','%I').replace(':%S', '')
    else:
        df = dFormat
    dtt = time.strptime(date, df)
    if not utc: return int(time.mktime(dtt))
    return int(time.mktime(dtt)) + UTC_OFFSET


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
    BUTTON_RECORD = 1152
    BUTTON_SWITCH = 1153
    BUTTON_CANCEL = 1154

    ACTION_SELECT = 7
    ACTION_NAV_BACK = 92

    def __init__(self, *args, **kwargs):

        self.timer = int(kwargs.get('timer', 5))
        self.text = kwargs.get('message', '')
        self.icon = kwargs.get('icon', '')
        self.recEnabled = kwargs.get('recEnabled', True)

        self.isCanceled = False
        self.requestSwitch = False
        self.initRecording = False

    def onInit(self):
        self.textControl = self.getControl(self.TEXT)  # Notification text field
        self.progressControl = self.getControl(self.PROGRESS)  # Notification progress bar
        self.imageControl = self.getControl(self.THUMB)  # Notification channel thumb
        self.buttonControl_1 = self.getControl(self.BUTTON_RECORD)  # Button 1 (Record)
        self.buttonControl_2 = self.getControl(self.BUTTON_SWITCH)  # Button 2 (Switch)
        self.buttonControl_3 = self.getControl(self.BUTTON_CANCEL)  # Button 3 (Cancel)

        self.textControl.setText(self.text)
        self.imageControl.setImage(self.icon)
        self.buttonControl_1.setEnabled(self.recEnabled)

        for t in range(100, -1, -1):
            self.progressControl.setPercent(t)
            xbmc.sleep(self.timer * 10)
            if self.isCanceled or self.requestSwitch or self.initRecording: break
        self.close()

    def onClick(self, controlId):
        if controlId == self.BUTTON_RECORD: self.initRecording = True
        elif controlId == self.BUTTON_SWITCH: self.requestSwitch = True
        elif controlId == self.BUTTON_CANCEL: self.isCanceled = True
        self.close()

    def onAction(self, action):
        if action == self.ACTION_NAV_BACK: self.close()

    def set_text(self, p):
        self.textControl.setText(p)

    def close(self):
        xbmcgui.WindowXMLDialog.close(self)


class cPvrProperties(object):

    class PvrAddTimerException(Exception):
        pass

    class JsonExecException(Exception):
        pass

    def __init__(self, *args, **kwargs):
        pass

    def jsonrpc(self, query):
        querystring = {"jsonrpc": "2.0", "id": 1}
        querystring.update(query)
        try:
            response = json.loads(xbmc.executeJSONRPC(json.dumps(querystring, encoding='utf-8')))
            if 'result' in response: return response['result']
        except TypeError as e:
            raise self.JsonExecException('Error executing JSON RPC: %s' % e)
        return None

    def getRecordingCapabilities(self, pvrid, timestamp):
        """
        :param pvrid:       str PVR-ID of the broadcast station
        :param timestamp:   int UNIX timestamp
        :return:            dict: int unique broadcastID of the broadcast or None, bool hastimer
        """
        params = {'broadcastid': None, 'hastimer': False}
        query = {
            "method": "PVR.GetBroadcasts",
            "params": {"channelid": pvrid,
                       "properties": ["title", "starttime", "hastimer"]}
        }
        res = self.jsonrpc(query)
        try:
            for broadcast in res.get('broadcasts'):
                if timestamp == date2timeStamp(broadcast['starttime'], dFormat=JSON_TIME_FORMAT, utc=True):
                    params.update({'broadcastid': broadcast['broadcastid'], 'hastimer': broadcast['hastimer']})
                    return params
            raise self.PvrAddTimerException('No broadcast found for pvr ID %s@%s' % (pvrid, timestamp))
        except (TypeError, AttributeError) as e:
            raise self.PvrAddTimerException('Error on determining broadcast for pvr ID %s: %s' % (pvrid, e))

    def setTimer(self, broadcastId):
        """
        :param broadcastId: int unique broadcastID of the broadcast
        :return:            none
        """
        query = {
            "method": "PVR.AddTimer",
            "params": {"broadcastid": broadcastId}
        }
        res = self.jsonrpc(query)
        if res == 'OK': return
        else:
            raise self.PvrAddTimerException('Timer for broadcast %s couldn\'t added' % broadcastId)
