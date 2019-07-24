import json
import os
import requests
from tkinter import *
from tkinter.filedialog import askdirectory
from tkinter import messagebox
import webbrowser
from base_logger import getLogger
from lrc_module import Lrc
import threading
import time
import psutil
from urllib import parse
import multiprocessing
import platform


from NeteaseLyricDownloader import NeteaseLyricDownloader


logger = getLogger(__name__)


# 用来修正文件规范。
def safe_filename(filename: str):
    # 过长的文件名
    if len(filename) >= 255:
        extend = '.' + filename.split('.')[-1]
        filename = filename[:-len(extend)-1]
        filename = filename + '~' + extend
    # 不能出现的符号
    errors = r'\/:*?#"<>|'
    for c in errors:
        filename = filename.replace(c, '_')
    return filename


# NeteaseDownloader的主类
# 主要负责UI、网络
class NeteaseDownloader:
    class Settings:
        def __init__(self):
            self.download_folder = 'Download'
            self.save_filename = 'settings.json'
            self.max_threads = 10
            self.max_retry = 3
            self.refresh_time = 0.5
            self.load()

        def load(self):
            if not os.path.exists('settings.json'):
                self.new()
            with open(self.save_filename, 'r') as f:
                js = json.loads(f.read())
                self.download_folder = js['download_folder']
                self.max_threads = js['max_threads']
                self.max_retry = js['max_retry']
                self.refresh_time = js['refresh_time']
                if not os.path.exists(self.download_folder):
                    self.download_folder = 'Download'
                    self.save()

        def save(self):
            with open(self.save_filename, 'w') as f:
                js = json.dumps({
                    'download_folder': self.download_folder,
                    'max_threads': self.max_threads,
                    'max_retry': self.max_retry,
                    'refresh_time': self.refresh_time
                })
                f.write(js)

        def new(self):
            with open(self.save_filename, 'w') as f:
                js = json.dumps({
                    'download_folder': 'Download',
                    'max_threads': 10,
                    'max_retry': 3,
                    'refresh_time': 0.5
                })
                f.write(js)

    class Network:
        def __init__(self):
            self.url_main = 'https://v1.hitokoto.cn/nm/'
            # 需要3个参数:key, offset, limit
            self.url_search_songs = self.url_main + 'search/%s?type=SONG&offset=%s&limit=%s'
            # 需要3个参数:key, offset, limit
            self.url_search_playlists = self.url_main + 'search/%s?type=PLAYLIST&offset=%s&limit=%s'
            # 需要1个参数:id
            self.url_playlist = self.url_main + 'playlist/%s'
            # 需要n个参数:id
            self.url_summary = self.url_main + 'summary/%s?common=true&lyric=true&quick=false'

        @staticmethod
        def get_json(url: str):
            try:
                response = requests.get(url)
            except requests.exceptions.ConnectionError:
                raise ConnectionError
            if response.status_code != 200:
                raise ConnectionError
            # 这里可以抛出异常
            js = json.loads(response.text)
            return js

        def search_songs_summary(self, key: str):
            key = parse.quote(key.encode('utf8'))
            try:
                js = self.get_json(self.url_search_songs % (key, 0, 1))
            except ConnectionError:
                messagebox.showerror('错误', '连接错误! 检查网络...')
                return 0
            # 服务器错误
            if js['code'] != 200:
                messagebox.showerror('错误', '远端服务器拒绝连接...情稍后再试...')
                return 0
            return int(js['result']['songCount'])

        def search_songs(self, key: str, offset: int, limit: int):
            key = parse.quote(key.encode('utf8'))
            try:
                js = self.get_json(self.url_search_songs % (key, offset, limit))
            except ConnectionError:
                messagebox.showerror('错误', '连接错误! 检查网络...')
                return []
            # 服务器错误
            if js['code'] != 200:
                messagebox.showerror('错误', '远端服务器拒绝连接...情稍后再试...')
                return []
            data = js['result']
            songs = []
            if 'songs' not in data:
                return songs
            for song in data['songs']:
                songs.append(NeteaseDownloader.Song(song))
            # print(json.dumps(js))
            return songs

        def get_summary(self, ids: list, reverse=False, blend_lrc=True, trans_only=False):
            if len(ids) == 0:
                return []
            res = ''
            for i in ids:
                res = res + str(i) + ','
            res = res[:-1]
            # print(self.url_summary % (res, ))
            try:
                js = self.get_json(self.url_summary % (res,))
            except ConnectionError:
                messagebox.showerror('错误', '连接错误! 检查网络...')
                return []
            # 服务器错误
            if js['code'] != 200:
                messagebox.showerror('错误', '远端服务器拒绝连接...情稍后再试...')
                return []
            summaries = []
            # print(js)
            for summary in js['songs']:
                summaries.append(NeteaseDownloader.SongSummary(summary, reverse=reverse,
                                                               blend_lrc=blend_lrc, trans_only=trans_only))
            # print(summaries)
            return summaries

        def get_playlist_summary(self, pid: int):
            try:
                js = self.get_json(self.url_playlist % (pid,))
            except ConnectionError:
                messagebox.showerror('错误', '连接错误! 检查网络...')
                return []
            # 服务器错误
            if js['code'] != 200:
                messagebox.showerror('错误', '远端服务器拒绝连接...情稍后再试...')
                return []
            playlist_summary = NeteaseDownloader.PlaylistSummary(js['playlist'])
            return playlist_summary

        def search_playlists_summary(self, key: str):
            key = parse.quote(key.encode('utf8'))
            try:
                js = self.get_json(self.url_search_playlists % (key, 0, 1))
            except ConnectionError:
                messagebox.showerror('错误', '连接错误! 检查网络...')
                return 0
            # 服务器错误
            if js['code'] != 200:
                messagebox.showerror('错误', '远端服务器拒绝连接...请稍后再试...')
                return 0
            return int(js['result']['playlistCount'])

        def search_playlists(self, key: str, offset: int, limit: int):
            key = parse.quote(key.encode('utf8'))
            try:
                js = self.get_json(self.url_search_playlists % (key, offset, limit))
            except ConnectionError:
                messagebox.showerror('错误', '连接错误! 检查网络...')
                return []
            # 服务器错误
            if js['code'] != 200:
                messagebox.showerror('错误', '远端服务器拒绝连接...请稍后再试...')
                return []
            data = js['result']
            playlists = []
            if 'playlists' not in data:
                return playlists
            for playlist in data['playlists']:
                playlists.append(NeteaseDownloader.Playlist(playlist))
            # print(json.dumps(js))
            return playlists

    class Artist:
        def __init__(self, data: dict):
            if 'id' in data:
                self.id = int(data['id'])
            else:
                self.id = None
            self.name = data['name']

        def __str__(self):
            return self.name

    class Song:
        @staticmethod
        def from_playlist(data: dict):
            data['artists'] = data['ar']
            return NeteaseDownloader.Song(data)

        def __init__(self, data: dict):
            self.split_artist_char = ' '
            self.id = int(data['id'])
            self.name = data['name']
            self.artists = []
            for artist in data['artists']:
                self.artists.append(NeteaseDownloader.Artist(artist))

        def filename(self):
            artists = ''
            for artist in self.artists:
                artists = artists + artist.name + self.split_artist_char
            artists = artists[:-len(self.split_artist_char)]
            filename = '%s - %s.mp3' % (artists, self.name)
            return safe_filename(filename)

        def __str__(self):
            artists = ''
            for artist in self.artists:
                artists = artists + artist.name + self.split_artist_char
            artists = artists[:-len(self.split_artist_char)]
            return '%s - %s' % (artists, self.name)

    class SongSummary:
        def __init__(self, data: dict, reverse=False, blend_lrc=True, trans_only=False):
            self.split_artist_char = ' '
            self.id = data['id']
            if 'url' in data:
                self.url = data['url']
            else:
                self.url = None
            self.name = data['name']
            self.artists = []
            for artist in data['artists']:
                self.artists.append(NeteaseDownloader.Artist({'name': artist}))
            self.lrc_target = []
            if 'base' in data['lyric'] and data['lyric']['base'] is not None:
                self.lrc_base = Lrc.parse_lrc(data['lyric']['base'])
                self.lrc_target.append(self.lrc_base)
            else:
                self.lrc_base = None
            if 'translate' in data['lyric'] and data['lyric']['translate'] is not None:
                self.lrc_trans = Lrc.parse_lrc(data['lyric']['translate'])
                self.lrc_target.append(self.lrc_trans)
            else:
                self.lrc_trans = None
            self.lrc_target = list(map(str, self.lrc_target))
            if blend_lrc:
                self.lrc = str(Lrc.blend(self.lrc_target, reverse=reverse))
            elif trans_only:
                if self.lrc_trans is not None:
                    self.lrc = str(self.lrc_trans)
                else:
                    self.lrc = str(self.lrc_base)
            else:
                if self.lrc is not None:
                    self.lrc = str(self.lrc_base)
                else:
                    self.lrc = '''[00:00.000] 纯音乐，敬请聆听。'''

            self.retry = 0

        def filename(self):
            artists = ''
            for artist in self.artists:
                artists = artists + artist.name + self.split_artist_char
            artists = artists[:-len(self.split_artist_char)]
            filename = '%s - %s.mp3' % (artists, self.name)
            return safe_filename(filename)

        def __str__(self):
            artists = ''
            for artist in self.artists:
                artists = artists + artist.name + self.split_artist_char
            artists = artists[:-len(self.split_artist_char)]
            return '%s - %s' % (artists, self.name)

    class Creator(Artist):
        pass

    class Playlist:
        def __init__(self, data: dict):
            self.id = int(data['id'])
            self.name = data['name']
            self.img_url = data['coverImgUrl']
            self.creator = NeteaseDownloader.Creator({'id': data['creator']['userId'],
                                                      'name': data['creator']['nickname']})
            self.count_track = data['trackCount']
            self.count_play = data['playCount']
            # self.count_book = data['bookCount']
            self.description = data['description']

        def __str__(self):
            return "%s - %s" % (self.name, str(self.creator))

    class PlaylistSummary:
        def __init__(self, data: dict):
            self.id = int(data['id'])
            self.name = data['name']
            self.creator = NeteaseDownloader.Creator({'id': data['creator']['userId'],
                                                      'name': data['creator']['nickname']})
            self.songs = []
            for track in data['tracks']:
                song = NeteaseDownloader.Song.from_playlist(track)
                self.songs.append(song)

            self.img_url = data['coverImgUrl']
            self.count_track = data['trackCount']
            self.count_play = data['playCount']
            # self.count_book = data['bookCount']
            self.description = data['description']

        def __str__(self):
            return '%s - %s' % (self.name, str(self.creator))

    def __init__(self, root=None):
        self.version = 'v0.01'

        self.settings = self.Settings()
        if not os.path.exists(self.settings.download_folder):
            os.mkdir(self.settings.download_folder)

        self.network = self.Network()

        self.offset = 0
        self.total = 0
        self.limit = 30

        if root is None:
            root = Tk()
        self.root = root
        self.title = "网易云音乐下载器"
        self.root.title(self.title)
        # 禁止最大化
        self.root.resizable(width=False, height=False)

        # TODO: 加上显示字体修改。主要是搜索结果显示。
        # self.font =

        self.frame_left = Frame(self.root)
        self.frame_right = Frame(self.root)

        self.frame_search = Frame(self.frame_left)
        self.frame_result = Frame(self.frame_left)
        self.frame_options = LabelFrame(self.frame_right, text='歌词设置')
        self.frame_operate = Frame(self.frame_right)
        self.frame_download = Frame(self.frame_right)

        # 搜索框部分
        self.var_search = StringVar()
        self.entry = Entry(self.frame_search, textvariable=self.var_search)
        self.entry.grid(column=0, row=1)
        self.entry.bind('<Return>', self.search_new_songs)
        Button(self.frame_search, text='搜索单曲', command=self.search_new_songs).grid(column=1, row=1)
        Button(self.frame_search, text='搜索歌单', command=self.search_playlists).grid(column=2, row=1)

        # 辨认一下是显示的啥子内容
        self.DISP_MODE_SONGS = 'SONGS'
        self.DISP_MODE_PLAYLISTS = 'PLAYLISTS'
        self.DISP_MODE_PLAYLISTS_SONGS = 'PLAYLISTS_SONGS'
        self.disp_mode = self.DISP_MODE_SONGS

        # 搜索结果显示部分
        self.var_result = StringVar()
        self.listbox_result = Listbox(self.frame_result, listvariable=self.var_result, selectmode=EXTENDED)
        self.listbox_result.bind('<Double-Button-1>', self.click_listbox)
        self.listbox_result.pack(side=TOP, fill=X, expand=1)
        frame_select = Frame(self.frame_result)
        Button(frame_select, text='上一页', command=self.previous_page).grid(row=0, column=0)
        self.var_page = StringVar()
        self.var_page.set('第%s页' % str(self.offset // self.limit))
        Label(frame_select, textvariable=self.var_page).grid(row=0, column=1)
        Button(frame_select, text='下一页', command=self.next_page).grid(row=0, column=2)
        Label(frame_select, text='提示：按住Ctrl/拖动鼠标/按住Shift多选\n双击下载    下载进度→').grid(row=1, columnspan=5)
        self.var_message = StringVar()
        Entry(frame_select, textvariable=self.var_message).grid(row=2, columnspan=5, sticky=W+E)
        frame_select.pack(side=BOTTOM)

        # 设置部分
        self.var_download_lrc = BooleanVar()
        self.var_download_translation = BooleanVar()
        self.var_insert_by_line = BooleanVar()
        self.var_download_translation_only = BooleanVar()
        self.var_lrc_gbk = BooleanVar()
        self.var_lrc_reverse = BooleanVar()

        self.chk_download_lrc = Checkbutton(self.frame_options, variable=self.var_download_lrc, text='下载lrc歌词',
                                            command=self.update_logic)
        self.chk_download_translation = Checkbutton(self.frame_options, variable=self.var_download_translation,
                                                    text='    下载翻译并嵌入lrc', command=self.update_logic)
        self.chk_insert_by_line = Checkbutton(self.frame_options, variable=self.var_insert_by_line,
                                              text='        按行嵌入(MP3播放器使用)', command=self.update_logic)
        self.chk_download_translation_only = Checkbutton(self.frame_options,
                                                         variable=self.var_download_translation_only,
                                                         text='    只下载翻译(若无翻译则下载原文)', command=self.update_logic)
        self.chk_lrc_gbk = Checkbutton(self.frame_options, variable=self.var_lrc_gbk, text='    保存为GBK格式')
        self.chk_lrc_reverse = Checkbutton(self.frame_options, variable=self.var_lrc_reverse, text='    中文在原文前')

        self.chk_download_lrc.grid(row=0, column=0, sticky=W)
        self.chk_download_translation.grid(row=1, column=0, sticky=W)
        self.chk_insert_by_line.grid(row=2, column=0, sticky=W)
        self.chk_download_translation_only.grid(row=3, column=0, sticky=W)
        self.chk_lrc_gbk.grid(row=4, column=0, sticky=W)
        self.chk_lrc_reverse.grid(row=5, column=0, sticky=W)

        self.var_download_lrc.set(True)
        self.var_download_translation_only.set(False)
        self.var_download_translation.set(True)
        self.var_insert_by_line.set(False)
        self.var_lrc_gbk.set(True)
        self.var_lrc_reverse.set(False)

        self.update_logic()

        # 操作部分
        self.var_select_all = StringVar()
        self.var_select_all.set('全选')
        Button(self.frame_operate, textvariable=self.var_select_all, command=self.select_all).pack(side=LEFT)
        Button(self.frame_operate, text='下载选中歌曲', command=self.click_listbox).pack(side=RIGHT, fill=X, expand=YES)

        # 下载管理部分
        self.var_download = StringVar()
        self.listbox_download = Listbox(self.frame_download, listvariable=self.var_download, height=5)
        self.listbox_download.pack(fill=X)

        self.frame_search.grid(row=1, sticky=W+E)
        self.frame_result.grid(row=2, sticky=W+E)
        self.frame_options.grid(row=3, sticky=W+E)
        self.frame_operate.grid(row=4, sticky=W+E)
        self.frame_download.grid(row=5, sticky=W+E)

        self.frame_left.pack(side=LEFT)
        self.frame_right.pack(side=RIGHT)

        # 生成菜单
        '''<菜单> 文件     设置      工具        关于    退出
            设置下载目录          歌词下载工具    关于我
        '''
        menubar = Menu(self.root)
        menu_file = Menu(menubar, tearoff=0)
        menu_file.add_command(label='设置下载目录', command=self.menu_set_download_folder)
        menu_tools = Menu(menubar, tearoff=0)
        menu_tools.add_command(label='歌词下载工具', command=self.menu_tools_lyric)
        menu_about = Menu(menubar, tearoff=0)
        menu_about.add_command(label='关于我', command=self.menu_about)

        menubar.add_cascade(label='文件', menu=menu_file)
        menubar.add_command(label='设置', command=self.setup)
        menubar.add_cascade(label='工具', menu=menu_tools)
        menubar.add_cascade(label='关于', menu=menu_about)
        menubar.add_command(label='退出', command=self.root.quit)

        self.root.config(menu=menubar)

        self.var_search.set('茶太')
        self.songs = []
        self.playlists = []
        self.max_threads = self.settings.max_threads
        self.max_retry = self.settings.max_retry
        # self.threads = []
        self.download_queue = []
        self.downloading = []
        self.thread_manager = None
        self.lock = threading.Lock()

        self.last_data = 0
        self.net_refresh_time = self.settings.refresh_time

        self.update_net_speed()

        self.setup_var_max_threads = StringVar()
        self.setup_var_max_retry = StringVar()
        self.setup_var_refresh_time = StringVar()

        self.top = None

    def setup(self):
        top = Toplevel(self.root)
        self.top = top
        if platform.system() == 'Windows':
            top.attributes("-toolwindow", 1)
            top.attributes("-topmost", 1)
        top.resizable(width=False, height=False)
        top.title("设置")
        # top.overrideredirect(True)
        # self.root.iconify()

        frame = Frame(top)

        self.setup_var_max_threads.set(str(self.max_threads))
        self.setup_var_max_retry.set(str(self.max_retry))
        self.setup_var_refresh_time.set(str(self.net_refresh_time))

        Label(frame, text='下载线程数').grid(row=1, column=1)
        Entry(frame, textvariable=self.setup_var_max_threads).grid(row=1, column=2)
        Label(frame, text='重试次数').grid(row=2, column=1)
        Entry(frame, textvariable=self.setup_var_max_retry).grid(row=2, column=2)
        Label(frame, text='网速刷新时间').grid(row=3, column=1)
        Entry(frame, textvariable=self.setup_var_refresh_time).grid(row=3, column=2)

        frame.pack(side=TOP)
        Button(top, text='保存设置', command=self.setup_confirm).pack(side=BOTTOM, fill=X, expand=1)

        top.mainloop()

    def setup_confirm(self):
        try:
            self.max_threads = int(self.setup_var_max_threads.get())
            self.max_retry = int(self.setup_var_max_retry.get())
            self.net_refresh_time = float(self.setup_var_refresh_time.get())
        except ValueError:
            messagebox.showerror('错误', '参数设置错误!')
            self.top.destroy()
        self.settings.max_threads = self.max_threads
        self.settings.max_retry = self.max_retry
        self.settings.refresh_time = self.net_refresh_time
        self.settings.save()
        self.top.destroy()

    def init_values(self):
        self.offset = 0
        self.total = 0
        self.update_values()

    def update_values(self):
        if self.disp_mode == self.DISP_MODE_SONGS or self.disp_mode == self.DISP_MODE_PLAYLISTS:
            string = '第%s/%s页' % (str(self.offset // self.limit + 1), str(self.total // self.limit + 1))
        else:
            string = '第1/1页'
        self.var_page.set(string)

    def menu_about(self):
        webbrowser.open('https://github.com/LanceLiang2018/NeteaseDownloader')

    def menu_tools_lyric(self):
        if platform.system() == 'Windows':
            p = multiprocessing.Process(target=start_lyric_downloader, args=(self.settings.download_folder, ))
            p.start()
        elif platform.system() == 'Linux':
            # t = threading.Thread(target=start_lyric_downloader, args=(self.settings.download_folder, ))
            # t.start()
            if not os.path.exists('NeteaseLyricDownloader'):
                messagebox.showerror('错误', '找不到NeteaseLyricDownloader文件。请下载相关文件。')
                return
            code = os.system('./NeteaseLyricDownloader &')
            # code = os.system('python3 NeteaseLyricDownloader.py &')
            if code != 0:
                messagebox.showerror('错误', '运行程序失败。错误码 %s' % code)
            return

    def menu_set_download_folder(self):
        path = askdirectory()
        if len(path) == 0:
            return
        self.settings.download_folder = path
        self.settings.save()
        messagebox.showinfo('成功', '下载文件夹成功设置为%s' % path)

    # 更新网速
    def update_net_speed(self):
        if self.last_data == 0:
            self.last_data = psutil.net_io_counters(pernic=False).bytes_recv + \
                             psutil.net_io_counters(pernic=False).bytes_sent
        size = psutil.net_io_counters(pernic=False).bytes_recv + psutil.net_io_counters(pernic=False).bytes_sent
        size -= self.last_data
        kbs = (size / 1024) / self.net_refresh_time
        unit = 'KB'
        if kbs > 1024:
            kbs /= 1024
            unit = 'MB'
        self.root.title("%s - %s进程 - %0.2f%s/s" % (self.title, len(threading.enumerate()), kbs, unit))
        self.last_data = psutil.net_io_counters(pernic=False).bytes_recv
        self.last_data += psutil.net_io_counters(pernic=False).bytes_sent
        self.root.after(int(self.net_refresh_time * 1000), self.update_net_speed)

    # 更新选项逻辑
    def update_logic(self):
        if self.var_download_lrc.get() is False:
            self.var_download_translation.set(False)
            self.var_download_translation_only.set(False)
            self.var_insert_by_line.set(False)
            self.var_lrc_gbk.set(False)
            self.chk_download_translation.configure(state='disabled')
            self.chk_download_translation_only.configure(state='disabled')
            self.chk_insert_by_line.configure(state='disabled')
            self.chk_lrc_gbk.configure(state='disabled')
        else:
            self.chk_download_translation.configure(state='normal')
            self.chk_download_translation_only.configure(state='normal')
            self.chk_insert_by_line.configure(state='normal')
            self.chk_lrc_gbk.configure(state='normal')

        if self.var_download_translation.get() is True:
            self.var_download_translation_only.set(False)
        if self.var_download_translation_only.get() is True:
            self.var_download_translation.set(False)

        if self.var_download_translation.get() is False:
            self.var_insert_by_line.set(False)
            self.chk_insert_by_line.configure(state='disabled')

    def search_new_songs(self, event=None):
        self.init_values()
        self.search_songs()

    def search_songs(self):
        self.disp_mode = self.DISP_MODE_SONGS
        if self.total == 0:
            self.total = self.network.search_songs_summary(self.var_search.get())
        logger.info('search_songs(): ' + str((self.var_search.get(), self.offset, self.limit)))
        self.var_message.set('搜索: %s' % self.var_search.get())

        songs = self.network.search_songs(self.var_search.get(), self.offset, self.limit)
        self.songs = songs
        songs_names = list(map(str, songs))
        self.var_result.set(songs_names)
        self.update_values()
        self.select_none()

    def search_new_playlists(self, event=None):
        self.init_values()
        self.search_playlists()

    def search_playlists(self):
        self.disp_mode = self.DISP_MODE_PLAYLISTS
        if self.total == 0:
            self.total = self.network.search_playlists_summary(self.var_search.get())
        self.var_message.set('搜索歌单: %s' % self.var_search.get())
        logger.info('search_playlists(): ' + str((self.var_search.get(), self.offset, self.limit)))
        playlists = self.network.search_playlists(self.var_search.get(), self.offset, self.limit)
        self.playlists = playlists
        playlists_names = list(map(lambda x: "[%s] %s" % (x.count_track, str(x)), playlists))
        self.var_result.set(playlists_names)
        self.update_values()
        self.select_none()

    def previous_page(self):
        if self.disp_mode == self.DISP_MODE_SONGS:
            if len(self.var_search.get()) == 0:
                return
            if self.total == 0:
                self.total = self.network.search_songs_summary(self.var_search.get())
            self.offset -= self.limit
            if self.offset < 0:
                self.offset = 0
                return
            self.search_songs()
        if self.disp_mode == self.DISP_MODE_PLAYLISTS_SONGS:
            return
        if self.disp_mode == self.DISP_MODE_PLAYLISTS:
            if len(self.var_search.get()) == 0:
                return
            if self.total == 0:
                self.total = self.network.search_playlists_summary(self.var_search.get())
            self.offset -= self.limit
            if self.offset < 0:
                self.offset = 0
                return
            self.search_playlists()

    def next_page(self):
        if self.disp_mode == self.DISP_MODE_SONGS:
            if len(self.var_search.get()) == 0:
                return
            if self.total == 0:
                self.total = self.network.search_songs_summary(self.var_search.get())
            self.offset += self.limit
            if self.offset > self.total:
                self.offset = self.total
                return
            self.search_songs()
        if self.disp_mode == self.DISP_MODE_PLAYLISTS_SONGS:
            return
        if self.disp_mode == self.DISP_MODE_PLAYLISTS:
            if len(self.var_search.get()) == 0:
                return
            if self.total == 0:
                self.total = self.network.search_playlists_summary(self.var_search.get())
            self.offset += self.limit
            if self.offset > self.total:
                self.offset = self.total
                return
            self.search_playlists()

    def click_listbox(self, event=None):
        selected = self.listbox_result.curselection()
        if self.disp_mode == self.DISP_MODE_SONGS or self.disp_mode == self.DISP_MODE_PLAYLISTS_SONGS:
            ids = []
            if len(selected) == 0:
                return
            for s in selected:
                ids.append(self.songs[s].id)
            summaries = self.network.get_summary(ids, reverse=self.var_lrc_reverse.get(),
                                                 blend_lrc=self.var_download_translation.get(),
                                                 trans_only=self.var_download_translation_only.get())
            self.download_manager(summaries)

        if self.disp_mode == self.DISP_MODE_PLAYLISTS:
            # 只接受一个歌单
            if len(selected) != 1:
                return
            pid = self.playlists[selected[0]].id
            playlist_summary = self.network.get_playlist_summary(pid)
            # print(str(playlist_summary))

            # 切换到显示歌单内容
            self.disp_mode = self.DISP_MODE_PLAYLISTS_SONGS
            self.songs = playlist_summary.songs
            songs_names = list(map(str, playlist_summary.songs))
            self.var_result.set(songs_names)
            self.update_values()
            self.select_none()

    def select_all(self):
        self.listbox_result.selection_set(0, self.limit)

    def select_none(self):
        self.listbox_result.selection_clear(0, self.limit)

    def download_manager(self, summaries: list):
        self.lock.acquire()
        # for summary in summaries:
        #     t = threading.Thread(target=self.download, args=(summary, ))
        #     t.setDaemon(True)
        #     self.threads.append(t)
        self.download_queue.extend(summaries)
        # print(self.download_queue)
        self.lock.release()
        if self.thread_manager is None:
            # logger.warning('Starting manager...' + ' %s' % len(self.download_queue))
            self.thread_manager = threading.Thread(target=self.manager)
            self.thread_manager.setDaemon(True)
            self.thread_manager.start()

    def manager(self):
        sleep_time = 0.2
        # logger.warning('Manager started...')
        while len(self.download_queue) > 0:
            # logger.info('Manager beats...')
            res = []
            for d in self.downloading:
                if d.retry <= self.max_retry:
                    res.append(str(d))
                else:
                    logger.error('%s超过%s次重试次数，下载失败' % (str(d), self.max_retry))
                    self.var_message.set('%s超过%s次重试次数，下载失败' % (str(d), self.max_retry))
            for d in self.download_queue:
                if d.retry <= self.max_retry:
                    res.append(str(d))
                else:
                    logger.error('%s超过%s次重试次数，下载失败' % (str(d), self.max_retry))
                    self.var_message.set('%s超过%s次重试次数，下载失败' % (str(d), self.max_retry))

            self.var_download.set(res)

            while len(threading.enumerate()) < self.max_threads:
                if len(self.download_queue) == 0:
                    break
                self.lock.acquire()
                top = self.download_queue[0]
                self.download_queue.remove(top)
                self.downloading.append(top)
                self.lock.release()
                t = threading.Thread(target=self.download, args=(top,))
                t.setDaemon(True)
                t.start()

            time.sleep(sleep_time)

        self.download_queue = []
        # self.var_download.set('')
        self.thread_manager = None

    def download_mp3(self, summary):
        if summary is None:
            return
        # 在这里下载MP3文件。（使用多线程，这个是子线程。）
        logger.info('Download ' + str(summary) + ' ' + str(summary.id) + ' ' + summary.filename())
        filepath = self.settings.download_folder + '/' + summary.filename()
        if os.path.exists(filepath):
            # 大于2MB则判断文件存在
            if os.path.getsize(filepath) / 1024 / 1024 > 2:
                logger.info(str(summary) + ' Exists.')
                self.var_message.set("%s文件已经存在" % (str(summary)))
                return
        try:
            response = requests.get(summary.url)
        except requests.exceptions.ConnectTimeout:
            # 超时就重试
            summary.retry += 1
            self.lock.acquire()
            self.download_queue.append(summary)
            self.lock.release()
            return
        if not os.path.exists(self.settings.download_folder):
            os.mkdir(self.settings.download_folder)
        with open(filepath, 'wb') as f:
            f.write(response.content)

    def download_lrc(self, summary):
        if summary is None:
            return
        if self.var_download_lrc.get() is False:
            return
        filename = summary.filename()
        filename = filename.split('.mp3')[0] + '.lrc'
        if self.var_insert_by_line.get() is True:
            summary.lrc = str(Lrc().blend_lines(str(summary.lrc)))
        if not os.path.exists(self.settings.download_folder):
            os.mkdir(self.settings.download_folder)
        if self.var_lrc_gbk.get() is True:
            with open(self.settings.download_folder + '/' + filename, 'w', encoding='gbk', errors='ignore') as f:
                f.write(summary.lrc)
        else:
            with open(self.settings.download_folder + '/' + filename, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(summary.lrc)

    def download(self, summary):
        logger.info("Start download: " + str(summary))
        self.var_message.set('开始下载 %s' % (str(summary), ))
        self.download_lrc(summary)
        self.download_mp3(summary)
        logger.info(str(summary) + ' Fin.')
        self.var_message.set('下载完成 %s' % (str(summary), ))

        self.lock.acquire()
        for d in self.downloading:
            if d.name == summary.name:
                self.downloading.remove(d)
                break
        self.lock.release()

        if len(self.downloading) == 0 and len(self.download_queue) == 0:
            self.var_download.set(["下载全部完成", ])

    def mainloop(self):
        self.root.mainloop()


def start_lyric_downloader(working_dir: str):
    # lyric = NeteaseLyricDownloader(root=Tk(), default_dir=working_dir)
    lyric = NeteaseLyricDownloader(root=None, default_dir=working_dir)
    lyric.mainloop()


if __name__ == '__main__':
    # multiprocessing.freeze_support()
    _downloader = NeteaseDownloader(root=Tk())
    _downloader.mainloop()

