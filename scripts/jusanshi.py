#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""十三支演義 偃月三国伝1・2 (NS) 正文提取 —— 容器链全部打通版。

★ 关键结论（2026-10-26 第三轮确立，反编译 + 实测双重确认）：
  1) TextAsset(`m_Script`) 顶层就是 **MessagePack-CSharp 的 Lz4BlockArray**
     压缩格式：`array(N) = [ ext(98, N*3 字节 = N 个 msgpack uint16=各块解压后长度),
                            bin(块1), bin(块2), … ]`
     ⚠ 前人误判点：每个 bin 的**前 2 字节不是"块头"**，而是 **LZ4 block 的 token +
     字面量长度扩展字节**。所以"去掉 2 字节再拼"必然崩、按块单独 lz4 也 0 命中。
     正确做法：`lz4.block.decompress(bin_i, uncompressed_size=ext_i)` 逐块解压后**直接拼接**。
  2) 拼接流是**标准 MessagePack**：`{Functions: [ {Id,Type,Name,Contents,Elements} … ]}`，
     `AdvScriptElementFormatter` 写的是 `WriteMapHeader(5)` + 5 组(预编码 key 原文 + value)，
     没有任何私有 tag/len。旧报告"长度前缀与 msgpack 语义不符"作废。
  3) 正文 = 递归 Elements 树里 `Name == b"maintxt_print"`（章节名另有 `maintxt_print_c`）
     的 `Contents` 列表。

用法: python scripts/jusanshi.py <bundle目录> <out.txt> [--census]
"""
import argparse
import glob
import os
import re
import sys

import lz4.block
import msgpack
import UnityPy

# 主角名宏（1,355 处）：`#Name[1]` = 可改名主角的默认名槽，回填默认名 `関羽`
# 2026-10-27：原本靠交付时一条外部替换（`#Name[1]`→`関羽`），现内置，重跑即得成品
NAME_MAP = {'#Name[1]': '関羽'}

JP = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')
TEXT_CMDS = (b'maintxt_print', b'maintxt_print_c', b'maintxt_print_s')


def bundle_text(path):
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name == 'TextAsset':
            d = o.read()
            s = d.m_Script
            if isinstance(s, str):
                return name_of(o), s.encode('utf-8', 'surrogateescape')
            return name_of(o), bytes(s)
    return None, None


def name_of(o):
    try:
        return o.peek_name()
    except Exception:
        return None


def decompress_mp(raw):
    """Lz4BlockArray → 原始 msgpack 字节。"""
    top = msgpack.unpackb(raw, raw=True, strict_map_key=False)
    bins = [x for x in top if isinstance(x, (bytes, bytearray))]
    exts = [x for x in top if isinstance(x, msgpack.ExtType)]
    if not exts:
        # 未压缩
        return b''.join(bytes(b) for b in bins)
    ext = exts[0].data
    lens = [int.from_bytes(ext[i + 1:i + 3], 'big') for i in range(0, len(ext) - 2, 3)]
    if len(lens) != len(bins):
        # 极少见（280 里 6 个）：先试"未压缩直拼"，再试"逐块不限长解压"
        raw_join = b''.join(bytes(b) for b in bins)
        try:
            msgpack.unpackb(raw_join, raw=True, strict_map_key=False)
            return raw_join
        except Exception:
            pass
        out = []
        for c in bins:
            ok = None
            for us in (1 << 22, 1 << 20, 1 << 16, 32768, 4096):
                try:
                    ok = lz4.block.decompress(bytes(c), uncompressed_size=us)
                    break
                except Exception:
                    continue
            if ok is None:
                ok = bytes(c)
            out.append(ok)
        return b''.join(out)
    out = []
    for i, c in enumerate(bins):
        out.append(lz4.block.decompress(bytes(c), uncompressed_size=lens[i]))
    return b''.join(out)


def decode_clean(b):
    """UTF-8 解码，跳过夹在串内的二进制控制码（u16 op + u16 arg）。"""
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        pass
    out = []
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if c < 0x80:
            if 0x20 <= c < 0x7f or c in (0x0a, 0x09):
                out.append(chr(c))
                i += 1
            else:
                i += 1
            continue
        L = 4 if c >= 0xf0 else 3 if c >= 0xe0 else 2 if c >= 0xc2 else 0
        if L and i + L <= n:
            try:
                out.append(b[i:i + L].decode('utf-8'))
                i += L
                continue
            except UnicodeDecodeError:
                pass
        i += 4 if i + 4 <= n else 1
    return ''.join(out)


TAG = re.compile(r'<[^<>]{1,48}>')


def walk(elems, out, census=None, st=None):
    """按文档序遍历；**连续的 maintxt_print 属于同一个文本框（引擎逐行 print）**，
    合并成一行输出，遇到别的命令即封口 —— 这就是「一次点击 = 一行」。"""
    if not elems:
        return
    if st is None:
        st = {'kind': None, 'buf': []}
    for x in elems:
        nm = x.get(b'Name')
        c = x.get(b'Contents') or []
        if census is not None:
            census[(nm, x.get(b'Type'))] = census.get((nm, x.get(b'Type')), 0) + 1
        if nm in TEXT_CMDS and c:
            if st['kind'] is not None and st['kind'] != nm:
                flush(out, st)
            st['kind'] = nm
            st['buf'].append(''.join(decode_clean(y) for y in c if isinstance(y, (bytes, bytearray))))
        else:
            flush(out, st)
        walk(x.get(b'Elements'), out, census, st)
    flush(out, st, soft=True)


def flush(out, st, soft=False):
    if st['buf'] and soft:
        # 句中被迫换框（引擎在两行之间插了 voice_play 等）：引号未闭合就继续吸收
        t = ''.join(st['buf'])
        if t.count('「') > t.count('」') or t.count('（') > t.count('）'):
            st['kind'] = None
            return
    if st['buf']:
        line = ''.join(st['buf'])
        line = TAG.sub('', line)
        line = line.replace('\r', '').replace('\n', '').strip()
        if line and JP.search(line):
            out.append(line)
    st['kind'] = None
    st['buf'] = []


def key_order(p):
    m = re.search(r'advscripts-jyuza(\d)-(\d+)', os.path.basename(p))
    if not m:
        return (9, 0, p)
    return (int(m.group(1)), int(m.group(2)), p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('srcdir')
    ap.add_argument('out')
    ap.add_argument('--census', action='store_true')
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.srcdir, '*advscripts-jyuza*')), key=key_order)
    census = {} if a.census else None
    lines = []
    stat = []
    for p in files:
        nm, raw = bundle_text(p)
        try:
            body = decompress_mp(raw)
            doc = msgpack.unpackb(body, raw=True, strict_map_key=False)
        except Exception as e:
            stat.append((nm, 'ERR', str(e)))
            continue
        before = len(lines)
        walk(doc.get(b'Functions'), lines, census)
        stat.append((nm, len(lines) - before, len(raw)))

    # ★ 名字宏替换放在「成行完成之后」：`#Name[1]` 独占一框的行原本因「无日文字符」被丢弃，
    #   若在 flush 里替换，`関羽` 本身是日文，会把 88 行纯名框捞回来（行数 +88）
    for k, v in NAME_MAP.items():
        lines = [L.replace(k, v) for L in lines]

    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for L in lines:
            f.write(L + '\n')
    print('bundles', len(files), 'lines', len(lines))
    bad = [s for s in stat if s[1] == 'ERR']
    print('failed', len(bad))
    for s in bad[:5]:
        print('  ', s)
    if census is not None:
        import collections
        for k, v in collections.Counter(census).most_common(40):
            print(v, k)


if __name__ == '__main__':
    main()
