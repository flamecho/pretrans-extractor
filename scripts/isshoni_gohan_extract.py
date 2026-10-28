#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""いっしょにごはん。 (PSP, 2011 / STCM2L "Oct  7 2010") 文本提取

容器链路: CHD v5 -> ISO9660 -> PSP_GAME/USRDIR/UNION.CPK (CRI CPK, ART2/STCM2L 混装)
          另 PSP_GAME/INSDIR/UNION.DNS 解密后与 UNION.CPK 完全同一份（重复载体）

STCM2L 记录（本作变体；与 キミカレ 同族但 cmd 集不同）
  代码段 = [u32 size][payload]；payload = 12B 槽 × k + 文本记录 × m + [0][cmd][flag]
  cmd: 0xd2 正文片段（续行）｜0xd3 正文片段+框末｜0xe7(s=1) 正文片段+框末
       0xd4 说话人框开始（名札＝其后紧跟的 1 槽 0xd2）
       0xe7(s=3) 选项 / 0xe6(s=3) 选项组末条
       0x1/0x5/0x0/0xd8/0xbd/0x33/0x3d = 标签、断面名、日期 UI、调试、系统通知（不收）
"""
import os
import re
import struct
import sys

JP = re.compile(r'[ぁ-んァ-ヴー一-龠]')
TAGS = re.compile(r'#(?:Name|Color|Scale|Pos|Ruby|Kana|Font|Speed|Wait|SE|Flag|Var)\[[^\]]*\]')
SKIP_CMDS = {0x1, 0x5, 0x0, 0xd8, 0xbd, 0x3d}
KANA = re.compile(r'[ぁ-んァ-ヴ]')
OPT = {0xe7: 3, 0xe6: 3}
SKIP_IDS = {5000, 5001, 5500, 5501}   # デバッグ遷移／フラグ確認 菜单脚本


def ops_of(d):
    i = d.find(b'CODE_START')
    if i < 0:
        return []
    end = struct.unpack_from('<I', d, 0x20)[0]
    off = i + 24
    out = []
    while off + 4 <= end and off + 4 <= len(d):
        sz = struct.unpack_from('<I', d, off)[0]
        if sz < 4 or off + sz > len(d):
            break
        out.append(d[off + 4:off + sz])
        off += sz
    return out


def split(p):
    s = 0
    while len(p) - 12 * (s + 1) >= 12:
        w = struct.unpack_from('<III', p, 12 * s)
        if w[1] == 0xff000000 and w[2] == 0xff000000:
            s += 1
        else:
            break
    rest = p[12 * s:]
    if len(rest) < 12:
        return s, [], None
    if struct.unpack_from('<I', rest, len(rest) - 12)[0] != 0:
        return s, [], None
    cmd, flag = struct.unpack_from('<II', rest, len(rest) - 8)
    mid = rest[:-12]
    recs, j = [], 0
    while j + 16 <= len(mid):
        a, b, c, L = struct.unpack_from('<IIII', mid, j)
        if a == 0 and b == L // 4 and c == 1 and 4 <= L <= 20000 and j + 16 + L <= len(mid):
            recs.append(mid[j + 16:j + 16 + L].split(b'\0')[0].decode('cp932', 'replace'))
            j += 16 + L
        else:
            break
    return s, recs, ((cmd, flag) if j == len(mid) else None)


def clean(t, hero1, hero2):
    t = t.replace('#Name[1]', hero1).replace('#Name[2]', hero2)
    t = TAGS.sub('', t)
    return t.replace('\uf8f2', '').replace('\uf8f3', '').strip('\u3000').strip()


def extract(d, h1, h2):
    sp = [split(p) for p in ops_of(d)]
    lines, opts, cur = [], [], []
    want = False

    def flush():
        if cur:
            t = ''.join(cur).strip()
            if t:
                lines.append(t)
            del cur[:]

    def flush_opts():
        if opts:
            lines.extend(opts)
            del opts[:]

    for s, recs, t in sp:
        if t is None:
            want = False
            continue
        cmd = t[0]
        if cmd == 0xd4:
            flush()
            flush_opts()
            want = True
            continue
        if want and cmd == 0xd2 and len(recs) == 1:
            want = False
            continue
        want = False
        if (cmd in OPT and s == OPT[cmd] and len(recs) == 1) or (cmd == 0x1 and s == 3 and len(recs) == 1):
            flush()
            x = clean(recs[0], h1, h2)
            if x:
                opts.append(x)
            continue
        if cmd in SKIP_CMDS or s > 1 or len(recs) != 1:
            continue
        if cmd == 0x33 and not KANA.search(recs[0]):
            continue
        x = clean(recs[0], h1, h2)
        if not x or x.isascii():
            continue
        if cmd == 0xd2:
            cur.append(x)
        else:
            cur.append(x)
            flush()
            flush_opts()
    flush()
    flush_opts()
    return lines


def main():
    src, dst = sys.argv[1], sys.argv[2]
    h1, h2 = sys.argv[3], sys.argv[4]
    out, nf = [], 0
    for n in sorted(os.listdir(src), key=lambda x: int(x.split('.')[0])):
        d = open(os.path.join(src, n), 'rb').read()
        if d[:5] != b'STCM2':
            continue
        if int(n.split('.')[0]) in SKIP_IDS:
            continue
        ls = extract(d, h1, h2)
        if ls:
            nf += 1
            out.extend(ls)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('files', nf, 'lines', len(out), '->', dst)


if __name__ == '__main__':
    main()
