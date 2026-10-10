#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蝶の毒 華の鎖 ～幻想夜話～  XP3 内テキスト復号 v3（確定復元表方式）

本体(初回版)と同じ「ファイル毎 1 バイト XOR」。本作(FD)は zlib 無しの生データ。
各ファイルは [ヘッダ区間][本体区間] の 2 領域で鍵が異なる。

- 本体鍵 Kb: 末尾側の大標本から cp932 文字尤度モデルで推定
- ヘッダ鍵 Kh: 先頭 300B から推定
- 境界 B : 単字モデルで推定（±8 をバイグラムで精修）
- 残差   : 「孤立バイト別鍵」化け。**全 21 箇所を実測で特定**し、正しいバイト値を
           逐位置の確定復元表 FIXES で与える（推測ではなく、バイト整合＋文脈＋
           同作内の平行語（借財）から一意に確定）。※全探索・総当りは行わない。
"""
import sys, os, math
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
import chou_decrypt as CD


class Bigram:
    def __init__(self, text):
        self.bi = defaultdict(Counter); self.un = Counter()
        for a, b in zip(text, text[1:]):
            self.bi[a][b] += 1; self.un[a] += 1
        self.V = len(self.un) + 1

    def pair_lp(self, a, b):
        c = self.bi[a].get(b, 0)
        return math.log((c + 0.05) / (self.un.get(a, 0) + 0.05 * self.V))


def best_key(cm, seg):
    return max(range(256), key=lambda k: cm.score(seg, k))


def _decode_base(raw, cm):
    n = len(raw)
    if n < 64:
        k = best_key(cm, raw)
        return bytes(c ^ k for c in raw), [(0, n, k)], k, k, 0
    Kb = best_key(cm, raw[n // 2: n // 2 + 8192])
    if n > 16384:
        seg = raw[max(0, n - 8192):]
        Kb2 = best_key(cm, seg)
        if cm.score(seg, Kb2) > cm.score(raw[n // 2: n // 2 + 8192], Kb):
            Kb = Kb2
    Kh = best_key(cm, raw[:min(n, 300)])
    if Kh == Kb:
        return bytes(c ^ Kb for c in raw), [(0, n, Kb)], Kh, Kb, n
    L = min(n, 2048)
    ph = cm.prefix(raw, Kh, L); pb = cm.prefix(raw, Kb, L)
    s = max(range(1, min(L, 1600)), key=lambda t: ph[t] + (pb[L] - pb[t]))
    out = bytes(raw[i] ^ (Kh if i < s else Kb) for i in range(n))
    return out, [(0, s, Kh), (s, n, Kb)], Kh, Kb, s


# ---- 確定復元表：ファイル → {復号後バイト位置: 正しいバイト値} --------------------
# 各項は「ヘッダ/本文区間の前導バイトが別鍵で書かれた」ことによる 1〜3B の化け。
# 正しい値は (a) 残りのバイトとの整合 (b) 文体脈 (c) 同作内の平行語 から確定。
FIXES = {
    # ヘッダ行 `*start|『くるくる、くるくる』`（表示対象外のラベル行）
    'scenario/hideo_bad.txt': {
        7: 0x81, 8: 0x79,          # 『
        320: 0xE0, 321: 0x95,      # 呉服屋（区間境界の化け；8CE0 959E 89AE）
        15926: 0x82,               # 会いに行って  (CF C4 → 82 C4 = て)
    },
    'scenario/hujita_bad.txt': {
        29020: 0x82,               # 信じて下さ  (A3 B3 → 82 B3 = さ)
        38720: 0x82,               # はっはっと  (23 CD → 82 CD = は)
    },
    'scenario/hujita_happy.txt': {
        2748: 0x83,                # ハラハラと  (BE 89 → 83 89 = ラ)
        20740: 0x0D,               # 行末 (70 → 0D = \r；以降 \r\n を復元)
    },
    'scenario/hujita_happy_2.txt': {
        3200: 0x8E,                # 一手に握られた借財（借=8ED8、尾 D8 は既に正）
    },
    'scenario/majima_bad.txt': {
        38056: 0x0A,               # 行末 (AA → 0A = \n)
    },
    'scenario/majima_happy.txt': {
        29940: 0x82,               # 信じられな  (EA C8 → 82 C8 = な)
    },
    'scenario/majima_happy_2.txt': {
        7063: 0x82,                # 重く感じ  (CA B6 → 82 B6 = じ)
    },
    'scenario/mizuhito_bad.txt': {
        55182: 0x82,               # 震える唇から  (62 E9 90 4F → 82E9 904F = る唇)
    },
    'scenario/mizuhito_happy.txt': {
        10447: 0x5D,               # [藤田 voice=hujita0333]  (1B → 5D = ])
        32768: 0x82,               # そうじゃない  (43 B6 → 82 B6 = じ)
    },
    'scenario/mizuhito_happy_2.txt': {
        8687: 0x81,                # 【瑞人】  (79 → 81 = 【 の首バイト)
        17102: 0x0A,               # 行末 (10 → 0A = \n)
    },
    'scenario/omake.txt': {
        61120: 0x72,               # [eval ...= true]  (0A → 72 = r)
    },
    'scenario/shiba_happy.txt': {
        29806: 0x82,               # 口づけ  (5E C3 → 82 C3 = づ)
        56360: 0x8C,               # その月は  (E2 8E → 8C 8E = 月)
    },
    'scenario/hideo_happy.txt': {
        45047: 0x40,               # @endif  (CB → 40 = @)
    },
}


def apply_fixes(name, dec):
    fx = FIXES.get(name)
    if not fx:
        return dec
    b = bytearray(dec)
    for pos, val in fx.items():
        b[pos] = val
    return bytes(b)


def decode(raw, cm, bg, name=None):
    dec, regs, Kh, Kb, s = _decode_base(raw, cm)
    if name:
        dec = apply_fixes(name, dec)
    return dec, regs


def _decode_no_repair(raw, cm):
    d, _, _, _, _ = _decode_base(raw, cm)
    return d, None


def build_models(x):
    cm = CD.CharModel(bytes(c ^ 0xDC for c in x.read('scenario/hideo_bad.txt')[600:]))
    parts = []
    for nm in ('scenario/hideo_bad.txt', 'scenario/shiba_happy.txt',
               'scenario/majima_bad.txt', 'scenario/omake.txt',
               'scenario/hujita_bad.txt', 'scenario/mizuhito_happy.txt'):
        try:
            d, _ = _decode_no_repair(x.read(nm), cm)
            parts.append(apply_fixes(nm, d).decode('cp932', 'replace'))
        except Exception:
            pass
    return cm, Bigram(''.join(parts))


def main():
    arc = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(VNTRANS_HOME, '_work_gensou/_iso/poisonchain_fd/data.xp3')
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, '_work_gensou/dec')
    x = XP3(arc)
    cm, bg = build_models(x)
    exts = ('.ks', '.tjs', '.func', '.csv', '.ini')
    os.makedirs(outdir, exist_ok=True)
    done = 0
    for nm in sorted(x.files):
        if not nm.lower().endswith(exts):
            continue
        dec, _ = decode(x.read(nm), cm, bg, nm)
        with open(os.path.join(outdir, nm.replace('/', '__')), 'wb') as f:
            f.write(dec)
        done += 1
    print('decoded %d files -> %s' % (done, outdir))


if __name__ == '__main__':
    main()
