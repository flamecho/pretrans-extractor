#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real Rode ポータブル (PSP, HuneX「IKA SEQ SYSTEM v3.1」) 全文本提取。

源：ISO `PSP_GAME/USRDIR/data/test/script.bin`（HFU2 容器，578 区块）
容器：`HFU2` + u32 count + u32 (表尾对齐值) + count×[u32 off][u32 size][u32 size][u32 hash]（16B/条，off 0x800 对齐）
字节码：指令 = `26 <cmd:u8> 24 <nargs:u8> <operands>`；字符串记录 = `5C <u8 len> <SJIS (len-4)B> 00 00`（len = 记录总长）
       标识符记录 = `23 <u8 len> <ASCII (len-1)B> <u8 tag>`
文本命令（全部 5C 记录恰由这 4 条命令承载，87676/87676）：
  0x3E n=1  姓名札（丢弃，不产出说话人）
  0x3C n=1  台词（引擎自动补开引号「；数据里只有结尾」）—— 本脚本补「
  0x44 n=1  地の文/独白（无引号）
  0x41 n=4  选项（连续出现＝同一组；0x42 收尾）。选项后的数值参数为写入值，非显示文本 → 丢弃
铭文宏：全角＠（SJIS 0x8197，U+FF20）= 主人公名（可改名，默认「ニィナ」）→ 行内替换
换行：`@n` = 同文本框内软换行 → 合并
"""
import sys, struct

HERO = 'ニィナ'
NAME_OP, SPEECH_OP, NARR_OP, CHOICE_OP = 0x3E, 0x3C, 0x44, 0x41
HERO_MACRO = '\uff20'   # ＝ 0x8197


def parse_container(d):
    assert d[:4] == b'HFU2', 'not HFU2'
    cnt = struct.unpack_from('<I', d, 4)[0]
    ents = [struct.unpack_from('<IIII', d, 0x10 + i * 16) for i in range(cnt)]
    return cnt, ents


def strrec(d, i, N):
    """i 指向 0x5C；返回 (text, total_len) 或 None"""
    if i >= N or d[i] != 0x5C:
        return None
    ln = d[i + 1]
    if ln < 4 or i + ln > N or d[i + ln - 2:i + ln] != b'\x00\x00':
        return None
    try:
        return d[i + 2:i + ln - 2].decode('cp932'), ln
    except UnicodeDecodeError:
        return None


def extract(d):
    N = len(d)
    out = []
    i = 0x4000
    while i < N - 8:
        if d[i] == 0x26 and d[i + 2] == 0x24 and d[i + 4] == 0x5C:
            op, n = d[i + 1], d[i + 3]
            ok = (op in (NAME_OP, SPEECH_OP, NARR_OP) and n == 0x01) or (op == CHOICE_OP and n == 0x04)
            if ok:
                r = strrec(d, i + 4, N)
                if r:
                    out.append((i, op, r[0]))
                    i += 4 + r[1]
                    continue
        i += 1
    return out


def to_lines(recs):
    lines = []
    for off, op, s in recs:
        if op == NAME_OP:
            continue
        t = s.replace('@n', '')                       # 软换行合并
        t = t.replace(HERO_MACRO, HERO)               # 主人公名宏
        if t.endswith('」') and not t.startswith('「'):
            t = '「' + t                               # 引擎自动补的开引号（0x3C 一律；0x44 仅 3 处作者手误）
        lines.append(t)
    return lines


def main():
    global HERO
    src = sys.argv[1]
    dst = sys.argv[2]
    if '--heroine' in sys.argv:
        HERO = sys.argv[sys.argv.index('--heroine') + 1]
    d = open(src, 'rb').read()
    cnt, _ = parse_container(d)
    recs = extract(d)
    lines = to_lines(recs)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    ops = {NAME_OP: 'name', SPEECH_OP: 'speech', NARR_OP: 'narr', CHOICE_OP: 'choice'}
    stat = {}
    for _, op, _ in recs:
        stat[ops[op]] = stat.get(ops[op], 0) + 1
    print('container blocks=%d  5C records=%d  %s' % (cnt, len(recs), stat))
    print('output lines=%d -> %s' % (len(lines), dst))


if __name__ == '__main__':
    main()
