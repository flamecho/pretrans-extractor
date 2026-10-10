#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BELIEVER! (PSV, PCSG00539)  HuneX / UNAS('HESL') script text extractor.

Reverse-engineered formats (see 提取结果/BELIEVER!_解析报告.md):

  script.heslnk (HESL)
    header 0x30 : 'HESL', version, count, unk1, unk2, name_offset, data_offset
    entries @0x30, 0x10B : checksum, item_offset, item_size
    names @name_offset (NUL terminated, one per entry)
    item[0] = 'charset.csb' : 'CSB\\0' + version + count, char table @0x44,
        6-byte cells (UTF-8 char 1..3B + zero padding)  -> index -> character
    item[n] = 'HESE' script (stored UNcompressed in this title)

  HESE
    header 0x30 : 'HESE', version, code_offset, string_count, text_op_count
    code @code_offset : little-endian instructions
        [u16 opcode][u16 flags][u32 param]     (flags 0x0000 -> bare 4-byte op)
        op 0x1a  NAME : +4B then inline string  (speaker / hero name -> dropped)
        op 0x1b  TEXT : param==0 -> +8B then string ; param!=0 -> +4B then string
                        an empty TEXT is a continuation marker (same text box)

  string = stream of u16 codes, ended by 0x0000 or by a following marker code
        0x0001-0x001F / 0x0023   marker (dropped, ends the string)
        0x0021-0x0024            marker (dropped)
        0x002C                   soft line break inside the box -> merge
        0x8000                   explicit display line break     -> merge
        0xFFFC / 0xFFFF          dropped
        < 0x80                   ascii
        >= 0x8000                character -> charset[(code - 0x8000) - 6]
"""
import os, struct, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, "_work_believer/dec/data/script.heslnk")
OUTDIR = os.path.join(VNTRANS_HOME, "提取结果")
PH = '〔未解析〕'


def hesl_entries(buf):
    magic, ver, count, u1, u2, nameoff, dataoff = struct.unpack_from('<5I12x2I8x', buf, 0)
    assert magic == int.from_bytes(b'HESL', 'little')
    names, o = [], nameoff
    for _ in range(count):
        e = buf.find(b'\0', o)
        names.append(buf[o:e].decode('latin1'))
        o = e + 1
    return [(names[k],) + struct.unpack_from('<3I4x', buf, 0x30 + k * 0x10)
            for k in range(count)]


def load_charset(buf, ents):
    ioff = ents[0][2]
    end = min(x[2] for x in ents if x[2] > ioff)
    csb = buf[ioff:end]
    assert csb[:4] == b'CSB\0', csb[:8]
    cnt = struct.unpack_from('<I', csb, 8)[0]
    reg = csb[0x44:]
    chars, i = [], 0
    while i < len(reg) and len(chars) < cnt:
        b = reg[i]
        if b >= 0xF0:
            l = 4
        elif b >= 0xE0:
            l = 3
        elif b >= 0xC0:
            l = 2
        elif b == 0:
            j = i
            while j < len(reg) and reg[j] == 0:
                j += 1
            i = j
            continue
        else:
            l = 1
        try:
            chars.append(reg[i:i + l].decode('utf-8'))
        except UnicodeDecodeError:
            chars.append(None)
        i += l + (3 - (l % 3)) % 3
    return chars


def decode_text(seg, chars):
    """u16 stream -> one display line (all in-box breaks merged)."""
    s = ''
    for i in range(0, len(seg) - 1, 2):
        c = seg[i] | (seg[i + 1] << 8)
        if c == 0:
            continue
        if c < 0x20 or c == 0x23 or c in (0xFFFC, 0xFFFF):
            continue                     # marker / control
        if c == 0x1D:
            break                        # end of a style block
        if c == 0x2C or c == 0x8000:     # soft / explicit in-box line break
            continue
        if 0x21 <= c <= 0x24:
            continue
        if c < 0x80:
            s += chr(c)
            continue
        idx = c - 0x8000 - 6
        if 0 <= idx < len(chars) and chars[idx]:
            s += chars[idx]
        else:
            s += PH
    s = s.strip()
    if not s or len(s.replace(PH, '')) < 2:
        return None
    return s


def extract_script(sub, chars):
    """-> list of lines; an empty TEXT op is merged into the previous line."""
    magic, ver, codeoff, strcount, unktop = struct.unpack_from('<5I', sub, 0)
    assert magic == int.from_bytes(b'HESE', 'little')
    n = len(sub)

    def term(s):
        k = s
        while k + 1 < n:
            c = sub[k] | (sub[k + 1] << 8)
            if c == 0 or c < 0x20 or c == 0x23:
                return k
            k += 2
        return -1

    out, cont, q = [], False, codeoff
    while q + 8 <= n:
        op = sub[q:q + 4]
        if op == b'\x1b\x00\x00\x80':                     # TEXT
            # two layout variants exist: the inline string either follows an
            # 8-byte instruction, or a 12-byte one (param==0 + extra u32)
            if (sub[q + 8] | (sub[q + 9] << 8)) >= 0x8000:
                s = q + 8
            elif struct.unpack_from('<I', sub, q + 4)[0] == 0:
                s = q + 12
            else:
                q += 8
                continue
            e = term(s)
            if e < 0:
                q += 2
                continue
            t = decode_text(sub[s:e], chars) if e > s else None
            if t is not None:
                out.append(t)
            # some scripts are stored WITHOUT a 0x0000 terminator: the text simply
            # stops where the next instruction begins
            q = e if sub[e:e + 4] == b'\x1b\x00\x00\x80' else e + 2
            continue
        if op == b'\x1a\x00\x00\x80':                     # NAME -> dropped
            e = term(q + 8)
            if 0 < e and e - (q + 8) < 400:
                q = e + 2
                continue
        q += 2
    return out


def main():
    with open(SRC, 'rb') as f:
        buf = f.read()
    ents = hesl_entries(buf)
    chars = load_charset(buf, ents)
    offs = sorted(e[2] for e in ents)
    files = []
    for nm, chk, ioff, dsize in ents:
        if nm.endswith('.csb') or nm.startswith('test_script'):
            continue
        nxt = [x for x in offs if x > ioff]
        end = nxt[0] if nxt else len(buf)
        files.append((nm, extract_script(buf[ioff:end], chars)))

    pref = files[0][1]
    for _, L in files[1:]:
        k = 0
        while k < len(pref) and k < len(L) and pref[k] == L[k]:
            k += 1
        pref = pref[:k]
    final = list(pref)
    for _, L in files:
        final.extend(L[len(pref):])

    # the script stores a few messages as two consecutive TEXT ops without
    # re-opening 「: rejoin them, but only when that is what repairs the quotes
    merged = []
    for l in final:
        if (merged and merged[-1].count('「') > merged[-1].count('」')
                and not l.startswith(('「', '（'))
                and (merged[-1] + l).count('「') == (merged[-1] + l).count('」')):
            merged[-1] += l
        else:
            merged.append(l)
    final = merged
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, 'BELIEVER!_全文本.txt')
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(final) + '\n')
    print('common prefix:', len(pref), pref[:8])
    print('files', len(files), 'lines', len(final))


if __name__ == '__main__':
    main()
