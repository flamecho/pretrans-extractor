# -*- coding: utf-8 -*-
"""Artemis Engine (iMel) 全文本提取工具 —— 以《滄海天記》(NS-JP) 定案

管线: NSP(PFS0) -> main NCA -> (Titlekey crypto) -> RomFS -> root.pfs / root.pfs.000
      -> PFS(pf8) 解包 + XOR 解密 -> script/*.ast -> 文本抽取

依赖: pycryptodome; NCA->RomFS 一步调用 hactool(可换自行实现)
   hactool -k <你的 prod.keys> -t nca --titlekey=<ENCRYPTED_TITLEKEY> --romfsdir=<dir> main.nca
   本脚本可自动从 NSP 内 .tik 推导 ENCRYPTED_TITLEKEY。

产物: UTF-8-BOM / LF / 一行一段。
  - 剧情: 每个含 text 字段的 block = 一个文本框 = 一行；select 选项各一行
  - 辞典: script/game_dic.ast (見出し 定義)
  - 系统: system/table/list_switch_ja.tbl 中日文串

—— 关键技术结论 ——
[PF8/PFS] 头部 11 字节: "pf8"(3) + u32 index_size + u32 file_count;
  条目: {u32 namelen, name, u32 sep=0, u32 offset, u32 size}; 之后 size_count 表 + 8B pad + u32 end。
  加密: key = SHA1(file[0x07 : 0x07+index_size]); **整个文件**逐字节 XOR key(20B 循环)（.mp4/.ogv 除外）。
[AST] 明文 Lua 风格: astver=2.0 / astname / root={ block_XXXXX={...} }；
  text = { ja = { { "…", {"rt2"}, {"ruby",text="かな"},"漢",{"/ruby"}, … } } }
  取 ja[0] 中所有 string 顺序拼接（丢弃 rt2/ruby/exfont 等标签与 name=）即该文本框文本。
[一次点击=一个文本框]; rt2 = 框内换行(合并)。
"""
import os, re, sys, struct, hashlib, glob, subprocess

# ---------------- PFS (pf8) ----------------
def parse_pfs(path):
    f = open(path, 'rb')
    magic = f.read(3)
    assert magic in (b'pf8', b'pf6', b'pf2'), magic
    index_size = struct.unpack('<I', f.read(4))[0]
    file_count = struct.unpack('<I', f.read(4))[0]
    entries = []
    for _ in range(file_count):
        nl = struct.unpack('<I', f.read(4))[0]
        name = f.read(nl).decode('utf-8', 'replace')
        f.read(4)  # separator
        off, size = struct.unpack('<II', f.read(8))
        entries.append((name, off, size))
    f.seek(0x07)
    key = hashlib.sha1(f.read(index_size)).digest()
    return f, entries, key


def pfs_read(f, key, off, size, name):
    f.seek(off)
    raw = f.read(size)
    if name.lower().endswith(('.mp4', '.ogv')):
        return raw
    n = len(raw)
    ks = (key * (n // len(key) + 1))[:n]
    return (int.from_bytes(raw, 'big') ^ int.from_bytes(ks, 'big')).to_bytes(n, 'big')


# ---------------- AST 解析 ----------------
class T:
    __slots__ = ('arr', 'map')

    def __init__(self):
        self.arr = []
        self.map = {}


class _P:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def skip(self):
        while self.i < len(self.s) and self.s[self.i] in ' \t\r\n':
            self.i += 1

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else ''

    def value(self):
        self.skip()
        c = self.peek()
        if c in '{[':
            return self.table()
        if c in '"\'':
            q = c
            j = self.s.index(q, self.i + 1)
            v = self.s[self.i + 1:j]
            self.i = j + 1
            return v
        m = re.match(r'-?\d+\.\d+|-?\d+', self.s[self.i:])
        if m and (c == '-' or c.isdigit()):
            v = m.group(0)
            self.i += len(v)
            return float(v) if '.' in v else int(v)
        m = re.match(r'[A-Za-z_][A-Za-z0-9_]*', self.s[self.i:])
        v = m.group(0)
        self.i += len(v)
        return v

    def table(self):
        op = self.peek()
        cl = '}' if op == '{' else ']'
        self.i += 1
        t = T()
        while True:
            self.skip()
            c = self.peek()
            if c == cl:
                self.i += 1
                break
            if c == '':
                raise ValueError('EOF in table')
            key = None
            m = re.match(r'(?:[A-Za-z_][A-Za-z0-9_]*|\[[^\]]*\])\s*=', self.s[self.i:])
            if m:
                key = m.group(0).split('=')[0].strip()
                self.i += m.end()
            val = self.value()
            if key is not None:
                t.map[key] = val
            else:
                t.arr.append(val)
            self.skip()
            if self.peek() == ',':
                self.i += 1
        return t


def parse_ast_text(s):
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    p = _P(s)
    out = {}
    while True:
        p.skip()
        if p.i >= len(s):
            break
        m = re.match(r'[A-Za-z_][A-Za-z0-9_]*\s*=', s[p.i:])
        key = m.group(0).split('=')[0].strip()
        p.i += m.end()
        out[key] = p.value()
    return out


# ---------------- 文本抽取 ----------------
def _natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def page_text(page):
    if not isinstance(page, T):
        return ''
    return ''.join(e for e in page.arr if isinstance(e, str))


def build_all(script_dir, tbl_path):
    story, dic, system = [], [], []
    for fp in sorted(glob.glob(os.path.join(script_dir, '*.ast')), key=lambda x: _natkey(os.path.basename(x))):
        bn = os.path.basename(fp)
        if bn.startswith('scene') or bn in ('pack.ast', 'brandlogo.ast', 'gamestart.ast', 'game_dic.ast'):
            continue  # scene*=回想跳转包装(重复); 其余无文本
        root = parse_ast_text(open(fp, encoding='utf-8').read()).get('ast')
        for b, blk in root.map.items():
            if not b.startswith('block_') or not isinstance(blk, T):
                continue
            sl = blk.map.get('select')
            if isinstance(sl, T) and isinstance(sl.map.get('ja'), T):
                for o in sl.map['ja'].arr:
                    if isinstance(o, str) and o.strip(' \u3000\t'):
                        story.append(o)
            t = blk.map.get('text')
            if isinstance(t, T) and isinstance(t.map.get('ja'), T):
                for pg in t.map['ja'].arr:
                    s = page_text(pg)
                    if s.strip(' \u3000\t'):
                        story.append(s)
    # 辞典
    root = parse_ast_text(open(os.path.join(script_dir, 'game_dic.ast'), encoding='utf-8').read()).get('dic')
    for b, blk in root.map.items():
        if not b.startswith('block_') or not isinstance(blk, T):
            continue
        t = blk.map.get('text')
        if not (isinstance(t, T) and isinstance(t.map.get('ja'), T) and t.map['ja'].arr):
            continue
        pg = t.map['ja'].arr[0]
        head = ''
        if isinstance(pg, T) and isinstance(pg.map.get('name'), T) and pg.map['name'].arr:
            head = pg.map['name'].arr[0]
        body = page_text(pg)
        # 辞典格式（跨作约定）：【見出し】解説，一行一条，不带读音
        dic.append(('【' + head + '】' + body) if head else body)
    # 系统/UI
    if os.path.exists(tbl_path):
        lang = parse_ast_text(open(tbl_path, encoding='utf-8').read()).get('lang')
        seen = set()
        JP = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]')

        def walk(v):
            if isinstance(v, T):
                for e in v.arr:
                    walk(e)
                for e in v.map.values():
                    walk(e)
            elif isinstance(v, str):
                s = v.replace('\\n', '').replace('\n', '')
                if JP.search(s) and s.strip(' \u3000\t') and s not in seen:
                    seen.add(s)
                    system.append(s)
        walk(lang)
    return story, dic, system


# ---------------- NSP -> RomFS ----------------
def _xts_dec(data, key, unit=0x200):
    from Crypto.Cipher import AES
    k1, k2 = key[:16], key[16:]
    a1 = AES.new(k1, AES.MODE_ECB)
    a2 = AES.new(k2, AES.MODE_ECB)

    def ma(Tv):
        c = 0
        r = 0
        for i in range(16):
            nv = (Tv >> (8 * i)) & 0xFF
            nc = (nv << 1) | c
            c = (nc >> 8) & 1
            r |= (nc & 0xFF) << (8 * i)
        if c:
            r ^= 0x87
        return r
    out = bytearray()
    for s in range((len(data) + unit - 1) // unit):
        sec = data[s * unit:(s + 1) * unit]
        Tv = int.from_bytes(a2.encrypt(s.to_bytes(16, 'big')), 'little')
        o = bytearray()
        for j in range(0, len(sec), 16):
            blk = sec[j:j + 16]
            if len(blk) < 16:
                blk += b'\0' * (16 - len(blk))
            tb = Tv.to_bytes(16, 'little')
            o += bytes(a ^ b for a, b in zip(a1.decrypt(bytes(a ^ b for a, b in zip(blk, tb))), tb))
            Tv = ma(Tv)
        out += o[:len(sec)]
    return bytes(out)


def nsp_ticket_titlekey(nsp_path):
    """返回 (加密titlekey, rights_id)（用于 hactool --titlekey）"""
    head = open(nsp_path, 'rb').read(0x20000)
    n = struct.unpack('<I', head[4:8])[0]
    strsize = struct.unpack('<I', head[8:12])[0]
    ent = 0x10
    strtab = ent + n * 0x18
    base = strtab + strsize
    for i in range(n):
        off, size, noff, _ = struct.unpack('<QQII', head[ent + i * 0x18:ent + i * 0x18 + 0x18])
        nm = head[strtab + noff:].split(b'\0')[0].decode()
        if nm.endswith('.tik'):
            with open(nsp_path, 'rb') as f:
                f.seek(base + off)
                tik = f.read(size)
            return tik[0x180:0x190]
    return None


WANT_EXT = ('.ast', '.lua', '.tbl', '.csv', '.ini', '.iet', '.asb', '.sli', '.dat')


def unpack_romfs(romfs, ext_dir):
    """把 romfs 下的 root.pfs* 解包到 ext_dir（含 XOR 解密）"""
    n = 0
    for pfsname in sorted(glob.glob(os.path.join(romfs, 'root.pfs*'))):
        if not os.path.isfile(pfsname):
            continue
        f, entries, key = parse_pfs(pfsname)
        for name, off, size in entries:
            if os.path.splitext(name)[1].lower() not in WANT_EXT:
                continue
            data = pfs_read(f, key, off, size, name)
            dst = os.path.join(ext_dir, name.replace('\\', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(data)
            n += 1
    return n


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    romfs = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(romfs), 'out')
    os.makedirs(outdir, exist_ok=True)
    # 若给定 RomFS 目录（含 root.pfs*），先解包
    if glob.glob(os.path.join(romfs, 'root.pfs*')):
        ext_dir = os.path.join(outdir, 'ext')
        print('unpacking PFS ->', ext_dir)
        print('files:', unpack_romfs(romfs, ext_dir))
        romfs = ext_dir
    story, dic, system = build_all(os.path.join(romfs, 'script'), os.path.join(romfs, 'system', 'table', 'list_switch_ja.tbl'))
    lines = story + dic + system
    p = os.path.join(outdir, '全文本.txt')
    with open(p, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('story=%d dic=%d system=%d total=%d -> %s' % (len(story), len(dic), len(system), len(lines), p))


if __name__ == '__main__':
    main()
