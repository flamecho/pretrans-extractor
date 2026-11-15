#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大正×対称アリス all in one（NS）→ 全文本

链路：XCI → secure 分区 → Program NCA → RomFS → `SCRIPT.PAK`（自研 PAK，UTF-16LE 明文）
  PAK 容器：0x00 u32 name_off_end / 0x04 u32 块数 / 0x08 u32 ver / 0x0C u32 ?
            0x20 起 N×{u32 未知, u32 块大小}；0x20+N*8 起名字表（ASCII, NUL 分隔）
            数据区 = 名字表末尾，各块**按 size 连续排列**（★ 第一字段不是偏移，别当 off 用）
  脚本块（.tat）：指令流；`21 03` = 文本指令
        named : `21 03 | A(u16) | B(u16) | C(u16) | L(u16, 字数+1) | 60 00 | 文本(L-1 字) | 00 00 | mark(u16)`
        plain : `21 03 | A | B | C | L(u16, 字数) | 文本(L 字) | 00 00 | mark`
                （plain = 地の文，无 `60 00`、无名字）
        ★ mark：`0b 00` ＝ 等点击；`05 00` ＝ **自动送行**（不等点击，短促插话／被打断）
          —— 403 处「引号未闭合」全是 0x05、0x0b 里 0 例；且 0x05 中位 9 字 vs 0x0b 17 字、
          69% 紧接着换说话人 ⇒ 是"自动送行"，**不是同框续写**，故仍一条＝一行。
  正文语法（UTF-16LE 明文）：
        `名前@本文`        ＝ 名字在独立名字窗 ⇒ 丢 `名前@`
        `$[基底$/よみ$]`   ＝ ルビ ⇒ 只留基底
        `$3`               ＝ 主角名宏（默认 **アリス**）
        `$A1`              ＝ 文面スタイル（后接英文原文也常见，如 `$A1Episode of Cinderella`）
        `$S034,1` / `$C[960000]` / `$b` / `$j0` ＝ 样式宏
        `#`                ＝ 同一句的**双写变体分隔**（`「$3……」#「……」`）⇒ 留第一版
  用語辞典：块 `_KEYWORD`（不是 21 03 记录，另行解析）＝ `$S$C[960000]用語（よみ）$C[000000]$S説明`
"""
import os
import re
import struct
import sys

DEFAULT_NAME = 'アリス'          # `$3` 回填值（有栖+$3 = 有栖アリス）

TAG_T = re.compile(r'^\$T\d')
RUBY = re.compile(r'\$\[([^\[\]]*?)\$/.*?\$\]')
MACRO_A = re.compile(r'\$A\d+')
MACRO_S = re.compile(r'\$S\d+(?:,\d+)*')
MACRO_C = re.compile(r'\$C\[[^\]]*\]')
MACRO_MISC = re.compile(r'\$[bj]\d*')
NAME_MACRO = re.compile(r'\$3')

OK_EXTRA = {0x2026, 0x2015, 0x300c, 0x300d, 0x3010, 0x3011, 0x3005, 0x000a,
            0x2018, 0x2019, 0x201c, 0x201d, 0x301c, 0xff5e, 0x2500, 0x2501}


def ok_char(ch):
    o = ord(ch)
    return (0x20 <= o <= 0x7e or 0x3000 <= o <= 0x30ff or 0x4e00 <= o <= 0x9fff
            or 0xff01 <= o <= 0xff60 or 0xff61 <= o <= 0xff9f or o in OK_EXTRA)


def load_pak(path):
    d = open(path, 'rb').read()
    n = struct.unpack_from('<I', d, 4)[0]
    tab = [struct.unpack_from('<2I', d, 0x20 + i * 8) for i in range(n)]
    pos = 0x20 + n * 8
    nt_end = None
    # 名字表：从表尾开始，到数据区起点（第一块的偏移）为止
    names = []
    i = pos
    while i < len(d):
        j = d.find(b'\0', i)
        if j < 0:
            break
        s = d[i:j]
        if s and all(32 <= b < 127 for b in s):
            names.append(s.decode('ascii'))
        elif len(names) > 3:
            nt_end = i
            break
        i = j + 1
    # ★ 数据区起点 = 头 u32@0x00（= 名字表末尾），别自己累加名字长度（会差 8 字节表头）
    data_start = struct.unpack_from('<I', d, 0)[0]
    blocks = []
    p = data_start
    for _unk, size in tab:
        blocks.append((p, size))
        p += size
    return d, names, blocks


def parse_stream(buf, base=0):
    """**连续流**解析脚本记录 → [(kind, text, mark, 起始绝对偏移)]

    ★★ 记录会**跨越脚本块边界**（块表只是脚本入口，数据区是一条连续流）：
    2026-10-28 实测 `SCE02_035` 末条被块尾截断，其尾巴（`貴方が作ってくれたものと…」`）
    落在 `SCE02_036` 的**开头**。按块各自解析会丢掉这类记录（分块 45,285 → 连续 45,521，**236 条**）。
    所以必须整段连续解析，再按「记录起点落在哪块」分桶。
    """
    out = []
    i = 0
    n = len(buf)
    while i + 10 < n:
        if buf[i:i + 2] == b'\x21\x03':
            A, B, C, L = struct.unpack_from('<4H', buf, i + 2)
            if buf[i + 10:i + 12] == b'\x60\x00' and L >= 2:
                q = i + 12 + 2 * (L - 1)
                if q + 4 <= n and buf[q:q + 2] == b'\x00\x00':
                    txt = _dec(buf[i + 12:q])
                    if txt is not None:
                        out.append(('named', txt, buf[q + 2:q + 4].hex(), base + i))
                        i = q + 4
                        continue
            if L >= 1:
                q = i + 10 + 2 * L
                if q + 4 <= n and buf[q:q + 2] == b'\x00\x00':
                    txt = _dec(buf[i + 10:q])
                    if txt is not None:
                        out.append(('plain', txt, buf[q + 2:q + 4].hex(), base + i))
                        i = q + 4
                        continue
        i += 2
    return out


def parse_block(buf):
    """单块解析（兼容旧调用）；跨块记录请用 parse_stream"""
    return [(k, t, m) for k, t, m, _p in parse_stream(buf)]


def _dec(raw):
    try:
        t = raw.decode('utf-16-le')
    except UnicodeDecodeError:
        return None
    if not t or any(not ok_char(ch) for ch in t):
        return None
    return t


def clean(txt, kind):
    """正文清洗（顺序：变体 → 名札 → ルビ → 名宏 → 样式宏 → 合行）"""
    if '#' in txt:                              # 双写变体：留第一版
        txt = txt.split('#', 1)[0]
    if '@' in txt:                              # 名字在独立名字窗 ⇒ 丢
        txt = txt.split('@', 1)[1]
    prev = None
    while prev != txt:                          # ルビ可能嵌套
        prev = txt
        txt = RUBY.sub(r'\1', txt)
    txt = NAME_MACRO.sub(DEFAULT_NAME, txt)
    txt = MACRO_C.sub('', txt)
    txt = MACRO_S.sub('', txt)
    txt = MACRO_A.sub('', txt)
    txt = MACRO_MISC.sub('', txt)
    txt = txt.replace('<<', '').replace('>>', '')      # 強調マーク（全作 1 处）
    txt = txt.replace('\r', '').replace('\n', '')     # 框内换行 ⇒ 合并
    return txt.strip('\u3000 \t')


def merge_boxes(recs):
    """mark 0x05 ＝ 不等点击（自动推进）。**是否同框由引号闭合状态决定**：

    - 本框引号**未闭合**（「 > 」）且下一条无名字、不带「（不开新引号、不换人）⇒ **同框续写**
    - 本框引号已闭合 ⇒ 下一条是新框（0x05 只省掉一次点击），必须断行
    - 下一条带名字（@）⇒ 换名字窗，必是新框

    全量统计（mark=0x05 且下一条为「无名字无「」的记录共 **674** 条）：
    本框 OPEN 的 **398** 条全部是「前框断在引号中间」（`「つまりはだ…………` → `僕も覚えていないんだ」`）；
    本框 closed 的 **276** 条全部是「台词框后接叙述框」（`かぐや@「……んー？」` → `かぐやさんは肩を竦めて…`）。
    ⇒ 曾按「下一条无名字无「就并」处理，把后者 276 处两框并成一框（`「……」かぐやさんは…`）。
    """
    out = []
    buf = ''
    for idx, (kind, txt, mark) in enumerate(recs):
        piece = clean(txt, kind)
        nxt = recs[idx + 1][1] if idx + 1 < len(recs) else None
        if buf and '@' in txt:                     # 换名字窗 ⇒ 必是新框
            out.append(buf)
            buf = ''
        if piece:
            buf = (buf + piece) if buf else piece
        if not buf:
            continue
        cont = (mark == '0500'
                and buf.count('「') > buf.count('」')
                and nxt is not None and '@' not in nxt and '「' not in nxt)
        if not cont:
            out.append(buf)
            buf = ''
    if buf:
        out.append(buf)
    return out


def parse_keyword(buf):
    """`_KEYWORD` 块 → [(用語（よみ）, 説明)]

    实测（★ 整块从**偏移 1** 起解 UTF-16；★ 表里声明的长度比实际短，
    实际数据一直延伸到 PAK 文件末尾 —— 必须整块吃到尾）：
        `$S$C[960000]用語（よみ）$C[000000] \x00 <len> $S説明 \x00` 循环
    """
    t = buf[1:].decode('utf-16-le', 'replace')
    t = '$S$C[960000]' + t                      # 首条缺前缀
    ents = []
    pat = re.compile(r'\$S\$C\[960000\]([^$]+?)\$C\[000000\].*?\$S([^\x00]+)')
    for m in pat.finditer(t):
        term = m.group(1).strip()
        desc = m.group(2)
        term = re.sub(r'^[^\u3000-\u9fff\uff01-\uff60]+', '', term)
        desc = RUBY.sub(r'\1', desc)
        desc = re.sub(r'\$C\[[^\]]*\]', '', desc).replace('$S', '')
        desc = re.sub(r'[\x00-\x1f]', '', desc).strip()
        if term and desc:
            ents.append((term, desc))
    return ents


def main():
    pak = sys.argv[1] if len(sys.argv) > 1 else '_w_txa/pak/SCRIPT.PAK'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'out.txt'
    d, names, blocks = load_pak(pak)
    print('PAK 块 %d，名字 %d，数据区 %#x' % (len(blocks), len(names), blocks[0][0]))
    lines = []
    per_block = []
    # ★ 数据区是**一条连续记录流**（记录可跨块），整段解析后按「起点」分桶
    kw_idx = names.index('_KEYWORD') if '_KEYWORD' in names else len(blocks)
    region_end = blocks[kw_idx][0] if kw_idx < len(blocks) else blocks[-1][0] + blocks[-1][1]
    stream = parse_stream(d[blocks[0][0]:region_end], blocks[0][0])
    import bisect
    starts = [b[0] for b in blocks]
    buckets = [[] for _ in blocks]
    for rec in stream:
        j = bisect.bisect_right(starts, rec[3]) - 1
        if 0 <= j < len(blocks):
            buckets[j].append((rec[0], rec[1], rec[2]))
    for k, (off, size) in enumerate(blocks):
        nm = names[k] if k < len(names) else '?'
        if nm == '_KEYWORD':
            continue
        n = 0
        for t in merge_boxes(buckets[k]):
            if t:
                lines.append(t)
                n += 1
        per_block.append((nm, n))
    # 用語辞典并入末尾
    kw = []
    if '_KEYWORD' in names:
        k = names.index('_KEYWORD')
        end = len(d) if k == len(blocks) - 1 else blocks[k][0] + blocks[k][1]
        kw = parse_keyword(d[blocks[k][0]:end])
        for term, desc in kw:
            lines.append(term)
            if desc:
                lines.append(desc)
    # 后置：跨脚本块被切开的断句（上一行引号未闭合 ＋ 下一行是纯收尾片段）⇒ 合并（全作 2 处）
    fixed = []
    for t in lines:
        if (fixed and fixed[-1].count('「') > fixed[-1].count('」')
                and '「' not in t and '」' in t):
            fixed[-1] += t
        else:
            fixed.append(t)
    lines = fixed
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('正文 %d 行；用語 %d 条' % (len(lines) - sum(2 if b else 1 for a, b in kw), len(kw)))
    print('合计 %d 行' % len(lines))
    for nm, n in per_block:
        if n:
            print('   %-14s %5d' % (nm, n))


if __name__ == '__main__':
    main()
