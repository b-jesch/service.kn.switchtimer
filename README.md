<h1>PVR switch timer aka PVR reminder</h1>
No more forgotten football matches or formula one races! Avoid discussion with your better half and let kodi switch to the channels you want! Or let they switch to their favorite shows at a given time!

This service adds items to the context menu of the pvr osd guide window (PVROSDGuide) automatically (add switchtimer, delete all switchtimer). Currently the skins Aeon Flex, Destiny and a Confluence Mod from Kodinerds fully supports this service with additional windows but other skins can this service implement too. Hints for integration see below here. If you aren't a skinner or don't need special windows for editing/deleting switchtimers just ignore the skinners section and install this service as usual. All can be done with the context menu of pvr osd guide.

Also if you call the switchtimer from the addon list directly, you get a list of active timers where you can delete timers from this point.

Skinners only:

If you want or need to call this service inside of another window different from PVROSDGuide, use:

    <label>$ADDON[service.kn.switchtimer 30040]</label>
    <visible>System.HasAddon(service.kn.switchtimer) + Window.IsVisible(tvguide)</visible>
    <onclick>RunScript(service.kn.switchtimer,action=add,channel=channelname,icon=icon,date=datestring,title=title,plot=plot)</onclick>

You have to provide the needed parameters, comparsion is done via valid Datetime. Format of Datetime must be the same as used in Kodi settings, e.g. '11.12.2013 14:15':

    channelname (e.g. $INFO[ListItem.Channelname])
    icon (e.g. $INFO[ListItem.Icon])
    datestring (e.g. $INFO[ListItem.Date])
    title (e.g. $INFO[ListItem.Title])
    plot (e.g. $INFO[ListItem.Plot])

If you want buttons for deleting one or all timers just use:

    <onclick>RunScript(service.kn.switchtimer,action=del,timer=tx)</onclick>

where tx is a timer from t0 to t9, or delete all timers with

    <label>$ADDON[service.kn.switchtimer 30041]</label>
    <onclick>RunScript(service.kn.switchtimer,action=delall)</onclick>

All timers are available as a JSON property file within the userdata folder of the addon. There is a window property too:
 
    $INFO[Window(Home).Property(SwitchTimerActiveItems)]  # No. of active timers

KN Switchtimer provides an own messaging window. If you want to adapt this to your skin, this window (WindowXMLDialog) musst named to the following scheme and resides within the skins/Default/1080i/ folder of this addon:

    <skin-id>.st_notification.xml
    
Look into the folder skins/Default/1080i for exapmles. If the skin file doesn't exist a standard countdown dialog will be used instead.