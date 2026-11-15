# -*- coding: utf-8 -*-
"""華ヤカ哉、我ガ一族 幻燈ノスタルジィ for Nintendo Switch（NS-JP, ichicolumn 自研 .lzs + SCD）

本 dump 是 **二合一**（官方：『キネマモザイク』＋『黄昏ポウラスタ』）：
  Data/SCD/KM/*.lzs   682 本 → キネマモザイク（＝2年目の話。OP_KM.mp4 / VOICE_KM.IDX）
  Data/SCD/PO/*.lzs   616 本 → 黄昏ポウラスタ（Polarstar＝PO。別荘で拾参日。OP_PO.mp4 / VOICE_PO.IDX）
  Data/SCD_/{KM,PO}/*.SCD  同内容の**非圧縮コピー**（内蔵 SCD と 1210/1298 本が完全一致）
  Data/CORE.lzs → 80.7 MB。選択肢（537）＋アイテム辞典（205）を保持
  Data/DICT/{KM,PO}/SH24_*.DDS は辞典の挿絵（画像のみ・本文なし）

SCD 構造（本作、明治活劇と同系統だが**文字列はパディング付き**）:
  [u16 tag][u16 size] の連続。<u16 size> は自身の 4B を含む。
  tag 0x10/0x11 = メッセージノード:
      +0x04 u32 ボイス連番 / +0x08 u16 話者ID / +0x0A u16 フラグ / +0x0C u16 ?
      +0x0E から <u16 len><utf8> の連続 = [ボイスID文字列][名札][本文][空]
  文字列は **NUL 終端込みの len**、レコード間は 0 パディング（1〜8B）。

本文中の制御: '%'=姓(浅木) '&'=名(はる) '*'=名(はる, 愛称形 `お*ちゃん`/`*吉`)
              '\\'=框内改行(合并) '$'/'#'/'@'=用語・人名マーカー(記号削除)
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
WORK = os.path.join(ROOT, '_w_hy')
OUT = os.path.join(ROOT, '提取结果', '[NS-JP]華ヤカ哉、我ガ一族 幻燈ノスタルジィ for Nintendo Switch.txt')

SURNAME = '浅木'
GIVEN = 'はる'      # ゲーム内の字面値は無い（名は全部マクロ）。根拠は CORE 物品名「はるの家」＋vndb 表記『浅木 はる』

MARK = re.compile(r'[$#@]')


def scd_bytes(path):
    """`.lzs` → 内蔵 SCD（ヘッダ +0x04=offset, +0x08=size）。SCD_ の非圧縮コピーと一致することを確認済み。"""
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
    """`<u16 len><utf8>` の連続。len は NUL 終端込み。"""
    out = []
    o = p
    while o + 2 <= end:
        L = struct.unpack_from('<H', d, o)[0]
        if o + 2 + L > end:
            break
        try:
            t = d[o + 2:o + 2 + L].decode('utf-8')
        except UnicodeDecodeError:
            break
        out.append(t.rstrip('\x00'))
        o += 2 + L
    return out


def clean(t):
    t = t.replace('%', SURNAME).replace('&', GIVEN).replace('*', GIVEN)
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
        if len(ss) < 3:
            continue
        t = clean(ss[2])
        if t:
            out.append(t)
    return out


def scene_key(name):
    m = re.match(r'EV(\d+)\.SCD$', name)
    return int(m.group(1)) if m else 0


# ── CORE：選択肢 ＋ アイテム辞典 ──────────────────────────────
def core_recs(d, S, E):
    """区画内を `[u32 len][u32 ?][utf8]` で走査（レコード間は 0 パディング 1〜8B）。"""
    JPN = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

    def rec(p):
        if p + 12 > len(d):
            return None
        L = struct.unpack_from('<I', d, p)[0]
        if not (2 <= L <= 400):
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
    return core_recs(d, 0x4c34600, 0x4c3d200)      # 537 条（キネマモザイク）


def items():
    """アイテム/小物辞典：224B 行 `[1][1][id][len]` + 名称/+0x60 説明。"""
    d = open(os.path.join(WORK, 'CORE'), 'rb').read()
    JPN = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
    out = []
    for p in range(0, len(d) - 0xE0, 4):
        if struct.unpack_from('<II', d, p) != (1, 1):
            continue
        ident = struct.unpack_from('<I', d, p + 8)[0]
        if not (0 < ident < 0x2000):
            continue
        e = d.find(b'\x00', p + 0x10, p + 0x30)
        if e < 0:
            continue
        try:
            nm = d[p + 0x10:e].decode('utf-8')
        except UnicodeDecodeError:
            continue
        if not nm or not JPN.search(nm[:1]):
            continue
        e2 = d.find(b'\x00', p + 0x60, min(p + 0xE0, len(d)))
        if e2 < 0:
            continue
        try:
            ds = d[p + 0x60:e2].decode('utf-8')
        except UnicodeDecodeError:
            continue
        if not ds or not JPN.search(ds):
            continue
        out.append((p, nm, ds))
    out.sort()
    return ['【%s】%s' % (nm.replace('\\', ''), ds.replace('\\', '')) for _, nm, ds in out]


def sub_rows(tag):
    """`Data/MAP/SCD_SUB_{KM,PO}.lzs` = 女中任務の掛け合い（内蔵 SCD 1 本、9 メッセージずつ）。"""
    d = meiji_lzs.decompress(open(os.path.join(DATA, 'MAP', 'SCD_SUB_%s.lzs' % tag), 'rb').read())
    off, size = struct.unpack_from('<II', d, 4)
    scd = d[off:off + size]
    out = []
    for p, t, sz in nodes(scd):
        if t not in (0x10, 0x11):
            continue
        ss = read_strs(scd, p + 14, p + sz)
        if len(ss) < 3:
            continue
        x = clean(ss[2])
        if x:
            out.append(x)
    return out


def main():
    lines, stat = [], []
    for sub, label in (('KM', 'キネマモザイク'), ('PO', '黄昏ポウラスタ')):
        files = sorted(glob.glob(os.path.join(DATA, 'SCD', sub, '*.lzs')), key=lambda f: scene_key(os.path.basename(f)))
        n = 0
        for f in files:
            rs = rows_of(f)
            lines.extend(rs)
            n += len(rs)
        sb = sub_rows(sub)
        lines.extend(sb)
        stat.append((sub, label, len(files), n, len(sb)))

    body = len(lines)
    ch = choices()
    it = items()
    lines.extend(ch)
    lines.extend(it)

    with open(OUT, 'wb') as fp:
        fp.write(b'\xef\xbb\xbf')
        fp.write(('\n'.join(lines) + '\n').encode('utf-8'))

    for sub, label, nf, n, ns in stat:
        print('%-3s %-10s 脚本 %-4d 行 %-6d 任務 %d' % (sub, label, nf, n, ns))
    print('正文 %d + 选项 %d + アイテム %d = %d 行 -> %s' % (body, len(ch), len(it), len(lines), OUT))


if __name__ == '__main__':
    main()
