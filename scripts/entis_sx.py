# -*- coding: utf-8 -*-
"""Entis / Sakura-OS Executable (gigolo.sx) 文本字面量提取

容器事实（[JP]GIGOLO 实测，2026-11-03）：
  文件头 "Entis\\x1a" + "Sakura-OS Executable"
  chunk 链： "informat"（原生类/函数名表，SArchive/SText/SInterface/...）
            + "codedata"（字节码 + **交织其间的 UTF-16LE 字面量**）
  正文不是独立文本文件 —— 字面量直接编译在 codedata 里。

判据（全部落在字节上，L1 自定界）：
  1) 一个字面量 = 一个文本框 = 一次点击；以 00 00（UTF-16 NUL）结尾；
  2) 字面量内部 0A 00（U+000A）= 作者硬换行，非断框依据；
  3) 续行恰好以 3 个 00 30（U+3000）悬挂缩进开头 -> 剥掉后拼接（不插空格）；
  4) 实测框高上限 4 行（与消息窗一致），故无分屏双版需求；
  5) 台词字面量内嵌「名字＋U+3000＋「…」」-> 名字同行保留（无独立名字窗）。

用法:
  # 1) 先全量 dump 带偏移的字面量，人工/统计找出剧本区间
  python scripts/entis_sx.py --sx data/gigolo.sx --dump all.tsv
  # 2) 按区间成行（可多段）
  python scripts/entis_sx.py --sx data/gigolo.sx --out out.txt \
      --range 0x96EC8:0x9F760 --range 0xA1C40:0xA3D10
"""
import argparse
import hashlib
import io
import sys

HDR = b'Entis\x1a'

# 允许出现在正文里的「非假名非常用汉字」标点/符号（各家引擎写法不同，按需增补）
EXTRA = {0x0a, 0x2026, 0x2015, 0x2190, 0x2192, 0x25a0, 0x25cb, 0x25cf, 0x301c,
         0x2018, 0x2019, 0x201c, 0x201d, 0x203b, 0x2605, 0x2606, 0x266a, 0x266b,
         0x21d2, 0x21d4, 0x2261, 0x2262, 0x00d7, 0x00f7, 0x00b1, 0x00b0, 0x2103,
         0x2116, 0x2121, 0x3010, 0x3011, 0x3008, 0x3009, 0x300a, 0x300b,
         0x30fb, 0x301c, 0xff5e}

ZEN = '\u3000'
INDENT = ZEN * 3
MAXLIT = 4000


def ok_unit(c):
    return ((0x20 <= c < 0x7f) or (0x3000 <= c <= 0x30ff) or (0x4e00 <= c <= 0x9fff)
            or (0xff01 <= c <= 0xff60) or (c in EXTRA))


def read_at(D, p, end):
    """从偶偏移读 NUL 结尾 UTF-16LE；遇非法 unit 返回 None（调用方 +2 重新对齐）。"""
    i, out, n = p, [], len(D)
    while i + 1 < n and i < end:
        c = D[i] | (D[i + 1] << 8)
        if c == 0:
            return ''.join(out), i + 2
        if not ok_unit(c):
            return None
        out.append(chr(c))
        i += 2
        if len(out) > MAXLIT:
            return None
    return None


def scan(D, a, b):
    """a..b 只约束**起始偏移**；字面量本身可能跨过 b（末尾一条常跨区间边界），
    故读取上限取文件长度，否则会静默丢掉最后一条。"""
    p, res, n = a, [], len(D)
    while p < b:
        r = read_at(D, p, n)
        if r and r[0]:
            res.append((p, r[0]))
            p = r[1]
        else:
            p += 2
    return res


def has_jp(s):
    return any(0x3040 <= ord(c) <= 0x30ff or 0x4e00 <= ord(c) <= 0x9fff for c in s)


def is_content(s):
    """含日文、且不含路径分隔符 / printf 占位符（滤掉资源路径与格式化串）。"""
    if not has_jp(s):
        return False
    if '\\' in s or '%' in s:
        return False
    return True


def merge(s):
    lines = s.split('\n')
    buf = [lines[0]]
    for ln in lines[1:]:
        buf.append(ln[len(INDENT):] if ln.startswith(INDENT) else ln)
    return ''.join(buf)


def parse_range(x):
    a, b = x.split(':')
    return int(a, 0), int(b, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sx', required=True)
    ap.add_argument('--out', help='成行输出（UTF-8 BOM + LF）')
    ap.add_argument('--range', action='append', default=[],
                    help='字节区间 a:b（可多次），支持 0x 前缀')
    ap.add_argument('--dump', help='全量 dump 字面量（偏移 \\t 文本）')
    ap.add_argument('--all', action='store_true',
                    help='dump 时不过滤（连资源路径/格式化串一起）')
    ap.add_argument('--no-merge', action='store_true', help='不合并硬换行（调试用）')
    a = ap.parse_args()

    with open(a.sx, 'rb') as f:
        D = f.read()
    if D[:6] != HDR:
        print('警告：文件头不是 Entis\\x1a', file=sys.stderr)
    N = len(D)

    if a.dump:
        hi = 0x60
        for r in a.range:
            _lo, b = parse_range(r)
            hi = max(hi, b)
        spans = [parse_range(r) for r in a.range] or [(0x60, N)]
        rows = []
        for lo, b in spans:
            for off, s in scan(D, lo, b):
                if a.all or is_content(s):
                    rows.append((off, s))
        with io.open(a.dump, 'w', encoding='utf-8', newline='\n') as f:
            for off, s in rows:
                f.write('0x%08x\t%s\n' % (off, s.replace('\n', '\\n')))
        print('%d literals -> %s' % (len(rows), a.dump), file=sys.stderr)

    if a.out:
        if not a.range:
            sys.exit('--out 需要至少一个 --range（先用 --dump 找区间）')
        rows = []
        for spec in a.range:
            lo, b = parse_range(spec)
            keep = 0
            for off, s in scan(D, lo, b):
                if not is_content(s):
                    continue
                rows.append((off, s if a.no_merge else merge(s)))
                keep += 1
            print('%s: %d boxes' % (spec, keep), file=sys.stderr)
        for off, s in rows:
            assert s and '\n' not in s, '0x%x 仍含换行' % off
        with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            for _off, s in rows:
                f.write(s + '\n')
        blob = open(a.out, 'rb').read()
        widths = sorted(len(s) for _o, s in rows)
        print('lines %d / bytes %d / md5 %s / CRLF %d / BOM %s' % (
            len(rows), len(blob), hashlib.md5(blob).hexdigest(),
            blob.count(b'\r\n'), blob[:3] == b'\xef\xbb\xbf'), file=sys.stderr)
        if widths:
            print('max width %d / median %d' % (
                widths[-1], widths[len(widths) // 2]), file=sys.stderr)


if __name__ == '__main__':
    main()
