#!/usr/bin/env python3
"""dk_final.py -- [PS2-JP]drastic Killer 成品生成（一次点击 = 一行）。

链路: ISO9660 -> DATA01.HD/BIN -> PACK(名键 XOR) -> flags&0xF {0:store,1:LZSS,2:type2}
     -> SCPT 字节码 -> 文本行
成行判据（L0）：06 <str> + 19 00 00 = 一框正文，19 0e 30 = 点击；
                06 <str> + 19 48 30 = 名札（丢弃，独立名字窗）；
                03 <id> 起连续 06 + 19 (a=4b/4c/12) = 选项窗，屏显序 = 池偏移升序（= 码序逆序，299/299 成立）。
"""
import sys, os, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dk_lib import walk, expand

OPTEND = {0x4b, 0x4c, 0x12}
OUT = '提取结果/[PS2-JP]drastic Killer.txt'


MACRO = {'[主人公]': '〔主人公〕', '[魔界名]': '〔魔界名〕',
         '[緋]': '緋', '[湊]': '湊', '[陸]': '陸', '[凪]': '凪'}


def subs(s):
    for k, v in MACRO.items():
        s = s.replace(k, v)
    return s


def clean(s):
    s = s.replace('\r', '').rstrip('\n')
    return subs(s.replace('\n　', '').replace('\n ', '').replace('\n', '').strip('　 '))


def arg_of(p, a):
    if not (0 < a < len(p)):
        return ''
    e = p.find(b'\x00', a)
    return p[a:e].decode('cp932', 'replace')


def parse(p):
    cl = struct.unpack_from('<I', p, 12)[0]
    ins, i, end = [], 0x20, 0x20 + cl
    while i < end - 4:
        op = p[i]
        if op == 0x19:
            ins.append((0x19, (p[i + 1], p[i + 2])))
            i += 10
        else:
            ins.append((op, struct.unpack_from('<I', p, i + 1)[0]))
            i += 5
    out, k, n = [], 0, len(ins)
    while k < n:
        op, a = ins[k]
        if op == 0x03:
            opts, j = [], k + 1
            while j < n and ins[j][0] == 0x06:
                opts.append(arg_of(p, ins[j][1]))
                j += 1
            if opts and j < n and ins[j][0] == 0x19 and ins[j][1][0] in OPTEND:
                for t in reversed(opts):           # 屏显序
                    t = clean(t)
                    if t:
                        out.append(t)
                k = j + 1
                continue
            k += 1
            continue
        if op == 0x06 and k + 1 < n:
            if ins[k + 1][0] == 0x19 and ins[k + 1][1] == (0, 0):
                t = clean(arg_of(p, a))
                if t:
                    out.append(t)
        k += 1
    return out


def main():
    scripts = {}
    for vol, nm, cs, us, fl, seg in walk(['DATA01']):
        if nm.upper().startswith('EV_') and nm.upper().endswith('.BIN') \
                and not nm.upper().startswith('EV_DUMMY'):
            scripts[nm.upper()] = (us, fl, seg)
    # 顺序以 seq_all.lst 为准（L0）
    order = None
    for vol, nm, cs, us, fl, seg in walk(['DATA01']):
        if nm.upper() == 'SEQ_ALL.LST':
            txt = expand(seg, us, fl).decode('cp932', 'replace')
            order = [x.strip().upper() for x in txt.replace('\r', '').split('\n') if x.strip()]
            break
    if order is None:
        order = sorted(scripts)
    lines = []
    used = 0
    for name in order:
        if name not in scripts:
            continue
        us, fl, seg = scripts[name]
        p = expand(seg, us, fl)
        if p[:4] != b'SCPT':
            continue
        used += 1
        lines += parse(p)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('scripts', used, 'lines', len(lines), '->', OUT)


main()
