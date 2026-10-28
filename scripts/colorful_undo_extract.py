#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PSP-JP]放課後colorful＊step～うんどうぶ！～ 全文本提取

链路：ISO9660 → SCRIPT.cpk(CRI CPK) → *.ks (CP932 明文 KAG 风脚本)
      正文 = [message ...] ... [/message] 块（一次点击一块）
      块内 [BR] = 同框软换行（实测每块 1~3 个，与 3 行文本框容量一致）⇒ 合并
      选项 = [SELECT WORD = "..."]
      主角名宏 [FAMILYNAME]/[FIRSTNAME] → 小日向/ナツコ（可改名，填默认值）

只用独立文件，避免与同批 ～ぶんかぶ！～ 作业单元冲突。
"""
import collections
import itertools
import os
import re
import sys
import unicodedata

SRC = os.environ.get('CU_SRC', '_work_colorful_undo/script_cpk')
OUT = os.environ.get('CU_OUT',
                     '提取结果/[PSP-JP]放課後colorful＊step～うんどうぶ！～.txt')

FAMILY = '小日向'
FIRST = 'ナツコ'

# 只收主线（houkago_*）：含共通/部活/MAP個別/おまけ
# 排除：basket_/track_/chika_/daichi_/nanao_/kou_/kiichi_/haruka_（回想副本，94~100% 被主线覆盖）
#       s_houkago_（训练结果系统提示）、status/opning/end/map*_000/mail_*/kyotu/kyotu 系样本、
#       first/test/fonttest/testscenario/sentaku1,2/debug_*、g_*（纯 CG 无字）
KEY_RE = re.compile(r'houkago_(?:[01]|map|omake)')
MSG_RE = re.compile(r'\[message([^\]]*)\](.*?)(?=\[/message\]|\[message|\Z)',
                    re.S | re.I)
SEL_RE = re.compile(r'\[SELECT\s+WORD\s*=\s*"([^"]*)"', re.I)
BAD = re.compile(r'\[/message\]', re.I)


def natkey(fn):
    """houkago_0_000_0.ks → (0,0,0,())、houkago_0_023_0_0_m.ks → (0,23,0,(0,'m'))"""
    stem = fn[:-3]
    m = re.match(r'houkago_(map|omake)_(.*)$', stem)
    if m:
        grp = 2 if m.group(1) == 'map' else 3
        nums = tuple(int(x) for x in re.findall(r'\d+', m.group(2)))
        return (grp, nums, ())
    m = re.match(r'houkago_(\d)_(\d+)_(.*)$', stem)
    nums = (int(m.group(2)),)
    alpha = []
    for p in m.group(3).split('_'):
        if p.isdigit():
            nums += (int(p),)
        else:
            alpha.append(p)
    return (int(m.group(1)), nums, tuple(alpha))


def clean_body(body):
    """块内文本 → 一行：去 [BR]、续行首缩进去掉后直连"""
    body = body.replace('\r\n', '\n').replace('\r', '\n')
    body = BAD.sub('', body)
    lines = [ln for ln in body.split('\n')]
    parts = []
    for ln in lines:
        ln = ln.replace('[BR]', '')
        ln = ln.strip()
        if not ln:
            continue
        parts.append(ln)
    return ''.join(parts)


def parse_file(path):
    """返回按出现顺序的条目：('msg', text) / ('opt', text)"""
    raw = open(path, 'rb').read()
    txt = raw.decode('cp932', errors='replace')
    events = []
    pos = 0
    # 按出现顺序扫描 message 块与 SELECT
    for m in re.finditer(r'\[message([^\]]*)\]|\[SELECT\s+WORD\s*=\s*"([^"]*)"',
                         txt, re.I):
        if m.start() < pos:
            continue
        if m.group(1) is not None:
            body_start = m.end()
            stop = re.search(r'\[/message\]|\[message', txt[body_start:], re.I)
            body = txt[body_start:body_start + stop.start()] if stop else txt[body_start:]
            body = re.sub(r'\[/message\]', '', body, flags=re.I)
            text = clean_body(body)
            if text:
                events.append(('msg', text))
        else:
            opt = m.group(2).strip()
            if opt:
                events.append(('opt', opt))
    return events


def main():
    files = [f for f in os.listdir(SRC) if f.endswith('.ks') and KEY_RE.match(f)]
    files.sort(key=natkey)
    data = {f: parse_file(os.path.join(SRC, f)) for f in files}
    files = [f for f in files if data[f]]

    # ---- 同场景分支副本聚类（≥90% 行重叠 ⇒ 同段取一）----
    parent = {f: f for f in files}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for a, b in itertools.combinations(files, 2):
        A = set(t for k, t in data[a])
        B = set(t for k, t in data[b])
        if len(A & B) / min(len(A), len(B)) >= 0.9:
            parent[find(a)] = find(b)
    clusters = collections.OrderedDict()
    for f in files:
        clusters.setdefault(find(f), []).append(f)

    out = []
    stats = {'files': 0, 'skip_dup_file': 0, 'msg': 0, 'opt': 0}
    merged_variants = []
    for members in clusters.values():
        rep = max(members, key=lambda f: (sum(1 for k, _ in data[f] if k == 'msg'),
                                          -files.index(f)))
        stats['files'] += 1
        stats['skip_dup_file'] += len(members) - 1
        seq = [[k, t] for k, t in data[rep]]
        texts = [t for k, t in seq]
        # 分支差异行：按其在自身文件里的前一行定位，插回同位置（只补不重复）
        for f in members:
            if f == rep:
                continue
            prev = None
            for k, t in data[f]:
                if t in texts:
                    prev = t
                    continue
                idx = (len(texts) - 1 - texts[::-1].index(prev)) if prev else len(texts) - 1
                seq.insert(idx + 1, [k, t])
                texts.insert(idx + 1, t)
                merged_variants.append((f, t))
                prev = t
        for kind, t in seq:
            t = t.replace('[FAMILYNAME]', FAMILY).replace('[FIRSTNAME]', FIRST)
            t = unicodedata.normalize('NFC', t)
            if not t:
                continue
            out.append(t)
            stats['msg' if kind == 'msg' else 'opt'] += 1
    # ★ 不做相邻去重：`「…………」`×2 / `「はい！」`×2 是**两个点击各说一次**，
    #   删掉会丢正文（实测 13 处，全为原文连续同句）
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('files=%d (skip dup file %d) msg=%d opt=%d lines=%d'
          % (stats['files'], stats['skip_dup_file'], stats['msg'], stats['opt'], len(out)))
    if merged_variants:
        print('分支差异并入 %d 行:' % len(merged_variants))
        for f, t in merged_variants[:20]:
            print('  %s | %s' % (f, t[:60]))


if __name__ == '__main__':
    main()
