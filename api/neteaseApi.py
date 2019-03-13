import time
import md5
import api
import binascii, base64
import random
import util
import json
import re

try:
    from Crypto.Cipher import AES
except:
    import aes as AES

NE_BRS = [('b', 96000),('l', 128000),('m', 192000),('h', 320000)]
NE_HOST = "music.163.com"
NE_MAGIC_MP3DFS = '3go8&$8*3*3h0k(2)2'

NE_LONGAPI = ["/weapi/v2/discovery/recommend/songs", "/weapi/v1/radio/get", "/api/album", "/api/song/detail", "/weapi/song/detail" ]
NE_SHORTAPI = ["/weapi/v3/playlist/detail", "/weapi/v1/album"]

NE_JS2JSON = re.compile(r"([\,\{])\s*([\w]+):([^,]+)")
NE_USERINFO = re.compile(r"GUser\s*=\s*([^;]+);")

def dfsId2Mp3Url(dfsId, serverNo = None):
    encryptedDfsId = ''
    magicLen = len(NE_MAGIC_MP3DFS)
    i = 0
    dfsId = str(dfsId)
    for x in dfsId:
        encryptedDfsId += chr(ord(x) ^ ord(NE_MAGIC_MP3DFS[i % magicLen]))
        i += 1
    md5Encoder = md5.new()
    md5Encoder.update(encryptedDfsId)
    encryptedDfsId = md5Encoder.hexdigest()

    encryptedDfsId = encryptedDfsId.encode('base64')[:-1]
    encryptedDfsId = encryptedDfsId.replace('/', '_')
    encryptedDfsId = encryptedDfsId.replace('+', '-')

    if serverNo == None:
        serverNo = random.randint(1,4)
    return "http://p%s.music.126.net/%s/%s.mp3" % (serverNo, encryptedDfsId, dfsId)

def aesEncrypt(text, secKey):
    pad = 16 - len(text) % 16
    text = text + pad * chr(pad)
    encryptor = AES.new(secKey, 2, '0102030405060708')
    ciphertext = encryptor.encrypt(text)
    ciphertext = base64.encodestring(ciphertext).replace('\n','')
    return ciphertext.decode()

def modpow(base, exponent, mod):
    ans = 1
    index = 0
    while(1 << index <= exponent):
        if(exponent & (1 << index)):
            ans = (ans * base) % mod
        index += 1
        base = (base * base) % mod
    return ans

def rsaEncrypt(text, pubKey, modulus):
    textRvs=""
    for x in text:
        textRvs = x + textRvs
    text = textRvs.encode()
    rs = modpow(long(binascii.hexlify(text), 16), long(pubKey, 16), long(modulus, 16))
    return ('%x' % rs).zfill(256)

def neEncrypt(params):
    text = json.dumps(params)
    secKey = ''.join(['%x' % random.randint(0, 15) for x in range(16)])
    encText = aesEncrypt(aesEncrypt(text, '0CoJUm6Qyw8W8jud'), secKey)
    encSecKey = rsaEncrypt(secKey, '010001', '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7')
    return {'params': encText, 'encSecKey': encSecKey}

class NEApiBlockedByYundun(api.ApiLoginError):
    def __init__(self, *args):
        api.ApiError.__init__(self, *args)

class NEApiNeedCaptcha(api.ApiLoginError):
    def __init__(self, *args):
        api.ApiError.__init__(self, *args)

class NEApiWrongPassword(api.ApiLoginError):
    def __init__(self, *args):
        api.ApiError.__init__(self, *args)

class NEApiNotLoggedInError(api.ApiNotLoggedinError):
    def __init__(self, *args):
        api.ApiError.__init__(self, *args)


class NEApiPlaylist(api.ApiPlaylist):
    def __init__(self, data, via):
        super(NEApiPlaylist, self).__init__(data, via)

    def creator(self):
        return api.getApiObject(NEApiUser, self.data.get('creator'), self.via)

    def createTime(self):
        t = self.data.get("createTime")
        if t is None:
            return None
        return time.localtime(t / 1000.)

    def description(self):
        return self.data.get("description")

    def length(self):
        t = self.data.get("tracks")
        if t is None:
            return None
        return len(t)

    def coverImgUrl(self):
        return self.data.get('coverImgUrl')

    def commentsId(self):
        return self.data.get('commentThreadId')

    def id(self):
        i = self.data.get('id')
        if i is None:
            return None
        return str(i)

    def songs(self):
        return api.getApiObject(api.ApiList, self.data.get("tracks"), self.via, NEApiSong)

    def copywriting(self):
        return self.data.get("copywriter")

class NEApiSong(api.ApiSong):
    def __init__(self, data, via):
        super(NEApiSong, self).__init__(data, via)

    def name(self):
        return self.data.get('name')

    def id(self):
        i = self.data.get('id')
        if i is None:
            return None
        return str(i)

    def duration(self):
        if self.via in NE_LONGAPI:
            return self.data.get("duration")
        elif self.via in NE_SHORTAPI:
            return self.data.get("dt")
        else:
            return None

    def album(self):
        if self.via in NE_LONGAPI:
            return api.getApiObject(NEApiAlbum, self.data.get("album"), self.via)
        elif self.via in NE_SHORTAPI:
            return api.getApiObject(NEApiAlbum, self.data.get("al"), self.via)
        else:
            return None

    def artists(self):
        if self.via in NE_LONGAPI:
            return api.getApiObject(api.ApiList, self.data.get("artists"), self.via, NEApiArtist)
        elif self.via in NE_SHORTAPI:
            return api.getApiObject(api.ApiList, self.data.get("ar"), self.via, NEApiArtist)
        else:
            return None

    def trackNo(self):
        return self.data.get("no")

    def alias(self):
        a = self.data.get('alias')
        if a is None:
            return []
        else:
            return a

    def dfsId(self):
        if self.via in NE_LONGAPI:
            return map(lambda x: (self.data.get(x) or {}).get('dfsId'), ["bMusic","lMusic", "mMusic", "hMusic"])
        elif self.via in NE_SHORTAPI:
            return map(lambda x: (self.data.get(x) or {}).get('fid'), ["b","l", "m", "h"])
        else:
            return None

    def reason(self):
        return self.data.get("reason")
        

class NEApiAlbum(api.ApiAlbum):
    def __init__(self, data, via):
        super(NEApiAlbum, self).__init__(data, via)

    def name(self):
        return self.data.get("name")

    def id(self):
        i = self.data.get("id")
        if i is None:
            return None
        return str(i)

    def artists(self):
        a = self.data.get('artists')
        if a is None:
            a = []
        return api.getApiObject(api.ApiList, a, self.via, NEApiArtist)
        

    def coverImgUrl(self):
        return self.data.get('picUrl')

    def songs(self):
        return api.getApiObject(api.ApiList, self.data.get('songs'), self.via, NEApiSong)

class NEApiArtist(api.ApiArtist):
    def __init__(self, data, via):
        super(NEApiArtist, self).__init__(data, via)

    def name(self):
        return self.data.get('name')

    def id(self):
        i = self.data.get('id')
        if i is None:
            return None
        return str(i)

class NEApiLyrics(api.ApiLyrics):
    def __init__(self, data, via):
        super(NEApiLyrics, self).__init__(data, via)

    def lyrics(self):
        return self.data.get("lrc",{}).get("lyric")

    def translatedLyrics(self):
        return self.data.get("tlyric",{}).get("lyric")

    def noLyrics(self):
        return self.data.get("nolyric")

class NEApiComment(api.ApiComment):
    def __init__(self, data, via):
        super(NEApiComment, self).__init__(data, via)

    def user(self):
        return self.data.get('user')

    def id(self):
        i = self.data.get('commentId')
        if i is None:
            return None
        return str(i)

    def time(self):
        t = self.data.get('time')
        if t is None:
            return None
        else:
            return time.localtime(t/1000)

    def content(self):
        c = self.data.get('content', "")
        if self.data.has_key('beReplied'):
            c += '\n回复 ' + self.data['beReplied'].get('user', {}).get('name', '') + "："
            c += '\n' + self.data['beReplied'].get('content', '')
        return c

class NEApiUser(api.ApiUser):
    def __init__(self, data, via):
        super(NEApiUser, self).__init__(data, via)

    def nickname(self):
        return self.data.get('nickname')

    def id(self):
        i = self.data.get('userId')
        if i is None:
            return None
        return str(i)

class NEApi(api.Api):
    def __init__(self, initConfig = {}):
        super(NEApi, self).__init__(initConfig)
        self.paths = {
            "directoryPath": [util.getPath("NEApi"), util.getPath("NEApi/pic"), util.getPath("NEApi/lyrics")],
            "songPathById": util.getPath("NEApi/%s_%d.mp3"),
            "songPathById_link": util.getPath("NEApi/%s_%s.txt"),
            "albumCoverById": util.getPath("NEApi/pic/%s.png"),
            "lyricsById": util.getPath("NEApi/lyrics/%s.lrc.json"),
        }

        if not self.localData['cookies']:
            nuid = util.randomString("0123456789abcdefghijklmnopqrstuvwxyz", 32)
            currTime = time.time() * 1000
            self.updateCookies(util.str2SimpleCookie('appver=1.5.9;os=osx; channel=netease;osver=%s;JSESSIONID-WYYY=%s:%.0f; _iuqxldmzr_=32; _ntes_nnid=%s,%.0f; _ntes_nuid=%s' % (r'%E7%89%88%E6%9C%AC%2010.13.2%EF%BC%88%E7%89%88%E5%8F%B7%2017C88%EF%BC%89', util.randomString("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKMNOPQRSTUVWXYZ", 176), currTime, nuid, currTime, nuid)))

    def getCsrf(self):
        c = util.str2SimpleCookie(self.localData['cookies'])
        if c.has_key('__csrf'):
            csrf = c['__csrf'].value
        else:
            csrf = ""
        return csrf

    def login(self, **kwargs):
        #md5Encoder = md5.new()
        #md5Encoder.update(self.config['password'].encode('utf-8'))
        #encPassword = md5Encoder.hexdigest()
        encPassword = self.config['password']  # 前端来对密码进行加密

        csrf = self.getCsrf()

        if not self.config['isPhone']:
            params = {
                'username' : self.config['username'],
                'password' : encPassword,
                'rememberLogin' : 'true',
            }
            url = "/weapi/login"
        else:
            params = {
                'phone' : self.config['cellphone'],
                'password' : encPassword,
                'rememberLogin' : 'true',
            }
            url = "/weapi/login/cellphone"

        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url, params, {})
        resBody = json.loads(resBody)

        if resBody['code'] == 415:
            # IP高频
            raise NEApiNeedCaptcha("IP Blocked. Please verify captcha.")
            
        if resBody['code'] == 200:
            self.updateLocalData({'loggedIn':True, "userProfile": resBody["profile"]})
            self.updateCookies(resCookie)

        if resBody['code'] == 502:
            raise NEApiWrongPassword("Login Failed for wrong username or password.")

        if resBody['code'] == 461:
            raise NEApiBlockedByYundun("Blocked by yundun. Please change ClientToken.")

        self.currentUser = NEApiUser(resBody['profile'], url)
        self.isLoggedIn *= True
        return self.currentUser

    def refreshLogin(self, **kwargs):
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), "/weapi/login/token/refresh", {'csrf_token' : self.getCsrf()}, {'csrf_token' : self.getCsrf()})
        resBody = json.loads(resBody)
        
        self.checkCode(resBody['code'], {}, resBody)

        self.updateCookies(resCookie)

        self.currentUser = NEApiUser(self.localData['userProfile'], "")
        self.isLoggedIn *= True
        return self.currentUser

    def refreshLogin_old2(self, **kwargs):
        resCookie, resBody = self._plainHTTP(kwargs.get("rawHTTP"), "/", 'GET', {}, {}, {'Referer': 'http://music.163.com/', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/603.2.4 (KHTML, like Gecko) Version/10.1.1 Safari/603.2.4'})
        self.updateCookies(resCookie)

        try:
            obj = json.loads(NE_JS2JSON.sub(r'\1"\2":\3', NE_USERINFO.finditer(resBody).next().group(1)))
            if not obj.has_key('nickname'):
                raise KeyError
        except (StopIteration, KeyError):
            self.isLoggedIn *= False
            self.logger.info("4")
            raise NEApiNotLoggedInError("Login status has expired or you haven't logged in. Please log in again.")

        self.currentUser = NEApiUser(obj, "/")
        self.isLoggedIn *= True
        return self.currentUser
        
    def _encHTTP(self, rawHTTP, url, params, query = {}, headers = {}):
        _headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Mobile Safari/537.36",
            'Referer': 'http://music.163.com/',
            'Host': "music.163.com",
            "Cookie": self.localData['cookies']
        }
        _headers.update(headers)

        self.logger.info("params: %s" % params)

        if rawHTTP == None:
            rawHTTP = self.rawHTTP

        return rawHTTP(NE_HOST, url, False, 'POST', neEncrypt(params), query, _headers, self.logger)

    def _plainHTTP(self, rawHTTP, url, method='GET', params={}, query = {}, headers = {}):
        _headers = {"Cookie": self.localData['cookies']}
        _headers.update(headers)

        if rawHTTP == None:
            rawHTTP = self.rawHTTP

        return rawHTTP(NE_HOST, url, False, method, params, query, _headers, self.logger)

    def checkCode(self, code, params, respBody):
        code = int(code)
        if code == 301:
            self.isLoggedIn *= False
            raise NEApiNotLoggedInError("Login status has expired or you haven't logged in. Please log in again.")

        if code == 200:
            pass
        elif code == 400:
            raise NEApiNotLoggedInError("Illegal Operation!", params, respBody)
        else:
            self.logger.warning("Code illegal: " + str(code))
        
        return

    def getUserPlaylists(self, uid = -1, offset = 0, limit = 1000, **kwargs):
        """
            Get ALL songlists of this user.
            Old API: limit can't be zero or negative.
            when UID is -1, returns current user's songlists.
        """
        url = "/weapi/user/playlist"
        params = {
            'csrf_token' : self.getCsrf(),
            'offset' : offset,
            'limit' : limit,
            'uid' : uid,
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url, params, {'csrf_token' : self.getCsrf()})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        return api.getApiObject(api.ApiList, resBody['playlist'], url, NEApiPlaylist)

    def getRecommendationPlaylist(self, limit = 200, offset = 0, **kwargs):
        url = "/weapi/v2/discovery/recommend/songs"
        params = {
            'csrf_token' : self.getCsrf(),
            'limit' : limit,
            'offset': offset,
            'total' : False
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url, params, {'csrf_token' : self.getCsrf()})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        return api.getApiObject(api.ApiList, resBody['recommend'], url, NEApiSong)

    def getFMPlaylist(self, limit = 3, **kwargs):
        url = "/weapi/v1/radio/get"
        params = {
            'csrf_token' : self.getCsrf(),
            'limit' : limit,
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url, params, {'csrf_token' : self.getCsrf()})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        return api.getApiObject(api.ApiList, resBody['data'], url, NEApiSong)
        
    def getPlaylist(self, id, limit = 1000, offset = 0, **kwargs):
        url = "/weapi/v3/playlist/detail"
        params = {
            'csrf_token' : self.getCsrf(),
            'id' : id,
            'limit': limit,
            'n' : limit,
            'offset' : offset,
            'total' : False,
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url, params, {'csrf_token' : self.getCsrf()})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        return api.getApiObject(NEApiPlaylist, resBody['playlist'], url)

    def getAlbum(self, id, apiVersion = 1, **kwargs):
        if apiVersion == 1:
            url = "/api/album"
        else:
            url = "/weapi/v1/album"

        params = {
            'csrf_token' : self.getCsrf(),
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url + "/%s" % id, params, {'csrf_token' : self.getCsrf()})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        if apiVersion == 1:
            return api.getApiObject(NEApiAlbum, resBody['album'], url)
        else:
            return api.getApiObject(NEApiAlbum, resBody, url)

    def getSongs(self, songIdList, **kwargs):
        i = 0
        for songId in songIdList:
            if not isinstance(songId, str):
                songIdList[i] = str(songId)
            i += 1

        url = "/weapi/song/detail"
        params = {
            'csrf_token' : self.getCsrf(),
            'ids' : repr(songIdList).replace(" ", "").replace("'", "").replace("\"", ""),
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url, params, {'csrf_token' : self.getCsrf()})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        sortedData = [None] * len(songIdList)
        for song in resBody['songs']:
            sortedData[songIdList.index(str(song['id']))] = song

        return api.getApiObject(api.ApiList, sortedData, url, NEApiSong)

    def getSongUrls_fidel(self, songIdList, br = 2, **kwargs):
        i = 0
        for songId in songIdList:
            if not isinstance(songId, str):
                songIdList[i] = str(songId)
            i += 1

        if isinstance(br, int):
            br = NE_BRS[br][0]

        url = "/weapi/song/enhance/player/url"
        params = {
            'csrf_token' : self.getCsrf(),
            'ids' : repr(songIdList).replace(" ", "").replace("'", "").replace("\"", ""),
            'br' : dict(NE_BRS)[br]
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url, params, {'csrf_token' : self.getCsrf()})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        sortedData = [None] * len(songIdList)
        for song in resBody['data']:
            sortedData[songIdList.index(str(song['id']))] = song

        return [(s is None) and s['url'] or None for s in sortedData]

    def getSongUrls(self, songIdList, br = 2, songList = {}):
        """
            get URLs of songs by their ids
            songIDList: a list that includes ids.
            br: one of 1, 2, 3
            sorted to be consistent with songIDList
        """
        # First : get url by new api(weapi) by calling getSongUrls_fidel
        urlList = self.getSongUrls_fidel(songIdList, br)
        brNum = br

        try:
            urlList.index(None)
        except ValueError:
            return urlList

        # Then : use old api + album + mp3enckey to get
        if not songList:
            songList = self.getSongs(songIdList)

        for urlI in range(len(urlList)):
            if urlList[urlI] is None:
                self.logger.warning("urlList[%d] is None, getting it by album" % urlI)
                
                albumId = songList[urlI].album().id()
                album = self.getAlbum(albumId)
                albumSongIndex = None
                albumSongs = album.songs()

                try:
                    albumSongIndex = [str(song.id()) for song in albumSongs].index(str(songIdList[urlI]))
                except KeyError:
                    self.logger.error("Song %s KeyError!" % songIdList[urlI])
                    continue

                albumSong = albumSongs[albumSongIndex]
                dfsIdUrls = []
                self.logger.warning("Got DfsId %s" % albumSong.dfsId())
                for dfsId in albumSong.dfsId():
                    if dfsId:
                        currUrl = dfsId2Mp3Url(dfsId)
                        if util.isURLAvailable(currUrl):
                            dfsIdUrls.append(currUrl)
                        else:
                            dfsIdUrls.append(None)
                    else:
                        dfsIdUrls.append(None)
                        
                availableBrs = [i for i, k in zip(range(len(dfsIdUrls)), dfsIdUrls) if k is not None]
                if len(availableBrs) == 0:
                    self.logger.error("No available DFSID-encrypted URL for Song %s !!" % songIdList[urlI])
                    continue
                closestSelector = [abs(i - brNum) for i in availableBrs]
                closestBrNum = min(closestSelector)
                closestBrNumIndex = closestSelector.index(closestBrNum)
                self.logger.debug("availableBrs : " + str(availableBrs))
                self.logger.debug("closestSelector : " + str(closestSelector))
                self.logger.debug("closestBrNumIndex : " + str(closestBrNumIndex))
                self.logger.debug("closestBrNum : " + str(closestBrNum))
                
                urlList[urlI] = dfsIdUrls[closestBrNum]

        self.logger.info("All urls: " + json.dumps(urlList))
        return urlList

    def getLyrics(self, songId, **kwargs):
        url = "/weapi/song/lyric"
        params = {
            'csrf_token' : self.getCsrf(),
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url, params, {'csrf_token' : self.getCsrf(),'id' : songId,'lv' : -1,'kv' : -1,'tv' : -1})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        return api.getApiObject(NEApiLyrics, resBody, url)

    def getComments(self, commentsId, offset, total, limit, **kwargs):
        url = "/weapi/v1/resource/comments"
        params = {
            'csrf_token' : self.getCsrf(),
            'offset' : offset,
            'total' : total,
            'limit' : limit
        }
        resCookie, resBody = self._encHTTP(kwargs.get("rawHTTP"), url + "/%s" % commentsId, params, {'csrf_token' : self.getCsrf()})

        resBody = json.loads(resBody)
        self.checkCode(resBody['code'], params, resBody)
        self.updateCookies(resCookie)

        return {
            'hotComments': api.getApiObject(api.ApiList, resBody['hotComments'], url, NEApiComment),
            'comments': api.getApiObject(api.ApiList, resBody['comments'], url, NEApiComment),
        }
            
        
