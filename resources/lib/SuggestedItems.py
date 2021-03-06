#################################################################################################
# Suggested Updater
#################################################################################################

import xbmc
import xbmcgui
import xbmcaddon

import json
import threading
from datetime import datetime
import urllib
from DownloadUtils import DownloadUtils
from Database import Database

_MODE_BASICPLAY=12
_MODE_ITEM_DETAILS=17

#define our global download utils
downloadUtils = DownloadUtils()
db = Database()

class SuggestedUpdaterThread(threading.Thread):

    logLevel = 0
    event = None
    exit = False    
    
    def __init__(self, *args):
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        level = addonSettings.getSetting('logLevel')        
        self.logLevel = 0
        if(level != None):
            self.logLevel = int(level)           
    
        xbmc.log("XBMB3C SuggestedUpdaterThread -> Log Level:" +  str(self.logLevel))
        
        self.event =  threading.Event()
        
        threading.Thread.__init__(self, *args)    
    
    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            try:
                xbmc.log("XBMB3C SuggestedUpdaterThread -> " + str(msg))
            except UnicodeEncodeError:
                try:
                    xbmc.log("XBMB3C SuggestedUpdaterThread -> " + str(msg.encode('utf-8')))
                except: pass
            
    def stop(self):
        self.logMsg("stop called")
        self.exit = True
        self.event.set()
        
    def run(self):
        self.logMsg("Started")
        
        self.updateSuggested()
        lastRun = datetime.today()
        
        while (xbmc.abortRequested == False and self.exit != True):
            td = datetime.today() - lastRun
            secTotal = td.seconds
            
            if(secTotal > 60 and not xbmc.Player().isPlaying()):
                self.updateSuggested()
                lastRun = datetime.today()

            self.logMsg("entering event wait")
            self.event.wait(30.0)
            self.logMsg("event wait finished")
                        
        self.logMsg("Exited")
        
    def updateSuggested(self):
        self.logMsg("updateSuggested Called")
        useBackgroundData = xbmcgui.Window(10000).getProperty("BackgroundDataLoaded") == "true"
        
        addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        mb3Host = addonSettings.getSetting('ipaddress')
        mb3Port = addonSettings.getSetting('port')    
        userName = addonSettings.getSetting('username')     
        
        userid = downloadUtils.getUserId()
        self.logMsg("updateSuggested UserID : " + userid)
        
        self.logMsg("Updating Suggested List")
        
        suggestedUrl = "http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Movies/Recommendations?UserId=" + userid + "&categoryLimit=2&ItemLimit=20&Fields=Overview,ShortOverview,CriticRatingSummary&format=json" 
        jsonData = downloadUtils.downloadUrl(suggestedUrl, suppress=True, popup=1 )
        if(jsonData == ""):
            return
            
        allresult = json.loads(jsonData)
        self.logMsg("Suggested Movie Json Data : " + str(allresult), level=2)
        basemovie = "Missing Base Title"
        
        if(allresult == None or len(allresult) == 0):
            return
        
        if (allresult[0].get("BaselineItemName") != None):
            basemovie = allresult[0].get("BaselineItemName").encode('utf-8')
            
        result = allresult[0].get("Items")
        WINDOW = xbmcgui.Window( 10000 )
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            
            if item.get("Type") == "Movie":  
                title = "Missing Title"
                if(item.get("Name") != None):
                    title = item.get("Name").encode('utf-8')
                
                rating = item.get("CommunityRating")
                criticrating = item.get("CriticRating")
                officialrating = item.get("OfficialRating")
                criticratingsummary = ""
                if(item.get("CriticRatingSummary") != None):
                    criticratingsummary = item.get("CriticRatingSummary").encode('utf-8')
                plot = item.get("Overview")
                if plot == None:
                    plot=''
                plot=plot.encode('utf-8')
                shortplot = item.get("ShortOverview")
                if shortplot == None:
                    shortplot = ''
                shortplot = shortplot.encode('utf-8')
                year = item.get("ProductionYear")
                if(item.get("RunTimeTicks") != None):
                    runtime = str(int(item.get("RunTimeTicks"))/(10000000*60))
                else:
                    runtime = "0"
    
                item_id = item.get("Id") 
                if useBackgroundData != True:
                    poster = downloadUtils.getArtwork(item, "Primary3")
                    thumbnail = downloadUtils.getArtwork(item, "Primary")
                    logo = downloadUtils.getArtwork(item, "Logo")
                    fanart = downloadUtils.getArtwork(item, "Backdrop")
                    landscape = downloadUtils.getArtwork(item, "Thumb3")
                    discart = downloadUtils.getArtwork(item, "Disc")
                    medium_fanart = downloadUtils.getArtwork(item, "Backdrop3")
                    
                    if item.get("ImageTags").get("Thumb") != None:
                        realthumbnail = downloadUtils.getArtwork(item, "Thumb3")
                    else:
                        realthumbnail = medium_fanart
                else:
                    poster = db.get(item_id +".Primary3")
                    thumbnail = db.get(item_id +".Primary")
                    logo = db.get(item_id +".Logo")
                    fanart = db.get(item_id +".Backdrop")
                    landscape = db.get(item_id +".Thumb3")
                    discart = db.get(item_id +".Disc")
                    medium_fanart = db.get(item_id +".Backdrop3")
                    
                    if item.get("ImageTags").get("Thumb") != None:
                        realthumbnail = db.get(item_id +".Thumb3")
                    else:
                        realthumbnail = medium_fanart  
                    
                url =  mb3Host + ":" + mb3Port + ',;' + item_id
                # play or show info
                selectAction = addonSettings.getSetting('selectAction')
                if(selectAction == "1"):
                    playUrl = "plugin://plugin.video.xbmb3c/?id=" + item_id + '&mode=' + str(_MODE_ITEM_DETAILS)
                else:
                    playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
                          
                playUrl = playUrl.replace("\\\\","smb://")
                playUrl = playUrl.replace("\\","/")    
    
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Title = " + title, level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Thumb = " + realthumbnail, level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Path  = " + playUrl, level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Rating  = " + str(rating), level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".CriticRating  = " + str(criticrating), level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".CriticRatingSummary  = " + criticratingsummary, level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Plot  = " + plot, level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Year  = " + str(year), level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".Runtime  = " + str(runtime), level=2)
                self.logMsg("SuggestedMovieMB3." + str(item_count) + ".SuggestedMovieTitle  = " + basemovie, level=2)
                
                
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Title", title)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Thumb", realthumbnail)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Path", playUrl)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(fanart)", fanart)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(landscape)", landscape)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(medium_fanart)", medium_fanart)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(clearlogo)", logo)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Art(poster)", thumbnail)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Rating", str(rating))
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Mpaa", str(officialrating))
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".CriticRating", str(criticrating))
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".CriticRatingSummary", criticratingsummary)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Plot", plot)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".ShortPlot", shortplot)
                
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Year", str(year))
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".Runtime", str(runtime))
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".SuggestedMovieTitle", basemovie)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".ItemGUID", item_id)
                WINDOW.setProperty("SuggestedMovieMB3." + str(item_count) + ".id", item_id)
                
                WINDOW.setProperty("SuggestedMovieMB3.Enabled", "true")
                
                item_count = item_count + 1
                
        if (allresult[1].get("BaselineItemName") != None):
            basemovie = allresult[1].get("BaselineItemName").encode('utf-8')
            
        result = allresult[1].get("Items")
        if(result == None):
            result = []   

        item_count = 1
        for item in result:
            
            if item.get("Type") == "Movie":  
                title = "Missing Title"
                if(item.get("Name") != None):
                    title = item.get("Name").encode('utf-8')
                
                rating = item.get("CommunityRating")
                criticrating = item.get("CriticRating")
                officialrating = item.get("OfficialRating")
                criticratingsummary = ""
                if(item.get("CriticRatingSummary") != None):
                    criticratingsummary = item.get("CriticRatingSummary").encode('utf-8')
                plot = item.get("Overview")
                if plot == None:
                    plot=''
                plot=plot.encode('utf-8')
                shortplot = item.get("ShortOverview")
                if shortplot == None:
                    shortplot = ''
                shortplot = shortplot.encode('utf-8')
                year = item.get("ProductionYear")
                if(item.get("RunTimeTicks") != None):
                    runtime = str(int(item.get("RunTimeTicks"))/(10000000*60))
                else:
                    runtime = "0"
    
                item_id = item.get("Id")  
                if useBackgroundData != True:
                    poster = downloadUtils.getArtwork(item, "Primary3")
                    thumbnail = downloadUtils.getArtwork(item, "Primary")
                    logo = downloadUtils.getArtwork(item, "Logo")
                    fanart = downloadUtils.getArtwork(item, "Backdrop")
                    landscape = downloadUtils.getArtwork(item, "Thumb3")
                    discart = downloadUtils.getArtwork(item, "Disc")
                    medium_fanart = downloadUtils.getArtwork(item, "Backdrop3")
                    
                    if item.get("ImageTags").get("Thumb") != None:
                        realthumbnail = downloadUtils.getArtwork(item, "Thumb3")
                    else:
                        realthumbnail = medium_fanart
                else:
                    poster = db.get(item_id +".Primary3")
                    thumbnail = db.get(item_id +".Primary")
                    logo = db.get(item_id +".Logo")
                    fanart = db.get(item_id +".Backdrop")
                    landscape = db.get(item_id +".Thumb3")
                    discart = db.get(item_id +".Disc")
                    medium_fanart = db.get(item_id +".Backdrop3")
                    
                    if item.get("ImageTags").get("Thumb") != None:
                        realthumbnail = db.get(item_id +".Thumb3")
                    else:
                        realthumbnail = medium_fanart 
                
                url =  mb3Host + ":" + mb3Port + ',;' + item_id
                # play or show info
                selectAction = addonSettings.getSetting('selectAction')
                if(selectAction == "1"):
                    playUrl = "plugin://plugin.video.xbmb3c/?id=" + item_id + '&mode=' + str(_MODE_ITEM_DETAILS)
                else:
                    playUrl = "plugin://plugin.video.xbmb3c/?url=" + url + '&mode=' + str(_MODE_BASICPLAY)
                          
                playUrl = playUrl.replace("\\\\","smb://")
                playUrl = playUrl.replace("\\","/")    
    
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Title = " + title, level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Thumb = " + realthumbnail, level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Path  = " + playUrl, level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Art(fanart)  = " + fanart, level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Art(clearlogo)  = " + logo, level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Art(poster)  = " + thumbnail, level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Rating  = " + str(rating), level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".CriticRating  = " + str(criticrating), level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".CriticRatingSummary  = " + criticratingsummary, level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Plot  = " + plot, level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Year  = " + str(year), level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".Runtime  = " + str(runtime), level=2)
                self.logMsg("SuggestedMovie2MB3." + str(item_count) + ".SuggestedMovieTitle  = " + basemovie, level=2)
                
                
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Title", title)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Thumb", realthumbnail)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Path", playUrl)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Art(fanart)", fanart)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Art(landscape)", landscape)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Art(medium_fanart)", medium_fanart)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Art(clearlogo)", logo)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Art(poster)", thumbnail)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Rating", str(rating))
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Mpaa", str(officialrating))
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".CriticRating", str(criticrating))
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".CriticRatingSummary", criticratingsummary)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Plot", plot)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".ShortPlot", shortplot)
                
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Year", str(year))
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".Runtime", str(runtime))
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".SuggestedMovieTitle", basemovie)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".ItemGUID", item_id)
                WINDOW.setProperty("SuggestedMovie2MB3." + str(item_count) + ".id", item_id)
                
                
                WINDOW.setProperty("SuggestedMovie2MB3.Enabled", "true")
                
                item_count = item_count + 1
            
            
