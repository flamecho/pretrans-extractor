# -*- coding: utf-8 -*-
"""[JP]Spring Flower (FUSYRO / KiriKiri2 KAG3) -> one line per on-screen message box.

Usage:
  python scripts/springflower_extract.py <data.xp3 | act000.ks> [out.txt]

L0 framing proof (scenario/fusyro_macro.ks + KAG3 built-ins):
  [SCN] = [delay][cm] ... [current layer=message1]   (scene/box start, clears message)
  [p]   = wait click + clear page (box boundary)
  [l]   = wait click, no clear (box boundary; only at choice lead-ins)
  [r]/[HNR] = in-box line break (merged into the same line)
  [N彬]/[N英知] write full-width-space+name into the CURRENT message1 layer
  (history output=false only hides from backlog) => in-box name plate => keep inline.
  Choices: message2 [nowait] block, one [locate x= y=]text per option.
"""
import re, os, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VNTRANS_HOME, "_work_springflower/[JP]Spring Flower/data.xp3")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, "提取结果/[JP]Spring Flower.txt")

if src.lower().endswith('.xp3'):
    from xp3 import XP3
    x = XP3(src)
    s = x.read('scenario/act000.ks').decode('cp932')
else:
    s = open(src, 'rb').read().decode('cp932')
s = s.replace('\r\n', '\n')
lines = s.split('\n')

TAG = re.compile(r'\[([^\]]*)\]')
NAMES = {
    'n彬': '\u3000本間 彬',
    'n英知': '\u3000佐古田 英知',
    'n・・・': '\u3000？？？',
}

boxes = []
buf = []
buf_start = None
cur_names = []
meta = collections.Counter()

def flush(kind, ln):
    global buf, buf_start, cur_names
    text = ''.join(buf).strip('\n').replace('\n', '')
    if text.strip() != '':
        boxes.append({'text': text, 'kind': kind, 'start': buf_start, 'end': ln,
                      'names': list(cur_names)})
    buf = []
    cur_names = []
    buf_start = ln

in_choice = False
for idx, raw in enumerate(lines):
    ln = idx + 1
    st = raw.lstrip()
    if st.startswith(';') or st.startswith('*'):
        continue
    toks = []
    pos = 0
    while True:
        m = TAG.search(raw, pos)
        if not m:
            if pos < len(raw):
                toks.append(('t', raw[pos:]))
            break
        if m.start() > pos:
            toks.append(('t', raw[pos:m.start()]))
        toks.append(('g', m.group(1)))
        pos = m.end()
        if pos >= len(raw):
            break
    for kind, tok in toks:
        if kind == 't':
            if tok == '' or in_choice:
                continue
            if buf_start is None:
                buf_start = ln
            buf.append(tok)
            continue
        tg = tok.strip()
        head = tg.split('=', 1)[0].split(None, 1)[0].lower()
        if head in ('scn', 'cm'):
            flush('clear', ln)
            buf_start = ln
            meta[head] += 1
        elif head in ('p', 'l'):
            flush(head, ln)
            buf_start = ln
            meta['term_' + head] += 1
        elif head == 'r':
            if buf_start is None:
                buf_start = ln
            buf.append('\n')
        elif head == 'hnr':
            if buf_start is None:
                buf_start = ln
            buf.append('\n')
        elif head == 'hnrs':
            if buf_start is None:
                buf_start = ln
            buf.append('\n\u3000')
        elif head in ('rtn', 'hnrtn', 'hnrtns'):
            flush('l', ln)
            buf_start = ln
            buf.append('\n' if head != 'hnrtns' else '\n\u3000')
            meta['term_l'] += 1
        elif head in NAMES:
            if buf_start is None:
                buf_start = ln
            buf.append(NAMES[head])
            buf.append('\n')
            cur_names.append(NAMES[head].strip())
            meta['name'] += 1
        elif head == 'nowait':
            in_choice = True
        elif head == 'endnowait':
            in_choice = False
        # all other tags carry no display text
    if buf_start is not None and not in_choice:
        buf.append('\n')
flush('eof', len(lines))

# choice blocks (message2 [nowait] ... [endnowait], [locate]text lines)
choice_blocks = []
cur = None
for idx, raw in enumerate(lines):
    ln = idx + 1
    if raw.lstrip().startswith(';'):
        continue
    if '[nowait]' in raw:
        cur = {'line': ln, 'items': []}
    if cur is not None:
        m = re.search(r'\[locate[^\]]*\]\s*(.+)$', raw)
        if m and not re.match(r'\s*\[button', m.group(1)):
            t = TAG.sub('', m.group(1)).strip()
            if t:
                cur['items'].append(t)
    if '[endnowait]' in raw and cur is not None:
        choice_blocks.append(cur)
        cur = None

# insert each choice block after the box whose terminator precedes it
ins = collections.defaultdict(list)
for cb in choice_blocks:
    k = -1
    for i, b in enumerate(boxes):
        if b['end'] is not None and b['end'] < cb['line']:
            k = i
    ins[k].extend(cb['items'])
final = []
for i, b in enumerate(boxes):
    final.append(b['text'])
    final.extend(ins.get(i, []))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
    f.write('\n'.join(final) + '\n')
print('boxes', len(boxes), 'options', sum(len(c['items']) for c in choice_blocks),
      'lines', len(final), 'bytes', os.path.getsize(OUT))
print('meta', dict(meta))
