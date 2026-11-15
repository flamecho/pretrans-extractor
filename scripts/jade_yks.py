#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""24時、君のハートは盗まれる～怪盗ジェイド～ 文本抽取（YKC 容器 → YKS 脚本 → 台詞/地の文）。

L0 判据（全部为字节层，可复核）：
  1) 容器 YKC001：`YKC001\\0\\0` + u32@8(=24 头长) + u32@16(=索引起始偏移) + u32@20(=索引长度)
     数据区 = [24, idx_off)，索引 = 20B/条：`[name_off u32][name_len u32][data_off u32][size u32][0]`
     名字为 NUL 结尾串，存在数据区末尾的字符串池里；data_off 逐条首尾相接（可闭合校验）。
  2) 脚本 YKS001：`YKS001` + u16 ver；u32@8=40(头长) u32@16=块1off u32@20=块2off u32@24=块3off
     u32@28=块3条数 u32@32=块4off u32@36=块4len。**仅块4 逐字节 XOR 0xAA**（其余块明文）。
  3) 块4 = 前缀式命令流：`命令名\\0` + 参数（u32 或 NUL 结尾串）。
     台詞节点 `[u32 13][名前\\0][本文\\0]`；地の文 `[u32][u32][本文\\0]` 或 `StrOut[..] <本文>\\0`；
     選択肢 `Case\\0<本文>\\0`。

用法：
  python scripts/jade_yks.py <jade01.dat>                # 列出条目
  python scripts/jade_yks.py <jade01.dat> --dump DIR     # 解出全部 .yks 的块4（XOR 后明文）
  python scripts/jade_yks.py <jade01.dat> --text OUT.txt  # 抽台词
"""
import argparse
import os
import struct
import sys


# ---------- 容器 ----------
def read_index(path):
    f = open(path, 'rb')
    head = f.read(24)
    if head[:6] != b'YKC001':
        raise SystemExit('不是 YKC001 容器: %s' % path)
    idx_off, idx_len = struct.unpack('<II', head[16:24])
    f.seek(idx_off)
    idx = f.read(idx_len)
    ents = []
    for i in range(idx_len // 20):
        name_off, name_len, off, size, _ = struct.unpack('<IIIII', idx[i * 20:i * 20 + 20])
        f.seek(name_off)
        name = f.read(name_len).rstrip(b'\x00').decode('cp932')
        ents.append((name, off, size))
    return f, ents


# ---------- YKS ----------
def ykc_entry(f, off, size):
    f.seek(off)
    return f.read(size)


def ykS_blocks(b):
    if b[:6] != b'YKS001':
        return None
    h = [struct.unpack('<I', b[o:o + 4])[0] for o in (8, 12, 16, 20, 24, 28, 32, 36)]
    code = bytes(c ^ 0xAA for c in b[h[6]:h[6] + h[7]])
    return h, code


# ---------- 分词 ----------
def is_cp932_ok(s):
    """串必须 cp932 可解、无 0xFF、无 PUA，且**字节稳定**（decode→encode 原样回来）。

    字节稳定这一条实测零误伤：全语料 47,588 个串里只有 1 种不往返——
    `fa d4 57`（decode 得「昤W」，encode 回去是 `ed b8 57`，cp932 的重复映射所致），
    它其实是 `{ 300 10 4 0 <color>` 里的颜色值 `00 fa d4 57`（0x0057D4FA）被误读。
    """
    if not s or b'\xff' in s:
        return False
    try:
        t = s.decode('cp932')
        if t.encode('cp932') != s:
            return False
    except UnicodeDecodeError:
        return False
    return not any(0xE000 <= ord(c) <= 0xF8FF for c in t)


# 1 字节 token 的歧义：YKS 串无长度前缀、只有 NUL 结尾，所以 `xx 00` 既可能是
# 真·1 字节 token（块定界符 `{`=0x7B / `}`=0x7D），也可能是 u32 的低字节。
# 字节层判据：**看 `xx 00` 之后两字节**——
#   后两字节 == `00 00`  ⇒ 是 u32（高字节为 0），按 u32 取 4 字节；
#   否则               ⇒ 是真 1 字节 token，只吃 2 字节。
# 实证：
#   `0d 00 00 00 | 6e 00 00 00 | 6f 67 67 5c …`  (J_GoodEnd.yks code+3038)
#     贪心取串得 "n"(0x6e)+1735327744(0x676F0000)+"g\sound\…"；
#     正确解 = 13 + 110 + "ogg\sound\…"。后两字节 `00 00` ⇒ 按 u32。✓
#   `54 54 45 00 | b8 0b 00 00 | 7b 00 | 7b 02 00 00 | 43 61 73 65 00 …`
#     (Jade\J1030.yks @2541) ⇒ TTE 3000 / `{` / 635 / Case。后两字节 `7b 02` ⇒ 真 1 字节。✓
# 反例（旧版 MIN_STR=2 一刀切）：会连块定界符一起吞掉，并啃掉紧随其后正文的首字节。
def _one_byte_is_u32(x, i):
    return len(x) >= i + 4 and x[i + 2:i + 4] == b'\x00\x00'


# 纯数值参数的命令：跟在命令名后面的固定个数 u32。若不强制，参数里的字节可能被当成字符串——
# 实证：`SelectMode\0 | 00000000 | fa d4 57 00 | ff ff ff 00 | SelectPosition\0`
# 其中 `fa d4 57` 恰为可解 cp932 的 3 字节，曾被误读成「昤W」（真身是颜色值 0x0057D4FA）。
# 该形态在 58 处 SelectMode 上完全一致（12 字节后必为命令名），故写成表。
NUM_ARGS = {b'SelectMode': 3}


def tokenize(x):
    i, ev = 0, []
    force = 0
    while i < len(x):
        if force > 0 and i + 4 <= len(x):
            ev.append(('N', struct.unpack('<i', x[i:i + 4])[0]))
            i += 4
            force -= 1
            continue
        j = x.find(b'\x00', i)
        if (j > i and all(c >= 0x20 for c in x[i:j]) and is_cp932_ok(x[i:j])
                and not (j - i == 1 and _one_byte_is_u32(x, i))):
            tok = x[i:j]
            ev.append(('S', tok))
            i = j + 1
            if tok in NUM_ARGS:
                force = NUM_ARGS[tok]
            continue
        if i + 4 <= len(x):
            ev.append(('N', struct.unpack('<i', x[i:i + 4])[0]))
            i += 4
            continue
        break
    # 块长常不是 4 的倍数，尾部留 1〜3 个 0x00 补零位（实测 20 个文件残留恰为 `00 00`）
    if i < len(x) and len(x) - i <= 3 and not any(x[i:]):
        i = len(x)
    return ev, i == len(x)


# 系统菜单脚本（非剧本）：内容为 SUBMENUSTART / MouseCase / ETC_CG / Index / Flag 等菜单记录，
# 无剧情正文。按文件名整文件排除，清单在报告里逐条列出。
UI_SCRIPTS = {'bgm.yks', 'cg_extra.yks', 'load.yks', 'memory.yks', 'memo_hide.yks',
              'memo_show.yks', 'start.yks', 'submenu.yks', 'submenu2.yks'}
UI_SCRIPTS = frozenset(s.lower() for s in UI_SCRIPTS)

NAME_CMDS = (b'WindowNameSet', b'WindowsNameSet')


def is_multibyte(v):
    return any(c > 0x7f for c in v)


def classify(ev, k, name_set=None):
    r"""返回 (kind, name, text_bytes)。kind ∈ say/narration/choice/header/name/?

    L0 判据（字节层记录形态，J_GoodEnd.yks 实测）：
      `13 本文`            地の文          （`N:13 | S:みんな今まで口には…`）
      `13 名前 本文`        台詞            （`N:13 | S:廉 | S:「……私はまだ…」`）
      `13 13 15 voice.ogg 13 名前 本文`    带语音的台詞（语音记录插在消息记录之前）
      `13 13 110 se.ogg 本文`              带音效的地の文（语音文件后直接是本文，无 13）
      `Case 本文`           選択肢          （J1030: SelectTTE 3000 { 635 | Case | 話す。）
      `WindowNameSet 日付`  章題/日付ヘッダ （参数实测全为 １０月１６日 / Prologue 一类）
      `StrOut 本文`         地の文
    即：**名前 ⇔ 前 token 为 13 且后 token 为日文串**；本文 ⇔ 前 token 为日文串。

    `13 X Y` 的判别：X 是名札槽。实测 `13` 之前那个 token 的类型分布为
    ASCII(6654) / 数字(43) / 正文串(**仅 1 例**)——唯一那例是 `Takashi\T1411.yks`
    的 `13 正文 正文`（第二条缺 `13` 前缀），故：**`13` 紧跟正文串时，本槽按正文，
    不按名札**。这说明引擎正常编译时时态里 `13` 一定跟在命令/参数之后。
    """
    v = ev[k][1]
    p1 = ev[k - 1] if k >= 1 else None
    nxt = ev[k + 1] if k + 1 < len(ev) else None
    if p1 and p1[0] == 'S' and is_multibyte(p1[1]):
        return ('say', p1[1], v)                       # 前是名前 → 本条是本文
    if p1 and p1[0] == 'N' and p1[1] == 13 and nxt and nxt[0] == 'S' \
            and is_multibyte(nxt[1]):
        p2 = ev[k - 2] if k >= 2 else None
        if p2 and p2[0] == 'S' and is_multibyte(p2[1]):
            return ('narration', None, v)              # 13 紧跟正文 → 本条是缺 13 的正文
        return ('name', None, v)                       # 本条是名札槽，剔除
    if p1 and p1[0] == 'S' and p1[1] == b'Case':
        return ('choice', None, v)
    if p1 and p1[0] == 'S' and p1[1] in NAME_CMDS:
        return ('header', None, v)
    if p1 and p1[0] == 'S' and p1[1] == b'StrOut':
        return ('narration', None, v)
    if p1 and p1[0] == 'N':
        return ('narration', None, v)
    # 兜底：前 token 为 PF（送り待ち）/ 命令的最后一个 ASCII 参数（如 ogg\xxx.ogg）
    # ⇒ 本条就是新节点的本文。实测 415 条全为日文散文，无垃圾。
    return ('narration', None, v)


def name_candidates(code):
    """收集 `13 X Y` 形态里的 X（名札候选），返回 Counter。"""
    import collections
    ev, _ = tokenize(code)
    c = collections.Counter()
    for k, (t, v) in enumerate(ev):
        if t != 'S' or not is_multibyte(v):
            continue
        p1 = ev[k - 1] if k >= 1 else None
        nxt = ev[k + 1] if k + 1 < len(ev) else None
        if p1 and p1[0] == 'N' and p1[1] == 13 and nxt and nxt[0] == 'S' \
                and is_multibyte(nxt[1]):
            c[v] += 1
    return c


def extract_lines(code, name_set=None):
    """返回 (行列表, 是否闭合, 审计表)。行 = (kind, name, text_bytes)，不含 name 行。"""
    ev, closed = tokenize(code)
    out, audit = [], []
    for k, (t, v) in enumerate(ev):
        if t != 'S' or not is_multibyte(v):
            continue
        kind, nm, tx = classify(ev, k, name_set)
        p1 = ev[k - 1] if k >= 1 else None
        if kind != 'name':
            out.append((kind, nm, tx))
        audit.append((kind, p1, v))
    return out, closed, audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dat')
    ap.add_argument('--dump')
    ap.add_argument('--text')
    ap.add_argument('--only', default='')
    ap.add_argument('--audit', action='store_true', help='打印分类审计表')
    a = ap.parse_args()
    f, ents = read_index(a.dat)
    only = [s.strip().lower() for s in a.only.split(';') if s.strip()]
    print('# %s  条目 %d' % (os.path.basename(a.dat), len(ents)))
    if a.dump:
        os.makedirs(a.dump, exist_ok=True)
    lines, bad, skipped_ui = [], [], []
    audit = []
    names = {}
    # ---- pass 1：全语料扫名札候选，取「复现 ≥2 次」者为名札表 ----
    import collections
    cand = collections.Counter()
    keep = []
    for name, off, size in ents:
        low = name.lower()
        if only and not any(s in low for s in only):
            continue
        b = ykc_entry(f, off, size)
        if not low.endswith('.yks'):
            if not a.text:
                print('%9d  %s' % (size, name))
            continue
        if os.path.basename(low) in UI_SCRIPTS:
            skipped_ui.append(name)
            continue
        r = ykS_blocks(b)
        if not r:
            bad.append((name, 'magic'))
            continue
        keep.append((name, r[1], b))
        cand.update(name_candidates(r[1]))
    name_set = set(v for v, c in cand.items() if c >= 2)
    # ---- pass 2 ----
    for name, code, b in keep:
        if a.dump:
            dst = os.path.join(a.dump, name.replace('\\', '_') + '.txt')
            open(dst, 'wb').write(code)
        got, closed, aud = extract_lines(code, name_set)
        if not closed:
            bad.append((name, 'token-not-closed'))
        for kind, p1, tx in aud:
            audit.append((name, kind, p1, tx))
        for kind, nm, tx in got:
            if nm is not None:
                names[nm.decode('cp932')] = names.get(nm.decode('cp932'), 0) + 1
            lines.append((name, kind, tx.decode('cp932')))
    if a.text:
        with open(a.text, 'w', encoding='utf-8-sig', newline='\n') as g:
            for _, _, s in lines:
                g.write(s + '\n')
        print('  行数 %d → %s' % (len(lines), a.text))
        print('  kind:', collections.Counter(k for _, k, _ in lines))
        print('  排除系统菜单脚本 %d: %s' % (len(skipped_ui),
                                        ', '.join(os.path.basename(x) for x in skipped_ui)))
        print('  名札表 %d: %s' % (
            len(name_set), ' '.join(sorted(v.decode('cp932') for v in name_set))))
        print('  仅出现 1 次的名札槽（照剔）: %s' % (
            ' '.join('%s(%dB)' % (v.decode('cp932', 'replace')[:16], len(v))
                     for v, c in cand.items() if c < 2)))
        print('  解析异常:', bad[:10], '共', len(bad))
        if a.audit:
            c = collections.Counter()
            ex = {}
            for fn, kind, _s, tx in audit:
                p1 = _s
                c[kind] += 1
                ex.setdefault(kind, (fn, tx))
            print('  审计:')
            for k, n in c.most_common():
                fn, tx = ex[k]
                print('    %-10s %5d  例 <%s> %s' % (k, n, os.path.basename(fn),
                                                    tx.decode('cp932', 'replace')[:34]))


if __name__ == '__main__':
    sys.exit(main())
