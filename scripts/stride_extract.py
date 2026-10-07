#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""《[PSV-JP]プリンス・オブ・ストライド》 (PCSG00491) 资源解密 / 解包 / 文本探查工具

管线（2026-10-06 定稿）:
  1. RAR 解包        -> app/PCSG00491/  (NoNpDrm dump)
  2. PFS 解密        -> psvpfsparser -i <titleid dir> -o <out> -z <zRIF> -f cma.henkaku.xyz
                        zRIF 需自备（见 references/third-party.md）
                        成功标志: keystone: matched retail hmac
  3. eboot -> ELF    -> util/self2elf.py -i eboot.bin -o eboot_elf.bin -k sce_sys/package/work.bin
  4. CPK 解包        -> scripts/cpk.py  (sc.cpk 272 / union.cpk 1927)
  5. 文本探查        -> scan_text()

结论: 全库无明文日文文本（见本作品解析报告）。
      本作文本以「字形索引 / 自研编码」形式存储，需进一步逆向。
"""
import os, sys, re, struct, zlib, hashlib, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ZRIF = os.environ.get('ZRIF','')
PSVPARSE = os.path.join(HERE, 'psvdec_tmp/psvdec-main/bin/win64/psvpfsparser.exe')
SELF2ELF = os.path.join(HERE, 'psvdec_tmp/psvdec-main/util/self2elf.py')

# ---------- 文本探查 ----------

JP_KANA_PUNCT = '、。「」『』ー？！・…'


def count_sjis_jp(d):
    """返回 (平假名, 片假名, 汉字, 标点) 的 2 字节出现次数。"""
    hira = sum(1 for i in range(len(d) - 1) if d[i] == 0x82 and 0xA0 <= d[i + 1] <= 0xF1)
    kata = sum(1 for i in range(len(d) - 1) if d[i] == 0x83 and 0x40 <= d[i + 1] <= 0x9F)
    kanji = sum(1 for i in range(len(d) - 1)
                if (0x88 <= d[i] <= 0x9F or 0xE0 <= d[i] <= 0xEA)
                and (0x40 <= d[i + 1] <= 0x7E or 0x80 <= d[i + 1] <= 0xFC))
    punc = sum(d.count(p.encode('cp932'))
               for p in JP_KANA_PUNCT if len(p.encode('cp932')) == 2)
    return hira, kata, kanji, punc


def scan_text(root):
    """遍历解包产物，报告各文件的日文密度（随机数据约 0.12% 为基线）。"""
    print('%-46s %9s %8s %8s %7s' % ('file', 'size', 'hira', 'kata', 'punct'))
    for dp, _, fs in os.walk(root):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            if os.path.getsize(p) < 4096:
                continue
            d = open(p, 'rb').read()
            h, k, _, pc = count_sjis_jp(d)
            if h + k + pc > 0:
                print('%-46s %9d %8d %8d %7d' %
                      (os.path.relpath(p, root), len(d), h, k, pc))


# ---------- 结构解析 ----------

def parse_pr_bin(path):
    """pr.bin：0x00 起 5×16 RGBA 调色板；0x800 起资源(blob 表 (type,offset,size,flags))。"""
    d = open(path, 'rb').read()
    print('pr.bin size', len(d))
    print(' palettes @0x000/0x100/0x200/0x300/0x400 (各 16×RGBA):')
    for off in (0x000, 0x100, 0x200, 0x300, 0x400):
        print('   %#06x' % off, d[off:off + 8].hex(), '...')
    print(' resource @0x800:')
    for i in range(6):
        v = struct.unpack_from('<4I', d, 0x800 + i * 16)
        print('   rec%d' % i, [hex(x) for x in v])


def parse_sc_entry(sc_entry_bytes):
    """sc.cpk 单条：@0x00 u32(场景ID/首串)；@0x80 u32 偏移表；@0x2000 数据；末 16B 校验。"""
    b = sc_entry_bytes
    head = struct.unpack_from('<I', b, 0)[0]
    tbl = list(struct.unpack_from('<8I', b, 0x80))
    tail = b[-16:].hex()
    return head, tbl, tail


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print('usage: stride_extract.py <scan|prbin|zrif> [path]')
        return
    cmd = sys.argv[1]
    if cmd == 'zrif':
        print(ZRIF)
    elif cmd == 'scan':
        scan_text(sys.argv[2] if len(sys.argv) > 2 else '.')
    elif cmd == 'prbin':
        parse_pr_bin(sys.argv[2])
    elif cmd == 'psv':
        src = sys.argv[2]
        out = sys.argv[3] if len(sys.argv) > 3 else 'dec'
        print('run:', PSVPARSE, '-i', src, '-o', out, '-z <zRIF> -f cma.henkaku.xyz')
        print('    (psvpfsparser 需可访问 F00D 服务 cma.henkaku.xyz；成功标志 keystone: matched retail hmac)')
    else:
        print('unknown cmd', cmd)


if __name__ == '__main__':
    main()
