#!/usr/bin/env python3
"""probe.py —— 低 token 探查器（所有输出**默认限量**，绝不整表 dump）。

用法:
  python scripts/probe.py magic   <file>                 # 扫已知魔数，只报命中
  python scripts/probe.py entropy <file> [--win 65536]   # 抽样窗口熵（判 明文/压缩/加密）
  python scripts/probe.py strings <file> [--min 4] [--top 30] [--off A:B] [--enc cp932]
  python scripts/probe.py jp      <file> [--min 6] [--top 30] [--off A:B]   # cp932 日文串摘要
  python scripts/probe.py hex     <file> <off> [--len 256]
  python scripts/probe.py u32     <file> <off> [--n 16]
  python scripts/probe.py find    <file> <hexpattern> [--top 10]
  python scripts/probe.py tree    <dir> [--top 25]       # 扩展名分布 + 数量 + 体积

★ 铁律：不要用 xxd/full-regex 打印整表（一次可白烧数万 token）。
  本工具所有命令都受 --top / --len / MAXLINES(默认 80 行) 约束。
"""
import os, re, sys, math, struct, collections

MAXLINES = int(os.environ.get('PROBE_MAXLINES', '80'))


def _cap(rows, top):
    top = min(top, MAXLINES)
    out = rows[:top]
    if len(rows) > top:
        out.append('... (共 %d 行，已截断；用 --top 调大)' % len(rows))
    print('\n'.join(out))


def read(p, n=None, off=0):
    with open(p, 'rb') as f:
        if off:
            f.seek(off)
        return f.read(n) if n else f.read()


MAGICS = [
    (b'XP3\r\n \x20', 'KiriKiri XP3'), (b'XP3', 'KiriKiri XP3'),
    (b'@UTF', 'CRI CPK'), (b'pf8', 'Artemis Engine (PFS)'),
    (b'ROM2', 'Kalmia8 ACTGS 容器 ROM2'), (b'SNR ', 'Kalmia8 ACTGS 脚本 SNR'),
    (b'TXA4', 'Kalmia8 纹理 TXA4'), (b'BUP4', 'Kalmia8 立绘 BUP4'),
    (b'CDAR', 'Koei CDAR'), (b'STCM2L', 'Idea Factory STCM2L'),
    (b'UNI2', 'CRI UNI2 (STCM2L/PS2 侧)'), (b'LIBP', 'Malie LIBP'),
    (b'ARC!', 'MNP (KoiGIG)'), (b'PackFile', 'BGI/Ethornell'),
    (b'NSAr', 'NScripter nsa'), (b'PSAR', 'PSARC'),
    (b'NSAC', 'NIS-NML NSAC'), (b'MZX0', 'HuneX MZX0'),
    (b'AFS\0', 'CRI AFS'), (b'mrgd00', 'HuneX mrg 容器'),
    (b'NPA\x01', 'Nitroplus NPA'), (b'allscr', 'HuneX allscr'),
    (b'PFS0', 'NSP (Switch)'), (b'NCA3', 'Switch NCA3'),
    (b'HEAD', 'Switch XCI'), (b'NFSO', 'Switch NFS0'),
    (b'CRPT', 'Madoka GScript CRPT'), (b'DDP2', 'Daisy2 DDP2'), (b'DDP3', 'Daisy2 DDP3'),
    (b'scene', 'Siglus? (scene 片段)'), (b'Gameexe', 'SiglusEngine Gameexe.dat'),
    (b'SPTHEADER', 'System-NNN spt'), (b'0x78', '?'),
    (b'Rar!\x1a\x07\x01', 'RAR5'), (b'Rar!\x1a\x07\x00', 'RAR4'),
    (b'PK\x03\x04', 'ZIP'), (b'7z\xbc\xaf\x27\x1c', '7-Zip'),
    (b'\x1f\x8b', 'gzip'), (b'BZh', 'bzip2'), (b'\xfd7zXZ', 'xz'),
    (b'\x89PNG', 'PNG'), (b'GIM', 'PS GIM 图像'), (b'DDS ', 'DDS 图像'),
    (b'\xff\xd8\xff', 'JPEG'), (b'RIFF', 'RIFF (WAV/AT9-hdr)'),
    (b'OggS', 'Ogg'), (b'\x7fELF', 'ELF'), (b'SCE\0', 'PSV/PSP SELF (需 self2elf)'),
    (b'MZ', 'PE (exe/dll)'), (b'CD001', 'ISO9660'),
    (b'Inno Setup Setup Data', 'Inno Setup 安装包'),
    (b'InstallShield', 'InstallShield 安装包'),
]
_TEXT_EXT = {'.png': 'PNG', '.jpg': 'JPEG', '.dds': 'DDS', '.gim': 'GIM'}


def cmd_magic(p):
    d = read(p, 1 << 20)
    rows = []
    for mg, name in MAGICS:
        i = d.find(mg)
        if i >= 0:
            rows.append('  hit @0x%-8x %-28s %s' % (i, name, mg[:12]))
    if os.path.isdir(p):
        print('(目录，用 tree 命令)'); return
    if len(d) > 0x200 and d[0x8001:0x8006] == b'CD001':
        rows.append('  hit @0x8001   ISO9660 (标准偏移)')
    print('== %s  size=%d ==' % (os.path.basename(p), os.path.getsize(p)))
    print('\n'.join(rows) if rows else '  (前 1 MB 无已知魔数)')
    e = entropy_of(d[:1 << 16])
    print('  首 64 KB 熵 = %.3f  %s' % (e, '<0.6 明文/表' if e < 0.6 else ('<0.9 压缩/代码' if e < 0.9 else '≥0.9 高度加密')))


def entropy_of(b):
    if not b:
        return 0.0
    c = collections.Counter(b)
    n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def cmd_entropy(p, win):
    sz = os.path.getsize(p)
    n = min(24, max(1, sz // win + 1))
    rows = []
    with open(p, 'rb') as f:
        for i in range(n):
            f.seek(min(i * (sz // n), sz - 1))
            e = entropy_of(f.read(win))
            rows.append('  @0x%-9x %.3f  %s' % (min(i * (sz // n), sz - 1), e,
                                                '明文/表' if e < 0.6 else ('压缩/代码' if e < 0.9 else '加密?')))
    print('== %s  %d 窗口 ==' % (os.path.basename(p), n))
    _cap(rows, MAXLINES)


def _strings(p, minlen, top, off, enc):
    b = read(p)
    if off:
        b = b[off[0]:off[1]]
    cps = re.compile(rb'[\x20-\x7e]{%d,}' % minlen) if enc == 'ascii' else \
          re.compile((rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc]){%d,}' % minlen) if enc == 'cp932' else
                     (rb'(?:[\x20-\x7e\x00-\xff][\x30-\xff]){%d,}' % minlen))
    found = list(cps.finditer(b))
    rows = []
    for m in found[:top]:
        s = m.group()
        try:
            s = s.decode('cp932' if enc == 'cp932' else ('utf-16-le' if enc == 'utf16le' else 'latin1'))
        except Exception:
            s = repr(s)
        rows.append('  @0x%-9x %s' % (m.start() + (off[0] if off else 0), s[:90]))
    print('== %s  命中 %d 条（列出前 %d）==' % (os.path.basename(p), len(found), min(top, MAXLINES)))
    _cap(rows, top)


def _parse_off(a):
    if not a:
        return None
    lo, _, hi = a.partition(':')
    return (int(lo, 0), int(hi, 0) if hi else None)


def cmd_hex(p, off, ln):
    b = read(p, ln, off)
    rows = []
    for i in range(0, len(b), 16):
        chunk = b[i:i + 16]
        asc = ''.join(chr(c) if 0x20 <= c < 0x7f else '.' for c in chunk)
        try:
            cp = chunk.decode('cp932', 'replace').replace('\n', '')
        except Exception:
            cp = ''
        rows.append('  %08x  %-47s  %s' % (off + i, ' '.join('%02x' % c for c in chunk), cp[:24]))
    print('== %s @0x%x len=%d ==' % (os.path.basename(p), off, len(b)))
    _cap(rows, MAXLINES)


def cmd_u32(p, off, n):
    b = read(p, off, n * 4)
    vals = struct.unpack_from('<%dI' % n, b)
    print('== %s @0x%x ==' % (os.path.basename(p), off))
    print('  ' + ' '.join('%08x' % v for v in vals))
    print('  ' + ' '.join(str(v) for v in vals))


def cmd_find(p, pat, top):
    mg = bytes.fromhex(pat.replace(' ', ''))
    d = read(p)
    idx = []
    st = 0
    while len(idx) < top + 1:
        i = d.find(mg, st)
        if i < 0:
            break
        idx.append(i); st = i + 1
    print('== find %s in %s ==' % (pat, os.path.basename(p)))
    print('  命中 %s%s' % (len(idx) if len(idx) <= top else '>%d' % top,
                           '' if not idx else '  偏移: ' + ' '.join('0x%x' % i for i in idx[:top])))


def cmd_tree(d, top):
    cnt = collections.Counter(); size = collections.Counter(); nfile = 0; nsize = 0
    for dp, dn, fn in os.walk(d):
        for f in fn:
            ext = os.path.splitext(f)[1].lower() or '(noext)'
            try:
                s = os.path.getsize(os.path.join(dp, f))
            except OSError:
                s = 0
            cnt[ext] += 1; size[ext] += s; nfile += 1; nsize += s
    rows = ['  %-12s %6d 个  %10.1f MB' % (e, c, size[e] / 1048576) for e, c in cnt.most_common(top)]
    print('== %s  共 %d 文件 / %.1f MB ==' % (d, nfile, nsize / 1048576))
    _cap(rows, top)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    cmd, tgt = a[0], a[1] if len(a) > 1 else '.'
    kw = {}
    for i, x in enumerate(a):
        if x.startswith('--'):
            kw[x[2:]] = a[i + 1] if i + 1 < len(a) and not a[i + 1].startswith('--') else True
    top = int(kw.get('top', 30)); ln = int(kw.get('len', 256)); n = int(kw.get('n', 16))
    win = int(kw.get('win', 65536)); mn = int(kw.get('min', 6))
    off = _parse_off(kw.get('off'))
    if cmd == 'magic':
        cmd_magic(tgt)
    elif cmd == 'entropy':
        cmd_entropy(tgt, win)
    elif cmd == 'strings':
        _strings(tgt, int(kw.get('min', 4)), top, off, kw.get('enc', 'ascii'))
    elif cmd == 'jp':
        _strings(tgt, mn, top, off, 'cp932')
    elif cmd == 'hex':
        cmd_hex(tgt, int(a[2], 0) if len(a) > 2 and not a[2].startswith('--') else 0, ln)
    elif cmd == 'u32':
        cmd_u32(tgt, int(a[2], 0) if len(a) > 2 and not a[2].startswith('--') else 0, n)
    elif cmd == 'find':
        cmd_find(tgt, a[2], int(kw.get('top', 10)))
    elif cmd == 'tree':
        cmd_tree(tgt, top)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
