#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""猛獣使いと王子様 ～Flower & Snow～ (NS) STCM2L 提取：一次点击 = 一行。

L0 链路
  XCI -> NCA -> RomFS/CONTENTS/GAME_01|02.cpk -> script/SCRIPT/*（STCM2L, UTF-8）
L1 记录形状：指令 = [u32 op][u32 nparams][u32 len]，len=整条字节数（4 对齐）
             串记录 = [u32 L/4][u32 1][u32 L][utf8][NUL pad]
L0 断框
  一条 op 0x4C7（np=4）= 一个文本框 = 一次点击（框内 1〜3 行软换行 ⇒ 合并）
  op 0x4BB/0x41B/0x41C/0x41D = 引擎冲刷/等待，出现在特效与分支处（不作分段依据）
  名札 op（逐文件平移，如 0x10AD0/0x16974）= 独立名窗 ⇒ 丢弃
  np>=4 且串表为两份等长变体（#Name 版 / 直写名版）⇒ 取一组
  选项 = 多条短串 + 紧随 0x4CE「select」
  0x4C0「第Ｎ章」= 章ジャンプ菜单（系统）⇒ 丢弃
"""
import sys, os, glob, re, struct
from collections import Counter

A4 = lambda n: (n + 3) & ~3
MACRO = re.compile(r'#[A-Za-z]+\[[^\]]*\]')
NAME_MACRO = re.compile(r'#Name\[(\d+)\]')
SURE = re.compile(r'^sure\d+$')
HERO = {1: 'ティアナ'}
TEXT, SELECT, TITLE, OP_WAIT = 0x4C7, 0x4CE, 0x4C0, 0x4BB


def scan_strings(body, base):
    out, i, n = [], 0, len(body)
    while i + 12 <= n:
        l4, one, L = struct.unpack_from('<3I', body, i)
        if one == 1 and L == l4 * 4 and 4 <= L <= 0x8000 and i + 12 + L <= n:
            raw = body[i + 12:i + 12 + L].rstrip(b'\x00')
            if raw:
                try:
                    s = raw.decode('utf-8')
                except Exception:
                    s = None
                if s is not None and A4(len(raw) + 1) == L and all(ord(c) >= 0x20 for c in s):
                    out.append((base + i, s))
                    i += 12 + L
                    continue
        i += 4
    return out


def walk(path):
    d = open(path, 'rb').read()
    i = d.find(b'CODE_START_')
    if i < 0:
        return []
    o, n, recs = i + 16, len(d), []
    while o + 12 <= n:
        op, np_, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n or np_ > 64:
            break
        recs.append((o, op, np_, ln, scan_strings(d[o + 12:o + ln], o + 12)))
        o += ln
    return recs


def has_jp(s):
    for ch in s:
        if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff'):
            return True
    return False


INLINE = re.compile(r'!\[\d+\]|!e(?![A-Za-z])')


TEXT_PUNCT = set('\u2026\u2025\u3001\u3002\uff01\uff1f\u300c\u300d\u300e\u300f'
                 '\uff08\uff09\u3008\u3009\u300a\u300b\u30fb\u30fc\uff5e\u301c'
                 '\uff1a\uff1b\uff0f\uff3c\u203b\u2605\u2606\u266a\u25c6\u25c7'
                 '\u25a0\u25a1\u25cf\u25cb\u2015\u2014')


def is_text(s):
    for c in s:
        if has_jp(c) or c in TEXT_PUNCT:
            return True
    return False


def clean(s):
    s = NAME_MACRO.sub(lambda m: HERO.get(int(m.group(1)), ''), s)
    return INLINE.sub('', MACRO.sub('', s))


def classify(recs):
    cnt = Counter()
    for o, op, np_, ln, ss in recs:
        if np_ < 1 or op == TITLE or len(ss) >= 6:
            continue
        for _, s in ss:
            if has_jp(s) and len(s) >= 12 and not SURE.match(s):
                cnt[op] += 1
    text_op = cnt.most_common(1)[0][0] if cnt else None
    lead = Counter()
    for k, (o, op, np_, ln, ss) in enumerate(recs):
        if op == text_op or np_ < 1:
            continue
        strs = [s for _, s in ss if s and s != 'c']
        if len(strs) != 1:
            continue
        s = clean(strs[0])
        if len(s) > 14 or any(c in s for c in '\u300c\u300d\uff08\uff09\u3000\u2026'):
            continue
        for o2, op2, np2, ln2, ss2 in recs[k + 1:k + 4]:
            if op2 == text_op:
                lead[op] += 1
                break
    name_op = lead.most_common(1)[0][0] if lead else None
    if name_op and lead[name_op] < 3:
        name_op = None
    opt_op = None
    oc = Counter()
    for k, (o, op, np_, ln, ss) in enumerate(recs):
        if op in (text_op, TITLE) or np_ < 1:
            continue
        jp = [s for _, s in ss if has_jp(s)]
        if not jp:
            continue
        near = any(r[1] == SELECT for r in recs[k + 1:k + 4])
        if near:
            oc[op] += len(jp)
    if oc:
        opt_op = oc.most_common(1)[0][0]
    return text_op, name_op, opt_op


def split_variant(strs):
    n = len(strs)
    if n < 2 or n % 2:
        return strs
    h = n // 2
    a, b = strs[:h], strs[h:]
    same = sum(1 for x, y in zip(a, b) if clean(x) == clean(y))
    if same < max(1, h - 1):
        return strs
    return b if any('#Name[' in s for s in b) else a


def join_lines(items):
    return ''.join(clean(s).lstrip('\u3000') if k else clean(s)
                   for k, s in enumerate(items))


def extract(path):
    recs = walk(path)
    if not recs:
        return [], None, None
    text_op, name_op, opt_op = classify(recs)
    if text_op is None:
        return [], text_op, name_op
    per = [len([s for _, s in r[4] if s and s != 'c'])
           for r in recs if r[1] == text_op]
    per.sort()
    layout_b = bool(per) and per[len(per) // 2] <= 1   # 单串记录 + 0x4BB 断框
    out, cur = [], []

    def flush():
        # 单版：0x4C7（A 布局）＝一条记录一个框一次点击；
        #       0x4BA+0x4BB（B 布局）＝**一屏多行同时显示**，0x4BB 才是等待（一次点击）⇒ 行内合并
        # 两类都是「一框一次点击」⇒ 单版（合并行 0 处）。（2026-10-24 两层双扫复核后确认）
        if not cur:
            return
        line = join_lines(cur)
        cur.clear()
        if line.strip() and not (out and out[-1] == line):
            out.append(line)

    for o, op, np_, ln, ss in recs:
        if op == OP_WAIT:
            if layout_b:
                flush()
            continue
        if op == TITLE or not ss:
            continue
        strs = [s for _, s in ss]
        if op == name_op:
            if layout_b:
                flush()
            continue
        if op == opt_op:
            for s in strs:
                if has_jp(s):
                    out.append(clean(s))
            continue
        if op == text_op:
            items = [s for s in strs if s and s != 'c']
            if items:
                cur.extend(items)
                if not layout_b:
                    flush()
            continue
        if np_ >= 4:
            grp = split_variant(strs)
            if grp is strs or len(grp) == len(strs):
                continue
            items = [s for s in grp if is_text(clean(s))]
            if items:
                cur.extend(items)
                flush()
    flush()
    return out, text_op, name_op


def split_variant(strs):
    n = len(strs)
    if n < 2 or n % 2:
        return strs
    h = n // 2
    a, b = strs[:h], strs[h:]
    same = sum(1 for x, y in zip(a, b) if clean(x) == clean(y))
    if same < max(1, h - 1):
        return strs
    return b if any('#Name[' in s for s in b) else a


def join_lines(items):
    return ''.join(clean(s).lstrip('\u3000') if k else clean(s)
                   for k, s in enumerate(items))
