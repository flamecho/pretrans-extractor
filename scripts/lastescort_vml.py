# -*- coding: utf-8 -*-
"""ラスト・エスコート 〜黒蝶スペシャルナイト〜 (PS2-JP / D3PUBLISHER, SLPS_256.73)
VML 剧本解析器（文本提取）

容器：DATA2/ADV.FPK  FPK 归档
  头：u32 count / u64 totalSize / u32 0x20(表偏移) / u32 dataStart
  条目 32B：name[16] + u32 size + u32 offset + u64 pad
脚本：*.VML
  头：u32 hdrSize(0x10) / u32 tableOff / u32 count / u32 fileSize
      tableOff!=0 时接 count 个 u32 偏移（非文本索引）
  文本编码：JIS X 0208 7bit —— 每字节 +0x80 即得 EUC-JP（一行 ≤18 字符）

记录
  68 00 00 ff <u8 len> <len>          = 正文（1 记录 = 画面 1 行）
  64 00 00 ff <u8 len> <len>          = 名札
  f6 01 00 ff <u16 idx> <u8 len> <len> = 选项（idx 从 0 起，同组连续）

紧跟文本记录之后的控制码
  69 00 00 ff = 软换行（同框换行 → 合并）
  6a 00 00 ff = 插入主角名（絢子）
  6b 00 00 ff = 插入主角名（行首/行中均有）
  6c 00 00 ff = 直接接续（无换行）
  其他        = 换框（6f / 0c / 09 / 6d ...）
"""
import os, re, sys, glob, json, hashlib
from collections import Counter

NAME = '明里'   # 名；6A=姓(作上) / 6B=名(明里)
SURNAME = '作上'
CONT = {b'\x69\x00\x00\xff': '', b'\x6a\x00\x00\xff': SURNAME,
        b'\x6b\x00\x00\xff': NAME, b'\x6c\x00\x00\xff': ''}

def jp(b):
    try: return bytes(x + 0x80 for x in b).decode('euc_jp')
    except Exception: return None

def records(d):
    """按偏移顺序返回事件 [(off, kind, text)]；kind: T 正文 / N 名札 / O 选项 / L 软换行 / M 插入主角名 / C 直接接续"""
    ev, i, n = [], 0, len(d)
    while i < n - 5:
        if d[i] in (0x68, 0x64) and d[i+1:i+4] == b'\x00\x00\xff':
            L = d[i+4]
            seg = d[i+5:i+5+L]
            if L and all(0x21 <= b <= 0x7e for b in seg):
                s = jp(seg)
                if s:
                    ev.append((i, 'T' if d[i] == 0x68 else 'N', s))
                    i += 5 + L
                    op = d[i:i+4]
                    if op == b'\x69\x00\x00\xff': ev.append((i, 'L', '')); i += 4
                    elif op == b'\x6c\x00\x00\xff': ev.append((i, 'C', '')); i += 4
                    elif op in (b'\x6a\x00\x00\xff', b'\x6b\x00\x00\xff'):
                        ev.append((i, 'M', SURNAME if op[0] == 0x6a else NAME)); i += 4
                    continue
        if d[i:i+4] == b'\xf6\x01\x00\xff' and i + 6 < n:
            L = d[i+6]
            seg = d[i+7:i+7+L]
            if L and all(0x21 <= b <= 0x7e for b in seg):
                s = jp(seg)
                if s:
                    ev.append((i, 'O', s))
                    i += 7 + L
                    continue
        if d[i:i+4] in (b'\x6a\x00\x00\xff', b'\x6b\x00\x00\xff'):
            ev.append((i, 'M', SURNAME if d[i] == 0x6a else NAME)); i += 4; continue
        i += 1
    return ev


def boxes(ev):
    """-> [(text, nametag, kind)]；kind: T 正文行 / O 选项行"""
    out, cur, name, pend, last = [], [], None, None, 'B'

    def flush():
        nonlocal cur, name, last
        if cur:
            out.append((''.join(cur), name, 'T'))
        cur, name, last = [], None, 'B'

    for off, kind, s in ev:
        if kind == 'N':
            flush(); pend = s
        elif kind == 'O':
            flush(); out.append((s, None, 'O'))
        elif kind == 'M':
            if last in ('T', 'L', 'C', 'M'):
                cur.append(s)
            else:
                flush(); cur.append(s); name = pend; pend = None
            last = 'M'
        elif kind == 'L':
            last = 'L'
        elif kind == 'C':
            last = 'C'
        else:
            if last in ('L', 'C', 'M'):
                cur.append(s); last = 'T'
            else:
                flush(); cur.append(s); name = pend; pend = None; last = 'T'
    flush()
    return out


def natkey(p):
    b = os.path.basename(p)
    m = re.match(r'^(\d+)_(.*)$', b)
    pre, rest = (m.group(1), m.group(2)) if m else ('99', b)
    g = re.match(r'^([A-Z]+)', rest).group(1)
    grp = {'E': 0, 'S': 1, 'D': 2, 'ED': 3, 'EVE': 4}.get(g, 9)
    return (grp, g, [int(x) for x in re.findall(r'\d+', rest)], pre)


def load(path):
    return boxes(records(open(path, 'rb').read()))


if __name__ == '__main__':
    root = sys.argv[1]
    files = sorted(glob.glob(os.path.join(root, '*.VML')), key=natkey)
    t = o = 0; names = Counter()
    for f in files:
        for txt, nm, k in load(f):
            if k == 'O': o += 1
            else: t += 1
            if nm: names[nm] += 1
    print('files', len(files), '正文行', t, '选项行', o)
