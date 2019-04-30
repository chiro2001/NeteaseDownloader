import math


class Lrc:
    class Line:
        def __init__(self, label: str=None, time: float=0.0, string: str=''):
            self.time = time
            self.string = string
            self.label = label

        def __str__(self):
            if self.label is not None:
                return '[%s]%s' % (self.label, self.string)
            return '[%s]%s' % (Lrc.int2str(self.time), self.string)

    class Data:
        def __init__(self):
            self.lines = []

        def sort(self):
            self.lines.sort(key=lambda x: x.time)

        def __str__(self):
            result = ''
            for line in self.lines:
                result = result + str(line) + '\n'
            return result

    def __init__(self, split_char: str=' - '):
        self.split_char = split_char

    # 解析字符串时间 -> 秒数
    # 遇到异常抛出
    @staticmethod
    def str2int(s: str):
        if len(s.split(':')) < 2:
            raise ValueError
        minn = s.split(':')[0]
        sec = s.split(':')[1]
        try:
            res = 60 * int(minn) + float(sec)
        except:
            raise ValueError
        return res

    # 秒数 -> 字符串时间
    @staticmethod
    def int2str(n: float):
        n = float(n)
        minn = int(n // 60)
        sec = math.floor(n - minn * 60)
        other = n - minn * 60 - sec
        res = "%02d:%02d.%s" % (minn, sec, str("%02d0" % int(other * 100)))
        return res

    @staticmethod
    def parse_line(line: str):
        if not line.startswith('['):
            raise ValueError
        if ']' not in line:
            raise ValueError
        # 我猜应该不会出现[xxx][yyyy]这样的歌词了...
        second = line.split('[')[-1].split(']')[0]
        string = line.split('[')[-1].split(']')[-1]
        # 尝试转换，转换失败就留着原来的格式。
        try:
            second = Lrc.str2int(second)
        except ValueError:
            return Lrc.Line(label=second, string=string)
        return Lrc.Line(time=second, string=string)

    @staticmethod
    def parse_lrc(lrc: str):
        lines = lrc.split('\n')
        # 删去空行。
        for i in lines:
            if len(i) == 0:
                lines.remove(i)

        data = Lrc.Data()
        for line in lines:
            data.lines.append(Lrc.parse_line(line))

        # 排序
        data.sort()

        return data

    # 合并多个lrc。主要是翻译。
    # 在排列前面的会显示在前面。
    @staticmethod
    def blend(lrcs_str: list, reverse=False):
        if reverse:
            lrcs_str.reverse()
        lrcs = []
        for lrc_str in lrcs_str:
            lrcs.append(Lrc.parse_lrc(lrc_str))
        data = Lrc.Data()
        for lrc in lrcs:
            data.lines.extend(lrc.lines)
        data.sort()
        return data

    # 按行合并。
    # 用于mp3显示不了同一时间的歌词和翻译时的处理。
    def blend_lines(self, lrc_str: str):
        lrc = Lrc.parse_lrc(lrc_str)
        data = Lrc.Data()
        index = 0
        while index < len(lrc.lines):
            i = 1
            while i + index < len(lrc.lines) and lrc.lines[index].time == lrc.lines[index + i].time and lrc.lines[index].label is None:
                i += 1
            # print(list(map(lambda x: str(x), lrc.lines[index:index+i])))
            got_lines = lrc.lines[index:index+i]
            if len(got_lines) > 1 or (len(got_lines) == 1 and got_lines[0].label is None):
                form_line = ''
                for got in got_lines:
                    form_line = form_line + got.string + self.split_char
                form_line = form_line[:-len(self.split_char)]
                data.lines.append(Lrc.Line(time=got_lines[0].time, string=form_line))
            if len(got_lines) == 1 and got_lines[0].label is not None:
                data.lines.append(got_lines[0])
            index += i
        data.sort()
        return data



lrc_test = "[00:00.000] 作曲 : 赤髪\n[00:01.000] 作词 : 赤髪\n[00:23.34]遠く 遠く 記憶の奥に沈めた\n[00:34.04]思い出を 掬い（すくい）上げる\n[00:44.88]拙い（つたない） 会話 慣れない姿に頬を染め\n[00:55.74]賑わう（にぎわう）方へ ゆっくりと歩くんだ\n[01:06.82]終わる夕暮れ 空を見上げ 近づく影\n[01:17.71]ほら ほら 手が触れ合って 気づけば\n[01:26.98]不器用に握った\n[01:33.71]高く空に 打ち上がり 咲いた\n[01:43.51]一瞬だけ キミを照らして 消えるんだ\n[01:56.33]嬉しそうにはしゃぐ横顔に\n[02:06.33]見惚れ焼きつく 記憶をぎゅっと\n[02:11.92]いつまでも 強く 強く この手握っていて\n[02:29.87]ひとつ ひとつ 描かれた歴史の欠片を\n[02:40.48]記憶へ沈め 抱きしめて 眠った\n[02:51.04]通り雨を 追いかけるように キミが現れ（あらわれ）\n[03:02.10]傘に入れてあげるよ 微笑み 頬を伝う雨\n[03:18.58]すべて世界がスローに写る（うつる）程\n[03:28.16]キミの言葉は 私への愛で満ちていて\n[03:39.95]抗う隙さえ与える間もなく\n[03:49.95]触れる息は 心もとなく 弱って\n[03:57.09]薄く 薄く キミが消えていく\n[04:06.74]キミが消えていく\n[04:12.59]流れる雨\n[04:22.74]止めどなく溢れ\n[04:41.55]土砂降りの雨はキミを通りぬけ\n[04:51.35]遠くの空は 嘘みたいに晴れていく\n[05:02.95]この世界がすべて書き換わり\n[05:13.10]キミの存在 記憶 すべて 消し去っても\n[05:20.70]消せない 消せない はしゃぐ笑顔\n[05:25.46]消せはしない キミを想っている\n[05:31.90]\n"
lrc_trans = "[by:希Home-0869]\n[00:23.34]沉浸在遥远的记忆深处\n[00:34.04]从其中掬出一捧回忆\n[00:44.88]笨拙的交谈  因还未能习惯的姿态  双颊染上绯红\n[00:55.74]慢步走向那热闹的地方\n[01:06.82]抬头仰望夕阳   渐渐靠近的身影\n[01:17.71]你看  发现触碰到一起的双手\n[01:26.98]没志气的握紧\n[01:33.71]高空中升起盛开的烟火\n[01:43.51]瞬间照亮你的脸庞又转瞬消失不见\n[01:56.33]看上去很开心欢喜的你的侧脸\n[02:06.33]恍惚的注视着你  将这记忆铭记于心\n[02:11.92]无论何时都会紧紧握住这双手\n[02:29.87]一片一片     将描绘往昔的断片\n[02:40.48]沉入记忆  拥紧而眠\n[02:51.04]想要追赶阵雨时  你悄然出现\n[03:02.10]我来给你撑伞吧   雨水沿着笑脸低落\n[03:18.58]整个世界仿佛都缓慢下来\n[03:28.16]你的话语中充满了对我的爱\n[03:39.95]连反抗的时间都不曾给过我\n[03:49.95]相触的气息  心跳微弱\n[03:57.09]逐渐稀薄   你就这样消失\n[04:06.74]你就这样消失\n[04:12.59]流淌的雨水\n[04:22.74]不停的流下\n[04:41.55]倾盆大雨淋透你的身体\n[04:51.35]遥远的天空  不真实的开始放晴\n[05:02.95]这个世界已经重新书写\n[05:13.10]即使你的存在 你的记忆 全部消逝\n[05:20.70]欢笑的笑颜  永远不会消失\n[05:25.46]对你的想念  永远不会消失\n"


if __name__ == '__main__':
    # lrc = Lrc()
    lrc = str(Lrc.blend([lrc_test, lrc_trans], reverse=False))
    # print(lrc)
    mlrc = Lrc()
    blend = mlrc.blend_lines(lrc)
    print(blend)
