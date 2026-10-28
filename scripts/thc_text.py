# -*- coding: utf-8 -*-
"""从 thc_extract.py 解出的成员文件中抽取正文（一框一点击）。

TAK 字节码（顺序解析，闭合到文件尾即证明指令边界正确）:
  [u8 op][u8 x][u16 arg]   4 字节定长指令
  0xAA 00 <u16 id> <cp932 文本> 00 00   ← 一框一点击
     其后恒接 0xAB 00 00 00（等待点击）
  0xA8 xx <u16> <名字串> 00 00          ← 名札（本作按规范丢弃）
"""
import os, sys, glob, struct

TEXT_OP = 0xAA
WAIT_OP = 0xAB
NAME_OPS = (0xA4, 0xA8)


def parse_script(d):
    """返回 [(kind, payload)]，kind in {'text','name','cmd'}"""
    out = []
    i = 0
    n = len(d)
    while i + 4 <= n:
        if d[i] == TEXT_OP and d[i + 1] == 0x00:
            k = d.find(b'\x00\x00', i + 4)
            if k < 0:
                break
            txt = d[i + 4:k]
            out.append(('text', txt))
            i = k + 2
            continue
        op = d[i]
        if op in NAME_OPS and d[i + 1] == 0x00 and i + 8 <= n:
            # A4/A8 后面可能跟内联名字串（NUL 结尾），也可能只是参数
            j = i + 4
            z = d.find(b'\x00', j)
            if z > j and all(0x20 <= b < 0x100 for b in d[j:z]):
                cand = d[j:z]
                try:
                    s = cand.decode('cp932')
                    if all('\u3040' <= c <= '\u9fff' or c in '　' for c in s):
                        out.append(('name', cand))
                        i = z + 1
                        continue
                except UnicodeDecodeError:
                    pass
        out.append(('cmd', d[i:i + 4].hex(' ')))
        i += 4
    return out


def main():
    srcdir = sys.argv[1] if len(sys.argv) > 1 else '_work_thc/files'
    outdir = sys.argv[2] if len(sys.argv) > 2 else '_work_thc/txt'
    os.makedirs(outdir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(srcdir, '*.bin')))
    total = 0
    for fn in files:
        d = open(fn, 'rb').read()
        if b'\xaa\x00' not in d:
            continue
        blocks = parse_script(d)
        lines = []
        for kind, payload in blocks:
            if kind != 'text':
                continue
            try:
                s = payload.decode('cp932')
            except UnicodeDecodeError:
                s = payload.decode('cp932', 'replace')
            lines.append((payload, s))
        if not lines:
            continue
        base = os.path.basename(fn)[:-4]
        with open(os.path.join(outdir, base + '.txt'), 'w', encoding='utf-8') as w:
            for raw, s in lines:
                w.write(s + '\n')
        total += len(lines)
    print('files with text', len(os.listdir(outdir)), 'lines', total)


if __name__ == '__main__':
    main()
