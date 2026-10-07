#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lamento -BEYOND THE VOID- (Windows 10 Support Edition)  —  Nitroplus NPA / NSS
全テキスト抽出ツール

チェーン:
  nss.npa / system.npa  (RAR5 ヘッダ暗号, パスワード)
    -> Nitroplus "NPA\\x01" アーカイブ (index 名は key1*key2 で復号 / 中身は DJANGO スキームで復号)
    -> 内部 .nss  (Nitroplus 独自スクリプト = NScripter 派生)
    -> <PRE boxNN> [textNNN] ... </PRE> ブロック = 1 テキストオブジェクト
       ブロック内 <K>/<k>/<Ｋ>/<?> = クリック待ち -> 1 クリック = 1 行
       (ブロック内の改行は同一メッセージ内のソフト改行として結合)

使い方:
  python lamento_extract.py <nss.npa のあるディレクトリ> <出力txt>
"""
import struct, sys, os, zlib, re, glob, json

# ---------------------------------------------------------------- NPA
NPA_SCHEMES = None  # (titleid -> (NameKey, Order)) は呼び出し側で設定 or 内蔵

BASE_TABLE = bytes([
0x6F,0x05,0x6A,0xBF,0xA1,0xC7,0x8E,0xFB,0xD4,0x2F,0x80,0x58,0x4A,0x17,0x3B,0xB1,0x89,0xEC,0xA0,0x9F,0xD3,0xFC,0xC2,0x04,0x68,0x03,0xF3,0x25,0xBE,0x24,0xF1,0xBD,
0xB8,0x41,0xC9,0x27,0x0E,0xA3,0xD8,0x7F,0x5B,0x8F,0x16,0x49,0xAA,0xB2,0x18,0xA7,0x33,0xE4,0xDB,0x48,0xCA,0xDE,0xAE,0xCD,0x13,0x1F,0x15,0x2E,0x39,0xF5,0x1E,0xDD,
0x0F,0x88,0x4C,0x98,0x36,0xB4,0x3F,0x09,0x83,0xFD,0x32,0xBA,0x14,0x30,0x7A,0x63,0xB9,0x56,0x95,0x61,0xCC,0x8B,0xEF,0xDA,0xE5,0x2C,0xDC,0x12,0x1A,0x67,0x23,0x50,
0xD1,0xC3,0x7E,0x6D,0xB6,0x90,0x3C,0xB3,0x0B,0xE2,0x91,0x70,0xA8,0xDF,0x44,0xC4,0xF4,0x01,0x5C,0x10,0x06,0xE7,0x54,0x40,0x43,0x72,0x38,0xBC,0xE3,0x07,0xFA,0x34,
0x02,0xA4,0xF7,0x74,0xA9,0x4D,0x42,0xA5,0x85,0x35,0x79,0xD2,0x76,0x97,0x45,0x4F,0x08,0x5A,0xB0,0xEE,0x51,0x73,0x69,0x9E,0x94,0x47,0x77,0x29,0xD9,0x64,0x11,0xEB,
0x37,0xAC,0x20,0x62,0x9A,0x6B,0x9C,0x75,0x22,0x87,0xAB,0x78,0x53,0xC8,0x5D,0xAD,0x2A,0xF2,0xCB,0xB7,0x0D,0xED,0x86,0x55,0xFF,0x19,0x57,0xD7,0xD5,0x60,0xC6,0x3D,
0xEA,0xC1,0x6C,0xE1,0xC0,0x65,0x84,0xC5,0xE0,0x3E,0x7D,0x28,0x66,0xAF,0x1C,0x9B,0xCF,0x81,0x4E,0x26,0x59,0x2B,0x5F,0x7B,0xE8,0x8D,0x52,0x7C,0xF8,0x82,0x0C,0xF9,
0x8C,0xE9,0xB5,0xE6,0x31,0x93,0x46,0x5E,0x1D,0x1B,0x4B,0x71,0xD6,0x92,0x3A,0xA6,0x2D,0x00,0x9D,0xBB,0x6E,0xF0,0x99,0xCE,0x21,0x0A,0xD0,0xF6,0xFE,0xA2,0x8A,0x96,
])

# Lamento W10 版 nss.npa が実際に使うスキーム = DJANGO (titleid 7)
DJANGO = (7, 0x87654321, bytes.fromhex('eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee1e4e66b6'))

def gen_table(order, titleid):
    table = bytearray(256)
    for i in range(256):
        edx = i << 4
        dl = (edx + order[i & 0x0F]) & 0xFF
        dh = (edx + (order[i >> 4] << 8)) & 0xFF00
        table[BASE_TABLE[i]] = ((dh | dl) >> 4) & 0xFF
    for i in range(17, len(order), 2):
        a, b = order[i-1], order[i]
        table[a], table[b] = table[b], table[a]
    if titleid == 22:  # TOTONO
        tt = bytearray(256)
        for i in range(256):
            r = table[i]; r = table[r]; r = table[r]; tt[i] = (~r) & 0xFF
        table = tt
    return bytes(table)

def npa_decrypt_name(index, curfile, ak):
    key = (0xFC * index) & 0xFFFFFFFF
    for sh in (0x18, 0x10, 0x08, 0):
        key = (key - (ak >> sh)) & 0xFFFFFFFF
    for sh in (0x18, 0x10, 0x08, 0):
        key = (key - (curfile >> sh)) & 0xFFFFFFFF
    return key & 0xFF

def npa_extract(npa_path, scheme):
    """NPA -> {name: decompressed_bytes}"""
    d = open(npa_path, 'rb').read()
    assert d[:4] == b'NPA\x01', 'not NPA'
    key1 = struct.unpack_from('<i', d, 7)[0]
    key2 = struct.unpack_from('<i', d, 11)[0]
    compressed = d[15]
    total = struct.unpack_from('<i', d, 17)[0]
    dirsize = struct.unpack_from('<I', d, 37)[0]
    arc_key = (key1 * key2) & 0xFFFFFFFF          # Lamento W10 は非 LAMENTO 扱い(=積)
    titleid, namekey, order = scheme
    tab = gen_table(order, titleid)

    cur = 41
    ents = []
    for i in range(total):
        ns = struct.unpack_from('<i', d, cur)[0]
        raw = bytearray(d[cur+4:cur+4+ns])
        for x in range(ns):
            raw[x] = (raw[x] + npa_decrypt_name(x, i, arc_key)) & 0xFF
        info = cur + 5 + ns
        fid, off, size, unp = struct.unpack_from('<IIII', d, info)
        ents.append((bytes(raw), dirsize + off + 41, size, unp))
        cur += 4 + ns + 17

    out = {}
    for name, base, size, unp in ents:
        enc_len = 0x1000 + (0 if titleid == 9 else len(name))
        key = namekey
        for b in name:
            key -= b
        key *= len(name)
        if titleid != 9:
            key = (key + arc_key) & 0xFFFFFFFF
            key = (key * unp) & 0xFFFFFFFF
        key &= 0xFF
        n = min(enc_len, size)
        buf = bytearray(d[base:base+n])
        if titleid == 9:
            for i in range(n):
                buf[i] = (tab[buf[i]] - key) & 0xFF
        else:
            for i in range(n):
                buf[i] = (tab[buf[i]] - key - i) & 0xFF
        data = bytes(buf) + d[base+n:base+size]
        try:
            data = zlib.decompress(data)
        except Exception:
            pass
        out[name.decode('cp932')] = data
    return out

# ---------------------------------------------------------------- NSS parse
JP = re.compile(r'[ぁ-ゖァ-ヺ一-龥぀-ゟ]')
CLICK = re.compile(r'<[KkＫ]>|<\?>')
RUBY = re.compile(r'<RUBY\s+text="[^"]*">(.*?)</RUBY>', re.S)
TAG = re.compile(r'<[^>]*>')
WS = re.compile(r'^[\s\u3000]+|[\s\u3000]+$')

def clean_text(s):
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    s = RUBY.sub(r'\1', s)
    s = TAG.sub('', s)
    parts = [WS.sub('', p) for p in s.split('\n')]
    return ''.join(p for p in parts if p)

def split_args(argstr):
    args, buf, q, esc = [], '', False, False
    for ch in argstr:
        if esc:
            buf += ch; esc = False; continue
        if ch == '\\' and q:
            esc = True; continue
        if ch == '"':
            q = not q; buf += ch; continue
        if ch == ',' and not q:
            args.append(buf); buf = ''; continue
        buf += ch
    if buf.strip() != '' or args:
        args.append(buf)
    return [a.strip() for a in args]

def str_args(argstr):
    return re.findall(r'"((?:[^"\\]|\\.)*)"', argstr)

def find_call(line, name):
    m = re.search(re.escape(name) + r'\s*\(', line)
    if not m:
        return None
    i = m.end(); depth = 1; q = False
    while i < len(line):
        c = line[i]
        if c == '"':
            q = not q
        elif not q:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return line[m.end():i]
        i += 1
    return None

def parse_nss(text):
    """NSS ソース -> テキスト行リスト（表示順）"""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        st = line.strip()
        if '<PRE' in line:
            body = []
            after = line.split('>', 1)[1] if '>' in line else ''
            body.append(after)
            i += 1
            while i < n and '</PRE>' not in lines[i]:
                body.append(lines[i]); i += 1
            if i < n:
                body.append(lines[i].split('</PRE>')[0])
            b = '\n'.join(body)
            b = re.sub(r'//[^\n]*', '', b)            # // コメント（無効化された差分テキスト）を除去
            b = re.sub(r'^\s*\[[A-Za-z0-9_]*\]?\s*$', '', b, flags=re.M)   # ラベル（閉じ括弧欠けも許容）
            b = re.sub(r'\{[^{}]*\}', '', b)
            b = CLICK.sub('\n\n', b)                  # クリック待ちもメッセージ境界
            # 空行（メッセージ区切り）で分割、連続行は 1 メッセージとして結合
            for chunk in re.split(r'\n[ \u3000]*\n', b):
                if JP.search(chunk) or '「' in chunk or '」' in chunk:
                    t = clean_text(chunk)
                    if t:
                        out.append(t)
            i += 1
            continue
        # command lines
        if not (st.startswith('//') or st.startswith('...') or st.startswith('#')):
            for fn in ('CreateTextEX', 'CreateText'):
                a = find_call(line, fn)
                if a:
                    ss = str_args(a)
                    if ss and JP.search(ss[-1]):
                        t = clean_text(ss[-1])
                        if t:
                            out.append(t)
            for fn in ('SetChoice02', 'SetChoice03'):
                a = find_call(line, fn)
                if a:
                    for s in str_args(a):
                        t = clean_text(s)
                        if t and JP.search(t):
                            out.append(t)
            a = find_call(line, 'CreateChoice')
            if a:
                for s in str_args(a):
                    t = clean_text(s)
                    if t and JP.search(t):
                        out.append(t)
            for fn in ('TextMirror01', 'TextMirror02'):
                a = find_call(line, fn)
                if a:
                    ss = str_args(a)
                    if ss:
                        t = clean_text(ss[0])
                        if t and JP.search(t):
                            out.append(t)
            # ★ 规范：只取「显示用」文本。SetBacklog 是「日志专用」载体（其文本经 CreateText/extext 另行显示），
            #    且常与显示稿改稿不同步 → 按规范【不取】。（TextMirror 是显示特效，仍取。）
            a = None
        i += 1
    return out

def numkey(fn):
    m = re.match(r'([a-z]+)(\d+)', fn)
    return (m.group(1), int(m.group(2)), fn) if m else ('zzz', 10**9, fn)

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else '.'
    outpath = sys.argv[2] if len(sys.argv) > 2 else 'out.txt'
    files = npa_extract(os.path.join(src, 'nss.npa'), DJANGO)
    scripts = {k: v.decode('cp932', 'replace') for k, v in files.items()}

    main_order = sorted([f for f in scripts if re.match(r'l[abc]\d+', f)], key=numkey)
    main_order = [f for f in main_order if not f.startswith('la0000')]
    extra_order = sorted([f for f in scripts if f.startswith('extra') and f != 'extra_function.nss'],
                         key=numkey)
    sys_order = ['boot.nss'] + sorted([f for f in scripts if f.startswith('sys_')])

    result = []
    stats = {}
    for f in main_order + extra_order + sys_order:
        if f not in scripts:
            continue
        ls = parse_nss(scripts[f])
        stats[f] = len(ls)
        result.extend(ls)

    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(result) + '\n')
    print('files=%d lines=%d' % (len(stats), len(result)))
    for f in main_order + extra_order + sys_order:
        if f in stats:
            print('  %6d  %s' % (stats[f], f))

if __name__ == '__main__':
    main()
