## 网易云音乐下载器

做一个`电脑版`的。`手机端`请用[这里](https://lance-latina-debug.herokuapp.com/update)

### 使用的API

    https://github.com/a632079/teng-koa
    http://v1.hitokoto.cn/nm/
    https://international.v1.hitokoto.cn/nm/

#### UI设计

<菜单> 文件       工具     退出     关于

  设置下载目录 歌词下载工具         关于我


[搜索框]   |搜索单曲|搜索歌单|

[这个框用来显示搜索结果(歌单+单曲)]

(一些按钮：|上一页|下一页|)

(提示：点击选定歌曲或者双击下载单曲)

(CheckBox：是否下载lrc歌词)

(CheckBox：是否下载翻译并嵌入lrc)

(CheckBox：按行嵌入)

|全选|下载选中歌曲|

## 功能

 - 下载网易云的歌曲
 - 下载歌词
 - 重新整理歌词
 - 批量匹配歌词
 - 多线程下载
 - 下载网速显示~~(多线程下载超快的)~~

## 使用

### 下载工具

![图片](https://github.com/LanceLiang2018/NeteaseDownloader/raw/master/images/first.png)

![图片](https://github.com/LanceLiang2018/NeteaseDownloader/raw/master/images/downloading.png)

![图片](https://github.com/LanceLiang2018/NeteaseDownloader/raw/master/images/done.png)

 - 搜索单曲后选择曲目下载
 - 搜索歌单后选择曲目下载
 - 选择歌词选项
 - 选择文件下载目录
 - 在菜单栏点击设置 设置线程数量 等
 - 在菜单栏的工具下进入歌词匹配工具
 
### 歌词匹配工具
 
![图片](https://github.com/LanceLiang2018/NeteaseDownloader/raw/master/images/lyric.png)
 
 - 选择文件夹，自动列出文件夹下的MP3文件
 - 选择歌词选项
 - 开始下载

## BUGS

 - 歌词选项的逻辑不对，点击了`下载翻译`就没法点击`只下载翻译`。详见`逻辑更新`函数。
 
```python
# 更新选项逻辑
def update_logic(self):...
```

 - 线程数量把主线程也算进去了
 - 搜索内容只有到第二页(offset == 60)。是API的问题。

## TODO

 - 修复BUG~~(不是很想修)~~
