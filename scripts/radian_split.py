#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ラディアンテイル（STCM2L "May 18 2015" 变体）—— **按源结构把「并框」拆开**。

为什么需要它（2026-10-27 用户指出 `「…」」（…）` 被并成一行）：
  旧 `radian_extract.py` 只把 `0x1f4`（收框）当断点，于是一个 `0x1f4` 周期内的
  **多个「名札 + 正文」组**被拼成了一行。本作 `0x14dac`（名札）每出现一次就是**新消息＝新点击**：
  - 全库 89,430 个 `0x1f4` 周期里，有 632 个含 ≥2 组；632/632 组内容互不相同（不是双版）；
  - 2026-10-26 的 `」「` 探针只拆到 472 个（台词接台词），**漏掉 台词+心声 / 地の文+台词 等 156 个**。

做法：从源重建每个 `0x1f4` 周期内的「组」，把合并串与成品行**唯一匹配**后替换成多行。
  · 只动「整行 === 各组文本按序拼接」的行（不漏不改）
  · `0x435cc`（双版 op）先按 clean 后相等折半，避免把双版拆成两行
  · 匹配不唯一 / 不命中 ⇒ 跳过并报数（人工看）

用法：
  python scripts/radian_split.py <成品.txt> [--src _w_rad/story/SCRIPT] [--dry]

输出：就地改写（先自行备份，如 `.preSplit`）。
"""
import argparse
import collections
import glob
import io
import os
import re
import sys

sys.path.insert(0, 'tools')
from sympathy_extract import walk, is_text
import importlib.util

_spec = importlib.util.spec_from_file_location('W', os.path.join('tools', 'radian_extract.py'))
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)
clean = W.clean
NAME, WAIT = 0x14dac, 0x1f4
BODY = {0x146b0, 0x435cc}
# 断点：名札 / switch+end / 清名 / 收框。**只要两条 BODY 记录之间夹了这些之外的任何 op，
# 也是新消息**（KLAP!! 实证：夹 switch/资源 ⇒ 分行；本作 2026-10-27 补 182 处）
SEPS = {0x14dac, 0x8d1c, 0x14bd4, 0x1f4}

# 3 处「同框混排」（台词 + 地の文，界面上是一屏）—— 用户 2026-10-27 定：**拆成两行，再保留合并行**
# （＝局部双版对照；原文一字不改，只多一行合并版供对照）
KEEP_MERGED = [
    '「んーと、そうだね……」その後。',
    '「ご、誤解させてごめんね。\u3000魔物対策に自衛できればと思って」ちゃんと理由を説明したあと。',
    '「……そうだろ？」突飛なアイディアだし、王様の元へ無許可で立ち入るなんて許されることじゃないのは分かっている。',
]


def all_parts(src):
    """全部「连续 BODY 段」（任意非 BODY op 都断开）—— 用于 KEEP_MERGED 的切分依据。"""
    parts = []
    files = sorted(glob.glob(os.path.join(src, '*.DAT')),
                   key=lambda p: int(re.sub(r'\D', '', os.path.basename(p)) or 0))
    for f in files:
        d = open(f, 'rb').read()
        if not d.startswith(b'STCM2L'):
            continue
        cur = []

        def push():
            if cur:
                t = clean(''.join(half(cur[:])))
                if t:
                    parts.append(t)
                cur.clear()

        for op, ss in walk(d):
            if op in BODY:
                for s in (ss or []):
                    if s and is_text(s):
                        cur.append(s)
            else:
                push()
        push()
    return parts


def half(group):
    """0x435cc 双版：同一组内的两半 clean 后相等 ⇒ 只留前半。"""
    n = len(group)
    if n >= 2 and n % 2 == 0 and [clean(x) for x in group[:n // 2]] == [clean(x) for x in group[n // 2:]]:
        return group[:n // 2]
    return group


def build_blocks(src):
    """返回 [(脚本名, [组文本…])]，只保留 ≥2 组的周期。"""
    out = []
    files = sorted(glob.glob(os.path.join(src, '*.DAT')),
                   key=lambda p: int(re.sub(r'\D', '', os.path.basename(p)) or 0))
    for f in files:
        d = open(f, 'rb').read()
        if not d.startswith(b'STCM2L'):
            continue
        groups, cur = [], []

        def push():
            if cur:
                groups.append(cur[:])
                cur.clear()

        def flush_block():
            if len(groups) >= 2:
                g = [clean(''.join(half(x))) for x in groups]
                g = [x for x in g if x]
                if len(g) >= 2:
                    out.append((os.path.basename(f), g))
            groups.clear()

        for op, ss in walk(d):
            if op in BODY:
                for s in (ss or []):
                    if s and is_text(s):
                        cur.append(s)
            elif op in SEPS:
                push()
                if op == WAIT:
                    flush_block()
        push()
        flush_block()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('txt')
    ap.add_argument('--src', default='_w_rad/story/SCRIPT')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    L = [x for x in io.open(a.txt, encoding='utf-8-sig').read().split('\n') if x.strip()]
    pos = collections.defaultdict(list)
    for i, x in enumerate(L):
        pos[x].append(i)

    blocks = build_blocks(a.src)
    plan, skip = {}, []
    for f, g in blocks:
        idx = pos.get(''.join(g)) or []
        if len(idx) == 1:
            plan[idx[0]] = g
        elif len(idx) > 1:
            skip.append((f, g, '重复 %d 次' % len(idx)))
        else:
            skip.append((f, g, '未在成品里'))

    # 3 处同框混排：拆成段行 + 合并行
    parts = all_parts(a.src)
    km = {}
    for tgt in KEEP_MERGED:
        for i in range(len(parts) - 1):
            for k in (2, 3):
                if i + k <= len(parts) and ''.join(parts[i:i + k]) == tgt:
                    km[tgt] = parts[i:i + k]
                    break
            if tgt in km:
                break

    out = []
    for i, x in enumerate(L):
        # 幂等：若上一行已经是本段的最后一段（＝已经拆过、这行就是留下的合并版），不再重复拆
        already = i > 0 and L[i - 1] == km.get(x, [None])[-1]
        if x in km and i not in plan and not already:
            out.extend(km[x])
            out.append(x)          # ← 合并版留一行
        else:
            out.extend(plan.get(i, [x]))
    print('源多组周期 %d ｜ 拟拆 %d 行 ｜ 跳过 %d' % (len(blocks), len(plan), len(skip)))
    for f, g, why in skip[:8]:
        print('   跳过 %-9s %s ｜ %s' % (f, why, [t[:22] for t in g[:2]]))
    print('行数 %d → %d（%+d）' % (len(L), len(out), len(out) - len(L)))
    if a.dry:
        return
    io.open(a.txt, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(out) + '\n')
    print('已写回', a.txt)


if __name__ == '__main__':
    main()
