#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""恋してしまった星の王子 ～制裁院編～（NS / Bezel Engine）文本提取器

链路：BEA(SCNE, zstd) -> .scb 字节码 -> 文本

容器（Archive/script.nxonnx32.bea）
  header 0x20 u16 条目数 / 0x28 u64 指针表；条目 ASST：
  +0x10 comp(2=zstd) / +0x14 csize / +0x18 dsize / +0x20 数据地址 / +0x28 名字地址(u16 长度+UTF-8)
  ja 675 个 / en 747 个（en 独有 72 个＝日文侧标「未収録」）

.scb 头
  0x00 "scb_" / 0x08 code_start / 0x10 code_end / 0x18 字符串偏移表 / 0x20 字符串池

字节码记录：u16 op, u16 count(含自身) ; 随后 (count-1) 个 u32
  0x0b 名札（字符串索引，空串＝地の文）
  0x0c 正文（字符串索引）           ← 唯一正文 op
  0x11 点击等待                     ← 一次点击结束
  0x13 选项：3 组 × (选项文本, 跳转标签, 返回标签)
  0x1a/0x1e 章节梗概（arg0 与 0x0c 同一字符串索引，全库 92 处 100% 重复 ⇒ 不另收）

行粒度（L0 证据）
  ① 0x11 之前的 0x0c 文本条数只有 0 或 1（141769/141769 段）⇒ 一次点击 = 一条文本。
  ② 每个含文本的点击段必有 0x0b 名札 op（0 例外）⇒ 每次点击重设名札、重绘文本框
     ⇒ 不存在「同框内多次点击累加」⇒ 单版（无整页合并行）。
"""
import os
import struct
import sys

import zstandard as zstd


def read_bea(path):
    b = open(path, 'rb').read()
    if b[:4] != b'SCNE':
        raise ValueError('not BEA/SCNE: ' + path)
    n = struct.unpack_from('<H', b, 0x20)[0]
    ptr_tab = struct.unpack_from('<Q', b, 0x28)[0]
    out = []
    for i in range(n):
        off = struct.unpack_from('<Q', b, ptr_tab + 8 * i)[0]
        if b[off:off + 4] != b'ASST':
            continue
        comp = b[off + 0x10]
        csize = struct.unpack_from('<I', b, off + 0x14)[0]
        dsize = struct.unpack_from('<I', b, off + 0x18)[0]
        caddr = struct.unpack_from('<Q', b, off + 0x20)[0]
        naddr = struct.unpack_from('<Q', b, off + 0x28)[0]
        nlen = struct.unpack_from('<H', b, naddr)[0]
        out.append(dict(name=b[naddr + 2:naddr + 2 + nlen].decode('utf-8', 'replace'),
                        comp=comp, csize=csize, dsize=dsize, caddr=caddr))
    return b, out


def bea_decompress(b, e, dctx):
    raw = b[e['caddr']:e['caddr'] + e['csize']]
    if e['comp'] == 2:
        return dctx.decompress(raw, max_output_size=e['dsize'])
    if e['comp'] == 1:
        import zlib
        return zlib.decompress(raw)
    return raw


def bea_get(bea_path, want):
    b, ents = read_bea(bea_path)
    dctx = zstd.ZstdDecompressor()
    for e in ents:
        if e['name'] == want:
            return bea_decompress(b, e, dctx)
    return None


def parse_scb(data):
    if data[:4] != b'scb_':
        raise ValueError('not scb')
    code_start = struct.unpack_from('<I', data, 0x08)[0]
    code_end = struct.unpack_from('<I', data, 0x10)[0]
    strtab = struct.unpack_from('<I', data, 0x18)[0]
    pool_start = struct.unpack_from('<I', data, 0x20)[0]
    nstr = struct.unpack_from('<I', data, strtab)[0]
    offs = [struct.unpack_from('<I', data, strtab + 4 + 4 * i)[0] for i in range(nstr)]
    pool = data[pool_start:]
    strs = []
    for o in offs:
        e = pool.find(b'\x00', o)
        strs.append(pool[o:e].decode('utf-8', 'replace'))
    pos = code_start
    seq = []
    while pos + 4 <= code_end:
        op, cnt = struct.unpack_from('<HH', data, pos)
        if cnt == 0:
            break
        nargs = cnt - 1
        if pos + 4 + 4 * nargs > code_end:
            raise ValueError('op overflow at %#x' % pos)
        args = list(struct.unpack_from('<%dI' % nargs, data, pos + 4)) if nargs else []
        seq.append((op, args))
        pos += 4 + 4 * nargs
    return strs, seq


def load_id_order(script_bin):
    """static/script.bin：u32[2]=条目数，0x14=id 偏移表，0x18=字符串池基址。"""
    cnt = struct.unpack_from('<I', script_bin, 8)[0]
    offtab = struct.unpack_from('<I', script_bin, 0x14)[0]
    strtab = struct.unpack_from('<I', script_bin, 0x18)[0]
    order = []
    for i in range(cnt):
        o = strtab + struct.unpack_from('<I', script_bin, offtab + 4 * i)[0]
        e = script_bin.find(b'\x00', o)
        s = script_bin[o:e].decode('latin1')
        if len(s) == 9 and s.isdigit():
            order.append(s)
    return order


def expand(s, surname, given):
    s = s.replace('\n', '')
    return s.replace('#NAME[1]', surname).replace('#NAME[2]', given)


def scb_lines(data, surname, given):
    """→ [(kind, line)]；kind: 'T' 正文/名札、'O' 选项"""
    strs, seq = parse_scb(data)
    out = []
    cur_name = ''
    for op, args in seq:
        if op == 0x0b:
            cur_name = strs[args[0]] if args and args[0] < len(strs) else ''
        elif op == 0x0c:
            txt = strs[args[0]] if args and args[0] < len(strs) else ''
            if not txt:
                continue          # 8,278 次纯演出点击（无正文）
            txt = expand(txt, surname, given)
            name = expand(cur_name, surname, given)
            out.append(('T', name + txt if name else txt))
        elif op == 0x13:
            for g in range(0, len(args) - 2, 3):
                oi = args[g]
                if oi < len(strs) and strs[oi]:
                    out.append(('O', expand(strs[oi], surname, given)))
    return out, strs, seq


def main():
    romfs = sys.argv[1]
    out_path = sys.argv[2]
    surname = sys.argv[3] if len(sys.argv) > 3 else '立花'
    given = sys.argv[4] if len(sys.argv) > 4 else 'なつみ'

    arch = os.path.join(romfs, 'Archive')
    script_bea = os.path.join(arch, 'script.nxonnx32.bea')
    script_bin = bea_get(os.path.join(arch, 'static~script.bin.nxonnx32.jaJP.bea'),
                         'static/script.bin')
    order = load_id_order(script_bin)

    b, ents = read_bea(script_bea)
    dctx = zstd.ZstdDecompressor()
    ja = {}
    for e in ents:
        if e['name'].startswith('script/ja/'):
            ja[os.path.basename(e['name'])[:-4]] = bea_decompress(b, e, dctx)

    seen_body = {}
    lines = []
    st = dict(files=0, dup_files=0, texts=0, options=0, nameplate=0, narration=0)
    for sid in order:
        data = ja.get(sid)
        if data is None:
            continue
        body, strs, seq = scb_lines(data, surname, given)
        key = tuple(x for x in body)
        if key in seen_body:
            st['dup_files'] += 1
            continue
        seen_body[key] = sid
        st['files'] += 1
        for kind, line in body:
            if kind == 'O':
                lines.append('◆' + line)
                st['options'] += 1
            else:
                lines.append(line)
                st['texts'] += 1
                if line[:len(line) - len(line.lstrip())] == '' and line.count('「') and line.split('「')[0]:
                    st['nameplate'] += 1
                else:
                    st['narration'] += 1

    print(st, 'total lines:', len(lines))
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
