#!/usr/bin/env python3
"""meine_extract.py -- [PS2-JP] マイネリーベ 優美なる記憶 text extractor.

Source chain (verified 2026-10-22):
  ISO9660  -> BREV.NKP (Konami NKP archive; hdr 'NKP\\x1a')
           -> 64 x *.scr  (a000..a062 / a100 / a200) = PLAIN TEXT Konami EVS script,
              CRLF, TAB separated, cp932 body text
Text ops:  MSG <name> <voice> <text>
           MSGCHR <chr> <expr> <name> <voice> <text>
           MSGQCHR <name> <n> <text>
           MSGSELECT / MSGSELECTF / MSGSELECTCHR <opt1>.<opt2>.<opt3> @L1 @L2 ...
Codes:     '.'   = in-box line break (merge; L0: single break code, merged len<=54)
           '①ｓN'= letter font-size code        -> strip
           'T0'/'T1' = end-of-line icon code    -> strip
           '○○○○' = heroine-name slot          -> ERIKA
           'Pn'/'In'/'Sn' = runtime person/date/spot slots -> 〔未解析〕
"""
import difflib
import os
import re
import struct
import sys

HEROINE = 'エリカ'
UNRES = '〔未解析〕'

# scripts excluded: a100 = date/place/system menus, a200 = char/expression test (debug)
SKIP = {'a100', 'a200'}


def nkp_entries(d):
    """NKP: 'NKP\\x1a' + u32 size + u32 0 + u32 count, then count*[u32 name_off][u32 data_off]."""
    assert d[:4] == b'NKP\x1a', 'not NKP'
    total, _, cnt = struct.unpack_from('<3I', d, 4)
    ents = []
    for i in range(cnt):
        no, do = struct.unpack_from('<2I', d, 0x10 + i * 8)
        e = d.find(b'\x00', no)
        ents.append((d[no:e].decode('latin1'), do))
    ents.sort(key=lambda x: x[1])
    out = []
    for i, (name, off) in enumerate(ents):
        end = ents[i + 1][1] if i + 1 < len(ents) else len(d)
        out.append((name, d[off:end]))
    return out


def _norm(t):
    return re.sub(r'[。、…‥「」『』！？!?\s\u3000]', '', t)


def clean(txt):
    txt = re.sub(r'①ｓ[0-9０-９]', '', txt)      # letter font size
    txt = re.sub(r'①[ａ-ｚ].{0,4}', '', txt)      # other ① escapes (defensive)
    txt = re.sub(r'[②③]', '', txt)
    txt = re.sub(r'T[0-9](?![0-9])', '', txt)      # end-of-line icon code
    txt = re.sub(r'○{4,}', HEROINE, txt)           # heroine name slot
    txt = re.sub(r'P[0-9]', UNRES, txt)            # runtime person slot
    txt = re.sub(r'I[0-9]', UNRES, txt)            # runtime date slot
    txt = re.sub(r'S[0-9]', UNRES, txt)            # runtime spot slot
    txt = txt.replace('.', '')                     # in-box line break -> merge
    txt = txt.replace('\u3000', ' ') if False else txt
    return txt.strip()


def parse_line(s):
    """Return list of output strings for one script line."""
    if not s or s[0] in '@\x00':
        return []
    m = re.match(r'^(MSG|MSGCHR|MSGQCHR|MSGSELECTCHR|MSGSELECTF|MSGSELECT)[ \t]', s)
    if not m:
        return []
    op = m.group(1)
    if op in ('MSG', 'MSGCHR', 'MSGQCHR'):
        n = {'MSG': 2, 'MSGCHR': 4, 'MSGQCHR': 2}[op]
        parts = s.split(None, n + 1)
        if len(parts) <= n + 1:
            # field-less form:  MSG <tab><text>
            parts = s.split(None, 1)
            txt = parts[1] if len(parts) > 1 else ''
        else:
            txt = parts[n + 1]
        out = clean(txt)
        return [out] if out else []
    # --- select ops: options separated by '.', trailing @labels
    body = s[len(op):].strip()
    body = re.sub(r'(\s*@[^\s@]+)+\s*$', '', body)
    if op == 'MSGSELECTCHR':
        # 2 leading numeric params (chr slot, flag) before the option list
        body = re.sub(r'^(\S+[ \t]+){2}', '', body)
    opts = [clean(o) for o in body.split('.')]
    return [o for o in opts if o]


def main(src, out_txt):
    d = open(src, 'rb').read()
    ents = nkp_entries(d)
    lines = []
    stats = {'files': 0, 'skipped': 0, 'echo': 0}
    for name, blob in ents:
        if not name.lower().endswith('.scr'):
            continue
        stem = name[:-4]
        if stem in SKIP:
            stats['skipped'] += 1
            continue
        stats['files'] += 1
        t = blob.decode('cp932', errors='replace')
        for raw in t.split('\r\n'):
            s = raw.strip()
            got = parse_line(s)
            if not got:
                continue
            # MSGQCHR is also used as an ECHO of the line just shown: the choice
            # window re-prints the preceding MSGCHR sentence (often with the leading
            # interjection / punctuation trimmed) -> keep the fuller dialogue line only.
            if s.startswith('MSGQCHR') and lines:
                prev, cur = _norm(lines[-1]), _norm(got[0])
                if cur and (cur in prev or prev in cur
                            or difflib.SequenceMatcher(None, prev, cur).ratio() >= 0.90):
                    stats['echo'] += 1
                    continue
            lines.extend(got)
    with open(out_txt, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('scripts: %d (skipped %d, echo dropped %d), lines: %d'
          % (stats['files'], stats['skipped'], stats['echo'], len(lines)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
