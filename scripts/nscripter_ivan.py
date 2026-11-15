#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NScripter script text extractor — [JP]イワンは見た! (WILD ROSE doujin ADV)
============================================================================
Engine : NScripter  (ivan.exe + nscript.dat)
Decode : nscript.dat is a bytewise XOR 0x84 of a cp932 text script.

TEXT MODEL (L0 — EMPIRICALLY VERIFIED on this title, 2026-11-08; do NOT
blindly reuse nscripter_dat.py from other titles):

  * Free-text mode: any line that is NOT a command / label / comment is
    DISPLAYED. There is exactly ONE text window (*custom → *text_cw_next does
    only `print 1`; no `name` command, no second setwindow) ⇒ speaker names
    are 正文内名札, KEPT and joined inline:  【虎徹】「……」  (skill S6-lines-names:
    NScripter 実測 41 作 全部保留).
  * Page break = the backslash `\\`. `\\` may be TRAILING, STANDALONE, or
    MID-LINE (e.g. `…気持ちいい。\\後ろに当たる…\\` = two pages on one line).
    We therefore ACCUMULATE display text in a buffer and FLUSH on every `\\`
    (one flushed buffer = one click = one output line). `@`(line-wait) = 0.
  * Display strings:  地の文 `……思った。\\` / 台詞 `「…」\\` (opens with 「) /
    名札 `【虎徹】` (no `\\`; sits in the same buffer as the following 「…」).
  * Choices: `csel` blocks; each choice is  "<text>",*label,  (last has no
    comma). The author's uniform bullet `・` is stripped (skill S6-lines-options).
    Options emitted ONE PER LINE, IN PLACE (剧情顺序).
  * `mov $127,"…"` and friends are command assignments (save-menu caption /
    system UI) → excluded (skill: 不收 系统 UI).
  * No 鏡文字 / 扉文 / 歌詞 / 用語辞典 in this title (verified) → none extracted.

VERSIONING: `@`=0 ⇒ no page has ≥2 clicks ⇒ 双版 N/A → single version only.
OUTPUT: UTF-8 BOM, LF, one line per click, names joined inline.
"""
import sys, re

XOR = 0x84
NAME_RE = re.compile(r'^【(.+?)】$')
CMD_FIRST = re.compile(r'^[A-Za-z@!]')     # NScripter commands head with ASCII letter/@/!
OPTION_BULLET = '・'


def decode_script(path):
    data = open(path, 'rb').read()
    raw = bytes(b ^ XOR for b in data)
    # split on raw bytes BEFORE cp932 decode: a bare `\\` immediately before
    # `\\n` would otherwise merge into a valid 2-byte char and eat the newline.
    return [ln.decode('cp932') for ln in raw.split(b'\n')]


def extract(lines):
    out = []
    carry = []                       # text fragments for the current page
    in_choice = False
    stats = {'pages': 0, 'options': 0, 'names_joined': 0}

    def flush():
        if carry:
            line = ''.join(carry)
            out.append(line)
            stats['pages'] += 1
            if line.startswith('【'):
                stats['names_joined'] += 1
        carry.clear()

    for rawln in lines:
        st = rawln.strip()
        if not st:
            continue
        if st.startswith('*') or st.startswith(';'):        # label / comment
            continue
        # ---- choice block ----
        if st == 'csel' or st.startswith('csel '):
            flush()                                            # page before the menu
            in_choice = True
            continue
        if in_choice:
            if st.startswith('"'):
                i = st.find('"'); j = st.rfind('"')
                if i >= 0 and j > i:
                    txt = st[i + 1:j].lstrip(OPTION_BULLET)   # strip uniform bullet
                    out.append(txt)
                    stats['options'] += 1
                continue
            else:                                            # terminator line
                in_choice = False
                continue
        # ---- command line (NScripter commands head with ASCII letter/@/!) ----
        if CMD_FIRST.match(st):
            continue
        # ---- display string: accumulate, flush on every backslash ----
        parts = st.split('\\')
        for k, part in enumerate(parts):
            if k > 0:
                flush()                                       # the preceding `\` is a page break
            if part:
                carry.append(part)
        # (last segment, if line did not end with `\`, stays pending in carry)
    flush()                                                   # flush any trailing buffer
    return out, stats


def selfcheck(out):
    bad_q = sum(1 for x in out if x.count('「') != x.count('」'))
    ffd = sum(1 for x in out if '�' in x)
    ctrl = sum(1 for x in out if any((ord(c) < 32 and c != '\t') for c in x))
    return bad_q, ffd, ctrl


def main():
    src = sys.argv[1]
    outp = sys.argv[2] if len(sys.argv) > 2 else None
    lines = decode_script(src)
    out, stats = extract(lines)
    text = '\n'.join(out)
    if outp:
        with open(outp, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write(text)
            if text and not text.endswith('\n'):
                f.write('\n')
        print('wrote', outp)
    print('STATS:', stats, '| total lines:', len(out))
    bad_q, ffd, ctrl = selfcheck(out)
    print('selfcheck: unbalanced「」=%d  U+FFFD=%d  control=%d' % (bad_q, ffd, ctrl))


if __name__ == '__main__':
    main()
