#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GsWin / DataPack5 (Takuyo PC) —— Scw5.x 剧本文本提取（一次点击 = 一行）。

依赖 scripts/garnet_pc_pak.py 解出的 .scw（含 0x1C8 头 + 解压后的 raw）。
本脚本直接读 .pak（自包含），按 MainRoot 的 0x1c4 调用序定场景顺序。

Scw 指令流（24B 头 + 参数块链）：
  u16 op / u16 len / 20B 其他；参数块 = [u16 0xff00][u16 count][count×(u32 type,u32 value)]
文本指令：
  0x1a8 = 正文（无语音）     参数 (1,flag)(0x10,str)
  0x1a9 = 正文（带语音）     参数 (1,flag)(0x10,正文)(0x10,语音ID)...
  0x1ce = 选项               参数 (0x10,显示文本)(0x100,RESULTxx)(1,flag)(4,0)
  0x1c4 = 呼叫脚本（跨脚本调用）——用于恢复场景顺序
串内标记：`#F` = 字形/颜色切换（删）；`#<…>` = 注音（删，保留基底）；`#N1` = 主人公名宏。
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from garnet_pc_pak import read_pak, read_scw, getstr

TAG_F = re.compile(r'#F')
TAG_RUBY = re.compile(r'#<[^>]{1,16}>')
TAG_NAME = re.compile(r'#N1')
TAG_OTHER = re.compile(r'#(?:[A-Za-z][A-Za-z0-9_]*|\[[^\]]*\])')


def params(buf):
    out = []
    q = 24
    n = len(buf)
    while q + 4 <= n:
        if struct.unpack_from('<H', buf, q)[0] != 0xFF00:
            break
        cnt = struct.unpack_from('<H', buf, q + 2)[0]
        for j in range(cnt):
            if q + 12 + 8 * j > n:
                break
            t, v = struct.unpack_from('<II', buf, q + 4 + 8 * j)
            out.append((t, v))
        q += 4 + 8 * cnt
    return out


def iter_inst(inst):
    q = 0
    n = len(inst)
    while q + 24 <= n:
        op, ln = struct.unpack_from('<HH', inst, q)
        if ln < 24 or q + ln > n:
            break
        yield op, inst[q:q + ln]
        q += ln


def clean(s, name):
    s = s.replace('\x00', '')
    s = TAG_F.sub('', s)
    s = TAG_RUBY.sub('', s)
    s = TAG_NAME.sub(name, s)
    s = s.replace('\n', '').replace('\r', '')
    return s.strip()


def script_events(scw, name):
    """返回 [('line'|'opt', text)]，按指令序。"""
    ev = []
    stab, strs = scw['stab'], scw['strs']
    for op, buf in iter_inst(scw['inst']):
        ps = params(buf)
        ss = [getstr(scw, v) for t, v in ps if t in (0x10, 0x100) and v < len(stab)]
        if op == 0x1A8:
            if ss:
                ev.append(('line', clean(ss[0], name)))
        elif op == 0x1A9:
            if ss:
                ev.append(('line', clean(ss[0], name)))
        elif op == 0x1CE:
            if ss:
                ev.append(('opt', clean(ss[0], name)))
        elif op in (0x1AA, 0x1B8):
            if ss:
                ev.append(('line', clean(ss[0], name)))
    return ev


def calls(scw):
    out = []
    stab, strs = scw['stab'], scw['strs']
    for op, buf in iter_inst(scw['inst']):
        if op != 0x1C4:
            continue
        for t, v in params(buf):
            if t == 0x10 and v < len(stab):
                out.append(getstr(scw, v).rstrip('\x00'))
    return out


def main():
    pak = sys.argv[1]
    out = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else '美紅'
    order_file = sys.argv[4] if len(sys.argv) > 4 else None
    skips = tuple(x for x in (sys.argv[5].split(',') if len(sys.argv) > 5 else []) if x)
    d, toc, blocks = read_pak(pak)
    scw = {}
    order_names = []
    for nm, h, body, unc, comp in blocks:
        try:
            scw[nm] = read_scw(h, body)
        except Exception as e:
            print('ERR', nm, e)
        order_names.append(nm)
    lower = {n.lower(): n for n in scw}
    # 场景顺序：MainRoot 的 0x1c4 调用序
    seq = []
    seen = set()

    def walk(n, depth=0):
        key = n.lower()
        if key in seen or key not in lower:
            return
        seen.add(key)
        real = lower[key]
        seq.append(real)
        if depth > 3:
            return
        for c in calls(scw[real]):
            walk(c, depth + 1)

    if order_file:
        for ln in open(order_file, encoding='utf-8'):
            ln = ln.strip()
            if ln and not ln.startswith('#'):
                walk(ln)
    else:
        for root in ('MainRoot',):
            if root.lower() in lower:
                walk(lower[root.lower()])
    # 未被调用到的脚本追加在后面（剔除 Sys*/Main*）
    rest = [] if order_file else [n for n in order_names if n.lower() not in seen]
    order = seq + rest

    lines = []
    for n in order:
        if (n.startswith('Sys') or n in ('Main', 'Main__', 'MainRoot', 'AAA', 'SYSV')
                or n.startswith('Start_op_MikuSet') or (skips and n.startswith(skips))):
            continue
        ev = script_events(scw[n], name)
        if n == 'MainRoot':
            ev = []  # 调试用路线选择菜单（剔除）
        for kind, t in ev:
            if not t:
                continue
            lines.append(t)
    txt = '\n'.join(lines) + '\n'
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(txt)
    print('lines', len(lines), 'scripts', len(order))


if __name__ == '__main__':
    main()
