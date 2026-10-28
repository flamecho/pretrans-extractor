#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""リプルのたまご ～Apprentice magician～ (PS2, HuneX .ebf) 全文本提取。

链路：ISO9660 → EVENTDAT.BIN（HFU2[1] → 内嵌 HFU2 339 条）
      每条 = "UFFA"+LZSS 压缩的 .ebf 字节码（同 HuneX IKA 家族 cLz）。
字节码：指令 `26 <cmd> 24 <n>` 之外，串参数一律 `<op> <argc> <len> <cp932 len-1 含 NUL>`。
文本 ops（实测唯一载体）：
  0x07 0x01 <len> <文字列>：显示串（含名札行与两种推进指令）
      文字列以 '\\' 开头 ⇒ 不是正文，是推进指令：
        '\'      = 点击等待（清框换页）      A 类
        '\\-5000' = 5 秒计时等待（清屏推进，非点击）
      其余 = 正文/名札；行末 '%n' = 框内软换行（合并）
  0x18 0x02 <文字> <label>：选项（一项一条）
名札：无 name 专用命令，名札是正文流里的普通串 `【名】%n`（占框内首行）
      ⇒ 正文内名札，保留并接同行；主角名槽 `$500` 按默认名 クリム inline。
"""
import sys, os, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ripple_deep import split

SKIP_SCRIPTS = {21}      # 0x15＝タイトル画面「オープニングを見る/見ない」UI 菜单，非正文
NAME_SLOT = '$500'
HEROINE = 'クリム'


def iter_ops(b):
    """按字节流顺序产出 ('text', str) / ('opt', str) / ('page',) / ('wait',) """
    i = 0
    n = len(b)
    while i < n - 3:
        op = b[i]
        if op == 0x07 and b[i + 1] == 0x01:
            L = b[i + 2]
            if 2 <= L <= 400 and i + 3 + L <= n and b[i + 3 + L - 1] == 0:
                try:
                    t = b[i + 3:i + 3 + L - 1].decode('cp932')
                except UnicodeDecodeError:
                    i += 1
                    continue
                if t == '\\':
                    yield ('page',)
                elif t.startswith('\\-'):
                    yield ('wait',)
                else:
                    yield ('text', t)
                i += 3 + L
                continue
        elif op == 0x18 and b[i + 1] == 0x02:
            L1 = b[i + 2]
            if 2 <= L1 <= 200 and i + 3 + L1 <= n and b[i + 3 + L1 - 1] == 0:
                j = i + 3 + L1
                if j < n:
                    L2 = b[j]
                    if 2 <= L2 <= 80 and j + 1 + L2 <= n and b[j + 1 + L2 - 1] == 0:
                        try:
                            t = b[i + 3:i + 3 + L1 - 1].decode('cp932')
                        except UnicodeDecodeError:
                            i += 1
                            continue
                        yield ('opt', t)
                        i = j + 1 + L2
                        continue
        i += 1


def clean(s):
    s = s.replace('%n', '')
    s = s.replace(NAME_SLOT, HEROINE)
    return s


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'single'   # single | dual

    data = open(src, 'rb').read()
    top = split(data)
    assert top and len(top) == 1, 'EVENTDAT 顶层应为单个 HFU2'
    scripts = split(data[0x800:])
    print('scripts', len(scripts))

    out = []          # 成品行
    boxes = 0
    multiseg = 0
    seg_total = 0
    opt_total = 0
    drop_wait = 0

    for k, (o, s, s2, b) in enumerate(scripts):
        if k in SKIP_SCRIPTS:
            continue
        segs = []      # 当前框内各段（B 类分段）
        cur = []       # 当前段内 07 记录

        def flush_seg():
            if cur:
                segs.append(''.join(clean(x) for x in cur))
                cur.clear()

        def flush_box():
            nonlocal boxes, multiseg, seg_total
            flush_seg()
            if not segs:
                return
            boxes += 1
            seg_total += len(segs)
            if len(segs) > 1:
                multiseg += 1
                if mode in ('dual', 'click'):
                    out.extend(segs)
                out.append(''.join(segs))
            else:
                out.append(segs[0])
            segs.clear()

        for ev in iter_ops(b):
            if ev[0] == 'text':
                cur.append(ev[1])
            elif ev[0] == 'page':
                flush_box()
            elif ev[0] == 'wait':
                # \-5000 = 5 秒计时等待：清屏推进到下一屏（不计点击）⇒ 单版按换页处理
                flush_box()
                drop_wait += 1
            elif ev[0] == 'opt':
                flush_box()
                out.append(clean(ev[1]))
                opt_total += 1
        flush_box()

    lines = [l for l in out if l != '']
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('boxes=%d multiseg=%d segs=%d opts=%d waits=%d lines=%d'
          % (boxes, multiseg, seg_total, opt_total, drop_wait, len(lines)))


if __name__ == '__main__':
    main()
