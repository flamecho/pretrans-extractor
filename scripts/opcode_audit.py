# -*- coding: utf-8 -*-
"""通用「有没有漏文本」审计（自定义 bytecode ADV 通用）。

两路检查（互相独立，缺一不可）：
  A) **opcode 日文承载量**（event.enc 内）—— 谁在承载日文？除 {台词,选项,无说话人文框} 外
     若还有 opcode 承载大量日文，就是漏收。这是「漏没漏」的最硬证据。
  B) **CPK 内非 event.enc 文件**的日文含量 —— 条目型文本（用語辞典/図鑑/事典）常**另存**在
     CPK 根（如 termItem.dat），只提 event.enc 必漏。
     ⚠ 必须用「**≥12 连续日文串**」判据；单字计数会被图像字节巧合解出的假日文污染（必然假阳性）。

用法：
    python scripts/opcode_audit.py <解包目录> <作品键> [--cpk <umd.cpk 路径>]
      <解包目录>  含 event.enc（如 _work_x/out1）
      <作品键>    urakata_extract.OPCODES 的键（urakata|akatsuki|…）；新作在该表加一行即可
      --cpk       可选，给则跑 B 路（扫 CPK 内非媒体文件）
"""
import sys, os, re, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import urakata_extract as U
from lzo1x import lzo1x_decompress


def load_entries(base, enc='event.enc'):
    raw = open(os.path.join(base, enc), 'rb').read()
    cnt = struct.unpack_from('<I', raw, 0)[0]
    ents = []
    for i in range(cnt):
        a, b, off = struct.unpack_from('<III', raw, 0x10 + 12 * i)
        s = a & 0x7fffffff
        ents.append(lzo1x_decompress(raw[off:off + s], b) if (a >> 31) & 1 else raw[off:off + s])
    return ents


def ops(e):
    """[u32 cmd][u32 len][data] 流式解析。"""
    out, pos = [], 0
    while pos + 8 <= len(e):
        cmd, ln = struct.unpack_from('<II', e, pos)
        if pos + 8 + ln > len(e):
            break
        out.append((pos, cmd, ln, e[pos + 8:pos + 8 + ln]))
        pos += 8 + ln
    return out


JP = lambda c: (0x3040 <= ord(c) <= 0x30ff or 0x4e00 <= ord(c) <= 0x9fff
                or c in '…‥「」『』（）〈〉《》？！?!。、，,ー〜～・･')


def jp_bytes(d):
    b = d.split(b'\x00')[0]
    if len(b) < 2 or any(c < 0x20 and c not in (0x0a, 0x0d, 0x09) for c in b):
        return 0
    try:
        t = b.decode('cp932')
    except Exception:
        return 0
    return len(b) if any(JP(c) for c in t) else 0


def audit_opcodes(base, title):
    op = U.OPCODES[title]
    keep, drop = {op['txt'], op['opt'], op['sys']}, set()
    for k in ('name', 'font'):
        if k in op:
            for v in (op[k] if isinstance(op[k], (list, tuple, set)) else [op[k]]):
                drop.add(v)
    ents = load_entries(base)
    st = collections.defaultdict(lambda: [0, 0, 0])          # cmd -> [块数, 日文块, 日文字节]
    for e in ents:
        if any(k.encode('cp932') in e for k in U.DEBUG_KW.get(title, ())):
            continue
        for _, cmd, _, d in ops(e):
            st[cmd][0] += 1
            nb = jp_bytes(d)
            if nb:
                st[cmd][1] += 1
                st[cmd][2] += nb
    print('=== A) opcode 日文承载量（%s；已收 = %s）===' %
          (title, '/'.join('%#x' % c for c in keep)))
    for cmd, (n, j, nb) in sorted(st.items(), key=lambda kv: -kv[1][2])[:14]:
        tag = ''
        if cmd not in keep and cmd not in drop and nb > 2000:
            tag = '   ★★ 未收取却在承载日文 —— 请核'
        elif cmd in drop:
            tag = '   （名札/字库，按规范丢弃）'
        print('  cmd=%#-7x 块%-7d 日文块%-7d 日文字节%-9d%s' % (cmd, n, j, nb, tag))
    covered = sum(st[c][2] for c in keep)
    total = sum(v[2] for v in st.values())
    print('  已收三类 = %d B | 全库日文 = %d B | 未收（名札+字库+其它）= %d B'
          % (covered, total, total - covered))
    return ents


def audit_cpk(cpk_path):
    """B) CPK 内非媒体文件的「≥12 连续日文串」扫描。"""
    from cpk import CPK
    SKIP = {'.gim', '.pmf', '.awb', '.png', '.gmo', '.at3', '.vag', '.acb', '.usm', '.ttf', '.otf'}
    JPR = re.compile(r'[ぁ-んァ-ヴー一-龥。、「」『』？！…‥・]{12,}')
    c = CPK(cpk_path)
    rows = []
    for e in c.entries:
        nm = e.get('name') or ''
        ext = ('.' + nm.rsplit('.', 1)[-1].lower()) if '.' in nm else ''
        if ext in SKIP or (e.get('FileSize') or 0) > 6 * 1024 * 1024:
            continue
        try:
            t = c.raw(e).decode('cp932', 'ignore')
        except Exception:
            continue
        ms = JPR.findall(t)
        if ms:
            rows.append((sum(map(len, ms)), len(ms), e.get('FileSize'), nm, ms[0][:36]))
    rows.sort(reverse=True)
    print()
    print('=== B) CPK 内非媒体文件含「≥12 连续日文串」= %d 个（event.enc 之外必查）===' % len(rows))
    for n, k, sz, nm, ex in rows[:22]:
        print('  %-46s %8s B  日文%-7d 串%-5d 例:%s' % (nm, sz, n, k, ex))
    print('  ⚠ 判「本作固有 vs 他作遗留」＝统计两组词频（本作固有词/他作词），不按文件名猜。')


if __name__ == '__main__':
    base = sys.argv[1]
    title = sys.argv[2]
    audit_opcodes(base, title)
    if '--cpk' in sys.argv:
        audit_cpk(sys.argv[sys.argv.index('--cpk') + 1])
