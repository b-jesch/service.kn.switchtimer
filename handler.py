import sys
import time
import datetime
import xbmc, xbmcaddon, xbmcgui
import os

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

__IconDefault__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'default.png'))
__IconAlert__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'alert.png'))
__IconOk__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'ok.png'))

__confirmTmrAdded__ = True if __addon__.getSetting('confirmTmrAdded').upper() == 'TRUE' else False

OSD = xbmcgui.Dialog()
DATEFORMAT = '%d.%m.%Y %H:%M'

def notifyLog(message, level=xbmc.LOGNOTICE):
    xbmc.log('[%s] %s' % (__addonid__, message.encode('utf-8')), level)

def notifyOSD(header, message, icon=__IconDefault__):
    OSD.notification(header.encode('utf-8'), message.encode('utf-8'), icon)

def setSwitchTimer(channel, date):
    for _prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
        try:
            dtime = datetime.datetime.strptime(date, DATEFORMAT)
        except TypeError:
            dtime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, DATEFORMAT)))
        except Exception:
            notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
            notifyOSD(__LS__(30000), __LS__(30020), icon=__IconAlert__)
            return False

        itime = int(time.mktime(dtime.timetuple()))
        if __addon__.getSetting(_prefix + 'date') != '':
            if itime == int(__addon__.getSetting(_prefix + 'date')):
                notifyLog('timer already set')
                notifyOSD(__LS__(30000), __LS__(30023), icon=__IconAlert__)
                return False
            continue
        if int(time.time()) > itime:
            notifyLog('timer date is in the past')
            notifyOSD(__LS__(30000), __LS__(30022), icon=__IconAlert__)
            return False

        __addon__.setSetting(_prefix + 'channel', channel)
        __addon__.setSetting(_prefix + 'date', str(itime))
        notifyLog('timer added @%s, ch:%s' % (date, channel.decode('utf-8')))
        if __confirmTmrAdded__: notifyOSD(__LS__(30000), __LS__(30021), icon=__IconOk__)
        return True
    notifyLog('timer limit exceeded, no free slot', xbmc.LOGERROR)
    notifyOSD(__LS__(30000), __LS__(30024), icon=__IconAlert__)
    return False

def clearTimerList():
    for _prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
        __addon__.setSetting(_prefix + 'channel', '')
        __addon__.setSetting(_prefix + 'date', '')
    __addon__.setSetting('cntTmr', '0')

notifyLog('parameter handler called')
try:
    if sys.argv[1]:
        args = {'action':None, 'channel':None, 'date':None}
        pars = sys.argv[1:]
        for par in pars:
            item, value = par.split('=')
            args[item] = value
        if args['action'] == 'add':
            if not setSwitchTimer(args['channel'], args['date']):
                notifyLog('timer couldn\'t or wouldn\'t be set', xbmc.LOGERROR)
        elif args['action'] == 'del':
            pass
        elif args['action'] == 'delall':
            clearTimerList()
            notifyLog('all timer deleted')
except IndexError:
        notifyLog('Calling this script without parameters is not allowed', xbmc.LOGERROR)
