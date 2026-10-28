# -*- coding: utf-8 -*-
"""スチームプリズン 按「文本表逐条 = 一次点击」重建（2026-10-26）。

判据（L1）：`_ZM` 开框、`_MSAD` 同框追加一条 = **各自一次点击**；
只有「上一条文本引号未闭合」（同一句被框内换行切开）才并入上一行。
实测 4,088 条 `_MSAD` 中仅 148 条属「未闭续写」，其余 3,939 条是独立句 ⇒ 旧规则（默认合并）错了。

用法: python scripts/steam_rebuild.py <romfs目录> [out.txt]
"""
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ozmafia_extract import mrgd00_members, mzx0_decompress

RUBY = re.compile(r'#R\([^)]*\)|<[^<>]{1,40},[^<>]{1,40}>')
ZM = re.compile(r'^_ZM[0-9a-fA-F]*\(\$(\d{6})\^?\)')
MS = re.compile(r'^_MSAD\(\$(\d{6})\^?\)')
EXCLUDE_PREFIX = ('SUB_SCRIPT', 'MAIN')


def clean(t):
    t = RUBY.sub('', t)
    return t.replace('\n', '').replace('\r', '').strip()


def main():
    rom = sys.argv[1] if len(sys.argv) > 1 else '_w_sp/romfs'
    out = sys.argv[2] if len(sys.argv) > 2 else '提取结果/[NS-JP]スチームプリズン.txt'
    blob = open(os.path.join(rom, 'script_text.mrg'), 'rb').read()
    cnt, mem = mrgd00_members(blob)
    jp, idx = mem[1], mem[0]
    n = len(idx) // 4
    offs = [int.from_bytes(idx[i * 4:i * 4 + 4], 'big') for i in range(n)]

    def T(i):
        if not (0 <= i < n):
            return ''
        a = offs[i]
        b = offs[i + 1] if i + 1 < n else len(jp)
        return clean(jp[a:b].decode('utf-8', 'replace'))

    blob = open(os.path.join(rom, 'allscr.mrg'), 'rb').read()
    cnt, mem = mrgd00_members(blob)
    nam = mem[0]
    names = [nam[i:i + 32][:30].rstrip(b'\x00').decode('cp932', 'replace')
             for i in range(0, len(nam) - 31, 32)]
    names = [x for x in names if x.strip()]

    lines, last, n_zm, n_join = [], '', 0, 0
    for i, nm in enumerate(names):
        if nm.startswith(EXCLUDE_PREFIX):
            continue
        b = mem[3 + i]
        if b[:4] == b'MZX0':
            ex = struct.unpack('<L', b[4:8])[0]
            raw = mzx0_decompress(b[8:], len(b) - 8, ex)
        else:
            raw = b
        for st in raw.decode('cp932', 'replace').split(';'):
            st = st.strip()
            m = ZM.match(st) or MS.match(st)
            if not m:
                continue
            t = T(int(m.group(1)))
            if not t:
                continue
            if last and last.count('「') > last.count('」'):
                lines[-1] += t
                n_join += 1
            else:
                lines.append(t)
                n_zm += 1
            last = t
    lines = [x for x in lines if x]
    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    open(out, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')
    print('行 %d｜开框 %d｜未闭并入 %d' % (len(lines), n_zm, n_join))


if __name__ == '__main__':
    main()
