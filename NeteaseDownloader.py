import json
import os
import requests
from tkinter import *
from tkinter.filedialog import askdirectory
from tkinter import messagebox
import webbrowser
from base_logger import getLogger


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


# NeteaseDownwloader的主类
# 主要负责UI、网络
class NeteaseDownloader:
    class Settings:
        def __init__(self):
            self.download_folder = 'Download/'
            self.save_filename = 'settings.json'
            self.load()

        def load(self):
            if not os.path.exists('settings.json'):
                self.new()
            with open(self.save_filename, 'r') as f:
                js = json.loads(f.read())
                self.download_folder = js['download_folder']

        def save(self):
            with open(self.save_filename, 'w') as f:
                js = json.dumps({
                    'download_folder': self.download_folder
                })
                f.write(js)

        def new(self):
            with open(self.save_filename, 'w') as f:
                js = json.dumps({
                    'download_folder': 'Download/'
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
            self.url_summary = self.url_main + 'summary/%s?common=false&lyric=true&quick=false'

        @staticmethod
        def get_json(url: str):
            response = requests.get(url)
            if response.status_code != 200:
                raise ConnectionError
            # 这里可以抛出异常
            js = json.loads(response.text)
            return js

        def search_songs_summary(self, key: str):
            js = self.get_json(self.url_search_songs % (key, 0, 1))
            # 服务器错误
            if js['code'] != 200:
                raise ConnectionRefusedError
            return int(js['result']['songCount'])

        def search_songs(self, key: str, offset: int, limit: int):
            js = self.get_json(self.url_search_songs % (key, offset, limit))# 服务器错误
            # 服务器错误
            if js['code'] != 200:
                raise ConnectionRefusedError
            data = js['result']
            songs = []
            if 'songs' not in data:
                return songs
            for song in data['songs']:
                songs.append(NeteaseDownloader.Song(song))
            # print(json.dumps(js))
            return songs

    class Artist:
        def __init__(self, data: dict):
            self.id = int(data['id'])
            self.name = data['name']

        def __str__(self):
            return self.name

    class Song:
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
        self.entry = Entry(self.frame_search, textvariable=self.var_search)
        self.entry.grid(column=0, row=1)
        self.entry.bind('<Return>', self.search_new_songs)
        Button(self.frame_search, text='搜索单曲', command=self.search_new_songs).grid(column=1, row=1)
        Button(self.frame_search, text='搜索歌单', command=self.search_playlists).grid(column=2, row=1)

        # 辨认一下是显示的啥子内容
        self.DISP_MODE_SONGS = 'SONGS'
        self.DISP_MODE_PLAYLISTS = 'PLAYLISTS'
        self.disp_mode = self.DISP_MODE_SONGS

        # 搜索结果显示部分
        self.var_result = StringVar()
        self.listbox_result = Listbox(self.frame_result, listvariable=self.var_result, selectmode=EXTENDED)
        # self.listbox_result.bind('<Double-Button-1>', )
        self.listbox_result.pack(side=TOP, fill=X, expand=1)
        frame_select = Frame(self.frame_result)
        Button(frame_select, text='上一页', command=self.previous_page).grid(row=0, column=0)
        self.var_page = StringVar()
        self.var_page.set('第%s页' % str(self.offset // self.limit))
        Label(frame_select, textvariable=self.var_page).grid(row=0, column=1)
        Button(frame_select, text='下一页', command=self.next_page).grid(row=0, column=2)
        Label(frame_select, text='提示：按住Ctrl/拖动鼠标/按住Shift多选').grid(row=1, columnspan=5)
        frame_select.pack(side=BOTTOM)

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
        Button(self.frame_operate, textvariable=self.var_select_all, command=self.select_all).pack(side=LEFT)
        Button(self.frame_operate, text='下载选中歌曲', command=self.click_listbox).pack(side=RIGHT, fill=X, expand=YES)

        self.frame_search.grid(row=1, sticky=W+E)
        self.frame_result.grid(row=2, sticky=W+E)
        self.frame_options.grid(row=3, sticky=W+E)
        self.frame_operate.grid(row=4, sticky=W+E)

        # 生成菜单
        '''<菜单> 文件       工具        关于    退出
            设置下载目录 歌词下载工具    关于我
        '''
        menubar = Menu(self.root)
        menu_file = Menu(menubar, tearoff=0)
        menu_file.add_command(label='设置下载目录', command=self.menu_set_download_folder)
        menu_tools = Menu(menubar, tearoff=0)
        menu_tools.add_command(label='歌词下载工具', command=self.menu_tools_lyric)
        menu_about = Menu(menubar, tearoff=0)
        menu_about.add_command(label='关于我', command=self.menu_about)

        menubar.add_cascade(label='文件', menu=menu_file)
        menubar.add_cascade(label='工具', menu=menu_tools)
        menubar.add_cascade(label='关于', menu=menu_about)
        menubar.add_command(label='退出', command=self.root.quit)

        self.root.config(menu=menubar)

        self.var_search.set('茶太')

    def init_values(self):
        self.offset = 0
        self.total = 0
        self.update_values()

    def update_values(self):
        self.var_page.set('第%s/%s页' % (str(self.offset // self.limit + 1), str(self.total // self.limit + 1)))

    def menu_about(self):
        webbrowser.open('https://github.com/LanceLiang2018/NeteaseDownloader')

    def menu_tools_lyric(self):
        messagebox.showinfo('...', '还没做...')

    def menu_set_download_folder(self):
        path = askdirectory()
        if len(path) == 0:
            return
        self.settings.download_folder = path
        self.settings.save()
        messagebox.showinfo('成功', '下载文件夹成功设置为%s' % path)

    def search_new_songs(self, event=None):
        self.init_values()
        self.search_songs()

    def search_songs(self):
        self.disp_mode = self.DISP_MODE_SONGS
        if self.total == 0:
            self.total = self.network.search_songs_summary(self.var_search.get())
        logger.info('search(): ' + str((self.var_search.get(), self.offset, self.limit)))
        songs = self.network.search_songs(self.var_search.get(), self.offset, self.limit)
        songs_names = list(map(str, songs))
        self.var_result.set(songs_names)
        self.update_values()
        self.select_none()

    def search_playlists(self):
        print('search playlists:', self.var_search.get())
        self.disp_mode = self.DISP_MODE_PLAYLISTS

    def previous_page(self):
        if len(self.var_search.get()) == 0:
            return
        if self.total == 0:
            self.total = self.network.search_songs_summary(self.var_search.get())
        self.offset -= self.limit
        if self.offset < 0:
            self.offset = 0
            return
        self.search_songs()

    def next_page(self):
        if len(self.var_search.get()) == 0:
            return
        if self.total == 0:
            self.total = self.network.search_songs_summary(self.var_search.get())
        self.offset += self.limit
        if self.offset > self.total:
            self.offset = self.total
            return
        self.search_songs()

    def click_listbox(self, event=None):
        print(self.listbox_result.curselection())

    def select_all(self):
        self.listbox_result.selection_set(0, self.limit)

    def select_none(self):
        self.listbox_result.selection_clear(0, self.limit)

    def download_mp3(self, id: int=0, url: str=''):
        if id == 0 or url == '':
            return
        # TODO: 在这里下载MP3文件。（使用多线程，这个是子线程。）

    def new_download(self):
        pass

    def mainloop(self):
        self.root.mainloop()


if __name__ == '__main__':
    downloader = NeteaseDownloader(root=Tk())
    downloader.mainloop()
    # _net = NeteaseDownloader.Network()
    # songs = _net.search_songs('ACG', 6, 30)
    # for song in songs:
    #     print('search:', song)

