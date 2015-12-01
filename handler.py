import sys
import time
import datetime
import xbmc, xbmcaddon, xbmcgui

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

def notifyLog(message, level=xbmc.LOGNOTICE):
    xbmc.log('[%s] %s' % (__addonid__, message.encode('utf-8')), level)

def setSwitchTimer(channel, date):
    for _timer in ['t0_', 't1_', 't2_', 't3_', 't4_', 't5_', 't6_', 't7_', 't8_', 't9_']:
        try:
            dtime = datetime.datetime.strptime(date, '%d.%m.%Y %H:%M')
        except TypeError:
            dtime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, '%d.%m.%Y %H:%M')))
        except Exception:
            notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
            return False

        itime = int(time.mktime(itime.timetuple()))
        if __addon__.getSetting(_timer + 'active') == 'true':
            if str(itime) == __addon__.getSetting(_timer['date']):
                notifyLog('timer already set')
                return False
            continue
        if int(time.time()) > itime:
            notifyLog('timer date resides in the past')
            return False

        __addon__.setSetting(_timer + 'channel', channel)
        __addon__.setSetting(_timer + 'date', str())
        __addon__.setSetting(_timer + 'active', 'true')
        notifyLog('timer added @%s, ch:%s' % (date, channel.decode('utf-8')))
        return True
    notifyLog('timer limit exceeded, no free slot', xbmc.LOGERROR)
    return False

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
                notifyLog('timer could or would not be set', xbmc.LOGERROR)
        elif args['action'] == 'del':
            pass
except IndexError:
        notifyLog('Calling this script without parameters are not allowed', xbmc.LOGERROR)
#except Exception, e:
#     notifyLog('An Error has occured')