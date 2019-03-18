import util
import time
import api
import json
import random
import os
import sys
import re
import traceback

try:
    import urlaudiostream_pymusic as urlaudiostream
except:
    pass

ORDER_LISTCYCLE = 0
ORDER_SINGLECYCLE = 1
ORDER_SHUFFLE = 2

QUALITIES_HIGHTOLOW = [3, 2, 1]

STATE_MASK = 3
STATE_NOT_LOADED = 0
STATE_NOT_PLAYING = 1
STATE_PLAYING = 2
STATE_PAUSING = 3

USING_MASK = 1 << 2
USING_AUDIOPLAYER = 0 << 2
USING_URLSTREAMPLAYER = 1 << 2

RE_LRC_USEFUL = re.compile(r'\[\D[^\]]*\][\n]*(\[\d.*)',re.DOTALL)
RE_LRC_LRCLINE_ALLTIMES = re.compile(r"\[(\d+:\d+(?:\.\d+)?)\]")
RE_LRC_LRCLINE_CONTENT = re.compile(r"\[\d+:\d+(?:\.\d+)?\](?!\[\d+:\d+(?:\.\d+)?\])(.*)")

STR_UTF8_BOM = "\xEF\xBB\xBF"

def formatLyrics(lyrics):
    if lyrics.noLyrics():
        return api.TextLyrics(unicode("没有歌词"))

    if lyrics.lyrics() is None:
        return []

    useful = RE_LRC_USEFUL.findall(u"[mark]" + lyrics.lyrics())

    if useful == []:
        return []

    lines = useful[0].split(u"\n")

    formattedLyricsList = []

    for line in lines:
        times = RE_LRC_LRCLINE_ALLTIMES.findall(line)
        content = RE_LRC_LRCLINE_CONTENT.findall(line)

        if times == [] or content == []:
            continue

        for t in times:
            t1 = t.split(u":")
            t2 = t1[1].split(u".")

            minute = int("0" + t1[0])
            sec = int("0" + t2[0])

            if (len(t2) > 1):
                msec = t2[1]
                if len(msec) == 2:
                    msec = int("0" + msec) * 10
                else:
                    msec = int("0" + msec)
            else:
                msec = 0

            timeInMsec = minute * 60000 + sec * 1000 + msec
            formattedLyricsList.append( (timeInMsec, [content, u""]) )

    if len(formattedLyricsList) and lyrics.translatedLyrics():
        useful_t = RE_LRC_USEFUL.findall(u"[mark]" + lyrics.translatedLyrics())
        if len(useful_t):
            formattedLyricsDict = dict(formattedLyricsList)

            lines_t = useful_t[0].split(u"\n")

            for line in lines_t:
                times = RE_LRC_LRCLINE_ALLTIMES.findall(line)
                content = RE_LRC_LRCLINE_CONTENT.findall(line)

                if times == [] or content == []:
                    continue

                for t in times:
                    t1 = t.split(u":")
                    t2 = t1[1].split(u".")

                    minute = int("0" + t1[0])
                    sec = int("0" + t2[0])

                    if (len(t2) > 1):
                        msec = t2[1]
                        if len(msec) == 2:
                            msec = int("0" + msec) * 10
                        else:
                            msec = int("0" + msec)
                    else:
                        msec = 0

                    timeInMsec = minute * 60000 + sec * 1000 + msec

                    if timeInMsec in formattedLyricsDict:
                        formattedLyricsDict[timeInMsec][1] = content

    if len(formattedLyricsList) == 0:
        return api.TextLyrics(lyrics.lyrics())
    else:
        return formattedLyricsList


class PlayerManager(object):
    def __init__(self, initConfig = {}):
        name = self.__class__.__name__
        self.config = {
            "name": name,
            "order": ORDER_LISTCYCLE,
            "defaultDownloadQuality": 2,
            "volume": 40,  # 统一 100 为满
            "apis": {

            },
            "monitor": None,
            "useUrlStreamPlayer": True,
        }
        '''
        "apis": {
            "NEApi": neapi,
            "XMApi": xmapi,
        }
        '''

        self.config['logger'] = util.Logger(self.config['name'] + "_%s" % time.localtime().__hash__().__hex__())
        self.config['logger'].setHandlers([])
    
        if initConfig:
            self._updateConfig(initConfig)

        self.isCurrentFM = False
        self.currentFMApi = None

        self.songList = []
        self.urlList = []
        self.lyricsList = []
        self.orderList = []
        
        self.prevLyricsI = 0

        self.latestPlayAfterDownload = None

        self.audioPlayer = None
        self.uasPlayer = None

    def _updateConfig(self, config):
        self.config.update(config)
        self.logger = self.config['logger']

    def updatePlaylist(self, songList, urlList, append = False):
        '''
        如果 urlList 不全为 None (说明已经为 songList 批量获取过地址)
        则不会再次获取每首歌的 URL.

        获取 URL 后 URL 仍为 None 的歌曲, 会从播放列表中删除(版权曲)
        '''
        if urlList:
            assert(len(songList) == len(urlList))

            noUrl = True
            for url in urlList:
                if url is not None:
                    noUrl = False
                    break
        else:
            noUrl = True

        if noUrl:
            urlList = [None] * len(songList)
            
            originalIndex = {}
            songIdListByApi = {}
            songListByApi = {}
            for apiName in self.config['apis']:
                originalIndex[apiName] = []
                songIdListByApi[apiName] = []
                songListByApi[apiName] = []

            i = 0
            for song in songList:
                thisSongApiName = song.apiClassString()
                originalIndex[thisSongApiName].append(i)
                songIdListByApi[thisSongApiName].append(song.id())
                songListByApi[thisSongApiName].append(song)
                i += 1

            for apiName in self.config['apis']:
                thisApiSongUrls = self.config['apis'][apiName].getSongUrls(songIdListByApi[apiName], self.config["defaultDownloadQuality"], songListByApi[apiName])

                i = 0
                for songUrl in thisApiSongUrls:
                    urlList[originalIndex[apiName][i]] = songUrl
                    i += 1

        finalApiSongList = []
        finalUrlList = []

        i = 0
        for url in urlList:
            if url is not None:
                finalApiSongList.append(songList[i])
                finalUrlList.append(urlList[i])
            i += 1

        if append:
            self.songList += finalApiSongList
            self.urlList += finalUrlList
            self.lyricsList += [None] * len(finalApiSongList)
        else:
            self.songList = finalApiSongList
            self.urlList = finalUrlList
            self.lyricsList = [None] * len(finalApiSongList)
            self.orderList = range(len(finalApiSongList))

        self.startFetchLyric()

    def initOrder(self):
        self.orderList = []
        self.seq = -1

    def startFetchLyric(self):
        monitor = self.config.get("monitor")
        if monitor:
            import taskQueue
            lyricsTask = taskQueue.Task(
                unicode("获取歌词"),
                self.fetchLyric_thread,
                (),
                {},
                None,
                None,
                None
            )
            monitor.newTask(lyricsTask)
        
    def fetchLyric_thread(self, **kwargs):
        try:
            l = len(self.songList)

            progress = 0
            maxProgress = l * 100
            i = 0

            def updateProgress(p, mp):
                progress = i * 100 + p * 100 / mp
                kwargs['progressCallback'](progress, maxProgress)

            def syncRawHTTP(host, url, https = True, method = 'GET', params = {}, query = "", header = {}, logger = None, writeIO = None, **kwargs):
                kwargs['progressCallback'] = updateProgress
                return util.rawHTTP(host, url, https, method, params, query, header, logger, writeIO, **kwargs)

            # i = 0
            for song in self.songList:
                if self.lyricsList[i]:
                    continue
                a = self.config['apis'][song.apiClassString()]
                lyricsPath = a.paths['lyricsById'] % song.id()

                if os.path.exists(lyricsPath):
                    f = open(lyricsPath, "r")
                    lyrics = api.getApiObjectFromJSON(f.read())
                    assert(isinstance(lyrics, api.ApiLyrics))
                    f.close()
                else:
                    lyrics = a.getLyrics(song.id(), rawHTTP = syncRawHTTP)
                    f = open(lyricsPath, "w")
                    f.write(lyrics.toJSON())
                    f.close()

                formattedLyrics = formatLyrics(lyrics)
                self.lyricsList[i] = formattedLyrics

                i += 1
                progress = i * 100
                kwargs['progressCallback'](progress, maxProgress)

        except Exception, e:
            kwargs['errorCallback'](e, {'errText': ''.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))})

        kwargs['finishCallback']({'formattedLyrics': formattedLyrics})
        

    def onDemand(self, index):
        if index < 0 or index >= len(self.songList):
            raise ValueError, unicode("index out of range")

        if self.seq + 1 < len(self.orderList) or self.orderList[self.seq + 1] != index:
            self.orderList[self.seq + 1:self.seq + 1] = [index]

        self._next()

    def _next(self, manual = False):
        # 播放次序加一
        if self.isCurrentFM:
            self.seq += 1
        elif self.config['order'] == ORDER_LISTCYCLE:
            self.seq += 1
        elif self.config['order'] == ORDER_SINGLECYCLE:
            if manual:
                self.seq += 1
            else:
                pass
        elif self.config['order'] == ORDER_SHUFFLE:
            self.seq += 1
        else:
            raise Exception, unicode("内部错误，请重新启动应用程序。")

        # 若播放次序超过了播放次序映射表
        if self.seq >= len(self.orderList):
            if self.isCurrentFM:
                apiList = self.currentFMApi.getFMPlaylist()
                beforeLen = len(self.songList)
                self.updatePlaylist(apiList, None, True)
                afterLen = len(self.songList)
                appendList = range(beforeLen, afterLen)
                if beforeLen == afterLen:
                    # No new FM songs anymore
                    return
            elif self.config['order'] == ORDER_LISTCYCLE:
                appendList = range(len(self.songList))
            elif self.config['order'] == ORDER_SINGLECYCLE:
                appendList = range(len(self.songList))
            elif self.config['order'] == ORDER_SHUFFLE:
                appendList = range(len(self.songList))
                random.shuffle(appendList)
                
            if appendList[0] == self.orderList[-1]:
                tmp = appendList[1]
                appendList[1] = appendList[0]
                appendList[0] = tmp
            self.orderList += appendList

        self._play()

    def previous(self):
        if self.config['order'] == ORDER_LISTCYCLE or self.config['order'] == ORDER_SINGLECYCLE:
            self.seq = self.seq - 1
            if self.seq < 0:
                self.seq = len(self.orderList) - 1
        elif self.config['order'] == ORDER_SHUFFLE:
            self.seq = self.seq - 1
            if self.seq < 0:
                self.seq = 0
        
        self._play()
                
    def getCurrentLyrics(self):
        currentLyrics = self.lyricsList[self.seq]
        if isinstance(currentLyrics, api.TextLyrics):
            return currentLyrics, 0

        currentMsec = self.getCurrentMsec()

        if self.prevLyricsI < 0 or self.prevLyricsI >= len(currentLyrics):
            self.prevLyricsI = 0
        
        currentI = -1

        for i in range(self.prevLyricsI, len(currentLyrics)):
            if currentMsec >= currentLyrics[i][0]:
                currentI = i

        if currentI == -1:
            for i in range(0, self.prevLyricsI):
                if currentMsec >= currentLyrics[i][0]:
                    currentI = i
        
        self.prevLyricsI = currentI

        return currentLyrics, currentI

    def isPlayAfterDownloadCancelled(self, func):
        return self.latestPlayAfterDownload is not func

    def _play(self):
        # 播放当前应该播放的歌曲

        currentState = self.state() & STATE_MASK

        if currentState == STATE_NOT_LOADED:
            return 
        elif currentState == STATE_NOT_PLAYING:
            pass
        elif currentState == STATE_PLAYING:
            self._stop()
        elif currentState == STATE_PAUSING:
            self._stop()
        else:
            raise ValueError

        song = self.songList[self.orderList[self.seq]]
        api = self.config['apis'][song.apiClassString]
        songPathFormat = a.paths['songPathById']
        songPathFormat_link = a.paths['songPathById_link']

        songPath = None

        for quality in QUALITIES_HIGHTOLOW:
            songPath = songPathFormat % (song.id(), quality)
            songPath_link = songPathFormat_link % (song.id(), quality)
            
            if os.path.exists(songPath):
                if os.path.isfile(songPath):
                    break
                os.rmdir(songPath)
                songPath = None

            if os.path.exists(songPath_link):
                if os.path.isfile(songPath_link):
                    try:
                        f = open(songPath_link, "rb")
                        songPath = f.read()
                        if os.path.isfile(songPath):
                            break
                    except:
                        pass
                    os.remove(songPath_link)
                    songPath = None
                else:
                    os.rmdir(songPath_link)
                    songPath = None

        def playAudioWrapped():
            if self.isPlayAfterDownloadCancelled(playAudioWrapped):
                return
            self._play_audio(songPath)

        if songPath == None:
            if self.config['useUrlStreamPlayer']:
                self._play_urlstream()
            else:
                songPath = songPathFormat % (song.id(), self.config['defaultDownloadQuality'])
                monitor = self.config.get("monitor")
                if monitor:
                    import taskQueue
                    self.latestPlayAfterDownload = playAudioWrapped
                    downloadTask = taskQueue.Task(
                        unicode("下载 %s") % song.name(),
                        util.rawHTTP_thread,
                        ("", self.urlList[self.orderList[self.seq]].replace("https://", "http://"), False, 'GET', {}, "", {}, self.config["logger"], songPath),
                        {},
                        None,
                        None,
                        playAudioWrapped
                    )
                    monitor.newTask(downloadTask)
        else:
            playAudioWrapped()

    def _play_urlstream(self):
        if self.uasPlayer is None:
            self.uasPlayer = urlaudiostream.New()