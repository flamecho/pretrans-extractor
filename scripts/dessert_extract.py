#!/usr/bin/env python3
"""Dessert Love -Sweet Plus- (PS2) 全文本提取。

链路: ISO9660 -> IMAGE.BIN (ARC ) -> script/*.adv (CP932 文本 DSL) -> 一框一行
  ARC 头: "ARC " + u32 count + u32 nameTableEnd + u32 0
  索引 16B/条: [u32 nameOff][u32 sector][u32 size][u32 flags]  数据自 sector*2048
  DSL: <WINDOW [VISIBLE=FALSE] [NAME="【名】"]> 起一框; 其后物理行=同框软换行 => 合并
       <SOUND SRC="..\voice\.."> 每框 1 条语音(一框=一次点击; 每框至多 4 行=屏容量)
       <SELECT TEXT="..."> 选项;  <SCRIPT SRC="..."> 包含;  <IF COND>/<END> 分支
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso9660 import ISO

ISO_PATH = sys.argv[1] if len(sys.argv) > 1 else 'Dessert Love - Sweet Plus (Japan).iso'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'dessert_raw.txt'

NAME_SURNAME = '瀬口'    # <KEYWORD KEYWORD="主人公の苗字">
NAME_GIVEN = 'はるか'    # <KEYWORD KEYWORD="主人公の名前">

TAG = re.compile(r'<[^>]*>')
KEYWORD = re.compile(r'<KEYWORD\s+KEYWORD="([^"]*)"\s*/?>')
ANYTAG = re.compile(r'<([A-Za-z_]+)([^>]*)>')
# 这些标签只做演出/语音, 不承担「切框」语义
NOISE = {'SOUND', 'IMG', 'SCREEN', 'EXP', 'WAIT', 'SAVETITLE', 'DEMO', 'SYSTEM',
         'CLEAR', 'EFFECT', 'BGM_STOP', 'KEYWORD', 'MOVIE', 'DATE', 'SPEED',
         'SCROLL', 'COLORMAP', 'FONT', 'RUBY'}


def load_arc(iso):
    e = iso.find('IMAGE.BIN')
    base = e['lba'] * 2048
    iso.f.seek(base)
    h = iso.f.read(16)
    assert h[:4] == b'ARC ', h[:4]
    count, names_end, _ = struct.unpack('<3I', h[4:16])
    iso.f.seek(base + 16)
    idx = iso.f.read(16 * count)
    names_off = 16 + 16 * count
    iso.f.seek(base + names_off)
    nt = iso.f.read(names_end - names_off + 64)
    files = {}
    for i in range(count):
        no, sec, size, fl = struct.unpack('<4I', idx[i * 16:(i + 1) * 16])
        p = no - names_off
        q = nt.find(b'\0', p)
        name = nt[p:q].decode('cp932', 'replace').replace('\\', '/')
        files[name.lower()] = (base + sec * 2048, size)
    return files


def read(iso, files, name):
    off, size = files[name.lower()]
    iso.f.seek(off)
    return iso.f.read(size)


def jp_text(s):
    s = KEYWORD.sub(lambda m: NAME_SURNAME if '苗字' in m.group(1) else NAME_GIVEN, s)
    s = TAG.sub('', s)
    return s.strip()


def tokenize(text):
    """-> tokens: ('box',txt) ('select',txt) ('if',cond) ('end',) ('script',path)"""
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    toks = []
    cur = None          # 当前 WINDOW 框
    for raw in lines:
        s = raw.strip()
        if not s or s[0] == ';':
            continue
        if s[0] == '<':
            for m in ANYTAG.finditer(s):
                tag, arg = m.group(1), m.group(2)
                if tag == 'WINDOW':
                    if cur:
                        toks.append(('box', cur))
                    cur = None if 'VISIBLE=FALSE' in arg else ''
                    continue
                if tag in NOISE:          # 演出/语音等: 不切框
                    continue
                if cur:
                    toks.append(('box', cur))
                cur = ''          # 结构性指令(IF/END/SELECT/SCRIPT)后若再有正文, 即新一页
                if tag == 'SELECT':
                    t = re.search(r'TEXT="([^"]*)"', arg)
                    toks.append(('select', t.group(1) if t else ''))
                elif tag == 'IF':
                    c = re.search(r'COND="([^"]*)"', arg)
                    toks.append(('if', c.group(1) if c else ''))
                elif tag == 'SCRIPT':
                    p = re.search(r'SRC="([^"]*)"', arg)
                    toks.append(('script', p.group(1).replace('\\', '/')))
                elif tag in ('END', 'EXIT'):
                    toks.append(('end',))
                # 其余（LABEL/JUMP...）忽略
            continue
        t = jp_text(s)
        if cur is None:
            continue
        cur += t
    if cur:
        toks.append(('box', cur))
    return toks


def is_debug_text(s):
    return '=' in s or 'flag' in s


def if_block_end(toks, i):
    """i 指向 <IF> 之后; 仅按 IF/END 配对(分支 END 不参与), 返回块后下标"""
    depth = 1
    n = len(toks)
    while i < n:
        k = toks[i][0]
        if k == 'if':
            depth += 1
        elif k == 'end':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def block_end(toks, i):
    """i 指向块内第一个 token; 返回该块 END 之后的下标"""
    depth = 0
    n = len(toks)
    while i < n:
        k = toks[i][0]
        if k in ('if', 'select'):
            depth += 1
        elif k == 'end':
            if depth == 0:
                return i + 1
            depth -= 1
        i += 1
    return n


def select_group(toks, i):
    """从 select 起收集同一点击的全部选项 -> ([(select_index, text, branch_end)], next_index)"""
    items = []
    n = len(toks)
    while i < n and toks[i][0] == 'select':
        end = block_end(toks, i + 1)
        items.append((i, toks[i][1], end))
        if end < n and toks[end][0] == 'select' and not is_debug_text(toks[end][1]):
            i = end
            continue
        i = end
        break
    return items, i


class Emit:
    def __init__(self, iso, files):
        self.iso = iso
        self.files = files
        self.done = set()
        self.out = []
        self.boxes = 0
        self.trace = []

    def walk(self, toks, basedir, seen=None, no_box=False):
        seen = set() if seen is None else seen
        i = 0
        n = len(toks)
        while i < n:
            t = toks[i]
            if t[0] == 'select':
                # 同一点击的整组选项一次输出; 分支内容随后按序展开
                if i not in seen:
                    items, _ = select_group(toks, i)
                    for idx, _, _ in items:
                        seen.add(idx)
                    opts = [o.strip() for _, o, _ in items
                            if o.strip('　 ') and '=' not in o]
                    self.out.extend(opts)
                i += 1
                continue
            if t[0] == 'box':
                s = '' if no_box else t[1].strip()
                if s:
                    self.out.append(s)
                    self.boxes += 1
            elif t[0] == 'script':
                p = os.path.normpath(os.path.join(basedir, t[1])).replace('\\', '/').lower()
                if p not in self.done and p in self.files:
                    self.done.add(p)
                    self.trace.append(p)
                    txt = read(self.iso, self.files, p).decode('cp932', 'replace')
                    self.walk(tokenize(txt), os.path.dirname(p),
                               no_box=(p == 'script/scenario.adv'))
                elif p not in self.files:
                    print('[!] missing script:', p, file=sys.stderr)
            i += 1

    def run(self, entry):
        p = entry.lower()
        self.done.add(p)
        txt = read(self.iso, self.files, p).decode('cp932', 'replace')
        self.walk(tokenize(txt), os.path.dirname(p),
                               no_box=(p == 'script/scenario.adv'))


def main():
    iso = ISO(ISO_PATH)
    files = load_arc(iso)
    em = Emit(iso, files)

    # ① 本篇: mainscript -> init + scenario（整棵分支树，按流程序）
    em.run('script/mainscript.adv')
    print('after main: lines=%d boxes=%d files=%d' % (len(em.out), em.boxes, len(em.done)))

    # ② ミニドラマ md01-07（各 END 后开放, system/minidrama/list.csv）
    for i in range(1, 8):
        em.run('script/sc/md%02d.adv' % i)

    # ③ 番外「占い」（title 菜单 -> uranai_main）
    em.run('script/uranai_main.adv')

    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(em.out) + '\n')
    print('lines=%d boxes=%d files=%d -> %s' % (len(em.out), em.boxes, len(em.done), OUT))


if __name__ == '__main__':
    main()
