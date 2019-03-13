RELEASE = False

import sys, os
PATH_LIBPATH = os.path.join(os.getcwd(), "lib")    # 在 Python shell 运行时，E:\PYTHON 和 E:\PYTHON\LIB 会自动加到 PATH
sys.path.append(PATH_LIBPATH)
if os.getcwd().find("2000b1a5") != -1:
    PATH_LIBPATH = "e:\\python\\lib"
    sys.path.append("e:\\python")
    sys.path.append(PATH_LIBPATH)

import progressnotes_pymusic as progressnotes
sys.progress = progressnotes.ProgressNote()
import appuifw2_pymusic as appuifw2
import e32

def progressCancelCallback():
    appuifw2.note("正在退出".decode("utf-8"))
    print "正在退出".decode("utf-8")
    if RELEASE:
        appuifw2.app.set_exit()
        sys.exit()
        e32.ao_yield()
        raise SystemExit, "User exit"

sys.progress.cancel_callback(progressCancelCallback)
sys.progress.progress(100)

sys.progressVal = 0
def updateProgressBy(x, text):
    sys.progressVal += x
    sys.progress.update(sys.progressVal, text + u"%d%%" % sys.progressVal)
    e32.ao_yield()


sys.updateProgressBy = updateProgressBy

sys.updateProgressBy(0, ("加载模块...").decode("utf-8"))
import staticnote_pymusic as staticnote
sys.updateProgressBy(2, ("加载模块...").decode("utf-8"))

import util  # progress + 20
sys.updateProgressBy(0, ("加载模块...").decode("utf-8"))

import views
import controllers
sys.updateProgressBy(3, ("加载模块...").decode("utf-8"))

import sys
import os
import traceback
import thread
import time
import types
sys.updateProgressBy(20, ("加载模块...").decode("utf-8"))

import json
import md5

import api
import api.neteaseApi
import taskQueue
sys.updateProgressBy(20, ("加载函数...").decode("utf-8"))

u = util.u
getPath = util.getPath

REFRESH_PERIOD = 0.5

class ConfigItem(object):
    typeDict = {'text': unicode, 'number': int, 'combo': int}
    def __init__(self, type1, name, friendlyName, extraValue, extraValue_inverse, defaultValue):
        self.formType = type1
        self.type = ConfigItem.typeDict[type1]
        self.name = name
        self.friendlyName = friendlyName
        self.extraValue = extraValue
        self.extraValue_inverse = extraValue_inverse
        self.defaultValue = defaultValue
        
def md5Encrypt(input):
    if not input:
        return u""
    md5Encoder = md5.new()
    md5Encoder.update(input.encode('utf-8'))
    return unicode(md5Encoder.hexdigest())

allConfigItems = [
    ConfigItem('text', u"cellphone", u/"手机号码", None, None, u""),
    ConfigItem('text', u"username", u/"登录用户名", None, None, u""),
    ConfigItem('text', u"password", u/"登录密码", lambda value: value and u/"****隐藏****", lambda value: (value == u/"****隐藏****") and config['password'] or md5Encrypt(value), u""),
    # My cjson will force return long, so int()
    ConfigItem('combo', u"isPhone", u/"是否使用手机登录", lambda value: ([u/"否", u/"是"], int(value)), lambda tupleValue: tupleValue[1], 0),
    ConfigItem('text', u"mediaFolder", u/"媒体文件夹", None, None, u"E:\\Music"),
]

config = {}
def updateConfig():
    # 当前无配置项 - 从文件加载配置项；当前有配置项 - 向文件写入配置项
    global config

    if config == {}:
        if os.path.exists(util.PATH_CONFIG):
            if os.path.isdir(util.PATH_CONFIG):
                raise Exception, u/util.PATH_CONFIG + u/" 是个文件夹，不是文件"
            f = open(util.PATH_CONFIG, "r")
            content = f.read()

            try:
                config = {}
                config = json.loads(content)
                f.close()
                
                for configItem in allConfigItems:
                    if not config.has_key(configItem.name):
                        raise KeyError
            except Exception:
                f.close()

                for configItem in allConfigItems:
                    if not config.has_key(configItem.name):
                        config[configItem.name] = configItem.defaultValue

                f = open(util.PATH_CONFIG, "w")
                content = json.dumps(config)
                f.write(content)
                f.close()
        else:
            config = {}
            for configItem in allConfigItems:
                config[configItem.name] = configItem.defaultValue
            f = open(util.PATH_CONFIG, "w")
            content = json.dumps(config)
            f.write(content)
            f.close()
    else:
        f = open(util.PATH_CONFIG, "w")
        content = json.dumps(config)
        f.write(content)
        f.close()

def safeStaticNote(title, content):
    try:
        routineMan.stopTimer()
    except Exception:
        pass

    staticnote.linknote(title, content, u"")
    util.errorOccurred = False
    
    try:
        routineMan.startTimer()
    except Exception:
        pass

def exitHandler():
    try:
        routineMan.exit()
    except Exception, e:
        exceptionHandler(e)

def formSaveHook(formList):
    # formList : [(x.friendlyName, x.formType, x.value for x in allConfigItems]

    global config
    i = 0
    for configItem in allConfigItems:
        if configItem.extraValue_inverse:
            extractedValue = configItem.extraValue_inverse(formList[i][2])
        else:
            extractedValue = formList[i][2]

        config[configItem.name] = extractedValue
        i += 1
    updateConfig()
    return True

def loadAPI():
    global neapi
    neapi = api.neteaseApi.NEApi({
        "isPhone": config['isPhone'],
        "cellphone": config['cellphone'],
        "username": config['username'],
        "password": config['password'],
        "logger": l,
        "localFile": util.getPath("NEApi_localdata.json")
    })

    neapi.createDirectory()

    neapi.rawHTTP = syncRawHTTP

def loadUI():
    global mainView
    views.tryWrapper = tryWrapper
    mainView = views.MainView()
    mainView.exit_key_handler = exitHandler
    appuifw2.app.view = mainView

    global tasksView
    tasksView = views.TasksView()

    global monitor
    monitor = taskQueue.Monitor(tasksView.body)
    routineMan.addRoutineObj(monitor)

def loadController():
    def menuConfig(view):
        form = appuifw2.Form([(x.friendlyName, x.formType, x.extraValue and x.extraValue(config[x.name]) or config[x.name]) for x in allConfigItems], appuifw2.FFormEditModeOnly | appuifw2.FFormDoubleSpaced)
        form.save_hook = formSaveHook
        form.execute()

    def testWork(**kwargs):
        try:
            running = True
            progressMax = 1000
            p = 0
            while p < progressMax:
                e32.ao_sleep(0.8)
                if running:
                    p += 20
                result = kwargs['progressCallback'](p, progressMax)
                if result == 0:
                    running = True
                elif result == 1:
                    running = False
                elif result == 2:
                    running = False
                    raise taskQueue.UserCancelled, unicode("User cancelled this Task")

            kwargs['finishCallback']()
        except Exception, e:
            kwargs['errorCallback'](e)

    def tasks(view):
        appuifw2.app.view = tasksView
        
    def tasksAdd(view):
        monitor.newTask(taskQueue.Task(
            u/"测试工作",
            testWork,
            (),
            {},
            None,
            None,
            None
        ))

    def login(view):
        neapi.ensureLoggedIn()

    def copy(mainView):
        appuifw2.query(mainView.body[mainView.body.current()].desc, u'text', unicode(mainView.body[mainView.body.current()].content))

    def tasksPauseCont(view):
        index = view.body.current()
        if monitor.tasks[index].suspended:
            monitor.resume(index)
        else:
            monitor.suspend(index)

    def tasksDetail(view):
        safeStaticNote(u/"该任务信息", view.body[view.body.current()].title)

    def tasksCancel(view):
        index = view.body.current()
        monitor.cancel(index)

    def notImplemented(view):
        raise NotImplementedError, u"Not Implemented"

    views.MenuCallbacks.playlist = notImplemented
    views.MenuCallbacks.saveSong = notImplemented
    views.MenuCallbacks.userPlaylists = notImplemented
    views.MenuCallbacks.playlistById = notImplemented
    views.MenuCallbacks.config = menuConfig

    views.MenuCallbacks.tasksAdd = tasksAdd
    views.MenuCallbacks.tasksPauseCont = tasksPauseCont
    views.MenuCallbacks.tasksDetail = tasksDetail
    views.MenuCallbacks.tasksCancel = tasksCancel

    views.ListboxCallbacks.tasks = tasks
    views.ListboxCallbacks.copy = copy
    views.ListboxCallbacks.login = progressNoteWrapper(login)
    views.ListboxCallbacks.playPause = notImplemented
    views.ListboxCallbacks.nextSong = notImplemented
    views.ListboxCallbacks.prevSong = notImplemented
    views.ListboxCallbacks.adjustVolume = notImplemented
    views.ListboxCallbacks.coverPic = notImplemented
    views.ListboxCallbacks.love = notImplemented
    views.ListboxCallbacks.hotComment = notImplemented
    views.ListboxCallbacks.latestComment = notImplemented

def loadConnection():
    util.connect(neapi.isLoggedIn, mainView.iLogin, views.itemDescriptionStyleUpdaterWrapper(lambda x: x and neapi.currentUser.nickname() or u/"未登录, 点此登录"))

    util.connect(monitor, mainView.iTasks, taskQueue.itemMonitorStyleUpdaterWrapper())

    # util.connect(player, mainView.iPlayPause, views.itemDurationPositionStyleUpdaterWrapper())

    mainView.update()

class RoutineManager(object):
    def __init__(self, period = 0.1):
        self.period = period
        self.routineObjs = []
        self.pendingTasks = []
        self.running = True

    def exit(self):
        for obj in self.routineObjs:
            obj.exit()
        
        self.running = False
        self.timer.cancel()
        self.lock.signal()
        pass

    def stopTimer(self):
        self.timer.cancel()
    
    def startTimer(self):
        self.timer.cancel()
        self.timer.after(0, self.routine)

    def routine(self):
        for obj in self.routineObjs:
            obj.routine()

        if self.running and not util.errorOccurred:
            self.timer.after(self.period, self.routine)

    def run(self):
        self.lock = e32.Ao_lock()
        self.timer = e32.Ao_timer()

        self.startTimer()
        
        while True:
            self.lock.wait()
            if self.running == False:
                break
            for t in self.pendingTasks:
                t()
            self.pendingTasks = []

    def addPendingTasks(self, func):
        self.pendingTasks.append(func)

    def addRoutineObj(self, routineObj):
        self.routineObjs.append(routineObj)

def main():
    global l, routineMan

    sys.updateProgressBy(25, ("创建日志句柄...").decode("utf-8"))

    l = util.Logger("main")
    l.addHandler(util.LoggerHandler("mainhandler", open(util.PATH_LOG, "w", buffering = 0), util.LOGGER_LEVEL['info']))

    util.logger = l
    # l.addHandler(util.LoggerHandler("screen", sys.stderr, util.LOGGER_LEVEL['error']))

    views.exceptionHandler = exceptionHandler

    sys.progress.update(100, unicode("完成，现在加载UI"))
    sys.progress.finish()
    e32.ao_sleep(0.1)

    routineMan = RoutineManager(REFRESH_PERIOD)

    updateConfig()

    loadAPI()
    
    loadController()

    loadUI()

    loadConnection()

    
    l.info(u/"After Creating Thread")

    routineMan.run()
    appuifw2.app.set_exit()

def tryWrapper(func, args = (), kwargs = {}):
    def wrapped():
        f = func
        try:
            if type(f) is types.UnboundMethodType:
                f = f.im_func

            f(*args, **kwargs)
        except Exception, e:
            exceptionHandler(e)
    return wrapped

def progressNoteWrapper(func):
    def wrapped(*args, **kwargs):
        pn = progressnotes.ProgressNote()
        util.currentProgressNote = pn
        util.currentProgressNoteProgressMax = 0
        pn.wait()
        pn.update(0, u/"请等待...")

        func(*args, **kwargs)

        pn.finish()
        util.currentProgressNote = None

    return wrapped

def refreshCurrentProgress(progress, progressMax):
    if not util.currentProgressNote:
        return

    if progressMax != util.currentProgressNoteProgressMax:
        util.currentProgressNote.finish()
        util.currentProgressNote.progress(progressMax)
        util.currentProgressNoteProgressMax = progressMax

    util.currentProgressNote.update(progress, u/"加载中(%d/%d)" % (progress, progressMax))

def syncRawHTTP(host, url, https = True, method = 'GET', params = {}, query = "", header = {}, logger = None, writeIO = None, **kwargs):
    kwargs['progressCallback'] = refreshCurrentProgress
    return util.rawHTTP(host, url, https, method, params, query, header, logger, writeIO, **kwargs)

def exceptionHandler(e):
    errStr = unicode(e.__class__.__name__) + u': ' + unicode(e)
    tb = ''.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
    errText = errStr + u"\n" + tb.decode("utf-8")

    #print errText

    try:
        l.error(u'Error :')
        l.error(errStr)
        l.error(tb)
    except Exception:
        pass

    util.lastError = e
    util.errorOccurred = True

    safeStaticNote(u/"发生错误", errText + u/"\n请查询日志" + util.PATH_LOG + u/"获取更多详情.")

    try:
        util.currentProgressNote.finish()
    except Exception:
        pass

try:
    main()
except Exception, e:
    exceptionHandler(e)