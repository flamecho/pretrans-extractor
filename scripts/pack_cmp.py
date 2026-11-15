#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VividColor «GameSystem» `*.cmp` PACK 容器工具（PC）。

适用：`PACK/*.cmp` 五包结构（INI / SCRIPT / GRAPHIC / SOUND / VOICE）。
引擎：VividColor 自研 GameSystem（脚本为 Xerces-C XML，见 `engines/vividcolor.md`）。

容器布局
--------
    [0x0000, 0x6400)   PE 壳（同模板，仅作 SFX 载体，不参与解压）
    [0x6400, idx)      载荷
    [idx,  EOF-8)      索引区（自身亦为同一压缩流；前 4 B = 索引解压后长度）
    [EOF-8, EOF-4)     ASCII "PACK"
    [EOF-4, EOF)       u32 LE 索引区起点

索引条目（10 字节头）
--------------------
    u32 偏移 | u8 名字字符数 | u8 标志(=1) | u32 保留(=0) | UTF-16LE 成员名
    终止条目：名字字符数 == 0

压缩（LZSS 变体，位域取自 `FileSystem.mod @0x5030` 反汇编）
---------------------------------------------------------
    b <  0x80 : 字面段，长度 = b + 1（1..128）
    b >= 0x80 : 2 字节回引 token  v = (b<<8)|src[p+1]
                len  = ((v >> 10) & 0x1E) + 2      # 恒偶数 2..32（bit10 丢弃）
                dist = (v & 0x7FF) + 1             # 1..2048

成员三种存储形态（按序判定，非穷举）
----------------------------------
    ① 压缩      : u32 raw 头 + 解压恰好 raw 字节 + 不限长消耗 == span-4
    ② 裸存无头  : 成员 = data[off:nxt]（SOUND/VOICE 的 .ogg、GRAPHIC 的 .chr）
    ③ 裸存带头  : u32 == span-4（本引擎尚未见到）

用法
----
    python scripts/pack_cmp.py list    PACK/SCRIPT.cmp
    python scripts/pack_cmp.py extract PACK/GRAPHIC.cmp -o out/graphic
    python scripts/pack_cmp.py text    PACK/SCRIPT.cmp -o out/script.txt [--name ユーリ]
    python scripts/pack_cmp.py raw     PACK/SCRIPT.cmp baseOMAKE.XML
"""
import argparse
import os
import struct
import sys

PAYLOAD_BASE = 0x6400      # 五包一致，实测
ENTRY_HDR = 10


# ---------------------------------------------------------------- 解压
def decompress(src, out_len=None, limit=None):
    """LZSS 变体解压。out_len=None 时解到流尾（用于「消耗量」校验）。

    返回 (data, consumed)。
    """
    out = bytearray()
    p = 0
    n = len(src) if limit is None else min(limit, len(src))
    target = float('inf') if out_len is None else out_len
    while p < n and len(out) < target:
        b = src[p]
        p += 1
        if b < 0x80:                       # 字面段：长度 = b + 1
            ln = b + 1
            take = min(ln, n - p)
            if out_len is not None:
                take = min(take, out_len - len(out))
            out += src[p:p + take]
            p += ln
            if take < ln:
                break
        else:                              # 回引 token
            if p >= n:
                break
            v = (b << 8) | src[p]
            p += 1
            ln = ((v >> 10) & 0x1E) + 2
            dist = (v & 0x7FF) + 1
            st = len(out) - dist
            if st < 0:
                raise ValueError('dist 越界 @src 0x%X（out=%d, dist=%d）' % (p - 2, len(out), dist))
            for k in range(ln):
                out.append(out[st + k])
                if len(out) >= target:
                    break
    return bytes(out), p


# ---------------------------------------------------------------- 索引
def parse_index(data):
    """返回 (members, idx_offset, index_bytes)。members = [(offset, name), ...]"""
    if len(data) < 12 or data[-8:-4] != b'PACK':
        raise ValueError('尾部 "PACK" 标记缺失，不是本引擎的 .cmp')
    idx = struct.unpack_from('<I', data, len(data) - 4)[0]
    if not 0 < idx < len(data) - 8:
        raise ValueError('索引偏移越界 0x%X' % idx)
    ireg = data[idx:len(data) - 8]
    declared = struct.unpack_from('<I', ireg, 0)[0]
    raw, _ = decompress(ireg[4:], declared)
    if len(raw) != declared:
        raise ValueError('索引解出 %d != 声明 %d' % (len(raw), declared))

    members = []
    p = 0
    while p + ENTRY_HDR <= len(raw):
        off = struct.unpack_from('<I', raw, p)[0]
        nlen = raw[p + 4]
        p += ENTRY_HDR
        if nlen == 0:
            break
        if p + nlen * 2 > len(raw):
            raise ValueError('名字越界 @0x%X' % p)
        name = raw[p:p + nlen * 2].decode('utf-16le')
        p += nlen * 2
        members.append((off, name))
    return members, idx, len(ireg)


# ---------------------------------------------------------------- 成员
def member_bytes(data, off, nxt):
    """按三种存储形态取成员原始字节。返回 (data, kind)。"""
    span = nxt - off
    if span <= 0:
        return b'', 'empty'
    if span > 4:
        raw_len = struct.unpack_from('<I', data, off)[0]
        if 0 < raw_len <= 512 * 1024 * 1024 and span - 4 != raw_len:
            try:
                buf, used = decompress(data[off + 4:nxt], raw_len)
                if len(buf) == raw_len and used == span - 4:
                    return buf, 'comp'
            except ValueError:
                pass
        elif span - 4 == raw_len:
            return data[off + 4:nxt], 'raw+hdr'
    return data[off:nxt], 'raw'


def iter_members(cmp_path):
    data = open(cmp_path, 'rb').read()
    members, idx, ilen = parse_index(data)
    for i, (off, name) in enumerate(members):
        nxt = members[i + 1][0] if i + 1 < len(members) else idx
        buf, kind = member_bytes(data, off, nxt)
        yield name, buf, kind, off


# ---------------------------------------------------------------- 成行
def script_lines(cmp_path):
    """从 SCRIPT.cmp 还原「一次点击 = 一行」。

    判据（L1，记录自定界 + 交叉验证）：
      <RESOURCE> 首参 0 → 台词，正文 = 第 3 个 <CREATE type="STR">，后随 <FUNCTION name="MESSAGE"/>
      <RESOURCE> 首参 1 → 选项，正文 = 组内全部 <CREATE type="STR">，后随 <FUNCTION name="SELECT"/>
    说话人为独立名字窗（MESSAGE.INI 的 NameTexture/NameArea）⇒ 剔除，不加前缀。
    """
    import xml.etree.ElementTree as ET

    lines = []
    for name, buf, kind, off in iter_members(cmp_path):
        if kind == 'raw' and not buf.lstrip().startswith(b'<?xml'):
            continue
        try:
            root = ET.fromstring(buf)
        except ET.ParseError:
            continue
        for res in root.iter('RESOURCE'):
            kids = list(res)
            if not kids:
                continue
            if kids[0].text == '0':
                txt = kids[2].text if len(kids) > 2 else ''
                if txt and txt.strip():
                    lines.append(txt.replace('\t', ''))
            else:
                for k in kids:
                    if k.get('type') == 'STR' and k.text and k.text.strip():
                        lines.append(k.text.replace('\t', ''))
    return lines


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description='VividColor GameSystem *.cmp PACK 工具')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('list', help='列出索引成员')
    p.add_argument('cmp')

    p = sub.add_parser('extract', help='全部成员解包到目录')
    p.add_argument('cmp')
    p.add_argument('-o', '--out', required=True)

    p = sub.add_parser('raw', help='取单个成员到 stdout')
    p.add_argument('cmp')
    p.add_argument('name')

    p = sub.add_parser('text', help='SCRIPT.cmp → 一行一次点击的文本')
    p.add_argument('cmp')
    p.add_argument('-o', '--out', required=True)

    a = ap.parse_args()

    if a.cmd == 'list':
        members, idx, ilen = parse_index(open(a.cmp, 'rb').read())
        data = open(a.cmp, 'rb').read()
        print('%s  索引区 %d B  idx=0x%X  成员 %d' % (os.path.basename(a.cmp), ilen, idx, len(members)))
        for i, (off, name) in enumerate(members):
            nxt = members[i + 1][0] if i + 1 < len(members) else idx
            buf, kind = member_bytes(data, off, nxt)
            print('  [%4d] 0x%08X %-46s %-7s %9d B' % (i, off, name, kind, len(buf)))

    elif a.cmd == 'extract':
        os.makedirs(a.out, exist_ok=True)
        n = 0
        for name, buf, kind, off in iter_members(a.cmp):
            path = os.path.join(a.out, name.replace('/', os.sep))
            os.makedirs(os.path.dirname(path) or a.out, exist_ok=True)
            with open(path, 'wb') as fh:
                fh.write(buf)
            n += 1
        print('解包 %d 个成员 → %s' % (n, a.out))

    elif a.cmd == 'raw':
        for name, buf, kind, off in iter_members(a.cmp):
            if name.lower() == a.name.lower():
                sys.stdout.buffer.write(buf)
                return 0
        print('未找到成员 %s' % a.name, file=sys.stderr)
        return 1

    elif a.cmd == 'text':
        lines = script_lines(a.cmp)
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as fh:
            fh.write('\n'.join(lines) + '\n')
        print('产出 %d 行 → %s' % (len(lines), a.out))

    return 0


if __name__ == '__main__':
    sys.exit(main())
