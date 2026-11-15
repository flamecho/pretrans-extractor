#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Live x Evil 熱砂のプロメテウス — KiriKiri XP3 / KAG3 全文本提取器

源链：PE+RAR5 SFX → CloneCD(raw2352 MODE1) → Inno Setup 5.1.2 → app/data.xp3
容器：flag=0 明文索引（u64 index_off @0x0B, u64 body_size @idx+1），
      segm={u32 flags; u64 off; u64 orig; u64 stored}，orig==stored ⇒ 无 zlib / 无加密。
脚本：scenario/*.ks 全 cp932 明文 + CRLF，KAG3 `@command` 简写。

★ 断框全部为代码级 L0（system/MainWindow.tjs + scenario/sys_macro.ks）：
  @p        -> p:4899 showPageBreak() -> conductor.wait(click)      收框（一次点击）
  @r        -> r:4772 processReturn()                              框内改行＝合并
  @cm/@ct/@er -> 4929/4920/4938 clearMessageLayers()                清屏＝收行点
  @s        -> 5032                                                 実行停止＝收段
  @l        -> 4893 存在但全库 0 次                                ⇒ 单版
  @voice    -> sys_macro.ks 宏体末尾 @p+@cm                        一次调用＝一框
               台词在 word= 属性；宏体 @emb 补 「」/『』（pron=sec）
  @select_item -> text= 由 @emb exp="mp.text" 上屏                  选项
  @hn       -> plugin_facewindow.ks 只隐藏图片名札                 非文本，丢弃
  名札 = namewindow_object.forestorage='n_*' 独立图片窗             ⇒ 剔除，不加前缀
  ruby / between_ruby = 振假名读音 ⇒ 丢弃；基字(word/afterword/afterword2) 保留
  选项序号 `１．` 中 １ 为 convHanToZen 动态生成、．为宏体写死 ⇒ 只收 text= 原文
  裸地の文行首全角空格 `　` 是原文 ⇒ 只裁行尾，不 strip 行首
  裸地の文内联 `[ruby text='…']` 512 处（全库唯一内联标签）⇒ 丢读音留基字

用法：python scripts/prometheus_extract.py [data.xp3路径] [输出txt]
"""
import os
import re
import sys
import zlib
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEF_XP3 = os.path.join(ROOT, "_work_prometheus", "inno_out", "app", "data.xp3")
DEF_OUT = os.path.join(ROOT, "提取结果", "[JP]Live x Evil 熱砂のプロメテウス.txt")

TAG_RE = re.compile(r"\[([^\]\s=]+)")
# 内联标签：引号感知（单/双引号内的 ] 不算标签结束）。全库唯一种类是 [ruby text='…']
INLINE_RE = re.compile(r"\[(?:[^\[\]'\"]|'[^']*'|\"[^\"]*\")*\]")
ATTR_RE = re.compile(r"""\b(\w+)\s*=\s*(?:'([^']*)'|"([^"]*)"|([^\s]+))""")


def u64(b, o=0):
    return struct.unpack_from("<Q", b, o)[0]


class PlainXP3:
    """明文索引 XP3：只读需要的成员，不全盘载入。"""

    def __init__(self, path):
        self.f = open(path, "rb")
        h = self.f.read(64)
        if h[:6] != b"XP3\r\n ":
            raise RuntimeError("not XP3")
        idx = u64(h, 0x0B)
        self.f.seek(idx)
        flag = self.f.read(1)[0]
        if flag != 0:
            raise RuntimeError("index is zlib-compressed, not plain")
        body = self.f.read(u64(self.f.read(8)))
        self.files = {}
        pos = 0
        while pos + 12 <= len(body):
            if body[pos:pos + 4] != b"File":
                break
            sz = u64(body, pos + 4)
            pos += 12
            pl = body[pos:pos + sz]
            pos += sz
            q, name, segs = 0, None, []
            while q + 12 <= len(pl):
                t = pl[q:q + 4]
                s = u64(pl, q + 4)
                q += 12
                d = pl[q:q + s]
                q += s
                if t == b"info":
                    nl = struct.unpack_from("<H", d, 0x14)[0]
                    name = d[0x16:0x16 + nl * 2].decode("utf-16-le", "replace")
                elif t == b"segm":
                    for i in range(0, len(d) - 27, 28):
                        fl, off, a, b = struct.unpack_from("<IQQQ", d, i)
                        segs.append((off, b, a, fl))
            if name is not None:
                self.files[name] = segs

    def read(self, name):
        buf = bytearray()
        for off, stored, orig, fl in self.files[name]:
            self.f.seek(off)
            raw = self.f.read(stored)
            buf += raw if stored == orig else zlib.decompress(raw)
        return bytes(buf)

    def text(self, name):
        b = self.read(name)
        if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return b.decode("utf-16", "replace")
        if b.count(b"\x00") > len(b) * 0.25:
            return b.decode("utf-16-le", "replace")
        return b.decode("cp932", "replace")


def order_files(available):
    """剧本播放序：title.ks -> @jump storage="c01-01.ks" ⇒ 共通线 → 共通TRUE → 各角色线 → normal。"""
    pats = [
        r"c\d\d-\d\d\.ks$",
        r"common_true\d+\.ks$",
        r"sei-.*\.ks$",
        r"fan-.*\.ks$",
        r"yuusi-.*\.ks$",
        r"kou-.*\.ks$",
        r"kf-.*\.ks$",
        r"kn-.*\.ks$",
        r"yk-.*\.ks$",
        r"normal.*\.ks$",
    ]
    out, seen = [], set()
    for p in pats:
        for n in sorted(k for k in available if re.match(p, k)):
            if n not in seen:
                seen.add(n)
                out.append(n)
    return out


def attrs(s):
    d = {}
    for k, a, b, c in ATTR_RE.findall(s):
        d[k] = a if a != "" else (b if b != "" else c)
    return d


class Extractor:
    def __init__(self):
        self.lines = []
        self.cur = ""
        self.st = collections.Counter()
        self.tok = 0           # 源码可见文本 token 数（含宏补的引号）
        self.empty_frames = 0
        self.skip = False      # @iscript / @macro 块内

    def flush(self, why):
        if self.cur:
            self.lines.append(self.cur)
            self.st["flush_" + why] += 1
            self.cur = ""
        elif why in ("p", "s"):
            self.empty_frames += 1

    def voice(self, a):
        q = ("『", "』") if a.get("pron") == "sec" else ("「", "」")
        body = a.get("word", "") + a.get("afterword", "") + a.get("afterword2", "")
        s = q[0] + body + q[1]
        self.cur += s
        self.tok += len(s)
        self.st["voice"] += 1
        # 宏体末尾 @p + @cm ⇒ 独立一框
        self.flush("voice")

    def option(self, a):
        t = a.get("text", "")
        self.flush("pre_opt")
        self.lines.append(t)
        self.tok += len(t)
        self.st["opts"] += 1

    def feed(self, name, text):
        for raw in text.splitlines():
            l = raw.rstrip()          # 只裁行尾，行首全角空格是原文
            t = l.lstrip()
            if not t:
                continue
            if t.startswith("@iscript") or t.startswith("@macro"):
                self.skip = True
                continue
            if t.startswith("@endscript") or t.startswith("@endmacro"):
                self.skip = False
                continue
            if self.skip:
                continue
            if t[0] in ";*":          # KAG 注释 / 标签
                continue
            if t[0] != "@":           # 裸地の文：剥内联 [ruby text=…]（丢读音，留标签后的基字）
                vis = INLINE_RE.sub("", l)
                self.cur += vis
                self.tok += len(vis)
                self.st["bare"] += 1
                self.st["ruby_stripped"] += len(INLINE_RE.findall(l))
                continue
            m = re.match(r"@([A-Za-z_][A-Za-z0-9_]*)", t)
            cmd = m.group(1) if m else ""
            rest = t[len("@" + cmd):]
            if cmd in ("p", "s"):
                self.flush(cmd)
                self.st["p" if cmd == "p" else "s"] += 1
            elif cmd in ("cm", "ct", "er"):
                self.flush(cmd)
                self.st[cmd] += 1
            elif cmd == "r":
                self.st["r"] += 1     # 框内改行＝合并，不加字符
            elif cmd == "voice":
                self.voice(attrs(rest))
            elif cmd == "select_item":
                self.option(attrs(rest))
            elif cmd == "select_start":
                self.flush("select_start")
            else:
                self.st["skip_" + cmd] += 1
        # 文件末：若有未收框文本，按清屏/换本收行
        self.flush("eof")


def main():
    xp3_path = sys.argv[1] if len(sys.argv) > 1 else DEF_XP3
    out_path = sys.argv[2] if len(sys.argv) > 2 else DEF_OUT
    xp = PlainXP3(xp3_path)
    ks = [n for n in xp.files if n.lower().endswith(".ks") and n.startswith("scenario/")]
    order = order_files([os.path.basename(n) for n in ks])
    ex = Extractor()
    for n in order:
        ex.feed(n, xp.text("scenario/" + n))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    data = "\ufeff" + "\n".join(ex.lines) + "\n"
    with open(out_path, "wb") as f:
        f.write(data.encode("utf-8"))

    out_chars = sum(len(x) for x in ex.lines)
    print("xp3 members", len(xp.files))
    print("story files", len(order))
    print("lines", len(ex.lines), "chars", out_chars, "bytes", len(data.encode("utf-8")))
    print("stats", dict(ex.st.most_common(18)))
    print("token(expected)", ex.tok, "out_chars", out_chars, "diff", ex.tok - out_chars)
    print("empty_frames", ex.empty_frames)
    print("--- first 12 ---")
    for x in ex.lines[:12]:
        print("   ", x[:100])
    print("--- last 6 ---")
    for x in ex.lines[-6:]:
        print("   ", x[:100])


if __name__ == "__main__":
    main()
