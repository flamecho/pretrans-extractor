import struct, sys, os, glob

# player-name variables (Squirrel `f.*` fields displayed inline in dialogue)
VAR_NAMES = {'f.name': '由香里', 'f.family': '姫宮'}


def classify(seg):
    """Classify one 08-record payload.

    Returns ('var', resolved_text) / ('code', text) / ('str', text) / None.
    """
    t = None
    try:
        t = seg.decode('cp932')
    except Exception:
        return None
    if t is None or '\ufffd' in t or not t:
        return None
    if all(32 <= ord(c) < 127 for c in t):
        if t in VAR_NAMES:
            return ('var', VAR_NAMES[t])
        return ('code', t)
    if any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in t):
        return ('str', t)
    return None


def extract_records(b):
    """Walk a .cnut record stream: 08 <u32 len> <payload> + 10 00 00 00 sep."""
    res = []
    i = 0
    n = len(b)
    while i < n - 5:
        if b[i] == 0x08:
            L = struct.unpack_from('<I', b, i + 1)[0]
            if 0 < L <= 8000 and i + 5 + L <= n:
                rec = classify(b[i + 5:i + 5 + L])
                if rec:
                    res.append(rec)
                i += 5 + L
                continue
        i += 1
    return res


def extract_strings(b):
    """Backward-compatible: JP text records only."""
    return [t for k, t in extract_records(b) if k == 'str']


def collect(files):
    out = []
    for p in files:
        for t in extract_strings(open(p, 'rb').read()):
            out.append(t)
    return out

if __name__=='__main__':
    d=sys.argv[1]
    files=sorted(glob.glob(os.path.join(d,'*')))
    alls=collect(files)
    print('files:',len(files),'strings:',len(alls))
    import re
    PUNC=re.compile(r'[。、！？…「」『』（）]')
    withp=[t for t in alls if PUNC.search(t)]
    print('with punctuation:', len(withp))
    # short strings (<=4) samples = likely labels
    from collections import Counter
    shorts=Counter(t for t in alls if len(t)<=4)
    print('short(<=4) unique:', len(shorts), 'top:', shorts.most_common(30))
