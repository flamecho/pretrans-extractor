# -*- coding: utf-8 -*-
"""[PC-JP]星の王女 ～宇宙意識に目覚めた義経～ final extractor.

L0/L1 evidence:
  * CRPT type-3 shell decrypt: 1024B blocks, out[0]=blk[0x2C],
    out[i]=blk[(0x43+0x17*i)&0x3FF]^out[i-1]; then XOR 256-dword LCG table
    (SEED 0x915354A9 / MUL 0x41C64E6D / ADD 0x3039). Payload at 0x20,
    declared size at +8.  Plaintext magic = 'GSCE'.
  * GSCE string pool at 0x4F5378: [u32 sid][u32 len][NUL-separated cp932 tokens];
    entries close exactly at EOF (0x6BC25B), i.e. self-delimiting (L1).
  * Story scripts = pool entries 426..840 (sids 864..1278); entry 0 of each is
    the chapter title, followed by resource tokens, then
    [name plate][voice id][text] groups.
  * One Japanese text token = one displayed message = one click = one line
    (voice-id anchored groups; no click code inside text tokens, only in-box
    0x08 breaks which are merged).  => single version, no dual layout.
  * Control codes proven in this game's story tokens:
      b'\\x05\\x80\\x80\\x80\\xc9\\xe4'  name macro -> 桜子 (standalone = plate)
      b'\\x10' base b'\\x11' reading b'\\x12'   ruby -> keep base only
      b'\\x02\\x80'                     style/text-run prefix -> strip
      b'\\x01\\x8f' / b'\\x01\\x8b'      emphasis open/close -> strip (2B)
      b'\\x07' + 2B (0x83 0xf4)         one display-effect command -> strip
      b'\\x08'                          in-box line break -> merge
      b'\\x09'                          paragraph indent -> strip
  * Name plates: standalone macro token and '？？？' placed immediately before a
    voice id; kept and merged inline before the following text (2026-11-08 rule).
  * Literal/macro variant pairs: adjacent units whose rendered text is identical
    and where exactly one raw token carries the macro -> keep the macro version.
"""
import struct, re, os, sys, argparse, json

CODE_NAME = {}
_cm = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'codemap.json')
if os.path.exists(_cm):
    CODE_NAME = json.load(open(_cm, encoding='utf-8'))

MUL, ADD, SEED, MASK = 0x41C64E6D, 0x3039, 0x915354A9, 0xFFFFFFFF
_s = SEED
_T = []
for _ in range(256):
    _T.append(_s)
    _s = (_s * MUL + ADD) & MASK
TB = b''.join(int(x).to_bytes(4, 'little') for x in _T)

POOL = 0x4F5378
STORY_LO, STORY_HI = 426, 840          # inclusive
GLOSSARY_ENTRY = 364                   # sid 412, 用語辞典

MACRO = b'\x05\x80\x80\x80\xc9\xe4'
MACRO_NAME = '桜子'
PLATE_UNKNOWN = '？？？'

VOICE = re.compile(r'^\$?[A-Za-z0-9]{2,6}(?:-[A-Za-z0-9]{1,6}){2,4}(?:_(?:ef|EF|lev|LEV))?$')
KANJI = re.compile(r'[\u4e00-\u9fff]')
KANA_ONLY = re.compile(r'^[\u3040-\u30ff\u30fc／/\s]+$')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
JP_PUNCT = re.compile(r'[\u3000-\u303f\uff01-\uff60\u2010-\u2015\u2026]')
IMG = re.compile(r'^(?:fc|tbg|bg|if|st|stm|tx)_', re.I)

RUBY = re.compile(rb'\x10(.*?)\x11.*?\x12', re.S)
CLEAN_BYTES = [(b'\x02\x80', b''), (b'\x01\x8f', b''), (b'\x01\x8b', b''),
               (b'\x07\x83\xf4', b''), (b'\x07', b''), (b'\x08', b''), (b'\x09', b'')]


def decrypt(data):
    declared = struct.unpack('<I', data[8:12])[0]
    pay = data[0x20:]
    out = bytearray()
    for k in range((len(pay) + 1023) // 1024):
        blk = pay[k * 1024:(k + 1) * 1024]
        if len(blk) < 1024:
            blk += bytes(1024 - len(blk))
        o = bytearray(1024)
        prev = blk[0x2C]
        o[0] = prev
        ecx = 0x43
        for i in range(1, 1024):
            prev = blk[ecx & 0x3FF] ^ prev
            o[i] = prev
            ecx = (ecx + 0x17) & 0x3FF
        out += bytes(a ^ b for a, b in zip(o, TB))
    return bytes(out[:declared])


def parse_entries(plain):
    N = len(plain)
    ents = []
    off = POOL
    while off + 8 <= N:
        sid, ln = struct.unpack('<II', plain[off:off + 8])
        if not (1 <= ln <= 0x40000 and sid <= 0x40000) or off + 8 + ln > N:
            break
        ents.append((sid, plain[off + 8:off + 8 + ln]))
        off += 8 + ln
    return ents, off


def render(raw):
    """bytes token -> visible string (macro expanded, ruby base kept)."""
    b = raw.replace(MACRO, MACRO_NAME.encode('cp932'))
    b = RUBY.sub(rb'\1', b)
    for a, c in CLEAN_BYTES:
        b = b.replace(a, c)
    try:
        s = b.decode('cp932')
    except UnicodeDecodeError:
        return None
    s = ''.join(ch for ch in s if ch >= ' ')
    return s.strip()


def is_text(s):
    return bool(JP.search(s) or JP_PUNCT.search(s))


def tok_kind(t):
    """'voice' / 'text' / None(resource) for a raw token."""
    try:
        s = t.decode('cp932')
    except UnicodeDecodeError:
        return None
    if VOICE.match(s):
        return 'voice'
    return 'text' if is_text(s) else None


def next_kind(toks, i):
    """Kind of the first voice/text token after i (resources skipped)."""
    for j in range(i + 1, min(len(toks), i + 5)):
        k = tok_kind(toks[j])
        if k:
            return k
    return None


def label_shape(r):
    """Standalone speaker-name shape: no quotes, no sentence punctuation."""
    if not r or r[0] in '「『' or r[-1] in '。！？…、':
        return False
    return len(r) <= 12


def build_labels(ents):
    """Speaker-name catalogue taken from pool position (L1):
    standalone short string immediately followed by a voice id."""
    labels = set()
    for ei in range(STORY_LO, STORY_HI + 1):
        toks = [t for t in ents[ei][1].split(b'\x00') if t]
        for i, t in enumerate(toks):
            if i == 0 or MACRO in t:
                continue
            try:
                s = t.decode('cp932')
            except UnicodeDecodeError:
                continue
            if not is_text(s):
                continue
            r = render(t)
            if r is None or not label_shape(r):
                continue
            if i + 1 < len(toks) and tok_kind(toks[i + 1]) == 'voice':
                labels.add(r)
    return labels


def story_units(payload, labels):
    """Return list of [plate, voice, rendered, rawtext] in script order."""
    toks = [t for t in payload.split(b'\x00') if t]
    units = []
    plate = None
    voice = None
    for i, t in enumerate(toks):
        if t == MACRO:
            plate = MACRO_NAME
            continue
        if t == b'\x81\x48\x81\x48\x81\x48' and next_kind(toks, i) == 'voice':
            plate = PLATE_UNKNOWN
            continue
        try:
            s = t.decode('cp932')
        except UnicodeDecodeError:
            continue
        if VOICE.match(s):
            voice = s
            continue
        if is_text(s):
            r = render(t)
            if r is None:
                continue
            if i > 0 and r in labels and next_kind(toks, i) == 'voice':
                plate = r
                continue
            if plate is None and voice:
                plate = CODE_NAME.get(voice.lstrip('$').split('-')[0].upper())
            units.append([plate, voice, r, t])
            plate = None
            voice = None
    return units


def dedupe_variants(units, stats):
    """Drop literal copy when adjacent to its macro twin (same rendered line)."""
    out = []
    for u in units:
        if out:
            p = out[-1]
            if p[2] == u[2]:
                pm = MACRO in p[3]
                um = MACRO in u[3]
                if pm != um:
                    stats['variant_pairs'] += 1
                    if um:              # keep the macro version
                        out[-1] = u
                    continue
        out.append(u)
    return out


def build_glossary(payload):
    toks = [t.decode('cp932', 'replace') for t in payload.split(b'\x00')]
    while toks and toks[-1] == '':
        toks.pop()

    def isdesc(i):
        t = toks[i]
        if not t or KANA_ONLY.match(t) or not JP.search(t):
            return False
        if not (KANJI.search(t) or t.endswith('。') or t.endswith('…')):
            return False
        if len(t) < 6:
            return False
        if t.endswith('。') or t.endswith('…') or '\x08' in t:
            return True
        nx = toks[i + 1] if i + 1 < len(toks) else ''
        return bool(IMG.match(nx))

    items = []
    prev_end = -1
    prev_desc = None
    for i, t in enumerate(toks):
        if not isdesc(i):
            continue
        if prev_desc is not None and t == prev_desc.split('\x08')[0]:
            prev_end = i
            continue
        seg = [j for j in range(prev_end + 1, i) if toks[j]]
        jp = [j for j in seg if JP.search(toks[j])]
        head = toks[jp[0]] if jp else None
        items.append((head, t))
        prev_end = i
        prev_desc = t
    lines = []
    for head, desc in items:
        d = desc.replace('\x08', '')
        d = ''.join(ch for ch in d if ch >= ' ')
        if head and d:
            lines.append('【%s】%s' % (head, d))
    return lines


def extract(plain):
    ents, endoff = parse_entries(plain)
    labels = build_labels(ents)
    stats = {'entries': len(ents), 'story_entries': 0, 'units': 0, 'lines': 0,
             'plates': 0, 'variant_pairs': 0, 'gloss': 0, 'labels': len(labels)}
    body = []
    for ei in range(STORY_LO, STORY_HI + 1):
        sid, payload = ents[ei]
        stats['story_entries'] += 1
        units = story_units(payload, labels)
        units = dedupe_variants(units, stats)
        stats['units'] += len(units)
        for plate, voice, r, raw in units:
            line = (plate + r) if plate else r
            if plate:
                stats['plates'] += 1
            body.append(line)
    stats['lines'] = len(body)
    gloss = build_glossary(ents[GLOSSARY_ENTRY][1])
    stats['gloss'] = len(gloss)
    return body, gloss, stats, endoff


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('sce')
    ap.add_argument('out')
    a = ap.parse_args()
    plain = decrypt(open(a.sce, 'rb').read())
    with open(os.path.splitext(a.out)[0] + '_plain.bin', 'wb') as f:
        f.write(plain)
    body, gloss, stats, endoff = extract(plain)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for ln in body:
            f.write(ln + '\n')
        for g in gloss:
            f.write(g + '\n')
    print('total lines', len(body) + len(gloss), 'body', len(body), 'gloss', len(gloss))
    print('stats', stats, 'end', hex(endoff), 'len', len(plain))
