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

def date2timeStamp(date, format=DATEFORMAT):
    try:
        dtime = datetime.datetime.strptime(date, DATEFORMAT)
    except TypeError:
        dtime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, DATEFORMAT)))
    except Exception:
        notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
        notifyOSD(__LS__(30000), __LS__(30020), icon=__IconAlert__)
        return False
    return int(time.mktime(dtime.timetuple()))

def setSwitchTimer(channel, date, title):
    itime = date2timeStamp(date)
    if not itime: return False

    for _prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
        if xbmc.getInfoLabel('Skin.String(%s)' % (_prefix + 'date')) != '':
            if date == xbmc.getInfoLabel('Skin.String(%s)' % (_prefix + 'date')):
                notifyLog('timer already set')
                notifyOSD(__LS__(30000), __LS__(30023), icon=__IconAlert__)
                return False
            continue
        if int(time.time()) > itime:
            notifyLog('timer date is in the past')
            notifyOSD(__LS__(30000), __LS__(30022), icon=__IconAlert__)
            return False

        # Set the Skin Strings

        xbmc.executebuiltin('Skin.SetString(%s,%s)' % (_prefix + 'channel', channel))
        xbmc.executebuiltin('Skin.SetString(%s,%s)' % (_prefix + 'date', date))
        xbmc.executebuiltin('Skin.SetString(%s,%s)' % (_prefix + 'title', title))

        notifyLog('timer %s added @%s, %s, %s' % (_prefix[:-1], date, channel.decode('utf-8'), title.decode('utf-8')))
        if __confirmTmrAdded__: notifyOSD(__LS__(30000), __LS__(30021), icon=__IconOk__)
        return True
    notifyLog('timer limit exceeded, no free slot', xbmc.LOGERROR)
    notifyOSD(__LS__(30000), __LS__(30024), icon=__IconAlert__)
    return False

def clearTimer(timer):

    # Reset the skin strings

    xbmc.executebuiltin('Skin.Reset(%s)' % (_prefix + 'channel'))
    xbmc.executebuiltin('Skin.Reset(%s)' % (_prefix + 'date'))
    xbmc.executebuiltin('Skin.Reset(%s)' % (_prefix + 'title'))

def clearTimerList():
    for _prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']: clearTimer(_prefix);
    __addon__.setSetting('cntTmr', '0')

notifyLog('parameter handler called')
try:
    if sys.argv[1]:
        args = {'action':None, 'channel':'', 'date':'', 'title':'', 'timer':''}
        pars = sys.argv[1:]
        for par in pars:
            item, value = par.split('=')
            args[item] = value
        if args['action'] == 'add':
            if not setSwitchTimer(args['channel'], args['date'], args['title']):
                notifyLog('timer couldn\'t or wouldn\'t set', xbmc.LOGERROR)
        elif args['action'] == 'del':
            clearTimer(args['timer'] + ':')
            notifyLog('timer %s deleted' % (args['timer']))
        elif args['action'] == 'delall':
            clearTimerList()
            notifyLog('all timer deleted')
except IndexError:
        notifyLog('Calling this script without parameters is not allowed', xbmc.LOGERROR)
except Exception, e:
        notifyLog('Script error, Operation couldn\'t performed', xbmc.LOGERROR)
