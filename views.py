from appuifw2_pymusic import View, Item, Menu, Listbox2, Text_display
import util
tryWrapper = None

class MenuCallbacks(object):
    pass

class ListboxCallbacks(object):
    pass

def listbox2Update(listbox2):
    for item in listbox2:
        item.update()

def itemUpdateGeneral(item):
    if item.__dict__.has_key("updater"):
        item.updater(item)

Item.update = itemUpdateGeneral

def itemDescriptionStyleUpdaterWrapper(convertFunction = lambda x:x):
    def itemDescriptionStyleUpdater(item):
        if item.__dict__.has_key("dataSource"):
            if item.dataSource:
                item.content = convertFunction(item.dataSource.getValue())

        item.title = item.desc + u": " + item.content

    return itemDescriptionStyleUpdater

def itemDurationPositionStyleUpdaterWrapper():
    def itemDurationPositionStyleUpdater(item):
        duration = u"00:00"
        position = u"00:00"
        stateText = unicode("播放器未载入")
        if item.__dict__.has_key("dataSource"):
            duration = util.colonTime(item.dataSource.duration() / 1000)
            position = util.colonTime(item.dataSource.currentPosition() / 1000)
            stateText = item.dataSource.stateText()

        item.title = u"[%s] %s/%s" % (stateText, position, duration)
    return itemDurationPositionStyleUpdater

class MainView(View):
    def PLAYER_TAB_MENU(self):
        return Menu(
            title = unicode("菜单"),
            items = [
                Item(unicode("播放列表"), callback = tryWrapper(MenuCallbacks.playlist, (self,))),
                Item(unicode("保存歌曲"), callback = tryWrapper(MenuCallbacks.saveSong, (self,))),
                Item(unicode("我的歌单"), callback = tryWrapper(MenuCallbacks.userPlaylists, (self,))),
                Item(unicode("根据ID播放歌单"), callback = tryWrapper(MenuCallbacks.playlistById, (self,))),
                Item(unicode("配置项"), callback = tryWrapper(MenuCallbacks.config, (self,))),
            ]
        )

    def LYRICS_TAB_MENU(self):
        return Menu(
            title = unicode("菜单"),
            items = [
            ]
        )

    def tabIndexCallback(self, tabIndex):
        self.body = [self.playerBody, self.lyricsBody][tabIndex]
        self.menu = [self.playerTabMenu, self.lyricTabMenu][tabIndex]
        
    def playerBodyListboxCallback(self):
        self.playerBody[self.playerBody.current()].callback()

    def update(self):
        listbox2Update(self.playerBody)

    def __init__(self):
        View.__init__(self)
        self.title = u"PyMusic"
        self.set_tabs([unicode("播放"), unicode("歌词")], self.tabIndexCallback)
        self.playerTabMenu = self.PLAYER_TAB_MENU()
        self.lyricTabMenu = self.LYRICS_TAB_MENU()

        self.iTasks = Item(unicode("当前任务"), callback = tryWrapper(ListboxCallbacks.tasks, (self,)))
        self.iLogin = Item(unicode("当前登录"), desc = unicode("当前登录"), content = unicode("未登录"), callback = tryWrapper(ListboxCallbacks.login, (self,)))
        self.iPlayPause = Item(unicode("[播放中]00:00/00:00"), callback = tryWrapper(ListboxCallbacks.playPause, (self,)))
        self.iSongName = Item(unicode("歌曲名"), desc = unicode("歌曲"), content = unicode("Song Name"), callback = tryWrapper(ListboxCallbacks.copy, (self,)))
        self.iArtistsName = Item(unicode("歌手名"), desc = unicode("歌手"), content = unicode("Aritists Name"), callback = tryWrapper(ListboxCallbacks.copy, (self,)))
        self.iAlbumName = Item(unicode("专辑名"), desc = unicode("专辑"), content = unicode("Album Name"), callback = tryWrapper(ListboxCallbacks.copy, (self,)))
        
        self.iNextSong = Item(unicode("下一曲"), desc = unicode("下一曲"), content = unicode("Next Song Name"), callback = tryWrapper(ListboxCallbacks.nextSong, (self,)))
        self.iPrevSong = Item(unicode("上一曲"), desc = unicode("上一曲"), content = unicode("Previous Song Name"), callback = tryWrapper(ListboxCallbacks.prevSong, (self,)))
        self.iVolume = Item(unicode("音量"), desc = unicode("音量"), content = unicode("0"), callback = tryWrapper(ListboxCallbacks.adjustVolume, (self,)))

        self.iCoverPic = Item(unicode("封面图片"), callback = tryWrapper(ListboxCallbacks.coverPic, (self,)))
        self.iSongId = Item(unicode("歌曲ID"), desc = unicode("歌曲ID"), content = unicode("Song ID"), callback = tryWrapper(ListboxCallbacks.copy, (self,)))
        self.iSongAlias = Item(unicode("歌曲别名"), desc = unicode("歌曲别名"), content = unicode("Song Alias"), callback = tryWrapper(ListboxCallbacks.copy, (self,)))
        self.iReason = Item(unicode("推荐理由"), desc = unicode("推荐理由"), content = unicode("Reason"), callback = tryWrapper(ListboxCallbacks.copy, (self,)))
        self.iLove = Item(unicode("喜欢/取消喜欢"), callback = tryWrapper(ListboxCallbacks.love, (self,)))

        self.iHotComment1 = Item(unicode("[热评]没有更多热评了哦"), callback = tryWrapper(ListboxCallbacks.hotComment, (self,)))
        self.iHotComment2 = Item(unicode("[热评]没有更多热评了哦"), callback = tryWrapper(ListboxCallbacks.hotComment, (self,)))
        self.iHotComment3 = Item(unicode("[热评]没有更多热评了哦"), callback = tryWrapper(ListboxCallbacks.hotComment, (self,)))
        self.iLatestComment1 = Item(unicode("[评论]没有更多评论了哦"), callback = tryWrapper(ListboxCallbacks.latestComment, (self,)))
        self.iLatestComment2 = Item(unicode("[评论]没有更多评论了哦"), callback = tryWrapper(ListboxCallbacks.latestComment, (self,)))
        self.iLatestComment3 = Item(unicode("[评论]没有更多评论了哦"), callback = tryWrapper(ListboxCallbacks.latestComment, (self,)))

        self.playerBody = Listbox2([
            self.iTasks,
            self.iLogin,
            self.iPlayPause,
            self.iSongName,
            self.iArtistsName,
            self.iAlbumName,
            
            self.iNextSong,
            self.iPrevSong,
            self.iVolume,

            self.iCoverPic,
            self.iSongId,
            self.iSongAlias,
            self.iReason,
            self.iLove,

            self.iHotComment1,
            self.iHotComment2,
            self.iHotComment3,
            self.iLatestComment1,
            self.iLatestComment2,
            self.iLatestComment3,
        ], select_callback = self.playerBodyListboxCallback)

        self.lyricsBody = Text_display(text=unicode("歌词"), skinned = True, scrollbar = True)

        self.activate_tab(0)
        self.tabIndexCallback(0)

        listbox2Update(self.playerBody)
        

class TasksView(View):
    def listboxCallback(self):
        item = self.menu.popup()
        if item:
            item.callback()

    def __init__(self):
        View.__init__(self)
        self.title = unicode("任务")
        self.body = Listbox2([], select_callback = self.listboxCallback)
        self.menu = Menu(
            title = unicode("菜单"),
            items = [
                Item(unicode("暂停/继续"), callback = tryWrapper(MenuCallbacks.tasksPauseCont, (self,))),
                Item(unicode("查看详细"), callback = tryWrapper(MenuCallbacks.tasksDetail, (self,))),
                Item(unicode("取消"), callback = tryWrapper(MenuCallbacks.tasksCancel, (self,))),
                Item(unicode("添加测试任务"), callback = tryWrapper(MenuCallbacks.tasksAdd, (self,))),
            ]
        )