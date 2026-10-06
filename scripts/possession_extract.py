"""Extractor for Possession Magenta (ポゼッション マゼンタ, PSV, PCSG00509).

Pipeline
--------
1. `data/allscr.mrg` (HuneX MRG container, plaintext "mrgd00" after the PFS
   decryption) is parsed with the layout documented by PS-HuneX_Tools
   (`scripts/unpack_allsrc.py`):
       "mrgd00"(6) + u16 entryCount
       + entryCount * {u16 sectorOffset, u16 offset, u16 sectorSizeUB, u16 size}
       data starts at 6+2+entryCount*8
       realOffset = dataStart + sectorOffset*0x800 + offset
       realSize   = (sectorSizeUB-1)//0x20*0x10000 + size
   Entry 0 is the name table, entries 1/2 are nested MRG tables, entries 3..
   are `MZX0` LZ-compressed script files.

2. Each `MZX0` file (magic + u32 rawSize + LZ block) is decompressed with the
   official MZX0 decoder using the `xorff=True` variant (custom scripts XOR the
   literal bytes with 0xFF); the result is CP932 SJS script text.

3. The script is a `;`-separated opcode stream:
       _ZM<id>(text)     one message (dialogue / narration)
       _MSAD(text)       continuation appended to the current message
       _MTLK1(,姓^名)    inline speaker name  -> dropped
       _SELR(idx,text,.) choice option
   Inline markup inside text:  `^` line break, `@n` page break,
   `<base,reading>` ruby.  `＊Ａ` = protagonist surname, `＊Ｂ` = given name.
"""
import os
import re
import struct
import sys
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hunex'))
from pshx_tools_mzx_decomp_mzx0 import mzx0_decompress  # noqa: E402

SURNAME = '美原'
GIVEN = '鈴'
GLYPH = '〓'   # placeholder for an undecodable user-defined font glyph

RE_RUBY = re.compile(r'<([^,<>]+),([^<>]*)>')
RE_STMT = re.compile(r'(_[A-Za-z][A-Za-z0-9_]*)\(([^()]*)\)')
RE_ZM = re.compile(r'^_ZM')


def _ruby(m):
    """`<base,reading>` -> base.  A few ruby bases use user-defined font glyphs
    (CP932 0xE0-0xEF) that cannot be decoded; fall back to the kana reading."""
    base, reading = m.group(1), m.group(2)
    if '\ufffd' in base:
        return reading
    return base


def clean(s):
    s = RE_RUBY.sub(_ruby, s)
    s = s.replace('^', '').replace('@n', '')
    s = s.replace('＊Ａ', SURNAME).replace('＊Ｂ', GIVEN)
    s = s.replace('\ufffd', GLYPH)          # user-defined glyph outside ruby
    return s.strip()


def parse_mrg(blob):
    """Return the list of raw entries of a HuneX MRG blob."""
    if blob[:6] != b'mrgd00':
        raise ValueError('not mrgd00: %r' % blob[:6])
    n, = struct.unpack_from('<H', blob, 6)
    base = 6 + 2 + n * 8
    out = []
    for k in range(n):
        so, off, ub, sz = struct.unpack_from('<HHHH', blob, 8 + k * 8)
        real = (ub - 1) // 0x20 * 0x10000 + sz
        o = base + so * 0x800 + off
        out.append(blob[o:o + real])
    return out


def decompress_mzx(blob):
    raw_size, = struct.unpack_from('<I', blob, 4)
    st, out = mzx0_decompress(BytesIO(blob[8:]), len(blob) - 8, raw_size, xorff=True)
    return out.read()


def parse_script(text):
    """SJS opcode stream -> list of message lines (in order)."""
    lines = []
    cur = None

    def flush():
        nonlocal cur
        if cur:
            lines.append(cur)
        cur = None

    for m in RE_STMT.finditer(text):
        name, arg = m.group(1), m.group(2)
        if RE_ZM.match(name):
            flush()
            cur = clean(arg) or None
        elif name == '_MSAD':
            t = clean(arg)
            cur = (cur + t) if cur else (t or None)
        elif name == '_SELR':
            flush()
            parts = arg.split(',')
            if len(parts) >= 2:
                t = clean(parts[1])
                if t:
                    lines.append(t)
        # _MTLK/_MTLK1/_PMVN/_PRAI/... = names & UI -> ignored
    flush()
    return lines


def extract(mrg_path, out_path):
    entries = parse_mrg(open(mrg_path, 'rb').read())
    all_lines = []
    per = []
    for i, e in enumerate(entries):
        if e[:4] != b'MZX0':
            continue
        try:
            text = decompress_mzx(e).decode('cp932', 'replace')
        except Exception as ex:
            per.append((i, 0, 'ERR %s' % ex))
            continue
        ls = parse_script(text)
        per.append((i, len(ls), ''))
        all_lines.extend(ls)
    with open(out_path, 'w', encoding='utf-8-sig') as f:
        for ln in all_lines:
            f.write(ln + '\n')
    return all_lines, per


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    lines, per = extract(src, dst)
    print('scripts=%d  lines=%d -> %s' % (len(per), len(lines), dst))
