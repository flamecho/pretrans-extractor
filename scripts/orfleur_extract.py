#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
オルフレール ～幸福の花束～ (PSV PCSG00919 / dramatic create「Orfre」DCVM) 文本提取
链路: rom/<name>.rom (1024B 页 + 12B 页头) -> 块 (zlib / ZPZP 容器 / 原始 DCVM)
      -> DCVM 段 (DCVM/STOR/PTBL/PSTR/[VTBL]/FTBL/CODE/STR /STBL)
      -> CODE 内 VM 解码 -> 提取「显示调用」串 id: <id>; STR; PUSH a; PUSH b; PCALL|CALL
      -> STR 池 NUL 分割取串 -> 半角假名转平假名 -> 去 <w> 标签
用法: python scripts/orfleur_extract.py <dec_dir> <out_txt> [--chunks-dir DIR]
"""
import sys, os, zlib, struct, re

PAGE = 0x400

# opcode 长度表 (index = opcode byte), 来自 eboot.elf file 0x1cd4e0 的 80x12B 表
OPLEN = [1,1,2,2,1,1,9,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
         1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,5,3,2,3,2,1,5,1,1,1,1,1,1,1,1,5,
         1,1,1,1,1,5,1,1,1,1,5,5,5,1,1,1]
OP_SYSCALL, OP_CALL, OP_PCALL = 10, 11, 71
OP_PUSHIW, OP_PUSHIH, OP_PUSHIB = 48, 49, 50
OP_STR = 55
PUSHES = (OP_PUSHIW, OP_PUSHIH, OP_PUSHIB)

# ---- 半角假名(池内表示平假名) -> 平假名 映射 ----
_HW = {}
_kana = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
_hws  = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜｦﾝ"
for a,b in zip(_hws,_kana): _HW[ord(a)] = b
for a,b in zip("ｧｨｩｪｫｬｭｮｯ", "ぁぃぅぇぉゃゅょっ"): _HW[ord(a)] = b
for a,b in zip("｡｢｣､･ｰ", "。「」、・ー"): _HW[ord(a)] = b
# 浊点/半浊点 组合
_DAK = {ord('ﾞ'):1, ord('ﾟ'):2}
_dakuten = {("か","が"),("き","ぎ"),("く","ぐ"),("け","げ"),("こ","ご"),("さ","ざ"),("し","じ"),
            ("す","ず"),("せ","ぜ"),("そ","ぞ"),("た","だ"),("ち","ぢ"),
            ("つ","づ"),("て","で"),("と","ど"),("は","ば"),("ひ","び"),("ふ","ぶ"),("へ","べ"),("ほ","ぼ"),
            ("う","ゔ")}
_handaku = {("は","ぱ"),("ひ","ぴ"),("ふ","ぷ"),("へ","ぺ"),("ほ","ぽ")}
_DAKMAP = {a:b for a,b in _dakuten}
_HDKMAP = {a:b for a,b in _handaku}


def hankaku_to_hiragana(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        nxt = s[i+1] if i+1 < len(s) else ""
        base = _HW.get(ord(c))
        if base and nxt and ord(nxt) in _DAK:
            m = _DAKMAP if _DAK[ord(nxt)] == 1 else _HDKMAP
            if base in m:
                out.append(m[base]); i += 2; continue
        out.append(base if base else c)
        i += 1
    return "".join(out)


TAG_RE = re.compile(r"</?w>")
# <a>(X) ：X 是「要绘制的开括号」（截图实证：<a>(「)…」显示为「…」；<a>(（)…）显示为（…））
ABRACKET_RE = re.compile(r"<a>\((.)\)")
NAMEMACRO_RE = re.compile(r"<name>\(\d+\)")
HERO_NAME = "クレア"          # 主人公デフォルト名（VNDB/取名截图实证）


def strip_tags(t: str) -> str:
    t = TAG_RE.sub('', t)
    t = ABRACKET_RE.sub(lambda m: m.group(1), t)
    t = NAMEMACRO_RE.sub(HERO_NAME, t)
    return t


def secs(b):
    out = {}; i = 0x10
    while i < len(b) - 8:
        tag = b[i:i+4].decode('latin1'); sz = int.from_bytes(b[i+4:i+8], 'little')
        if sz < 8 or sz > len(b): break
        out[tag.strip()] = (i, sz); i += sz
    return out


def parse_rom(path):
    d = open(path, 'rb').read()
    N = len(d) // PAGE
    chunks = []
    pg = 1
    while pg < N:
        o = pg * PAGE
        tag = int.from_bytes(d[o:o+4], 'little')
        if (tag & 0xFFFF) == 0x19A6:
            typ = (tag >> 16) & 0xFFFF
            comp = int.from_bytes(d[o+4:o+8], 'little')
            raw = int.from_bytes(d[o+8:o+12], 'little')
            blob = d[o+12:o+12+comp]
            try:
                if typ == 1:
                    data = zlib.decompress(blob)
                else:
                    n = int.from_bytes(blob[4:8], 'little')
                    hs = int.from_bytes(blob[12:16], 'little')
                    offs = [int.from_bytes(blob[16+4*i:20+4*i], 'little') for i in range(n)]
                    data = b''.join(zlib.decompress(blob[x:y]) for x, y in zip([hs]+offs, offs))
            except Exception:
                data = None
            npages = (12 + comp + PAGE - 1) // PAGE
        else:
            size = int.from_bytes(d[o+4:o+8], 'little')
            if size < 12 or size > PAGE * 8000:
                pg += 1; continue
            data = d[o:o+size]
            npages = (size + PAGE - 1) // PAGE
        chunks.append(data)
        pg += npages
    return chunks


def vm_ops(code):
    """按 opcode 表线性解码，返回 [(off, op, arg)]"""
    ops = []; p = 20
    L = len(code)
    while p < L:
        op = code[p]
        if op >= 80: break
        n = OPLEN[op]
        if n == 2: a = code[p+1]
        elif n == 3: a = struct.unpack_from('<H', code, p+1)[0]
        elif n == 5: a = struct.unpack_from('<I', code, p+1)[0]
        else: a = None
        ops.append((p, op, a)); p += n
    return ops


def extract_chunk(data):
    """返回显示序文本行 list（原始，未转换）"""
    if not data or data[:4] != b'DCVM':
        return None, None
    S = secs(data)
    if 'CODE' not in S or 'STR' not in S:
        return None, None
    co, cs = S['CODE']; code = data[co+8:co+cs]
    so, ss = S['STR']; strd = data[so+8:so+ss]
    parts = strd.split(b'\0')
    ops = vm_ops(code)
    lines = []
    for i in range(1, len(ops)-3):
        q, op, a = ops[i]
        if op != OP_STR: continue
        prev = ops[i-1]
        if prev[1] not in PUSHES or prev[2] is None: continue
        n1, n2, n3 = ops[i+1], ops[i+2], ops[i+3]
        if n1[1] in PUSHES and n2[1] in PUSHES and n3[1] in (OP_CALL, OP_PCALL):
            k = prev[2]
            if 0 < k < len(parts):
                s = parts[k]
                if s:
                    lines.append(s)
    return lines, parts


def clean(s: bytes):
    try:
        t = s.decode('cp932')
    except Exception:
        return None
    t = TAG_RE.sub('', t)
    t = hankaku_to_hiragana(t)
    # 剔除舞台指令/资源名：仍含 < > 标记、或几乎全为 ASCII 的串
    if '<' in t or '>' in t:
        return None
    jp = sum(1 for c in t if '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff'
             or '\uff01' <= c <= '\uff60' or c in '。、・「」『』…ー')
    if jp * 2 < len(t.strip()):
        return None
    return t


def main():
    dec = sys.argv[1] if len(sys.argv) > 1 else "_work_orfleur/dec"
    out = sys.argv[2] if len(sys.argv) > 2 else "提取结果/[PSV-JP]オルフレール_全文本.txt"
    romdir = os.path.join(dec, "rom")
    chunks_dir = None
    if "--chunks-dir" in sys.argv:
        chunks_dir = sys.argv[sys.argv.index("--chunks-dir")+1]
        os.makedirs(chunks_dir, exist_ok=True)
    roms = sorted(os.listdir(romdir))
    allout = []
    for rn in roms:
        path = os.path.join(romdir, rn)
        chs = parse_rom(path)
        n_ok = 0
        for idx, data in enumerate(chs):
            lines, parts = extract_chunk(data)
            if not lines: continue
            n_ok += 1
            if chunks_dir:
                fn = os.path.join(chunks_dir, "%s_%04d.txt" % (rn[:-4], idx))
                with open(fn, 'w', encoding='utf-8') as fp:
                    for s in lines:
                        c = clean(s)
                        if c: fp.write(c + "\n")
            allout.append((rn, idx, lines))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    total = 0
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fp:
        for rn, idx, lines in allout:
            prev = None
            for s in lines:
                c = clean(s)
                if c and c.strip() and c != prev:
                    fp.write(c + "\n"); total += 1; prev = c
    print("chunks with text:", len(allout), "lines:", total, "->", out)


if __name__ == "__main__":
    main()
