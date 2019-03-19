import util
import time
import api
import json
import random
import os
import sys
import re
import traceback
import audio

try:
    import urlaudiostream_pymusic as urlaudiostream
except:
    pass

ORDER_LISTCYCLE = 0
ORDER_SINGLECYCLE = 1
ORDER_SHUFFLE = 2

QUALITIES_HIGHTOLOW = [3, 2, 1]

STATE_NOTLOADED = 0
STATE_NOTPLAYING = 1
STATE_BUFFERING = 4         # 下载中/缓冲中
STATE_PLAYING = 2
STATE_PAUSING = 3

USING_AUDIOPLAYER = 0
USING_URLAUDIOSTREAMPLAYER = 1

RE_LRC_USEFUL = re.compile(r'\[\D[^\]]*\][\n]*(\[\d.*)',re.DOTALL)
RE_LRC_LRCLINE_ALLTIMES = re.compile(r"\[(\d+:\d+(?:\.\d+)?)\]")
RE_LRC_LRCLINE_CONTENT = re.compile(r"\[\d+:\d+(?:\.\d+)?\](?!\[\d+:\d+(?:\.\d+)?\])(.*)")

STR_UTF8_BOM = "\xEF\xBB\xBF"

UASSTATE_STOP = 0
UASSTATE_CONNECTING = 1
UASSTATE_CONNECTED = 2
UASSTATE_READINGINFO = 3
UASSTATE_PLAYING = 4

UASERROR_NOERROR = 0
UASERROR_UNSUPPORTED = 1
UASERROR_READERROR = 2
UASERROR_END = 3

DEVICE_MAX_VOLUME = 100

tryWrapper = lambda x:lambda :None

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
            "useUrlAudioStreamPlayer": True,
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

        self.state = STATE_NOTPLAYING
        self.using = USING_AUDIOPLAYER

        self.changed = []

    def addSubscriber(self, func):
        self.changed.append(func)

    def update(self):
        for func in self.changed:
            func()

    def _updateConfig(self, config):
        self.config.update(config)
        self.logger = self.config['logger']

    def updatePlaylist(self, songList, urlList, append = False):
        '''
        如果 urlList 不全为 None (说明已经为 songList 批量获取过地址)
        则不会再次获取每首歌的 URL.

        获取 URL 后 URL 仍为 None 的歌曲, 会从播放列表中删除(版权曲)
        '''

        # TODO: 获取到待播放歌曲后立即获取 url 的做法容易导致播放到后面的歌曲时 url 失效，需要引入 url 定期刷新机制或改成每次播放前获取 url 来解决这个问题

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

        currentState = self.state

        if currentState == STATE_NOTLOADED:
            return 
        elif currentState == STATE_NOTPLAYING:
            pass
        elif currentState == STATE_PLAYING:
            self._stop()
        elif currentState == STATE_PAUSING:
            self._stop()
        else:
            self.state = STATE_NOTPLAYING
            raise ValueError, unicode("PlayerManager state not good")

        song = self.songList[self.orderList[self.seq]]
        api = self.config['apis'][song.apiClassString]
        songPathFormat = api.paths['songPathById']
        songPathFormat_link = api.paths['songPathById_link']

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

        def playAudioAfterDownloadWrapped():
            if self.isPlayAfterDownloadCancelled(playAudioAfterDownloadWrapped):
                return
            os.rename(songPath + ".download", songPath)
            self._play_audio(songPath)

        if songPath == None:
            if self.config['useUrlAudioStreamPlayer']:
                self._play_urlAudioStream()
            else:
                songPath = songPathFormat % (song.id(), self.config['defaultDownloadQuality'])
                monitor = self.config.get("monitor")
                if monitor:
                    import taskQueue
                    self.latestPlayAfterDownload = playAudioAfterDownloadWrapped
                    downloadTask = taskQueue.Task(
                        unicode("下载 %s") % song.name(),
                        util.rawHTTP_thread,
                        ("", self.urlList[self.orderList[self.seq]].replace("https://", "http://"), False, 'GET', {}, "", {}, self.config["logger"], songPath + ".download"),
                        {},
                        None,
                        None,
                        tryWrapper(playAudioAfterDownloadWrapped)
                    )
                    monitor.newTask(downloadTask)

                self.state = STATE_BUFFERING
                self.update()
        else:
            self._play_audio(songPath)

    def _urlAudioStream_callback(self, uasState, uasError, uasInfo):
        currentState = self.state
        currentUsing = self.using
        if currentUsing == USING_AUDIOPLAYER:
            # 这种情况一般都是 urlaudiostream 模块延迟反应，实际程序已经在使用 audio 播放歌曲了
            self.logger.warning(u"Not using urlaudiostream, received callback %s %s %s" % (uasState, uasError, uasInfo))
        elif currentUsing == USING_URLAUDIOSTREAMPLAYER:
            pass
        else:
            self.state = USING_URLAUDIOSTREAMPLAYER
            raise ValueError, unicode("PlayerManager using not good")

        if currentState == STATE_NOTLOADED:
            self.state = STATE_NOTPLAYING
            raise ValueError, unicode("PlayerManager state inappropriate (NOT_LOADED)")
        elif currentState == STATE_NOTPLAYING:
            if uasState == UASSTATE_STOP:
                self._urlAudioStream_stopTiming()
                pass
            elif uasState == UASSTATE_CONNECTING:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                pass
            elif uasState == UASSTATE_CONNECTED:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                pass
            elif uasState == UASSTATE_READINGINFO:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                pass
            elif uasState == UASSTATE_PLAYING:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_PLAYING
                self._urlAudioStream_playTiming()
            else:
                # Incorrect value
                pass
        elif currentState == STATE_PAUSING:
            self.logger.warning(u"PlayerManager state inappropriate (STATE_PAUSING when USING_UAS)")
            if uasState == UASSTATE_STOP:
                self._urlAudioStream_stopTiming()
                pass
            elif uasState == UASSTATE_CONNECTING:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                pass
            elif uasState == UASSTATE_CONNECTED:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                pass
            elif uasState == UASSTATE_READINGINFO:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                pass
            elif uasState == UASSTATE_PLAYING:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_PLAYING
                self._urlAudioStream_playTiming()
            else:
                # Incorrect value
                pass
        elif currentState == STATE_BUFFERING:
            if uasState == UASSTATE_STOP:
                self._urlAudioStream_stopTiming()
                self.state = STATE_NOTPLAYING
                pass
            elif uasState == UASSTATE_CONNECTING:
                self.using = USING_URLAUDIOSTREAMPLAYER
                pass
            elif uasState == UASSTATE_CONNECTED:
                self.using = USING_URLAUDIOSTREAMPLAYER
                pass
            elif uasState == UASSTATE_READINGINFO:
                self.using = USING_URLAUDIOSTREAMPLAYER
                pass
            elif uasState == UASSTATE_PLAYING:
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_PLAYING
                self._urlAudioStream_playTiming()
            else:
                # Incorrect value
                pass
        elif currentState == STATE_PLAYING:
            if uasState == UASSTATE_STOP:
                self._urlAudioStream_stopTiming()
                self.state = STATE_NOTPLAYING
                if uasError == UASERROR_END:
                    self._next()
                pass
            elif uasState == UASSTATE_CONNECTING:
                self.logger.warning(u"PlayerManager state inappropriate (CONNECTING when PLAYING)")
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                self._urlAudioStream_stopTiming()
                pass
            elif uasState == UASSTATE_CONNECTED:
                self.logger.warning(u"PlayerManager state inappropriate (CONNECTED when PLAYING)")
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                self._urlAudioStream_stopTiming()
                pass
            elif uasState == UASSTATE_READINGINFO:
                self.logger.warning(u"PlayerManager state inappropriate (READINGINFO when PLAYING)")
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_BUFFERING
                self._urlAudioStream_stopTiming()
                pass
            elif uasState == UASSTATE_PLAYING:
                self.logger.warning(u"PlayerManager state inappropriate (PLAYING when PLAYING)")
                self.using = USING_URLAUDIOSTREAMPLAYER
                self.state = STATE_PLAYING
                self._urlAudioStream_playTiming()
            else:
                # Incorrect value
                pass
        self.update()

        if uasError != UASERROR_NOERROR and uasError != UASERROR_END:
            raise Exception, u"UrlAudioStream Error: %s" % [u"", u"Unsupported format", u"Read error", u""][uasError]

    def _audio_callback(self, aPrevState, aCurrState, aErrCode):
        currentState = self.state
        currentUsing = self.using
        if currentUsing == USING_URLAUDIOSTREAMPLAYER:
            self.state = USING_AUDIOPLAYER
            self.logger.warning(u"Not using audio, received callback %s %s %s" % (aPrevState, aCurrState, aErrCode))
        elif currentUsing == USING_AUDIOPLAYER:
            pass
        elif currentUsing == USING_AUDIOPLAYER:
            self.state = USING_URLAUDIOSTREAMPLAYER
            raise ValueError, unicode("PlayerManager using not good")

        if currentState == STATE_NOTLOADED:
            self.state = STATE_NOTPLAYING
            raise ValueError, unicode("PlayerManager state inappropriate (NOT_LOADED)")
        elif currentState == STATE_NOTPLAYING:
            if aCurrState == audio.ENotReady or aCurrState == audio.EOpen:
                # Strange
                self.state = STATE_NOTPLAYING
                pass
            elif aCurrState == audio.EPlaying:
                self.state = STATE_PLAYING
                pass
            else:
                # Incorrect value
                pass
        elif currentState == STATE_PAUSING:
            if aCurrState == audio.ENotReady or aCurrState == audio.EOpen:
                # Strange
                self.state = STATE_NOTPLAYING
                pass
            elif aCurrState == audio.EPlaying:
                self.state = STATE_PLAYING
                pass
            else:
                # Incorrect value
                pass
        elif currentState == STATE_BUFFERING:
            # Strange
            if aCurrState == audio.ENotReady or aCurrState == audio.EOpen:
                # Strange
                self.state = STATE_NOTPLAYING
                pass
            elif aCurrState == audio.EPlaying:
                self.state = STATE_PLAYING
                pass
            else:
                # Incorrect value
                pass
        elif currentState == STATE_PLAYING:
            if aCurrState == audio.ENotReady or aCurrState == audio.EOpen:
                if aPrevState != audio.EPlaying:
                    self.logger.warning(u"aPrevState is not audio.EPlaying")
                self.state = STATE_NOTPLAYING
                self._next()
                pass
            elif aCurrState == audio.EPlaying:
                pass
            else:
                # Incorrect value
                pass
        self.update()
        
    def _play_urlAudioStream(self):
        if self.uasPlayer is None:
            self.uasPlayer = urlaudiostream.New(tryWrapper(self._urlAudioStream_callback))

        self.using = USING_URLAUDIOSTREAMPLAYER
        self.uasPlayer.play(unicode(self.urlList[self.orderList[self.seq]]))
        self.update()

    def _play_audio(self, songPath):
        try:
            if self.audioPlayer is not None:
                self.audioPlayer.close()
                self.audioPlayer = None

            self.audioPlayer = audio.Sound.open(songPath)
            self.audioPlayer.set_volume(self.config['volume'] * self.audioPlayer.max_volume() / 100)
            self.audioPlayer.player(callback = tryWrapper(self._audio_callback))
        except Exception, e:
            if self.audioPlayer is not None:
                self.audioPlayer.close()

            try:
                if os.path.exists(songPath):
                    os.remove(songPath)
            except Exception, ee:
                self.logger.error(ee.args)

            raise e.__class__, e



        