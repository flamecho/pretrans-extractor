# RealLive SEEN.TXT parser (length-scanner port of rlvm libreallive)
import struct
from rl_decomp import decompress, read_toc, scenario

class Parser:
    def __init__(self, d):
        self.d = d
        self.p = 0

    def eof(self):
        return self.p >= len(self.d)

    def peek(self, n=0):
        return self.d[self.p + n] if self.p + n < len(self.d) else 0

    # --- length scanners (port of expression.cc) ---
    def next_token(self, p):
        if self.d[p] != 0x24:  # '$'
            return 0
        if self.d[p+1] == 0xff:
            return 6
        if self.d[p+2] != 0x5b:  # '['
            return 2
        return 4 + self.next_expression(p + 3)

    def next_term(self, p):
        c = self.d[p]
        if c == 0x28:  # '('
            return 2 + self.next_expression(p + 1)
        if c == 0x5c:  # '\\'
            return 2 + self.next_term(p + 2)
        return self.next_token(p)

    def next_arithmatic(self, p):
        lhs = self.next_term(p)
        while self.d[p+lhs] == 0x5c:
            lhs += 2 + self.next_term(p + lhs + 2)
        return lhs

    def next_condition(self, p):
        lhs = self.next_arithmatic(p)
        while self.d[p+lhs] == 0x5c and 0x28 <= self.d[p+lhs+1] <= 0x2d:
            lhs += 2 + self.next_arithmatic(p + lhs + 2)
        return lhs

    def next_and(self, p):
        lhs = self.next_condition(p)
        while self.d[p+lhs] == 0x5c and self.d[p+lhs+1] == 0x3c:
            lhs += 2 + self.next_condition(p + lhs + 2)
        return lhs

    def next_expression(self, p):
        lhs = self.next_and(p)
        while self.d[p+lhs] == 0x5c and self.d[p+lhs+1] == 0x3d:
            lhs += 2 + self.next_and(p + lhs + 2)
        return lhs

    def next_string(self, p):
        d = self.d
        end = p
        quoted = False
        while True:
            c = d[end]
            if quoted:
                if c == 0x22 and d[end-1] != 0x5c:  # unescaped quote
                    quoted = False
                    end += 1
                    break
            else:
                if c == 0x22:
                    quoted = True
                if d[end:end+9] == b'###PRINT(':
                    end += 9
                    end += 1 + self.next_expression(end)
                    continue
                if not ((0x81 <= c <= 0x9f) or (0xe0 <= c <= 0xef) or
                        (0x61 <= c <= 0x7a) or (0x41 <= c <= 0x5a) or
                        (0x30 <= c <= 0x39) or c in (0x20, 0x3f, 0x5f, 0x22, 0x5c)):
                    break
            if (0x81 <= c <= 0x9f) or (0xe0 <= c <= 0xef):
                end += 2
            else:
                end += 1
        return end - p

    def next_data(self, p):
        d = self.d
        c = d[p]
        if c == 0x2c:  # ','
            return 1 + self.next_data(p + 1)
        if c == 0x0a:  # '\n'
            return 3 + self.next_data(p + 3)
        if ((0x81 <= c <= 0x9f) or (0xe0 <= c <= 0xef) or
                (0x41 <= c <= 0x5a) or (0x30 <= c <= 0x39) or
                c in (0x20, 0x3f, 0x5f, 0x22) or d[p:p+9] == b'###PRINT('):
            return self.next_string(p)
        if c == 0x61 or c == 0x28:  # 'a' or '('
            end = p
            if d[end] == 0x61:
                end += 1
                end += 1  # tag
                if d[end] == 0x61:
                    end += 2
                if d[end] != 0x28:
                    end += self.next_data(end)
                    return end - p
            end += 1  # consume '('
            while d[end] != 0x29:  # ')'
                end += self.next_data(end)
            end += 1
            if d[end] == 0x5c:
                end += self.next_expression(end)
            return end - p
        return self.next_expression(p)

    # --- elements ---
    def read_element(self):
        d = self.d
        start = self.p
        c = d[start]
        if c in (0x00, 0x2c):  # NUL / ','
            self.p += 1
            return ('comma', None)
        if c == 0x0a:  # line meta
            self.p += 3
            return ('meta', struct.unpack_from('<H', d, start+1)[0])
        if c in (0x40, 0x21):  # '@' '!'
            self.p += 3
            return ('entry', struct.unpack_from('<H', d, start+1)[0])
        if c == 0x24:  # '$' expression element: term + 2 + expression
            p = start
            p += self.next_term(p)
            p += 2
            p += self.next_expression(p)
            self.p = p
            return ('expr', d[start:p])
        if c == 0x23:  # '#'
            return self.read_function(start)
        # text
        p = start
        quoted = False
        while p < len(d):
            ch = d[p]
            if quoted:
                quoted = ch != 0x22
                if ch == 0x5c and d[p+1] == 0x22:
                    p += 1
            else:
                if ch == 0x2c:
                    p += 1
                    ch = d[p]
                quoted = ch == 0x22
                if ch in (0x00, 0x23, 0x24, 0x0a, 0x40, 0x21):
                    break
            if (0x81 <= ch <= 0x9f) or (0xe0 <= ch <= 0xef):
                p += 2
            else:
                p += 1
        self.p = p
        return ('text', d[start:p])

    def read_function(self, start):
        d = self.d
        hdr = d[start:start+8]
        modtype, module = hdr[1], hdr[2]
        opcode = hdr[3] | (hdr[4] << 8)
        argc = hdr[5] | (hdr[6] << 8)
        overload = hdr[7]
        packed = (modtype << 24) | (module << 16) | opcode
        p = start + 8
        kind = 'func'
        extra = {}
        if packed in (0x00010000, 0x00010005, 0x00050001, 0x00050005,
                      0x00060001, 0x00060005):  # goto
            p += 4
            kind = 'goto'
        elif packed in (0x00010001, 0x00010002, 0x00010006, 0x00010007,
                        0x00050002, 0x00050006, 0x00050007, 0x00060000,
                        0x00060002, 0x00060006, 0x00060007):  # gotoif
            assert d[p] == 0x28
            p += 1 + self.next_expression(p + 1) + 1
            p += 4
            kind = 'gotoif'
        elif packed in (0x00010003, 0x00010008, 0x00050003, 0x00050008,
                        0x00060003, 0x00060008):  # gotoon
            p += self.next_expression(p)
            assert d[p] == 0x7b
            p += 1 + argc * 4
            assert d[p] == 0x7d
            p += 1
            kind = 'gotoon'
        elif packed in (0x00010004, 0x00010009, 0x00050004, 0x00050009,
                        0x00060004, 0x00060009):  # gotocase
            p += self.next_expression(p)
            assert d[p] == 0x7b
            p += 1
            for _ in range(argc):
                assert d[p] == 0x28
                if d[p+1] == 0x29:
                    p += 2
                else:
                    p += 1 + self.next_expression(p + 1) + 1
                p += 4
            assert d[p] == 0x7d
            p += 1
            kind = 'gotocase'
        elif packed in (0x00010010, 0x00060010):  # gosubwith
            if d[p] == 0x28:
                p += 1
                while d[p] != 0x29:
                    p += self.next_data(p)
                p += 1
            p += 4
            kind = 'gosub'
        elif packed in (0x00020000, 0x00020001, 0x00020002, 0x00020003,
                        0x00020010):  # select
            if d[p] == 0x28:
                p += self.next_expression(p)
            assert d[p] == 0x7b, f'select {{ at {p}'
            p += 1
            if d[p] == 0x0a:
                p += 3
            opts = []
            for _ in range(argc):
                while d[p] == 0x2c:
                    p += 1
                if d[p] == 0x28:
                    p += 1
                    while d[p] != 0x29:
                        if d[p] == 0x28:
                            p += self.next_expression(p)
                        eff = d[p]
                        seekarg = eff not in (0x32, 0x33)
                        p += 1
                        if seekarg and d[p] != 0x29 and not (0x30 <= d[p] <= 0x39):
                            p += self.next_expression(p)
                    p += 1
                tlen = self.next_string(p)
                opts.append(d[p:p+tlen])
                p += tlen
                assert d[p] == 0x0a
                p += 3
            while d[p] == 0x0a:
                p += 3
            assert d[p] == 0x7d, f'select }} at {p}'
            p += 1
            kind = 'select'
            extra['opts'] = opts
        else:  # plain function
            if d[p] == 0x28:
                p += 1
                params = []
                while d[p] != 0x29:
                    ln = self.next_data(p)
                    params.append(d[p:p+ln])
                    p += ln
                p += 1
                extra['params'] = params
        self.p = p
        return (kind, (modtype, module, opcode, overload, extra))

def parse_scenario(data):
    p = Parser(data)
    elts = []
    while not p.eof():
        elts.append(p.read_element())
    return elts

if __name__ == '__main__':
    import sys
    d = open('game/Seen.txt', 'rb').read()
    toc = read_toc(d)
    sn = int(sys.argv[1]) if len(sys.argv) > 1 else 101
    off, ln = toc[sn]
    hdr_len, ver, comp_off, dlen, clen, s = scenario(d, off, ln)
    code = decompress(s[comp_off:comp_off+clen], dlen)
    assert len(code) == dlen
    elts = parse_scenario(code)
    print(f'SEEN{sn:04d}: {len(elts)} elements, {len(code)} bytes')
    # histogram
    from collections import Counter
    hist = Counter()
    for kind, val in elts:
        if kind == 'text':
            hist['text'] += 1
        elif kind in ('func', 'select', 'goto', 'gotoif', 'gotoon', 'gotocase', 'gosub'):
            mt, mo, op, ov, _ = val
            hist[f'{kind} {mt}:{mo}:{op}/{ov}'] += 1
        else:
            hist[kind] += 1
    for k, v in hist.most_common(40):
        print(v, k)
    # dump first text elements raw
    n = 0
    for kind, val in elts:
        if kind == 'text':
            print('TEXT', val[:120])
            n += 1
            if n >= 15:
                break