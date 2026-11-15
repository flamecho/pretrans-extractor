#!/usr/bin/env python3
# Pleasure☆ (BARON engine) scenario.arc text extractor.
# Container: ARC  magic, body = sequence of zlib streams (78 01/9c/da).
# Script: line-based. Text lines = cp932 dialogue/narration (one box = one run
# of consecutive text lines; in-box \n merged). `$name` / `名（班级）` = separate
# name window (stripped). The recap/shared block (chunk 190) uses an inline
# name-window variant `名＠＃（班级）` instead of a standalone name line -> also
# stripped. `(※...)` editorial routing notes are not displayed -> stripped.
# Choices = `MENU n <text>` presented by `MENU_CHOICE`.
# 双版: a box whose source text is split by empty lines (>=2 segments) is emitted
# as two versions in the same file: the per-segment lines first, then the merged
# line (segments joined with ''); single-segment boxes stay as one merged line.
import zlib, re, sys, os

KANA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
MENU_RE = re.compile(r'^MENU (\d+) (.*)$')
# Standalone name-plate line: a name followed by a class tag, e.g. 透（2-5）.
# These are separate name windows (like $name) -> stripped. Inline forms
# (e.g. 透（2-5）も…) stay in the dialogue text.
NAMEPLATE = re.compile(r'^[\u3040-\u30ff\u4e00-\u9fff]+（\d+[-－]?\d*）\s*$')
# Inline name-window variant used only in the recap/shared block (chunk 190),
# e.g. 響＠＃（6-10）. Same semantics as a standalone name window -> stripped.
INLINE_NAME = re.compile(r'^[\u3040-\u30ff\u4e00-\u9fff]+＠＃（[^）]*）\s*$')

def read_chunks(path):
    b = open(path, 'rb').read()
    out = []
    i, n = 0, len(b)
    while i < n - 1:
        if b[i] == 0x78 and b[i+1] in (0x01, 0x9c, 0xda):
            try:
                do = zlib.decompressobj()
                o = do.decompress(b[i:])
                if len(o) > 20:
                    out.append(o)
                rem = do.unused_data
                if not rem:
                    break
                i = n - len(rem)
                continue
            except Exception:
                pass
        i += 1
    return out

def is_text(l):
    if not l:
        return False
    if l.startswith('$'):
        return False
    if ord(l[0]) < 0x80:
        return bool(KANA.search(l))
    return True

def extract(scenario_path):
    chunks = read_chunks(scenario_path)
    out = []          # final deliverable lines (script order, global dedup)
    seen = set()
    # run = list of segments; each segment = list of text lines.
    # A source empty line splits the run into a new segment (in-box line break).
    run = []
    def flush():
        if not run:
            return
        segs = [''.join(s) for s in run if s]
        run.clear()
        if not segs:
            return
        merged = ''.join(segs)
        if not merged or merged in seen:
            return
        seen.add(merged)
        if len(segs) >= 2:
            # 双版: list the per-segment lines first, then the merged line
            for s in segs:
                out.append(s)
            out.append(merged)
        else:
            out.append(merged)
    for o in chunks:
        for raw in o.split(b'\n'):
            l = raw.decode('cp932', 'replace').replace('\x00', '').rstrip('\r').strip('\n')
            if l == '':
                # in-box line break -> start a new segment (only if run has text)
                if run and run[-1]:
                    run.append([])
                continue
            if l == 'MENU_CHOICE' or l == 'MENU':
                flush()
                continue
            m = MENU_RE.match(l)
            if m:
                flush()
                text = m.group(2)
                if text and text not in seen:
                    seen.add(text)
                    out.append(text)
                continue
            # format-B choice: bullet + option text, followed by a ->[target] label
            if l.startswith('●'):
                flush()
                text = l[1:].strip()
                if text and text not in seen:
                    seen.add(text)
                    out.append(text)
                continue
            if l.startswith('→') or re.fullmatch(r'→［[^］]*］', l):
                # branch-target label (control flow), not displayed text
                flush()
                continue
            if l.strip() in ('ＢE',):
                # Bad-End route label token
                flush()
                continue
            if l.startswith('（※'):
                # editorial/routing note to scenario writers, not displayed text
                flush()
                continue
            if INLINE_NAME.fullmatch(l):
                # inline name-window variant used in the recap/shared block
                # (e.g. 響＠＃（6-10）); same as standalone name window -> stripped
                flush()
                continue
            if l.startswith('$') or NAMEPLATE.fullmatch(l) or (ord(l[0]) < 0x80 and not KANA.search(l)):
                # name plate or command -> ends box
                flush()
                continue
            # text line: append to the current (or a new) segment
            if not run or not run[-1]:
                run.append([l])
            else:
                run[-1].append(l)
    flush()
    return out

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) > 1:
        sc = sys.argv[1]
    else:
        sc = os.path.join(here, 'extracted', '[JP]PLEASURE☆', 'scenario.arc')
    lines = extract(sc)
    if len(sys.argv) > 2:
        dst = sys.argv[2]
        with open(dst, 'wb') as f:
            f.write(b'\xef\xbb\xbf')
            for ln in lines:
                f.write(ln.encode('utf-8'))
                f.write(b'\n')
        print('wrote', len(lines), 'lines ->', dst)
    else:
        for ln in lines:
            print(ln)
