#!/usr/bin/env python3
"""鳥籠のマリアージュ ～初恋の翼～ (PSV, PCSG90230, Kalmia8 / ACTGS engine)
main.snr 剧本文本提取。

SNR format (reverse-engineered):
  header 0x20 bytes: "SNR " + u32 filesize + ...
  script region: linear command stream.  Message record:
     87 <A:u16> <F:u8> 01 <C:u16> <LEN:u16> <LEN bytes content>
  content = [speaker-name] @r [@v<voice>] text            (@r = line break)
  ruby:    @b <reading>. @< <base> @>      -> keep <base>
  macro:   %0 = protagonist given name
  choice gadget (inline, in gaps):
     ... 01 80 xx xx 07 <91 49 91 f0 8e 88 00 '選択肢'> <u8 blocklen>
         <opt1> 00 <opt2> 00 ... 00 00
"""
import re, struct, sys, os

SEL = b'\x91\x49\x91\xf0\x8e\x88\x00'      # "選択肢"
NAME = '佳奈子'                              # protagonist given name (default)


def parse_records(d):
    recs = []
    lastA = -1
    for m in re.finditer(b'\x87', d):
        o = m.start()
        if o + 9 > len(d):
            break
        A = struct.unpack_from('<H', d, o + 1)[0]
        if d[o + 3] > 0x10:            # F byte usually 0
            continue
        if d[o + 4] != 0x01:
            continue
        C, LEN = struct.unpack_from('<HH', d, o + 5)
        if LEN < 3 or o + 9 + LEN > len(d):
            continue
        body = d[o + 9:o + 9 + LEN]
        if body[-1] != 0 or b'\x00' in body[:-1]:
            continue
        if A <= lastA:
            continue
        recs.append((o, A, C, body))
        lastA = A
    return recs


def parse_choices(d):
    out = []
    for m in re.finditer(re.escape(SEL), d):
        o = m.start()
        p = o + len(SEL)
        if p >= len(d):
            continue
        blk = d[p + 1:p + 1 + d[p]]
        parts = blk.split(b'\x00')
        opts = [x for x in parts if x]
        # sanity: each opt must decode (no control bytes)
        good = []
        for x in opts:
            if any(b < 0x20 for b in x) or len(x) > 200:
                good = []
                break
            good.append(x)
        if len(good) >= 2:
            out.append((o, good))
    return out


def decode(body, has_speaker=True):
    """-> (speaker, text). @r merged, ruby reduced to base, voice dropped."""
    if has_speaker:
        seg = body.split(b'\x40\x72')
        name = ''
        if seg and seg[0]:
            name = seg[0].decode('cp932', 'replace')
            seg = seg[1:]
        text = b''.join(b'\x40\x72' + s for s in seg)[2:] if seg else b''
    else:
        name, text = '', body
    s = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == 0x40 and i + 1 < len(text):
            n = text[i + 1]
            if n == 0x72:                       # line break (already merged)
                i += 2; continue
            if n == 0x76:                       # voice name -> drop
                k = i + 2
                while k < len(text) and 0x20 <= text[k] < 0x7f:
                    k += 1
                i = k; continue
            if n == 0x62:                       # ruby start -> drop reading
                k = text.find(b'\x40\x3c', i)
                i = k if k >= 0 else i + 2
                continue
            if n == 0x3c:
                i += 2; continue                # ruby base start
            if n == 0x3e:
                i += 2; continue                # ruby end
            i += 2; continue                    # unknown @X : drop
        if c == 0x25:                           # %0 macro
            if i + 1 < len(text) and text[i + 1] == 0x30:
                s.append(NAME); i += 2; continue
            i += 1; continue
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            try:
                s.append(text[i:i + 2].decode('cp932'))
            except Exception:
                s.append('\ufffd')
            i += 2; continue
        if c < 0x20:
            i += 1; continue
        s.append(chr(c)); i += 1
    return name, ''.join(s).strip()


def main():
    src = sys.argv[1]
    out = sys.argv[2]
    d = open(src, 'rb').read()
    items = []
    for (o, A, C, b) in parse_records(d):
        nm, tx = decode(b)
        if tx:
            items.append((o, tx))
    nchoice = 0
    for (o, opts) in parse_choices(d):
        for k, x in enumerate(opts):
            tx = decode(x, has_speaker=False)[1]
            if tx:
                items.append((o + k * 0.001, tx))
                nchoice += 1
    items.sort(key=lambda t: t[0])
    lines = [t for _, t in items]
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('records=%d  choice options=%d  lines=%d' %
          (len([1 for _ in items]) - nchoice, nchoice, len(lines)))


if __name__ == '__main__':
    main()
