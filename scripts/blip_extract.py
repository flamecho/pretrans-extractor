# -*- coding: utf-8 -*-
"""Butterfly Lip (PC / WillPlus-AdvHD) text extractor.

Disc set:
  DKLDISC1.iso   : base game -> Rio.arc     (BL_* story + OMAKE01* + system)
  DKLAPPEND.iso  : 'After Love' patch -> RIO+.arc (OMAKE02*/OMAKE03*)

Engine : WillPlus / AdvHD   (see scripts/advhd.py)
Cipher : every byte of a WSC file is rotl_8(c, 6)   (decrypt == rotl_8(c, 6))
Text   : op41 = narration ; op42 = speaker+line ; op02 = choices
Line   : one message box == one line. literal '\\n' (0x5C 0x6E) = soft break -> merged.

Output : 提取结果/Butterfly Lip_全文本.txt              (BL_* + OMAKE01*)
         提取结果/Butterfly Lip After Loveパッチ_全文本.txt (OMAKE02* + OMAKE03*)

Usage:
    python scripts/blip_extract.py _work_blip/Rio.arc _work_blip/APP/RIO+.arc 提取结果
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import advhd

BL_RE = re.compile(r'^BL_(\d+)')
OMK_RE = re.compile(r'^OMAKE(\d+)')

def is_story(name):
    return bool(BL_RE.match(name) or OMK_RE.match(name))

def sortkey(name):
    m = BL_RE.match(name)
    if m: return (0, int(m.group(1)), name)
    m = OMK_RE.match(name)
    if m: return (1, int(m.group(1)), name)
    return (9, 0, name)

def collect(arc, pred):
    d = open(arc, 'rb').read()
    ents = advhd.parse_arc(d)
    names = sorted((n for n in ents if pred(n)), key=sortkey)
    out = []
    for n in names:
        ext, ln, so = ents[n]
        if ext != 'WSC':
            continue
        out += advhd.messages_of(advhd.decrypt(d[so:so + ln]))
    return out, names

def main():
    base = sys.argv[1]
    app = sys.argv[2] if len(sys.argv) > 2 else None
    outdir = sys.argv[3] if len(sys.argv) > 3 else '提取结果'
    os.makedirs(outdir, exist_ok=True)

    lines, names = collect(base, is_story)
    out = os.path.join(outdir, "Butterfly Lip_全文本.txt")
    advhd.write_txt(out, lines)
    print(f"base : {len(lines)} lines  ({len(names)} scripts) -> {out}")

    if app and os.path.exists(app):
        lines2, names2 = collect(app, is_story)
        out2 = os.path.join(outdir, "Butterfly Lip After Loveパッチ_全文本.txt")
        advhd.write_txt(out2, lines2)
        print(f"patch: {len(lines2)} lines  ({len(names2)} scripts) -> {out2}")

if __name__ == '__main__':
    main()
