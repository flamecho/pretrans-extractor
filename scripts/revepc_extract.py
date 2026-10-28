#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP] DYNAMIC CHORD feat.[rēve parfait] Append Disc（honeybee black / ASGARD）
全文本提取 —— ISO9660 直读 → Rio.arc（Will/AdvHD ext-group）→ rotl_8(c,6) → ws2 字节码。

容器（实测，与同系列 PC 版 apple-polisher 的 Rio.arc 布局不同）：
  ISO9660 → Rio.arc 6,612,205 B
  u32 extGroupCount(=1)
  每组：[ext 4B "WSC\0"][count u32=538][tableOffset u32=0x10]
  条目表 21 B/条：[name 13B][size u32][offset u32]
  自证：Σsize = 6,600,891 = 文件尾 − 数据区首(0x2C32)，零误差

加密：ws2 每字节 rotl_8(c,6)（解密即 rotr 2）。

字节码（本作实测，文本记录＝自定界 NUL 串）：
  0x41 + u16 id + u16 flag + <cp932 台词> NUL      ← 地の文／独白（一框＝一次点击）
  0x42 + u16 id + u16 flag + u8 0 + <名札> NUL + <台词> NUL   ← 台詞（名札整条丢弃）
  0x02 + u16 n + n×[u16 id][选项文本 NUL][01 XX 03][07 <跳转脚本> NUL]   ← 选项

  ★ id 空间：文本记录与选项项共用同一 u16 计数器；每个剧本的 id 恒为 0..N-1
    连续无缺口、无重号（全 436 个含文本剧本 436/436 成立）⇒ 完整性的 L0 自证。

用法: python scripts/revepc_extract.py [--iso <ISO>] [--out <txt>] [--stats]
"""
import argparse
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HOME, 'tools'))
from iso9660 import ISO  # noqa: E402

SRC_DIR = os.path.join(os.environ.get('VNTRANS_HOME', os.getcwd()), 'src')
SRC_TAG = 'rēve parfait'
OUT = os.path.join(HOME, '提取结果/[PC-JP]DYNAMIC CHORD feat.[rēve parfait] Append Disc.txt')

# 路线分组（顺序：共通 → 各自本篇 → 各自后篇 → おまけ）
GROUPS = [
    ('RKYO', '共通ルート'),
    ('RAKI', '亜貴ルート'),
    ('RKUO', '久遠ルート'),
    ('RREO', '玲音ルート'),
    ('RTUM', 'つむぎルート'),
    ('EAKI', '亜貴アフター'),
    ('EKUO', '久遠アフター'),
    ('EREO', '玲音アフター'),
    ('ETUM', 'つむぎアフター'),
    ('ROMAKE', 'おまけ'),
]


def rot(b):
    return bytes((((c << 6) | (c >> 2)) & 0xFF) for c in b)


def find_iso():
    for n in os.listdir(SRC_DIR):
        if SRC_TAG in n and n.lower().endswith('.iso'):
            return os.path.join(SRC_DIR, n)
    raise SystemExit('ISO not found')


def load_arc(iso_path):
    iso = ISO(iso_path)
    ent = None
    for p, e in iso.walk():
        if os.path.basename(p).lower() == 'rio.arc':
            ent = e
            break
    if ent is None:
        raise SystemExit('Rio.arc not found in ISO')
    d = iso.read_file(ent)
    gc = struct.unpack_from('<I', d, 0)[0]
    groups = []
    p = 4
    for _ in range(gc):
        ext = d[p:p + 4].split(b'\x00')[0].decode('latin1')
        cnt, off = struct.unpack_from('<II', d, p + 4)
        p += 12
        groups.append((ext, cnt, off))
    out = {}
    for ext, cnt, off in groups:
        q = off
        for _ in range(cnt):
            name = d[q:q + 13].split(b'\x00')[0].decode('cp932')
            ln, so = struct.unpack_from('<II', d, q + 13)
            q += 21
            out[name] = d[so:so + ln]
    return out


# ---------------- 字节码记录（id 链式扫描，自定界） ----------------

def text_records(b):
    """0x41/0x42 文本记录，按 id 0,1,2… 链式推进（NUL 自定界，永不失步）。"""
    recs = []
    want = 0
    pos = 0
    n = len(b)
    while pos < n - 7:
        cand = [x for x in (b.find(b'\x41', pos), b.find(b'\x42', pos)) if x >= 0]
        if not cand:
            break
        p = min(cand)
        idv = struct.unpack_from('<H', b, p + 1)[0]
        if idv != want or struct.unpack_from('<H', b, p + 3)[0] not in (0, 3):
            pos = p + 1
            continue
        if b[p] == 0x41:
            j = b.find(b'\x00', p + 5)
            if j < 0:
                break
            recs.append((p, idv, None, b[p + 5:j]))
            pos = j + 1
        else:
            j = b.find(b'\x00', p + 6)
            k = b.find(b'\x00', j + 1) if j >= 0 else -1
            if j < 0 or k < 0:
                break
            recs.append((p, idv, b[p + 6:j], b[j + 1:k]))
            pos = k + 1
        want += 1
    return recs


def choice_records(b, nameset):
    """0x02 选项组：[u16 n] + n×([u16 id][文本][01 XX 03][07 目标脚本])，须落在合法剧本名上。"""
    out = []
    for m in re.finditer(rb'\x02', b):
        p = m.start()
        if p + 3 >= len(b):
            continue
        n = struct.unpack_from('<H', b, p + 1)[0]
        if not 1 <= n <= 8:
            continue
        q = p + 3
        items = []
        ok = True
        for _ in range(n):
            idc = struct.unpack_from('<H', b, q)[0]
            s = q + 2
            j = b.find(b'\x00', s)
            if j < 0 or j - s > 200:
                ok = False
                break
            try:
                t = b[s:j].decode('cp932')
            except UnicodeDecodeError:
                ok = False
                break
            if b[j + 1] != 0x01 or b[j + 3] != 0x03 or b[j + 4] != 0x07:
                ok = False
                break
            k = j + 5
            e2 = b.find(b'\x00', k)
            if b[k:e2] not in nameset:
                ok = False
                break
            items.append((idc, t))
            q = e2 + 1
        if ok and items:
            out.append((p, items))
    return out


# ---------------- 清洗 ----------------

def clean(t):
    # 名札并进正文框的特例：`理緒】\n「…」`（开括号是贴图，源串只有收括号）⇒ 去前缀
    t = re.sub(r'^[^\s「」（）]{1,12}】[ \u3000]*(?:\\n)+', '', t)
    t = re.sub(r'%[A-Z]{1,3}', '', t)          # %K %P %O %LC %LR %V …
    t = re.sub(r'[\ue000-\uf8ff]', '', t)      # 内联图标（PUA 字形槽）
    # ruby {基底:読み} → 只留基底（排除含 = " ' 空白的花括号，避免误吃脚本表达式）
    t = re.sub(r'\{([^{}:：="\'\s]+)[:：][^{}]*\}', r'\1', t)
    t = re.sub(r'\\n[ \u3000]*', '', t)        # 框内软换行（字面 \n）＋其后缩进 → 合并
    t = t.replace('\\n', '')
    return t.strip('\u3000 \t\r\n')


def natkey(name):
    m = re.match(r'^([A-Z]+)_?(\d+)([A-Z]*)$', name)
    if not m:
        return (9999, 0, '', name)
    return (int(m.group(2)), 0, m.group(3).ljust(4, '\0'), name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=None)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()

    files = load_arc(a.iso or find_iso())
    nameset = {k.encode('cp932') for k in files}

    # 剧本流：按分组 → 编号 → 变体后缀
    stream = []
    for pref, _label in GROUPS:
        sel = [n for n in files if re.match(r'^%s(\d|_)' % pref, n)]
        sel.sort(key=natkey)
        stream += sel

    per, stats = {}, []
    for nm in stream:
        b = rot(files[nm])
        recs = text_records(b)
        chs = choice_records(b, nameset)
        items = [(p, 0, idv, txt.decode('cp932', 'replace')) for p, idv, nmz, txt in recs]
        for p, its in chs:
            for idc, t in its:
                items.append((p, 1, idc, t))
        items.sort(key=lambda x: (x[0], x[1]))
        out = []
        for p, _k, idv, raw in items:
            t = clean(raw)
            if t:
                out.append(t)
        per[nm] = out
        stats.append((nm, len(recs), len(chs), len(out)))

    # 互斥分支的共通导入块：同 base（前缀+编号）的 A/B/C… 变体，取各行列表的最长公共前缀
    # （≥5 行才折叠），只保留一次 ⇒ 首个变体全出，其余变体从公共前缀之后开始。
    sibs = {}
    for nm in per:
        m = re.match(r'^([A-Z]+)_?(\d+)[A-Z]*$', nm)
        if m:
            sibs.setdefault((m.group(1), int(m.group(2))), []).append(nm)
    drop = {}
    dedup_log = []
    for key, names in sibs.items():
        if len(names) < 2:
            continue
        names.sort(key=natkey)
        ls = [per[n] for n in names]
        n0 = min(len(x) for x in ls)
        lcp = n0
        for i in range(n0):
            if len({x[i] for x in ls}) > 1:
                lcp = i
                break
        if lcp >= 5:
            for n in names[1:]:
                drop[n] = lcp
            dedup_log.append((names, lcp))

    lines = []
    final = {}
    for nm in stream:
        keep = per[nm][drop.get(nm, 0):]
        final[nm] = len(keep)
        lines += keep

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    if a.stats:
        print('scripts %d   texts %d   choice-groups %d   lines %d'
              % (len(stream), sum(s[1] for s in stats), sum(s[2] for s in stats), len(lines)))
        for pref, label in GROUPS:
            sub = [s for s in stats if s[0].startswith(pref)]
            print('  %-8s %3d scripts  %5d lines  %s'
                  % (pref, len(sub), sum(final[s[0]] for s in sub), label))
        for names, lcp in dedup_log:
            print('  共通导入折叠 %s … 前 %d 行 ×%d 份' % (names[0], lcp, len(names) - 1))
    print('->', a.out, len(lines), '行')


if __name__ == '__main__':
    main()
