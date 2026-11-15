#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract text from Lasting Snow (Witch/Katze) system/text_data.wbc.
.wbc = 8-byte header + zlib stream @32.  Decompressed blob is a TLV script:
  [cmd bytes] <len:u8> 00 <cp932 text of `len` bytes>  (00 = field separator)
Text boxes are length-prefixed cp932; 0x0a inside a box = in-box soft newline (merge).
We anchor on `<len:u8> 00 <SJIS-lead>` then greedily read a maximal cp932 run.
"""
import io, zlib, sys, os

SJIS_LEAD = lambda b: 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef

def try_cp932(b):
    try:
        return b.decode('cp932')
    except Exception:
        return None

def is_text(s):
    return any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f' for c in s)

def read_run(d, start):
    """Greedy maximal cp932+ascii(+0x0a) run from `start`."""
    j = start
    buf = bytearray()
    while j < len(d):
        b = d[j]
        if SJIS_LEAD(b):
            if j + 1 < len(d) and try_cp932(d[j:j+2]):
                buf += d[j:j+2]; j += 2; continue
            else:
                break
        elif 0x20 <= b <= 0x7e:
            buf += bytes([b]); j += 1; continue
        elif b == 0x0a:
            buf += b'\n'; j += 1; continue
        else:
            break
    return bytes(buf), j

# ★ 系统 UI 剔除集（非对白，按交付口径"不收系统 UI"排除；证据见解析报告 §品检）
# 背景・昼/夕方/夜 = 背景场景指令；フリーSep = 日历数据；
# モ*ＮＤ＞/モ*ＯＯＤ ＥＮＤ＞/モ*ＡＰＰＹ ＥＮＤ＞ = 错位捕获的 ＜ＥＮＤ＞/＜ＧＯＯＤ ＥＮＤ＞/＜ＨＡＰＰＹ ＥＮＤ＞ 结局标题。
EXCLUDE = {
    '背景・昼', '背景・夕方', '背景・夜',
    'フリーSep',
    'モdＮＤ＞', 'モfＯＯＤ  ＥＮＤ＞', 'モgＡＰＰＹ  ＥＮＤ＞',
}

def extract(wbc_path):
    raw = open(wbc_path, 'rb').read()
    # header: 8 bytes (ver u32=1, size u32) then zlib @32
    dec = zlib.decompress(raw[32:])
    lines = []
    seen = set()
    i = 0
    n = len(dec)
    while i < n - 1:
        b0 = dec[i]
        # anchor: <len:u8 in 4..250> then text. Two framings:
        #   (a) <len> 00 <SJIS lead>   (00 = field separator)
        #   (b) <len> <SJIS lead>      (no separator; length directly precedes text)
        start = None
        if 4 <= b0 <= 250:
            if i + 2 < n and SJIS_LEAD(dec[i+2]) and dec[i+1] == 0x00:
                start = i + 2
            elif i + 1 < n and SJIS_LEAD(dec[i+1]):
                start = i + 1
        if start is not None:
            run, jend = read_run(dec, start)
            s = try_cp932(run)
            if s is not None and is_text(s):
                s = s.replace('\n', '')  # merge in-box soft newlines -> one box = one line
                if s in EXCLUDE:
                    i = jend
                    continue
                if s not in seen:
                    seen.add(s)
                    lines.append(s)
                i = jend
                continue
        i += 1
    return lines

if __name__ == '__main__':
    wbc = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    lines = extract(wbc)
    print("extracted lines:", len(lines), file=sys.stderr)
    if out:
        with io.open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
            for ln in lines:
                f.write(ln + '\n')
        print("written:", out, file=sys.stderr)
    else:
        for ln in lines[:30]:
            print(ln)
