#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""悠久のティアブレイド for Nintendo Switch —— STCM2L 全文本提取（一次点击＝一行）。

链路
  xcz -> nsz 解压 -> xci -> HFS0 手取 NCA -> hactool -t nca --romfsdir
  romfs/CONTENTS/STORY_01|02.cpk -> SCRIPT/*.DAT（STCM2L, UTF-8）

记录形状（L1，字节码自定界）
  指令 = [u32 op][u32 nparam][u32 len]，len = 整条字节数（4 对齐）
  串记录 = [u32 L/4][u32 1][u32 L][utf8][NUL+pad]

L0 断框
  一条文本 op（np=1，逐文件平移 Δ，基准 95824）＝ 显示行片段
  op 0x1F4（500，builtin，不随 Δ 动）＝ 一次点击/等待 ⇒ 断框
  ⇒ 一框内 1〜3 条文本 op ＝ 软换行 ⇒ 合并成一行（单版）
  名札 op ＝ 文本 op + 1960（独立名字窗）⇒ 丢弃、不加前缀
  变体文本 op（np=8）＝ 同名台词的两版（#Name[1] 版 / 直写名版）⇒ 取首版
  选项 op ＝ 文本 op - 9156 + (Δ)… 见 OPT_DELTA；一记录一选项
  章题 op（「第Ｎ話　…」扉文）⇒ 单独成行
"""
import os, sys, glob, re, struct, argparse

A4 = lambda n: (n + 3) & ~3
HERO = 'イヴ'                      # vndb v19012 主人公 Eve / イヴ（可改名，默认名）
BASE_TEXT = 95824                  # Δ=0 时的文本 op
D_NAME = 1960                      # 名札 = 文本 op + D_NAME
D_VAR = 206960                     # 变体文本 = 文本 op + D_VAR
D_OPT = 9156                       # 选项 = 文本 op + D_OPT
D_CHAP = 368612                    # 章题 = 文本 op + D_CHAP
WAIT = 500                         # 0x1F4 = 一次点击（builtin，固定不平移）
CERO_FILES = {('story01', '100.DAT'), ('story02', '999.DAT')}   # CERO 審査用メニュー

NAME_MACRO = re.compile(r'#Name\[\d+\]')
TAG = re.compile(r'#[A-Za-z_]+\[[^\]]*\]')
SYSTEM_PROMPT = re.compile(r'をスキップしますか？')
SEEN_CHAP = set()          # 章题已出集合（分支重复只留一次）


def scan_strings(body):
    """记录体内按 [L/4][1][L][utf8] 形状取串（自定界，步进 4）。

    ★ L==4 的同类项是**整数参数**（[1][1][4][u32 值]），不是串 ⇒ 跳 16 字节，
      否则会把值当两字符串（实证：0x4E66 → "fN"）混进正文。
    """
    out, k, n = [], 0, len(body)
    while k + 12 <= n:
        l4, one, L = struct.unpack_from('<3I', body, k)
        if one == 1 and L == l4 * 4 and 4 <= L <= 0x8000 and k + 12 + L <= n:
            if L == 4:
                k += 16
                continue
            raw = body[k + 12:k + 12 + L].rstrip(b'\x00')
            if raw:
                try:
                    s = raw.decode('utf-8')
                except UnicodeDecodeError:
                    s = None
                if s is not None and A4(len(raw) + 1) == L and all(ord(c) >= 0x20 for c in s):
                    out.append(s)
                    k += 12 + L
                    continue
        k += 4
    return out


def has_jp(s):
    return any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in s)


def read_records(path):
    d = open(path, 'rb').read()
    i = d.find(b'CODE_START_')
    if i < 0:
        return d, []
    o, recs = i + 16, []
    while o + 12 <= len(d):
        op, np_, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > len(d) or np_ > 64:
            break
        recs.append((o, op, np_, ln))
        o += ln
    return d, recs


def detect_text_op(d, recs):
    from collections import Counter
    c = Counter()
    for off, op, np_, ln in recs:
        if np_ == 1:
            c[op] += sum(1 for s in scan_strings(d[off + 12:off + ln]) if has_jp(s))
    return c.most_common(1)[0][0] if c else None


def strip_tags(s):
    s = NAME_MACRO.sub(HERO, s)
    return TAG.sub('', s)


def split_groups(strs):
    """同框变体：按「引号闭合」切组（组=一次渲染的整段）。标记串 ()/(( 先丢。"""
    strs = [s for s in strs if s.strip() not in ('()', '))', '((', ')', '(')]
    groups, cur, depth = [], [], 0
    for s in strs:
        if depth == 0 and cur and s.startswith('\u300c'):
            groups.append(cur)
            cur = []
        cur.append(s)
        depth += s.count('\u300c') - s.count('\u300d')
        if depth <= 0:
            depth = 0
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return [g for g in groups if g]


def variant_text(strs):
    """变体记录（#Name 版 / 直写名版 同框并列）⇒ 取首组；不像变体则返回 None。"""
    gs = split_groups(strs)
    if len(gs) < 2:
        return None

    def norm(x):
        return re.sub(r'#Name\[\d+\]|イヴ|彼女|彼', '#', ''.join(x))
    if len({norm(g) for g in gs}) == 1:
        return gs[0]
    return None


def extract_file(path):
    d, recs = read_records(path)
    if not recs:
        return []
    top = detect_text_op(d, recs)
    if top is None:
        return []
    delta = top - BASE_TEXT
    NAME, VAR, OPT, CHAP = top + D_NAME, top + D_VAR, top + D_OPT, top + D_CHAP

    out, cur = [], []
    after_chapter, skip_choices = 0, 0
    seen_chap = SEEN_CHAP

    def flush():
        if cur:
            line = strip_tags(''.join(cur))
            cur.clear()
            if line.strip():
                out.append(line)

    for k, (off, op, np_, ln) in enumerate(recs):
        if op == WAIT:
            flush()
            if after_chapter:
                after_chapter -= 1
            continue
        ss = scan_strings(d[off + 12:off + ln])

        if op == NAME:                       # 独立名字窗 ⇒ 丢
            flush()
            continue
        if op == top:
            frags = [s for s in ss if s]
            if after_chapter and any(SYSTEM_PROMPT.search(s) for s in frags):
                # 章题后的「第Ｎ話をスキップしますか？」＝系统确认 ⇒ 连同 はい/いいえ 丢弃
                cur.clear()
                after_chapter = 0
                skip_choices = 4
                continue
            cur.extend(frags)
            continue
        if op == VAR:
            cur.extend(variant_text([s for s in ss if s]) or [])
            flush()
            continue
        if op == OPT:
            txt = [s for s in ss if has_jp(s)]
            if txt:
                if skip_choices:
                    skip_choices -= 1
                    continue
                out.append(strip_tags(txt[0]))
            continue
        if np_ >= 4 and ss:                      # 变体记录：op 逐卷不同 ⇒ 结构化判定
            v = variant_text([s for s in ss if s])
            if v:
                cur.extend(v)
                flush()
                continue
        if op == CHAP:
            flush()
            for s in ss:
                if has_jp(s):
                    t = strip_tags(s)
                    if t not in seen_chap:      # 同章题在分支里重复出现 ⇒ 只留一次
                        seen_chap.add(t)
                        out.append(t)
            after_chapter = 8
            continue
    flush()
    return out


def dict_entries(gbin_path):
    d = open(gbin_path, 'rb').read()
    g = d.rfind(b'GBNL')
    if g < 0:
        return []
    w = struct.unpack_from('<14I', d, g)
    cnt, rsz, stab, sdata = w[6], w[7], w[9], w[11]
    start = stab - cnt * rsz
    blob = d[sdata:]
    rows = []
    for i in range(cnt):
        o = start + i * rsz
        fields = struct.unpack_from('<%dQ' % (rsz // 8), d, o)
        strs = []
        for f in fields:
            if f >= len(blob):
                continue
            e = blob.find(b'\0', f)
            try:
                s = blob[f:e].decode('utf-8')
            except UnicodeDecodeError:
                continue
            if s and s not in strs:
                strs.append(s)
        strs = [s for s in strs if has_jp(s)]
        if len(strs) >= 2:
            rows.append((strs[0], ''.join(strs[1:])))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='_work_tia2')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    lines = []
    for vol in ('story01', 'story02'):
        files = [p for p in glob.glob(os.path.join(args.root, vol, 'SCRIPT', '*.DAT'))
                 if os.path.isfile(p)]
        files.sort(key=lambda p: int(os.path.basename(p)[:-4]))
        for p in files:
            if (vol, os.path.basename(p)) in CERO_FILES:
                continue
            rows = extract_file(p)
            for r in rows:
                if r and (not lines or lines[-1] != r):
                    lines.append(r)

    for name in ('dbDictionary_01', 'dbDictionary_02'):
        gb = os.path.join(args.root, 'system', 'DATABASE', name + '.gbin')
        if os.path.exists(gb):
            for term, desc in dict_entries(gb):
                lines.append('【%s】%s' % (term, desc.replace('#n', '')))

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('[+] %s  %d lines' % (args.out, len(lines)))


if __name__ == '__main__':
    main()
