#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP] DYNAMIC CHORD feat.apple-polisher（honeybee black 2016-11-04 / PC）
全文本提取 —— ASGARD 自研「AdvHD(ws2) 字节码」链路。

容器链（本作实测，与 NS Remaster 完全不同）：
  SETUP.INI 声明 GAMEEXE=AdvHD.exe、INSTCMPDIR=ASGARD，脚本扩展名 ws2
  Rio.arc（9.4 MB，477 个 *.ws2）← 全部脚本；Script.arc 只有 4 个引擎库 Lua 块

Rio.arc 索引（本作实测，非 Will 的 ext-group 格式）：
  u32 count | u32 hdr04(=表尾-0x10) | u32 size0 | u32 0
  随后 count 条：[name UTF-16LE NUL]  （最后一条无 size/offset）
  前 count-1 条各跟 [u32 size_{i+1}] [u32 end_i]（end 为累计结束偏移，从数据区首字节起算）
  ⇒ 第 i 个文件 = [end_{i-1}, end_i)，end_{-1}=0，size_0 取自 header@0x08
  自证：Σsize == 文件尾 - 数据区首（本作 9,460,823 == 9,460,823，零误差）

加密：ws2 每个字节 rotl_8(c,6)（解密等价 rotr 2），与 Will/AdvHD 的 .wsc 同一 cipher。

字节码（文本相关）：
  0x14 + u32 id + "char\0" + <cp932 台词>          ← 一条 = 一个文本框 = 一次点击
  0x14 + u32 id + ""     + "%N"                     ← 空键命令（文本特效/送り），不收
  0x15 + ""                                          ← 清名札
  0x15 + "%LR<名前>"                                  ← 名札（独立名字窗，整条丢弃）
台词内标记：%K（等待点击）、%P（清框）、%LR（前缀，少数台词也带）、
           字面 `\\n`（框内软换行，合并时删；其后紧跟的全角空格是缩进，一并删）
宏：<@FIRNAME>→美羽、<@FAMNAME>→柊、<@ARTISTNAME>→Ｍｉｕ

用法: python scripts/dycpc_extract.py [--src Rio.arc] [--out 输出.txt] [--stats]
"""
import argparse
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HOME, '_dyc_pc/src/DYNAMIC CHORD feat．apple-polisher/Rio.arc')
OUT = os.path.join(HOME, '提取结果/[PC-JP]DYNAMIC CHORD feat.apple-polisher.txt')

NAME_FIRST = '美羽'
NAME_FAMILY = '柊'
NAME_ARTIST = 'Ｍｉｕ'
MACROS = {'<@FIRNAME>': NAME_FIRST, '<@FAMNAME>': NAME_FAMILY,
          '<@ARTISTNAME>': NAME_ARTIST}

# 路线顺序（由 NS 版成品行位置反推：apkuro → apkyo → apnal → aptoi → apuk → sp01..sp06）
ROUTES = ['apkuro', 'apkyo', 'apnal', 'aptoi', 'apuk']
SP = ['sp01_nal', 'sp02_toi', 'sp03_uk', 'sp04_kuro', 'sp05_boys',
      'sp06_girls', 'sp06_girlsa', 'sp06_girlsb', 'sp06_girlsc',
      'sp06_girlsd', 'sp06_girlse']

TEXT = re.compile(rb'\x14(.{4})char\x00([^\x00]*)\x00', re.S)
PLATE = re.compile(rb'\x15%LR([^\x00]*)\x00')
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')


def rot(b):
    return bytes((((c << 6) | (c >> 2)) & 0xFF) for c in b)


def parse_arc(d):
    cnt, _h4, size0, _z = struct.unpack_from('<IIII', d, 0)
    o = 0x10
    names, pairs = [], []
    for i in range(cnt):
        s = o
        while d[o:o + 2] != b'\x00\x00':
            o += 2
        names.append(d[s:o].decode('utf-16le'))
        o += 2
        if i < cnt - 1:
            a, b = struct.unpack_from('<II', d, o)
            o += 8
            pairs.append((a, b))
    sizes = [size0] + [a for a, b in pairs]
    ends = [b for a, b in pairs]
    data = o
    assert sum(sizes) == len(d) - data, (sum(sizes), len(d) - data)
    out = {}
    cur = data
    for i, (nm, sz) in enumerate(zip(names, sizes)):
        out[nm] = rot(d[cur:cur + sz])
        cur += sz
    return out


def natkey(nm):
    m = re.match(r'^(.*?)(\d+)([a-z]*)$', nm)
    if not m:
        return (9999, 0, nm)
    return (int(m.group(2)), m.group(3), nm)


def order_names(names):
    rank = {r: i for i, r in enumerate(ROUTES)}
    sprank = {s: i for i, s in enumerate(SP)}
    story, sp = [], []
    for nm in names:
        base = nm[:-4]
        if base in sprank:
            sp.append(base)
        elif base.split('_')[0] in rank:
            story.append(base)
    story.sort(key=lambda b: (rank[b.split('_')[0]], natkey(b)))
    sp.sort(key=lambda b: sprank[b])
    return story + sp


def clean(t):
    t = re.sub(r'%[A-Z]{1,3}', '', t)          # %K %P %LR %LC %XS %XE …
    t = re.sub(r'[\ue000-\uf8ff]', '', t)      # 内联图标（PUA 字形槽）
    # ruby 注音 {漢字:かんじ} → 只留基底汉字（读音是振假名，不入正文）
    # 基底限定不含 = " ' 与空白，避免误吃脚本表达式
    t = re.sub(r'\{([^{}:：="\'\s]+)[:：][^{}]*\}', r'\1', t)
    t = re.sub(r'\\n\u3000?', '', t)
    for k, v in MACROS.items():
        t = t.replace(k, v)
    return t.strip('\u3000 ').strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=SRC)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()

    files = parse_arc(open(a.src, 'rb').read())
    seq = order_names(list(files))

    lines, stats, ids_bad = [], [], []
    for base in seq:
        b = files[base + '.ws2']
        ms = list(TEXT.finditer(b))
        ids = [struct.unpack('<I', m.group(1))[0] for m in ms]
        if ids and ids != list(range(ids[0], ids[0] + len(ids))):
            ids_bad.append(base)
        n = 0
        for m in ms:
            t = clean(m.group(2).decode('cp932'))
            if not t:
                continue
            lines.append(t)
            n += 1
        stats.append((base, len(ms), n))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    if a.stats:
        print('files %d   texts %d   lines %d' % (len(seq), sum(s[1] for s in stats), len(lines)))
        print('id 非连续文件:', ids_bad or '无')
        print('名札表条数 %d' % sum(len(PLATE.findall(files[b + '.ws2'])) for b in seq))
        print('空/纯标记丢弃 %d' % (sum(s[1] for s in stats) - len(lines)))
    print('->', a.out, len(lines), '行')


if __name__ == '__main__':
    main()
