# -*- coding: utf-8 -*-
"""[Loose Lips series] RPG Maker MV text extractor (Enigma-boxed single exe).

The game ships as ONE exe (`Game_boxed.exe` = Enigma Virtual Box wrapping NW.js).
evbunpack reports a corrupted filetable, but the MV data files are stored as
PLAIN UTF-8 JSON inside the exe, so we locate them by structure instead:

  * candidate start = '[' followed by '\\n' | 'n' | '{'  ,  '{' followed by '"' | '\\n'
  * json_end() balances [ ] { } while skipping string literals -> exact end offset
  * json.loads() doubles as the validator
  * keep only outermost spans (nested dicts parse fine on their own, so drop them)

Document kinds are recognised by content:
  dict with 'events'            -> MAP
  dict with 'switches'          -> System
  list whose [1] has 'nickname' -> Actors
  list whose [1] has 'list'     -> CommonEvents

Line rule (L0, RPG Maker MV semantics):
  101 (Show Text) starts a box, the following 1..N 401 (Show Text line) are its
  rows -> ONE click == ONE box == ONE output line (rows joined).
  Verified on LL1: 780 boxes, every 101 is followed by >=1 401 (0 exceptions),
  every 401 is preceded by 101 or 401 (0 exceptions), 401 total 1837 == 780+1057.

Name slot:
  In LL1 every speaker name occupies the FIRST 401 row of the box and is always
  the runtime variable macro \\V[20] (System.variables[20] is literally named
  "文章内変数置き換え" = in-text variable substitution). It cannot be resolved
  statically, so the row is dropped (same effect as an independent name window).
  --keep-name-slot keeps it verbatim instead.

Choice (L0): 102 (Show Choices). parameters[0] = option texts.
  402 (When [n]) branches start after it. Menu-only choice groups are dropped:
  a group is KEPT only when its option list has no UI markup
  (\\I[n] icon, \\N[4] the author's "back" button, or a plugin expression like en(...)).
  That is a structural rule, not a text filter.

Control codes stripped: \\C[n] colour, \\I[n] icon, \\CL, \\> \\< \\| \\! \\. \\{ \\}
  \\N[n] is RESOLVED to the Actors[n] name (decodable), \\V[n] is left as-is if it
  survives into the text (only 2 hits, both in phone-book UI text outside story).
"""
import json, os, re, sys, collections

# note: \\RL (and friends) are plugin inline codes that carry alignment;
# the text AFTER them is real on-screen text, so only the code is dropped.
CTRL = re.compile(r'\\[Cc]\[\d+\]|\\[Ii]\[\d+\]|\\CL|\\R[A-Za-z]?|\\[><|!.^]|\\[{}]|\\\$')
VAR = re.compile(r'\\[Vv]\[(\d+)\]')
C0 = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
ACTOR = re.compile(r'\\N\[(\d+)\]')
NAME_SLOT = re.compile(r'^[\s\u3000]*\\[Vv]\[\d+\][\s\u3000]*$')
INLINE_NAME = re.compile(r'^[\s\u3000]*\\[Vv]\[\d+\]')
SYS_LINE = re.compile(r'^\s*(?:☒|クレジット)|(?:BGM|SE)\s*[:：]|https?://|dova-s\.jp|ondoku3\.com|\\item\[')


def json_end(buf, p):
    """Byte offset just past the JSON value starting at buf[p] (string-aware)."""
    depth = 0; instr = False; esc = False; i = p; n = len(buf)
    while i < n:
        c = buf[i]
        if instr:
            if esc: esc = False
            elif c == 0x5c: esc = True
            elif c == 0x22: instr = False
        else:
            if c == 0x22: instr = True
            elif c in (0x5b, 0x7b): depth += 1
            elif c in (0x5d, 0x7d):
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    return None


def load_docs(exe_path, lo, hi):
    d = open(exe_path, 'rb').read()
    starts = [lo + m.start() for m in re.finditer(rb'\[(?=[\n{n])|\{(?=["\n])', d[lo:hi])]
    raw = []
    for p in starts:
        e = json_end(d, p)
        if e is None or e - p < 128:
            continue
        try:
            obj = json.loads(d[p:e].decode('utf-8', 'surrogateescape'))
        except ValueError:
            continue
        raw.append((p, e, obj))
    raw.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    docs = []
    last = -1
    for p, e, o in raw:
        if p < last:
            continue
        docs.append((p, e, o)); last = e
    return docs


def classify(o):
    if isinstance(o, dict):
        if 'events' in o:
            return 'map'
        if 'switches' in o and 'variables' in o:
            return 'system'
        return 'dict'
    if isinstance(o, list) and len(o) > 1 and isinstance(o[1], dict):
        k = set(o[1])
        if 'nickname' in k:
            return 'actors'
        if 'list' in k:
            return 'common'
    return 'other'


def bag_lists(doc, kind):
    """Yield command lists in document order."""
    if kind == 'map':
        for ev in (doc.get('events') or []):
            if not ev:
                continue
            for pg in (ev.get('pages') or []):
                yield pg.get('list') or []
    elif kind == 'common':
        for ev in doc[1:]:
            if isinstance(ev, dict) and 'list' in ev:
                yield ev['list'] or []


CREDITS = re.compile(r'^\s*#')


def clean(t, actors):
    t = ACTOR.sub(lambda m: actors.get(int(m.group(1)), m.group(0)), t)
    t = CTRL.sub('', t)
    # \V[n] = runtime game variable; unresolvable statically -> mark, never guess
    t = VAR.sub('〔未解析〕', t)
    t = C0.sub('', t)          # stray inline control bytes (U+0001 seen in LL3)
    return t.strip(' \u3000')


def extract_game(exe, lo, hi, keep_name_slot=False):
    docs = load_docs(exe, lo, hi)
    kinded = [(classify(o), p, e, o) for p, e, o in docs]
    actors = {}
    for k, p, e, o in kinded:
        if k == 'actors':
            for a in o[1:]:
                if isinstance(a, dict) and a.get('name'):
                    actors[a.get('id')] = a['name']
            break

    lines = []
    stat = collections.Counter()
    for k, p, e, o in kinded:
        if k not in ('map', 'common'):
            continue
        for lst in bag_lists(o, k):
            has_text = any(c.get('code') == 401 for c in lst)
            i = 0
            n = len(lst)
            while i < n:
                code = lst[i].get('code')
                if code == 101:
                    j = i + 1
                    rows = []
                    while j < n and lst[j].get('code') == 401:
                        rows.append((lst[j].get('parameters') or [''])[0]); j += 1
                    if rows:
                        body = rows
                        if NAME_SLOT.match(rows[0] or ''):
                            stat['name_slot'] += 1
                            body = rows if keep_name_slot else rows[1:]
                        elif not keep_name_slot:
                            m = INLINE_NAME.match(rows[0] or '')
                            if m:
                                stat['name_slot'] += 1
                                body = [rows[0][m.end():]] + rows[1:]
                        s = ''.join(clean(r, actors) for r in body)
                        s = s.strip(' \u3000')
                        if s.startswith('〔未解析〕'):
                            # name var wrapped in control codes (e.g. \>\}\C[2]\v[n]\C[0]\{):
                            # after clean it leads the line -> strip as the name label
                            s = s[len('〔未解析〕'):].lstrip(' \u3000')
                            stat['name_slot'] += 1
                        if s and CREDITS.match(s):
                            # staff-roll marker lines ('#Director...'): production
                            # credits, not script text. Dropped so the '#' ledger
                            # rule and the allow file (both '#'-commented) stay clean.
                            stat['credits_skipped'] += 1
                        elif s and SYS_LINE.match(s):
                            # system UI lines (close button ☒ / credits block / \item[..] residue)
                            stat['credits_skipped'] += 1
                        elif s:
                            lines.append(s)
                            stat['line'] += 1
                        else:
                            stat['empty'] += 1
                    i = j
                    continue
                if code == 102:
                    pr = lst[i].get('parameters') or []
                    choices = [c for c in (pr[0] or []) if isinstance(c, str)]
                    ui = any(('\\I[' in c) or ('\\N[' in c) or ('en(' in c) or ('s[' in c) for c in choices)
                    if has_text and not ui:
                        for c in choices:
                            s = clean(c, actors)
                            if s and not s.lstrip().startswith('☒') and s.strip() != '〔未解析〕':
                                lines.append(s)
                                stat['choice'] += 1
                    else:
                        stat['menu_choice_skipped'] += len(choices)
                    i += 1
                    continue
                i += 1
    return lines, stat, actors, kinded


def auto_range(exe_path):
    """Narrow the scan window to the plaintext MV data area.

    The data block is bracketed by '"list":[' occurrences (CommonEvents is
    usually the first, map events follow).  1 MB of slack before the first and
    256 KB after the last covers the smaller database files that sit around.
    """
    d = open(exe_path, 'rb').read()
    pos = [m.start() for m in re.finditer(re.escape(b'"list":['), d)]
    if not pos:
        raise SystemExit('no MV data found in %s' % exe_path)
    lo = max(0, pos[0] - 0x100000)
    hi = min(len(d), pos[-1] + 0x40000)
    return lo, hi


def main():
    if len(sys.argv) < 3:
        print('usage: looselips_extract.py <exe> <out.txt> [--keep-name-slot] [lo_hex hi_hex]')
        return
    exe, out = sys.argv[1], sys.argv[2]
    args = [a for a in sys.argv[3:] if not a.startswith('--')]
    if len(args) >= 2:
        lo, hi = int(args[0], 16), int(args[1], 16)
    else:
        lo, hi = auto_range(exe)
        print('auto range: %#x - %#x (%.1f MB)' % (lo, hi, (hi - lo) / 1048576.0))
    keep = '--keep-name-slot' in sys.argv
    lines, stat, actors, kinded = extract_game(exe, lo, hi, keep)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('docs:', len(kinded), collections.Counter(k for k, *_ in kinded))
    print('actors:', len(actors), list(actors.items())[:4])
    print('lines: %d  choices: %d  skipped menu options: %d  empty boxes: %d'
          % (stat['line'], stat['choice'], stat['menu_choice_skipped'], stat['empty']))
    print('name slots dropped:', stat['name_slot'])
    print('bytes:', os.path.getsize(out))
    for t in lines[:4]:
        print('  |', t[:60])


if __name__ == '__main__':
    main()
