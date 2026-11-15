# -*- coding: utf-8 -*-
"""[JP] ディストピアの王 (Daisy2 / DDP3) text extractor.

Same engine family as 三国恋戦記 魁 (see scripts/sgs_kai_ddp.py) -- container,
LZSS and key derivation are reused verbatim.

Container  Data/kod_text.dat = DDP3
    "DDP3" | u32@4 = 0x20 | u32@8 = data area offset (0x14CB)
    entry records live in [0x120, data_off); each block starts with the inner
    magic "DDWuHXB" preceded by 2 bytes; block name is a UTF-16LE record.
    93 entries, 92 named.

Block    = 16 B inner header + payload
           payload = DWORDS XOR make_key(outsize)
           (inner block is LZSS-compressed first when stored != 0)

Plaintext commands (L0):
    03 0d 36 ff 01 80 <UTF-16LE string> 00 00   -> STORY MESSAGE (one click == one box)
    03 0d 32 ff 02 0d 0c ff 01 80 <str> 00 00   -> CHOICE ITEM
    03 0d 37 ff 02 xx ff 01 80 <str>            -> sprite/expression resource name (NOT text)
    03 0d 35 ff 02 xx ff 01 80 <str>            -> background / UI resource name (NOT text)

String layout inside a STORY MESSAGE:
    "名字\\n台词"      (13,938 msgs)  -> name lives in its own name window -> strip
    "\\n旁白"           (15,338 msgs)  -> no speaker
    any further \\n     -> in-box soft wrap -> merge (never split)

The name window is independent: every named message puts the name before the
first literal \\n and every nameless one starts with that \\n, i.e. the field is
a fixed slot, not inline narration. So names are dropped, matching the
handling of the same engine's previous title.

Order: block names encode the route (main_sec<n> / rt_<char>_ch<n>_sec<m> /
rt_<char>_chend_<kind> / subroutine). Cross-block jump references are only
~10 edges over 92 blocks, NOT enough to build a graph -> order comes from the
name encoding (L1: record self-delimiting + name-encoded sequence).
"""
import sys, os, re, struct, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import sgs_kai_ddp as K

SRC = os.path.join(VNTRANS_HOME, '_work_dystopia/Data/kod_text.dat')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP] ディストピアの王.txt')

MSG = b'\x03\x0d\x36\xff\x01\x80'
CHOICE = b'\x03\x0d\x32\xff\x02\x0d\x0c\xff\x01\x80'
SEP = '\\n'                      # literal backslash + n inside the string
CHAR_ORDER = {'hanza': 1, 'anji': 2, 'rikyou': 3, 'suimei': 4, 'kiriku': 5}


def read_utf16z(data, p):
    buf = bytearray()
    q = p
    while q + 1 < len(data) and not (data[q] == 0 and data[q+1] == 0):
        buf += data[q:q+2]
        q += 2
    return buf.decode('utf-16le', 'replace'), q + 2


def order_key(name):
    m = re.match(r'^main_sec(\d+)$', name)
    if m:
        return (0, 0, int(m.group(1)), name)
    m = re.match(r'^rt_(\w+?)_ch(\d+)_sec(\d+)([a-z]?)$', name)
    if m:
        c = CHAR_ORDER.get(m.group(1), 9)
        return (1, c, int(m.group(2)) * 1000 + int(m.group(3)), name)
    m = re.match(r'^rt_(\w+?)_chend_(\w+)$', name)
    if m:
        c = CHAR_ORDER.get(m.group(1), 9)
        return (1, c, 999999, name)      # endings at the end of that route
    if name == 'subroutine':
        return (9, 0, 0, name)
    return (5, 0, 0, name)


RUBY = re.compile(r'\|([^<>|]+)<[^<>]*>')   # |base<kana> -> base  (58 occurrences)


def split_name(s):
    """Split the name-window slot from the text.

    The name slot is the segment before the first literal \\n. Empirically:
      empty                    -> no speaker (string starts with \\n)   15,338
      starts with 「 （ 『      -> NOT a name, it is quoted narration      26
      pure punctuation (？？？) -> unknown-speaker placeholder -> name    233
      short, no ending punct   -> name                                 13,851
      no \\n at all            -> whole string is text                     61
    """
    if SEP not in s:
        return '', s
    first, rest = s.split(SEP, 1)
    if first == '':
        return '', rest
    if first[:1] in '「（『':
        return '', s                      # quoted narration, keep as one text
    if set(first) <= set('？?…・'):        # ？？？ = unknown speaker -> name slot
        return first, rest
    # a real name: short, the NEXT segment opens with a quote, and the name
    # itself does not end with a sentence mark.  The "next segment opens with a
    # quote" clause is essential -- without it the first wrapped line of plain
    # narration gets eaten (that exact mistake cost 20k lines on the earlier
    # title of this engine).
    if len(first) <= 12 and rest[:1] in '「（『' and first[-1:] not in '、。！？…':
        return first, rest
    return '', s                          # fall back: treat whole string as text


def clean_msg(s):
    """strip ruby markup, the name window slot, and merge in-box soft wraps."""
    s = s.replace('\u8001', '')          # 01 80 read as U+8001 -- control byte residue
    s = RUBY.sub(r'\1', s)               # ruby: keep the base text, drop the kana
    name, s = split_name(s)
    s = re.sub(r'\\s\[[^\]]*\]', '', s)    # voice/SE marker
    s = re.sub(r'\\[a-zA-Z]{1,3}\[[^\]]*\]', '', s)
    s = s.replace(SEP, '')                 # remaining soft wraps
    s = s.replace('\u3000', ' ').strip()
    return s


def main():
    d, entries, typ = K.parse_ddp(SRC)
    if typ != 'DDP3':
        raise SystemExit('expected DDP3, got %s' % typ)
    named = [e for e in entries if e[0] and e[2] is not None]
    named.sort(key=lambda e: order_key(e[0]))

    lines = []
    stat = collections.Counter()
    for nm, off, osz, st in named:
        plain, _ = K.get_block(d, off, osz, st)
        # walk the command stream in offset order so dialogue and choices interleave
        pos = 0
        events = []
        for m in re.finditer(re.escape(MSG), plain):
            events.append((m.start(), 'msg', len(MSG)))
        for m in re.finditer(re.escape(CHOICE), plain):
            events.append((m.start(), 'choice', len(CHOICE)))
        events.sort()
        for start, kind, plen in events:
            s, _ = read_utf16z(plain, start + plen)
            c = clean_msg(s)
            if not c:
                continue
            lines.append(c)
            stat[kind] += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('blocks used:', len(named))
    print('story lines: %d   choices: %d   total: %d' % (stat['msg'], stat['choice'], len(lines)))
    print('bytes:', os.path.getsize(OUT))
    for t in lines[:5]:
        print('  |', t[:62])
    print('  ...')
    for t in lines[-5:]:
        print('  |', t[:62])


if __name__ == '__main__':
    main()
