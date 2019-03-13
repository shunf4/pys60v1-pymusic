import util
import thread
import e32
import appuifw2_pymusic as appuifw2
import progressnotes_pymusic as progressnotes

u = util.u

'''
对于可被 Wrap 为一个 Task 的函数的约定 (通常时需要长时间 IO 的后台过程)
    
    这样的函数通常需要实时更新进度、进行错误状态和完成状态的上报

    更新进度：

        这个函数接受一个名为 progressCallback(currProgress, fullProgress, obj = {}) 的 kwarg；
        这个函数必须每隔一段时间调用 progressCallback 更新参数，不可陷入长时间等待；
        obj 可以作为额外参数；

        这个函数的返回值为0、1或2，反映了 Monitor 对 Task 对象的控制。
        0: 这个函数可以正常继续运行
        1: 这个函数现在必须暂停运行，但仍应该每隔一段时间调用 progressCallback，直到获取的返回值是0；
        2: 这个函数现在必须停止运行，并抛出 UserCancelled 异常。
        
    错误状态：
        
        所有的异常都应该在函数内部捕获，不能使其跳到函数外部。

        这个函数接受一个名为 errorCallback(e, obj = {}) 的 kwarg
        捕获异常后，这个函数必须执行 errorCallback(e) 登记错误，并在稍后终止函数的运行；
        obj 可以作为额外参数；
        
    完成状态：

        这个函数接受一个名为 finishCallback(obj = {}) 的 kwarg
        这个函数必须在完成后执行 finishCallback()
        obj 可以作为额外参数

    

    Monitor 在 UI 线程中作为一个 Active Object 化的线程运行。

    当 Monitor 开启任务后，它会调用 Task 对象中的函数，并将实参 progressCallback errorCallback finishCallback 传入。这些实参函数一般只会更新 Task 对象中的progress/error/finish属性。
    每隔 0.5s，Monitor 会检查一遍所有 Task 的进度情况，并（在 UI 线程内）调用各个 Task 的 extraProgressCallback(progress变化时) extraErrorCallback extraFinishCallback，只传入一个实参即前文的 obj。这三个函数是 Task 对象的属性，可用于更新 UI。
    
'''

class UserCancelled(Exception):
    def __init__(self, *args):
        Exception.__init__(self, *args)

class Task(object):
    def __init__(self, title, func, args = (), kwargs = {}, extraProgressCallback = None, extraErrorCallback = None, extraFinishCallback = None):
        self.title = title

        self.progressMax = 100
        self.progress = 0

        self.error = None
        self.finish = False

        self.suspended = False
        self.cancelled = False

        self.tid = 0

        self.monitor = None

        self.func = func

        self.args = ()
        self.kwargs = {}

        self.extraProgressCallback = extraProgressCallback
        self.extraErrorCallback = extraErrorCallback
        self.extraFinishCallback = extraFinishCallback

        self.extraProgressCallbackObj = {}
        self.extraErrorCallbackObj = {}
        self.extraFinishCallbackObj = {}

    def progressCallback(self, progress, progressMax, obj = {}):
        self.progress = progress
        self.progressMax = progressMax
        self.extraProgressCallbackObj = obj
        
        if self.cancelled:
            return 2
        elif self.suspended:
            return 1
        else:
            return 0

    def errorCallback(self, e, obj = {}):
        self.error = e
        self.extraErrorCallbackObj = obj

    def finishCallback(self, obj = {}):
        self.finish = True
        self.extraFinishCallbackObj = obj
        
    def start(self):
        self.tid = thread.start_new_thread(self.func, (), {
            "progressCallback" : self.progressCallback,
            "errorCallback" : self.errorCallback,
            "finishCallback" : self.finishCallback
        })

class Monitor(object):
    def exit(self):
        for task in self.tasks:
            if not task.error and not task.finish:
                raise Exception, unicode("还有未结束的任务")
        pass

    def __init__(self, listBox):
        self.tasks = []
        self.listBox = listBox
        self.changed = []

    def addSubscriber(self, func):
        self.changed.append(func)

    def update(self):
        for func in self.changed:
            func()

    def routine(self):
        i = 0

        if appuifw2.app.body == self.listBox:
            self.listBox.begin_update()
            for task in self.tasks:
                if task.error:
                    self.listBox[i].title = (isinstance(task.error, UserCancelled) and unicode("[取消]") or unicode("[错误]")) + u"[%d]" % task.tid + task.title + u"(%d/%d, %d%%)" % (task.progress, task.progressMax, task.progress * 100 / task.progressMax)
                    if task.extraErrorCallback:
                        task.extraErrorCallback(task.extraErrorCallbackObj)
                        task.extraErrorCallback = None  # 只能调用一次
                elif task.finish:
                    self.listBox[i].title = unicode("[完成]") + u"[%d]" % task.tid + task.title + u"(%d/%d, %d%%)" % (task.progress, task.progressMax, task.progress * 100 / task.progressMax)
                    if task.extraFinishCallback:
                        task.extraFinishCallback(task.extraFinishCallbackObj)
                        task.extraFinishCallback = None  # 只能调用一次
                else:
                    self.listBox[i].title = (task.suspended and u/"[暂停]" or u"") + u"[%d]" % task.tid + task.title + u"(%d/%d, %d%%)" % (task.progress, task.progressMax, task.progress * 100 / task.progressMax)
                    if task.extraProgressCallback:
                        task.extraProgressCallback(task.extraProgressCallbackObj)
                i += 1

            self.listBox.end_update()

        self.update()

    def newTask(self, task):
        pn = progressnotes.ProgressNote()
        pn.wait()

        self.tasks.insert(0, task)
        task.monitor = self
        task.start()
        self.listBox.insert(0, appuifw2.Item(unicode("新任务")))
        
        pn.finish()
        self.update()

    def suspend(self, index):
        if self.tasks[index].suspended:
            return

        self.tasks[index].suspended = True
        
    def resume(self, index):
        if not self.tasks[index].suspended:
            return

        self.tasks[index].suspended = False

    def cancel(self, index):
        self.tasks[index].cancelled = True
        

def itemMonitorStyleUpdaterWrapper():
    def itemMonitorStyleUpdater(item):
        running = 0
        finish = 0
        error = 0
        progress = 0
        progressMax = 0

        if item.__dict__.has_key("dataSource"):
            for task in item.dataSource.tasks:
                if task.finish:
                    finish += 1
                    running += 1
                    progress += task.progressMax
                    progressMax += task.progressMax
                elif task.error:
                    if not isinstance(task.error, UserCancelled):
                        error += 1
                else:
                    running += 1
                    progress += task.progress
                    progressMax += task.progressMax

        item.title = unicode("当前任务: %d/%d (%d%%) (失败: %d)") % (finish, running, (progress == 0 and progressMax == 0) and 100 or (progress * 100 / progressMax), error)

    return itemMonitorStyleUpdater