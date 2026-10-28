"""Hakushaku to Yousei (PS2, 5pb) scene text extractor.

Container : ISO9660 -> SCENE00.AFS (CRI AFS) -> NNxxx.bin scene files
Scene file: [header][code][string pool][footer]
String pool: NUL-terminated cp932 strings, in script order.

In-string commands (evidence: every string terminates with %K):
  %K        wait for key (one click)
  %P        clear message window (page break)  -> always right after %K
  %p        wait for key + open choice list
  %N        line break inside the same window (soft wrap -> merge)
  %O032     close overlay window (letter / sign)
  %S032 %FS %FE %LC %LE %tNNN  style/window commands (strip)
  %C------  colour (strip)
  %D        numeric insert (only in point popups -> dropped)

Output: one box = one message window.
  single-segment box -> 1 line
  multi-segment box  -> each segment, then the merged line (A,B,C,ABC rule)
"""
import glob
import os
import re
import sys

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\uff01-\uff5e]')
HAS = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
HK = re.compile(r'[\uff61-\uff9f]')
CLEAR = re.compile(r'%C[0-9A-Fa-f]{6}|%FS|%FE|%LC|%LE|%[SO]\d{2,4}|%t\d{2,4}|%[LT]\d{0,2}|%[KPpND]')
NAME = re.compile(r'^(【[^】]{1,40}】)+')
POPUP = re.compile(r'ポイント *\+')
# ├┤ = 制御用の代替字形（ルビ／間隔のプレースホルダ）。本文ではないので剥がす
PLACEHOLDER = re.compile(r'[├┤]+')


def valid(seg):
    if seg == b'':
        return 0
    for b in seg:
        if b < 0x20 or b == 0x7F:
            return -1
    try:
        t = seg.decode('cp932')
    except Exception:
        return -1
    if '\ufffd' in t or any(0xE000 <= ord(c) <= 0xF8FF for c in t):
        return -1
    if HK.search(t):
        return -1
    return 1 if JP.search(t) else 0


def pool(path):
    d = open(path, 'rb').read()
    runs = []
    pos = 0
    while pos < len(d):
        j = d.find(b'\x00', pos)
        if j < 0:
            runs.append((pos, d[pos:]))
            break
        runs.append((pos, d[pos:j]))
        pos = j + 1
    best = (0, 0, 0)
    cur = 0
    st = 0
    for o, s in runs:
        v = valid(s)
        if v >= 0:
            if cur == 0:
                st = o
            cur += v
            if cur > best[0]:
                best = (cur, st, o + len(s))
        else:
            cur = 0
    n, start, end = best
    idx = [i for i, (o, s) in enumerate(runs) if o == start][0]
    while idx > 0 and valid(runs[idx - 1][1]) >= 0:
        idx -= 1
        start = runs[idx][0]
    # the 16-byte trailer after the last %K string decodes as kanji -> cut it
    last = idx
    for i in range(idx, len(runs)):
        if b'%K' in runs[i][1]:
            last = i
    out = []
    for o, s in runs[idx:last + 1]:
        out.append(s.decode('cp932'))
    return out


def clean(t):
    t = CLEAR.sub('', t)
    t = PLACEHOLDER.sub('', t)
    t = NAME.sub('', t)
    return t.strip('\u3000 ')


def parse_file(path):
    boxes = []      # list of list-of-segments
    opts = []
    expecting_opt = False
    cur = []
    for raw in pool(path):
        if not raw:
            continue
        plain = CLEAR.sub('', raw)
        if POPUP.search(plain):
            continue
        if '%K' in raw:
            expecting_opt = False
            t = clean(raw)
            tail = raw.rstrip()
            if t:
                cur.append(t)
            if tail.endswith('%K%N') or tail.endswith('%K%N%N'):
                continue
            if cur:
                boxes.append(cur)
                cur = []
            if tail.endswith('%K%p'):
                expecting_opt = True
        else:
            t = clean(raw)
            if not t or not HAS.search(t):
                continue
            if expecting_opt:
                opts.append(t)
            else:
                # text without a click command: belongs to the open box
                cur.append(t)
    if cur:
        boxes.append(cur)
    return boxes, opts


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'out.txt'
    files = sorted(glob.glob(os.path.join('_work_hakushaku/scene/*.bin')))
    files = [p for p in files if 16 <= int(os.path.basename(p)[:5]) <= 102]
    lines = []
    nbox = nseg = nopt = nmerge = 0
    for p in files:
        boxes, opts = parse_file(p)
        for b in boxes:
            nbox += 1
            nseg += len(b)
            lines.extend(b)
        for o in opts:
            lines.append(o)
            nopt += 1
    print('boxes', nbox, 'segments', nseg, 'merged', nmerge, 'options', nopt, 'lines', len(lines))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
