#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""even if TEMPEST 連なるときの暁（Switch / Nintendo **Bezel Engine**）剧本文本提取。

链路：NSP(PFS0) → NCA(keygen16 / Titlekey crypto, 未压缩 romfs) → Archive/static~NN_MM.bin.nx.bea
      → SCNE 容器 → zstd 负载 → "BIN_" 字符串池

★ 格式（2026-10-26 实测）：
  SCNE 头 0x00 'SCNE'，0x110 处 '_RLT' 段之后是 **单个 zstd 帧**（magic 28 B5 2F FD）。
  解压得 `BIN_` 池：
    0x00 'BIN_'  0x04 u32  0x08 u32  0x0C u32 = 字符串数 N
    0x10 u32 (=0x1C)  0x14 u32  0x18 u32 = 字符串区起点 base  0x1C 起 N×u32 偏移（相对 base）
    字符串 = NUL 结尾 UTF-8
  池内顺序 = [ID/标签串] + [日文正文块] + [英文正文块]（两语言块等长）
  ⇒ 从「第一条含假名/汉字的串」起，取一半即日文正文，顺序即脚本顺序（实测通读连贯）。

★ 成行（L0）：一个字符串 = 一个文本框（= 一次点击）；框内 `\n` 为排版换行 ⇒ 合并。
  实测：单框最多 3 行（8,910/5,390/3,131 条为 1/2/3 行），续行 99.6% 不缩进，行宽上限 32 字。
  仅 100 条「新聞記事」为整页文本（4–15 行，行首 　 段首缩进），同样按一框一行合并。

★ 宏：`######`（390 处）= 主角名占位（可改名），官方默认名 **アナスタシア**
  （同文件内并存 '「あ！　アナスタシア！」' 与 '「あ！　######！」' 两条，可互证）。
  引擎转义：`\\f`（清页）、`\\cN`（改色）⇒ 剥除。

用法：
  python scripts/bezel_extract.py <解包目录（含 Archive/static~*.nx.bea）> --out <txt> [--json <dump>]
"""
import sys, os, re, json, glob, struct

import zstandard

NAME_MAP = {'######': 'アナスタシア'}
ESC = re.compile(r'\\[fc][0-9]?')
SPK = re.compile(r'#[sS]\d+')  # 话者名宏（localize/clue 各 1 处），静态不可解 ⇒ 统一占位
ORDER_HEAD = ['00_01', '01_01', '02_01', '03_01', '04_01', '05_01', '06_01', '07_01', '08_01', '09_01',
              '10_01', '11_01', '12_01', '13_01', '14_01', '15_01', '16_01', '17_01', '18_01', '19_01',
              '20_01', '21_01', '22_01', '23_01', '24_01', '25_01', '26_01', '27_01', '90_01', '91_01']


def scne_payload(b):
    j = b.find(b'\x28\xb5\x2f\xfd')
    if j < 0:
        raise ValueError('no zstd')
    return zstandard.ZstdDecompressor().decompress(b[j:], max_output_size=256 << 20)


def parse_pool(d):
    assert d[:4] == b'BIN_', d[:4]
    n = struct.unpack_from('<I', d, 0x0C)[0]
    base = struct.unpack_from('<I', d, 0x18)[0]
    offs = struct.unpack_from('<%dI' % n, d, 0x1C)
    out = []
    for o in offs:
        e = d.index(b'\x00', base + o)
        out.append(d[base + o:e].decode('utf-8', 'replace'))
    return out


JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def clean(t):
    for k, v in NAME_MAP.items():
        t = t.replace(k, v)
    t = ESC.sub('', t)
    t = SPK.sub('〔話者名〕', t)
    t = t.replace('\n', '')
    return t.strip('\u3000 \t')


def main():
    srcdir = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None

    files = {}
    for p in glob.glob(os.path.join(srcdir, '**', 'static~*.nx.bea'), recursive=True):
        nm = os.path.basename(p).replace('static~', '').replace('.bin.nx.bea', '').replace('.nx.bea', '')
        files[nm] = p
    seq = [k for k in ORDER_HEAD if k in files]
    print('[i] 找到脚本池 %d 个，按章节序取 %d 个' % (len(files), len(seq)))

    lines, stat = [], {}
    for k in seq:
        d = scne_payload(open(files[k], 'rb').read())
        pool = parse_pool(d)
        i = next((x for x, v in enumerate(pool) if JP.search(v)), None)
        if i is None:
            print('   ! %s 无日文' % k)
            continue
        # 日文块 = 首条含日文 .. 最后一条含日文（尾部混入的英文占位串如 '"..."' 一并丢弃）
        last = max(x for x, v in enumerate(pool) if JP.search(v))
        jp = pool[i:last + 1]
        n0 = len(lines)
        for t in jp:
            c = clean(t)
            if not c:
                continue
            # 源侧「实名版 / ######占位版」成对重复：只保留一条（两者替换后逐字相同）
            if '######' in t and lines and lines[-1] == c:
                continue
            lines.append(c)
        stat[k] = (len(jp), len(lines) - n0)
        print('   %s n=%4d ids=%3d jp=%4d -> 收 %d' % (k, len(pool), i, len(jp), len(lines) - n0))
    # 用語/手がかり辞典（static~clue.bin）：标题 3..21 ↔ 正文 24..42（末尾对齐自证，19 对）
    cp = files.get('clue')
    if cp:
        cd = scne_payload(open(cp, 'rb').read())
        base = struct.unpack_from('<I', cd, 0x18)[0]
        S = [x.decode('utf-8', 'replace') for x in cd[base:].split(b'\x00') if x]
        titles, bodies = S[3:22], S[24:43]
        if len(titles) == len(bodies) and not any('\n' in t for t in titles):
            n0 = len(lines)
            for t, b in zip(titles, bodies):
                lines.append('【%s】%s' % (t, clean(b)))
            stat['clue'] = (len(titles), len(lines) - n0)
            print('   clue  %d 条用語并入末尾' % len(titles))
    print('[i] 合计 %d 行' % len(lines))
    if js:
        json.dump({'stat': stat, 'lines': lines}, open(js, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[i] -> %s' % out)


if __name__ == '__main__':
    main()
