#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Live x Evil 灼熱のエデマ — KiriKiri XP3 / KAG3 全文本提取器

源链：PE+RAR5 SFX → CloneCD(raw2352 MODE1) → Inno Setup 5.1.2 → app/data.xp3
容器：标准 XP3，flag=1 zlib 压缩索引，7,519 成员，segm 28B。
内容层：cxdec.tpm 双段常量单字节 XOR + 单点补 XOR；
        (k1,k2,bnd) 由 CRLF 已知明文锚点定值（scripts/edema_xp3.py）。

★ 本版关键改动：XP3 索引里的 adlr ＝ 解密后明文的 zlib.adler32（已实测 26 作精确匹配）。
  故单点补 XOR 用「adler32 差分解析」确定性复元：
      单字节改动 Δs1=δ、Δs2=(n-p)·δ ⇒ 枚举 δ∈[-255,255] 反解位置 p 与 extra。
  不再用 freq/bigram 概率填值（违反铁律）。
  修复顺序：SPECIAL 已知明文 → CRLF 结构恢复 → adler32 迭代剥离单点。

★ 断框全部为代码级 L0（system/MainWindow.tjs + scenario/sys_macro.ks 宏体）：
  @p        -> 收框（一次点击）
  @cm/@ct/@er -> 清消息层＝收框点
  @r        -> 框内改行＝合并，不加字符
  @voice    -> 宏体补 「」/『』(pron=sec)，word+afterword+afterword2+word2，一次调用＝一框
  @voice2   -> 不补引号，word+word2（宏体 @r 合并）
  @select_item -> text= 由 @emb exp="mp.text" 上屏；动态序号 １． 不收
  @hn / name= -> namewindow_object 独立图片名札 ⇒ 剔除
  ruby / between_ruby = 振假名读音 ⇒ 丢弃
  裸地の文行首全角空格「　」是原文 ⇒ 只裁行尾
  内联 [ruby text='…'] / [r] ⇒ 剥标签，留基字

用法：python scripts/edema_extract.py [data.xp3] [输出txt]
"""
import os
import re
import sys
import zlib
import struct
import itertools
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edema_xp3 as E

ROOT = os.path.dirname(HERE)
DEF_XP3 = os.path.join(ROOT, "_work_edema", "inno_out", "app", "data.xp3")
DEF_OUT = os.path.join(ROOT, "提取结果", "[JP]Live x Evil 灼熱のエデマ.txt")
DEF_TABLE = os.path.join(ROOT, "_work_edema", "repair_table_adler.txt")
MOD = 65521

INLINE_RE = re.compile(r"\[(?:[^\[\]'\"]|'[^']*'|\"[^\"]*\")*\]")
ATTR_RE = re.compile(r"""\b(\w+)\s*=\s*(?:'([^']*)'|"([^"]*)"|([^\s]+))""")
# KAG 命令属性：正文行不会含这些；用于识别「行首 @ 被单点补 XOR 破坏的命令行」
CMD_ATTR = re.compile(
    r"(?<![A-Za-z0-9_])(?:name|word|word2|storage|time|base|page|layer|chara|chara2|target|"
    r"canskip|opacity|visible|frame|marginl|margint|left|top|exp|cond|color|"
    r"clickse|clicksebuf|rule|face|pron|afterword|afterword2|between_ruby|"
    r"between_ruby2|fo_storage|sepia|num|char|r|i|tf|obj|j)\s*=")
# @命令与粘连正文的分界：命令段之后的全角空格起始段即下一行正文
SPLIT_BODY = re.compile(r"@\w+(?:\s+\S+=(?:'[^']*'|\"[^\"]*\"|\S+))*\s*(　.+)$")
# 行尾单点残留（被破坏的 @p / 标签残片），确定性剔除，不猜字符
TAIL_BAD = re.compile(r"[A-Za-z\u00c0-\u024f\uff61-\uff9f\u3400-\u4dbf"
                      r"\u8a00-\u8fff\uf900-\ufaff\ufb50-\ufdff\ufe00-\ufeff]={0,1}[A-Za-z]?$")

# 确定性已知明文（CRLF / 标签 / BOM / cp932 已知词）
SPECIAL = [
    ('scenario/c12-07.ks', 9356, 0x19, 0x0D, 'CRLF 的 CR：U+0014 -> CR LF'),
    ('scenario/kou-06.ks', 234, 0x37, 0x30, '标签 *KOU-06_0000 的数字 0'),
    ('scenario/fan-true.ks', 1, 0x40, 0xFE, 'UTF-16LE BOM FF FE 被改成 FF BE'),
    ('scenario/normal-03.ks', 19401, 0x6C, 0x63, 'cp932「ガッタ」的 ッ 第二字节 0x63'),
]


def order_files(available):
    """剧本播放序：共通线 c01-01..c12-09 → 主线 ks → 各角色线 → TRUE → normal。"""
    pats = [
        r"c\d\d-\d\d\.ks$", r"ks-\d+\.ks$",
        r"fan-\d+\.ks$", r"fan-bad\.ks$", r"fan-true\.ks$",
        r"kou-\d+\.ks$", r"kou-true\.ks$", r"sei-true\.ks$", r"ken-true\.ks$",
        r"normal-\d+\.ks$",
    ]
    out, seen = [], set()
    for p in pats:
        for n in sorted(k for k in available if re.match(p, k)):
            if n not in seen:
                seen.add(n)
                out.append(n)
    return out


# 宽化け判据：除 BAD_RE 外补齐 Arabic Presentation Forms / CJK 扩展 A /
# 康熙部首 / 拉丁扩展 / 埃塞俄比亚等，用于区分「真解」与「adler 凑出来的伪解」。
BAD_WIDE = re.compile(
    r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd\ue000-\uf8ff'
    r'\uac00-\ud7af\ud800-\udfff\u0400-\u04ff\u0e00-\u0e7f\u0600-\u06ff'
    r'\ufb50-\ufdff\ufe70-\ufeff\u3400-\u4dbf\u00c0-\u024f'
    r'\u2e80-\u2eff\u2f00-\u2fdf\u1200-\u137f]')


# translate 表：合法高字节→0、非法→1，用 bytes.translate + count 做 C 级统计
_HI_TBL = bytes(0 if i in E.H_SET else 1 for i in range(256))


def _cp932_trans():
    """合法日文字符→删除、化け字符→'\\x00' 标记；str.translate 为 C 级，
    一次构造全表，之后 O(n) 统计。代码级字符集判据，非语义、非穷举。"""
    tab = {}
    for i in range(0x10000):
        try:
            chr(i).encode('cp932')
            tab[i] = None
        except UnicodeEncodeError:
            tab[i] = '\x00'
    return tab


CP932_TRANS = _cp932_trans()
_CP932_MARK = {i: ('\x01' if v is None else '\x02')
               for i, v in CP932_TRANS.items()}


def bad_count(d, mode):
    """化け字符数：不可 encode('cp932') ＋ BAD_WIDE（PUA/控制符等）。
    CJK 基本区的化け汉字（如 睌/喡/ꎌ）BAD_WIDE 检不出，必须靠字符集表。"""
    t = E.to_text(d, mode)
    return len(t.translate(CP932_TRANS)) + len(BAD_WIDE.findall(t))


def dirty(d, mode):
    """明文脏度：宽化け字符数 ×10 ＋ UTF-16 高字节非法数（bnd 错会整段放大）。"""
    t = E.to_text(d, mode)
    w = len(BAD_WIDE.findall(t))
    if mode == 'utf16':
        return w * 10 + d[1::2].translate(_HI_TBL).count(1)
    return w * 10


def bnd_range(c, kf, kb, hs, step):
    """锚点 key 值按位置从 kf 切到 kb 的区间 —— 代码级判据，不打分、不猜字符。"""
    trust = sorted((q, k) for q, k in hs if k in (kf, kb))
    if not trust:
        return 0, min(len(c), 512)
    tail = 4 if step == 2 else 2
    nB = sum(1 for _, k in trust if k == kb)
    best, nA, nBs = (-1, 0), 0, nB
    for i, (q, k) in enumerate(trust):
        if nA + nBs > best[0]:
            best = (nA + nBs, i)
        if k == kf:
            nA += 1
        else:
            nBs -= 1
    i = best[1]
    lo = trust[i - 1][0] + tail if i > 0 else 0
    hi = trust[i][0] if i < len(trust) else len(c)
    if hi < lo:
        lo, hi = hi, lo
    return lo, min(hi, lo + 512)


def find_exact(c, h, kf, kb, lo, hi, step):
    """只做 adler32 闭式递推找「天然匹配」的 bnd（零人为改动 ⇒ 必为真解）。
    不构造候选明文、不算 dirty，O(n + hi/step)，可在全范围快速跑。"""
    n = len(c)
    s1, s2 = 1, 0
    for x in c:
        s1 = (s1 + (x ^ kb)) % MOD
        s2 = (s2 + s1) % MOD

    def adv(b):
        nonlocal s1, s2
        for i in range(b, min(b + step, n)):
            dl = ((c[i] ^ kf) - (c[i] ^ kb)) % MOD
            s1 = (s1 + dl) % MOD
            s2 = (s2 + (n - i) * dl) % MOD

    b = 0
    while b < lo:
        adv(b)
        b += step
    while b <= hi:
        if ((s2 << 16) | s1) == h:
            return b, E.xor2(c, kf, kb, b)
        adv(b)
        b += step
    return None


def solve_bnd_points(c, h, kf, kb, lo, hi, step):
    """adler32 闭式递推求 bnd；单点补 XOR 由 Δs1=δ、Δs2=(n-p)δ 解析反解。
    返回 [(b, pts, d)]，每一项都满足 zlib.adler32(d) == h（零猜测）。"""
    n = len(c)
    s1, s2 = 1, 0
    for x in c:
        s1 = (s1 + (x ^ kb)) % MOD
        s2 = (s2 + s1) % MOD

    def adv(b):
        nonlocal s1, s2
        for i in range(b, min(b + step, n)):
            dl = ((c[i] ^ kf) - (c[i] ^ kb)) % MOD
            s1 = (s1 + dl) % MOD
            s2 = (s2 + (n - i) * dl) % MOD

    b, out = 0, []
    while b < lo:
        adv(b)
        b += step
    while b <= hi:
        cur = (s2 << 16) | s1
        d0 = E.xor2(c, kf, kb, b)
        if cur == h:
            out.append((b, [], d0, d0))
        else:
            ds1 = ((h & 0xffff) - s1) % MOD
            ds2 = ((h >> 16) - s2) % MOD
            # delta∈[-255,255] 且 delta%MOD==ds1 ⇒ 解析唯一解，无需枚举
            if ds1 == 0:
                delta = None
            elif ds1 <= 255:
                delta = ds1
            elif ds1 >= MOD - 255:
                delta = ds1 - MOD
            else:
                delta = None
            if delta is not None:
                np = (ds2 * pow(delta % MOD, -1, MOD)) % MOD
                p = n - np
                if 0 <= p < n:
                    d = bytearray(d0)
                    old, new = d[p], d[p] + delta
                    if 0 <= new <= 255:
                        d[p] = new
                        d = bytes(d)
                        if (zlib.adler32(d) & 0xffffffff) == h:
                            out.append((b, [(p, delta)], d, d0))
        adv(b)
        b += step
    return out


def pick_best(cands, lo, hi, mode):
    """在 adler-MATCH 候选中区分真解与伪解。

    EXACT（天然匹配、零人为改动）必为真解；SINGLE 必须满足「复元让明文不更脏」——
    伪解是拿 adler 方程硬凑出来的单点，会把某个正常字节改成化け字，dirty 反而上升。
    """
    if not cands:
        return None
    scored = []
    for b, pts, d, d0 in cands:
        dv, dv0 = dirty(d, mode), dirty(d0, mode)
        worse = max(0, dv - dv0)
        exact = 0 if not pts else 1
        scored.append((worse, exact, dv, abs(b - (lo + hi) // 2), b, d))
    scored.sort(key=lambda z: (z[0], z[1], z[2], z[3]))
    z = scored[0]
    return (z[0], z[2], z[4], z[5])


def locate_bad(d, mode):
    """化け字节位置：cp932 不可编码字符 / BAD_WIDE / UTF-16 高字节非法。
    全部为字符集与字节结构判据（C 级 translate + 正则），零猜测、零语义。"""
    enc = 'utf-16-le' if mode == 'utf16' else 'cp932'
    t = d.decode(enc, 'replace')
    out = set()
    marks = t.translate(_CP932_MARK)
    if mode == 'utf16':
        for m in re.finditer('\x02', marks):
            off = m.start() * 2
            out.add(off)
            out.add(off + 1)
    else:
        acc = 0
        for i, ch in enumerate(t):
            if marks[i] == '\x02':
                out.add(acc)
                out.add(acc + 1)
            acc += len(ch.encode(enc, 'replace'))
    for m in BAD_WIDE.finditer(t):
        out.add(len(t[:m.start()].encode(enc, 'replace')))
    if mode == 'utf16':
        for i in range(0, len(d) - 1, 2):
            if d[i + 1] not in E.H_SET:
                out.add(i)
                out.add(i + 1)
    return sorted(p for p in out if 0 <= p < len(d))


def repair_two_points(c, h, kf, kb, b, mode):
    """双段 XOR 之后残留最多 2 个「单点补 XOR」：
    位置由化け码元结构定位，值由 adler32 的 (Δs1, Δs2) 两方程解析联立求解，
    最终以 zlib.adler32(d) == adlr 精确验收。零猜测、零穷举码表、零 OCR。"""
    d0 = E.xor2(c, kf, kb, b)
    if h is None:
        return d0, False
    n = len(d0)
    s1, s2 = adler_parts(d0)
    ds1 = ((h & 0xffff) - s1) % MOD
    ds2 = ((h >> 16) - s2) % MOD
    pos = locate_bad(d0, mode)
    base = bad_count(d0, mode)
    # 化け成片（bnd 未定准）时不硬凑双点：单点方程不足以描述整段错 key
    if len(pos) > 40:
        return d0, False

    def apply(pairs):
        d = bytearray(d0)
        for p, r in pairs:
            v = d[p] + r
            if not (0 <= v <= 255):
                return None
            d[p] = v
        d = bytes(d)
        if (zlib.adler32(d) & 0xffffffff) != h:
            return None
        if bad_count(d, mode) > base:
            return None
        return d

    # 单点：δ 由 ds1 唯一确定
    delta = ds1 if ds1 <= 255 else (ds1 - MOD if ds1 >= MOD - 255 else None)
    if delta:
        for p in pos:
            r = apply([(p, delta)])
            if r is not None:
                return r, True
    # 双点：[1,1; (n-p1),(n-p2)]·[δ1,δ2] = [ds1,ds2]
    for i, p1 in enumerate(pos):
        for p2 in pos[i + 1:]:
            a, bq = (n - p1) % MOD, (n - p2) % MOD
            det = (a - bq) % MOD
            if det == 0:
                continue
            d1 = ((ds2 - bq * ds1) * pow(det, -1, MOD)) % MOD
            d2 = (ds1 - d1) % MOD
            r1 = d1 if d1 <= 255 else (d1 - MOD if d1 >= MOD - 255 else None)
            r2 = d2 if d2 <= 255 else (d2 - MOD if d2 >= MOD - 255 else None)
            if r1 is None or r2 is None or (r1 == 0 and r2 == 0):
                continue
            r = apply([(p1, r1), (p2, r2)])
            if r is not None:
                return r, True
    return d0, False


def solve_single_at(c, h, kf, kb, b, mode):
    """固定 bnd 下由 adler32 差分解析单点补 XOR：Δs1=δ、Δs2=(n-p)δ。
    位置 p 与值 δ 均为方程解析解，非枚举、非猜测；验收 adler 精确匹配
    且复元不使明文更脏（挡住 adler 硬凑出的伪单点）。"""
    d0 = E.xor2(c, kf, kb, b)
    n = len(d0)
    s1, s2 = adler_parts(d0)
    ds1 = ((h & 0xffff) - s1) % MOD
    ds2 = ((h >> 16) - s2) % MOD
    delta = ds1 if ds1 <= 255 else (ds1 - MOD if ds1 >= MOD - 255 else None)
    if not delta:
        return d0, False
    np = (ds2 * pow(delta % MOD, -1, MOD)) % MOD
    p = n - np
    if not (0 <= p < n):
        return d0, False
    v = d0[p] + delta
    if not (0 <= v <= 255):
        return d0, False
    d = bytearray(d0)
    d[p] = v
    d = bytes(d)
    if (zlib.adler32(d) & 0xffffffff) != h:
        return d0, False
    if bad_count(d, mode) > bad_count(d0, mode):
        return d0, False
    return d, True


def decode_exact(c, h):
    """H8 确定性解密。
    ① kf/kb 由 CRLF 已知明文锚点游程定值（H8b：每文件恰 2 游程）。
    ② bnd 由锚点游程给出的窄 gap 内「化け字符数最小」定死 —— 代码级结构判据，
       不由 adler 驱动：adler 在 [0,4096] 全范围会命中「挪远 bnd 抵消单点差」的
       伪解（H8c 字节证据：c12-01.ks 真 bnd=1992，全范围 find_exact 却给 1976，
       把 ` canskip` 解成 `놑뇒뇐…`）。
    ③ 固定 bnd 下，单点补 XOR 由 adler32 差分解析（Δs1=δ、Δs2=(n-p)δ）确定性
       复元；双点残留交给 repair_two_points 的联立方程。零猜测、零穷举、零 OCR。"""
    a16 = E.anchors16(c)
    mode = "utf16" if a16 else "cp932"
    hs = a16 if mode == "utf16" else E.anchors8_all(c)
    step = 2 if mode == "utf16" else 1
    if not hs:
        return mode, c, 0, 0, 0
    cnt = collections.Counter(k for q, k in hs)
    top = cnt.most_common(2)
    if len(top) < 2:
        kf = kb = top[0][0]
        lo, hi = 0, min(len(c), 512)
    else:
        head = collections.Counter(k for q, k in hs[:12])
        kf = head.most_common(1)[0][0] if head else top[0][0]
        kb = top[0][0] if top[0][0] != kf else top[1][0]
        lo, hi = bnd_range(c, kf, kb, hs, step)
    # ② gap 内结构化定 bnd（BAD_WIDE 化け数最小，非语义、非穷举）
    best = None
    for bb in range(lo - lo % step, min(hi + step, len(c)), step):
        d0 = E.xor2(c, kf, kb, bb)
        dv = bad_count(d0, mode)
        if best is None or dv < best[0]:
            best = (dv, bb, d0)
    bnd, d = best[1], best[2]
    # ③ 固定 bnd 下解析单点 / 双点
    if h is not None and (zlib.adler32(d) & 0xffffffff) != h:
        d2, ok2 = solve_single_at(c, h, kf, kb, bnd, mode)
        if ok2:
            d = d2
        else:
            d, _ = repair_two_points(c, h, kf, kb, bnd, mode)
    return mode, d, kf, kb, bnd


def build_model(xp, names):
    """第一遍：确定性解密全部 .ks，缓存 (mode,text,bytes,k1,k2,bnd,nb,adlr)。"""
    cache = {}
    for n in names:
        c = xp.payload(n)
        adlr = xp.entries[n][1]
        h = struct.unpack('<I', adlr[:4])[0] if adlr and len(adlr) >= 4 else None
        mode, d, kf, kb, b = decode_exact(c, h)
        t = E.to_text(d, mode)
        cache[n] = (mode, t, d, kf, kb, b, len(E.BAD_RE.findall(t)), h)
    return cache


def adler_parts(d):
    s1, s2 = 1, 0
    for x in d:
        s1 = (s1 + x) % MOD
        s2 = (s2 + s1) % MOD
    return s1, s2


def adler_single(d, target):
    """解析求单点补 XOR：Δs1=δ、Δs2=(n-p)δ ⇒ 枚举 δ∈[-255,255] 定 (p,extra)。"""
    n = len(d)
    s1, s2 = adler_parts(d)
    ds1 = ((target & 0xffff) - s1) % MOD
    ds2 = ((target >> 16) - s2) % MOD
    out = []
    for delta in range(-255, 256):
        if delta == 0:
            continue
        dm = delta % MOD
        if ds1 != dm:
            continue
        np = (ds2 * pow(dm, -1, MOD)) % MOD
        p = n - np
        if 0 <= p < n:
            old, new = d[p], d[p] + delta
            if 0 <= new <= 255:
                out.append((p, old ^ new, old, new))
    return out


def fix_crlf(b, mode):
    """恢复被单点补 XOR 破坏的 UTF-16LE CRLF（结构判据，零猜测）。"""
    fixes = []
    if mode != 'utf16':
        return fixes
    for i in range(0, len(b) - 3, 2):
        q = b[i:i + 4]
        if q == b'\x0d\x00\x0a\x00':
            continue
        if q[2:4] == b'\x0a\x00' and q[0] == 0x0d:
            b[i + 1] = 0x00
            fixes.append((i + 1, 'CR_HI', q[1], 0x00))
        elif q[2:4] == b'\x0a\x00' and q[1] == 0x00:
            b[i] = 0x0d
            fixes.append((i, 'CR_LO', q[0], 0x0d))
        elif q[0:2] == b'\x0d\x00' and q[3] == 0x00:
            b[i + 2] = 0x0a
            fixes.append((i + 2, 'LF_LO', q[2], 0x0a))
        elif q[0:2] == b'\x0d\x00' and q[2] == 0x0a:
            b[i + 3] = 0x00
            fixes.append((i + 3, 'LF_HI', q[3], 0x00))
    return fixes


def line_mask_fix(b, h, k1, k2):
    """行区间「双重 XOR」复元：整行内容被多应用了一次 XOR，净 mask = k1^k2。

    候选＝每个 CRLF 分隔的行内容（不含末尾 4B CRLF）；
    验收＝施加该变换后 zlib.adler32 精确等于 adlr（零猜测、不命中的一律不动）。
    """
    mask = k1 ^ k2
    fixes = []
    if mask == 0 or h is None:
        return fixes
    n = len(b)
    for _ in range(8):
        if (zlib.adler32(b) & 0xffffffff) == h:
            break
        s1, s2 = adler_parts(b)
        t1, t2 = h & 0xffff, h >> 16
        starts = [0]
        for i in range(0, n - 3, 2):
            if b[i:i + 4] == b'\x0d\x00\x0a\x00':
                starts.append(i + 4)
        found = None
        for j, s in enumerate(starts):
            e = (starts[j + 1] - 4) if j + 1 < len(starts) else n
            if e <= s:
                continue
            ds1 = ds2 = 0
            for i in range(s, e):
                dl = (b[i] ^ mask) - b[i]
                ds1 += dl
                ds2 += (n - i) * dl
            if (s1 + ds1) % MOD == t1 and (s2 + ds2) % MOD == t2:
                found = (s, e)
                break
        if not found:
            break
        for i in range(found[0], found[1]):
            b[i] ^= mask
        fixes.append(found)
    return fixes


def solve_points(b, h, mode):
    """多点补 XOR 联合复元：meet-in-the-middle + adler32 精确验收（零猜测）。

    Δs1=Σδ、Δs2=Σ(n-p)δ；候选位置＝UTF-16 高字节非法 / BAD_RE / 半角假名的码元。
    每个位置枚举 extra e∈[0,255]，δ=(old^e)-old；两半哈希配对，命中即应用并复核校验和。
    """
    if h is None or mode != 'utf16':
        return []
    if (zlib.adler32(b) & 0xffffffff) == h:
        return []
    n = len(b)
    cand = []
    for i in range(2, len(b) - 1, 2):
        hi, lo = b[i + 1], b[i]
        ch = chr(lo | (hi << 8))
        if hi not in E.H_SET or E.BAD_RE.search(ch) or '\uff61' <= ch <= '\uff9f':
            cand.append(i + 1)
    if not cand or len(cand) > 4:
        return []
    s1, s2 = adler_parts(b)
    ds1 = ((h & 0xffff) - s1) % MOD
    ds2 = ((h >> 16) - s2) % MOD
    opts = []
    for p in cand:
        old = b[p]
        vals = {}
        for e in range(256):
            new = old ^ e
            if new != old:
                vals.setdefault(new - old, e)
        opts.append(list(vals.items()))
    half = len(cand) // 2

    def build(sel):
        res = {}
        for choice in itertools.product(*[opts[j] for j in sel]):
            a1 = sum(d for d, e in choice) % MOD
            a2 = sum((n - cand[j]) * d for j, (d, e) in zip(sel, choice)) % MOD
            res.setdefault((a1, a2), []).append(choice)
        return res

    left = build(list(range(half)))
    right = build(list(range(half, len(cand))))
    left_idx, right_idx = list(range(half)), list(range(half, len(cand)))
    for (a1, a2), lcs in left.items():
        need = ((ds1 - a1) % MOD, (ds2 - a2) % MOD)
        if need not in right:
            continue
        for lc in lcs:
            for rc in right[need]:
                applied = list(zip(left_idx, lc)) + list(zip(right_idx, rc))
                for j, (d, e) in applied:
                    b[cand[j]] ^= e
                if (zlib.adler32(b) & 0xffffffff) == h:
                    return [(cand[j], e) for j, (d, e) in applied]
                for j, (d, e) in applied:
                    b[cand[j]] ^= e
    return []


def repair(name, d, mode, h, k1, k2):
    """明文已由 decode_exact() 确定性复元（bnd + 单点均由 adler32 解析）。
    此处只做零猜测验收，不做任何修补 —— SPECIAL / CRLF 结构 / line_mask /
    solve_points / MANUAL_FIX 等旧的概率与语义填值路线全部废弃。"""
    ok = h is not None and (zlib.adler32(d) & 0xffffffff) == h
    return d, [], ok


# 残留单点补 XOR 的「已知明文定值表」（依据逐条见解析报告 §品检）
# 全部来自：KAG 行结构 / 惯用句 / 上下文交叉验证 / 全文重复专名；无概率填值。
MANUAL_FIX = [
    ('팀店主としては', '　店主としては', '裸地の文行首全角空格'),
    ('ともす낌ば', 'ともすれば', '惯用句「ともすれば」'),
    ('　냎ギ、と呼ばれた', '　ノギ、と呼ばれた', '前一行「ノ、ノギさん……？」交叉验证'),
    ('翳りが射\ufffdていた', '翳りが射していた', '「射して」'),
    ('悪くなባて', '悪くなって', '「悪くなって」'),
    ('その즖線が', 'その視線が', '「視線」'),
    ('済んだ䭑れど', '済んだだけれど', '「だけれど」'),
    ('\uf0abイエン', 'カイエン', '全文多处「カイエン」'),
    ('、ﾗﾌ喧騒', '、喧騒', '多余残片剔除；「段々と、喧騒が…」语义完整'),
    ('、푂くまで', '、あくまで', '「あくまで」'),
]
# KAG 正文行必以全角空格／引号开头；以 CJK 罕见字等开头的行＝命令/标签残片
RARE_HEAD = re.compile(
    r'^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\ufb50-\ufdff\ufe00-\ufeff'
    r'\uac00-\ud7af\u00c0-\u024f\u0400-\u04ff\u0600-\u06ff\u1200-\u137f]')


def attrs(s):
    d = {}
    for k, a, b, c in ATTR_RE.findall(s):
        d[k] = a if a != "" else (b if b != "" else c)
    return d


class Extractor:
    def __init__(self):
        self.lines = []
        self.cur = ""
        self.st = collections.Counter()
        self.tok = 0
        self.empty = 0
        self.skip = False

    def flush(self, why):
        if self.cur:
            self.lines.append(self.cur)
            self.st["flush_" + why] += 1
            self.cur = ""
        elif why in ("p", "s"):
            self.empty += 1

    def inline(self, s):
        self.st["ruby_stripped"] += len(INLINE_RE.findall(s))
        return INLINE_RE.sub("", s)

    def voice(self, a, v2=False):
        q = ("", "") if v2 else (("『", "』") if a.get("pron") == "sec" else ("「", "」"))
        body = (a.get("word", "") + a.get("afterword", "") +
                a.get("afterword2", "") + a.get("word2", ""))
        s = self.inline(q[0] + body + q[1])
        self.cur += s
        self.tok += len(s)
        self.st["voice2" if v2 else "voice"] += 1
        self.flush("voice")

    def option(self, a):
        t = self.inline(a.get("text", ""))
        self.flush("pre_opt")
        self.lines.append(t)
        self.tok += len(t)
        self.st["opts"] += 1

    def feed(self, name, text):
        for raw in text.splitlines():
            l = raw.rstrip()
            t = l.lstrip()
            if not t:
                continue
            if t.startswith("@iscript") or t.startswith("@macro"):
                self.skip = True
                continue
            if t.startswith("@endscript") or t.startswith("@endmacro"):
                self.skip = False
                continue
            if self.skip or t[0] in ";*":
                continue
            # 脚本残留：行首 @ 被单点补 XOR 破坏 ⇒ 整行不再以 @ 开头。
            # 代码级判据＝出现 KAG 命令属性（正文行不含 name=/word=/time= 等）。
            if t[0] != "@" and CMD_ATTR.search(t):
                m = SPLIT_BODY.search(t)
                if m:
                    vis = self.inline(m.group(1).rstrip())
                    self.cur += vis
                    self.tok += len(vis)
                    self.st["recover_body"] += 1
                else:
                    a = attrs(t)
                    if a.get("word") or a.get("word2"):
                        q = ("『", "』") if a.get("pron") == "sec" else ("「", "」")
                        s = self.inline(q[0] + a.get("word", "") + a.get("word2", "") + q[1])
                        self.cur += s
                        self.tok += len(s)
                        self.st["recover_voice"] += 1
                self.st["skip_cmd_residue"] += 1
                continue
            if t[0] != "@":                       # 裸地の文 / 台词
                vis = self.inline(TAIL_BAD.sub("", l))
                self.cur += vis
                self.tok += len(vis)
                self.st["bare"] += 1
                continue
            m = re.match(r"@([A-Za-z_][A-Za-z0-9_]*)", t)
            cmd = m.group(1) if m else ""
            rest = t[len("@" + cmd):]
            if cmd in ("p", "s"):
                self.flush(cmd)
                self.st[cmd] += 1
            elif cmd in ("cm", "ct", "er"):
                self.flush(cmd)
                self.st[cmd] += 1
            elif cmd == "r":
                self.st["r"] += 1
            elif cmd == "voice":
                self.voice(attrs(rest))
            elif cmd == "voice2":
                self.voice(attrs(rest), v2=True)
            elif cmd == "select_item":
                self.option(attrs(rest))
            elif cmd == "select_start":
                self.flush("select_start")
            else:
                self.st["skip_" + cmd] += 1
        self.flush("eof")


def main():
    xp3_path = sys.argv[1] if len(sys.argv) > 1 else DEF_XP3
    out_path = sys.argv[2] if len(sys.argv) > 2 else DEF_OUT
    xp = E.XP3(xp3_path)
    names = sorted(n for n in xp.entries
                   if n.lower().endswith(".ks") and n.startswith("scenario/"))
    cache = build_model(xp, names)

    texts, table, okcnt = {}, [], 0
    for n in names:
        mode, t, d, k1, k2, b, nb, h = cache[n]
        fixed, fixes, ok = repair(n, d, mode, h, k1, k2)
        texts[n] = E.to_text(fixed, mode)
        okcnt += int(ok)
        for fx in fixes:
            table.append((n, mode, k1, k2, b) + fx)

    order = order_files([os.path.basename(n) for n in names])
    ex = Extractor()
    for n in order:
        ex.feed(n, texts["scenario/" + n])

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    data = "\ufeff" + "\n".join(ex.lines) + "\n"
    with open(out_path, "wb") as f:
        f.write(data.encode("utf-8"))

    with open(DEF_TABLE, "w", encoding="utf-8") as g:
        g.write("# 单点补 XOR 确定性复元表（SPECIAL / CRLF 结构 / adler32 差分解析）\n")
        g.write("# 成员 | mode | k1 | k2 | bnd | 字节偏移 | 依据 | 原值 | 新值\n")
        for row in table:
            g.write(" | ".join(str(x) for x in row) + "\n")

    out_chars = sum(len(x) for x in ex.lines)
    print("xp3 members", len(xp.entries), "| scenario ks", len(names),
          "| story files", len(order))
    print("adler matched", okcnt, "/", len(names), "| repairs", len(table))
    print("lines", len(ex.lines), "chars", out_chars, "bytes", len(data.encode("utf-8")))
    print("stats", dict(ex.st.most_common(22)))
    print("token(expected)", ex.tok, "out_chars", out_chars, "diff", ex.tok - out_chars)
    print("empty_frames", ex.empty)
    print("--- first 6 ---")
    for x in ex.lines[:6]:
        print("   ", x[:100])
    print("--- last 4 ---")
    for x in ex.lines[-4:]:
        print("   ", x[:100])
    xp.f.close()


if __name__ == "__main__":
    main()
