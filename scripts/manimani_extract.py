#!/usr/bin/env python3
"""花咲くまにまに (PSV, PCSG00366, MAGES. / SC3) 文本提取。

链路：
  1) PKG 层 → psvpfsparser 解密得明文 MPK（本脚本不负责，见报告）
  2) MPK 容器 (magic "MPK\\0", 每文件 zlib) → 解出 .scr
  3) SC3 脚本：header = "SC3\\0" + i32 OffsetStart + i32 OffsetEnd；
     偏移表 = [OffsetStart, OffsetEnd) 的 u32 绝对偏移；字符串 = 到下一偏移。
  4) 文本编码：自定义 16bit 码表 = eboot.elf 内联 Unicode 表（起于 ELF 0x751D0，
     码 = 0x8025 + 表内索引）。0x8000-0x8024 与 0x20xx 为控制码。

用法：
  python scripts/manimani_extract.py charset <eboot.elf> <out.tbl>
  python scripts/manimani_extract.py extract <mpkdir> <eboot.elf> <outdir>
"""
import os, sys, struct, zlib

MPK_MAGIC = b'MPK\x00'
TBL_START = 0x751D0
TBL_BASE = 0x8025

# ---------------- MPK ----------------
def mpk_extract(path, outdir):
    d = open(path, 'rb').read()
    assert d[:4] == MPK_MAGIC
    n = struct.unpack('<Q', d[8:16])[0]
    os.makedirs(outdir, exist_ok=True)
    for i in range(n):
        e = 64 + i * 256
        flag, off, csize, usize = struct.unpack('<IIII', d[e:e + 16])
        name = d[e + 32:e + 256].split(b'\0')[0].decode('utf8')
        blk = d[off:off + csize]
        data = zlib.decompress(blk) if flag == 1 else blk
        assert len(data) == usize, (name, len(data), usize)
        open(os.path.join(outdir, name), 'wb').write(data)
    return n

# ---------------- SC3 ----------------
def sc3_strings(path):
    d = open(path, 'rb').read()
    if d[:4] != b'SC3\x00':
        return []
    a, b = struct.unpack('<ii', d[4:12])
    if a == b:
        return []
    offs = [struct.unpack('<I', d[o:o + 4])[0] for o in range(a, b, 4)]
    return [d[offs[i]:(offs[i + 1] if i + 1 < len(offs) else len(d))] for i in range(len(offs))]

# ---------------- charset ----------------
# ★ 关键：引擎码表 = 字体字形序列（`槽 = 码 - 0x8000`），与 eboot 内联 Unicode 表 T（起于 0x751D0）
#   在低区**同序**、在高区**相差 37**（字体另有 37 个 T 未收录的字形，插在槽 89..125）。
#   ⇒ 码 ≤ 0x8058：char = T[码-0x8000]；码 ≥ 0x807E：char = T[码-0x8025]；
#      0x8059..0x807D（该 37 个仅字体有的字形）脚本从未使用，留空。
#   依据（已知明文双向确证）：
#     0x8017→M 0x803D→y 0x803F→' ' 0x8032→n 0x8025→a 0x8031→m 0x8029→e 0x802D→i 0x8037→s 0x8021→W
#     0x8039→u 0x802F→k 0x801E→T 0x8047→'.'  ⇒  密码串 = "My name is Wasuke Tani."
#     0x8031/0x8025/0x8036/0x802D/0x8032/0x8025 ⇒ "marina"（ED「泡沫ノ花」歌：marina）
#     0x8084→４ 0x8096→Ｍ 0x808B→Ｂ（"空き容量が４ＭＢ以上必要です。"）⇒ 高区用 0x8025
#   表尾 4 码（0x8F3F..0x8F42）为字体尾部独有字形，由字形目视 + Cmap 确证。
OVERRIDE = {0x8F3F: '澤', 0x8F40: '跪', 0x8F41: '躱', 0x8F42: '巫'}

def build_charset(elf_path, max_slot=4200):
    d = open(elf_path, 'rb').read()
    def T(i):
        o = TBL_START + i * 2
        if i < 0 or o + 2 > len(d):
            return 0
        return d[o] | (d[o + 1] << 8)
    cs = {}
    for code in range(0x8000, 0x8000 + max_slot):
        if 0x8059 <= code <= 0x807D:
            continue                      # 37 个仅字体有的字形（脚本未使用）
        idx = code - 0x8000 if code <= 0x8058 else code - 0x8025
        v = T(idx)
        if v:
            cs[code] = chr(v)
    cs.update(OVERRIDE)
    return cs

NOARG = {0x03, 0x05, 0x06, 0x08, 0x09, 0x0a, 0x0b, 0x0e, 0x0f, 0x18, 0x1e, 0x1f, 0xff}
ARG2 = {0x0c, 0x11, 0x12, 0x13, 0x14, 0x16, 0x19, 0x1a}
LINEBREAK = {0x8000}          # 框内换行 → 合并
NAMEMACRO = {0x2000: '望月', 0x2001: '七緒'}   # 主角 姓 / 名
UNRESOLVED = '〔未解析〕'

def _chars(s, i, n, cs):
    """读一个字符，返回 (text, new_i)。"""
    if i + 1 >= n:
        return UNRESOLVED, n
    c = (s[i] << 8) | s[i + 1]
    return cs.get(c, UNRESOLVED if c < 0x8025 else '[%04X]' % c), i + 2

def decode(s, cs, want_name=False):
    """返回 (name, text)。name 为名札（无则 None）；text 已合并框内换行、内联主角名。"""
    out = []
    name = None
    i, n = 0, len(s)
    while i < n:
        b = s[i]
        if b == 0x01:
            i += 1
            nm = []
            while i < n and s[i] != 0x02:
                if s[i] >= 0x80 or s[i] == 0x20:
                    t, i = _chars(s, i, n, cs); nm.append(t)
                else:
                    nm.append('{%02X}' % s[i]); i += 1
            i += 1
            name = ''.join(nm)
            if want_name:
                out.append('〔%s〕' % name)
        elif b == 0x02:
            i += 1
        elif b in NOARG:
            i += 1
        elif b == 0x04:
            i += 4
        elif b == 0x07:
            i += 2
        elif b in ARG2:
            i += 3
        elif b == 0x15:
            j = i + 1
            while j < n:
                c = s[j]
                if c == 0: j += 1; break
                j += 1 + ((c >> 5) & 3) if c & 0x80 else 1
            i = j
        elif b == 0x1b:
            i += 2
        else:
            if i + 1 >= n:
                break
            c = (s[i] << 8) | s[i + 1]; i += 2
            if c in LINEBREAK:
                pass                       # 框内换行：合并
            elif c in NAMEMACRO:
                out.append(NAMEMACRO[c])
            else:
                out.append(cs.get(c, UNRESOLVED if c < 0x8025 else '[%04X]' % c))
    return name, ''.join(out)

STORY = ('hm00_', 'hm01_', 'hm02_', 'hm03_', 'hm04_', 'hm05_', 'hmv_')

# 原文笔误（照原始字节确证：行首 0x80CC「（」、行尾 0x80D9「」」）→ 整行定值修，勿正则泛修
FIXES = {
    '（白玖さん……もしかして潔癖なのかな……？」': '（白玖さん……もしかして潔癖なのかな……？）',
    '（まあ、おかげで酉の市をゆっくり見てから帰れるよね」': '（まあ、おかげで酉の市をゆっくり見てから帰れるよね）',
}

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'charset':
        cs = build_charset(sys.argv[2])
        with open(sys.argv[3], 'w', encoding='utf8') as f:
            for c in sorted(cs):
                f.write('%04X=%s\n' % (c, cs[c]))
        print('charset entries', len(cs))
    elif cmd == 'extract':
        print('extracted', mpk_extract(sys.argv[2], sys.argv[3]))
    elif cmd == 'dump':
        cs = build_charset(sys.argv[3])
        for k, s in enumerate(sc3_strings(sys.argv[2])):
            nm, tx = decode(s, cs)
            print('%4d %s| %s' % (k, ('[%s]' % nm) if nm else '', tx))
    elif cmd == 'text':
        # text <scr_dir> <eboot.elf> <out.txt> [--with-names]
        srcdir, elf, out = sys.argv[2], sys.argv[3], sys.argv[4]
        withnames = '--with-names' in sys.argv
        cs = build_charset(elf)
        lines = []
        files = sorted(f for f in os.listdir(srcdir) if f.endswith('.scr'))
        story = [f for f in files if f.startswith(STORY)]
        for f in story:
            for s in sc3_strings(os.path.join(srcdir, f)):
                nm, tx = decode(s, cs, want_name=withnames)
                tx = tx.strip()
                tx = FIXES.get(tx, tx)
                if tx:
                    lines.append(tx)
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as fp:
            fp.write('\n'.join(lines) + '\n')
        print('files', len(story), 'lines', len(lines))
