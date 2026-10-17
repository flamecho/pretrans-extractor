# -*- coding: utf-8 -*-
"""BLACK WOLVES SAGA -Wei\u00df und Schwarz- (Switch, STCM2L) \u5267\u672c\u63d0\u53d6\u5668.

\u3010\u683c\u5f0f\u5b9e\u8bc1\u7ed3\u8bba\u3011
\u5bb9\u5668: XCI -> NCA -> RomFS -> CONTENTS/DATA.cpk -> SCRIPT/*.DAT (+ SCRIPT_fd/*.DAT)
\u811a\u672c: STCM2L (Idea Factory) \u2014 \u5b57\u7b26\u4e32\u5bf9\u8c61 = [u32 L][utf8][NUL pad], L=align4(len+1)\u3002
\u5bf9\u8c61\u5934\u56fa\u5b9a\u540e\u7f00\uff084 \u5b57\u6bb5\uff09:
    u32(i-0x18)==0x61  u32(i-0x10)==0x10  u32(i-0x0c)==0  u32(i-0x04)==1
\u7c7b\u578b\u5b57\u6bb5 u32(i-0x34):
    0x4ba=\u6b63\u6587\uff08\u53f0\u8bcd/\u65c1\u767d\uff09\u30010x4bc=\u540d\u672d\u30010x4be='<'\u7b26\u53f7\u3001
    0xb8c/0xbac\u7b49=\u8d44\u6e90\u540d\uff08her01/cck\uff09\u30010x44e='sureNN'\u30010x1fb1c='switch'
\u7ae0\u9898/\u573a\u666f\u9898\uff1au32(i-0x1c)==0x62 \u4e14\u7c7b\u578b\u4e0d\u662f 0x4ba/0x4bc\uff08\u5373\u5934\u90e8\u4e3a\u6307\u9488\u7c7b\uff09\u3002
\u9009\u9879\uff1au32(i-0x1c) \u2208 [0x6b,0x78] \u4e14\u5934\u90e8\u4e3a\u6307\u9488\u7c7b\uff1b\u5176\u4e2d 'BWS*'/\u597d\u611f\u5ea6/\u5224\u5b9a/\u6e05\u695a\u7b49\u4e3a\u5185\u90e8 flag\uff08\u6392\u9664\uff09\u3002

\u3010\u6210\u884c\u3011\u6846 = \u8fde\u7eed id\uff08i-0x14\uff09\u7684\u6b63\u6587\u8bb0\u5f55\uff1b\u540d\u672d\uff08id = \u9996\u6587\u672c id \u2212 1\uff09
\u4e3a\u8be5\u6846\u8bdd\u8005\uff08\u4e22\u5f03\u4e0d\u8f93\u51fa\uff09\u3002\u4e00\u6b21\u70b9\u51fb = \u4e00\u884c\u3002
"""
import struct
import re
import os
import glob
import sys
import io

A4 = lambda n: (n + 3) & ~3

NAME_TYP = 0x4bc
TEXT_TYP = 0x4ba
TITLE_KIND = 0x62
OPTION_KINDS = set(range(0x6b, 0x79))

HEROINE = {1: 'フィオナ'}          # vndb c7044 \u30d5\u30a3\u30aa\u30ca\u30fb\u30ac\u30fc\u30e9\u30f3\u30c9

RE_INLINE_NAME = re.compile(r'#Name\[(\d+)\]')
RE_COLOR = re.compile(r'#Color\[\d+\]')
RE_KANA = re.compile(r'[\u3040-\u30ff]')
RE_HAS_JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
RE_FLAG = re.compile(r'^(?:BWS|.*(?:フラグ|好感度|判定|クリア|BAD|TRUE|ED|ルート選択|キャラルート選択))$')
RE_DEBUGLINE = re.compile(r'^(?:[-－─―=＝]{4,}|★|※|動作確認|作成者)')
# \u539f\u4f5c\u306e\u30bf\u30a4\u30dd\uff08\u9589\u3058\u62ec\u5f27\u6b20\u843d\uff09\u2014\u2014 \u6574\u884c\u5b9a\u5024\u3067\u4fee\u6b63\uff08\u6b63\u898f\u5f0f\u3067\u306e\u4e00\u62ec\u4fee\u6b63\u306f\u3057\u306a\u3044\uff09
LINE_FIX = {
    '（ガーランド家の責任が\u3000問われなければいいんだけど……。':
    '（ガーランド家の責任が\u3000問われなければいいんだけど……。）',
}
# \u30af\u30ea\u30c3\u30af\u5f85\u3061 / \u6539\u30da\u30fc\u30b8\u7b26\u53f7\uff08\u5358\u4f53\u8a18\u9332\uff09\u2014\u2014\u6846\u5883\u754c\u306b\u306a\u308b
MARKER_TEXTS = {'＠', '<pb>'}

# \u30d7\u30ec\u30fc\u30b9\u30db\u30eb\u30c0\uff08\u975e\u8868\u793a\uff09
PLAIN_SKIP = {'仮', '－', '-'}

# \u958b\u767a\u30fb\u52d5\u4f5c\u78ba\u8a8d\u7528\u30b9\u30af\u30ea\u30d7\u30c8\u30fb\u30ea\u30bd\u30fc\u30b9\u5c02\u7528\uff08\u975e\u8868\u793a\uff09
EXCLUDE_FILES = {'901.DAT', '910.DAT', '1000.DAT', '1100.DAT', '3000.DAT', '10000.DAT'}


def find_breaks(d):
    """\u30c6\u30ad\u30b9\u30c8\u30d6\u30ed\u30c3\u30af\u306e\u7d42\u7aef\u30ec\u30b3\u30fc\u30c9 (typ=0x4bb) \u306e\u4f4d\u7f6e\u4e00\u89a7\u3002
    \u69cb\u9020: [0x4bb][0][0x20][0x0a][0x61][id][0x10][0]  \u2014\u2014 \u540c\u3058\u6846\u5185\u306e\u7d9a\u304d\u306b\u306f\u73fe\u308c\u305a\u3001
    \u6846\u306e\u6700\u5f8c\u306e\u884c\u306e\u76f4\u5f8c\u306b\u5fc5\u305a\u73fe\u308c\u308b\uff08\u5b9f\u8a3c\uff09\u3002"""
    pat = b'\xbb\x04\x00\x00\x00\x00\x00\x00\x20\x00\x00\x00\x0a\x00\x00\x00'
    out = []
    st = 0
    while True:
        j = d.find(pat, st)
        if j < 0:
            break
        out.append(j)
        st = j + 1
    return out


def scan(path):
    """\u8fd4\u56de\u6309\u504f\u79fb\u9806\u306e\u8a18\u9332 [(off, role, id, text)]\u3002
    role \u2208 {'TEXT','NAME','TITLE','OPTION'}\u3002"""
    d = open(path, 'rb').read()
    breaks = find_breaks(d)
    n = len(d)
    out = []
    bi = 0

    def has_break(a, b):
        nonlocal bi
        while bi < len(breaks) and breaks[bi] < a:
            bi += 1
        return bi < len(breaks) and breaks[bi] < b

    i = 0
    while i < n - 8:
        L = struct.unpack_from('<I', d, i)[0]
        if 4 <= L <= 0x4000 and L % 4 == 0 and i + 4 + L <= n and i >= 0x34:
            t = d[i + 4:i + 4 + L].rstrip(b'\x00')
            if t:
                try:
                    s = t.decode('utf-8')
                except Exception:
                    s = None
                if s and all(ord(c) >= 0x20 for c in s) and A4(len(t) + 1) == L:
                    if (struct.unpack_from('<I', d, i - 0x18)[0] == 0x61
                            and struct.unpack_from('<I', d, i - 0x10)[0] == 0x10
                            and struct.unpack_from('<I', d, i - 0x0c)[0] == 0
                            and struct.unpack_from('<I', d, i - 0x04)[0] == 1):
                        typ = struct.unpack_from('<I', d, i - 0x34)[0]
                        kind = struct.unpack_from('<I', d, i - 0x1c)[0]
                        rid = struct.unpack_from('<I', d, i - 0x14)[0]
                        role = None
                        if typ == NAME_TYP:
                            role = 'NAME'
                        elif typ == TEXT_TYP:
                            role = 'TEXT'
                        elif typ > 0x1000 and kind == TITLE_KIND and RE_KANA.search(s):
                            role = 'TITLE'
                        elif (typ > 0x1000 and RE_HAS_JP.search(s)
                              and s not in PLAIN_SKIP and not RE_FLAG.match(s)):
                            role = 'OPTION'
                        if role:
                            out.append((i - 0x34, role, rid, s))
        i += 4
    # \u5404\u8a18\u9332\u306e\u76f4\u524d\u306b\u30d6\u30ed\u30c3\u30af\u7d42\u7aef\u30ec\u30b3\u30fc\u30c9\u304c\u3042\u308b\u304b\uff08=\u3053\u306e\u8a18\u9332\u304b\u3089\u65b0\u3057\u3044\u6846\uff09
    res = []
    prev_off = -1
    for off, role, rid, s in out:
        res.append((off, role, rid, s, has_break(prev_off, off)))
        prev_off = off
    return res


def subst(s):
    s = RE_INLINE_NAME.sub(lambda m: HEROINE.get(int(m.group(1)), m.group(0)), s)
    s = RE_COLOR.sub('', s)
    s = s.strip()
    return LINE_FIX.get(s, s)


def build(path):
    recs = scan(path)
    lines = []
    buf = []

    def flush():
        if buf:
            txt = subst(''.join(x[1] for x in buf))
            if txt and not RE_DEBUGLINE.match(txt):
                lines.append(txt)
            buf.clear()

    for off, r, rid, s, brk in recs:
        if r == 'NAME':
            flush()
            continue
        if r == 'TEXT':
            if s in MARKER_TEXTS:      # \u30af\u30ea\u30c3\u30af\u5f85\u3061\u30fb\u6539\u30da\u30fc\u30b8 \u21d2 \u5883\u754c
                flush()
                continue
            if buf and brk:            # \u3053\u306e\u8a18\u9332\u306e\u76f4\u524d\u306b\u30d6\u30ed\u30c3\u30af\u7d42\u7aef\uff1d\u65b0\u3057\u3044\u6846
                flush()
            buf.append((rid, s))
            continue
        flush()
        txt = subst(s)
        if txt and not RE_DEBUGLINE.match(txt):
            lines.append(txt)
    flush()
    return lines


def main():
    srcs = sys.argv[1:-1]
    out = sys.argv[-1]
    files = []
    for src in srcs:
        if os.path.isfile(src):
            files.append(src)
        else:
            files.extend(sorted(glob.glob(os.path.join(src, '*.DAT')),
                                key=lambda p: int(os.path.basename(p).split('.')[0])))
    files = [f for f in files if os.path.basename(f) not in EXCLUDE_FILES]
    all_lines = []
    for f in files:
        all_lines.extend(build(f))
    with io.open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for ln in all_lines:
            ln = ln.strip()
            if ln:
                fh.write(ln + '\n')
    print('files=%d lines=%d -> %s' % (len(files), len(all_lines), out))


if __name__ == '__main__':
    main()
