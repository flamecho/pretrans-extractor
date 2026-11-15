#!/usr/bin/env python3
# Re;quartz零度 (PC / TyranoScript NW.js port) text extractor.
#
# Source path:
#   [JP]Re;quartz零度.exe  (PE32 + RAR5 SFX @0x48E00)
#     -> RJ314876 (4-part DLSite RAR)
#       -> reraid_DLver_20210225/windows_0225_ver103/reraid.exe  (NW.js app,
#          PE + embedded APP ZIP @ offset 61057024)
#         -> data/scenario/*.ks   (UTF-8 no BOM, TyranoScript scripts)
#
# Engine = custom TyranoScript dialect. Boxing rules (L0):
#   [tb_start_text mode=3 ] ... [_tb_end_text]   = one text session
#   line starting with '#'  (e.g. '#ユニ' / lone '#') = name window / close marker -> STRIP
#   [p] = page break = click boundary = new box
#   [r] = soft line break inside the same box (displayed newline)
#   [ruby text="..."] = ruby annotation -> strip tag, keep base char
#   [glink ... text="<choice>" target="*label"] = story choice -> extract text=
#   [button ... storage=...] = system/UI navigation (excluded)
#
# Dual-version rule: a box (one [p]-page) that has >=2 [r]-separated displayed
# lines emits the segment lines first, then the merged line.
#
# NOTE: this is the PC/TyranoScript port. It is a DIFFERENT engine/build from the
# NS version (rq_extract.py: 自研 PAK / 24 03 / UTF-16). Do not reuse that tool.
import os, re, glob, sys

TB_RE = re.compile(r'\[tb_start_text[^\]]*\]')
TB_END = '[_tb_end_text]'
RUBY_RE = re.compile(r'\[ruby[^\]]*\]')
TAG_RE = re.compile(r'\[[^\]]*\]')
GLINK_RE = re.compile(r'\[glink\b[^]]*\]')
SPEAKER_RE = re.compile(r'^#(.+)$')


def strip_tags(s):
    s = RUBY_RE.sub('', s)
    s = TAG_RE.sub('', s)
    return s


# Lines that are debug/variable leftovers inside a tb block (engine does not
# display them; they sit next to [tb_eval] variable increments).
DEBUG_LINE = re.compile(r'[A-Za-z_]\w*\s*=\s*[\w.+\-]+$')


def pages_of_session(session):
    """Return list of boxes; each box is a list of [r]-segment strings."""
    lines = []
    for ln in session.split('\n'):
        st = ln.strip()
        if st.startswith('#'):          # name window / close marker
            continue
        if st.startswith(';'):          # script debug comment
            continue
        # strip inline tags before judging debug/variable lines, so that e.g.
        # "konoe=1[r]" is recognized and dropped.
        clean = TAG_RE.sub('', st).strip()
        if DEBUG_LINE.match(clean):      # e.g. konoe=1 (variable assignment)
            continue
        ln = ln.replace('\xa0', ' ')     # normalize stray nbsp to space
        lines.append(ln)
    body = '\n'.join(lines)
    boxes = []
    for pg in body.split('[p]'):
        segs = [strip_tags(x).strip() for x in pg.split('[r]')]
        # Remove the engine-template leftover token "Unity" (romaji artifact,
        # not narrative; protagonist is ユニ). Only ever appears trailing.
        segs = [s.replace('　Unity', '').replace(' Unity', '').strip() for s in segs]
        segs = [s for s in segs if s]
        if segs:
            boxes.append(segs)
    return boxes


def emit_boxes(boxes, out, seen):
    for segs in boxes:
        merged = ''.join(segs)
        if not merged:
            continue
        if len(segs) >= 2:
            for s in segs:
                if s not in seen:
                    seen.add(s)
                    out.append(s)
            if merged not in seen:
                seen.add(merged)
                out.append(merged)
        else:
            s = segs[0]
            if s not in seen:
                seen.add(s)
                out.append(s)


def iter_blocks(t):
    """Yield (session_str, after_str) for each tb block, in order."""
    i = 0
    n = len(t)
    while i < n:
        m = TB_RE.search(t, i)
        if not m:
            break
        start = m.end()
        end = t.find(TB_END, start)
        if end < 0:
            break
        session = t[start:end]
        after = t[end + len(TB_END):]
        nxt = TB_RE.search(t, end + len(TB_END))
        between = after[: nxt.start() - (end + len(TB_END))] if nxt else after
        i = nxt.start() if nxt else n
        yield session, between


def extract(scenario_dir):
    out = []
    seen = set()
    speakers = {}
    files = sorted(glob.glob(os.path.join(scenario_dir, '*.ks')))
    for fn in files:
        b = open(fn, 'rb').read()
        if b[:3] == b'\xef\xbb\xbf':
            t = b.decode('utf-8-sig')
        else:
            try:
                t = b.decode('utf-8')
            except UnicodeDecodeError:
                t = b.decode('cp932', 'replace')
        for session, between in iter_blocks(t):
            # speaker name (first '#<name>' line in session)
            for ln in session.split('\n'):
                st = ln.strip()
                if st.startswith('#') and len(st) > 1:
                    nm = st[1:].strip()
                    if nm:
                        speakers[nm] = speakers.get(nm, 0) + 1
                    break
            boxes = pages_of_session(session)
            emit_boxes(boxes, out, seen)
            # choices: glink inside session (rare) + glink between blocks
            for region in (session, between):
                for gm in GLINK_RE.finditer(region):
                    tm = re.search(r'text="([^"]*)"', gm.group(0))
                    if tm:
                        txt = tm.group(1).strip()
                        if txt and txt not in seen:
                            seen.add(txt)
                            out.append(txt)
    return out, speakers


if __name__ == '__main__':
    scenario_dir = sys.argv[1] if len(sys.argv) > 1 else 'ks/data/scenario'
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    lines, speakers = extract(scenario_dir)
    if dst:
        with open(dst, 'wb') as f:
            f.write(b'\xef\xbb\xbf' + '\n'.join(lines).encode('utf-8') + b'\n')
        print('wrote', len(lines), 'lines ->', dst)
    else:
        for ln in lines:
            print(ln)
    print('--- top speakers ---')
    for nm, c in sorted(speakers.items(), key=lambda x: -x[1])[:12]:
        print('  %s : %d' % (nm, c))
