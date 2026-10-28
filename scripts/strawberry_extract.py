#!/usr/bin/env python3
"""strawberry_extract.py —— PS2『きまぐれストロベリーカフェ』EVT 字节码文本提取（v3）

链路：ISO9660 → DATA/EVT/<NN>/F####.EVT（129）＋ DATA/TALK/*.EVT（10）→ 记录流

记录语法（实测）：
  0x0c <u8 len> <cp932 字节, 末尾 NUL>   len 含 NUL   → 显示 1 行
  0x10                                   → 框内改行（软换行，沿用同一框）
  0x02 …属性… 0x19 <u16 msgid>            → 新消息＝一次点击（msgid 逐条 +1，实测 258/260 差 1）
  0x05 <cp932 NUL 串>                     → 名字窗字符串（栗田/葛城/猪口/梨香/あやか…）
  0x02 0x03 [<u8 id>]                     → 名字窗模式，紧随的 0x0c 记录是名札（本作仅「梨香」）
  0x0d / 0x0e / 0x0f <0-4>                → 行内人名宏（姓 / 名 / 固定角色姓）
"""
import sys, os, glob

F0F = {0: '水原', 1: '町谷', 2: '猪口', 3: '葛城', 4: '千頭'}
# 主角名（可改名，vndb c46657 水原 苺）：0x0d=姓 / 0x0e=名
HERO_SURNAME = '水原'
HERO_GIVEN = '苺'


def scan(d):
    out = []
    i, n = 0, len(d)
    while i < n - 3:
        if d[i] == 0x0c:
            L = d[i + 1]
            if 2 <= L <= 0x80 and i + 2 + L <= n:
                s = d[i + 2:i + 2 + L]
                if s[-1] == 0 and all(b >= 0x20 for b in s[:-1]):
                    try:
                        t = s[:-1].decode('cp932')
                    except UnicodeDecodeError:
                        t = None
                    if t is not None:
                        out.append((i, i + 2 + L, t))
                        i += 2 + L
                        continue
        i += 1
    return out


def macros_in(gap):
    """返回间隔内的人名宏序列 [(kind, arg)]，只认紧贴下一条文本记录者"""
    res = []
    i, n = 0, len(gap)
    while i < n:
        b = gap[i]
        # 宏必须紧接在「上一条文本的 NUL」或「框内改行 0x10」之后，且后随文本记录 0x0c
        ok_prev = (i == 0) or (gap[i - 1] in (0x00, 0x10, 0x0d, 0x0e, 0x0f))
        at_end = i == n - 1
        nxt = gap[i + 1] if i + 1 < n else 0x0c
        if not ok_prev:
            i += 1
            continue
        if b == 0x0e and (at_end or nxt == 0x0c):
            res.append(('given', None)); i += 1; continue
        if b == 0x0d and (at_end or nxt in (0x0c, 0x0e)):
            res.append(('surname', None)); i += 1; continue
        if b == 0x0f and i + 1 < n and gap[i + 1] <= 4 and (i + 1 == n - 1 or gap[i + 2] == 0x0c):
            res.append(('f0f', gap[i + 1])); i += 2; continue
        i += 1
    return res


def expand(ms):
    out = []
    for kind, arg in ms:
        if kind == 'f0f':
            out.append(F0F.get(arg, ''))
        elif kind == 'given':
            out.append(HERO_GIVEN)
        else:
            out.append(HERO_SURNAME)
    return ''.join(out)


def extract(path):
    d = open(path, 'rb').read()
    base = os.path.basename(path)
    recs = scan(d)
    boxes, cur = [], None
    prev = 0
    plate = ''          # 当前框名札
    last_other = ''     # 最近的非主角名札
    for k, (a, b, t) in enumerate(recs):
        gap = d[prev:a] if k else d[:a]
        is_name = gap[-2:] == b'\x02\x03' or (gap[-1:] == b'\x03' and t == '梨香')
        if is_name:
            plate = t
            if t != '栗田':
                last_other = t
            prev = b
            continue
        newbox = gap[-3:-2] == b'\x19'
        ms = macros_in(gap)
        pre = expand(ms) if ms else ''
        if newbox or cur is None:
            if cur is not None:
                boxes.append(''.join(cur))
            cur = [pre, t] if pre else [t]
            plate = ''
        else:
            if pre:
                cur.append(pre)
            cur.append(t)
        prev = b
    if cur is not None:
        boxes.append(''.join(cur))
    return [x for x in boxes if x.strip()]


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '_work_straw/iso/DATA'
    out = sys.argv[2] if len(sys.argv) > 2 else '提取结果/[PS2-JP]きまぐれストロベリーカフェ.txt'
    files = sorted(glob.glob(os.path.join(root, 'EVT', '*', '*.EVT')))
    files += sorted(glob.glob(os.path.join(root, 'TALK', '*.EVT')))
    lines = []
    for f in files:
        lines.extend(extract(f))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(lines) + '\n')
    print('files', len(files), 'lines', len(lines))


if __name__ == '__main__':
    main()
