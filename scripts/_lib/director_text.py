#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
King of Beast / Macromedia Director 8 文本提取器
================================================
文本成员正文序列化格式:  \x00 <2位hex长度> , <cp932文本(长度字节)>
字体名/成员名属性格式:    <1字节长度 L> <L 字节干净名> <补零>   (无 \x00HH, 前缀)

提取策略 (纯结构判据, 非内容过滤):
  - 扫描所有 \x00HH, 字段, 解出 cp932.
  - 空 / 控制串 -> 丢弃.
  - 前导字节 p0 在 1..0x40 且 field[1:1+p0] 是「干净可打印 token」(无内部 NUL/控制)
    且后续基本为空 -> 判定为长度前缀属性 (字体名/成员名/键盘串) -> 丢弃.
  - 否则视为正文 -> 保留 (再叠加字体名关键字黑名单兜底).
  - 正文内的 \\r 是文本框内换行, 保留为 LF (一行 = 一个文本框).
"""
import re, sys, os, json

PAT_A = re.compile(rb'\x00([0-9a-fA-F]{2}),')
FONT_KW = ('体','ゴシック','明朝','楷書','隷書','W9','W7','W5','W3','ＤＦＰ')

def is_garbage(s: str) -> bool:
    """二进制误解码串：含半角仮名(U+FF66-9F)或 PUA(U+E000-F8FF)即判垃圾。"""
    for ch in s:
        o = ord(ch)
        if 0xFF66 <= o <= 0xFF9F or 0xE000 <= o <= 0xF8FF:
            return True
    return False

def is_clean_token(b: bytes) -> bool:
    """无内部 NUL/控制字符且可 cp932 解码为单 token."""
    if not b:
        return False
    if b'\x00' in b or any(0 < c < 0x20 for c in b):
        return False
    try:
        b.decode('cp932')
        return True
    except Exception:
        return False

def decode_field(field: bytes):
    """cp932 解码并剥除游戏内部控制码（C1 控制符 / 孤立无效字节）。"""
    try:
        s = field.decode('cp932', 'ignore')
    except Exception:
        s = field.decode('latin1', 'ignore')
    # \r / \n 为文本框内换行 -> 半角空格; 去 NUL
    s = s.replace('\r', ' ').replace('\n', ' ').replace('\x00', '')
    # 剥 C1 控制符 (U+0080-009F) 等残留控制码
    s = ''.join(ch for ch in s if not (0x00 <= ord(ch) <= 0x1f or 0x7f <= ord(ch) <= 0x9f))
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def extract_file(path: str, verbose=False):
    data = open(path, 'rb').read()
    out = []
    for m in PAT_A.finditer(data):
        L = int(m.group(1), 16)
        if L == 0:
            continue
        field = data[m.end():m.end()+L]
        if len(field) < 1:
            continue
        p0 = field[0]
        dropped = False
        # 前导单字节长度前缀 + 干净名 + 后续补零 => 字体名/成员名属性串
        if 1 <= p0 <= 0x40 and (p0 + 1) <= L:
            name = field[1:1+p0]
            tail = field[1+p0:]
            null_ratio = (tail.count(0) + sum(1 for x in tail if 0 < x < 0x20)) / (len(tail) + 1)
            if is_clean_token(name) and null_ratio > 0.5:
                dropped = True
        if dropped:
            continue
        s = decode_field(field)
        if not s:
            continue
        # 字体名关键字兜底
        if any(k in s for k in FONT_KW):
            continue
        # 二进制误解码垃圾（半角仮名/PUA）
        if is_garbage(s):
            continue
        out.append(s)
    return out

def main():
    if len(sys.argv) < 2:
        print("usage: director_text.py <file|dir> [--json out.json]")
        sys.exit(1)
    target = sys.argv[1]
    results = {}
    if os.path.isdir(target):
        for fn in sorted(os.listdir(target)):
            if fn.lower().endswith(('.dxr', '.cxt', '.cst')):
                p = os.path.join(target, fn)
                results[fn] = extract_file(p)
    else:
        results[os.path.basename(target)] = extract_file(target)
    # 输出
    total = 0
    for fn, lines in results.items():
        total += len(lines)
        print(f"# {fn}: {len(lines)} lines", file=sys.stderr)
    if '--json' in sys.argv:
        jp = sys.argv[sys.argv.index('--json')+1]
        json.dump(results, open(jp, 'w'), ensure_ascii=False)
    else:
        # 顺序输出所有行 (供人工核对)
        for fn, lines in results.items():
            for s in lines:
                print(s)
    print(f"# TOTAL={total}", file=sys.stderr)
