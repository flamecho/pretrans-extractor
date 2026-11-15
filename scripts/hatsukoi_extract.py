#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]大人の初恋、はじめます（Nintendo Switch / Bezel Engine）剧本文本提取。

链路：romfs/Archive/script.nx.bea → SCNE 容器 → 766 个 zstd 帧
      （前 383＝jaJP，后 383＝enUS，sid 逐帧一一对应，唯一例外 310301091/310301086）
      → scb_ 脚本容器 → 命令流

★ scb_ 帧结构（实测，383/383 个 jaJP 帧结构自洽）：
  0x00 'scb_'
  0x08 8×u32 段表：[代码区偏移, 代码区长度, 段1偏移, 段1长度, 段2偏移, 段2长度,
                    字符串池偏移, 字符串池长度]
      自证：四对 (偏移,长度) 首尾相接；起 0x28、止于帧长（383/383 通过）
  代码区：命令流 [op u16][argc u16][arg0 u32 …]（argc 含自身，实参个数 = argc-1）；
          逐帧遍历到 code_end 恰好闭合（383/383，无 overrun / 无残余）
  字符串池：NUL 结尾 UTF-8，代码区 u32 实参即池内下标的索引

★ 命令语义（L0；383 帧全量统计 + 邻接结构交叉验证）：
  0x0008 名札   1 实参＝字符串索引（空串＝旁白/无名）   92,407 次
  0x0009 正文   1 实参＝字符串索引                       92,407 次（空串 6,068）
  0x000e 点击   无实参                                   92,799 次
  0x000a 清屏   无实参                                    6,104 次
  0x0010 选项   24 实参 = 8 组 × [选项文本, 跳转label, 演出flag]；本作恒 3 组有文本，297 次
  其余：0x06 立绘 92,794 / 0x01·0x13·0x25 背景 / 0x15 SE 692 / 0x0f 跳转脚本 3,494 /
        0x14·0x16 表情 / 0x1d·0x1e 画面效果 / 0x23 闪光 等（均为演出，不含正文）

★ 成行（L0，单版判据三条）：
  ① op0x09 : op0x0e = 92,407 : 92,799 —— 每个文本框恰有一次点击等待；
  ② 相邻两条 op0x09 之间**必含** op0x0e（0 例外）⇒ 不存在"一次点击显示两段"；
  ③ 正文长度硬上限 50 字（26,864 条 ≤45 字、94 条 46–50 字，无跨框长文）
     ⇒ 一条 op0x09 就是一次点击的全部文本，页内点击数恒为 1 ⇒ **单版**。

★ 宏：#NAME[1] → 主角姓「立花」、#NAME[2] → 主角名「なつみ」
  默认值出处：Archive/static~localize.bin.nx.bea 字符串池 #487/#488
  （教名输入画面「名字を入力してください」/「名前を入力してください」后的默认值）。

用法：
  python scripts/hatsukoi_extract.py <romfs目录> --out <txt> [--json <dump>]
"""
import json
import os
import struct
import sys

import zstandard

NAME_MAP = {'#NAME[1]': '立花', '#NAME[2]': 'なつみ'}

OP_NAME = 0x08
OP_TEXT = 0x09
OP_CLEAR = 0x0A
OP_CLICK = 0x0E
OP_CHOICE = 0x10


def zstd_frames(b):
    pos, j = [], 0
    while True:
        j = b.find(b'\x28\xb5\x2f\xfd', j)
        if j < 0:
            return pos
        pos.append(j)
        j += 1


def parse_scb(fr):
    """解析 scb_ 帧；结构不闭合直接抛异常（绝不静默丢数据）。"""
    if fr[:4] != b'scb_':
        raise ValueError('not scb_: %r' % fr[:4])
    secs = struct.unpack_from('<8I', fr, 8)
    code_s, code_l = secs[0], secs[1]
    st_s, st_l = secs[6], secs[7]

    spans = sorted((secs[k], secs[k] + secs[k + 1]) for k in range(0, 8, 2))
    if spans[0][0] != 0x28 or spans[-1][1] != len(fr):
        raise ValueError('section table does not cover frame: %r' % (spans,))
    p = 0x28
    for s, e in spans:
        if s != p or e < s:
            raise ValueError('section gap/overlap at %#x (%r)' % (p, spans))
        p = e
    if code_s + code_l > len(fr) or st_s + st_l > len(fr):
        raise ValueError('section out of range')

    strs, q = [], st_s
    while q < st_s + st_l:
        e = fr.find(b'\x00', q, st_s + st_l)
        if e < 0:
            e = st_s + st_l
        strs.append(fr[q:e].decode('utf-8', 'replace'))
        q = e + 1

    cmds, code_e, q = [], code_s + code_l, code_s
    while q + 4 <= code_e:
        op, argc = struct.unpack_from('<HH', fr, q)
        n = argc - 1
        if n < 0 or q + 4 + 4 * n > code_e:
            raise ValueError('command overrun at %#x' % q)
        args = struct.unpack_from('<%dI' % n, fr, q + 4) if n else ()
        cmds.append((q, op, args))
        q += 4 + 4 * n
    if q != code_e:
        raise ValueError('code section not closed: %#x != %#x' % (q, code_e))
    return strs, cmds


def sub_names(t):
    for k, v in NAME_MAP.items():
        t = t.replace(k, v)
    return t


def main():
    src = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None

    b = open(os.path.join(src, 'Archive', 'script.nx.bea'), 'rb').read()
    dc = zstandard.ZstdDecompressor()
    frames = []
    for o in zstd_frames(b):
        fr = dc.decompress(b[o:], max_output_size=256 << 20)
        if fr[:4] == b'scb_':
            strs, cmds = parse_scb(fr)
            frames.append((strs[0] if strs else '', strs, cmds))
    n_jp = 383
    print('[i] scb_ 帧 %d（JP %d / EN %d）' % (len(frames), n_jp, len(frames) - n_jp))

    lines, stat = [], []
    n_text = n_empty_text = n_click = n_choice = 0
    n_opt = 0
    for fi in range(n_jp):
        sid, strs, cmds = frames[fi]

        def S(i):
            return strs[i] if 0 <= i < len(strs) else ''

        cur_name = ''
        last_text = None
        n0 = len(lines)
        for q, op, a in cmds:
            if op == OP_NAME:
                cur_name = S(a[0]) if a else ''
                last_text = None
            elif op == OP_TEXT:
                last_text = S(a[0]) if a else ''
                if last_text.strip():
                    n_text += 1
                else:
                    n_empty_text += 1
            elif op == OP_CHOICE:
                n_click += 1
                n_choice += 1
                for g in range(len(a) // 3):
                    txt = S(a[3 * g]).strip()
                    if txt:
                        lines.append(sub_names(txt))
                        n_opt += 1
            elif op == OP_CLICK:
                n_click += 1
                if last_text is not None:
                    body = sub_names(last_text).strip()
                    name = sub_names(cur_name).strip()
                    if name and body:
                        body = name + body
                    elif name:
                        body = name
                    if body:
                        lines.append(body)
                last_text = None
                cur_name = ''
        stat.append({'idx': fi, 'sid': sid, 'lines': len(lines) - n0})

    print('[i] 正文点击 %d（其中非空正文 %d / 空文本框 %d）' % (n_text + n_empty_text, n_text, n_empty_text))
    print('[i] 点击等待 %d 次 / 选项指令 %d 次 / 选项行 %d' % (n_click, n_choice, n_opt))
    print('[i] 成品行数 %d' % len(lines))
    print('[i] 闭合：正文 %d + 选项 %d = %d' % (n_text, n_opt, n_text + n_opt))
    if js:
        json.dump({'stat': stat, 'lines': lines, 'closure': {
            'text': n_text, 'empty_text': n_empty_text, 'clicks': n_click,
            'choice_ops': n_choice, 'options': n_opt, 'lines': len(lines)}},
            open(js, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[i] -> %s' % out)


if __name__ == '__main__':
    main()
