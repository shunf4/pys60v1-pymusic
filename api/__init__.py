#coding=utf-8
import time
import os
import json
import copy
import util
import re

import pyid3v2
import cfileman_pymusic as cfileman

def getApiObject(classObj, data, *args):
    if data is None:
        return None
    return classObj(data, *args)

def getApiObjectFromJSON(jsonStr):
    apiObj = json.loads(jsonStr)
    classObj = eval(apiObj['apiObjectClass'])
    
    if classObj is ApiList:
        elemClassObj = eval(apiObj['apiElementClass'])
        return ApiList(apiObj['data'], apiObj['via'], elemClassObj)
    else:
        return classObj(apiObj['data'], apiObj['via'])

def tagMp3(fileName, song, logger = None):
    id3 = pyid3v2.ID3v2(fileName, pyid3v2.ID3V2_FILE_MODIFY)

    # TODO: Remove existing tags
    logger.info("tagMp3 1")

    # Add Title Tag
    nf = pyid3v2.ID3v2Frame(fid = 'TIT2')
    nf.fields = (pyid3v2.ID3V2_FIELD_ENC_UTF16, unicode(song.name()), [unicode(song.name())])
    id3.frames.append(nf)

    logger.info("tagMp3 2")

    # Add Album Tag
    nf = pyid3v2.ID3v2Frame(fid = 'TALB')
    nf.fields = (pyid3v2.ID3V2_FIELD_ENC_UTF16, unicode(song.album().name()), [unicode(song.album().name())])
    id3.frames.append(nf)

    logger.info("tagMp3 3")

    # Add Artists Tag
    nf = pyid3v2.ID3v2Frame(fid = 'TPE1')
    artists = u'/'.join([unicode(a.name()) for a in song.artists()])
    nf.fields = (pyid3v2.ID3V2_FIELD_ENC_UTF16, artists, [artists])
    id3.frames.append(nf)

    logger.info("tagMp3 4")

    # Add Artists of Album Tag
    nf = pyid3v2.ID3v2Frame(fid = 'TPE2')
    artists = u'/'.join([unicode(a.name()) for a in song.album().artists()])
    nf.fields = (pyid3v2.ID3V2_FIELD_ENC_UTF16, artists, [artists])
    id3.frames.append(nf)

    logger.info("tagMp3 5")

    # Add TrackNo Tag
    nf = pyid3v2.ID3v2Frame(fid = 'TRCK')
    nf.fields = (pyid3v2.ID3V2_FIELD_ENC_UTF16, unicode(song.trackNo()), [unicode(song.trackNo())])
    id3.frames.append(nf)

    logger.info("tagMp3 6")

    id3.commit()

    logger.info("tagMp3 7")

def testPrint(name, sth, depth = 0):
    print "  " * depth,
    print name, ":",
    if isinstance(sth, ApiObject):
        print ""
        sth.testPrint(depth)
    else:
        print type(sth), sth

class ApiError(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)

class ApiLoginError(ApiError):
    def __init__(self, *args):
        ApiError.__init__(self, *args)

class ApiNotLoggedinError(ApiError):
    def __init__(self, *args):
        ApiError.__init__(self, *args)

RE_APINAME = re.compile(r"([A-Z]*Api).*")
class ApiObject(object):
    def __init__(self, data, via):
        self.data = data
        self.via = via

    def apiClassString(self):
        # 根据 ApiObject 类的命名规范来提取 Api 类。
        # NEApiSong => NEApi; XMApiList => XMApi
        fa = RE_APINAME.findall(self.__class__.__name__)
        if not fa:
            raise ValueError
        else:
            return fa[0]

    def toJSON(self):
        return json.dumps({
            'apiObjectClass': self.__class__.__name__,
            'via': self.via,
            'data': self.data
        })

    def __repr__(self):
        return "<%s(%s): %s>" % (self.__class__.__name__, self.via, self.data)
        
    def __str__(self):
        return "<%s(%s): %s>" % (self.__class__.__name__, self.via, self.data)

    def methods(self):
        return list(filter(lambda m: not m.startswith("__") and not m.endswith("__") and m != "methods" and m != "testPrint" and m != "toJSON" and callable(getattr(self, m)), dir(self)))

    def testPrint(self, depth = 0):
        print "  " * depth ,
        print "<%s(%s)>" % (self.__class__.__name__, self.via)
        for method in self.methods():
            testPrint(method, getattr(self, method)(), depth + 1)


class ApiList(ApiObject):
    # A list of class <classObj>'s intances
    
    def __init__(self, data, via, classObj):
        super(ApiList, self).__init__(data, via)
        self.classObj = classObj
        self.length = len(data)
        self.apiObjs = range(self.length)

    def __getitem__(self, index):
        if self.apiObjs[index] != index:
            return self.apiObjs[index]
        self.apiObjs[index] = getApiObject(self.classObj, self.data[index], self.via)
        return self.apiObjs[index]

    def toJSON(self):
        return json.dumps({
            'apiObjectClass': self.__class__.__name__,
            'apiElementClass': self.classObj.__name__,
            'via': self.via,
            'data': self.data
        })

    def __len__(self):
        return len(self.data)

    def testPrint(self, depth = 0):
        print "  " * depth ,
        print "<%s(%s)>" % (self.__class__.__name__, self.via)
        i = 0
        for item in self:
            testPrint(str(i), item, depth + 1)
            i += 1

class ApiPlaylist(ApiObject):
    def __init__(self, data, via):
        super(ApiPlaylist, self).__init__(data, via)

    # Abstract methods
        
    def creator(self):
        return getApiObject(ApiUser, self.data.get('creator'), self.via)

    def createTime(self):
        pass

    def description(self):
        pass

    def length(self):
        pass

    def coverImgUrl(self):
        pass

    def commentsId(self):
        pass

    def id(self):
        pass

    def songs(self):
        return getApiObject(ApiList, self.data.get("tracks"), self.via, ApiSong)

class ApiSong(ApiObject):
    def __init__(self, data, via):
        super(ApiSong, self).__init__(data, via)

    # Abstract methods
        
    def name(self):
        pass

    def id(self):
        pass

    def duration(self):
        pass

    def album(self):
        pass

    def artists(self):
        pass

    def trackNo(self):
        pass

    def alias(self):
        pass

class ApiAlbum(ApiObject):
    def __init__(self, data, via):
        super(ApiAlbum, self).__init__(data, via)

    # Abstract methods
        
    def name(self):
        pass

    def id(self):
        pass

    def artists(self):
        pass

    def coverImgUrl(self):
        pass

    def songs(self):
        pass

class ApiArtist(ApiObject):
    def __init__(self, data, via):
        super(ApiArtist, self).__init__(data, via)

    # Abstract methods
        
    def name(self):
        pass

    def id(self):
        pass

class TextLyrics(object):
    def __init__(self, lrc):
        self.lyrics = lrc

class ApiLyrics(ApiObject):
    def __init__(self, data, via):
        super(ApiLyrics, self).__init__(data, via)

    # Abstract methods
        
    def lyrics(self):
        pass

    def translatedLyrics(self):
        pass

    def noLyrics(self):
        pass

class ApiComment(ApiObject):
    def __init__(self, data, via):
        super(ApiComment, self).__init__(data, via)

    # Abstract methods
        
    def user(self):
        pass

    def id(self):
        pass

    def time(self):
        pass

    def content(self):
        pass

class ApiUser(ApiObject):
    def __init__(self, data, via):
        super(ApiUser, self).__init__(data, via)

    # Abstract methods
        
    def nickname(self):
        pass

    def id(self):
        pass

class Api(object):
    def __init__(self, initConfig = {}):
        name = self.__class__.__name__
        self.paths = {
            "directoryPath": [util.getPath("Api"), util.getPath("Api/pic"), util.getPath("Api/lyrics")], # 每个 API 对应目录
            "songPathById": util.getPath("Api/%s_%d.mp3"),  # 第一个参数代表曲目ID，第二个代表音质（所有API统一为3档，分别为1 2 3）
            "songPathById_link": util.getPath("Api/%s_%s.txt"),  # 当对应曲目不在 API 目录时，该 txt 文件记录其路径位置
            "albumCoverById": util.getPath("Api/pic/%s.png"), # 第一个参数代表专辑ID
            "lyricsById": util.getPath("Api/lyrics/%s.lrc.json"),
        }

        # Initialize config
        self.config = {
            "name": name,
            "localFile" : util.PATH_LOCALDATA,
            "logger": None
        }
        self.config['logger'] = util.Logger(self.config['name'] + "_%s" % time.localtime().__hash__().__hex__())
        self.config['logger'].setHandlers([])
    
        if initConfig:
            self._updateConfig(initConfig)

        # Initialize localData
        self.localData = {
            "config" : {},
            "cookies" : '',
            "loggedIn": False
        }
        self.initLocalData()

        self.isLoggedIn = util.ValuedBoundData(False)

        self.currentUser = None

    def createDirectory(self):
        fileman = cfileman.FileMan()
        for dir in self.paths['directoryPath']:
            if dir[-1] != "\\":
                dir = dir + "\\"    # Must, for a bug in CFileMan::Mkdir
            if isinstance(dir, str):
                dir = unicode(dir)

            if not fileman.exists(dir):
                fileman.mkdir(dir, cfileman.EOverWrite | cfileman.ERecurse)
            elif not fileman.is_dir(dir):
                fileman.delete(dir)
                fileman.mkdir(dir, cfileman.EOverWrite | cfileman.ERecurse)

    def rawHTTP(self, host, url, https = True, method = 'GET', params = {}, query = "", header = {}, logger = None, writeIO = None, **kwargs):
        kwargs['progressCallback'] = lambda a,b:None
        return util.rawHTTP(host, url, https, method, params, query, header, logger, writeIO, **kwargs)

    def _updateConfig(self, config):
        self.config.update(config)
        self.logger = self.config['logger']

    def initLocalData(self):
        if not os.path.exists(self.config['localFile']):
            self.writeLocalData()
        else:
            self.loadLocalData()

    def loadLocalData(self):
        file1 = open(self.config['localFile'], 'rb')
        self.localData = json.loads(file1.read())
        file1.close()
        self.config.update(self.localData['config'])
        self.logger.info("Loaded localData : %s" % self.localData)

    def writeLocalData(self):
        file0 = open(self.config['localFile'], 'wb')
        file0.write(json.dumps(self.localData))
        file0.close()

    def updateLocalData(self, localData):
        self.localData.update(localData)
        self.config.update(self.localData['config'])
        self.writeLocalData()

    def updateCookies(self, cookies):
        currCookie = util.str2SimpleCookie(self.localData['cookies'])
        currCookie.update(cookies)
        self.updateLocalData({'cookies': util.SimpleCookie2Str(currCookie)})


    def login(self):
        error = False
        self.isLoggedIn *= True
        if (error):
            raise ApiError("登录错误。常见错误。")
        return ApiUser({}, "")

    def refreshLogin(self):
        error = False
        self.isLoggedIn *= True
        if (error):
            raise ApiError("尚未登录。")
        return ApiUser({}, "")

    def ensureLoggedIn(self):
        try:
            return self.refreshLogin()
        except ApiNotLoggedinError:
            self.logger.info("11")
            self.logger.info("Not logged in. Try log in again using login()")
            self.logger.info("12")
            self.isLoggedIn *= False
            self.logger.info("13")
            return self.login()

    def getUserPlaylists(self, uid = -1, offset = 0, limit = 1000):
        """
            Get ALL songlists of this user.
            Old API: limit can't be zero or negative.
            when UID is -1, returns current user's songlists.
        """
        return getApiObject(ApiList, [], "/api/userplaylists", ApiPlaylist)

    def getRecommendationPlaylist(self, limit = 200, offset = 0):
        return getApiObject(ApiPlaylist, {}, "/api/recommendation")

    def getFMPlaylist(self, limit = 3):
        return getApiObject(ApiPlaylist, {}, "/api/fm")
        
    def getPlaylist(self, id, limit = 1000, offset = 0):
        return getApiObject(ApiPlaylist, {}, "/api/playlist/detail")

    def getAlbum(self, id):
        return getApiObject(ApiAlbum, {}, "/api/album/detail")

    def getSongs(self, songIdList):
        return getApiObject(ApiList, [], "/api/song/detail", ApiSong)

    def getSongUrls(self, songIdList, br):
        return []

    def getLyrics(self, songId):
        return getApiObject(ApiLyrics, {}, "/api/lyrics")

    def getComments(self, commentsId):
        return getApiObject(ApiList, [], "/api/comments", ApiComment)
            
        
