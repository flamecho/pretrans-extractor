# -*- coding: utf-8 -*-
"""[NS-JP]レンドフルール for Nintendo Switch 全文本提取（Otomate STCM2L / CPK）

## 容器链（全用工具）
  .xci（头字段坏：rom_size=0x7b、version/cardtype=0xFF ⇒ hactool -t xci 报 corrupt）
  → `scripts/xci_hfs0.py` 选 @0x1f022（Σsize 闭合到 EOF）
  → Program NCA `e2a1e3ab…`（NCA3 / keygen 7 / Gamecard / rights id 全 0，Standard crypto）
  → **nstool --part1**（hactool 1.4.0 对 4.5 GB NCA 不可靠；nstool 直接给 AES-CTR key + 段表）
  → romfs/CONTENTS/STORY.cpk（CRI CPK，`scripts/cpk.py` 解）→ `SCRIPT/*.DAT`（202 个，STCM2L）

## 脚本格式（STCM2L `May 18 2015 17:17:25` / UTF-8）
  头：`STCM2L <date>\0` … `GLOBAL_DATA\0` … **`CODE_START_\0`（0x1A0）⇒ 记录区从 0x1AC 起**
  记录：`[pre][tag][n][size]`，**步进 = size**
  参数：n × `[ptr][2.0f][2.0f]`（12 字节/组），紧跟其后是对象区
  对象：`[0][L/4][1][L][utf8 + NUL + pad]`（`L = align4(len+1)`）

  tag（全库统计，202 个 .DAT）：
    0xE120 = 台词（55,426 条，单串）
    0x35404 = **多串台词**（一屏多行，记录内 2 个串 ⇒ 同一文本框的框内换行）
    0xE81C = 名札（13,659 条，独立名字窗 ⇒ 剔除）
    0x5E90/0x61C0/0x6028/0x6688/0x16084/0x17198 = 调试/旗标/变量名（不收）

## 断行判据（L0）
  **一个「台词记录」= 一个文本框 = 一次点击**；连续相邻的台词记录（中间无其它记录）
  = 同一框被引擎拆成多段 ⇒ 合并成一行（0x35404 的多个串同理，按序拼接）。

## 宏
  `#Name[1]` → **ヴィオレット**（vndb v14919 主角 Violette；剧本里另有直写「ヴィオレット」的行可对照）
"""
import json
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct

ROOT = os.path.join(VNTRANS_HOME, '_w_lf/story/SCRIPT')
OUT = os.path.join(VNTRANS_HOME, "提取结果/[NS-JP]レンドフルール for Nintendo Switch.txt")
HERO = 'ヴィオレット'

TAG_TEXT = {0xE120, 0x35404}
TAG_NAME = {0xE81C}

U = lambda d, o: struct.unpack_from('<I', d, o)[0]
NAME_MACRO = re.compile(r'#Name\[(\d+)\]')
MARKUP = re.compile(r'#[A-Za-z]+\[[^\]]*\]')      # #Speed[2] / #Scale[1.5] / #Color[..] 之类
JUNK = '#]^z{\\$%,*+/=\'"`~|&!?[<>();:._-'


def is_junk(c):
    return ord(c) < 0x80 and not c.isalnum() and c not in ' \u3000'


JP = re.compile(r'[\u3000-\u30ff\u4e00-\u9fff\uff00-\uffef]')   # 日文正文/标点（含「」…。、！？）
SUSPECT = re.compile(r'[\u0400-\u08ff\u0100-\u024f]')          # 西里尔/阿拉伯/希伯来/拉丁扩展 ⇒ 二进制误解码


def clean(s):
    # ⚠ 顺序要紧：`#Name[1]` 也被 MARKUP 的 `#[A-Za-z]+\[…\]` 覆盖，
    #   先替换再删其它指令宏，否则主角名会被一起抹掉（本作 173 处变体段曾因此变成「おい、！」）
    s = NAME_MACRO.sub(HERO, s)
    s = MARKUP.sub('', s)
    s = s.replace('\r', '').replace('\n', '').replace('\t', '')   # \t = 框内软换行（202.DAT/613.DAT 各 1）
    s = s.strip(JUNK)
    # 只有含日文的串才当正文（其余是资源名/变量名/被误当串的二进制）
    if not JP.search(s) or SUSPECT.search(s):
        return ''
    return s


SEG = re.compile(r'「[^「」]{0,400}」')
SPACE = re.compile(r'[\s\u3000]')


def _norm(g):
    """归一化：去空白 + 把 `#Name[n]`/主角名统一抹掉 ⇒ 「直写名版 / #Name 宏版」归一成同一串。"""
    return SPACE.sub('', NAME_MACRO.sub(HERO, g)).replace(HERO, '')


def finalize(s):
    """一条显示行定稿：同一屏并存的两个变体（直写名 / `#Name[1]` 宏版）只留一支。"""
    spans = [(m.start(), m.end(), m.group()) for m in SEG.finditer(s)]
    if len(spans) >= 2:
        keep = []
        for a, b, g in spans:
            if keep and _norm(keep[-1][2]) == _norm(g):
                continue                      # 归一化后同文 ⇒ 同一句的另一支变体
            keep.append((a, b, g))
        if len(keep) < len(spans):
            out = ''
            for k, (a, b, g) in enumerate(keep):
                gap = s[keep[k - 1][1]:a] if k else s[:a]
                out += ''.join(ch for ch in gap if not is_junk(ch)) + g
            s = out.strip(JUNK)
    groups = re.findall(r'「[^「」]*」', s)
    if len(groups) >= 2 and s.rstrip().endswith('」'):
        head, last = groups[0], groups[-1]
        body = last[1:-1].replace(HERO, '')
        if body and body in head:
            s = s[:s.find(head) + len(head)]
    # 「A」＋「A 的前半段（未闭合）」⇒ 后者是变体残段，丢掉
    if s.startswith('「') and s.count('「') == 2 and s.count('」') == 1:
        end = s.find('」')
        head = s[1:end].replace(HERO, '')
        tail = s[end + 2:].replace(HERO, '')
        if tail and head.startswith(tail[:min(12, len(tail))]):
            s = s[:end + 1]
    return s


def slot_text(d, i, n):
    """按槽 ptr 取每槽的串（`0x35404` 的 8 槽 = 两套：标记 + 3 行 ×2）。"""
    out = []
    for k in range(n):
        p = U(d, i + 16 + 12 * k)
        s = ''
        if p and p + 16 <= len(d) and U(d, p + 8) == 1:
            L = U(d, p + 12)
            if 4 <= L < 8000 and p + 16 + L <= len(d):
                try:
                    t = d[p + 16:p + 16 + L].rstrip(b'\x00').decode('utf-8')
                except UnicodeDecodeError:
                    t = ''
                if t and not any(ord(c) < 0x20 and c not in '\t\n\r' for c in t):
                    s = t
        out.append(s)
    return out


def records(d):
    """从 CODE_START_ 之后按 [pre][tag][n][size] 步进，产出 (off, tag, 串表, 槽表)"""
    n_file = len(d)
    i = 0x1AC
    out = []
    while i + 16 <= n_file:
        pre, tag, n, size = U(d, i), U(d, i + 4), U(d, i + 8), U(d, i + 12)
        if pre not in (0, 1) or size < 16 or i + size > n_file or n > 64:
            break
        a, b = i + 16 + 12 * n, i + size
        txt = []
        while a < b - 20:
            L = U(d, a + 12)
            if (U(d, a) == 0 and U(d, a + 4) == L // 4 and U(d, a + 8) == 1
                    and 4 <= L <= 6000 and L % 4 == 0 and a + 16 + L <= b):
                raw = d[a + 16:a + 16 + L].rstrip(b'\x00')
                try:
                    t = raw.decode('utf-8')
                except UnicodeDecodeError:
                    t = None
                if t and not any(ord(c) < 0x20 and c not in '\t\n\r' for c in t):
                    txt.append(t)
                    a += 16 + L
                    continue
            a += 4
        out.append((i, tag, txt, slot_text(d, i, n)))
        i += size
    return out


def variant_text(slots):
    """`0x35404` 的 8 槽 = 两套（各 4 槽：标记槽 + 3 行），两套是同一屏的互斥版本。

    取哪套（代码判据）：
      1. B 引号不平衡（B 缺收尾「」，203.DAT 0x5d880 这类数据残缺）⇒ 取 A；
      2. 归一化（`#Name[1]` 当主角名、去空白）后 **A 是 B 的严格前缀** ⇒ A 被截断，取 B
         （132.DAT 0x59af4：A「…！！」/ B「…#Name[1]…！！　マジか！」）；
      3. 其余取 A —— A 一律是直写名字版，保留「ヴィ、ヴィオレット！？」这类结巴/口语原样。
    """
    A = ''.join(slots[1:4])
    B = ''.join(slots[5:8])
    if not A:
        return B
    if not B:
        return A
    bal = lambda t: t.count('「') == t.count('」')
    if not bal(B) and bal(A):
        return A
    na = _norm(A).rstrip('」')
    nb = _norm(B)
    if na and nb.startswith(na) and len(nb) > len(na):
        return B
    return A


DB = os.path.join(VNTRANS_HOME, '_w_lf/system/DATABASE/dbEntryScript.gbin')


def script_order():
    """脚本顺序取引擎自己的表 `dbEntryScript.gbin`（只收 /SCRIPT/NNN.DAT，不含 init/ 与未登记的 960〜972）。"""
    raw = open(DB, 'rb').read()
    names = [m.group().decode().split('/')[-1]
             for m in re.finditer(rb'/SCRIPT/\d+\.DAT', raw)]
    return names or [f for f in sorted(os.listdir(ROOT)) if f.endswith('.DAT') and f[0].isdigit()]


def build():
    rows, st = [], {'msg': 0, 'name': 0, 'files': 0, 'merged': 0}
    order = script_order()
    for f in order:
        d = open(os.path.join(ROOT, f), 'rb').read()
        if d[:6] != b'STCM2L':
            continue
        st['files'] += 1
        cur = []
        for off, tag, txt, slots in records(d):
            if tag == 0x35404 and len(slots) == 8:
                t = clean(variant_text(slots))
                if t:
                    cur.append(t)
                st['msg'] += 1
                continue
            if tag in TAG_TEXT and txt:
                cur.extend(x for x in (clean(t) for t in txt) if x)
                st['msg'] += 1
                continue
            if tag in TAG_NAME:
                st['name'] += 1
                continue
            if cur:
                rows.append(finalize(''.join(cur)))
                cur = []
        if cur:
            rows.append(finalize(''.join(cur)))
    return rows, st


def main():
    rows, st = build()
    out = [r for r in rows if JP.search(r)]
    ded = []
    for r in out:
        if ded and ded[-1] == r:
            st['merged'] += 1
            continue
        ded.append(r)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(ded) + '\n')
    st['rows'] = len(ded)
    st['chars'] = sum(len(x) for x in ded)
    print(json.dumps(st, ensure_ascii=False))


if __name__ == '__main__':
    main()
