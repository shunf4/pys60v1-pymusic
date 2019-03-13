import sys
def updateProgressBy(x, text = None):
    if sys.__dict__.has_key('updateProgressBy'):
        if text is None:
            text = ("加载模块...").decode("utf-8")
        sys.updateProgressBy(x, text)
import Cookie
import httplib, urllib
import re
updateProgressBy(2)
import StringIO
import exceptions
import time
import thread
import traceback

import random
import os
updateProgressBy(3)

machineType = "pc"

if os.path.exists("E:\\Private"):
    machineType = "nokia"

if machineType == "nokia":
    print "Machine type: nokia"
else:
	sys.path.append("..")

if machineType == "nokia":
    import cfileman_pymusic as cfileman

import imp

# PATH 路径、软件根目录的路径设置
_sys_org = imp.load_dynamic('_sys_org', 'sys')
_sys_org.setdefaultencoding("utf-8")
del _sys_org

updateProgressBy(2)

PATH_LIBPATH = os.path.join(os.getcwd(), "lib")    # 在 Python shell 运行时，E:\PYTHON 和 E:\PYTHON\LIB 会自动加到 PATH

if machineType == "nokia":
    sys.path.append(PATH_LIBPATH)
    PATH_PYMROOT = "e:\\PyMusic"
else:
    PATH_PYMROOT = os.path.join(os.getcwd(), "..\\PyMusic")

sys.path[0:0] = [PATH_LIBPATH]

updateProgressBy(1)

def getPath(relativePath):
    return os.path.join(PATH_PYMROOT, relativePath)

updateProgressBy(1, ("加载TLS模块，稍久...").decode("utf-8"))

from tlslite.integration.HTTPTLSConnection import HTTPTLSConnection

updateProgressBy(5)

enumerate = lambda x:zip(range(len(x)), x)

class UTF8ToUnicodeShorthand:
    def __init__(self):
        pass

    def __div__(self, str1):
        return unicode(str1)

    def __call__(self, str1):
        return unicode(str1)

# u/"x" 和 u("x") 均等价于 "x".decode("utf-8")
u = UTF8ToUnicodeShorthand()

class InvalidHTTPStatusException(exceptions.Warning):
    def __init__(self, *args):
        Warning.__init__(self, *args)


class LoggerHandler(object):
    def __init__(self, id, obj, level):
        self.id = id
        self.obj = obj
        self.level = level
        self.write = obj.write

logger = None

LOGGER_LEVEL = {"debug": 5, "info": 15, "warning": 25, "error": 35, "critical": 45}
LOGGER_LEVEL_INFINITE = 100
class Logger(object):
    def __init__(self, name):
        self.name = name
        self.handlers = []
        self._lowestLevel = LOGGER_LEVEL_INFINITE
        self.threadID = thread.get_ident()
        
        self.pending = []

        # self.handlers = [LoggerHandler("default_stderr"), sys.stderr, LOGGER_LEVEL["error"]]
        #self._lowestLevel = LOGGER_LEVEL["error"]

    def __repr__(self):
        return "<Logger %s at %s>" % (self.name, hex(id(self)))

    def _updateLowestLevel(self):
        self._lowestLevel = LOGGER_LEVEL_INFINITE
        for handler in self.handlers:
            if self._lowestLevel > handler.level:
                self._lowestLevel = handler.level

    def setHandlers(self, handlers):
        self.handlers = handlers
        self._updateLowestLevel()

    def addHandler(self, handler):
        self.handlers.append(handler)
        self._updateLowestLevel()

    def delHandler(self, id):
        self.handlers = [handler for handler in self.handlers if handler.id == id]
        self._updateLowestLevel()

    def log(self, level, args, processingPending = False):
        if thread.get_ident() != self.threadID:
            if self._lowestLevel > LOGGER_LEVEL[level]:
                return

            self.pending.append((level, args))
            return
        else:
            if not processingPending and self.pending:
                self.processPending()

        if self._lowestLevel > LOGGER_LEVEL[level]:
            return

        for handler in self.handlers:
            if handler.level > LOGGER_LEVEL[level]:
                continue
            for arg in args:
                handler.write("%.2f %s[%s]%s : %s" % (time.clock(), processingPending and u"P" or u" ", level[0].upper(), self.name, arg))
                handler.write("\r\n")

    def debug(self, *args):
        self.log("debug", args)

    def info(self, *args):
        self.log("info", args)

    def warning(self, *args):
        self.log("warning", args)

    def error(self, *args):
        self.log("error", args)

    def critical(self, *args):
        self.log("critical", args)

    def processPending(self):
        for level, args in self.pending:
            self.log(level, args, True)

        self.pending = []

def itemUpdateContent(item):
    if item.__dict__.has_key("desc"):
        if item.__dict__.has_key("contentGenerator"):
            if item.contentGenerator:
                item.content = item.contentGenerator()

        item.title = item.desc + u": " + item.content

def itemUpdateContentWithValue(item, value, extraConversion = None):
    if item.__dict__.has_key("desc"):
        if extraConversion:
            item.content = extraConversion(value)
        else:
            item.content = value
        item.title = item.desc + u": " + item.content

# 接口类描述
# class BoundData(object):
#     def __init__(self):
#         self.changed = []
#     def addSubscriber(self, func):
#         self.changed.append(func)
#     def update(self):
#         for func in self.changed:
#             func()

class ValuedBoundData(object):
    def __init__(self, value = None):
        self.changed = []
        self.value = value

    def addSubscriber(self, func):
        self.changed.append(func)

    def update(self):
        for func in self.changed:
            func()

    def getValue(self):
        return self.value

    def __imul__(self, value):
        self.value = value
        self.update()
        return self

def connect(boundData, item, updater):
    item.dataSource = boundData
    item.updater = updater
    boundData.addSubscriber(item.update)

def legalFileName(sth):
    return sth.replace("?", "_").replace("/", "_").replace("\\", "_").replace("(", "_").replace(")", "_").replace(":", "_").replace("*", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_")
    
def mu(*arg):
    if(len(arg) == 1):
        return unicode(arg[0])
    return tuple([unicode(x) for x in arg])

def isURLAvailable(url):
    host = url.split("/")[2]
    conn = httplib.HTTPSConnection(host, port = httplib.HTTPS_PORT)
    conn.request("GET", url, None, {})
    resp = conn.getresponse()
    code = resp.status

    available = True
    if code is not 200:
        available = False

    resp.close()
    conn.close()
    return available

def getIOLength(readIO):
    try:
        if readIO.len == None:
            raise AttributeError
        else:
            totalSize = long(readIO.len)
            return totalSize == 0 and 1048576 or totalSize
    except AttributeError:
        pass

    try:
        if readIO.getheader("Content-Length") is None:
            raise AttributeError
        else:
            totalSize = int(readIO.getheader("Content-Length"))
            return totalSize == 0 and 1048576 or totalSize
    except AttributeError:
        pass

    try:
        if readIO.length == None:
            raise AttributeError
        else:
            totalSize = readIO.length
            return totalSize == 0 and 1048576 or totalSize
    except AttributeError:
        pass

    #raise IOError, "Can't read Length"
    return 10485760

def SimpleCookie2Str(cookie):
    return cookie.output([],"","")

def str2SimpleCookie(inCookie):
    if(isinstance(inCookie, str) or isinstance(inCookie, unicode)):
        if(isinstance(inCookie, unicode)):
            inCookie = inCookie.encode("utf-8")
        elif isinstance(inCookie, str):
            pass
        else:
            raise TypeError, "inCookie should be a str or unicode."
        #Since Python2.5- have a bug on unquoted ExpiresDate String
        inCookie = EXPIREDATE_RE.sub(lambda matched:"Expires=\"%s\";" % matched.group('date'), inCookie)
        inCookie = Cookie.SimpleCookie(inCookie)
    elif isinstance(inCookie, Cookie.SimpleCookie):
        pass
    else:
        raise TypeError, 'inCookie must be Headercookie str or SimpleCookie Object'
    return inCookie

def doIO(readIO, writeIO, callbackFunc, blockSize, totalSize):
    receivedBlocks = 0
    receivedSize = 0
    if callbackFunc:
        #tmpDebug.debug("callback Func: %s %s %s %s" %(receivedBlocks, blockSize, receivedSize, totalSize))
        callbackFunc(receivedSize, totalSize)

    while True:
        block = readIO.read(blockSize)
        if (not block):
            break
        receivedBlocks += 1
        receivedSize += len(block)
        writeIO.write(block)
        if callbackFunc:
            #tmpDebug.debug("callback Func: %s %s %s %s" %(receivedBlocks, blockSize, receivedSize, totalSize))
            callbackFunc(receivedSize, totalSize)


'''
url 的格式：
    1. /path/to/page
    2. http[s]://host/path/to/page，此格式会覆盖 host 和 https 参数

注意 writeIO 如果是以传类 File 对象的方式在不同线程之间传递会运行出错。
若要跨线程，writeIO 可直接填目的文件路径。
'''

def rawHTTP(host, url, https = True, method = 'GET', params = {}, query = "", header = {}, logger = None, writeIO = None, **kwargs):
    if url[0] != "/":
        splittedUrl = url.split('/')
        if url[0:7] == "http://" or url[0:8] == "https://":
            if url[0:8] == "https://":
                https = True
            else:
                https = False
            host = splittedUrl[2]
            url = '/' + '/'.join(splittedUrl[3:])
        else:
            host = splittedUrl[0]
            url = '/' + '/'.join(splittedUrl[1:])

    if isinstance(query, dict):
        query = urllib.urlencode(query)
    if query:
        url = url + "?" + query


    if isinstance(params, dict):
        params = urllib.urlencode(params)
    if not isinstance(params, str):
        params = str(params)


    if logger is None:
        logger = Logger("empty")
    logger.info(u'Request URI : %s ; Host : %s' % (unicode(url), unicode(host)))
    logger.info(u"Request Headers  : %s" % header)
    logger.info(u'Request Body : %s' % unicode(params))

    if https:
        conn = HTTPSConnection(host)
    else:
        conn = HTTPConnection(host)

    conn.request(method, url, params, header)
    resp = conn.getresponse()

    logger.info(u"Response:")
    logger.info(u"HeaderMsgs : %s" % unicode(resp.msg.dict))

    code = int(resp.status)

    if code == 302 or bool(resp.getheader('Location')):
        resp.close()
        conn.close()

        url2 = resp.getheader('Location')
        logger.info('Redirecting to ' + url2)

        return rawHTTP("", url2, https, method, params, query, header, logger, writeIO, **kwargs)

    logger.info(u"Content-Length: %s" % resp.getheader("Content-Length"))
    totalSize = getIOLength(resp)
    kwargs['progressCallback'](0, totalSize)
    logger.info(u'Response Length : %s' % unicode(totalSize))

    if hasattr(writeIO, "read"):
        destFile = writeIO
    elif isinstance(writeIO, str):
        destFile = open(str, "wb")
    elif writeIO is None:
        destFile = StringIO.StringIO()
    else:
        raise ValueError("writeIO is not good")

    doIO(resp, destFile, kwargs['progressCallback'], HTTP_BLOCKSIZE, totalSize)

    cookie = ''.join([x for x in resp.msg.headers if x.strip().upper().find('SET-COOKIE:') == 0])

    cookie = str2SimpleCookie(cookie)

    logger.info(u'Respose Cookie : %s' % cookie)
    logger.info(u'Response Body : (level 15 for short, level debug for long)')

    result = ""
    if isinstance(destFile, StringIO.StringIO):
        result = destFile.getvalue()
        if(len(result) < 1000):
            logger.info(result)
        else:
            logger.debug(result)

    logger.info(u'(Length : %d)' % len(result))
    
    resp.close()
    conn.close()
    destFile.close()

    if code != 200 and code != 304:
        logger.error("Code %s: %s" % (code, result))
        raise InvalidHTTPStatusException(code)

    return (cookie, result)

def rawHTTP_thread(host, url, https = True, method = 'GET', params = {}, query = "", header = {}, logger = None, writeIO = None, **kwargs):
    try:
        (cookie, result) = rawHTTP(host, url, https, method, params, query, header, logger, writeIO, **kwargs)
    except Exception, e:
        kwargs['errorCallback'](e, {'errText': ''.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))})

    kwargs['finishCallback']({'cookie': cookie, 'result': result})

def randomString(pattern, length):
    return ''.join([random.choice(pattern) for i in range(length)])

updateProgressBy(5)

def colonTime(msec):
    hr = long(msec / 3600000L)
    msec = long(msec % 3600000L)
    min = long(msec / 60000)
    msec = long(msec % 60000)
    sec = long(msec / 1000)
    msec = long(msec % 1000)
    str1 = ''
    unit = [':',':','.','']
    if hr:
        str1 = '%.2i%s' % (hr,unit[0])
    str1 = str1 + '%.2i%s' % (min,unit[1])
    str1 = str1 + '%.2i' % (sec)
    if str1 == '': str1 = '00:00'
    return str1


PATH_LOG = getPath("logs.txt")
PATH_CONFIG = getPath("config.json")
PATH_LOCALDATA = getPath("localData.json")

updateProgressBy(1)

# DIR_DOWNLOADEDMUSIC = getPath("DownloadedMusic")
# DIR_LYRICS = getPath("Lyrics")
# DIR_COVERPIC = getPath("CoverPic")
DIR_CACHE = getPath("Cache")

errorOccurred = False
lastError = None

if machineType == "nokia":
    fileman = cfileman.FileMan()
    for dir in [DIR_CACHE]:
        if dir[-1] != "\\":
            dir = dir + "\\"    # Must, for a bug in CFileMan::Mkdir
        if isinstance(dir, str):
            dir = unicode(dir)

        if not fileman.exists(dir):
            sys.stdout.write("%s not exist, creating it\n" % dir)
            try:
                fileman.mkdir(dir, cfileman.EOverWrite | cfileman.ERecurse)
            except SymbianError, e:
                sys.stdout.write("Making %s: SymbianError " % dir + str(e.args) + "\n")
        elif not fileman.is_dir(dir):
            try:
                fileman.delete(dir)
            except SymbianError, e:
                sys.stdout.write("Deleting %s: SymbianError " % dir + str(e.args) + "\n")
            try:
                fileman.mkdir(dir, cfileman.EOverWrite | cfileman.ERecurse)
            except SymbianError, e:
                sys.stdout.write("Making %s: SymbianError " % dir + str(e.args) + "\n")

HTTPConnection = httplib.HTTPConnection
HTTPSConnection = HTTPTLSConnection
HTTP_BLOCKSIZE =  8192

time.clock()

EXPIREDATE_RE = re.compile(r'expires\s*=\s*(?P<date>.+?);', re.I)