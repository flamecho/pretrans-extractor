# -*- coding: utf-8 -*-
"""遥かなる時空の中で6 DX —— 用語辞典（見出し語＋解説）构建器 v2

格式：一行 = 【用語】解説文（无读音）。
配对原理（2026-10-03 破解）：
  · 脚本容器 CDAR 内存在一张「资源映射表」条目，结构为
        [u32 n][u32 resourceHash × n][u16 index × n]
    长度满足 4 + 6n == 条目长度，且 hash 列表与 CDAR 头部的 hash 数组吻合。
    ORG(DATA_ORG.BIN) 中该条目 = 2001 (n=1840)；PK(DATA_PK.BIN) 中 = 2875 (n=2516)。
  · 对每个 i：hlist[i] 对应的资源条目 = 一个「用語解説」条目；
    其用語番号 tid = uarr[i] - 483  (BASE=483，两作通用)。
  · 用語表（0x40 步长记录，[u32 hdr=01000000][term cp932][reading hiragana][key 半角片假名]）
    位于 table-entry 内、以最后一次出现的 'ダリウス' - 4 为 tid=1 锚点；tid=0 = 锚点-0x40。
  · 解説条目 = 以固定尾码 1ef907874c1ec70947741ed308905e 结尾的小条目（<4000B）；
    若含多条文本记录（短版+长版），取最长者。

用法:
  haruka6_dict.py ORG <DATA_ORG.BIN> PK <DATA_PK.BIN> <out.txt>
"""
import struct, zlib, re, os, sys

TAIL = bytes.fromhex('1ef907874c1ec70947741ed308905e')
BASE = 483   # tid = uarr - BASE（两作通用）

_here = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(_here, 'haruka6_extract.py'), encoding='utf-8').read()
     .replace("if __name__ == '__main__':\n    main()", ''))


# ---------------- 用語表 ----------------
def parse_term_table(d, base):
    """返回 {tid: term}。tid=1 在 base，tid=0 在 base-0x40。"""
    out = {}
    for r in range(0, 1200):
        off = (base - 0x40) + r*0x40
        if off + 0x40 > len(d): break
        rec = d[off:off+0x40]
        term = rec[4:0x18].split(b'\x00')[0]
        if not term: continue
        try: out[r] = term.decode('cp932')
        except Exception: pass
    return out


# ---------------- 名称类扫描 ----------------
def table_strings(d, start, end):
    out = []; seen = set(); i = start; L = min(end, len(d))
    while i < L - 1:
        b = d[i]
        if (0x81<=b<=0x9F) or (0xE0<=b<=0xEF) or (0x20<=b<=0x7E):
            j = i; ok = True; chars = []
            while j < L:
                c = d[j]
                if c == 0: break
                if 0x81<=c<=0x9F or 0xE0<=c<=0xFC:
                    if j+1 >= L: ok=False; break
                    try: ch = d[j:j+2].decode('cp932')
                    except Exception: ok=False; break
                    if len(ch)!=1: ok=False; break
                    chars.append(ch); j += 2
                elif 0x20<=c<=0x7E:
                    chars.append(chr(c)); j += 1
                else:
                    ok=False; break
            if ok and chars:
                t = ''.join(chars).lstrip(' ')
                if len(t) >= 2 and (0x20 <= ord(t[0]) <= 0x7E) and not (0x20 <= ord(t[1]) <= 0x7E):
                    t = t[1:]
                if jp_ratio(t) >= 0.5 and t not in seen:
                    if not re.match(r'^[0-9A-Za-z_\- ]+$', t):
                        out.append((i, t)); seen.add(t)
                i = j + 1; continue
        i += 1
    return out

def scan_names(d, ranges, out):
    seen = set(out)
    for (s, e) in ranges:
        for off, t in table_strings(d, s, e):
            if t in seen: continue
            if is_noise(t): continue
            if re.match(r'^(ダミー|仮|予備|テスト|札|配信イベント|回想録[0-9０-９]+$|イベント[・_])', t): continue
            seen.add(t); out.append(t)
    return out


# ---------------- 映射表定位 ----------------
def find_map_entry(c):
    """定位 [u32 n][hash×n][u16×n] 结构条目，返回 (entry, hlist, uarr)。"""
    hashes = struct.unpack_from(f'<{c.count}I', c.d, 16)
    hset = set(hashes)
    for i in range(c.count):
        o, ds, s = c.entries[i]
        if ds > 2_000_000: continue
        try: dd = c.data(i)
        except Exception: continue
        if len(dd) < 8: continue
        n = struct.unpack_from('<I', dd, 0)[0]
        if not (50 < n < 6000): continue
        if 4 + 6*n != len(dd): continue
        hlist = struct.unpack_from(f'<{n}I', dd, 4)
        if sum(1 for h in hlist[:300] if h in hset) >= 200:
            return i, hlist, struct.unpack_from(f'<{n}H', dd, 4+4*n)
    return None, None, None


# ---------------- 构建 ----------------
RANGES = {
    'ORG': (914, [(0x0, 0x400), (0x800, 0x18fc0), (0x1f280, 0x2d304)]),
    'PK':  (1302, [(0x0, 0x400), (0x800, 0x1f000), (0x27000, 0x37480)]),
}
TAGR = {'ORG': '遥か6本篇', 'PK': '幻燈ロンド'}

def build(gkey, path, f):
    te, ranges = RANGES[gkey]
    game = TAGR[gkey]
    c = CDAR(path)
    d = c.data(te)
    f.write(f'\n{"="*72}\n【{game}】\n{"="*72}\n')

    # 用語表
    base = d.rfind('ダリウス'.encode('cp932')) - 4
    terms = parse_term_table(d, base)

    # 映射表
    mi, hlist, uarr = find_map_entry(c)
    hashes = struct.unpack_from(f'<{c.count}I', c.d, 16)
    h2e = {}
    for e in range(c.count): h2e.setdefault(hashes[e], e)
    e2tid = {}
    if hlist:
        for i in range(len(hlist)):
            e = h2e.get(hlist[i])
            if e is not None: e2tid[e] = uarr[i] - BASE

    # 解説条目
    def desctext(e):
        ins = walk_safe(c.data(e))
        recs = [x[3].rstrip(b'\x00').decode('cp932','replace').replace('\n','').strip()
                for x in ins if x[3] is not None]
        recs = [r for r in recs if r]
        return max(recs, key=len) if recs else ''

    tid2desc = {}
    for i in range(c.count):
        try: dd = c.data(i)
        except Exception: continue
        if len(dd) > 4000 or len(dd) < 20: continue
        if not dd.endswith(TAIL): continue
        tid = e2tid.get(i)
        if tid is None or tid < 0 or tid in tid2desc: continue
        tid2desc[tid] = i

    items = []
    for tid in sorted(tid2desc):
        t = terms.get(tid)
        if not t: continue
        items.append((t, desctext(tid2desc[tid])))
    f.write(f'\n■ 用語（見出し語＋解説） — {len(items)} 項\n')
    for t, desc in items:
        f.write(f'【{t}】{desc}\n')

    names = scan_names(d, ranges, [])
    f.write(f'\n■ 名称・タイトル類 — {len(names)} 件\n')
    for t in names:
        f.write(t + '\n')


def main():
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)
    outpath = sys.argv[-1]
    args = sys.argv[1:-1]
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        for a in range(0, len(args), 2):
            build(args[a], args[a+1], f)
    print('dict ->', outpath)

if __name__ == '__main__':
    main()
