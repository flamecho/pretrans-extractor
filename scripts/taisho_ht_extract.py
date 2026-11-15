#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大正×対称アリス HEADS & TAILS（NS）→ 全文本

链路：XCI → secure → Program NCA → hactool --section1（明文 romfs）→ `SCRIPT.PAK`
      ＋ 更新档（NSP，BKTR）用 `nstool --basenca -x` 取合并后的 `SCRIPT.PAK`（v1.0.2 有改动，必须用）

PAK 容器（与本系列另一作 all in one 同族但字段不同）：
  0x00 u32 data_start（= 名字表末尾）      ★ 直接读，别累加名字长度
  0x04 u32 块数 N
  0x08 u32 ver / 0x0C u32 ?
  0x20 起 N×{u32 hash?, u32 size}          ★ 两字段都不是可用偏移；块在数据区**连续排列**
  0x20+N*8 起 名字表：8 字节头 + ASCII 名（NUL 分隔）
  data_start 起 块数据

脚本记录（**opcode = `23 03`**，本作与 all in one 的 `21 03` 不同）：
  `23 03 | A(u16) | B(u16) | C(u16) | L(u16=日文字数) | 日文(UTF-16LE, L 字) | 00 00
         | flag(u16, 高位 0xFE/0xFF) | 英文(UTF-8) | 00 | mark(u8)`
  ★★ 记录**跨块**、且更新档在日文后**追加了英文**（v0 无此段）⇒ 必须：
     ① 逐字节推进（英文长度不定，奇偶会错位）
     ② 日文后按 `flag 高位 ∈ {FE,FF}` 判英文段，跳到英文的 NUL 再取 mark
  mark：`0b` = 等点击（框到此结束）；`05` = 不等点击（自动推进）。
        05 之后**只有本框引号未闭合**且下一条无名字无 `「` 才同框续写。

正文语法：
  `@名前@本文`  名字在独立名字窗 ⇒ 只留最后一个 `@` 之后的本文（首字段常为空）
  `$[汉字$/よみ$]` ルビ ⇒ 留汉字；`$3` ⇒ 主角名（默认 **アリス**，`有栖$3` = 有栖アリス）
  `$A1` `$S…` `$b` `$w` `$C[…]` 样式/停顿宏 ⇒ 删
  `#` 同一句的双写变体分隔 ⇒ 留第一版
"""
import os
import re
import struct
import sys

DEFAULT_NAME = 'アリス'

OK_EXTRA = {0x2026, 0x2015, 0x300c, 0x300d, 0x3010, 0x3011, 0x3005, 0x000a,
            0x2018, 0x2019, 0x201c, 0x201d, 0x2500, 0x2501}

RUBY = re.compile(r'\$\[([^\[\]]*?)\$/.*?\$\]')
RUBY1 = re.compile(r'\$\[([^\[\]]*?)\$\]')
MACRO_C = re.compile(r'\$C\[[^\]]*\]')
MACRO_S = re.compile(r'\$S(?:\([^)]*\)|\d+(?:,\d+)*)?')
MACRO_A = re.compile(r'\$A\d+')
MACRO_M = re.compile(r'\$[bjw]\d*')
NAME_MACRO = re.compile(r'\$3')


def ok_char(ch):
    """可上屏字符：排除控制符 / PUA / 替换符，其余（含 ♪♡☆ 等记号）一律算原文。

    ★ 曾用「白名单式」字符集，结果把 `「ふんふんふーん♪」` 这类含 `♪`(U+266A) 的
      50 条记录整条判掉（假阴性），所以改成**黑名单**：只挡真不该上屏的码位。
    """
    o = ord(ch)
    if o < 0x20 and o != 0x0a:
        return False
    if 0x7f <= o <= 0x9f or 0xe000 <= o <= 0xf8ff or o == 0xfffd:
        return False
    return True


def looks_japanese(t):
    """至少含 1 个假名/汉字 ⇒ 排除把二进制当 UTF-16 解出来的噪声"""
    return any(0x3000 <= ord(c) <= 0x30ff or 0x4e00 <= ord(c) <= 0x9fff
               or 0xff01 <= ord(c) <= 0xff60 for c in t)


def load_names(d):
    n = struct.unpack_from('<I', d, 4)[0]
    start = 0x20 + n * 8
    end = struct.unpack_from('<I', d, 0)[0]
    nt = d[start + 8:end]                      # 跳过 8 字节表头
    return n, [x.decode('latin1') for x in nt.split(b'\0') if x]


def parse_records(d):
    """连续流解析 → [(offset, jp_text, mark)]"""
    n = len(d)
    ds = struct.unpack_from('<I', d, 0)[0]
    out = []
    i = ds
    while i + 12 < n:
        if d[i] == 0x23 and d[i + 1] == 0x03:
            _a, _b, _c, L = struct.unpack_from('<4H', d, i + 2)
            p = i + 10
            q = p + 2 * L
            if 1 <= L <= 1200 and q + 6 <= n and d[q] == 0 and d[q + 1] == 0:
                try:
                    t = d[p:q].decode('utf-16-le')
                except UnicodeDecodeError:
                    i += 1
                    continue
                if all(ok_char(ch) for ch in t) and looks_japanese(t):
                    if d[q + 3] in (0xFE, 0xFF):
                        k = d.find(b'\x00', q + 4, min(n, q + 1500))
                        if k > 0:
                            out.append((i, t, d[k + 1]))
                            i = k + 2
                            continue
                    out.append((i, t, d[q + 2]))
                    i = q + 4
                    continue
        i += 1
    return out


def split_name(t):
    """`@名前@本文` 或 `本文` → (有名?, 本文)"""
    if '@' in t:
        return True, t.rsplit('@', 1)[1]
    return False, t


def clean(body):
    if '#' in body:                             # 双写变体：留第一版
        body = body.split('#', 1)[0]
    prev = None
    while prev != body:                         # ルビ可能嵌套
        prev = body
        body = RUBY.sub(r'\1', body)
        body = RUBY1.sub(r'\1', body)
    body = NAME_MACRO.sub(DEFAULT_NAME, body)
    body = MACRO_C.sub('', body)
    body = MACRO_S.sub('', body)
    body = MACRO_A.sub('', body)
    body = MACRO_M.sub('', body)
    body = body.replace('\r', '').replace('\n', '')   # 框内换行 ⇒ 合并
    return body.strip('\u3000 \t')


PAIRS = (('「', '」'), ('（', '）'), ('『', '』'))


def unclosed(s):
    """框内引号/括号是否未闭合（台词「」、独白（）、内引『』）"""
    return any(s.count(a) > s.count(b) for a, b in PAIRS)


def starts_new(s):
    """下一条是否**另起**一框 ⇒ 判据是「行首」而不是「含」。

    - 带名字（`@`）⇒ 换名字窗，必是新框；
    - **以** `「` 或 `（` **开头** ⇒ 新框。
    ★ 不能写成「含」：续写片段里也常有 `（察し）`、`『…』` 这类内嵌括号/引号
      （例 `『あ（察し）』ですね!!` 是同框续写），用「含」会把它拆开。
    """
    s = s.lstrip()
    return '@' in s or s[:1] in ('「', '（')


def merge_boxes(recs):
    """mark 0x05 只在「本框引号未闭合」且「下一条无名字无「」时同框续写"""
    out = []
    buf = ''
    for idx, (pos, txt, mark) in enumerate(recs):
        named, body = split_name(txt)
        piece = clean(body)
        nxt = recs[idx + 1][1] if idx + 1 < len(recs) else None
        if buf and named:                        # 换名字窗 ⇒ 必是新框
            out.append(buf)
            buf = ''
        if piece:
            buf = (buf + piece) if buf else piece
        if not buf:
            continue
        cont = (mark == 0x05 and unclosed(buf)
                and nxt is not None and not starts_new(nxt))
        if not cont:
            out.append(buf)
            buf = ''
    if buf:
        out.append(buf)
    return out


def main():
    pak = sys.argv[1] if len(sys.argv) > 1 else '_w_ht/part1/SCRIPT.PAK'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'out.txt'
    d = open(pak, 'rb').read()
    n, names = load_names(d)
    recs = parse_records(d)
    lines = merge_boxes(recs)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('PAK 块 %d，名字 %d，记录 %d → 成品 %d 行' % (n, len(names), len(recs), len(lines)))


if __name__ == '__main__':
    main()
