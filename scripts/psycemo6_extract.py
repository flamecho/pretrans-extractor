#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PsychicEmotion6 (PSV / PCSG00815 / Otomate x Idea Factory / 2015) 全文本提取

容器链路
  NoNpDrm zip -> psvpfsparser -z <zRIF> -> data/STORY.cpk  [CRI CPK]
  ★ CPK: @UTF TOC 的 FileOffset 基址 +0x1000 偏移不可靠 —— 须按「ContentOffset 起、
     Align 对齐、TOC 偏移序」顺序排布，再按 CRILAYLA 解压（用 cpk.py 的 crilayla_decompress，
     cpk_v1 的版本缺变长长度编码，解不出）。
  STORY.cpk = 104 x SCRIPT/*.DAT（剧本, STCM2L）；SYSTEM.cpk = DATABASE/*.gbin/.gstr（系统/表）；
  GAME.cpk = 822 x .tid（纹理）→ 无正文。

STCM2L（PSV 变体）
  0x00 'STCM2L <date>'  0x20 exports_off  0x24 exports_n  0x2c size
  0x50 'GLOBAL_DATA\\0' … 'CODE_START_\\0' → 指令流起点 = 该串 + 12
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length] ＋ nparams×[p0,p1,p2] ＋ data
    ic==0 → opcode 为 builtin 号；ic==1 → opcode 为**函数地址**（随文件常量平移 Δ，Δ=0x10 的整数倍）
  字符串记录（内联于 data 或他处）＝ [0][L/4][1][L][UTF-8 text][pad]，L=align4(len+1)
  显示语义：
     TEXT = call <f_t>  (p0 指向文本记录)   ← 正文/心声/选项
     NAME = call <f_n>  (p0 指向名札记录)   ← 丢弃（不加前缀）
     WAIT = builtin 0x1f4                    ← 换框（= 一次点击边界）
  Δ 自适应：统计各 call 目标引用「含日文串」的次数 → 最多的 = TEXT，次多 = NAME。
  宏：#Name[1] = 月嶋（姓）/ #Name[2] = ヒカリ（名）；默认名 月嶋ヒカリ（vndb v17641）。

用法：
  python scripts/psycemo6_extract.py unpack <cpk> <outdir>
  python scripts/psycemo6_extract.py dump   <scriptdir> <out.txt> [--all]
"""
import os
import re
import sys
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk_v1 import CPK
from cpk import crilayla_decompress   # ★ 必须用此实现

WAIT_OP = 0x1F4
GOTO_OP = 0x006
RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
SURNAME = '月嶋'
GIVEN = 'ヒカリ'
RE_NAME1 = re.compile(r'#Name\[1\]')
RE_NAME2 = re.compile(r'#Name\[2\]')
RE_COMMENT = re.compile(r'/\*.*?\*/', re.S)      # 源内调试注释残留（全库 1 处：608.DAT）

# 原文笔误（整行定值表；勿正则泛修）——已对原始字节核对：该文本框确有「（」无「）」
FIXES = {
    '（瑞希くんのこと、私はどう思ってるんだろう？':
        '（瑞希くんのこと、私はどう思ってるんだろう？）',
}


def clean(s):
    if not s:
        return s
    if '/*' in s:
        s = RE_COMMENT.sub('', s)
        s = s.replace('\r', '').replace('\n', '').replace('\t', '')
    s = s.replace('\x00', '').strip()
    return FIXES.get(s, s)


# ---------------- CPK unpack ----------------
def cpk_entries(path):
    c = CPK(path)
    es = sorted(c.entries, key=lambda e: e['offset'])
    al = c.Align or 1
    off = c.ContentOffset
    out = []
    with open(path, 'rb') as f:
        for e in es:
            sz = e['FileSize']
            f.seek(off)
            data = f.read(sz)
            if data[:8] == b'CRILAYLA':
                try:
                    data = crilayla_decompress(data)
                except Exception as ex:
                    sys.stderr.write('[warn] CRILAYLA fail %s: %s\n' % (e.get('name'), ex))
            out.append((e.get('name') or '', data))
            off += ((sz + al - 1) // al) * al
    return out


def unpack(cpk, outdir):
    n = 0
    for name, data in cpk_entries(cpk):
        name = (name or 'unnamed').replace('\\', '/').lstrip('/')
        dst = os.path.join(outdir, *name.split('/'))
        os.makedirs(os.path.dirname(dst) or outdir, exist_ok=True)
        with open(dst, 'wb') as o:
            o.write(data)
        n += 1
    return n


# ---------------- STCM2L ----------------
def read_record(d, off, limit=2000):
    """[0][L/4][1][L][utf-8][pad] -> str 或 None"""
    if off < 0 or off + 16 > len(d):
        return None
    a, x, c, e = struct.unpack_from('<4I', d, off)
    if a == 0 and c == 1 and 0 < e <= limit * 4 and e % 4 == 0 and x == e // 4 and off + 16 + e <= len(d):
        try:
            return d[off + 16:off + 16 + e].decode('utf-8').rstrip('\x00')
        except UnicodeDecodeError:
            return None
    return None


def walk(d):
    """返回 [(pc, ic, op, np, ln)]"""
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


def detect_ops(d, ins):
    """自适应求 TEXT 的 call 地址：引用「含日文串」最多的 = 正文。
    同一函数表中：NAME = TEXT+0x6FC，OPT = TEXT+0x10F4（Δ 均匀平移，相对偏移恒定）。"""
    from collections import Counter
    cnt = Counter()
    for (p, ic, op, np, ln) in ins:
        if ic != 1 or np < 1:
            continue
        v = struct.unpack_from('<I', d, p + 16)[0]
        s = read_record(d, v)
        if s is not None and RE_JP.search(s):
            cnt[op] += 1
    if not cnt:
        return None, None, None
    t = cnt.most_common(1)[0][0]
    return t, t + 0x6FC, t + 0x10F4


def parse_script(d, stats=None):
    """返回 [line, ...]（一次点击 = 一行；选项一行一条、按序）"""
    ins = walk(d)
    if not ins:
        return []
    T, N, OPT = detect_ops(d, ins)
    lines = []
    segs = []      # 当前文本框的各「段」(goto 分隔的互斥版本)
    cur = []       # 当前段

    def end_seg():
        if cur:
            segs.append(list(cur))
            del cur[:]

    def flush():
        end_seg()
        if not segs:
            return
        # 互斥版本：优先「不含 #Name 宏」的段；并列取最长
        best = None
        for s in segs:
            joined = ''.join(s)
            key = (('#Name' in joined), -len(joined))
            if best is None or key < best[0]:
                best = (key, joined)
        s = clean(best[1])
        s = RE_NAME1.sub(SURNAME, s)
        s = RE_NAME2.sub(GIVEN, s)
        s = clean(s)
        if stats is not None and len(segs) > 1:
            stats['multiseg'] = stats.get('multiseg', 0) + 1
        if s:
            lines.append(s)
        del segs[:]

    for (p, ic, op, np, ln) in ins:
        if ic == 0 and op == WAIT_OP:
            flush()
        elif ic == 0 and op == GOTO_OP:
            end_seg()   # 互斥版本分隔（不下线，不结束点击）
        elif ic == 1 and T is not None and op == T:
            v = struct.unpack_from('<I', d, p + 16)[0]
            s = read_record(d, v)
            if s is None:
                continue
            if cur and s.startswith('\u3000'):
                s = s.lstrip('\u3000')
            cur.append(s)
        elif ic == 1 and OPT is not None and op == OPT:
            flush()     # 选项前先收尾当前框
            v = struct.unpack_from('<I', d, p + 16)[0]
            s = read_record(d, v)
            if s:
                s = clean(s)
                s = RE_NAME1.sub(SURNAME, s)
                s = RE_NAME2.sub(GIVEN, s)
                if s:
                    lines.append(s)
        elif ic == 1 and N is not None and op == N:
            pass        # 名札：丢弃
    flush()
    return lines


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == 'unpack':
        print('unpacked:', unpack(sys.argv[2], sys.argv[3]))
    elif cmd == 'dump':
        root, out = sys.argv[2], sys.argv[3]
        allf = '--all' in sys.argv
        files = []
        for dp, _, fs in os.walk(root):
            for fn in fs:
                if not fn.upper().endswith('.DAT'):
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), root).replace('\\', '/')
                if not allf and rel.lower().startswith('script/init/'):
                    continue
                files.append(rel)
        files.sort(key=lambda r: (0 if r.endswith('/99.DAT') or r == 'SCRIPT/99.DAT' else 1, r))
        res = []
        for rel in files:
            d = open(os.path.join(root, *rel.split('/')), 'rb').read()
            ls = parse_script(d)
            res.append((rel, ls))
            sys.stderr.write('%-24s %5d\n' % (rel, len(ls)))
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as o:
            for rel, ls in res:
                for l in ls:
                    o.write(l + '\n')
        print('files=%d lines=%d -> %s' % (len(res), sum(len(l) for _, l in res), out))


if __name__ == '__main__':
    main()
