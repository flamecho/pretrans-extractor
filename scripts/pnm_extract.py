"""Princess Nightmare (PS2, SLPM-66973) script text extractor.

Chain: ISO9660 -> DATA/DATA.TAG (32-byte entries, names at 0x810) ->
       DATA/DATA.BIN -> *.AS (plain Squirrel-like text table, cp932)
Record: _global.msg[chapter][seq] = [8 ints, "name", "text", <tags...>];
        type 3/4 (first int) = choice: [8 ints, "", "prompt", "opt"..., <tags>]
One record = one message box (one click).  "\r" inside a string = line break
inside the same box -> merged.
"""
import os
import re
import sys
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from iso9660 import ISO

ISO_PATH = '_src_pnm/Princess Nightmare [NTSC-J] [SLPM-66973].iso'
WORK = '_work_pnm'

REC = re.compile(rb'_global\.msg\[(\d+)\]\[(\d+)\]\s*=\s*\[(.*?)\];', re.S)
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]')
TAG = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')


def iso_files():
    i = ISO(ISO_PATH)
    out = {}

    def walk(rec, prefix=''):
        for e in i.entries(rec):
            nm = e['name']
            if isinstance(nm, bytes):
                nm = nm.decode('ascii', 'replace')
            if nm in ('.', '..'):
                continue
            if e['flags'] & 2:
                walk(e, prefix + nm + '/')
            else:
                out[prefix + nm] = (e['lba'], e['size'])
    walk(i.root)
    return i, out


def tag_entries():
    d = open(os.path.join(WORK, 'tag', 'DATA.TAG'), 'rb').read()
    n = (len(d) - 0x810) // 32
    out = []
    for k in range(n):
        e = d[0x810 + k * 32:0x810 + (k + 1) * 32]
        nm = e[:16].split(b'\0')[0].decode('ascii', 'replace')
        flag, off, size, aligned = struct.unpack('<4I', e[16:])
        out.append((nm, off, size))
    return out


def dump_scripts():
    os.makedirs(os.path.join(WORK, 'tag'), exist_ok=True)
    i, files = iso_files()
    tag = os.path.join(WORK, 'tag', 'DATA.TAG')
    lba, size = files['DATA/DATA.TAG']
    i.f.seek(lba * 2048)
    open(tag, 'wb').write(i.f.read(size))
    bin_lba = files['DATA/DATA.BIN'][0]
    dst = os.path.join(WORK, 'as')
    os.makedirs(dst, exist_ok=True)
    got = []
    for nm, off, size in tag_entries():
        if not nm.endswith('.AS'):
            continue
        i.f.seek(bin_lba * 2048 + off)
        open(os.path.join(dst, nm), 'wb').write(i.f.read(size))
        got.append(nm)
    return got


def fields(body):
    """Split an array body into [is_string, value] pairs."""
    parts = []
    p = 0
    while p < len(body):
        c = body[p]
        if c == '"':
            q = p + 1
            while q < len(body) and body[q] != '"':
                q += 1
            parts.append((True, body[p + 1:q]))
            p = q + 1
        elif c == ',':
            p += 1
        else:
            q = p
            while q < len(body) and body[q] != ',':
                q += 1
            parts.append((False, body[p:q].strip()))
            p = q
    return parts


def parse(path):
    raw = open(path, 'rb').read()
    out = []
    for m in REC.finditer(raw):
        ch, seq = int(m.group(1)), int(m.group(2))
        parts = fields(m.group(3).decode('cp932'))
        nums = [v for s, v in parts if not s]
        strs = [v for s, v in parts if s]
        if not strs:
            continue
        typ = nums[0] if nums else '1'
        if typ in ('3', '4'):
            # choice: "", prompt, options..., <se/tag>
            prompt = strs[1] if len(strs) > 1 else ''
            opts = [x for x in strs[2:] if JP.search(x)]
            out.append((ch, seq, 'choice', prompt, opts))
        else:
            name = strs[0] if strs else ''
            text = strs[1] if len(strs) > 1 else ''
            out.append((ch, seq, 'msg', name, text))
    return out


FIXED = []


def clean(text):
    text = text.replace('\\r', '')
    text = text.replace('\\"', '"')
    # source typo: a full-width "（" closed by ASCII ")"  (3 lines)
    if text.count('（') > text.count('）') and text.endswith(')'):
        text = text[:-1] + '）'
        FIXED.append(text)
    return text


def main():
    files = sorted(f for f in os.listdir(os.path.join(WORK, 'as')) if f.endswith('.AS'))
    files.sort(key=lambda f: int(re.sub(r'\D', '', f)))
    seen = set()
    lines = []
    stat = []
    for fn in files:
        recs = parse(os.path.join(WORK, 'as', fn))
        texts = [clean(t) for _, _, k, _, t in recs for t in ([t] if k == 'msg' else [])]
        texts = [t for t in texts if t]
        dup = sum(1 for t in texts if t in seen) / max(1, len(texts))
        variant = dup >= 0.90
        kept = 0
        for ch, seq, kind, a, b in recs:
            if kind == 'choice':
                opts = [clean(o) for o in b if clean(o)]
                if variant:
                    # the whole block came from an already-emitted chapter
                    if any(o in seen for o in opts):
                        continue
                elif a and clean(a):
                    lines.append(clean(a))
                for o in opts:
                    lines.append(o)
                    seen.add(o)
                    kept += 1
            else:
                t = clean(b)
                if variant and t in seen:
                    continue
                if t:
                    lines.append(t)
                    seen.add(t)
                    kept += 1
        for t in texts:
            seen.add(t)
        stat.append((fn, len(recs), len(texts), kept, variant))

    dst = '提取结果/[PS2-JP]プリンセスナイトメア.txt'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        for t in lines:
            f.write(t + '\n')

    for s in stat:
        print('%-8s recs=%4d text=%4d out=%4d %s' % (s[0], s[1], s[2], s[3], 'VARIANT' if s[4] else ''))
    print('total lines', len(lines))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'unpack':
        print(dump_scripts())
    else:
        main()
