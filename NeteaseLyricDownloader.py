from tkinter import *
import os
from tkinter import messagebox
from tkinter.filedialog import askdirectory
import psutil
import threading
from base_logger import getLogger
from lrc_module import Lrc
import time
import requests
import json
from urllib import parse
# import multiprocessing


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


# 独立的按照文件夹匹配歌词
class NeteaseLyricDownloader:
    class Network:
        def __init__(self):
            self.url_main = 'https://international.v1.hitokoto.cn/nm/'
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
                songs.append(NeteaseLyricDownloader.Song(song))
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
                summaries.append(NeteaseLyricDownloader.SongSummary(summary, reverse=reverse,
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
            playlist_summary = NeteaseLyricDownloader.PlaylistSummary(js['playlist'])
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
                playlists.append(NeteaseLyricDownloader.Playlist(playlist))
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
            return NeteaseLyricDownloader.Song(data)

        def __init__(self, data: dict):
            self.split_artist_char = ' '
            self.id = int(data['id'])
            self.name = data['name']
            self.artists = []
            for artist in data['artists']:
                self.artists.append(NeteaseLyricDownloader.Artist(artist))

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
                self.artists.append(NeteaseLyricDownloader.Artist({'name': artist}))
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
            self.creator = NeteaseLyricDownloader.Creator({'id': data['creator']['userId'],
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
            self.creator = NeteaseLyricDownloader.Creator({'id': data['creator']['userId'],
                                                           'name': data['creator']['nickname']})
            self.songs = []
            for track in data['tracks']:
                song = NeteaseLyricDownloader.Song.from_playlist(track)
                self.songs.append(song)

            self.img_url = data['coverImgUrl']
            self.count_track = data['trackCount']
            self.count_play = data['playCount']
            # self.count_book = data['bookCount']
            self.description = data['description']

        def __str__(self):
            return '%s - %s' % (self.name, str(self.creator))

    def __init__(self, root=None, default_dir: str='.'):
        self.root = root
        if self.root is None:
            self.root = Tk()
        self.title = "歌词适配"
        self.root.title(self.title)
        # 禁止最大化
        self.root.resizable(width=False, height=False)

        frame_left = Frame(self.root)
        frame_right = Frame(self.root)

        frame_filepath = Frame(frame_left)
        self.var_working_path = StringVar()
        Button(frame_filepath, text='选择文件夹', command=self.choose_dir).pack(side=LEFT)
        Entry(frame_filepath, textvariable=self.var_working_path).pack(side=RIGHT, fill=BOTH, expand=1)
        frame_filepath.grid(row=1, column=1)

        self.var_download = StringVar()
        self.listbox_download = Listbox(frame_left, listvariable=self.var_download, height=5)
        self.listbox_download.grid(row=3, column=1, sticky=W+E)

        frame_files = Frame(frame_left)
        self.var_files = StringVar()
        Listbox(frame_files, listvariable=self.var_files, height=5).pack(fill=X, expand=1)
        frame_files.grid(row=2, column=1, sticky=W+E)

        self.working_dir = default_dir

        self.frame_options = LabelFrame(frame_right, text='歌词设置')

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

        self.frame_options.grid(row=1, column=1)

        Button(frame_right, text='开始下载', command=self.start_download).grid(row=2, column=1, sticky=W+E)

        frame_left.pack(side=LEFT, fill=X, expand=1)
        frame_right.pack(side=RIGHT, fill=X, expand=1)

        self.files = []
        self.songs = []

        self.max_threads = 10
        self.max_retry = 4
        # self.threads = []
        self.download_queue = []
        self.downloading = []
        self.thread_manager = None
        self.lock = threading.Lock()

        self.thread_manager_fetch_id = None

        self.net_refresh_time = 0.5
        self.last_data = 0
        self.update_net_speed()

        self.update_logic()

        self.network = self.Network()

        self.running = False

        self.refresh_files()

    def start_download(self):
        if self.running is True:
            messagebox.showwarning('警告', '请等待下载完成')
            return
        self.download_queue = []
        self.downloading = []
        self.songs = []
        self.running = True
        self.download_manager_fetch_id(self.files)

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

    def choose_dir(self):
        path = askdirectory()
        if len(path) == 0:
            return
        self.working_dir = path
        self.var_working_path.set(path)
        self.refresh_files()

    def refresh_files(self):
        res = []
        li = os.listdir(self.working_dir)
        for file in li:
            if file.lower().endswith('.mp3'):
                file = file[:-len('.mp3')]
                res.append(file)
        if len(res) != 0:
            self.var_files.set(res)
        else:
            self.var_files.set(["文件列表", ])
        self.files = res
        self.songs = []
        self.var_working_path.set(self.working_dir)

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

    def fetch_id(self, key: str):
        logger.debug('fetch_id: %s' % key)
        songs = self.network.search_songs(key, 0, 1)
        if len(songs) == 0:
            logger.error('找不到歌曲 %s' % key)
        song = songs[0]
        self.lock.acquire()
        self.songs.append(song)
        self.lock.release()
        logger.debug('fetch_id DONE: %s' % key)
        if key in self.downloading:
            self.downloading.remove(key)

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
            for d in self.download_queue:
                if d.retry <= self.max_retry:
                    res.append(str(d))
                else:
                    logger.error('%s超过%s次重试次数，下载失败' % (str(d), self.max_retry))

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

    def download_manager_fetch_id(self, songs: list):
        # logger.warning('download_manager_fetch_id: %s' % str(songs))
        self.lock.acquire()
        self.download_queue.extend(songs)
        self.lock.release()
        if self.thread_manager_fetch_id is None:
            # logger.warning('Starting manager...' + ' %s' % len(self.download_queue))
            self.thread_manager_fetch_id = threading.Thread(target=self.manager_fetch_id)
            self.thread_manager_fetch_id.setDaemon(True)
            self.thread_manager_fetch_id.start()

    def manager_fetch_id(self):
        sleep_time = 0.2
        # logger.warning('Manager started...')
        while len(self.download_queue) > 0:
            # logger.debug('manager_fetch_id beat...')
            res = []
            for d in self.downloading:
                res.append(str(d))
            for d in self.download_queue:
                res.append(str(d))

            self.var_download.set(res)

            while len(threading.enumerate()) < self.max_threads:
                if len(self.download_queue) == 0:
                    break
                self.lock.acquire()
                top = self.download_queue[0]
                self.download_queue.remove(top)
                self.downloading.append(top)
                self.lock.release()
                t = threading.Thread(target=self.fetch_id, args=(top,))
                t.setDaemon(True)
                t.start()

            time.sleep(sleep_time)

        while len(self.downloading) > 0:
            # print(str(self.downloading))
            time.sleep(self.net_refresh_time)

        # logger.debug('manager_fetch_id DONE')

        self.download_queue = []
        # self.var_download.set('')
        self.thread_manager_fetch_id = None

        ids = []
        for song in self.songs:
            ids.append(song.id)
        # logger.info('fetch_id songs DONE: %s' % str(self.songs))
        # logger.info('fetch_id ids DONE: %s' % str(ids))
        summaries = self.network.get_summary(ids, reverse=self.var_lrc_reverse.get(),
                                             blend_lrc=self.var_download_translation.get(),
                                             trans_only=self.var_download_translation_only.get())
        self.download_manager(summaries)

    def download_lrc(self, summary):
        if summary is None:
            return
        if self.var_download_lrc.get() is False:
            return
        filename = summary.filename()
        filename = filename.split('.mp3')[0] + '.lrc'
        if self.var_insert_by_line.get() is True:
            summary.lrc = str(Lrc().blend_lines(str(summary.lrc)))
        if not os.path.exists(self.working_dir):
            os.mkdir(self.working_dir)
        if self.var_lrc_gbk.get() is True:
            with open(self.working_dir + '/' + filename, 'w', encoding='gbk', errors='ignore') as f:
                f.write(summary.lrc)
        else:
            with open(self.working_dir + '/' + filename, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(summary.lrc)

    def download(self, summary):
        logger.info("Start download: " + str(summary))
        # self.var_message.set('开始下载 %s' % (str(summary), ))
        self.download_lrc(summary)
        # self.download_mp3(summary)
        logger.info(str(summary) + ' Fin.')
        # self.var_message.set('下载完成 %s' % (str(summary), ))

        self.lock.acquire()
        for d in self.downloading:
            if d.name == summary.name:
                self.downloading.remove(d)
                break
        self.lock.release()

        if len(self.downloading) == 0 and len(self.download_queue) == 0:
            self.var_download.set(["下载全部完成", ])
            self.running = False

    def mainloop(self):
        self.root.mainloop()


if __name__ == '__main__':
    # multiprocessing.freeze_support()
    _lyric = NeteaseLyricDownloader(Tk())
    _lyric.mainloop()
