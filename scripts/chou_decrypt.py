#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蝶の毒 華の鎖  XP3 内テキスト復号（区間 XOR 鍵推定）v3

平文(cp932) を 1 バイト XOR。鍵はファイル内で区間一定。
cp932 文字レベル尤度モデルで (head鍵, body鍵, 境界) を推定。byte0 は別鍵のことがある。
"""
import math, collections

def is_lead(c): return (0x81 <= c <= 0x9F) or (0xE0 <= c <= 0xFC)
def ok_trail(c): return (0x40 <= c <= 0x7E) or (0x80 <= c <= 0xFC)

def chars(p):
    i, n = 0, len(p)
    out = []
    while i < n:
        c = p[i]
        if c < 0x80: w = 1
        elif 0xA1 <= c <= 0xDF: w = 1
        elif is_lead(c) and i + 1 < n and ok_trail(p[i + 1]): w = 2
        else: w = 1
        out.append((i, i + w))
        i += w
    return out

class CharModel:
    def __init__(self, corpus):
        cm = collections.Counter()
        for a, b in chars(corpus):
            try: cm[corpus[a:b].decode('cp932')] += 1
            except Exception: pass
        self.cm = cm
        self.tot = sum(cm.values())
        self.floor = math.log(0.02 / max(1, self.tot))

    def charlp(self, ch):
        try: t = ch.decode('cp932')
        except Exception: return self.floor - 5
        o = ord(t[0]) if t else 0
        if o == 0xFFFD or (o < 0x20 and t not in '\r\n\t'): return self.floor - 3
        if 0xFF61 <= o <= 0xFF9F: return self.floor - 2      # 半角カナは本文で稀 → 強ペナルティ
        if o == 0x3000: return self.floor - 2                # 全角空白の連続回避
        return math.log((self.cm.get(t, 0) + 0.5) / (self.tot + 0.5 * len(self.cm) + 10))

    def score(self, p, k):
        pb = bytes(c ^ k for c in p)
        return sum(self.charlp(pb[a:b]) for a, b in chars(pb))

    def prefix(self, buf, k, L):
        pb = bytes(c ^ k for c in buf[:L])
        pre = [0.0] * (L + 1)
        acc = 0.0
        for a, b in chars(pb):
            for j in range(a, b):
                pre[j] = acc
            acc += self.charlp(pb[a:b])
            pre[b] = acc
        return pre


def best_key(cm, seg):
    return max(range(256), key=lambda k: cm.score(seg, k))


def head_key_crib(buf, cm):
    """先验 crib 推定头部键（byte1 以降）。返回 (key, byte0_plain) 或 (None,None)。"""
    n = len(buf)
    if n < 8:
        return None, None
    # ;■--- 型
    k = buf[1] ^ 0x81
    if buf[2] ^ k == 0xA1:
        return k, 0x3B          # byte0 = ';'
    # *start
    k = buf[1] ^ 0x73
    if buf[2] ^ k == 0x74 and buf[3] ^ k == 0x61 and buf[4] ^ k == 0x72 and buf[5] ^ k == 0x74:
        return k, 0x2A          # byte0 = '*'
    return None, None


def head_key_and_b0(buf, cm):
    """头部键＝字符模型 top-1（[1:256]）。byte0 は crib のパターンから決定。"""
    n = len(buf)
    Kh = best_key(cm, buf[1:min(n, 256)])
    b0 = None
    hc, cb0 = head_key_crib(buf, cm)
    if hc is not None and hc == Kh:
        b0 = cb0
    elif buf[2] ^ Kh == 0xA1 and buf[1] ^ Kh == 0x81:
        b0 = 0x3B
    elif bytes(c ^ Kh for c in buf[1:6]) == b'start':
        b0 = 0x2A
    elif bytes(c ^ Kh for c in buf[1:5]) == b'itle':
        b0 = 0x2A
    return Kh, b0


def decode_file(buf, cm, verbose=False):
    n = len(buf)
    if n == 0:
        return b'', []
    Kb = best_key(cm, buf[max(0, n // 3):max(0, n // 3) + 2048])
    Kh, b0 = head_key_and_b0(buf, cm)
    if Kh == Kb or n < 64:
        out = bytearray(c ^ Kb for c in buf)
        if b0 is not None:
            out[0] = b0
        return bytes(out), [(0, n, Kb)]
    L = min(n, 1600)
    ph = cm.prefix(buf, Kh, L)
    pb = cm.prefix(buf, Kb, L)
    # 纯 body 基准
    base = pb[L]
    best = None
    for s in range(0, min(L, 900)):
        v = ph[s] + (pb[L] - pb[s])
        if best is None or v > best[0]:
            best = (v, s)
    s = best[1]
    # 局部精修：分界前后 ±20 用“混合键解整窗”后按字符统一评分（可正确处理跨界双字节）
    if 20 <= s < min(L, 900):
        R = 24
        lo = max(0, s - R); hi = min(n, s + R)
        def mixed(sv):
            seg = bytes(buf[i] ^ (Kh if i < sv else Kb) for i in range(lo, hi))
            return sum(cm.charlp(seg[a:b]) for a, b in chars(seg))
        bs, bv = s, None
        for t in range(max(1, s - 12), min(n - 1, s + 13)):
            v = mixed(t)
            if bv is None or v > bv:
                bv, bs = v, t
        s = bs
    if s < 4 or best[0] <= base + 8:
        out = bytearray(c ^ Kb for c in buf)
        if b0 is not None:
            out[0] = b0
        return bytes(out), [(0, n, Kb)]
    out = bytearray(c ^ Kh for c in buf[:s])
    out += bytes(c ^ Kb for c in buf[s:])
    if b0 is not None:
        out[0] = b0
    return bytes(out), [(0, s, Kh), (s, n, Kb)]


def invalid_positions(out):
    n = len(out); i = 0; bad = []
    while i < n:
        c = out[i]
        if c < 0x80: i += 1
        elif 0xA1 <= c <= 0xDF: i += 1
        elif is_lead(c) and i + 1 < n and ok_trail(out[i + 1]): i += 2
        else: bad.append(i); i += 1
    return bad


def repair_invalid(buf, out, cm):
    """局所的に鍵を差し替えて不正 cp932 を解消（スコア改善が条件）"""
    out = bytearray(out)
    n = len(out)
    for _ in range(4):
        bad = invalid_positions(out)
        if not bad:
            break
        fixed_any = False
        for i in bad:
            lo = max(0, i - 2); hi = min(n, i + 3)
            wlo = max(0, i - 10); whi = min(n, i + 12)
            def sc_of(bb):
                seg = bytes(bb[wlo:whi])
                return sum(cm.charlp(seg[a:b]) for a, b in chars(seg))
            base = sc_of(out)
            best = None
            for k in range(256):
                cand = bytearray(out)
                for j in range(lo, hi):
                    cand[j] = buf[j] ^ k
                sc = sc_of(cand)
                if best is None or sc > best[0]:
                    best = (sc, bytes(cand[lo:hi]))
            if best and best[0] > base:
                out[lo:hi] = best[1]
                fixed_any = True
        if not fixed_any:
            break
    return bytes(out)


def fix_byte0(decoded):
    if not decoded:
        return decoded
    b = bytearray(decoded)
    head2 = ''
    try: head2 = bytes(b[1:3]).decode('cp932')
    except Exception: pass
    if head2.startswith('■'):
        b[0] = 0x3B
    elif bytes(b[1:6]) == b'start':
        b[0] = 0x2A
    elif bytes(b[1:5]) == b'itle':
        b[0] = 0x2A
    return bytes(b)
