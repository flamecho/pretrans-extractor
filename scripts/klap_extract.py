#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KLAP!! for Nintendo Switch (NS) STCM2L 文本提取（`STCM2L Apr 12 2018 18:22:39` 变体）。

指令: [u32 func][u32 argc][u32 len][argc × 12B 槽][行内串区]，起点 = CODE_START_+0x10
串记录: 由 sympathy_extract.readrec 兼容 16/24B 头
语义（两作 STORY_01/02 共 174 文件统计）：
  0x1348C 正文(1槽) / 0x13BF8 名札(1槽) / 0x1F4 点击 / 0x15524 选项(4槽: 文,'y','sureN')
  0x6AE8 flag / 0x6108·0x64D8 条件 / 0x62F0 LOVE_xx 参数 —— 不收
用法: python scripts/klap_extract.py <SCRIPT目录>[,<目录2>] <out.txt>
"""
import sys, os, glob, struct, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sympathy_extract import readrec

BODY = {0x1348C}
NAME = {0x13BF8}
CLICK = {0x1F4}
CHOICE = {0x15524}

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
RE_NAME = re.compile(r'#Name\[(\d+)\]')
HERO = {'1': '山城', '2': '曆'}      # 山城 曆（vndb c37652，可改名）


def clean(s):
    s = RE_NAME.sub(lambda m: HERO.get(m.group(1), ''), s)
    return s.strip(' \u3000')


def walk(d):
    i = d.find(b'CODE_START_')
    if i < 0:
        return
    o, n = i + 0x10, len(d)
    while o + 12 <= n:
        op, argc, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n or argc > 400 or 12 + argc * 12 > ln:
            return
        slots = [readrec(d, struct.unpack_from('<I', d, o + 12 + k * 12)[0]) for k in range(argc)]
        yield o, op, slots
        o += ln


def dict_entries(path):
    """用語辞典 dbDictionary.gbin：`[見出し][解説]` 成对（NUL 分隔，串表 @0xA00）。"""
    d = open(path, 'rb').read()
    parts = [x for x in d[0xA00:].split(b'\x00') if x.strip()]
    out = []
    for i in range(0, len(parts) - 1, 2):
        try:
            a, b = parts[i].decode('utf-8'), parts[i + 1].decode('utf-8')
        except UnicodeDecodeError:
            break
        if JP.search(a) and JP.search(b) and len(a) <= 40:
            out.append('【%s】%s' % (a, b.replace('#n', '')))
    return out


def main():
    srcs = sys.argv[1].split(',')
    out = sys.argv[2]
    dpath = sys.argv[3] if len(sys.argv) > 3 else None
    lines, stats = [], {'files': 0, 'boxes': 0, 'opt': 0, 'frag': 0}

    for src in srcs:
        for fn in sorted(glob.glob(os.path.join(src, '*.DAT'))):
            d = open(fn, 'rb').read()
            stats['files'] += 1
            buf = []

            def flush():
                if not buf:
                    return
                body = ''.join(buf)
                buf.clear()
                if body.strip():
                    lines.append(body)
                    stats['boxes'] += 1

            # 2026-10-26 判据更正：`0x1F4`(CLICK) 是「段落末等一次点击」，**不是**「每条文本都点一次」。
            # 实机结构：每句台词前有 NAME(换说话人) + 0x43B54(立绘/表情) + 0x1EAE4，句间无 CLICK
            #   ⇒ 一次点击后文本会**逐条替换**（配 5 次不同立绘），玩家看到的仍是「一句一屏」。
            # 故：只有**两条 BODY 直接相邻**（同一句被框内换行切碎）才合并；其余每个 BODY 起新行。
            prev_body = False
            for o, op, slots in walk(d):
                if op in BODY:
                    t = clean(slots[0]) if slots and slots[0] else ''
                    if t:
                        if not prev_body:
                            flush()
                        buf.append(t)
                        stats['frag'] += 1
                        prev_body = True
                    else:
                        prev_body = False
                    continue
                if op in CHOICE:
                    flush()
                    prev_body = False
                    t = [s for s in slots if s and JP.search(s)]
                    if t:
                        lines.append(clean(max(t, key=len)))
                        stats['opt'] += 1
                    continue
                if op in CLICK or op in NAME:
                    flush()
                    prev_body = False
                    continue
                prev_body = False
            flush()

    if dpath:
        de = dict_entries(dpath)
        lines.extend(de)
        stats['dict'] = len(de)

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as w:
        for ln in lines:
            w.write(ln + '\n')
    print(stats)
    print('lines', len(lines), 'chars', sum(len(x) for x in lines))


if __name__ == '__main__':
    main()
