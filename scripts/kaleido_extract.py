#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カレイドイヴ (PSV / PCSG00520 / estciel & HuneX) 全文本提取器
================================================================
输入：PFS 解密后的 PCSG00520/data/ 目录（须含 allscr.hed + allscr.mrg）
输出：UTF-8(BOM) + 纯 LF 的全文本 txt，一次点击 = 一个文本框 = 一行。

引擎：HuneX「Ogre」系。脚本容器 allscr.hed/.mrg：
  mrg 头 = 171 条 32B 脚本名表（'CH00_A'..'CH07_SP06'）+ 内嵌 mrgd00；
  hed  = 176 条 8B 通用条目（offset,size），小端、0x800 扇区；
  每个脚本 = MZX0 压缩流（字面字节 XOR 0xFF）。
脚本指令以 ';' 分隔，形如 `_CMD(args)`：
  _ZM<id>(text)  一次点击显示的一个文本框（@n=框内换页/再点击，^=框内软换行）
  _MSAD(text)    续接当前文本框
  _MTLK(1,名前)   说话人名（本器不输出）
  _SELR(n,text)   选项（每项一行）
  _LVSV(...)      章节标题（MISSION/END/AFTERSTORY/INTRODUCTION）
  @w/@h/@e + 数字 演出/结束标记（删）
  ＊Ａ/＊Ｂ       主角姓名占位符（→ 葉山 / 翼，inline）
用法： python kaleido_extract.py <解密后的 data 目录> <输出.txt> [--merge-atn]
  --merge-atn  把 @n（框内换页）也并成同一行（合并版）；默认 @n 拆为独立行（原文版）
"""
import struct, io, re, sys, os

HERO_SURNAME = '葉山'
HERO_GIVEN = '翼'


def mzx0_decompress(data, inlen, exlen, xorff=True):
    """HuneX MZX0 (LZ77 变体) 解压；xorff=True 时字面字节 XOR 0xFF。"""
    key = 0xFF
    out = bytearray()
    ring = [b'\xFF\xFF'] * 64 if xorff else [b'\x00\x00'] * 64
    rw = 0
    f = io.BytesIO(data)
    cl = 0
    last = b'\xFF\xFF' if xorff else b'\x00\x00'
    while len(out) < exlen:
        if f.tell() >= inlen:
            break
        if cl <= 0:
            cl = 0x1000
            last = b'\xFF\xFF' if xorff else b'\x00\x00'
        fl = f.read(1)[0]
        cl -= 1 if (fl & 3) == 2 else fl // 4 + 1
        if (fl & 3) == 0:
            out += last * ((fl // 4) + 1)
        elif (fl & 3) == 1:
            k = 2 * (f.read(1)[0] + 1)
            for _ in range(fl // 4 + 1):
                last = bytes(out[len(out) - k:len(out) - k + 2])
                out += last
        elif (fl & 3) == 2:
            last = ring[fl // 4]
            out += last
        else:
            for _ in range(fl // 4 + 1):
                b = f.read(2)
                if xorff:
                    b = bytes(x ^ key for x in b)
                last = bytes(b)
                ring[rw] = last
                rw = (rw + 1) % 64
                out += last
    del out[exlen:]
    return bytes(out)


def hed_entry(blk):
    """allscr.hed 通用条目：<HHHH> ofs_low, ofs_high, size_sect, size_low"""
    ol, oh, ss, sl = struct.unpack('<HHHH', blk)
    off = 0x800 * ((oh & 0xF000) << 4 | ol)
    size = 0x800 * ss if sl == 0 else (0x800 * (ss - 1) & 0xFFFF0000) | sl
    return off, size


def load_scripts(data_dir):
    h = open(os.path.join(data_dir, 'allscr.hed'), 'rb').read()
    m = open(os.path.join(data_dir, 'allscr.mrg'), 'rb').read()
    names, i = [], 0
    while i + 32 <= len(m):
        r = m[i:i + 32]
        if r[30:32] == b'\x0d\x0a':
            names.append(r[:30].rstrip(b'\x00').decode('cp932', 'replace'))
            i += 32
        else:
            break
    out = []
    for k in range(len(h) // 8):
        off, size = hed_entry(h[k * 8:k * 8 + 8])
        if m[off:off + 4] == b'MZX0':
            exlen = struct.unpack('<L', m[off + 4:off + 8])[0]
            txt = mzx0_decompress(m[off + 8:off + size], size - 8, exlen).decode('cp932', 'replace')
            out.append((names[len(out)], txt))
    return out


EFF = re.compile(r'@[whe]\d*')   # @w<n>/@h<n> 演出、@e 结束（非显示文本）


def clean(t):
    t = t.replace('＊Ａ', HERO_SURNAME).replace('＊Ｂ', HERO_GIVEN)
    t = EFF.sub('', t)
    t = t.replace('^', '')       # 框内软换行 -> 合并
    return t


def extract(data_dir, merge_atn=False):
    """merge_atn=False（默认）：@n=框内换页 -> 拆为独立行（原文版）
       merge_atn=True         ：@n=框内换页 -> 与前后合并为同一行（合并版）"""
    lines = []
    for nm, tx in load_scripts(data_dir):
        # EVCG = 事件CG回放，与正章逐字重复；TEST_SCRIPT = 开发残留（排版/注音测试）
        if '_EVCG_' in nm or nm == 'TEST_SCRIPT':
            continue
        buf = ''
        for tok in tx.split(';'):
            tok = tok.strip()
            mm = re.match(r'^_([A-Za-z0-9]+)\(', tok)
            if not mm:
                continue
            cmd = mm.group(1)
            args = tok[mm.end():].rstrip(')')   # 去掉指令右侧闭括号（数目随指令而异）
            if cmd.startswith('ZM') or cmd == 'MSAD':
                if cmd.startswith('ZM') and buf:      # 新 ZM = 新文本框
                    lines.append(buf); buf = ''
                segs = clean(args).split('@n')        # @n = 框内换页（再点击）
                if merge_atn:
                    segs = [''.join(segs)]            # 合并版：@n 不拆行
                for k, s in enumerate(segs):
                    buf += s
                    if k < len(segs) - 1:
                        if buf: lines.append(buf)
                        buf = ''
            elif cmd == 'SELR':                        # 选项（每项一行）
                if buf:
                    lines.append(buf); buf = ''
                lines.append(args.split(',', 1)[1] if ',' in args else args)
            elif cmd == 'LVSV':                        # 章节标题
                if buf:
                    lines.append(buf); buf = ''
                lines.append(args)
        if buf:
            lines.append(buf)
    return lines


if __name__ == '__main__':
    argv = [a for a in sys.argv[1:] if not a.startswith('--')]
    merge = '--merge-atn' in sys.argv
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    data_dir, out_path = argv[0], argv[1]
    lines = extract(data_dir, merge_atn=merge)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('%d lines (%s) -> %s' % (len(lines), 'merged @n' if merge else 'split @n', out_path))
