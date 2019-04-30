import json
import requests
from tkinter import *


# NeteaseDownwloader的主类
# 主要负责UI、网络
class NeteaseDownloader:
    def __init__(self, root=None):

        self.url_main = 'https://v1.hitokoto.cn/nm/'
        # 需要3个参数:key, offset, limit
        self.url_search_songs = self.url_main + 'search/%s?type=SONG&offset=%s&limit=%s'
        # 需要3个参数:key, offset, limit
        self.url_search_playlists = self.url_main + 'search/%s?type=PLAYLIST&offset=%s&limit=%s'
        # 需要1个参数:id
        self.url_playlist = self.url_main + 'playlist/%s'
        # 需要n个参数:id
        self.url_summary = self.url_main + 'summary/%s?common=false&lyric=true&quick=false'

        self.version = 'v0.01'
        if root is None:
            root = Tk()
        self.root = root
        self.root.title("网易云音乐下载器")
        # 禁止最大化
        self.root.resizable(width=False, height=False)

        # TODO: 加上显示字体修改。主要是搜索结果显示。
        # self.font =

        self.frame_search = Frame(self.root)
        self.frame_result = Frame(self.root)
        self.frame_options = LabelFrame(self.root, text='设置')
        self.frame_operate = Frame(self.root)

        # 搜索框部分
        self.var_search = StringVar()
        Entry(self.frame_search, textvariable=self.var_search).grid(column=0, row=1)
        Button(self.frame_search, text='搜索单曲', command=self.search_songs).grid(column=1, row=1)
        Button(self.frame_search, text='搜索歌单', command=self.search_playlists).grid(column=2, row=1)

        # 辨认一下是显示的啥子内容
        self.DISP_MODE_SONGS = 'SONGS'
        self.DISP_MODE_PLAYLISTS = 'PLAYLISTS'
        self.disp_mode = self.DISP_MODE_SONGS

        # 搜索结果显示部分
        self.var_result = StringVar()
        self.listbox_result = Listbox(self.frame_result, listvariable=self.var_result)
        self.listbox_result.pack(fill=BOTH, expand=1)

        # 设置部分
        self.var_download_lrc = BooleanVar()
        self.var_download_translation = BooleanVar()
        self.var_insert_by_line = BooleanVar()
        Checkbutton(self.frame_options, variable=self.var_download_lrc, text='是否下载lrc歌词').grid(row=1, column=0)
        Checkbutton(self.frame_options, variable=self.var_download_translation, text='是否下载翻译并嵌入lrc').grid(row=1, column=1)
        Checkbutton(self.frame_options, variable=self.var_insert_by_line, text='按行嵌入(MP3播放器使用)')\
            .grid(row=2, column=0, columnspan=2)

        # 操作部分
        self.var_select_all = StringVar()
        self.var_select_all.set('全选')
        Button(self.frame_operate, textvariable=self.var_select_all, command=None).pack()
        Button(self.frame_operate, text='下载选中歌曲', command=None).pack()

        self.frame_search.grid(row=1, sticky=W+E)
        self.frame_result.grid(row=2, sticky=W+E)
        self.frame_options.grid(row=3, sticky=W+E)
        self.frame_operate.grid(row=4, sticky=W+E)


    def search_songs(self):
        print('search songs:', self.var_search.get())
        self.disp_mode = self.DISP_MODE_SONGS

    def search_playlists(self):
        print('search playlists:', self.var_search.get())
        self.disp_mode = self.DISP_MODE_PLAYLISTS


    def mainloop(self):
        self.root.mainloop()


if __name__ == '__main__':
    downloader = NeteaseDownloader(root=Tk())
    downloader.mainloop()
