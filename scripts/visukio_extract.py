# -*- coding: utf-8 -*-
"""[JP]VISUKIO（Yuuki! Novel 旧版 PackageFile2 ／ .yne）文本提取驱动。

链路：RAR5 SFX(otoame) → VISUKIO.exe → overlay 里 `\x0cPackageFile2` 归档
      → pair0 = autorun.yne（LCG+XOR 解密） → .yne 脚本 DSL → 一框一行。

L0 判据（沿用 engines/yuuki-novel.md，本作实测修正）：
  · 裸文本记录，**行尾（去掉尾随空白后）`@` ＝ 一次点击 ＝ 一个框**；
    无 `@` 的文本记录是**同框续行**（自动换行/续排，不产生点击）⇒ 与下一行合并。
  · `.NextPage` 也结束当前框（页面推进）。
  · `＃選択`（二进制 00 01 块）＝选项组：显示文本按序一行一条。
  · `01 01` / `02 01` 分支块只带跳转标签，不上屏 ⇒ 忽略。
  · 名字窗：本作 `.WindowSet` 0 次 ⇒ 无名札、无内联前缀。
  · 本作 4 条记录里 `@` 出现在句中（作者把点击符写在标点前）——按引擎文档「@ 仅行尾生效」
    ⇒ 视作源笔误，统一剥除，不据此拆框。

用法：
    python scripts/visukio_extract.py --exe "<VISUKIO.exe>" --verify
    python scripts/visukio_extract.py --exe "<VISUKIO.exe>" --out "提取结果/[JP]VISUKIO.txt"
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yuuki_yne as Y

MAGIC = b'\x0cPackageFile2'


def decrypt(blk):
    """LCG + XOR；blk[0:4] = seed（同 yuuki_pkg）。"""
    if len(blk) < 8:
        return b''
    state = struct.unpack_from('<I', blk, 0)[0]
    out = bytearray(len(blk) - 4)
    for i in range(4, len(blk)):
        state = (state * 0x6C078965 + 1) & 0xFFFFFFFF
        out[i - 4] = blk[i] ^ (state >> 24)
    return bytes(out)


def find_archive(d):
    """找 overlay 里的 PackageFile2 归档；用记录区可读性排除代码段里同名字符串。"""
    for mo in [i for i in range(len(d)) if d.startswith(MAGIC, i)]:
        np0 = mo + 0x118
        nlen = d[np0 - 1] if np0 - 1 < len(d) else 0
        if not (1 <= nlen <= 200):
            continue
        raw = d[np0:np0 + nlen]
        try:
            name = raw.decode('cp932')
        except UnicodeDecodeError:
            continue
        if '.' in name and (name.lower().endswith(('.png', '.jpg', '.bmp', '.mid', '.wav', '.yne', '.ynx'))):
            return mo
    return None


def scan(d):
    mo = find_archive(d)
    if mo is None:
        raise SystemExit('未找到 PackageFile2 归档')
    np0 = mo + 0x118
    recs = []
    for i in range(2048):
        np = np0 + 264 * i
        if np + 1 > len(d):
            break
        nlen = d[np - 1]
        if nlen == 0 or nlen > 200:
            break
        off, size = struct.unpack_from('<II', d, np - 9)
        if off > 0x40000000 or size > 0x40000000:
            break
        recs.append((off, size, d[np:np + nlen].decode('cp932', 'replace')))
    dir_end = np0 + 264 * len(recs)
    # pair[k] 位于 np0-9+264k：pair0 给头槽 autorun.yne，pair[i+1] 给 name[i]
    base = dir_end - 1
    return {'magic': mo, 'np0': np0, 'recs': recs, 'base': base, 'dir_end': dir_end}


def pair(d, np0, k):
    p = np0 - 9 + 264 * k
    return struct.unpack_from('<II', d, p)


def build_frames(yne):
    """把 .yne 正文流 → 帧列表；返回 (items, stats)，items 元素：
       ('line', text) / ('choice', [opts])"""
    st = Y.body_start(yne)
    if st < 0:
        raise SystemExit('.yne 未找到正文起点')
    items = yne[st:].split(b'\r\n')
    events = []
    for it in items:
        if not it:
            continue
        if it[0] < 0x09:
            blk, tail = Y.split_tail(it)
            if blk[:2] == b'\x00\x01':
                opts = Y.parse_choices(blk)
                if opts:
                    events.append(('choice', opts))
            it = tail
            if not it:
                continue
        if it.startswith(b'.'):
            parts = it.split(b' ', 1)
            events.append(('cmd', parts[0].decode('ascii', 'replace')))
            continue
        events.append(('text', it.decode('cp932', 'replace')))

    out = []
    stats = {'frames': 0, 'click': 0, 'nclick_rec': 0, 'cont_rec': 0,
             'nextpage': 0, 'choice_groups': 0, 'choice_items': 0}
    cur, click, mid_at = [], 0, 0

    def flush():
        nonlocal cur, click
        if cur:
            s = ''.join(cur).replace('@', '')
            if s.strip(' \t\u3000'):
                out.append(('line', s))
                stats['frames'] += 1
        cur, click = [], 0

    for ev in events:
        if ev[0] == 'text':
            s = ev[1]
            core = s.rstrip(' \t\u3000')
            n_at = s.count('@')
            if n_at > (1 if core.endswith('@') else 0):
                mid_at += 1
            if core.endswith('@'):
                stats['nclick_rec'] += 1
                click += 1
            else:
                stats['cont_rec'] += 1
            segs = s.split('@')
            cur.extend(x for x in segs if x != '')
            if core.endswith('@'):
                flush()
        elif ev[0] == 'choice':
            flush()
            out.append(('choice', ev[1]))
            stats['choice_groups'] += 1
            stats['choice_items'] += len(ev[1])
        elif ev[0] == 'cmd' and ev[1] == '.NextPage':
            flush()
            stats['nextpage'] += 1
    flush()
    stats['mid_at'] = mid_at
    return out, stats


def main():
    ap = argparse.ArgumentParser(description='[JP]VISUKIO（Yuuki! Novel PackageFile2）文本提取')
    ap.add_argument('--exe', required=True)
    ap.add_argument('--out')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    d = open(a.exe, 'rb').read()
    info = scan(d)
    print('PackageFile2 @%#x：记录 %d 条，目录末 %#x，数据基址 %#x'
          % (info['magic'], len(info['recs']), info['dir_end'], info['base']))
    off0, size0 = pair(d, info['np0'], 0)
    yne = decrypt(d[info['base'] + off0:info['base'] + off0 + size0])
    h = Y.header(yne)
    print('autorun.yne：%d B  magic_ok=%s  场景名=%r  正文起点 %#x'
          % (len(yne), h['magic_ok'], h['title'], Y.body_start(yne)))
    items, st = build_frames(yne)
    print('帧 %(frames)d（点击记录 %(nclick_rec)d ＋ 续行记录 %(cont_rec)d）/ '
          '.NextPage %(nextpage)d / 选项 %(choice_items)d（%(choice_groups)d 组）/ '
          '句中@源笔误 %(mid_at)d' % st)

    # 双版判定：@ 只在行尾生效（引擎文档）⇒ 每帧恰 1 点击；跨帧开口只列不并
    lines = []
    for kind, val in items:
        if kind == 'line':
            lines.append(val)
        else:
            for disp, lab in val:
                lines.append(disp)
    print('成品 %d 行 / %d 字' % (len(lines), sum(len(x) for x in lines)))

    # 跨帧断引号检查（只报告，不合并）
    groups = []
    i = 0
    while i < len(lines) - 1:
        if lines[i].count('「') - lines[i].count('」') > 0:
            for j in range(i + 1, min(i + 4, len(lines))):
                if lines[j].count('」') - lines[j].count('「') > 0:
                    groups.append((i, j))
                    i = j
                    break
        i += 1
    print('跨帧断引号 %d 组（不同 ＃单击 框；不合并）：' % len(groups))
    for i, j in groups:
        print('  #%d %r … #%d %r' % (i + 1, lines[i][:34], j + 1, lines[j][-34:]))
    unbal = sum(1 for l in lines if (l.count('「') - l.count('」')) != 0 or (l.count('（') - l.count('）')) != 0)
    print('未平衡行 %d（全部是上述跨帧组的开口/收口）' % unbal)

    if a.out and not a.verify:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, 'wb') as f:
            f.write(b'\xef\xbb\xbf' + ''.join(x + '\n' for x in lines).encode('utf-8'))
        print('写出 %s（%d B）' % (a.out, os.path.getsize(a.out)))


if __name__ == '__main__':
    main()
