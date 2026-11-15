#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Live x Evil 灼熱のエデマ — XP3 读取 + cxdec.tpm 内容层解密

== 容器层（标准 XP3 / zlib 压缩索引）==
  头 11B  b'XP3\\r\\n \\n\\x1a\\x8bg\\x01'（第 6 字节是空格）
  @0x0B   u64 index_offset（绝对）；本作 = 610,646,564
  @idx    u8 flag=1 + u64 compressed_size + u64 original_size + zlib 流
          flag=0 才是「明文索引」（续作 熱砂のプロメテウス 的形态，本作不是）
  闭合    idx + 17 + compressed_size == filesize
  索引内  'File' chunk ×7,519，每含 info / segm / adlr
  segm    28B = {u32 flags; u64 off; u64 orig; u64 stored}
          flags=1 ⇒ 载荷 zlib 压缩（272 段）；flags=0 ⇒ 原样
  adlr    4B，cxdec 密钥派生用 hash，**不是**明文 Adler32（已实证）

== 内容层（cxdec.tpm；与银冠 ginkoku_cx_vm2.py 同族算法结构）==
  历史 decode()：
      bnd = f(hash); h2 = h ^ (h >> 16)
      decode_range(data, 0, bnd, h)         # 前段：常量单字节 XOR
      decode_range(data, bnd, n-bnd, h2)   # 后段：常量单字节 XOR
      # 每段另有 start / end 两个「单点补 XOR」
  本作拿不到插件内存 dump（tpm_mem.bin），不复现密钥派生公式；改用
  「CRLF 已知明文锚点 + 逐位置定值复元」直接定出每文件 (k1, k2, bnd)：

   A) UTF-16LE：明文 CRLF = 0d 00 0a 00
        c[q]^c[q+1]==0x0D and c[q+2]^c[q+3]==0x0A and c[q+1]==c[q+3]==key
   B) cp932/ASCII：明文 CRLF = 0d 0a
        c[q]^c[q+1]==0x07, key = c[q]^0x0D

   ① 全局锚点 key 众数 ⇒ k2（后段占绝大多数行，稳定；误命中被多数淹没）
   ② q<400 的锚点中排除 k2 后的众数 ⇒ k1（前段）
   ③ 只保留 k∈{k1,k2} 的可信锚点，令
        score(i) = 前缀中 k1 个数 + 后缀中 k2 个数
      取 score 最大处为变点 ⇒ bnd 夹在 (前一可信锚点+tail, 后一可信锚点]
   ④ 在该小区间内以「UTF-16 高字节合法率」定 bnd（结构化打分，非穷举码表）
      只查 BAD_RE 会漏掉 CJK 扩展 A 等「看似汉字实为乱码」的字节：
      c04-04.ks 曾把变点选在 1698，后段开头一整串 U+42xx 没被惩罚。
      UTF-16 下 b 只取偶数以保持码元对齐。

  剩余个位坏字符来自 start/end 单点补 XOR（16 位绝对位置、单字节值），
  由「低字节不变 + 高字节合法集合 + 确定性 KAG 串」逐位置定值复元。

用法：python scripts/edema_xp3.py [data.xp3] [输出目录]
"""
import os
import sys
import re
import zlib
import struct
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEF_XP3 = os.path.join(ROOT, "_work_edema", "inno_out", "app", "data.xp3")
DEF_OUT = os.path.join(ROOT, "_work_edema", "xp3_text")
TEXT_EXT = (".ks", ".tjs", ".txt", ".csv", ".ini", ".asd", ".sli", ".scc")
MAGIC = b"XP3\r\n \n\x1a\x8bg\x01"
# 明确非日文字符：控制符 / U+FFFD / 私用区 / 孤立代理 / 韩文 / 西里尔 / 泰文 / 阿拉伯。
# 错 key 解出的字节多落在 CJK 罕见汉字或韩文音节区，只查控制符会让 bnd 打分失去区分力。
BAD_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd\ue000-\uf8ff'
                    r'\uac00-\ud7af\ud800-\udfff\u0400-\u04ff\u0e00-\u0e7f\u0600-\u06ff]')
# UTF-16LE 日文文本中允许出现的高字节（0x00 ASCII / 0x20-0x26 符号 /
# 0x30 假名与全角标点 / 0x4E-0x9F CJK 汉字 / 0xFF 全角英数半角假名）。
# 落在此集合外＝错 key 或单点补 XOR 残留，用于 bnd 打分与事后验收。
H_SET = frozenset([0x00, 0x20, 0x21, 0x25, 0x26, 0x30, 0xFF]) | frozenset(range(0x4E, 0xA0))
L0_NAMES = ['system/MainWindow.tjs', 'system/Config.tjs', 'system/MessageLayer.tjs',
            'scenario/sys_macro.ks', 'scenario/plugin_facewindow.ks', 'scenario/config.ks']


def u64(b, o=0):
    return struct.unpack_from("<Q", b, o)[0]


class XP3:
    def __init__(self, path):
        self.f = open(path, "rb")
        h = self.f.read(64)
        if h[:11] != MAGIC:
            raise RuntimeError("not XP3 (magic mismatch)")
        idx = u64(h, 0x0B)
        self.f.seek(idx)
        meta = self.f.read(17)
        self.flag = meta[0]
        if self.flag == 1:
            comp, orig = struct.unpack_from("<QQ", meta, 1)
            raw = zlib.decompress(self.f.read(comp))
            if len(raw) != orig:
                raise RuntimeError("index size mismatch")
        elif self.flag == 0:
            raw = self.f.read(u64(self.f.read(8)))
        else:
            raise RuntimeError("unknown index flag %d" % self.flag)
        self.entries = {}
        self._parse(raw)

    def _parse(self, raw):
        pos = 0
        while pos + 12 <= len(raw):
            if raw[pos:pos + 4] != b"File":
                break
            sz = u64(raw, pos + 4)
            pos += 12
            pl = raw[pos:pos + sz]
            pos += sz
            q, name, segs, adlr = 0, None, [], None
            while q + 12 <= len(pl):
                t = pl[q:q + 4]
                s = u64(pl, q + 4)
                q += 12
                bd = pl[q:q + s]
                q += s
                if t == b"info":
                    nl = struct.unpack_from("<H", bd, 20)[0]
                    name = bd[22:22 + nl * 2].decode("utf-16-le", "replace")
                elif t == b"segm":
                    for i in range(0, len(bd) - 27, 28):
                        segs.append(struct.unpack_from("<IQQQ", bd, i))
                elif t == b"adlr":
                    adlr = bd
            if name is not None:
                self.entries[name] = (segs, adlr)

    def payload(self, name):
        buf = bytearray()
        for fl, off, orig, stored in self.entries[name][0]:
            self.f.seek(off)
            r = self.f.read(stored)
            buf += zlib.decompress(r) if orig != stored else r
        return bytes(buf)


def anchors16(c):
    """UTF-16LE 的 CRLF：4 字节约束，返回 [(CRLF 起始, key)]，零误命中。"""
    return [(q, c[q + 1]) for q in range(0, len(c) - 3)
            if c[q] ^ c[q + 1] == 0x0D and c[q + 2] ^ c[q + 3] == 0x0A
            and c[q + 1] == c[q + 3]]


def anchors8_all(c):
    """单字节编码的 CRLF：2 字节约束，不过滤（误命中交给众数/变点吸收）。"""
    return [(q, c[q] ^ 0x0D) for q in range(0, len(c) - 1)
            if c[q] ^ c[q + 1] == 0x07]


def xor2(c, k1, k2, b):
    """前 [0,b) 用 k1、[b,n) 用 k2 的单字节 XOR。"""
    d = bytearray(c)
    for i in range(min(b, len(d))):
        d[i] ^= k1
    for i in range(b, len(d)):
        d[i] ^= k2
    return bytes(d)


def to_text(d, mode):
    if mode == "utf16":
        return d.decode("utf-16-le", "replace").lstrip("\ufeff")
    return d.decode("cp932", "replace")


def decode(name, c):
    """返回 (mode, text, k1, k2, bnd, bad_chars)。全部参数来自 CRLF 已知明文锚点。"""
    a16 = anchors16(c)
    mode = "utf16" if a16 else "cp932"
    hs, tail = (a16, 4) if mode == "utf16" else (anchors8_all(c), 2)
    if not hs:
        t = to_text(c, mode)
        return mode, t, 0, 0, 0, len(BAD_RE.findall(t))
    # ① 前段 key：文件头部 1000B 内锚点众数（按位置定值）
    head = [k for q, k in hs if q < 1000]
    k1 = collections.Counter(head).most_common(1)[0][0] if head else 0
    # ② 后段 key：文件尾部 1500B 内锚点众数
    #    禁全局众数：短文件前段行数可能反超后段，会把 k1/k2 整个对调
    tail_a = [k for q, k in hs if q >= max(0, len(c) - 1500)]
    k2 = collections.Counter(tail_a).most_common(1)[0][0] if tail_a else k1
    # ③ 可信锚点变点
    trust = [(q, k) for q, k in hs if k in (k1, k2)] or hs
    nB = sum(1 for _, k in trust if k == k2)
    best, nA, nBs = (-1, 0), 0, nB
    for i, (q, k) in enumerate(trust):
        if nA + nBs > best[0]:
            best = (nA + nBs, i)
        if k == k1:
            nA += 1
        else:
            nBs -= 1
    i = best[1]
    lo = trust[i - 1][0] + tail if i > 0 else 0
    hi = trust[i][0] if i < len(trust) else len(c)
    if hi < lo:
        lo, hi = hi, lo
    hi = min(hi, lo + 512)          # 安全上限，防异常宽区间
    # ④ 小区间内结构化定 bnd（UTF-16 用高字节合法率，b 取偶数保持码元对齐）
    def score(b):
        d = xor2(c, k1, k2, b)
        t = to_text(d, mode)
        nb = len(BAD_RE.findall(t))
        if mode == 'utf16':
            bad_hi = sum(1 for i in range(2, len(d) - 1, 2)
                         if d[i + 1] not in H_SET)   # 跳过 FF FE BOM
            return -(bad_hi + 20 * nb)
        return -nb
    step = 2 if mode == 'utf16' else 1
    start = lo if lo % step == 0 else lo + (step - lo % step)
    bb, bn = start, None
    for b in range(start, hi + 1, step):
        s = score(b)
        if bn is None or s > bn:
            bn, bb = s, b
    t = to_text(xor2(c, k1, k2, bb), mode)
    return mode, t, k1, k2, bb, len(BAD_RE.findall(t))


def main():
    xp3 = sys.argv[1] if len(sys.argv) > 1 else DEF_XP3
    out = sys.argv[2] if len(sys.argv) > 2 else DEF_OUT
    os.makedirs(out, exist_ok=True)
    x = XP3(xp3)
    names = sorted(n for n in x.entries if n.lower().endswith(TEXT_EXT))
    stat = collections.Counter()
    bad = []
    for n in names:
        c = x.payload(n)
        mode, t, k1, k2, b, nb = decode(n, c)
        stat[mode] += 1
        if nb:
            bad.append((n, nb))
        rel = n.replace("\\", "/")
        if len(os.path.basename(rel)) > 120:
            rel = os.path.join(os.path.dirname(rel), "protected_archive_warning.txt")
        p = os.path.join(out, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as g:
            g.write(t)
    print("xp3 members", len(x.entries), "| text files", len(names))
    print("encoding", dict(stat))
    print("files with bad chars", len(bad), "| total bad chars", sum(v for _, v in bad))
    print("worst", sorted(bad, key=lambda z: -z[1])[:12])
    ks_bad = [(n, v) for n, v in bad if n.startswith("scenario/") and n.endswith(".ks")]
    print("scenario .ks bad files", len(ks_bad), "| total", sum(v for _, v in ks_bad))
    for n in L0_NAMES:
        if n not in x.entries:
            continue
        mode, t, k1, k2, b, nb = decode(n, x.payload(n))
        print("L0", n, mode, "k", hex(k1), hex(k2), "bnd", b, "bad", nb,
              "head", repr(t[:70]))
    x.f.close()


if __name__ == "__main__":
    main()
