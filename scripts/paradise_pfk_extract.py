# -*- coding: utf-8 -*-
"""[JP] Paradise 極-KIWAME- (Daisy2 / DDP3) text extractor.

Same engine family as 三国恋戦記 魁 (sgs_*) and ディストピアの王 (kod_*) -- the
container (DDP3), custom LZSS and DWORD-XOR key derivation in scripts/sgs_kai_ddp.py
are reused verbatim. Script command set is identical (03 0d 36 = message,
03 0d 32 = choice, strings are UTF-16LE + 00 00).

Per-game differences vs the family (verified on this title, 2026-11-06):
  * U+8001 ('老') is a REAL kanji here (老人/老衰/老公), NOT the 01 80 control-byte
    residue seen on ディストピアの王.  DO NOT strip it.
  * No voice/SE markers (\\s[...]) at all -> marker regexes are no-ops.
  * Route block names come in three ending spellings:  ch<N>_sec<M>  /  ch<N>end_<kind>
    /  ch<N>_end_<kind>  /  chend_<kind>  (4p uses ch1_end; aduma uses chend).
  * Protagonist is unnamed, first-person '俺'; the 7 targets (アヅマ/タカラ/マツダ/
    ミツギ/シマダ/ホンゴウ/ナンジョウ) appear in independent name windows -> stripped.

Order: main_sec<N> first, then routes by container offset order (approximate,
name-encoded; the true entry order is an exe branch table per family behaviour),
then subroutine.  Route order is NOT authoritative.
"""
import sys, os, re, struct, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import sgs_kai_ddp as K

SRC = os.path.join(VNTRANS_HOME, '_work_paradise/extracted/pfk_text.dat')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]Paradise 極-KIWAME-.txt')

MSG = b'\x03\x0d\x36\xff\x01\x80'
CHOICE = b'\x03\x0d\x32\xff\x02\x0d\x0c\xff\x01\x80'
SEP = '\\n'                      # literal backslash + n (in-box soft wrap)
# container-offset order (approximate route order; see module docstring)
CHAR_ORDER = {'matsuda': 1, 'mitsugi': 2, 'takara': 3, 'hongou': 4,
              'shimada': 5, 'nanjo': 6, 'aduma': 7, '4p': 8}
RUBY = re.compile(r'\|([^<>|]+)<[^<>]*>')   # |base<kana> -> base


def read_utf16z(data, p):
    buf = bytearray(); q = p
    while q + 1 < len(data) and not (data[q] == 0 and data[q + 1] == 0):
        buf += data[q:q + 2]; q += 2
    return buf.decode('utf-16le', 'replace'), q + 2


def order_key(name):
    m = re.match(r'^main_sec(\d+)$', name)
    if m:
        return (0, 0, int(m.group(1)), name)
    m = re.match(r'^rt_(\w+?)_ch(\d+)_sec(\d+)([a-z]?)$', name)
    if m:
        c = CHAR_ORDER.get(m.group(1), 9)
        return (1, c, int(m.group(2)) * 1000 + int(m.group(3)), name)
    m = re.match(r'^rt_(\w+?)_ch(\d+)end_(\w+)$', name)        # chNend_kind
    if m:
        c = CHAR_ORDER.get(m.group(1), 9)
        return (1, c, int(m.group(2)) * 1000 + 995, name)
    m = re.match(r'^rt_(\w+?)_ch(\d+)_end_(\w+)$', name)       # chN_end_kind (4p)
    if m:
        c = CHAR_ORDER.get(m.group(1), 9)
        return (1, c, int(m.group(2)) * 1000 + 995, name)
    m = re.match(r'^rt_(\w+?)_chend_(\w+)$', name)             # chend_kind (aduma)
    if m:
        c = CHAR_ORDER.get(m.group(1), 9)
        return (1, c, 999 * 1000 + 995, name)
    if name == 'subroutine':
        return (9, 0, 0, name)
    return (5, 0, 0, name)


def split_name(s):
    """Name-slot (independent name window) lives before the first literal \\n.

    * empty first segment        -> no speaker (narration)        14,066
    * opens with 「（『          -> quoted narration, keep whole     (few)
    * pure punctuation (？？？)  -> unknown-speaker placeholder     131
    * short, next seg opens w/ 「（『, name does not end w/ punct -> name
    * no \\n                     -> whole string is text
    """
    if SEP not in s:
        return '', s
    first, rest = s.split(SEP, 1)
    if first == '':
        return '', rest
    if first[:1] in '「（『':
        return '', s
    if set(first) <= set('？?…・'):
        return first, rest
    if len(first) <= 12 and rest[:1] in '「（『' and first[-1:] not in '、。！？…':
        return first, rest
    return '', s


def clean_msg(s):
    s = RUBY.sub(r'\1', s)               # ruby: keep base, drop kana
    name, s = split_name(s)
    s = s.replace(SEP, '')               # remaining in-box soft wraps -> merge
    s = s.replace('\u3000', ' ').strip()
    return s


def main():
    d, entries, typ = K.parse_ddp(SRC)
    if typ != 'DDP3':
        raise SystemExit('expected DDP3, got %s' % typ)
    named = [e for e in entries if e[0] and e[2] is not None]
    named.sort(key=lambda e: order_key(e[0]))

    lines = []; stat = collections.Counter(); names = collections.Counter()
    for nm, off, osz, st in named:
        plain, _ = K.get_block(d, off, osz, st)
        events = []
        for m in re.finditer(re.escape(MSG), plain):
            events.append((m.start(), 'msg', 6))
        for m in re.finditer(re.escape(CHOICE), plain):
            events.append((m.start(), 'choice', 10))
        events.sort()
        for start, kind, plen in events:
            s, _ = read_utf16z(plain, start + plen)
            c = clean_msg(s)
            if not c:
                continue
            lines.append(c)
            stat[kind] += 1
            if kind == 'msg' and SEP in s:
                first = s.split(SEP, 1)[0]
                if first and first[:1] not in '「（『' and not (set(first) <= set('？?…・')) \
                   and len(first) <= 12 and s.split(SEP, 1)[1][:1] in '「（『' \
                   and first[-1:] not in '、。！？…':
                    names[first] += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))

    print('blocks used:', len(named))
    print('story lines: %d   choices: %d   total: %d' % (stat['msg'], stat['choice'], len(lines)))
    print('bytes:', os.path.getsize(OUT))
    print('distinct name-slot speakers:', len(names))
    for t in lines[:4]:
        print('  |', t[:70])
    print('  ...')
    for t in lines[-4:]:
        print('  |', t[:70])


if __name__ == '__main__':
    main()
