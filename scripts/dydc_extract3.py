#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DYNAMIC CHORD Remaster 系列 3 部（Liar-S / KYOHSO / apple-polisher）全文本提取。

同族链路（与 feat.[rêve parfait] 共用）：
  XCI/XCZ → (nsz -D) → XCI → HFS0 手切 secure → Program NCA(Standard/Titlekey) → hactool --romfsdir
    romfs/Data/StreamingAssets/script/script_dialog_ja.hdlg   ← 正文
    romfs/Data/StreamingAssets/script/script_dialog_en.hdlg   ← 键名（未翻译，作分区索引）
  HDLG 表：HLZS(LZSS) → HDGL + count + dataOffset + offsets[]，字符串 NUL 结尾 UTF-8。

分区（en 键名，三作同构）：
  TRANS_M*  菜单占位      → 不收
  TRANS_N*  名札表        → 不收（独立名字窗；成品不加前缀）
  TRANS_S*  系统/UI       → 不收
  TRANS_T*  おやすみ/バカンスストーリー（Remaster 追加读物）→ 收，置末尾
  TRANS_W*  本篇正文      → 收

引擎回声：一条文本框之后常紧跟一条**上文副本**（＝上一框全文，或上一框的某个 <br> 段），
三作共 56 / 67 / 256 条；不剔除则整段重复。

用法:
  python scripts/dydc_extract3.py --romfs _work_dydc/romfs_liars \
      --out "提取结果/[NS-JP]DYNAMIC CHORD feat.Liar-S Remaster edition.txt" \
      --first 仁菜 --last 双海
"""
import argparse
import os
import re
import struct
import sys


# ---------------------------------------------------------------- LZSS (HLZS)
def hlzs_decompress(buf, dec_size):
    dic = bytearray(0x1000)
    out = bytearray()
    flag8 = 1
    ip = 0
    dp = 0
    n = len(buf)
    while ip < n and len(out) < dec_size:
        if flag8 == 1:
            flag8 = buf[ip] | 0x100
            ip += 1
        f = flag8 & 1
        flag8 >>= 1
        if f:
            c = buf[ip]
            ip += 1
            out.append(c)
            dic[dp] = c
            dp = (dp + 1) & 0xFFF
        else:
            low = buf[ip]
            high = buf[ip + 1]
            ip += 2
            wp = (((high & 0xF0) << 4) | low) + 0x12
            ws = (high & 0x0F) + 3
            for i in range(ws):
                c = dic[(wp + i) & 0xFFF]
                out.append(c)
                dic[dp] = c
                dp = (dp + 1) & 0xFFF
    return bytes(out)


def load_hdlg(path):
    raw = open(path, 'rb').read()
    base = raw.find(b'HLZS')
    assert base >= 0, 'no HLZS in %s' % path
    _m, _v, _enc, dec = struct.unpack_from('<4I', raw, base)
    body = hlzs_decompress(raw[base + 0x20:], dec)
    magic, _ver, cnt, dof = struct.unpack_from('<4sIII', body, 0)
    assert magic in (b'HDGL', b'HDLG'), magic
    offs = [struct.unpack_from('<I', body, 0x10 + 4 * i)[0] for i in range(cnt)]
    out = []
    for o in offs:
        p = dof + o
        if p >= len(body):
            out.append(None)
            continue
        e = body.find(b'\x00', p)
        if e < 0:
            e = len(body)
        out.append(body[p:e].decode('utf-8', 'replace'))
    return out


TAG = re.compile(r'<[^>]{1,32}>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--romfs', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--first', required=True, help='主角名（<firstname> 落地）')
    ap.add_argument('--last', required=True, help='主角姓（<lastname> 落地）')
    ap.add_argument('--nick', default='', help='主角昵称（<nickname> 落地）')
    a = ap.parse_args()

    sc = os.path.join(a.romfs, 'Data', 'StreamingAssets', 'script')
    ja = load_hdlg(os.path.join(sc, 'script_dialog_ja.hdlg'))
    en = load_hdlg(os.path.join(sc, 'script_dialog_en.hdlg'))
    assert len(ja) == len(en), (len(ja), len(en))

    W, T = [], []
    for i, k in enumerate(en):
        if not k:
            continue
        if k.startswith('TRANS_W'):
            W.append(ja[i])
        elif k.startswith('TRANS_T'):
            T.append(ja[i])

    macros = {'<firstname>': a.first, '<lastname>': a.last}
    if a.nick:
        macros['<nickname>'] = a.nick

    SYS = re.compile(r'^[^\s]{1,8}　[^\s]{1,8}のENCOREシナリオが追加されました。$')

    def render(t):
        segs = t.split('<br>')
        out = segs[0]
        for seg in segs[1:]:
            # 扉文式：两侧都是拉丁字母/数字时直接相连会粘成词 ⇒ 用全角空格代替该换行
            if re.search(r'[A-Za-z0-9]$', out) and re.match(r'[A-Za-z]', seg):
                out += '\u3000' + seg
            else:
                out += seg
        for k, v in macros.items():
            out = out.replace(k, v)
        out = TAG.sub('', out)          # <sprite=N> / <size=…> / </size> 等富文本剥净
        return out.strip('\n').rstrip()

    def dedupe(seq):
        kept, dropped = [], 0
        for t in seq:
            if t is None:
                continue
            if kept and (t == kept[-1] or t in kept[-1].split('<br>')):
                dropped += 1
                continue
            kept.append(t)
        return kept, dropped

    Wk, Wecho = dedupe(W)
    Tk, Techo = dedupe(T)

    lines, skipped_sys, skipped_empty = [], 0, 0
    for t in Wk + Tk:
        s = render(t or '')
        if not s or s == '\u3000':
            skipped_empty += 1
            continue
        if SYS.match(s):
            skipped_sys += 1
            continue
        lines.append(s)

    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')

    print('[i] HDLG=%d（W=%d / T=%d）' % (len(ja), len(W), len(T)))
    print('[i] 回声副本丢弃 W=%d / T=%d；空/占位 %d；系统通知 %d'
          % (Wecho, Techo, skipped_empty, skipped_sys))
    print('[+] %s 行数=%d' % (a.out, len(lines)))


if __name__ == '__main__':
    main()
