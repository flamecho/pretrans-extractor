# -*- coding: utf-8 -*-
"""LiveMaker 3 通用文本提取（VF 归档 ＋ LMScript `.lsb` ＋ LiveNovel `TpWord`）。

比 `anotherrewind_extract.py` 多出三件事（2026-11-02 Battle Four Re 实测）：
  1. ★ **正文可能分散在多本 `.lsb`**（本作 6 本）—— 按「入口 → 引用图」排序并把子剧本
     插到父脚本的**引用点**上，而不是只读一本；
  2. ★ **选项字面**＝`To(____N)=Str <文本>` 之后紧跟 `0c …「選択値」` 结构（本作 40 项）；
  3. ★ **系统菜单要按结构排除**：标题菜单的选项记录落在**最后一个 TpWord 之后**（本作 スタート/えくすとら/ロード）。

判据一律结构性（类型字节 / 标记串 / 记录位置），不做内容过滤。禁穷举、禁 OCR。

用法：
    python scripts/livemaker_extract.py --verify                 # 只自检
    python scripts/livemaker_extract.py --out out.txt            # 出成品
    python scripts/livemaker_extract.py --exe "...\\Game.exe"    # 指定内层 exe（已解 RAR）
"""
import argparse
import hashlib
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
import zlib

VF_SEED = 0x75D6EE39
# --split-line：把 BreakType.LINE 也当断点（按「显示行」出，而不是按「一框」）
SPLIT_LINE = False
# --dual-pause：把 `\x01PAUSE` 事件当「一次点击」的段界（引擎：PAUSE → SetProp 81 1，点击后
#   只清标志、不换页 ⇒ 同一框内追加文字）；一页 ≥2 段时出「段行 ＋ 合并行」双版。
DUAL_PAUSE = False
# --inline-placeholder：把 TWdImg（内嵌图）与 TWdOpeVar（变量插入）落成可见占位
#   `⟦IMG:路径⟧` / `⟦VAR:名⟧`，供调用方按作替换（默认关＝静默丢弃，等同旧行为）。
INLINE_PH = False
CTL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
SEVENZIP = [
    r'C:\Program Files\7-Zip\7z.exe',
    r'C:\Program Files (x86)\7-Zip\7z.exe',
]
# 选项结构：To(____N)=Str 之后 0c 记录 + 字段名「選択値」
OPT_MARK = 6 .to_bytes(4, 'little') + '選択値'.encode('cp932')
TO_SIG = b'\x01\x05\x00\x00\x00____'
# ★ 脚本名是 8 位**十六进制**（Battle Four 用 `000000B9.lsb`，只认 \d{8} 会漏）
REF_RE = re.compile(rb'([0-9A-Fa-f]{8}\.lsb)')
ENTRY = 'ゲームメイン.lsb'

# ★ 系统区段（由引擎资源串界定，段内一切「選択値」记录都不是剧情选项）
#   Battle Four(2008) 的 000000B0.lsb：0x028B00 起是标题菜单（`グラフィック\taitol.gal` / `たいとる.mid` /
#   `グラフィック\T2.lpm` `T3.lpm` / カーソル音.wav），到 0x02B92A 为止还含名字表（`DB名前代替` / `名前\n1.gal`）。
#   段内记录：Button01..03 / 01 / ex（标题菜单 9 条）、キョウ / リュウジ / アヴェル（名字表菜单 3 条）。
# [JP]Limit 的 00000001.lsb：标题/再開菜单（Start / Sload / ex 共 5 条）位于文件靠前段
#   @0x03780c–0x037e81，而本脚本末 TpWord 在 @0x185e87，故 q<limit 会把菜单误收为剧情选项。
#   菜单代码块被两个 TpWord 夹住（前块 0x3710e–0x371bf、后块 0x37f6f–0x38102），故用其间隙 (0x371bf, 0x37f6f)
#   精确剔除 5 条菜单选项，且不影响任何剧情 TpWord / 剧情选项（下一个剧情选项在 0x050f85）。
OPT_SKIP = {
    '000000B0.lsb': [(0x028B00, 0x02B92A)],
    '00000001.lsb': [(0x371BF, 0x37F6F)],
    # [JP]POLICEチャンネル 用語辞典（00000568.lsb）：本脚本是辞典，无任何剧情选项。
    # 其开头 0x9C3~0xBF7 是 AddArray 通道的系统导航（隠しシナリオへザッピング / 右クリック処理解説へザッピング /
    # やっぱり戻る）；另有 20 处 `選択値` 是 `____1`/`____0` 临时变量构成的选择子程序共享代码（同 IDOL STEP! §13.1），
    # 二者均非剧情选项。整段剔除选项扫描（仅作用于选项，词条 TpWord 不受影响）。
    '00000568.lsb': [(0x0000, 0x10000)],
}


def u32(b, p):
    return struct.unpack_from('<I', b, p)[0]


def pstr(b, p):
    n = u32(b, p)
    return b[p + 4:p + 4 + n].decode('cp932', 'replace'), p + 4 + n


def skip_pstr(b, p):
    return p + 4 + u32(b, p)


def _keystream(seed=VF_SEED):
    key = 0
    while True:
        key = ((key << 2) + key + seed) & 0xFFFFFFFF
        yield key


class Xor:
    __slots__ = ('ks',)

    def __init__(self):
        self.ks = _keystream()

    def raw_bytes(self, data):
        return bytes(x ^ (next(self.ks) & 0xFF) for x in data)

    def raw_int(self, data):
        key = next(self.ks)
        return bytes(x ^ ((key >> (8 * i)) & 0xFF) for i, x in enumerate(data))


# ------------------------------------------------- LiveMaker Pro 加密归档（TScramble）
# 纯 Python 复现 pylivemaker `scramble.py`（零依赖；numpy 版仅用 uint32/uint64 环绕，
# Python int 加掩码即可等价）。仅本族「全加密」作品需要（如 [JP]POLICEチャンネル：
# 453 项全部 compress_type∈{2,3}，encflags 全 0）。
_SCRAMBLE_KEY = 0xF8EA
_SCRAMBLE_FACTORS = (0x7DD4FFC7, 0x000005D4, 0x000006F0, 0x000013FB)


class _LMScramble:
    def __init__(self, seed):
        if seed == 0:
            seed = 0xFFFFFFFF
        seed &= 0xFFFFFFFF
        st = []
        for _ in range(5):
            seed ^= (seed << 13) & 0xFFFFFFFF
            seed ^= (seed >> 17) & 0xFFFFFFFF
            seed ^= (seed << 5) & 0xFFFFFFFF
            st.append(seed)
        self.state = st
        for _ in range(19):
            self.rand()

    def rand(self):
        x = (self.state[3] * _SCRAMBLE_FACTORS[0]
             + self.state[2] * _SCRAMBLE_FACTORS[1]
             + self.state[1] * _SCRAMBLE_FACTORS[2]
             + self.state[0] * _SCRAMBLE_FACTORS[3]
             + self.state[4]) & 0xFFFFFFFFFFFFFFFF
        self.state[4] = (x >> 32) & 0xFFFFFFFF
        self.state[3] = self.state[2]
        self.state[2] = self.state[1]
        self.state[1] = self.state[0]
        self.state[0] = x & 0xFFFFFFFF
        return self.state[0]

    def random(self):
        return self.rand() / 0x100000000

    def randint(self, lo, hi):
        return lo + int(self.random() * (hi - lo + 1))

    @classmethod
    def randseq(cls, count, seed):
        sc = cls(seed)
        vals = list(range(count))
        seq = [0] * count
        i = 0
        while vals:
            n = 0 if len(vals) == 1 else sc.randint(0, len(vals) - 2)
            seq[vals.pop(n)] = i
            i += 1
        return seq


def scramble_decrypt(data):
    """还原被 TScramble 打乱的字节流（LiveMaker Pro 加密归档）。前 8 B = chunk_size(i32)+seed(u32)。"""
    if len(data) < 8:
        return data
    chunk_size, seed = struct.unpack('<iI', data[:8])
    total_chunks = math.ceil((len(data) - 8) / chunk_size)
    out = b''.join(
        data[8 + i * chunk_size: 8 + i * chunk_size + chunk_size]
        for i in _LMScramble.randseq(total_chunks, seed ^ _SCRAMBLE_KEY)
    )
    if len(out) != len(data) - 8:
        raise ValueError('scramble 长度不匹配')
    return out


def pe_overlay(d):
    if d[:2] != b'MZ':
        raise ValueError('不是 PE 文件（缺 MZ）')
    lf = u32(d, 0x3C)
    if d[lf:lf + 4] != b'PE\0\0':
        raise ValueError('PE 签名不符')
    nsec = struct.unpack_from('<H', d, lf + 6)[0]
    optsz = struct.unpack_from('<H', d, lf + 20)[0]
    sec = lf + 24 + optsz
    end = 0
    for i in range(nsec):
        o = sec + 40 * i
        end = max(end, u32(d, o + 20) + u32(d, o + 16))
    return end


def unwrap_rar(path):
    exe = next((p for p in SEVENZIP if os.path.isfile(p)), None)
    if not exe:
        raise SystemExit('输入是 RAR5 SFX，未找到 7-Zip。请先手工解出内层 exe 再 --exe 指过去。')
    tmp = tempfile.mkdtemp(prefix='_lm_rar_')
    print('  解 RAR5 →', tmp)
    subprocess.run([exe, 'x', '-y', '-bso0', '-bsp0', '-o' + tmp, path],
                   capture_output=True)
    best = None
    for root, _d, files in os.walk(tmp):
        for f in files:
            if f.lower().endswith('.exe'):
                p = os.path.join(root, f)
                if best is None or os.path.getsize(p) > os.path.getsize(best):
                    best = p
    if not best:
        raise SystemExit('RAR 解包后未找到内层 exe')
    return best


class VFArchive:
    """LiveMaker VF 归档目录（参考 pylivemaker archive.py:LMArchiveDirectory）。"""

    def __init__(self, blob):
        if blob[:2] != b'vf':
            raise ValueError('VF 签名不符：%r' % blob[:4])
        self.blob = blob
        self.ver = u32(blob, 2)
        self.count = u32(blob, 6)
        p = 10
        ks = Xor()
        self.names = []
        for _ in range(self.count):
            n = u32(blob, p)
            p += 4
            self.names.append(ks.raw_bytes(blob[p:p + n]).decode('cp932', 'replace'))
            p += n
        klo, khi = Xor(), Xor()
        self.offsets = []
        for _ in range(self.count + 1):
            lo = u32(klo.raw_int(blob[p:p + 4]), 0)
            p += 4
            hi = u32(khi.raw_int(blob[p:p + 4]), 0)
            p += 4
            self.offsets.append(((hi & 0x80000000) << 32) | lo)
        self.ctypes = list(blob[p:p + self.count]); p += self.count
        self.unk1s = list(struct.unpack_from('<%dI' % self.count, blob, p)); p += 4 * self.count
        self.checksums = list(struct.unpack_from('<%dI' % self.count, blob, p)); p += 4 * self.count
        self.encflags = list(blob[p:p + self.count]); p += self.count
        self.dir_end = p
        self.index = {n: i for i, n in enumerate(self.names)}

    def check(self):
        errs = []
        if self.offsets[0] != self.dir_end:
            errs.append('首项 offset %#x != 目录末 %#x' % (self.offsets[0], self.dir_end))
        if self.offsets[-1] + 6 != len(self.blob):
            errs.append('末项 %#x + 6 != 归档长 %#x' % (self.offsets[-1], len(self.blob)))
        if any(self.offsets[i] > self.offsets[i + 1] for i in range(self.count)):
            errs.append('offsets 非单调')
        if any(self.encflags):
            errs.append('存在加密项（encrypt_flag != 0）')
        return errs

    def read(self, name):
        i = self.index[name]
        raw = self.blob[self.offsets[i]:self.offsets[i + 1]]
        ct = self.ctypes[i]
        if ct == 0:
            return zlib.decompress(raw)
        if ct == 1:
            return raw
        if ct == 2:
            return scramble_decrypt(raw)
        if ct == 3:
            return zlib.decompress(scramble_decrypt(raw))
        raise ValueError('%s: 不支持的 compress_type=%d' % (name, ct))


# ---------------------------------------------------------------- TpWord
def parse_tpword(b, o, end, split_line=False, dual_pause=False, inline_ph=False):
    p = o
    if b[p:p + 6] != b'TpWord':
        raise ValueError('TpWord 签名不符 @%#x' % p)
    p += 6
    ver = int(b[p:p + 3]); p += 3
    n = u32(b, p); p += 4
    for _ in range(n):
        p += 16
        p += 2
        p += 1 if ver < 100 else 4
        p = skip_pstr(b, p)
        p = skip_pstr(b, p)
        if ver >= 100:
            p += 8
    if ver >= 104:
        n = u32(b, p); p += 4
        for _ in range(n):
            p += 4
            p = skip_pstr(b, p)
    if ver >= 105:
        n = u32(b, p); p += 4
        for _ in range(n):
            p += 4
            p = skip_pstr(b, p)
            p = skip_pstr(b, p)
    n = u32(b, p); p += 4
    pages, cur = [], []
    segs, seg_lists = [], []                     # dual_pause：页内按 PAUSE 切段
    cur_flushed = False
    nchar = 0
    st = {'pause': 0, 'line': 0, 'page': 0, 'page_empty': 0,
          'break_other': 0, 'event': 0, 'glyph_other': 0, 'ctl': 0}
    for _ in range(n):
        t = b[p]; p += 1
        if ver >= 104:
            p += 4
        if t == 0x01:                                   # TWdChar
            if ver < 105:
                p = skip_pstr(b, p)
            else:
                p += 4
            p += 4
            code = struct.unpack_from('<H', b, p)[0]; p += 2
            p += 4
            ch = code.to_bytes(2, 'big').decode('cp932')
            if ch.startswith('\x00'):
                ch = ch[1]
            nchar += 1
            if CTL.match(ch):
                st['ctl'] += 1
            else:
                cur.append(ch)
        elif t == 0x02:                                 # TWdOpeDiv
            p += 1
            if ver >= 105:
                p += 9
        elif t == 0x03:                                 # TWdOpeReturn
            bt = b[p]; p += 1
            if bt == 1:                                 # BreakType.PAGE ⇒ 断框
                if dual_pause or DUAL_PAUSE:
                    segs.append(''.join(cur))
                    cur = []
                    seg_text = ''.join(segs)
                    s = seg_text.strip(' \t\r\n')
                    if s:
                        pages.append(s)
                    elif not (split_line or SPLIT_LINE) or not cur_flushed:
                        st['page_empty'] += 1
                    if s:                       # 与 pages 严格对齐：空页不入表
                        sl = [x.strip(' \t\r\n') for x in segs]
                        seg_lists.append([x for x in sl if x])
                    segs = []
                    cur_flushed = False
                    st['page'] += 1
                    continue
                s = ''.join(cur).strip(' \t\r\n')
                if s:
                    pages.append(s)
                elif not (split_line or SPLIT_LINE) or not cur_flushed:
                    st['page_empty'] += 1               # split_line 下已按行 flush 过就不算空段
                cur = []
                cur_flushed = False
                st['page'] += 1
            elif bt == 0:                               # BreakType.LINE ⇒ 框内换行，合并
                st['line'] += 1
                if split_line or SPLIT_LINE:            # --split-line：按显示行断
                    s2 = ''.join(cur).strip(' \t\r\n')
                    if s2:
                        pages.append(s2)
                    cur = []
                    cur_flushed = True
            else:
                st['break_other'] += 1
        elif t in (0x04, 0x05):
            pass
        elif t == 0x06:                                 # TWdOpeEvent
            ev, p = pstr(b, p)
            st['event'] += 1
            if ev.split('\r\n')[0].lstrip('\x01') == 'PAUSE':
                st['pause'] += 1                          # 同框「继续」：点击后不换页
                if dual_pause or DUAL_PAUSE:
                    segs.append(''.join(cur))
                    cur = []
        elif t in (0x07, 0x0A):
            p += 4
            if ver > 100:
                p += 4
            if 100 < ver < 105:
                p = skip_pstr(b, p)
            if ver >= 105:
                p += 4
            if ver < 102:
                raise NotImplementedError('TpWord %d 的 var_name 未实现' % ver)
            vname, p = pstr(b, p)
            st['glyph_other'] += 1
            if inline_ph or INLINE_PH:
                cur.append('\u27e6VAR:%s\u27e7' % vname)
        elif t == 0x09:                                 # TWdImg
            if ver < 105:
                p = skip_pstr(b, p)
            else:
                p += 4
            p += 4
            src, p = pstr(b, p)                          # 内嵌图路径（如 `グラフィック\CO.gal`）
            p += 1
            if ver >= 103:
                p = skip_pstr(b, p)
            if ver >= 105:
                p += 16
                p = skip_pstr(b, p)
            st['glyph_other'] += 1
            if inline_ph or INLINE_PH:
                cur.append('\u27e6IMG:%s\u27e7' % src)
        else:
            st['glyph_other'] += 1
    if cur or segs:
        if dual_pause or DUAL_PAUSE:
            segs.append(''.join(cur))
            s = ''.join(segs).strip(' \t\r\n')
            if s:
                pages.append(s)
                sl = [x.strip(' \t\r\n') for x in segs]
                seg_lists.append([x for x in sl if x])
            segs = []
        else:
            s = ''.join(cur).strip(' \t\r\n')
            if s:
                pages.append(s)
    if p != end:
        raise ValueError('TpWord 长度不符：解析到 %#x，块末 %#x' % (p, end))
    st['segs'] = seg_lists
    return pages, nchar, st


def scan_tpwords(b, split_line=False, dual_pause=False, inline_ph=False):
    out = []
    i = 0
    while True:
        i = b.find(b'TpWord', i + 1)
        if i < 0:
            break
        if i < 4:
            continue
        length = u32(b, i - 4)
        end = i + length
        if end > len(b):
            continue
        try:
            pages, nchar, st = parse_tpword(b, i, end, split_line, dual_pause, inline_ph)
        except (ValueError, UnicodeDecodeError, struct.error):
            continue
        out.append((i - 4, end, pages, nchar, st))
    return out


# ---------------------------------------------------------------- 选项
ADD_RE = re.compile(rb'\x0b\x05\x00\x00\x00____.\x02\x00\x00\x00\x42')
TO_RE = re.compile(re.escape(TO_SIG))


def scan_options_addarray(b, limit, skip=()):
    """变体（2026-11-04 IDOL STEP!）：`To(____N)=Str X` 紧跟 `Func(____M)=AddArray(_tmp, ____N)`。

    判据是**命令层**：`0B`=Func ＋ 参数数 2 ＋ func id `0x42`=AddArray（L0）。
    本作 15 个分歧点 × 3 选项 = 45 条，每个分歧点后调共享「等待选择」子程序，
    所以脚本里那 15 处 `選択値` 与选项**并不配对**（属系统等待逻辑）⇒ 不能走 OPT_MARK 路径。
    off 取 AddArray 记录位置，供与 TpWord 页排序。
    """
    out, dropped = [], []
    for m in ADD_RE.finditer(b):
        q = m.start()
        t = None
        for x in TO_RE.finditer(b, max(0, q - 400), q):
            t = x
        if t is None:
            continue
        to = t.start()
        nlen = u32(b, to + 1)
        r = to + 5 + nlen
        if b[r:r + 4] != b'\x01\x00\x00\x00' or b[r + 4] != 0x04:
            continue
        ln = u32(b, r + 5)
        if not (0 < ln <= 4096):
            continue
        try:
            txt = b[r + 9:r + 9 + ln].decode('cp932')
        except UnicodeDecodeError:
            continue
        if q >= limit:
            dropped.append((q, txt, '超出剧情区'))
            continue
        if any(lo <= q < hi for lo, hi in skip):
            dropped.append((q, txt, '在系统区段'))
            continue
        out.append((q, txt))
    return out, dropped


def scan_options(b, limit, skip=()):
    """结构性选项：`To(____N)=Str X` 之后紧接 `0c …「選択値」`。

    `limit` = 本脚本最后一个 TpWord 的结束位置；之后的记录属系统菜单（标题菜单），按位置剔除。
    `skip` = 显式「系统区段」[(lo, hi), …]：由引擎资源串界定的标题/名字表代码段，
    段内一切 `選択値` 记录都不是剧情选项（2026-11-02 Battle Four 实测需要）。
    返回 (保留, 剔除[(off, 文本, 理由)])。
    """
    # 先走 AddArray 变体（IDOL STEP! 等：选项不经 `選択値` 配对）；命中就不必再扫 OPT_MARK
    aa, aa_drop = scan_options_addarray(b, limit, skip)
    if aa:
        return aa, aa_drop
    out, dropped = [], []
    p = -1
    while True:
        p = b.find(OPT_MARK, p + 1)
        if p < 0:
            break
        q = b.rfind(TO_SIG, max(0, p - 300), p)
        if q < 0:
            continue
        nlen = u32(b, q + 1)
        r = q + 5 + nlen
        if b[r + 4] != 0x04:                     # 只认 Str 参数
            continue
        ln = u32(b, r + 5)
        body = b[r + 9:r + 9 + ln]
        try:
            txt = body.decode('cp932')
        except UnicodeDecodeError:
            continue
        if q >= limit:                           # 系统菜单区（最后一个 TpWord 之后）
            dropped.append((q, txt, '超出剧情区'))
            continue
        if any(lo <= q < hi for lo, hi in skip):
            dropped.append((q, txt, '在系统区段'))
            continue
        out.append((q, txt))
    # 去重（同一记录可能被两处标记命中）
    seen, uniq = set(), []
    for q, txt in sorted(out):
        if q in seen:
            continue
        seen.add(q)
        uniq.append((q, txt))
    return uniq, dropped


# ---------------------------------------------------------------- 组织
def load(exe):
    d = open(exe, 'rb').read()
    ov = pe_overlay(d)
    if d[ov:ov + 2] == b'vf':
        blob = d[ov:]
    elif d[ov:ov + 7] == b'Rar!\x1a\x07\x01':
        return load(unwrap_rar(exe))
    else:
        raise SystemExit('overlay 既不是 VF 也不是 RAR5：%r' % d[ov:ov + 8])
    arc = VFArchive(blob)
    errs = arc.check()
    if errs:
        raise SystemExit('VF 目录自检失败：' + '；'.join(errs))
    return arc


def discover(arc):
    """找出所有承载正文的脚本（判据：TpWord 字数 > 0，不看文件名）。"""
    st = {}
    for n in arc.names:
        if not n.lower().endswith('.lsb'):
            continue
        try:
            b = arc.read(n)
        except (ValueError, zlib.error):
            continue
        tps = scan_tpwords(b)
        nchar = sum(t[3] for t in tps)
        if nchar:
            st[n] = (b, tps, nchar)
    return st


def refs_of(b):
    out = []
    for m in REF_RE.finditer(b):
        out.append((m.start(), m.group(1).decode('ascii')))
    return out


def build_order(arc, story):
    """入口 → 引用图（深度优先，按引用点字节顺序）。返回 (order, edges, orphans)。"""
    order, edges, seen = [], {}, set()

    def walk(name):
        if name in seen or name not in story:
            return
        seen.add(name)
        order.append(name)
        kids = []
        for off, t in refs_of(story[name][0]):
            if t != name and t in story and t not in seen:
                kids.append((off, t))
        edges[name] = kids
        for off, t in kids:
            walk(t)

    root = None
    if ENTRY in arc.index:
        b = arc.read(ENTRY)
        for off, t in refs_of(b):
            if t in story:
                root = t
                break
    if root is None:
        root = max(story, key=lambda n: story[n][2])
        print('  ⚠ 未从 %s 找到入口，改用字数最多的脚本 %s' % (ENTRY, root))
    walk(root)
    orphans = [n for n in sorted(story) if n not in seen]
    for n in orphans:
        order.append(n)
    return order, edges, orphans


def story_events(name, story, edges, stats, depth=0):
    """把一本脚本的 TpWord 页 与 选项 按字节位置合并；遇到子剧本引用点则整段插入。"""
    b, tps, nchar = story[name]
    limit = tps[-1][1] if tps else 0
    opts, dropped = scan_options(b, limit, OPT_SKIP.get(name, ()))

    items = []
    for off, end, pages, _nc, _st in tps:
        if DUAL_PAUSE:
            seg_lists = _st.get('segs') or []
            for i, page_txt in enumerate(pages):
                sl = [x for x in (seg_lists[i] if i < len(seg_lists) else []) if x]
                # 4 元组 (off, cat, sub, val)：cat 0=正文 1=选项 2=子剧本引用，互不混淆；
                # sub 按「页序 ×1024 ＋ 位次」编排：段0 < 段1 < … < 合并行(+9) 且页与页不交错
                if len(sl) >= 2:                # 一页 ≥2 次点击 ⇒ 段行 ＋ 合并行
                    items.extend((off, 0, i * 1024 + k, x) for k, x in enumerate(sl))
                    items.append((off, 0, i * 1024 + 9, page_txt))
                else:
                    items.append((off, 0, i * 1024, page_txt))
            continue
        for s in pages:
            items.append((off, 0, 0, s))
    for off, txt in opts:
        items.append((off, 1, 0, txt))
    for off, t in edges.get(name, []):
        items.append((off, 2, 0, t))
    items.sort(key=lambda x: (x[0], x[1], x[2]))

    ev, emitted = [], set()
    for off, cat, sub, val in items:
        if cat == 2:                       # 子剧本引用点
            if val not in emitted:
                emitted.add(val)
                ev.extend(story_events(val, story, edges, stats, depth + 1))
            continue
        ev.append((name, val))

    stats[name] = {
        'lsb': len(b), 'tp': len(tps), 'nchar': nchar,
        'page': sum(t[4]['page'] for t in tps),
        'page_empty': sum(t[4]['page_empty'] for t in tps),
        'line': sum(t[4]['line'] for t in tps),
        'pause': sum(t[4]['pause'] for t in tps),
        'break_other': sum(t[4]['break_other'] for t in tps),
        'ctl': sum(t[4]['ctl'] for t in tps),
        'opt': len(opts),
        'opt_dropped': dropped,
        # dual_pause：多段页把 1 行换成 (段数 + 1) 行 ⇒ 额外行数 = Σ段数
        'multi': sum(len(sl) for t in tps for sl in (t[4].get('segs') or []) if len(sl) >= 2)
                 if DUAL_PAUSE else 0,
        'mpages': sum(1 for t in tps for sl in (t[4].get('segs') or []) if len(sl) >= 2)
                  if DUAL_PAUSE else 0,
        'lines': sum(len(t[2]) for t in tps) + len(opts)
                 + (sum(len(sl) for t in tps for sl in (t[4].get('segs') or []) if len(sl) >= 2)
                    if DUAL_PAUSE else 0),
        'depth': depth,
    }
    return ev


def run(exe, out=None):
    arc = load(exe)
    print('VF 归档   : ver=%d, %d 项, 目录末 0x%X, 首项 0x%X, 末项 0x%X（+6 = 0x%X）'
          % (arc.ver, arc.count, arc.dir_end, arc.offsets[0], arc.offsets[-1], arc.offsets[-1] + 6))
    story = discover(arc)
    print('正文脚本  : %d 本 —— %s' % (len(story), ', '.join(sorted(story))))
    order, edges, orphans = build_order(arc, story)
    print('输出顺序  : %s' % ' → '.join(order))
    if orphans:
        print('  ⚠ 未连通（附在末尾）：%s' % ', '.join(orphans))

    stats, ev = {}, []
    for n in order[:1] + orphans:          # 只从根与未连通脚本展开（子剧本由引用点递归插入）
        ev.extend(story_events(n, story, edges, stats))

    lines = [t for _n, t in ev]
    tp = sum(s['nchar'] for s in stats.values())
    pg = sum(s['page'] for s in stats.values())
    pe = sum(s['page_empty'] for s in stats.values())
    ln = sum(s['line'] for s in stats.values())
    pa = sum(s['pause'] for s in stats.values())
    bo = sum(s['break_other'] for s in stats.values())
    ct = sum(s['ctl'] for s in stats.values())
    op = sum(s['opt'] for s in stats.values())
    tp_lines = sum(len(t[2]) for n in order for t in story[n][1])

    print('--- 逐本 ---')
    for n in order:
        s = stats[n]
        print('  %-14s %8d B  TpWord=%-3d 字=%-6d PAGE=%-4d LINE=%-4d PAUSE=%-3d 多段页=%-3d opt=%-2d 行=%-4d'
              % (n, s['lsb'], s['tp'], s['nchar'], s['page'], s['line'], s['pause'],
                 s['mpages'], s['opt'], s['lines']))
    print('--- 合计 ---')
    print('  TpWord 块 %d ／ 正文 %d 字 ／ PAGE %d（空段 %d）／ LINE %d ／ PAUSE %d ／ 其它 break %d ／ 控制符 %d'
          % (sum(s['tp'] for s in stats.values()), tp, pg, pe, ln, pa, bo, ct))
    print('  选项 %d 项 ／ 成品 %d 行 ／ %d 字' % (op, len(lines), sum(len(x) for x in lines)))
    dr = [(n, x) for n in order for x in stats[n]['opt_dropped']]
    if dr:
        print('  剔除的菜单项 %d 条（结构证据）:' % len(dr))
        for n, (off, txt, why) in dr:
            print('    %-14s 0x%06X %-24s %s' % (n, off, txt[:24], why))
    if DUAL_PAUSE:
        mp = sum(s['mpages'] for s in stats.values())
        ex = sum(s['multi'] for s in stats.values())
        print('  闭合（--dual-pause）：PAGE %d − 空段 %d = %d 屏；多段页 %d（一页换成「段行＋合并行」）'
              ' ⇒ %d + %d = %d 行；%d + 选项 %d = %d 行'
              % (pg, pe, pg - pe, mp, pg - pe, ex, pg - pe + ex,
                 pg - pe + ex, op, pg - pe + ex + op))
    elif SPLIT_LINE:
        print('  闭合（--split-line）：PAGE %d − 空段 %d = %d 屏；显示行 %d = 屏数 + %d 个屏内换行；%d + 选项 %d = %d 行'
              % (pg, pe, pg - pe, tp_lines, tp_lines - (pg - pe),
                 tp_lines, op, tp_lines + op))
    else:
        print('  闭合：PAGE %d − 空段 %d = %d，TpWord 产行 %d ⇒ %s；%d + 选项 %d = %d 行'
              % (pg, pe, pg - pe, tp_lines, 'OK' if pg - pe == tp_lines else '★不符★',
                 tp_lines, op, tp_lines + op))

    if out:
        body = ''.join(s + '\n' for s in lines)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'wb') as f:
            f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))
        print('  写出 %s（%d B, md5 %s）'
              % (out, os.path.getsize(out), hashlib.md5(open(out, 'rb').read()).hexdigest()))
    else:
        print('  （--verify：未写文件）')
    return stats, lines


def main():
    ap = argparse.ArgumentParser(description='LiveMaker 3 文本提取（多脚本 ＋ 结构性选项）')
    ap.add_argument('--exe', required=True)
    ap.add_argument('--out')
    ap.add_argument('--dual-pause', action='store_true',
                    help='把 `\\x01PAUSE` 事件当一次点击（同框继续）⇒ 一页 ≥2 段时出「段行 ＋ 合并行」双版')
    ap.add_argument('--inline-placeholder', action='store_true',
                    help='把内嵌图 TWdImg 与变量插入 TWdOpeVar 落成 ⟦IMG:…⟧ / ⟦VAR:…⟧ 占位')
    ap.add_argument('--split-line', action='store_true',
                    help='把 BreakType.LINE 也当断点（按显示行出；默认按 <PG> 一框一行）')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()
    global SPLIT_LINE, DUAL_PAUSE, INLINE_PH
    SPLIT_LINE = a.split_line
    DUAL_PAUSE = a.dual_pause
    INLINE_PH = a.inline_placeholder
    run(a.exe, None if a.verify else a.out)


if __name__ == '__main__':
    main()
