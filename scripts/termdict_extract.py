# -*- coding: utf-8 -*-
"""用語辞典（termItem.dat）→ `【見出し語】解説文` 一行一条，并入成品末尾

用途：裏語 薄桜鬼 / ～暁の調べ～（Zerodiv 自研）等——成品只从 event.enc 出正文，
而**用語辞典另存于 CPK 的 termItem.dat**，按交付规范须并入全文本末尾。

格式（实测，两作同构）：
  termItem.dat = N × **322 B 定长记录**（本作 N=108）
    0x00 見出し語  32 B  cp932 + NUL 填充
    0x20 読み      32 B  ← **不入正文**（规范：不带读音）
    0x40 解説     残り  以 `01 <索引1字节>` 起头，条内换行 `\\n` ⇒ **合并**

用法：
  python scripts/termdict_extract.py <解包目录> <成品.txt> [--check]
    --check  只打印条目，不改文件
  幂等：先删除成品末尾既有的「【…】」区块再重新追加。
"""
import io
import os
import re
import sys

REC = 322
HEAD_LEN = 32
READ_LEN = 32


def load_terms(dat_path):
    d = open(dat_path, 'rb').read()
    n = len(d) // REC
    out = []
    for i in range(n):
        o = i * REC
        head = d[o:o + HEAD_LEN].split(b'\x00')[0].decode('cp932', 'replace').strip()
        expl = d[o + HEAD_LEN + READ_LEN:o + REC].split(b'\x00')[0].decode('cp932', 'replace')
        # 去 `01 <索引>` 前缀（索引 ≤ 0x6c，恒为 1 字节；0x01 为控制符）
        if expl[:1] == '\x01':
            expl = expl[2:]
        expl = expl.replace('\r', '').replace('\n', '').strip()   # 条内换行合并
        expl = re.sub(r'@\d+[a-z]', '', expl)                       # 去着色码
        if head:
            out.append('【%s】%s' % (head, expl))
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    srcdir, outpath = argv[1], argv[2]
    check = '--check' in argv
    dat = os.path.join(srcdir, 'termItem.dat')
    if not os.path.exists(dat):
        print('[!] 找不到 %s' % dat)
        return 1
    terms = load_terms(dat)
    print('[+] 用語辞典 %d 条' % len(terms))
    for t in terms[:6]:
        print('    ' + t[:80])
    if check:
        return 0

    lines = [x for x in io.open(outpath, encoding='utf-8-sig').read().split('\n') if x]
    before = len(lines)
    lines = [x for x in lines if not x.startswith('【')]      # 幂等：去旧区块
    n_old = before - len(lines)
    lines += terms
    with io.open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('[+] %s : %d 行 -> %d 行（移除旧辞典行 %d，追加 %d）'
          % (outpath, before, len(lines), n_old, len(terms)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
