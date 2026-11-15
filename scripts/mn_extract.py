# -*- coding: utf-8 -*-
"""華ヤカ哉、我ガ一族 モダンノスタルジィ for Nintendo Switch（NS-JP, ichicolumn 自研 .lzs + SCD）

TID `01008DE00C022000`。同引擎第 3 例（第 1 例 明治活劇 ハイカラ流星組 / 第 2 例 幻燈ノスタルジィ）。
本作是**单作**（本篇移植）：`Data/SCD/*.lzs` 658 本、`VOICE.IDX` 只有一份、`MAP/SCD_SUB.lzs` 只有一份。

SCD 记录（本作第 3 型）：
  [u16 tag][u16 size(含自身 4B)] 连续；tag 0x10/0x11 = メッセージノード
  payload: +0x04 u32 序号 / +0x08 u16 話者ID / +0x0A u16 ? / +0x0C u16 ?
           +0x0E 起 `<u16 len><utf8>` 连串（**len 不含 NUL**，串后 1B NUL + 0 填充到**绝对 4 字节对齐**）
           串序列 = [ボイスID("-1"/"VC…")][名札][本文]（2 串＝無名札の独白、3 串＝名札あり）
           ⇒ 本文 = **最后一个串**
  全 658 本 `tag/size` 走查闭合、38,622 条消息全部解析成功（零处剩余）

CORE（`Data/CORE.lzs` → 82,662,912 B）里的表（本作のみ、偏移与上作不同）：
  0x4de09ab..0x4de4c0b  `<u32 len><u32 组内序号><utf8>` = **選択肢 286 条**
  0x4e14e00..0x4e15370  `[u32 nlen][u32 type 1..3][名称][pad4][u32 dlen][u32 type][説明][pad4]` = **アイテム 8 条**
  0x4e155d4..            `[u32 ?][u32 ?][u32 1][u32 nlen][名称][pad4][u32 dlen][u32 0][説明]` = 蓄音機の曲名（**収録しない**：音楽鑑賞 UI）
  0x4dd8…               `[u32 id][u32 off][称号名]` 0x30 行 = 称号表（**収録しない**：実績 UI）

本文中の制御: '%'=姓(浅木) '&'=名(はる) '\\'=框内改行(合并) '$'/'#'/'@'=用語・人名マーカー(記号削除)
  ※ 本作に `*`（愛称形）は **0 回**（第 2 例にはあった）
"""
import glob
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meiji_lzs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = r'<本地路径>'
WORK = os.path.join(ROOT, '_w_mn')
OUT = os.path.join(ROOT, '提取结果', '[NS-JP]華ヤカ哉、我ガ一族 モダンノスタルジィ for Nintendo Switch.txt')

SURNAME = '浅木'
GIVEN = 'はる'      # ゲーム内の字面値は無い（名は全部マクロ）。根拠＝CORE 曲名「はるの家」＋vndb『浅木 はる』

MARK = re.compile(r'[$#@]')
JPN = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def scd_bytes(path):
    d = meiji_lzs.decompress(open(path, 'rb').read())
    off, size = struct.unpack_from('<II', d, 4)
    return d[off:off + size]


def nodes(d):
    p = 0
    n = len(d)
    while p + 4 <= n:
        tag, size = struct.unpack_from('<HH', d, p)
        if size < 4 or p + size > n:
            return
        yield p, tag, size
        p += size


def read_strs(d, p, end):
    """`<u16 len><utf8>`（len 不含 NUL）＋ 1B NUL ＋ 0 填充到绝对 4 字节对齐。"""
    out = []
    o = p
    while o + 2 <= end:
        L = struct.unpack_from('<H', d, o)[0]
        if L == 0 or o + 2 + L > end:
            break
        try:
            t = d[o + 2:o + 2 + L].decode('utf-8')
        except UnicodeDecodeError:
            break
        out.append(t.rstrip('\x00'))
        o += 2 + L
        while o % 4 and o < end and d[o] == 0:
            o += 1
    return out


def clean(t):
    t = t.replace('%', SURNAME).replace('&', GIVEN)
    t = t.replace('\\', '')          # 框内改行 → 合并
    t = MARK.sub('', t)              # 用語/人名マーカー
    return t.strip()


def rows_of(path):
    d = scd_bytes(path)
    out = []
    for p, tag, size in nodes(d):
        if tag not in (0x10, 0x11):
            continue
        ss = read_strs(d, p + 14, p + size)
        if not ss:
            continue
        t = clean(ss[-1])
        if t:
            out.append(t)
    return out


def scene_key(name):
    m = re.match(r'EV(\d+)\.SCD$', name)
    return int(m.group(1)) if m else 0


def core_pairs(d, S, E):
    """`[u32 nlen][u32 type(1..9)][名称][pad4][u32 dlen][u32 type][説明][pad4]` 的链式扫描。
    type 不是 1..9 时按 `[u32 nlen][名称]`（蓄音機表の形）解。"""
    out = []
    p = S
    while p < E - 24:
        nlen = struct.unpack_from('<I', d, p)[0]
        if 2 <= nlen <= 120:
            nxt = struct.unpack_from('<I', d, p + 4)[0]
            ns = p + 8 if nxt <= 9 else p + 4
            try:
                nm = d[ns:ns + nlen - 1].decode('utf-8')
            except UnicodeDecodeError:
                nm = None
            if nm and JPN.search(nm) and d[ns + nlen - 1] == 0:
                q = ns + nlen
                while q % 4 and d[q] == 0:
                    q += 1
                dlen, dflag = struct.unpack_from('<II', d, q)
                if 2 <= dlen <= 800 and dflag <= 9:
                    try:
                        ds = d[q + 8:q + 8 + dlen - 1].decode('utf-8')
                    except UnicodeDecodeError:
                        ds = None
                    if ds and JPN.search(ds) and d[q + 8 + dlen - 1] == 0:
                        out.append((p, nm, ds))
                        p = q + 8 + dlen
                        continue
        p += 4
    return out


def choice_recs(d, S, E):
    """選択肢：`<u32 len><u32 組内序号><utf8 len バイト>`（レコード間 0 填充 1〜8B）。
    単串なので core_pairs（名称＋説明の対）では拾えない ⇒ 逐バイト再同期で読む。"""
    def rec(p):
        if p + 12 > E:
            return None
        L, slot = struct.unpack_from('<II', d, p)
        if not (2 <= L <= 400) or slot > 9:
            return None
        try:
            t = d[p + 8:p + 8 + L].decode('utf-8')
        except UnicodeDecodeError:
            return None
        if not t or not JPN.search(t) or any(ord(c) < 0x20 for c in t):
            return None
        return L, t

    out, p = [], S
    while p < E:
        h = rec(p)
        if h:
            out.append(h[1])
            p += 8 + h[0]
            continue
        nxt = None
        for k in range(1, 9):
            if rec(p + k):
                nxt = p + k
                break
        p = nxt if nxt else p + 1
    return out


def choices():
    d = open(os.path.join(WORK, 'CORE'), 'rb').read()
    return choice_recs(d, 0x4de0900, 0x4de4d00)


def item_rows(d, S, E):
    """アイテム表：`[u32 nlen][u32 type 1..3][名称][pad4][u32 dlen][u32 type][説明][pad4]`。
    ★ 行間に 12B の前置き（前レコードの尾部）が混ざるので**跳ばずに全走査＋名称で去重**する
      （跳ぶと誤ヒット 1 件で 8 行まとめて飛び越す：実際に踏んだ）。"""
    out = []
    for p in range(S, E - 24, 4):
        nlen = struct.unpack_from('<I', d, p)[0]
        if not (2 <= nlen <= 120):
            continue
        typ = struct.unpack_from('<I', d, p + 4)[0]
        if typ > 9:
            continue
        ns = p + 8
        try:
            nm = d[ns:ns + nlen - 1].decode('utf-8')
        except UnicodeDecodeError:
            continue
        if not nm or not JPN.search(nm) or d[ns + nlen - 1] != 0:
            continue
        q = ns + nlen
        while q % 4 and d[q] == 0:
            q += 1
        dlen, dflag = struct.unpack_from('<II', d, q)
        if not (2 <= dlen <= 800) or dflag > 9:
            continue
        try:
            ds = d[q + 8:q + 8 + dlen - 1].decode('utf-8')
        except UnicodeDecodeError:
            continue
        if not ds or not JPN.search(ds) or d[q + 8 + dlen - 1] != 0:
            continue
        out.append((p, nm, ds))
    return out


def items():
    d = open(os.path.join(WORK, 'CORE'), 'rb').read()
    rows = item_rows(d, 0x4e14d00, 0x4e15400)
    seen, out = set(), []
    for _, nm, ds in rows:
        if nm in seen:
            continue
        seen.add(nm)
        out.append('【%s】%s' % (nm.replace('\\', ''), ds.replace('\\', '')))
    return out


def main():
    files = sorted(glob.glob(os.path.join(DATA, 'SCD', '*.lzs')), key=lambda f: scene_key(os.path.basename(f)))
    lines = []
    for f in files:
        lines.extend(rows_of(f))
    body = len(lines)
    ch = choices()
    it = items()
    lines.extend(ch)
    lines.extend(it)

    with open(OUT, 'wb') as fp:
        fp.write(b'\xef\xbb\xbf')
        fp.write(('\n'.join(lines) + '\n').encode('utf-8'))

    print('脚本 %d 本 → 正文 %d 行' % (len(files), body))
    print('正文 %d + 选项 %d + アイテム %d = %d 行 -> %s' % (body, len(ch), len(it), len(lines), OUT))


if __name__ == '__main__':
    main()
