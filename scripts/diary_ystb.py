# -*- coding: utf-8 -*-
"""Diary（[PC-JP] Operetta 2011 / YU-RIS・YSTB v0x199）全文本提取。

链路：ysbin.ypf(索引名=按位取反, 名表自定界) → .ybn(zlib) → 4B XOR 0x96ac6fd3
      → 头 32B + code/args/res/off 四段 → op0x5A(消息, raw cp932) / op0x3F(一次点击)
用法：python diary_ystb.py <工作目录> <主角名>
"""
import struct, zlib, glob, os, sys, difflib, collections, re

XKEY = bytes([0xd3, 0x6f, 0xac, 0x96])
TXT_OP, END_OP, CALL_OP, EXPR_OP = 0x5A, 0x3F, 0x1D, 0x55
NAME_VAR = 0x0447          # 主角名（运行时输入；本作※名前変更可，默认「綾子」）
MINRUN = 12                # 跨文件重复段判据：difflib 匹配块 >=12 行且逐行全等
RUBY = re.compile(r'≪([^≪≫／]*)／[^≫]*≫')     # 原文 ruby：≪親文字／ルビ≫


def unpack_ypf(path, outdir):
    d = open(path, 'rb').read()
    assert d[:4] == b'YPF\0'
    end = struct.unpack_from('<I', d, 12)[0]          # 数据区起点
    p = 0x20
    n = 0
    while p < end:
        q = p + 5
        e = d.index(b'\x00', q)
        name = ''.join(chr(c ^ 0xff) for c in d[q:e])
        usize, csize, off, _ = struct.unpack_from('<IIII', d, e + 2)
        blob = d[off:off + csize]
        try:
            data = zlib.decompress(blob)
        except zlib.error:
            data = blob[:usize]                        # YSTD：未压缩
        open(os.path.join(outdir, os.path.basename(name)), 'wb').write(data)
        n += 1
        p = e + 18
    return n


def items(ch):
    p = 0
    out = []
    while p + 3 <= len(ch):
        t = ch[p]
        ln = struct.unpack_from('<H', ch, p + 1)[0]
        p += 3
        if p + ln > len(ch):
            break
        out.append((t, ch[p:p + ln]))
        p += ln
    return out


class Scr:
    def __init__(self, path):
        d = open(path, 'rb').read()
        self.ok = d[:4] == b'YSTB'
        if not self.ok:
            return
        self.inst, csz, asz, rsz, osz, _ = struct.unpack_from('<IIIIII', d, 8)
        assert 32 + csz + asz + rsz + osz == len(d), path
        b = bytes(c ^ XKEY[i % 4] for i, c in enumerate(d[32:]))
        self.code, self.args = b[:csz], b[csz:csz + asz]
        self.res = b[csz + asz:csz + asz + rsz]

    def walk(self):
        A = [struct.unpack_from('<III', self.args, i * 12)
             for i in range(len(self.args) // 12)]
        ai = 0
        for i in range(min(self.inst, len(self.code) // 4)):
            c, n = self.code[i * 4], self.code[i * 4 + 1]
            yield i, c, A[ai:ai + n]
            ai += n

    def chunk(self, a):
        pre, ln, off = a
        if 0 < ln and off + ln <= len(self.res):
            return pre, self.res[off:off + ln]
        return pre, None


def extract(path, name):
    s = Scr(path)
    lines, buf, stat = [], [], collections.Counter()
    if not s.ok:
        return lines, stat
    for i, op, a in s.walk():
        if op == TXT_OP:
            for arg in a:
                pre, ch = s.chunk(arg)
                if ch is not None and pre == 0:
                    buf.append(ch.decode('cp932', 'replace'))
        elif op == EXPR_OP:                  # 同框内的变量插入（不改行）
            for arg in a:
                pre, ch = s.chunk(arg)
                if ch is None:
                    continue
                ids = [dd[1] | (dd[2] << 8) for tt, dd in items(ch)
                       if tt == 0x56 and len(dd) == 3]
                if NAME_VAR in ids:
                    buf.append(name)
                    stat['name_insert'] += 1
                elif 0x49 in ids:
                    stat['var49_noop'] += 1
        elif op == CALL_OP and a:
            pre, ch = s.chunk(a[0])
            fn = ''
            if ch is not None:
                it = items(ch)
                if it and it[0][0] == 0x4D:
                    fn = it[0][1].decode('cp932', 'replace').strip('"')
            if fn == 'ES.SEL.SET':           # 选项：紧跟 ES.SEL.GO，中间无正文
                cur = []
                for arg in a[1:]:
                    pre, ch = s.chunk(arg)
                    if ch is None:
                        continue
                    for tt, dd in items(ch):
                        if tt == 0x4D:
                            v = dd.decode('cp932', 'replace').strip('"\'')
                            if v.strip('"\'') and v.strip():
                                cur.append(v)
                lines.extend(cur)
                stat['option'] += len(cur)
            elif fn == 'ES.SEL.GO':
                stat['sel_go'] += 1
        elif op == END_OP:
            txt = RUBY.sub(r'\1', ''.join(buf)).strip()
            buf = []
            if txt and not txt.startswith('【合流点】'):   # 【合流点】= 分岐合流调试标记
                lines.append(txt)
                stat['box'] += 1
    if buf:
        txt = ''.join(buf).strip()
        if txt:
            lines.append(txt)
    return lines, stat


def dedupe(files):
    out, removed = [], []
    for name, lines in files:
        sm = difflib.SequenceMatcher(None, out, lines, autojunk=False)
        drop = [False] * len(lines)
        for b in sm.get_matching_blocks():
            if b.size >= MINRUN:
                for k in range(b.b, b.b + b.size):
                    drop[k] = True
                removed.append((name, b.b, b.size))
        out.extend(l for k, l in enumerate(lines) if not drop[k])
    return out, removed


def main():
    work = sys.argv[1]
    name = sys.argv[2]
    sdir = os.path.join(work, 'script')
    os.makedirs(sdir, exist_ok=True)
    n = unpack_ypf(os.path.join(work, 'Diary', 'pac', 'ysbin.ypf'), sdir)
    files, st = [], collections.Counter()
    for f in sorted(glob.glob(os.path.join(sdir, 'yst*.ybn'))):
        ls, s = extract(f, name)
        st.update(s)
        if ls:
            files.append((os.path.basename(f), ls))
    total = sum(len(l) for _, l in files)
    out, removed = dedupe(files)
    print('ypf entries', n, 'scripts', len(files), 'lines', total, '->', len(out))
    print('stat', dict(st))
    print('dedupe blocks', len(removed), 'lines', total - len(out))
    open(os.path.join(work, '_out.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
    return out


if __name__ == '__main__':
    main()
