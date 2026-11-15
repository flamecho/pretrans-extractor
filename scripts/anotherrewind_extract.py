#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""anotherrewind_extract.py —— [JP]Another Rewind（LiveMaker / LiveNovel）正文+选项提取

链路
----
外层 `[JP]Another Rewind.exe`（PE + RAR5 SFX）
  → 内层 `AnotherRewind.exe`（PE，overlay = VF 归档）
  → VF 目录（TTpRandom 混淆）解出 `00000001.lsb`
  → 扫描自定界的 `TpWord` 块（1,892 个，= 1,892 条 TextIns）
  → 按 `TWdOpeReturn.break_type` 分框
  → 选项：`AddArray(_tmp, …)` 参数被编译器提升为临时变量 `____N`，
     用 `To(____N)=Str` 回配；按 `選択メニュー\\■選択実行.lsb` 调用点分组

断框判据（代码级，非内容猜测）
------------------------------
* 断框 = `TWdOpeReturn.break_type == 1`（`BreakType.PAGE`，LNS 记作 `<PG>`）
  依据：本作自带的消息框状态机 `ノベルシステム\\メッセージボックス\\アイドル時.lsb`
        - 点击事件（`@KeyClick[256]` / `@LClick` / `@KeyClick[13]`）分支里
          `GetProp(メッセージボックス, 44)` 是**当前页索引**、`45` 是**页数**：
          `If n < GetProp(…,45)-1` ⇒ `SetProp …,44 n+1`（只翻页、**不** `TextClr`）
          否则 `TextClr メッセージボックス`。
* 同框内「继续」= `{PAUSE}`（`TWdOpeEvent`）⇒ **不**是框界
  依据：同上文件 `If S == "一時停止"` 分支只 `SetProp …,81 0`，随后
        `SetProp …,82 StatusTextSpeed`（恢复打字），**不动 prop 44**；
        `イベント.lsb` 里 `If @ParamStr[0]=="PAUSE"` ⇒ 显示 `メッセージ続き.gal` + `SetProp 81 1`。
* 框内换行 = `break_type == 0`（`BreakType.LINE`，LNS 记作 `<BR>`）⇒ 一律合并（不拆）。
* `FACE` / `CREATECG` / `PLAYSND` / `WAIT` / `QUAKE` / 空名（关标签）等 `TWdOpeEvent` 不产生框界。

用法
----
    python scripts/anotherrewind_extract.py                       # 提取到默认路径
    python scripts/anotherrewind_extract.py --exe <路径> --out <路径>
    python scripts/anotherrewind_extract.py --verify              # 全链路自检（不写文件）
"""
import argparse
import hashlib
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import subprocess
import sys
import tempfile
import zlib

# ---------------------------------------------------------------- 常量
VF_SEED = 0x75D6EE39          # TTpRandom / LMObfuscator 种子（实测）
STORY = '00000001.lsb'        # 唯一承载正文的脚本
CTL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')   # 剥离（保留文本，见 skill S4 §20）
DEFAULT_EXE = os.path.join(VNTRANS_HOME, '还没做/[JP]Another Rewind.exe')
DEFAULT_OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]Another Rewind.txt')
INNER_EXE = 'AnotherRewind.exe'
MENU_CALL = 'ノベルシステム\\選択メニュー\\■選択実行.lsb'
SEVENZIP = [
    r'C:\Program Files\7-Zip\7z.exe',
    r'C:\Program Files (x86)\7-Zip\7z.exe',
    r'C:\Program Files\WinRAR\WinRAR.exe',
]


# ---------------------------------------------------------------- 小工具
def u32(b, p):
    return struct.unpack_from('<I', b, p)[0]


def pstr(b, p):
    """u32 长度 + cp932 串。返回 (str, 新位置)。"""
    n = u32(b, p)
    return b[p + 4:p + 4 + n].decode('cp932', 'replace'), p + 4 + n


def skip_pstr(b, p):
    return p + 4 + u32(b, p)


def _keystream(seed=VF_SEED):
    """LMObfuscator._keystream：key = (key*5 + seed) & 0xFFFFFFFF，key0 = 0。"""
    key = 0
    while True:
        key = ((key << 2) + key + seed) & 0xFFFFFFFF
        yield key


class Xor:
    """一条独立的混淆流（文件名 / offset_low / offset_high 各用一条）。"""

    __slots__ = ('ks',)

    def __init__(self):
        self.ks = _keystream()

    def raw_bytes(self, data):
        return bytes(x ^ (next(self.ks) & 0xFF) for x in data)

    def raw_int(self, data):
        key = next(self.ks)
        return bytes(x ^ ((key >> (8 * i)) & 0xFF) for i, x in enumerate(data))


# ---------------------------------------------------------------- PE / RAR5
def pe_overlay(d):
    """返回 PE 映像末尾（overlay 起点）= max(PointerToRawData + SizeOfRawData)。"""
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
    """外层 RAR5 SFX ⇒ 解出内层 exe，返回其路径（解到临时目录）。"""
    exe = next((p for p in SEVENZIP if os.path.isfile(p)), None)
    if not exe:
        raise SystemExit(
            '输入是 RAR5 SFX，本机未找到 7-Zip/WinRAR。请先手工解出内层 %s，\n'
            '再用 --exe 指向它；或安装 7-Zip 后重跑。' % INNER_EXE)
    tmp = tempfile.mkdtemp(prefix='_ar_rar_')
    cmd = [exe, 'x', '-y', '-bso0', '-bsp0', '-o' + tmp, path]
    print('  解 RAR5 →', tmp)
    r = subprocess.run(cmd, capture_output=True)
    hit = None
    for root, _dirs, files in os.walk(tmp):
        for f in files:
            if f.lower() == INNER_EXE.lower():
                hit = os.path.join(root, f)
    if not hit:
        raise SystemExit('RAR 解包失败（返回码 %s）：%s' % (r.returncode, r.stderr[-400:].decode('cp932', 'replace')))
    return hit


# ---------------------------------------------------------------- VF 归档
class VFArchive:
    """LiveMaker VF 归档目录。参考 pylivemaker/livemaker/archive.py:LMArchiveDirectory。"""

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

        # ★ offset_low 与 offset_high 各用**独立**混淆流（参考实现是两个 LMObfuscator 实例）
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
        """目录闭合自检：首项 offset == 目录末、末项 + trailer == 归档总长、offset 单调。"""
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
        raise ValueError('%s: 不支持的 compress_type=%d' % (name, ct))


# ---------------------------------------------------------------- TpWord
def parse_tpword(b, o, end):
    """解析一个自定界的 TpWord 块。

    返回 (pages, nchar, stat)。pages = 按 BreakType.PAGE 切开的非空框文（框内 LINE 已合并）。
    结构参考 pylivemaker/livemaker/lsb/novel.py:TpWord._struct（本作 version = 102）。
    """
    p = o
    if b[p:p + 6] != b'TpWord':
        raise ValueError('TpWord 签名不符 @%#x' % p)
    p += 6
    ver = int(b[p:p + 3]); p += 3

    n = u32(b, p); p += 4                                  # decorators
    for _ in range(n):
        p += 16                                            # count / unk2 / unk3 / unk4
        p += 2                                             # unk5 / unk6
        p += 1 if ver < 100 else 4                         # unk7
        p = skip_pstr(b, p)                                # unk8
        p = skip_pstr(b, p)                                # ruby
        if ver >= 100:
            p += 8                                         # unk10 / unk11
    if ver >= 104:                                         # conditions
        n = u32(b, p); p += 4
        for _ in range(n):
            p += 4
            p = skip_pstr(b, p)
    if ver >= 105:                                         # links
        n = u32(b, p); p += 4
        for _ in range(n):
            p += 4
            p = skip_pstr(b, p)
            p = skip_pstr(b, p)

    n = u32(b, p); p += 4                                  # body
    pages = []
    cur = []
    nchar = 0
    st = {'pause': 0, 'line': 0, 'page': 0, 'page_empty': 0,
          'break_other': 0, 'event': 0, 'glyph_other': 0, 'ctl': 0}
    for _ in range(n):
        t = b[p]; p += 1
        if ver >= 104:
            p += 4                                         # condition
        if t == 0x01:                                      # TWdChar
            if ver < 105:
                p = skip_pstr(b, p)                        # link_name
            else:
                p += 4                                     # link
            p += 4                                         # text_speed
            code = struct.unpack_from('<H', b, p)[0]; p += 2
            p += 4                                         # decorator
            ch = code.to_bytes(2, 'big').decode('cp932')
            if ch.startswith('\x00'):
                ch = ch[1]
            nchar += 1
            if CTL.match(ch):                              # 控制符剥离、文本保留
                st['ctl'] += 1
            else:
                cur.append(ch)
        elif t == 0x02:                                    # TWdOpeDiv
            p += 1                                         # align
            if ver >= 105:
                p += 9                                     # padleft / padright / noheight
        elif t == 0x03:                                    # TWdOpeReturn
            bt = b[p]; p += 1
            if bt == 1:                                    # BreakType.PAGE ⇒ 断框
                s = ''.join(cur).strip(' \t\r\n')
                if s:
                    pages.append(s)
                else:
                    st['page_empty'] += 1                  # 连续 <PG> / 空段：不产行（对账用）
                cur = []
                st['page'] += 1
            elif bt == 0:                                  # BreakType.LINE ⇒ 框内换行，合并
                st['line'] += 1
            else:
                st['break_other'] += 1
        elif t in (0x04, 0x05):                            # Indent / Undent
            pass
        elif t == 0x06:                                    # TWdOpeEvent
            ev, p = pstr(b, p)
            st['event'] += 1
            if ev.split('\r\n')[0].lstrip('\x01') == 'PAUSE':
                st['pause'] += 1
        elif t in (0x07, 0x0A):                            # TWdOpeVar / HistChar
            p += 4                                         # decorator
            if ver > 100:
                p += 4                                     # unk3
            if 100 < ver < 105:
                p = skip_pstr(b, p)                        # link_name
            if ver >= 105:
                p += 4                                     # link
            if ver < 102:
                raise NotImplementedError('TpWord %d 的 var_name_params 未实现' % ver)
            p = skip_pstr(b, p)                            # var_name
            st['glyph_other'] += 1
        elif t == 0x09:                                    # TWdImg
            if ver < 105:
                p = skip_pstr(b, p)                        # link_name
            else:
                p += 4
            p += 4                                         # text_speed
            p = skip_pstr(b, p)                            # src
            p += 1                                         # align
            if ver >= 103:
                p = skip_pstr(b, p)                        # hoversrc
            if ver >= 105:
                p += 16
                p = skip_pstr(b, p)                        # downsrc
            st['glyph_other'] += 1
        else:
            st['glyph_other'] += 1                         # 未知 type 只占 1 字节

    if cur:
        s = ''.join(cur).strip(' \t\r\n')
        if s:
            pages.append(s)
    if p != end:
        raise ValueError('TpWord 长度不符：解析到 %#x，块末 %#x' % (p, end))
    return pages, nchar, st


def scan_tpwords(b):
    """扫描全部自定界的 TpWord 块。返回 [(offset, end, pages, nchar, stat)]。

    闭合判据：块前 u32 长度前缀 == 解析实际消耗字节数（否则视为误命中并跳过）。
    """
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
            pages, nchar, st = parse_tpword(b, i, end)
        except (ValueError, UnicodeDecodeError, struct.error):
            continue
        out.append((i - 4, end, pages, nchar, st))
    return out


# ---------------------------------------------------------------- 选项
def scan_choices(b):
    """扫出全部菜单。返回 [(offset, [选项…])]。

    LiveParser 把 `AddArray(_tmp, "字面")` 编译成
        To(____k) = Str "字面"            （OpeDataType.To=0x01，name=____k，count=1，Param Str）
        Func(____k+1) = AddArray(_tmp, ____k)   （type=0x0B，count=2，func=0x42）
    菜单分组用调用点（`選択メニュー\\■選択実行.lsb` 的 cp932 串）做锚点：
    落在 (上一调用点, 本调用点) 区间内的 AddArray 即本菜单的选项。
    """
    # 1) 全部 To(____N) = Str
    tos = []
    p = 0
    while True:
        o = b.find(b'\x01\x05\x00\x00\x00____', p)
        if o < 0:
            break
        name, q = pstr(b, o + 1)
        if b[q:q + 4] == b'\x01\x00\x00\x00' and b[q + 4] == 0x04:
            val, _ = pstr(b, q + 5)
            tos.append((o, name, val))
        p = o + 1

    # 2) 全部 AddArray(_tmp, ____M)
    recs = []
    p = 0
    while True:
        j = b.find(b'\x0b\x05\x00\x00\x00____', p)
        if j < 0:
            break
        name, k = pstr(b, j + 1)
        if b[k:k + 4] == b'\x02\x00\x00\x00' and b[k + 4] == 0x42:
            m = k + 5
            if b[m] == 0x00 and b[m + 1:m + 5] == b'\x04\x00\x00\x00' and b[m + 5:m + 9] == b'_tmp':
                # 第 2 个操作数：Param(Var, "____M") = type(0x00) + u32 长度 + 串
                arg, _ = pstr(b, m + 10)
                recs.append((j, arg))
        p = j + 1

    # 3) 用调用点分组
    key = MENU_CALL.encode('cp932')
    calls = []
    p = -1
    while True:
        p = b.find(key, p + 1)
        if p < 0:
            break
        calls.append(p)

    menus = []
    prev = 0
    for c in calls:
        vals = []
        for off, arg in recs:
            if prev <= off < c:
                cand = [t for t in tos if t[0] < off and t[1] == arg]
                if cand:
                    vals.append(cand[-1][2])
        if vals:
            first = next(off for off, arg in recs if prev <= off < c)
            menus.append((first, vals))
        prev = c
    return menus, len(tos), len(recs), len(calls)


# ---------------------------------------------------------------- 主流程
def load_lsb(exe):
    """从 exe 里取出 STORY 对应的 .lsb 字节。"""
    d = open(exe, 'rb').read()
    ov = pe_overlay(d)
    if d[ov:ov + 2] == b'vf':
        blob = d[ov:]
    elif d[ov:ov + 7] == b'Rar!\x1a\x07\x01':
        inner = unwrap_rar(exe)
        return load_lsb(inner)
    else:
        raise SystemExit('overlay 既不是 VF 也不是 RAR5：%r' % d[ov:ov + 8])

    arc = VFArchive(blob)
    errs = arc.check()
    if errs:
        raise SystemExit('VF 目录自检失败：' + '；'.join(errs))
    if STORY not in arc.index:
        raise SystemExit('归档里没有 %s' % STORY)
    return arc.read(STORY), arc


def build(exe):
    lsb, arc = load_lsb(exe)
    tps = scan_tpwords(lsb)
    menus, n_to, n_rec, n_call = scan_choices(lsb)

    events = []
    for off, end, pages, nchar, st in tps:
        for s in pages:
            events.append((off, 0, s))
    for off, vals in menus:
        for k, s in enumerate(vals):
            events.append((off, 1 + k / 100.0, s))
    events.sort(key=lambda x: (x[0], x[1]))

    lines = [e[2] for e in events]
    stat = {
        'arc': arc,
        'lsb': len(lsb),
        'tp': len(tps),
        'nchar': sum(t[3] for t in tps),
        'pause': sum(t[4]['pause'] for t in tps),
        'line': sum(t[4]['line'] for t in tps),
        'page': sum(t[4]['page'] for t in tps),
        'page_empty': sum(t[4]['page_empty'] for t in tps),
        'brk_other': sum(t[4]['break_other'] for t in tps),
        'ctl': sum(t[4]['ctl'] for t in tps),
        'to': n_to, 'rec': n_rec, 'call': n_call,
        'menus': len(menus), 'choices': sum(len(v) for _, v in menus),
        'lines': len(lines),
        'chars': sum(len(s) for s in lines),
    }
    return lines, stat


def write_text(path, lines):
    body = ''.join(s + '\n' for s in lines)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description='[JP]Another Rewind 文本提取')
    ap.add_argument('--exe', default=DEFAULT_EXE)
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--verify', action='store_true', help='只做全链路自检，不写文件')
    a = ap.parse_args()

    if not os.path.isfile(a.exe):
        raise SystemExit('找不到：%s' % a.exe)
    lines, st = build(a.exe)
    arc = st['arc']

    print('VF 归档   : ver=%d, %d 项, 目录末 %#x, 首项 %#x, 末项 %#x（+6 = %#x）'
          % (arc.ver, arc.count, arc.dir_end, arc.offsets[0], arc.offsets[-1], len(arc.blob)))
    print('剧本      : %s  %d B（compress_type=%d）' % (STORY, st['lsb'], arc.ctypes[arc.index[STORY]]))
    print('TpWord    : %d 块，%d 字' % (st['tp'], st['nchar']))
    print('断框 token: PAGE=%d（其中 %d 次落在空段，不产行）  LINE=%d（合并）  PAUSE=%d（同框继续，合并）  其它 break=%d'
          % (st['page'], st['page_empty'], st['line'], st['pause'], st['brk_other']))
    print('控制符    : 剥离 %d 个（保留文本）' % st['ctl'])
    print('选项      : 调用点 %d / AddArray %d / To(____N) %d ⇒ %d 菜单 %d 项'
          % (st['call'], st['rec'], st['to'], st['menus'], st['choices']))
    print('成品      : %d 行，%d 字' % (st['lines'], st['chars']))

    if a.verify:
        print('（--verify：未写文件）')
        return 0

    md5 = write_text(a.out, lines)
    print('写出      : %s  md5=%s' % (a.out, md5))
    return 0


if __name__ == '__main__':
    sys.exit(main())
