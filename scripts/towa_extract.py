# -*- coding: utf-8 -*-
"""悠遠ノ桜 (Towa no Sakura / PS2-JP) LSB 解析 —— VSC VDP + LSB 族

与 ラスト・エスコート2 同族但记录形状不同：正文区头部 4B，其后为记录流
  [u32 X][u32 voice][name 域][text\0]
  X     : 0xff / 0xfe / 0x9f / 0x0d …（样式/有无语音）
  voice : 0xffffffff = 无语音；否则语音 ID（>0x10000）
  name  : `26 00` = 主角名宏；`00` = 无名；否则 NUL 结尾名札串（≤12 字、无句读）
  text  : NUL 结尾 cp932
记录之间可夹 0–6 字节填充 ⇒ 解析器按「试位 + 校验」推进（非穷举：每位仅一次验证）。

正文内控制码：0x5C = 同框软换行（合并）；0x5C5C = 换页（清框，另起一行）；
             0x26 = 主角名；0x25 = 主角姓；0x23 = 破折号演出（丢弃）。
"""
import struct, sys, os, glob, re

BRK = 0x5C
NAME_MACRO = 0x26
SUR_MACRO = 0x25


def read_cstr(d, i, limit=400):
    e = d.find(b'\x00', i)
    if e < 0 or e - i > limit:
        return None, i
    try:
        s = d[i:e].decode('cp932')
    except UnicodeDecodeError:
        return None, i
    if '\ufffd' in s:
        return None, i
    return s, e + 1


def is_jp(s):
    return any(ord(c) > 0xff for c in s)


BAD = re.compile('[\u0000-\u001f\u007f\ue000-\uf8ff\ufffd]')


def valid(s):
    return bool(s) and is_jp(s) and not BAD.search(s)


NAME_OK = re.compile(r'^[^\s]{1,12}$')


def parse_text(d, i):
    """在名字域位置 i 解析 (name, text, end)。
    d[i]==0        -> 无名（旁白）
    d[i:i+2]==26 00-> 主角名宏
    否则            -> NUL 结尾名札串（可含 ！？ 等演出字）"""
    n = len(d)
    j = i
    if j >= n:
        return None
    name = ''
    if d[j:j + 2] == b'\x26\x00':
        name = '#MC'
        j += 2
    elif d[j] == 0:
        j += 1
    else:
        nm, k = read_cstr(d, j, 40)
        if nm is None or not is_jp(nm) or not NAME_OK.match(nm) or BAD.search(nm):
            return None
        name = nm
        j = k
    txt, e = read_cstr(d, j)
    if txt is None or not valid(txt):
        return None
    return (name, txt, e)


def records(d):
    """返回 (title, [(name, text)])"""
    if len(d) < 0x30:
        return '', []
    body = struct.unpack('<I', d[0x10:0x14])[0]
    try:
        title = d[0x18:d.find(b'\x00', 0x18)].decode('cp932')
    except Exception:
        title = ''
    out = []
    n = len(d)
    pos = body
    guard = 0
    while pos < n - 8 and guard < 100000:
        guard += 1
        cands = []
        for skip in range(0, 8):
            q = pos + skip
            if q + 8 > n:
                break
            X = struct.unpack_from('<I', d, q)[0]
            if not (X <= 0xffff or X == 0xffffffff):
                continue
            for extra in (4, 0):
                if extra:
                    V = struct.unpack_from('<I', d, q + 4)[0]
                    if not (V == 0xffffffff or 0x10000 <= V <= 0x3fffff):
                        continue
                r = parse_text(d, q + 4 + extra)
                if r is None:
                    continue
                name, txt, end = r
                score = (3 if name else 0) + min(len(txt), 12)
                cands.append((score, -skip, name, txt, end))
                break
        if not cands:
            pos += 1
            continue
        cands.sort(reverse=True)
        _, _, name, txt, end = cands[0]
        out.append((name, txt))
        pos = end
    return title, out


def clean(txt, name, sur):
    out = []
    i = 0
    while i < len(txt):
        c = txt[i]
        if c == chr(BRK):
            if i + 1 < len(txt) and txt[i + 1] == chr(BRK):
                out.append('\x01')          # 换页标记
                i += 2
                continue
            i += 1
            continue
        if c == chr(NAME_MACRO):
            out.append(name)
        elif c == chr(SUR_MACRO):
            out.append(sur)
        elif c == chr(0x23):
            pass
        else:
            out.append(c)
        i += 1
    return ''.join(out)


if __name__ == '__main__':
    t, rs = records(open(sys.argv[1], 'rb').read())
    print(t, len(rs))
    for nm, tx in rs:
        print(('[' + nm + '] ' if nm else '') + repr(tx))
