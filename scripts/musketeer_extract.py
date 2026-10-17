#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Musketeer (PSP/5pb) `.evb` -> text.

A text box ends at `0A 00` (one box = one player click = one output line).
Inside a box, `0A` is a soft line break (merged) and `FE xx` / other
non-character bytes are inline commands (skipped).

Box start = a character whose immediately preceding byte is a print command:
  * `FE <op>`       with op in TEXT_OPS          (original rule), OR
  * `<any> <b>`     with b in PRE = {00,02,1F}   (rule added 2026-10-14;
      such boxes were missed before, e.g. `07 18 00 <text>`).
  The start char must be followed by another character or by `0A 00`,
  which rejects false starts inside `FE FF <u16>` command payloads.
"""
import sys
import os
import glob
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import musketeer_charset as M

# 'print text' opcodes (second byte of an `FE xx` pair that begins a box)
TEXT_OPS = {
    0x00, 0x02, 0x13, 0x15, 0x1D, 0x1E, 0x24, 0x25, 0x27, 0x29, 0x2B, 0x30,
    0x34, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3D, 0x3E, 0x3F, 0x45, 0x48,
    0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x52, 0x53, 0x55, 0x57, 0x58,
    0x59, 0x5A, 0x5F, 0x80, 0x81, 0x82, 0x84, 0x87, 0x88, 0x8B, 0x8C, 0xC0,
    0xC2,
}
PRE = {0x00, 0x02, 0x1F}
# 2-byte commands that also terminate a text box (= page break / new text box):
#   FB FF <u16> <u32> <u32> [<u32>] <text>
#   FE FF <u16> <u32> <u32> <u8>    FE 00 <text>
# (a long narration / option list is stored as several such pages)
SEP_TERM = {(0xFB, 0xFF), (0xFE, 0xFF)}
NAME_MACRO = (0x1D, 0x00)      # inline protagonist-name insertion
# protagonist default name (renameable character -> default inlined, see report)
PROTAGONIST_NAME = 'ダルタニアン'

UNRESOLVED = '〔未解析〕'


def _is_junk(text):
    """reject 1-3 char pure-kanji 'boxes' -- they come from data/table records
    (e.g. `<u16> 0A 00`) mistaken for text; every real line here has kana or
    punctuation."""
    if len(text) < 1 or len(text) > 3:
        return False
    return all('\u4e00' <= ch <= '\u9fff' or ch == '々' for ch in text)


def _lead(b):
    return 0x81 <= b <= 0x9F


def _is_start(data, i, n):
    """data[i] is a lead byte; decide whether a text box starts here."""
    p = data[i - 1]
    if i >= 2 and data[i - 2] == 0xFE and p in TEXT_OPS:
        return True
    if p in PRE:
        if i + 2 < n and _lead(data[i + 2]):
            return True
        if i + 3 < n and data[i + 2] == 0x0A and data[i + 3] == 0x00:
            return True
    return False


def scan(data):
    """yield the raw char-run (bytes, incl. internal 0x0A) of each text box."""
    n = len(data)
    out = []
    i = 1
    while i < n - 1:
        if _lead(data[i]) and _is_start(data, i, n):
            j = i
            closed = False
            while j < n - 1:
                if data[j] == 0x0A and data[j + 1] == 0x00:
                    closed = True
                    break
                if (data[j], data[j + 1]) in SEP_TERM:
                    closed = True
                    break
                if data[j] == 0xFE:          # inline `FE xx` command -> skip 2
                    j += 2
                    continue
                if _lead(data[j]):           # character -> skip 2
                    j += 2
                    continue
                j += 1                        # other inline command byte
            if closed and j > i:
                # the print command may be followed by the name macro; keep it
                st = i - 2 if (i >= 2 and (data[i - 2], data[i - 1]) == NAME_MACRO) else i
                out.append(bytes(data[st:j]))
                i = j + 2
                continue
        i += 1
    return out


def decode(buf, name=None):
    """decode one box -> (text, unresolved_count).  Internal 0x0A merged."""
    if name is None:
        name = PROTAGONIST_NAME
    s = []
    unknown = 0
    q, n = 0, len(buf)
    while q < n:
        if buf[q] == NAME_MACRO[0] and q + 1 < n and buf[q + 1] == NAME_MACRO[1]:
            s.append(name)
            q += 2
            continue
        if buf[q] == 0x0A:
            q += 1
            continue
        if _lead(buf[q]) and q + 1 < n:
            code = (buf[q] << 8) | buf[q + 1]
            q += 2
            ch = M.decode_char(code)
            if ch is None:
                if M.is_effect(code):
                    continue
                unknown += 1
                s.append(UNRESOLVED)
            else:
                s.append(ch)
            continue
        q += 1
    return ''.join(s).strip(), unknown


def main():
    srcdir = sys.argv[1] if len(sys.argv) > 1 else 'ca000'
    dst = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else PROTAGONIST_NAME
    files = sorted(glob.glob(os.path.join(srcdir, 'ev*.evb')))
    seen = set()
    rows = []
    unknown = collections.Counter()
    for f in files:
        for buf in scan(open(f, 'rb').read()):
            text, unk = decode(buf, name)
            if not text or text in seen or _is_junk(text):
                continue
            seen.add(text)
            rows.append(text)
            unknown[unk] += 0
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(rows) + '\n')
    print('files', len(files), 'lines', len(rows),
          'chars', sum(len(x) for x in rows),
          'unresolved', sum(x.count(UNRESOLVED) for x in rows))


if __name__ == '__main__':
    main()
