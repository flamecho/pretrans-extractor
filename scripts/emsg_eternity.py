#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""EMSG（Eternity 引擎 / white plum『Jewel Garden』系）消息库提取器

格式（2026-11-04 逆向确认，L0：eternity.exe 0x40D665 处的加载函数）
------------------------------------------------------------------
  +0x00  char[4]  'EMSG'
  +0x04  u16      version = 100
  +0x06  u32      count          记录数
  +0x0A  u32      blob_size      正文区字节数
  +0x0E  u32[count] offset       相对 blob 起点的偏移（mono，首项 0）
  blob   = 14 + count*4，长度 blob_size，文件到此结束（无尾垫）

  记录（blob 内）：u32 len + len 字节
    正文 = 该 len 字节 **逐字节 ^ 0xFF** 后按 cp932 解码
    （引擎侧加载函数只做 memcpy，不解码；取反发生在渲染前的字节流里）

  控制码（eternity.exe 0x41234C 起的转义分派表，cmp al 链）
    \\n  → call 0x409340（把行高加到 Y 坐标）        = 框内改行，不点击
    \\k  → [0x43BD38]=5 + call 0x409390（SRCCOPY 重绘）= 改ページ待ち：点击 + 清屏
    \\i  → [0x43BD38]=6                              = 另一种等待（本作 0 次）
    \\v<file>; → 解析到 ';'，写入 0x43BD4C           = 播放语音，不上屏

  成行规则：一框 = 一次点击 = 一条输出行
    \\n 结尾 → 同框续行（合并）
    \\k 结尾 → 收框
    \\v…;   → 纯语音记录，丢弃（本作 14,483 条，无正文）

用法
----
  python scripts/emsg_eternity.py <msg.dat> <out.txt> [--drop-system-ui] [--stats]
"""
import argparse
import re
import struct
import sys

MAGIC = b'EMSG'
VERSION = 100
XOR = 0xFF
# 系统 UI 提示（渲染在确认框里，非剧情）——用 --drop-system-ui 才剔除
SYSTEM_UI = {'セーブしますか？', 'ロードしますか？', '終了しますか？'}
VOICE = re.compile(r'\\v[^;]{0,64};')


def load(path):
    d = open(path, 'rb').read()
    if d[:4] != MAGIC:
        raise SystemExit('不是 EMSG：%r' % d[:4])
    ver = struct.unpack_from('<H', d, 4)[0]
    if ver != VERSION:
        print('警告：version=%d（预期 %d）' % (ver, VERSION), file=sys.stderr)
    n = struct.unpack_from('<I', d, 6)[0]
    size = struct.unpack_from('<I', d, 10)[0]
    tab_at = 14
    blob = tab_at + n * 4
    if blob + size != len(d):
        raise SystemExit('结构不符：blob(%d)+size(%d)=%d ≠ 文件长 %d'
                         % (blob, size, blob + size, len(d)))
    offs = list(struct.unpack_from('<%dI' % n, d, tab_at))
    recs = []
    for i in range(n):
        p = blob + offs[i]
        ln = struct.unpack_from('<I', d, p)[0]
        raw = d[p + 4:p + 4 + ln]
        if len(raw) != ln:
            raise SystemExit('记录 %d 越界' % i)
        recs.append(raw)
    return recs, offs, blob, size


def decode(raw):
    return bytes(b ^ XOR for b in raw).decode('cp932', 'replace')


def build_boxes(recs, drop_sys=False):
    """返回 [(文本, 行数, 是否系统UI)]"""
    boxes = []
    cur, nl = [], 0
    for raw in recs:
        t = decode(raw)
        if VOICE.fullmatch(t.rsplit('\\k', 1)[0]) or (t.startswith('\\v') and t.endswith(';')
                                                      and t.count('\\') == 1):
            continue        # 纯语音记录：无正文，且不是点击
        endk = t.endswith('\\k')
        body = t[:-2] if (endk or t.endswith('\\n')) else t
        if t.endswith('\\n'):
            nl += 1
        body = VOICE.sub('', body)
        if body:
            cur.append(body)
        if endk:
            boxes.append((''.join(cur), nl))
            cur, nl = [], 0
    if cur:
        boxes.append((''.join(cur), nl))
    if drop_sys:
        boxes = [b for b in boxes if b[0].strip() not in SYSTEM_UI]
    return boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--drop-system-ui', action='store_true',
                    help='剔除渲染在确认框里的系统提示（%s）' % '/'.join(sorted(SYSTEM_UI)))
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()

    recs, offs, blob, size = load(a.src)
    boxes = build_boxes(recs, a.drop_system_ui)
    lines = [b for b, _ in boxes]
    with open(a.dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    if a.stats:
        chars = sum(len(x) for x in lines)
        tot = sum(len(r) for r in recs)
        print('文件      %s (%d B)' % (a.src, blob + size))
        print('记录      %d（正文区 %d B，偏移表 @14）' % (len(recs), size))
        print('纯语音    %d' % sum(1 for r in recs
                                   if decode(r).startswith('\\v') and decode(r).endswith(';')))
        print('文本框    %d' % len(lines))
        print('总字数    %d' % chars)
        print('行数分布  %s' % sorted(__import__('collections').Counter(k for _, k in boxes).items()))
        print('记录字节  %d / 正文区 %d（差 = 各记录 u32 长度头 %d）'
              % (tot, size, size - tot))


if __name__ == '__main__':
    main()
