# -*- coding: utf-8 -*-
"""Entis / EMSAC-Binary Archive-2  (gigolo.arc, *.arc of Entis GLS titles)

列出归档目录树（叶子 + 目录），供定位剧本 / 图像 / 语音。

容器事实（[JP]GIGOLO 实测，2026-11-03）：
  文件头   "Entis\\x1a" + 12 B + "EMSAC-Binary Archive-2" 填至 0x40
  之后     chunk 链： tag(8 B ASCII) + u64 size + 数据区
  有意义的 chunk 只有 "DirEntry"：
      tag_off+0x08 = u64 size      数据区长度
      tag_off+0x10 = u32 count     条目数          <- 「父数据起」= 这里
      tag_off+0x14 起 count 条：
        entry = 9 x u32  ([0..2]=0/0/0x10, [4]=offset, [6]=mtime, [8]=pathlen)
              + u32 pathlen + path(cp932, NUL 结尾)
              + u32 namelen + name(NUL 结尾)
      ★ offset 相对「父 DirEntry 数据起」(tag_off+0x10)，不是文件绝对偏移。
        子目录的 DirEntry 也按同一基准定位；漏掉这一条会把 offset 落进路径串中间。

用法:
  python scripts/entis_arc.py --arc data/gigolo.arc            # 打印树
  python scripts/entis_arc.py --arc data/gigolo.arc --leaves   # 只打印叶子
  python scripts/entis_arc.py --arc data/gigolo.arc --dump out.txt
"""
import argparse
import struct
import sys

MAGIC_HDR = b'Entis\x1a'


def load(path):
    with open(path, 'rb') as f:
        return f.read()


def parse_dir(blob, tag_off):
    """返回 (entries, data_end)；entries = [(name, offset, size, mtime)]，解析失败返回 None。"""
    n = len(blob)
    if tag_off + 0x14 > n or blob[tag_off:tag_off + 8] != b'DirEntry':
        return None
    size = struct.unpack_from('<Q', blob, tag_off + 0x08)[0]
    end = tag_off + 0x10 + size
    if not (0 < size and end <= n):
        return None
    o = tag_off + 0x14
    out = []
    while o < end - 36:
        f = struct.unpack_from('<9I', blob, o)
        plen = f[8]
        if not (8 < plen < 400):
            return None
        path = blob[o + 36:o + 36 + plen]
        if path[-1:] != b'\0':
            return None
        q = o + 36 + plen
        nlen = struct.unpack_from('<I', blob, q)[0]
        if not (1 < nlen < 300):
            return None
        name = blob[q + 4:q + 4 + nlen]
        if name[-1:] != b'\0':
            return None
        out.append((name[:-1].decode('cp932', 'replace'), f[4], f[6], f[7]))
        o = q + 4 + nlen
    return out, end


def find_root(blob):
    """文件头 0x40 处若就是 DirEntry 直接用；否则按 chunk 链找第一个 DirEntry。"""
    if blob[:6] == MAGIC_HDR and blob[0x40:0x48] == b'DirEntry':
        return 0x40
    p = 0x40
    n = len(blob)
    while p + 16 <= n:
        if blob[p:p + 8] == b'DirEntry':
            return p
        size = struct.unpack_from('<Q', blob, p + 8)[0]
        if not (0 < size < n):
            break
        p += 0x10 + size
    return None


def walk(blob, tag_off, prefix='', depth=0, lines=None, leaves=None):
    r = parse_dir(blob, tag_off)
    if not r:
        lines.append('  ' * depth + 'PARSEFAIL @0x%x' % tag_off)
        return
    ents, _end = r
    base = tag_off + 0x10          # ★ 所有 offset 的基准
    for name, off, size, mtime in ents:
        abs_off = base + off
        if blob[abs_off:abs_off + 8] == b'DirEntry':
            lines.append('  ' * depth + '[D] %-24s @0x%08x' % (name, abs_off))
            if depth < 12:
                walk(blob, abs_off, prefix + name + '/', depth + 1, lines, leaves)
        else:
            head = blob[abs_off:abs_off + 8]
            lines.append('  ' * depth + '[F] %-24s @0x%08x %s' % (name, abs_off, head.hex(' ')))
            leaves.append((prefix + name, abs_off, size))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arc', required=True)
    ap.add_argument('--leaves', action='store_true', help='只输出叶子文件清单')
    ap.add_argument('--dump', help='把结果写进文本文件（UTF-8）')
    a = ap.parse_args()

    blob = load(a.arc)
    root = find_root(blob)
    if root is None:
        sys.exit('未找到 DirEntry 根：%s' % a.arc)

    lines, leaves = [], []
    walk(blob, root, lines=lines, leaves=leaves)

    if a.leaves:
        body = [p for p, _o, _s in leaves]
    else:
        body = lines
    body.append('')
    body.append('leaves %d / dirs %d' % (
        len(leaves), sum(1 for l in lines if '[D]' in l)))
    text = '\n'.join(body)
    if a.dump:
        with open(a.dump, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text + '\n')
        print('-> %s' % a.dump)
    else:
        print(text)


if __name__ == '__main__':
    main()
