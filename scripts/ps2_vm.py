"""VM-level .cnut (Squirrel 'SQIR'/PART container) dialogue extractor for
*Hakarena Heart* (PS2).

Container layout (reverse-engineered 2026-09-29):
  fafa 'RIQS' 01 000000 'TRAP' ... header strings ('DataMake/SCENE/x.nut','main')
  'TRAP' + 7 u32 (nliterals=470, ...) + 'TRAP'
  literal table : entries [10 00 00 08][len:u32][cp932 text]  (len may be 0!)
  ... metadata TRAPs ('this', ...) ...
  'TRAP' code-chunk header (fields include ninstructions) 
  instructions : 8 bytes each = [_arg1:u32][op:u8][a0:u8][a2:u8][a3:u8]
  final 'TRAP' tail marker

VM model (empirically verified):
  op 0x04 DLOAD : r3 = literals[_arg1]; r4 = literals[_arg3]
  op 0x01 LOAD  : r{a0} = literals[_arg1]
  op 0x02 LOADINT: r{a0} = _arg1
  op 0x3c CALL  : execute tag (r3, r4)

Engine tag language:
  ('text', s)      append dialogue text s to the current message box
  ('embex', var)   insert runtime variable (f.name -> 由香里, f.family -> 姫宮)
  ('eol', 'true')  end of message -> flush one output line (one click)
  ('p', ...)       click wait -> flush
  ('r', ...)       line break INSIDE the same message box (join in output)
  ('target', lbl)  branch label; before each select-option text -> flush
  ('name'/'disp'/'dispname'/'voice'/'笑い'/... ) presentation -- ignored
"""
import struct

VAR_NAMES = {'f.name': '由香里', 'f.family': '姫宮'}


def parse_literals(d):
    """Walk the literal table; returns list of cp932 strings."""
    # find the TRAP whose following bytes start a long [10 00 00 08] chain
    traps = []
    i = d.find(b'TRAP')
    while i >= 0:
        traps.append(i)
        i = d.find(b'TRAP', i + 1)
    best = None
    for t in traps:
        p = t + 4
        entries = []
        while p + 8 <= len(d) and d[p:p + 4] == b'\x10\x00\x00\x08':
            L = struct.unpack_from('<I', d, p + 4)[0]
            if L > 8000 or p + 8 + L > len(d):
                break
            entries.append(d[p + 8:p + 8 + L].decode('cp932', errors='replace'))
            p += 8 + L
        if len(entries) >= 3 and (best is None or len(entries) > len(best[1])):
            best = (t, entries, p)
    if best is None:
        raise ValueError('literal table not found')
    return best[1], best[2]


def find_code_start(d, lit_end, nlit):
    """Locate the instruction-stream start.

    The last TRAP (t_end) is the tail marker; some earlier TRAP header field
    holds the instruction count N.  START = t_end - 8*N (phase-invariant:
    any candidate with the same (t_end-START) % 8 decodes identically).
    Candidates are validated by op sanity + DLOAD literal bounds.
    """
    traps = []
    i = d.find(b'TRAP')
    while i >= 0:
        traps.append(i)
        i = d.find(b'TRAP', i + 1)
    t_end = traps[-1]
    max_n = max(16, (t_end - lit_end) // 8)
    cands = set()
    for t in traps[:-1]:
        for k in range(8):
            off = t + 4 + 4 * k
            if off + 4 <= len(d):
                v = struct.unpack_from('<I', d, off)[0]
                if 16 <= v <= max_n:
                    cands.add(v)
    sane_ops = (0, 1, 2, 3, 4, 5, 6, 7, 0x13, 0x14, 0x1e, 0x20, 0x3c)
    for n in sorted(cands, reverse=True):
        start = t_end - 8 * n
        if start <= lit_end:
            continue
        ok = True
        p = start
        while p + 8 <= t_end:
            arg1 = struct.unpack_from('<I', d, p)[0]
            op = d[p + 4]
            if op not in sane_ops:
                ok = False
                break
            if op == 0x04 and (arg1 >= nlit or d[p + 7] >= nlit):
                ok = False
                break
            p += 8
        if ok:
            return start, t_end
    raise ValueError('code start not found')


def decode_calls(d):
    """Emulate the VM; yield (tag, arg) engine calls in execution order."""
    lit, lit_end = parse_literals(d)
    start, t_end = find_code_start(d, lit_end, len(lit))
    r3 = r4 = None
    calls = []
    p = start
    while p + 8 <= t_end:
        arg1 = struct.unpack_from('<I', d, p)[0]
        op = d[p + 4]
        a0 = d[p + 5]
        a3 = d[p + 7]
        if op == 0x04:
            r3 = ('s', arg1)
            r4 = ('s', a3)
        elif op == 0x01:
            if a0 == 3:
                r3 = ('s', arg1)
            elif a0 == 4:
                r4 = ('s', arg1)
        elif op == 0x02:
            if a0 == 3:
                r3 = ('i', arg1)
            elif a0 == 4:
                r4 = ('i', arg1)
        elif op == 0x3c:
            calls.append((r3, r4))
        p += 8
    out = []
    for r3, r4 in calls:
        tag = lit[r3[1]] if r3 and r3[0] == 's' and r3[1] < len(lit) else None
        if r4 is None:
            arg = None
        elif r4[0] == 's':
            arg = lit[r4[1]] if r4[1] < len(lit) else None
        else:
            arg = r4[1]
        out.append((tag, arg))
    return out


def extract_lines(d, var_names=None):
    """Return one output line per message box (per click), options separate."""
    if var_names is None:
        var_names = VAR_NAMES
    calls = decode_calls(d)
    lines = []
    buf = []
    for tag, arg in calls:
        if tag == 'text':
            if arg:
                buf.append(arg)
        elif tag == 'exp':
            # ('exp', 'f.name') + tagname('embex') inserts the player-name
            # variable into the current message (game-verified pattern);
            # other expressions (f.cp_*=..., conditions) are code -> ignore
            if arg in var_names:
                buf.append(var_names[arg])
        elif tag in ('eol', 'p', 'target', 'label', 'select'):
            # eol/p  = message end (click boundary)
            # target = branch label (precedes each select option text)
            # label/select = option-branch entry: execution resumes in a
            #                new block -> the pending option text must not
            #                merge with the branch's first message
            if buf:
                lines.append(''.join(buf))
                buf = []
    if buf:
        lines.append(''.join(buf))
    return lines


if __name__ == '__main__':
    import sys
    lines = extract_lines(open(sys.argv[1], 'rb').read())
    print('lines:', len(lines))
    for ln in lines[:20]:
        print(' ', ln)
