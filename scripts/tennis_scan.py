#!/usr/bin/env python3
"""tennis_scan.py -- [PS2-JP] テニスの王子様 RUSH & DREAM! 脚本解码/文本扫描.

链路: SCRIPT.HD/BIN -> 条目(.s) -> 8B XOR(PACK|0 锚定) -> PACK -> type2 解压 -> SCPT
      SCPT: [SCPT][0][u32 codeStart=0x20][u32 codeLen][...]; 代码 5B/条, 0x19=10B
用法: python scripts/tennis_scan.py <name.s> [...]   (调试用)
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tennis_unpack import pak_entries, unpack_entry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, '_work_tennis')


def load_scriptbin():
    hd = open(os.path.join(WORK, 'x', 'SCRIPT.HD'), 'rb').read()
    sizes = list(struct.unpack('<%dI' % (len(hd) // 4), hd))
    off, offs = 0, []
    for s in sizes:
        offs.append(off)
        off = (off + s + 2047) // 2048 * 2048
    f = open(os.path.join(WORK, 'x', 'SCRIPT.BIN'), 'rb')
    names = [n for n in f.read(sizes[0]).decode('cp932').split('\r\n') if n]
    assert len(names) == len(sizes)
    return names, offs, sizes, f


def get_scpt(d):
    """返回解出的 SCPT 字节串."""
    key = bytes(d[j] ^ b for j, b in enumerate(b'PACK')) + d[4:8]
    dec = bytes(d[j] ^ key[j % 8] for j in range(len(d)))
    assert dec[:4] == b'PACK', dec[:4]
    ents = pak_entries(dec)
    assert len(ents) == 1, ents
    nm, off, csize, usize, fl = ents[0]
    return nm, unpack_entry(dec, off, csize, usize, fl)


JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def parse_scpt(d):
    assert d[:4] == b'SCPT'
    code_start, code_len = struct.unpack_from('<II', d, 8)
    code = d[code_start:code_start + code_len]
    return code, d[code_start + code_len:]


def walk(code):
    """线性走指令流，返回 (offset, op, operand_bytes)."""
    p = 0
    out = []
    n = len(code)
    while p < n:
        op = code[p]
        if op == 0x19:
            out.append((p, op, code[p + 1:p + 10]))
            p += 10
        else:
            out.append((p, op, code[p + 1:p + 5]))
            p += 5
    return out


if __name__ == '__main__':
    names, offs, sizes, f = load_scriptbin()
    for arg in sys.argv[1:]:
        i = names.index(arg)
        f.seek(offs[i])
        d = f.read(sizes[i])
        nm, sc = get_scpt(d)
        code, tail = parse_scpt(sc)
        ins = walk(code)
        print('==', arg, '->', nm, 'scpt', len(sc), 'code', len(code), hex(len(code)), 'tail', len(tail), 'ins', len(ins))
        print('   hdr', [hex(x) for x in struct.unpack_from('<8I', sc, 0)])
        segs = []
        pos = 0
        while pos < len(tail):
            e = tail.find(b'\x00', pos)
            if e < 0:
                e = len(tail)
            s = tail[pos:e]
            if len(s) >= 4:
                try:
                    t = s.decode('cp932')
                except Exception:
                    t = None
                if t and len(JP.findall(t)) >= 3:
                    segs.append((pos, t))
            pos = e + 1
        print('   text segs', len(segs))
        for o, t in segs[:3]:
            print('     ', hex(o), t[:50].replace('\n', '|'))
