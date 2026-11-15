import struct, zlib, re
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, "_work_toiro/src/toiro_gekka/sys/scenario.swf")
OUT = os.path.join(VNTRANS_HOME, "提取结果/[PC-JP]といろ小町 〜紅に染まるそのときまで〜.txt")
PLACEHOLDER = "＄＄＄"
# protagonist name placeholder ＄＄＄ resolves to the GIVEN name only (茜);
# full name is 二藍 茜 (二藍 = surname, never appears in script).
PROTAGONIST = "茜"
KANJI = re.compile(r'[ぁ-んァ-ヶ一-龯]')
# bare name-box-set tokens that only ever appear as standalone name display,
# never as [dialogue,name] 2-string ops -> dropped (verified against bytecode context)
NAME_OVERRIDE = {"かすみ", "貝洋建設白井", "朋子", "藤崎さん", "藤村さん"}

def decompress(path):
    data = open(path, "rb").read()
    sig = data[:3]
    if sig == b'FWS': return data[8:]
    if sig == b'CWS': return zlib.decompress(data[8:])
    if sig == b'ZWS': return lzma.decompress(data[8:])
    return None

def parse_header(d):
    p = 0; nbits = d[p] >> 3; p += (nbits*4+5+7)//8; p += 4; return p

def tags(d):
    p = parse_header(d); n = len(d)
    while p+2 <= n:
        hdr = struct.unpack_from("<H", d, p)[0]; typ = hdr >> 6; ln = hdr & 0x3F; p += 2
        if ln == 0x3F:
            ln = struct.unpack_from("<I", d, p)[0]; p += 4
        if p + ln > n: break
        yield typ, d[p:p+ln]; p += ln

def constpool(operand):
    out = []
    if len(operand) < 2: return out
    cnt = struct.unpack_from("<H", operand, 0)[0]
    j = 2; k = 0
    while k < cnt and j < len(operand):
        e = operand.find(b'\x00', j)
        if e < 0: s = operand[j:]; j = len(operand)
        else: s = operand[j:e]; j = e+1
        try: out.append(s.decode('utf-8'))
        except: out.append(None)
        k += 1
    return out

def inline_strings(seg):
    """raw NUL-terminated UTF-8 jp strings inside a push operand.
    This game uses a CUSTOM Push operand format (string preceded by an 8-byte
    header like XX 00 07 YY <flag> 00 00 00); standard AS2 ty-parsing misses it,
    but the strings are still NUL-terminated UTF-8, so a raw scan captures them."""
    out = []
    for part in seg.split(b'\x00'):
        if len(part) < 2: continue
        try: s = part.decode('utf-8')
        except: continue
        if KANJI.search(s): out.append(s)
    return out

def pool_ref_strings(seg, pool):
    """resolve ty=8/ty=9 constant-pool references (reusable strings: names + common lines)."""
    out = []; i = 0; m = len(seg)
    while i < m:
        ty = seg[i]; i += 1
        if ty == 8:
            if i < m:
                idx = seg[i]; i += 1
                if 0 <= idx < len(pool) and pool[idx]: out.append(pool[idx])
        elif ty == 9:
            if i+2 <= m:
                idx = struct.unpack_from("<H", seg, i)[0]; i += 2
                if 0 <= idx < len(pool) and pool[idx]: out.append(pool[idx])
        elif ty == 0:
            e = seg.find(b'\x00', i); i = (e+1) if e >= 0 else m
        elif ty == 1: i += 4
        elif ty == 6: i += 8
        elif ty in (4,5,7): i += 1
        elif ty in (2,3): pass
        else: break
    return out

def is_text(s):
    if s is None: return None
    if PLACEHOLDER in s: return s.replace(PLACEHOLDER, PROTAGONIST)
    if KANJI.search(s): return s
    return None

def clean(s):
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s).replace('\r','').replace('\n','')

def main():
    d = decompress(SRC)
    push_ops = []
    for t, b in tags(d):
        if t in (12, 59):
            pool = []
            i = 0; n = len(b)
            while i < n:
                op = b[i]; i += 1
                if op & 0x80:
                    if i+2 > n: break
                    l = struct.unpack_from("<H", b, i)[0]; i += 2; operand = b[i:i+l]; i += l
                else: operand = b""
                if op == 0x88:
                    pool = constpool(operand)
                elif op == 0x96:
                    strs = inline_strings(operand) + pool_ref_strings(operand, pool)
                    seen = set(); uniq = []
                    for s in strs:
                        if s not in seen:
                            seen.add(s); uniq.append(s)
                    push_ops.append(uniq)

    # authorized name set: names from [dialogue,name] 2-string ops + override
    name_set = set(NAME_OVERRIDE)
    for strs in push_ops:
        jp = [t for t in (is_text(s) for s in strs) if t]
        if len(jp) == 2:
            name_set.add(clean(jp[1]))

    lines = []
    n_choice = n_mono = n_namedrop = 0
    for strs in push_ops:
        jp = [t for t in (is_text(s) for s in strs) if t]
        if not jp:
            continue
        if len(jp) == 1:
            c = clean(jp[0])
            if c in name_set:
                n_namedrop += 1; continue
            lines.append(c)
        elif len(jp) == 2:
            # [dialogue, name] — name is in a SEPARATE name window (名札窓),
            # not the text box; per skill rules drop the name plate, keep only dialogue.
            dialogue = jp[0]
            lines.append(clean(dialogue))
        else:
            # 3+ strings: choice group or split monologue -> per-item lines + merged (双版)
            frags = [clean(s) for s in jp]
            if any(f in name_set for f in frags):
                n_namedrop += 1; continue
            for s in frags:
                lines.append(s)
            lines.append("".join(frags))     # merged line
            n_choice += 1

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\ufeff")
        f.write("\n".join(lines))
        f.write("\n")
    print(f"push-ops total: {len(push_ops)}")
    print(f"output lines: {len(lines)}  | 3+-str ops(dual): {n_choice} | bare-name dropped: {n_namedrop}")

if __name__ == "__main__":
    main()
