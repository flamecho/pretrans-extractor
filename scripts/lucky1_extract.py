# -*- coding: utf-8 -*-
"""[JP]ラッキードッグ１ (PC / Will-ARCG + Kagura TLV bytecode) text extractor.

Container  LD1.scb = ARCG archive
    header : 'ARCG' u16 u16 u32 dir_off u32 aux u16 groups u32 count
    dir    : [u32 ?][u32 table_off][u32 count][u32 pad]
    entry  : [u8 L][name L-1 bytes ascii + NUL pad][u32 off][u32 size]
    dir/entries are monotone; sum(size) closes on the data region.

Bytecode  TLV: [u8 len][u8 op][len-2 operand]
    0x25  open text box, operand = "<speaker>\0<faceid>"   (empty => narration)
    0x09  one display row, operand = cp932 text + NUL
    0x0a  close box (wait for click)
    0x24  choice item: [4B][text\0][target\0]"選択パネル"
    0x26  block caption (authoring title, not rendered in the text box)
    0x21  jump  (!@call / @label)
    0x2e  condition, 0x52 set-var, 0x3a label, 0x40 return

Line rule (L0): one click == commands 0x25..0x0a.  Every 0x09 inside belongs to
the SAME box (soft-wrapped rows) and is merged into one output line.
Verified on the whole archive: 42,531 x 0x09 all fall inside a 0x25..0x0a pair,
0 exceptions.

Reading order: DFS over the jump/choice graph starting at NewGame (the only
block with no incoming edge), then any leftovers in directory order.
"""
import struct, sys, os, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SCB = os.path.join(VNTRANS_HOME, '_work_lucky1/setup/LD1.scb')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]ラッキードッグ１.txt')

SYS_BLOCKS = {
    'FlgTbl', 'RegTbl', 'ScoreView', 'Choices', 'Return', 'Tomorrow',
    'RootFix', 'LoveComparison', 'CheckValue', '__GameOver',
}

d = open(SCB, 'rb').read()
hdr = struct.unpack_from('<4sHHIIHI', d, 0)
dir_off, count = hdr[3], hdr[6]
table_off = struct.unpack_from('<I', d, dir_off + 4)[0]

def read_dir():
    p = table_off
    out = []
    for _ in range(count):
        L = d[p]
        name = d[p+1:p+L].split(b'\x00')[0].decode('ascii', 'replace')
        off, size = struct.unpack_from('<II', d, p + L)
        out.append((name, off, size))
        p += L + 8
    return out

def walk(s, e):
    p = s
    while p < e:
        L = d[p]
        if L < 2 or p + L > e:
            return
        yield (p, L, d[p+1], d[p+2:p+L])
        p += L

def cp932(b):
    try:
        return b.decode('cp932')
    except UnicodeDecodeError:
        return None

def block_events(off, size):
    """Yield ('line'|'choice', text) in script order."""
    rows = None
    for p, L, op, arg in walk(off, off + size):
        if op == 0x25:
            rows = []
        elif op == 0x09 and rows is not None:
            t = cp932(arg[:-1]) if arg[-1:] == b'\x00' else cp932(arg)
            if t:
                rows.append(t)
        elif op == 0x0a and rows is not None:
            s = ''
            for i, r in enumerate(rows):
                if i and r.startswith('\u3000'):
                    r = r[1:]
                s += r
            s = s.strip(' \u3000')
            if s:
                yield ('line', s)
            rows = None
        elif op == 0x24:
            parts = [x for x in arg.split(b'\x00') if x]
            strs = [cp932(x) for x in parts]
            if strs and strs[-1] == '選択パネル' and len(strs) >= 2 and strs[0]:
                yield ('choice', strs[0])

def ordered_events(recs):
    """Walk the script in execution order, interleaving text with control flow.

    op 0x21 transfers control ('!@name' = call, '@name' = jump) and is expanded
    in place the first time it is reached, so text follows the real reading
    order instead of being grouped per block.
    """
    names = set(recs)
    seen = set()
    out = []

    def emit(name):
        if name in seen or name not in names:
            return
        seen.add(name)
        off, size = recs[name]
        rows = None
        for p, L, op, arg in walk(off, off + size):
            if op == 0x25:
                rows = []
            elif op == 0x09 and rows is not None:
                t = cp932(arg[:-1]) if arg[-1:] == b'\x00' else cp932(arg)
                if t:
                    rows.append(t)
            elif op == 0x0a and rows is not None:
                s = ''
                for i, r in enumerate(rows):
                    if i and r.startswith('\u3000'):
                        r = r[1:]
                    s += r
                s = s.strip(' \u3000')
                if s:
                    out.append((name, 'line', s))
                rows = None
            elif op == 0x24:
                parts = [x for x in arg.split(b'\x00') if x]
                strs = [cp932(x) for x in parts]
                if strs and strs[-1] == '選択パネル' and len(strs) >= 2 and strs[0]:
                    out.append((name, 'choice', strs[0]))
            elif op == 0x21:
                t = cp932(arg.rstrip(b'\x00'))
                if t:
                    emit(t.lstrip('!@'))
        if rows:
            s = ''
            for i, r in enumerate(rows):
                if i and r.startswith('\u3000'):
                    r = r[1:]
                s += r
            s = s.strip(' \u3000')
            if s:
                out.append((name, 'line', s))

    emit('NewGame')
    for k in sorted(names, key=lambda x: recs[x][0]):
        emit(k)
    return out

def main():
    entries = read_dir()
    recs = {n: (o, s) for n, o, s in entries}
    events = ordered_events(recs)
    lines, stat = [], collections.Counter()
    for name, kind, t in events:
        if name in SYS_BLOCKS:
            continue
        lines.append(t)
        stat[kind] += 1
    stat['blocks'] = len({n for n, _, _ in events if n not in SYS_BLOCKS})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('blocks visited:', stat['blocks'])
    print('lines:', stat['line'], 'choices:', stat['choice'], 'total:', len(lines))
    print('out bytes:', os.path.getsize(OUT))
    for t in lines[:4]:
        print('  |', t[:44])
    print('  ...')
    for t in lines[-4:]:
        print('  |', t[:44])

if __name__ == '__main__':
    main()
