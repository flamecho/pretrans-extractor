#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Starry☆Sky ~Spring Memories~ (NS-JP, 0100a3d026610000) 全文本提取。

★ 本作要点（2026-10-19 首次跑通，通用结论已写进 skill / engines/platform-switch-nca.md）：
  1) NSP(PFS0) → 主 Program NCA（**Titlekey crypto**）。
     - NCA 头 AES-XTS（大端 sector tweak + rev(α) 递进），`scripts/switch_nca.py` 可直接用。
     - **内容密钥＝解密后的 titlekey 本身**（不是 key_area[i]）；
       titlekey = AES_ECB_dec(titlekek[0x14], tik[0x180:0x190])（Master Key Rev 0x14，非 ticket 0x285=0x15）。
     - Section CTR：高位 8B = fs header `@0x400+secno*0x200+0x141`，低位 8B = **绝对文件偏移/16 大端**。
     - romfs 起点 = section1 起点 + IVFC level5 offset（本作 0x1c000+0x58c000）。
  2) RomFS 元数据条目 dir=0x18 / file=0x20，**名字内联且 4 字节对齐**（advance = size + align4(namelen)）。
  3) 正文载体 = `script_dialog_ja.hdlg`（HLZS @0x200 → **HDLG** 表，UTF-8）：
     `HDLG + ver + count + dataOffset + u32 offsets[count]`，字符串内联，`<br>`=框内软换行（合并）、
     `<firstname>/<lastname>` = 主角名宏、`<firstname2>` = 第二可改名槽（默认名未证实，占位 未莉）。
     **HESE 脚本内无日文**（只有 max/min/value 之类变量名），文本全部外置在这张表里。
  4) 表结构：0..756 = UI/系统串（TRANS_* 键、日期、章題、改名提示）；757.. = 正文（en 键表为
     `TRANS_W000_0000_0` … `TRANS_W169_0080_0`，共 28,788 条 = 169 个脚本块），之后为收尾场景。

用法:
  python scripts/sspm_extract.py <nsp 或 nca> [--name 月子] [--out 输出.txt] [--dump-dir DIR]
"""
import sys, os, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import switch_nca as S
from Crypto.Cipher import AES
from Crypto.Util import Counter

KEYSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_sw', 'prod_fixed.keys')
MASTER_KEY_REV = 0x14          # hactool 打印 Master Key Revision，非 ticket 0x285
STORY_START = 757              # 正文起点（UI 表 0..756）
MACROS = {'<firstname>': '月子', '<lastname>': '夜久',
          '<firstname2>': '未莉', '<lastname2>': '夜久'}


# ---------------------------------------------------------------- 容器层
def pfs0_entries(path):
    with open(path, 'rb') as f:
        assert f.read(4) == b'PFS0'
        n, ss, _ = struct.unpack('<3I', f.read(12))
        ents = [struct.unpack('<QQII', f.read(24)) for _ in range(n)]
        st = f.read(ss)
        base = 0x10 + n * 0x18 + ss
    out = {}
    for off, size, no, _r in ents:
        out[st[no:st.find(b'\x00', no)].decode()] = (base + off, size)
    return out


class Sub:
    """NSP 内某个成员的只读视图。"""

    def __init__(self, path, base, size):
        self.f = open(path, 'rb')
        self.base, self.size, self.pos = base, size, 0

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b''
        self.f.seek(self.base + self.pos)
        d = self.f.read(n)
        self.pos += len(d)
        return d

    def seek(self, p, w=0):
        self.pos = p
        return p

    def tell(self):
        return self.pos


class Nca:
    def __init__(self, nsp, off, size, tik):
        self.f = Sub(nsp, off, size)
        keys = S.load_keys(KEYSET)
        self.keys = keys
        self.hdr = S.xts_decrypt(bytes.fromhex(keys['header_key'][:32]),
                                 bytes.fromhex(keys['header_key'][32:64]), 0, self.f.read(0x1600))
        assert self.hdr[0x200:0x204] == b'NCA3'
        self.secs = []
        for i in range(4):
            e = self.hdr[0x240 + i * 0x10:0x250 + i * 0x10]
            self.secs.append((int.from_bytes(e[0:4], 'little') * 0x200,
                              int.from_bytes(e[4:8], 'little') * 0x200))
        t = open(tik, 'rb').read()
        self.titlekey = S.AES.new(bytes.fromhex(keys['titlekek_%02x' % MASTER_KEY_REV]),
                                  S.AES.MODE_ECB).decrypt(t[0x180:0x190])
        self.key = self.titlekey
        self.ctr_hi = self.hdr[0x600 + 0x141:0x600 + 0x149]
        self.sec_off = self.secs[1][0]
        lv = [struct.unpack_from('<QQII', self.hdr, 0x618 + 0x18 * i) for i in range(6)]
        self.lv5 = lv[5][0]
        self.romfs = self.sec_off + self.lv5

    def read(self, off, ln):
        a = self.romfs + off
        ctr = self.ctr_hi + (a // 16).to_bytes(8, 'big')
        c = AES.new(self.key, AES.MODE_CTR,
                    counter=Counter.new(128, initial_value=int.from_bytes(ctr, 'big')))
        pad = a % 16
        self.f.seek(a - pad)
        raw = self.f.read(ln + pad)
        return c.decrypt(raw)[pad:pad + ln]

    # ---------------- RomFS
    def files(self):
        v = struct.unpack('<10Q', self.read(0, 0x50))
        dm, fm = self.read(v[3], v[4]), self.read(v[7], v[8])

        def al(x):
            return (x + 3) & ~3

        dirs, out = [], []
        off = 0
        while off + 0x18 <= len(dm):
            parent, sib, child, fno, h, nl = struct.unpack_from('<IIIIII', dm, off)
            dirs.append([parent, dm[off + 0x18:off + 0x18 + nl].decode('utf-8', 'replace')])
            off += 0x18 + al(nl)

        def dpath(i):
            parts, seen = [], set()
            while i < len(dirs) and i not in seen:
                seen.add(i)
                parts.append(dirs[i][1])
                if dirs[i][0] == i:
                    break
                i = dirs[i][0]
            return '/'.join(reversed(parts))

        off = 0
        while off + 0x20 <= len(fm):
            parent, sib, dof, dsz, h, nl = struct.unpack_from('<IIQQII', fm, off)
            nm = fm[off + 0x20:off + 0x20 + nl].decode('utf-8', 'replace')
            base = dpath(parent) if parent < len(dirs) else ''
            out.append(((base + '/' if base else '/') + nm, dof, dsz))
            off += 0x20 + al(nl)
        return out

    def read_file(self, off, size):
        out = bytearray()
        pos = 0
        while pos < size:
            d = self.read(off + pos, min(1 << 22, size - pos))
            if not d:
                break
            out += d
            pos += len(d)
        return bytes(out)


# ---------------------------------------------------------------- HLZS / HDLG
def hlzs_decompress(buf, dec_size):
    dic = bytearray(0x1000)
    out = bytearray()
    flag8 = 1
    ip = 0
    dp = 0
    n = len(buf)
    try:
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
    except IndexError:
        pass                       # 本作 ja 表尾部压缩流比声明短 ~486B ⇒ 末 1 条被截断（已记录）
    return bytes(out)


def load_hdlg(raw):
    base = raw.find(b'HLZS')          # 本作 HDLG/HLZS 块前有 0x200 字节前缀
    assert base >= 0, 'no HLZS'
    _m, _v, enc, dec = struct.unpack_from('<4I', raw, base)
    body = hlzs_decompress(raw[base + 0x20:], dec)
    magic, ver, cnt, dof = struct.unpack_from('<4sIII', body, 0)
    assert magic == b'HDGL', magic
    offs = [struct.unpack_from('<I', body, 0x10 + 4 * i)[0] for i in range(cnt)]
    strings = []
    for o in offs:
        p = dof + o
        if p >= len(body):
            strings.append(None)
            continue
        e = body.find(b'\x00', p)
        if e < 0:
            e = len(body)
        strings.append(body[p:e].decode('utf-8', 'replace'))
    return strings


def main():
    src = sys.argv[1]
    name = '月子'
    out_path = None
    dump_dir = None
    for a in sys.argv[2:]:
        if a.startswith('--name='):
            name = a.split('=', 1)[1]
        elif a.startswith('--out='):
            out_path = a.split('=', 1)[1]
        elif a.startswith('--dump-dir='):
            dump_dir = a.split('=', 1)[1]

    if src.lower().endswith('.nsp'):
        ents = pfs0_entries(src)
        big = max(ents.items(), key=lambda kv: kv[1][1])
        tik = [v for k, v in ents.items() if k.endswith('.tik')][0]
        # 需要 tik 落地才能读
        tmp_tik = os.path.join(os.path.dirname(os.path.abspath(out_path or 'x')), '_titlekey.tik')
        os.makedirs(os.path.dirname(tmp_tik), exist_ok=True)
        with open(src, 'rb') as f:
            f.seek(tik[0])
            open(tmp_tik, 'wb').write(f.read(tik[1]))
        nca = Nca(src, big[1][0], big[1][1], tmp_tik)
    else:
        tik = None
        d = os.path.dirname(src)
        for n in os.listdir(d):
            if n.endswith('.tik'):
                tik = os.path.join(d, n)
        keys = S.load_keys(KEYSET)
        self_hdr = S.xts_decrypt(bytes.fromhex(keys['header_key'][:32]),
                                 bytes.fromhex(keys['header_key'][32:64]), 0,
                                 open(src, 'rb').read(0x1600))
        # 复用 Nca：把 nca 当 NSP 成员、基址 0
        nca = Nca.__new__(Nca)
        nca.f = open(src, 'rb')
        nca.keys = keys
        nca.hdr = self_hdr
        nca.secs = []
        for i in range(4):
            e = self_hdr[0x240 + i * 0x10:0x250 + i * 0x10]
            nca.secs.append((int.from_bytes(e[0:4], 'little') * 0x200,
                             int.from_bytes(e[4:8], 'little') * 0x200))
        t = open(tik, 'rb').read()
        nca.titlekey = S.AES.new(bytes.fromhex(keys['titlekek_%02x' % MASTER_KEY_REV]),
                                 S.AES.MODE_ECB).decrypt(t[0x180:0x190])
        nca.key = nca.titlekey
        nca.ctr_hi = self_hdr[0x600 + 0x141:0x600 + 0x149]
        nca.sec_off = nca.secs[1][0]
        lv = [struct.unpack_from('<QQII', self_hdr, 0x618 + 0x18 * i) for i in range(6)]
        nca.lv5 = lv[5][0]
        nca.romfs = nca.sec_off + nca.lv5

    print('[i] titlekey=%s romfs@0x%x' % (nca.titlekey.hex(), nca.romfs))
    files = {n: (o, s) for n, o, s in nca.files()}
    for k in sorted(files):
        print('    %-32s %10d' % (k, files[k][1]))

    raw_ja = nca.read_file(*files['/script_dialog_ja.hdlg'])
    raw_en = nca.read_file(*files['/script_dialog_en.hdlg'])
    if dump_dir:
        os.makedirs(dump_dir, exist_ok=True)
        open(os.path.join(dump_dir, 'script_dialog_ja.hdlg'), 'wb').write(raw_ja)
        open(os.path.join(dump_dir, 'script_dialog_en.hdlg'), 'wb').write(raw_en)

    ja = load_hdlg(raw_ja)
    keys_s = load_hdlg(raw_en)
    print('[i] HDLG entries=%d（ja）' % len(ja))

    # 用 en 键表验证结构（本作 en/zhcn 只有键名，未翻译）
    wpat = re.compile(r'TRANS_W\d{3}_\d{4}_\d')
    widx = [i for i, k in enumerate(keys_s) if k and wpat.fullmatch(k)]
    print('[i] en 键表 TRANS_W* = %d 条，范围 %s..%s' % (len(widx), widx[0], widx[-1]))

    lines = []
    dropped = 0
    tail_bad = 0
    for i in range(STORY_START, len(ja)):
        t = ja[i]
        if t is None:
            tail_bad += 1
            continue
        t = t.replace('<br>', '')
        for k, v in MACROS.items():
            t = t.replace(k, name if k in ('<firstname>', '<firstname2>') else v)
        t = t.strip()
        if '\ufffd' in t:          # 压缩流尾部截断造成的残行，整行丢弃
            tail_bad += 1
            continue
        if not t or t == '\u3000':
            dropped += 1
            continue
        lines.append(t)

    out_path = out_path or '提取结果/[NS-JP]Starry☆Sky ~Spring Memories~_全文本.txt'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('[+] %s  行数=%d（空/%s 跳过=%d，尾部残缺=%d）' % (out_path, len(lines), dropped, dropped, tail_bad))


if __name__ == '__main__':
    main()
