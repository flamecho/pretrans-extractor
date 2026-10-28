"""Monochrome Factor - Cross Road (PS2, 5pb) scene text extractor.

Chain : ISO9660 -> SCENE00.AFS (CRI AFS) -> NNNNN.bin scene files
Scene : [header][bytecode][NUL-terminated cp932 string pool][trailer]
Pool  : ordered NUL-terminated strings; one *click* = the records up to and
        including the one carrying %K.

In-string commands
  %K    wait for key  (one click; L0 boundary)
  %P    clear message window (page break, always after %K)
  %p    wait for key + open the choice list (options = the following
        NUL-terminated strings that carry no command)

Name / glyph macros
  %IF0 -> given name of the heroine      (default 芹那)
  %IL0 -> family name                    (default 春宮)
  %IW0 -> full name                      (default 春宮芹那)
  The script also ships a literal copy of every such line (so the voice can
  say the default name); the two copies are two text records inside ONE click
  => mutually exclusive variants, keep one.
  %T2  -> runtime chapter title (no plaintext in the archive -> banner dropped)

Substitution glyphs (custom font slots, not text)
  |-...-|  (U+251C/U+2524/U+2500)  drawn dash / pause mark   -> strip
  <<...>>  (U+226A/U+226B + U+2015) drawn long vowel         -> strip

Output: one click = one line.  Boxes whose segments are near-duplicates are
collapsed to one; genuine multi-op boxes (a shout split in two) are joined.
"""
import glob
import os
import re
import sys

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
CTRL = re.compile(r'[\x00-\x1f\x7f]')
CLEAR = re.compile(r'%CF[0-9A-Fa-f]{6}|%CE|%FS|%FE|%LC|%LE|%[SO]\d{2,4}'
                   r'|%t\d{2,4}|%[LT]\d{0,2}|%[NnDd]')
PH = re.compile(r'[\u251c\u2524][\u2500\u2015\-]*[\u251c\u2524]'
                r'|[\u226a\u226b][\u2015\-\u2500]*[\u226a\u226b]')
PH2 = re.compile(r'[\u251c\u2524\u2500\u2015]+')
NAME = re.compile(r'^(【[^】]{1,40}】)+')
CMDONLY = re.compile(r'^(?:%[A-Za-z][0-9A-Za-z]*)+$')
DEFAULT = (('%IF0', '芹那'), ('%IL0', '春宮'), ('%IW0', '春宮芹那'))

FILES = [i for i in range(16, 93)]


def runs_of(d):
    out = []
    pos = 0
    while True:
        j = d.find(b'\x00', pos)
        if j < 0:
            out.append(d[pos:])
            break
        out.append(d[pos:j])
        pos = j + 1
    return out


def dec(s):
    try:
        t = s.decode('cp932')
    except UnicodeDecodeError:
        return None
    if not t:
        return ''
    if '\ufffd' in t or CTRL.search(t):
        return None
    if any(0xE000 <= ord(c) <= 0xF8FF for c in t):
        return None
    return t


def pool(path):
    d = open(path, 'rb').read()
    tags = []
    for s in runs_of(d):
        t = dec(s)
        if t is None and b'%K' in s:
            # pool starts inside a code run: keep the longest decodable tail
            for k in range(1, len(s)):
                u = dec(s[k:])
                if u:
                    t = u
                    break
        tags.append(t)
    kids = [i for i, t in enumerate(tags) if t and '%K' in t]
    if not kids:
        return []
    b = kids[-1]
    a = b
    while a > 0 and tags[a - 1] is not None:
        a -= 1
    while a <= b and not tags[a]:
        a += 1
    # nothing after the last %K record is script: the 16-byte trailer decodes
    # as one or two stray kanji, so stop at the last click record
    return [tags[k] for k in range(a, b + 1) if tags[k]]


def clean(s):
    for k, v in DEFAULT:
        s = s.replace(k, v)
    s = CLEAR.sub('', s)
    s = PH.sub('', s)
    s = PH2.sub('', s)
    s = re.sub(r'%[KpP]', '', s)
    s = NAME.sub('', s)
    return s.strip('\u3000 ')


def keep(t):
    """text that is a rendered line, not a resource name / banner"""
    if not t:
        return False
    if not JP.search(t):
        return False
    if t.count('～') == 2 and not re.search(r'[^\u3000～]', t):
        return False          # ～　%T2　～ banner after the title was dropped
    return True


def boxes(path):
    out = []          # list of (segments, has_name_macro)
    cur = []
    mac = False
    opt = False
    for s in pool(path):
        hk = '%K' in s
        hp = '%p' in s
        if '%IF0' in s or '%IL0' in s or '%IW0' in s:
            mac = True
        t = clean(s)
        if opt and t and not hk:
            out.append(([t], False))          # one option = one line
            continue
        if hk:
            opt = False
        if t:
            cur.append(t)
        if hk:
            if cur:
                out.append((cur, mac))
            cur = []
            mac = False
            if hp:
                opt = True
    if cur:
        out.append((cur, mac))
    return out


def merge(segs):
    import difflib
    segs = [s for s in segs if keep(s)]
    if not segs:
        return None
    if len(segs) == 1:
        return segs[0]
    r = difflib.SequenceMatcher(None, segs[0], segs[-1]).ratio()
    if r >= 0.5:
        return segs[0]               # name-variant pair: same click, same text
    return ''.join(segs)             # one shout split over two text ops


def lyrics(path):
    """ED song lyrics shown by the sound menu (CONFIG.AFS string block)."""
    d = open(path, 'rb').read()
    out = []
    on = False
    pos = 0
    while True:
        j = d.find(b'\x00', pos)
        if j < 0:
            break
        s = d[pos:j]
        pos = j + 1
        t = dec(s)
        if t is None:
            continue
        if t.startswith('探していたものは'):
            on = True
        if on:
            if not t:
                continue
            out.append(t)
            if t == 'ひとつに…':
                break
    return out


def main():
    out = sys.argv[1]
    root = sys.argv[2] if len(sys.argv) > 2 else '_work_mono/scene'
    lines = []
    seen = {}
    nbox = ndup = nvar = 0
    for i in FILES:
        p = os.path.join(root, '%05d.bin' % i)
        if not os.path.exists(p):
            continue
        h = hash(open(p, 'rb').read())
        if h in seen:
            ndup += 1
            continue
        seen[h] = i
        prev = None
        for segs, mac in boxes(p):
            t = merge(segs)
            if not t:
                continue
            if mac and t == prev:
                nvar += 1         # literal copy + %IF0 copy of the same click
                continue
            lines.append(t)
            prev = t
            nbox += 1
    ly = lyrics(os.path.join(root, '..', 'ex2', 'CONFIG.AFS'))
    lines.extend(ly)
    print('files', len(seen), 'skipped-identical', ndup,
          'lines', nbox, 'name-variants-dropped', nvar, 'lyrics', len(ly))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
