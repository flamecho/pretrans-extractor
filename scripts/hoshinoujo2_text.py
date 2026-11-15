#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP]星の王女2（PC / 美蕾 MADOKA GScript・GSCE 编译包）全文本提取。

容器/引擎（L0，魔数＋exe 内部串）：
  exe manifest = `MADOKA.GSX`「Madoka Game Script eXecuter」；剧本 `MP1_星の王女2.sce` 头 `GSCE`。
  `.sce` 布局：
    - 0x00 头（0x0c=365 脚本数、0x28=640/0x2c=480 画面）
    - 0x4c 起 365×0x120 脚本名表（条目 +0xb4 = NUL 结尾 cp932 名）
    - 0x19aec 资源名表（8×0x40）；0x19d60 常量定义表
    - 0x30000~0x225d5a 编译指令区：16B `[u32 行id][u32 类型 0x74/0x06][u32 标志][u32 实参]`
    - 0x225d5a~EOF **字符串表**：`[u32 条目id][u32 字节长][NUL 结尾 cp932 串…]`，逐条自定界

行粒度（L1）：
  一条正文串＝一次点击＝一框；资源 id／语音 id／空串剔；`\x08` 框内换行合并；
  注音 `\x10 base \x11 read \x12` 留 base；人名宏 AF A3=立花、AF A4=未来。

双版（用户规则：一框多次点击 ⇒ 段行＋合并行）：
  - 引擎在「台词」后紧接一条以 `（` 开头的「心之声」串（表格内**紧邻**、中间无任何资源/语音/空串），
    二者为**同一 message 命令**的两次点击（代码实例：id=194 组内 `4639`+`4640`）；
  - 少数作者把两者写进同一串（形如 `「…」（…）`，全作 3 处），其内部亦为两行；
  ⇒ 双版：段行各一次点击一行，合并行＝两段拼接（＝同框全文）。

用法: python hoshinoujo2_text.py <MP1_星の王女2.sce> <out.txt> [--single]
"""
import sys, re, argparse

TABLE_START = 0x225d5a
VOICE = re.compile(r'^[A-Z]{1,4}-[A-Z0-9]{2,6}-\d{1,3}-\d{1,4}$')
JAP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
MACRO_SUR = b'\x05\x80\x80\x80\xaf\xa3'
MACRO_GIV = b'\x05\x80\x80\x80\xaf\xa4'
# 同一串内含「台词」＋（心之声）：在 「」 收尾与 （ 之间切开
SPLIT_INLINE = re.compile(r'^(.*?」)\s*(（.*）)$')


def parse_entries(data, start):
    off = start
    out = []
    while off + 8 <= len(data):
        sid = int.from_bytes(data[off:off + 4], 'little')
        ln = int.from_bytes(data[off + 4:off + 8], 'little')
        if not (1 <= ln <= 0x40000 and sid <= 0x40000):
            break
        if off + 8 + ln > len(data):
            break
        out.append((sid, data[off + 8:off + 8 + ln]))
        off += 8 + ln
    return out, off


def clean(b):
    b = b.replace(MACRO_SUR, '立花'.encode('cp932'))
    b = b.replace(MACRO_GIV, '未来'.encode('cp932'))
    try:
        t = b.decode('cp932')
    except UnicodeDecodeError:
        return None
    t = re.sub(r'\x10(.*?)\x11.*?\x12', r'\1', t)
    t = t.replace('\x08', '')
    return re.sub(r'[\x00-\x1f]', '', t)


def extract(path):
    data = open(path, 'rb').read()
    assert data[:4] == b'GSCE', 'not a GSCE script'
    ents, end = parse_entries(data, TABLE_START)
    # units: (text, adjacent_to_prev_text)
    units = []
    stats = {'entries': len(ents), 'voice': 0, 'nonjp': 0, 'bad': 0}
    for sid, pay in ents:
        prev_text = False
        for s in pay.split(b'\x00'):
            if not s:
                prev_text = False
                continue
            t = clean(s)
            if t is None:
                stats['bad'] += 1
                prev_text = False
                continue
            if VOICE.match(t):
                stats['voice'] += 1
                prev_text = False
                continue
            if not JAP.search(t):
                stats['nonjp'] += 1
                prev_text = False
                continue
            units.append((t, prev_text))
            prev_text = True
    stats['units'] = len(units)
    stats['parsed_end'] = end
    return units, stats


def build(units):
    """段行＋合并行。返回 (lines, n_pairs, n_inline_split)"""
    out = []
    n_pair = 0
    n_split = 0
    prev = None       # 上一段正文（仅相邻时有效）
    prev_is_paren = False
    for t, adj in units:
        is_paren = t.startswith('（') or t.startswith('(')
        m = SPLIT_INLINE.match(t)
        if m and not is_paren:
            a, b = m.group(1), m.group(2)
            out.extend([a, b, a + b])
            n_split += 1
            prev = None
            prev_is_paren = False
            continue
        out.append(t)
        if adj and prev is not None and is_paren and not prev_is_paren:
            out.append(prev + t)      # 合并行：同一 command 的两次点击
            n_pair += 1
        prev = t
        prev_is_paren = is_paren
    return out, n_pair, n_split


def main():
    ap = argparse.ArgumentParser(description='[PC-JP]星の王女2 (MADOKA GSX / GSCE) extractor')
    ap.add_argument('sce')
    ap.add_argument('out')
    ap.add_argument('--single', action='store_true', help='只出单版（段行）')
    a = ap.parse_args()
    units, stats = extract(a.sce)
    if a.single:
        lines = [t for t, _ in units]
        n_pair = n_split = 0
    else:
        lines, n_pair, n_split = build(units)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for l in lines:
            f.write(l + '\n')
    print('entries=%d units=%d out=%d voice=%d nonjp=%d bad=%d pairs=%d inline_split=%d table_end=0x%x'
          % (stats['entries'], stats['units'], len(lines), stats['voice'], stats['nonjp'],
             stats['bad'], n_pair, n_split, stats['parsed_end']))
    print('-> ' + a.out)


if __name__ == '__main__':
    main()
