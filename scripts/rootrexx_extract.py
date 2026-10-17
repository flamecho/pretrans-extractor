#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ROOT∞REXX (PSV / PCSG00458 / Otomate×Idea Factory / 2015) 全文本提取

容器链路
  NoNpDrm zip -> psvpfsparser -z <zRIF> -f cma.henkaku.xyz -> data/STORY.cpk [CRI CPK]
  STORY.cpk = 134 x SCRIPT/*.DAT (STCM2L, CP932); SYSTEM.cpk = DATABASE/*.gbin/.gstr (系统表)

STCM2L (PSV 变体, 本作 = 固定 opcode, 无逐文件 Δ)
  0x00 'STCM2L <date>';  'CODE_START_\\0' -> 指令流起点 = 该串偏移 + 12
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length] + nparams×[p0,p1,p2] + data
  字符串记录 = [0][L/4][1][L][CP932 text][pad]  (L=align4(len+1))
  本作语义:
    ic=1 op=53436  TEXT  p0=内联文本记录 (p0=PC+28)          -> 收
    ic=1 op=54788  NAME  p0=名札记录                          -> 丢弃 (不加前缀)
    ic=1 op=56856  OPT   np=4: p0=选项文本, p3=跳转label       -> 收 (一行一条)
    ic=1 op=121804 DUP   np=8: [id][t1][t2][t3][id][t1'][t2'][t3'] 双写变体 -> 取组1
    ic=0 op=0x1F4  WAIT                                       -> 框/一次点击边界 (flush)
    ic=0 op=6      GOTO                                       -> 段内分隔 (不断点击)
  框 = WAIT 之间; 连续 TEXT 为同框软换行 (续行以 U+3000 起头 -> 合并)
  宏: #Name[1]=望月 (姓) / #Name[2]=和音 (名); 主角默认名 望月和音 (vndb v15577/c37665)

用法:
  python scripts/rootrexx_extract.py cpk <cpk-file> <outdir>
  python scripts/rootrexx_extract.py dump <scriptdir> <out.txt>
"""
import os, re, sys, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK, crilayla_decompress

WAIT_OP = 0x1F4
GOTO_OP = 0x006
TEXT_OP = 53436      # 0xD0BC
NAME_OP = 54788      # 0xD604
OPT_OP = 56856       # 0xDE18
DUP_OP = 121804      # 0x1DBCC (seen 0x1DBCC? -> 121804 = 0x1DBCC)

SURNAME = '望月'
GIVEN = '和音'
RE_NAME1 = re.compile(r'#Name\[1\]')
RE_NAME2 = re.compile(r'#Name\[2\]')

# 排除: replay/回想载体 (按 §0)
EXCLUDE_PREFIX = ('200_replay', '201_replay', '202_replay', '203_replay',
                  '204_replay', '205_replay', '206_replay')

# 原文笔误（整行定值表；勿正则泛修）——已对原始字节核对：
#   2 处缺收尾 」；4 处全角「（」配半角「)」。
FIXES = {
    '「す、すみません。もちろん返事はイエスです。': '「す、すみません。もちろん返事はイエスです。」',
    '「あ、その、九条先輩は今、手が離せなくて……。': '「あ、その、九条先輩は今、手が離せなくて……。」',
    '（お弁当を忘れちゃうだなんて……)': '（お弁当を忘れちゃうだなんて……）',
    '（みんなはどうしてるのかな……。年末年始だから、きっと何かと忙しいはずだよね……)':
        '（みんなはどうしてるのかな……。年末年始だから、きっと何かと忙しいはずだよね……）',
    '（みんなに会いたいな……)': '（みんなに会いたいな……）',
    '（それが分かっただけでも、私はもう十分だよ)': '（それが分かっただけでも、私はもう十分だよ）',
}


def _numkey(rel):
    """按文件名数字前缀排序（00 < 01 < … < 09 < 10 < … < 127），还原阅读顺序。"""
    m = re.match(r'(\d+)', os.path.basename(rel))
    return int(m.group(1)) if m else 10 ** 9


def read_record(d, off, limit=4000, enc='cp932'):
    if off < 0 or off + 16 > len(d):
        return None
    a, x, c, e = struct.unpack_from('<4I', d, off)
    if a == 0 and c == 1 and 0 < e <= limit * 4 and e % 4 == 0 and x == e // 4 and off + 16 + e <= len(d):
        try:
            return d[off + 16:off + 16 + e].decode(enc).rstrip('\x00')
        except UnicodeDecodeError:
            return None
    return None


def walk(d):
    i = d.find(b'CODE_START_')
    if i < 0:
        return []
    p = i + 12
    out = []
    while p + 16 <= len(d):
        ic, op, np, ln = struct.unpack_from('<4I', d, p)
        if ln < 16 or ln % 4 or p + ln > len(d) or np > 0x100:
            break
        out.append((p, ic, op, np, ln))
        p += ln
    return out


def param(d, p, k):
    return struct.unpack_from('<I', d, p + 16 + 12 * k)[0]


def clean(s):
    if not s:
        return s
    s = s.replace('\r', '').replace('\n', '').replace('\t', '').replace('\x00', '')
    s = RE_NAME1.sub(SURNAME, s)
    s = RE_NAME2.sub(GIVEN, s)
    s = s.strip()
    return FIXES.get(s, s)


def parse_script(d, stats=None):
    ins = walk(d)
    lines = []
    cur = []

    def flush():
        if cur:
            s = clean(''.join(cur))
            if s:
                lines.append(s)
            del cur[:]

    for (p, ic, op, np, ln) in ins:
        if ic == 0 and op == WAIT_OP:
            flush()
        elif ic == 0 and op == GOTO_OP:
            pass
        elif ic == 1 and op == TEXT_OP:
            s = read_record(d, param(d, p, 0))
            if s is None:
                continue
            if cur and s.startswith('\u3000'):
                s = s.lstrip('\u3000')
            cur.append(s)
        elif ic == 1 and op == OPT_OP:
            flush()
            s = clean(read_record(d, param(d, p, 0)) or '')
            if s:
                lines.append(s)
                if stats is not None:
                    stats['opt'] = stats.get('opt', 0) + 1
        elif ic == 1 and op == DUP_OP:
            flush()
            grp = []
            for k in (1, 2, 3):
                r = read_record(d, param(d, p, k))
                if r:
                    if grp and r.startswith('\u3000'):
                        r = r.lstrip('\u3000')
                    grp.append(r)
            s = clean(''.join(grp))
            if s:
                lines.append(s)
                if stats is not None:
                    stats['dup'] = stats.get('dup', 0) + 1
        # NAME_OP and everything else: ignored
    flush()
    return lines


def unpack_cpk(cpkpath, outdir):
    c = CPK(cpkpath)
    n = 0
    for e in sorted(c.entries, key=lambda e: e['offset']):
        name = (e.get('name') or 'unnamed').replace('\\', '/').lstrip('/')
        dst = os.path.join(outdir, *name.split('/'))
        os.makedirs(os.path.dirname(dst) or outdir, exist_ok=True)
        with open(dst, 'wb') as o:
            o.write(c.raw(e))
        n += 1
    return n


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == 'cpk':
        print('unpacked:', unpack_cpk(sys.argv[2], sys.argv[3]))
    elif cmd == 'dump':
        root, out = sys.argv[2], sys.argv[3]
        files = []
        for dp, _, fs in os.walk(root):
            for fn in fs:
                if not fn.upper().endswith('.DAT'):
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), root).replace('\\', '/')
                files.append(rel)
        files.sort(key=lambda r: (_numkey(r), r))
        res = []
        stats = {}
        for rel in files:
            base = os.path.basename(rel)
            if base.startswith(EXCLUDE_PREFIX):
                continue
            d = open(os.path.join(root, *rel.split('/')), 'rb').read()
            ls = parse_script(d, stats)
            res.append((rel, ls))
            sys.stderr.write('%-32s %5d\n' % (rel, len(ls)))
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as o:
            for rel, ls in res:
                for l in ls:
                    o.write(l + '\n')
        print('files=%d lines=%d opt=%d dup=%d -> %s' %
              (len(res), sum(len(l) for _, l in res), stats.get('opt', 0), stats.get('dup', 0), out))


if __name__ == '__main__':
    main()
