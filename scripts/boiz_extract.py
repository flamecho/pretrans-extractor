#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]♂ボ～イズ！！～イケメン陵辱パラダイス～（体験版） 文本提取

链路:
  RAR5 SFX (本 .exe) -> cg/nss/sound/system.npa
  Nitroplus NPA (NPA\\x01)：
    · 索引名：raw[i] += (0xFC*i - Σ(arc_key>>sh) - Σ(curfile>>sh)) & 0xFF
    · arc_key = key1*key2（乘积分支；名字解出即证明走此分支）
    · 内容：b[i] = KEY[b[i]] - key - i（前 0x1000+len(name) 字节）
      key = ((0x20101118 - Σ(name)) * len(name) + arc_key) * unpackedSize & 0xFF
      KEY = osu_trial.exe @1320464 处 256B 置换表的逆（该作不在 GARbro 25 套预置 Order 内）
    · 压缩 = zlib，解压长度 == unpackedSize（17/17 条目闭合）
  Nitroplus NSS（NScripter 派生，cp932/CRLF）：
    · <PRE @boxNN> … </PRE> = 一个文本对象（一次 TypeBegin）
    · 块内空行 = 消息分隔（一次点击 = 一行）；块内连续行 = 同一框内的软换行，合并
    · [textNNNN] = 文本标签行，非正文；{…} = 行内演出指令；<voice …> = 语音挂点（非显示）
    · /* … */ 与 // 为注释（作者废弃稿），必须剔除

用法: python boiz_extract.py <nss.npa 目录> <输出 txt>
"""
import struct, sys, os, zlib, re

NAMEKEY = 0x20101118
KEYTAB_OFF = 1320464

STORY_ORDER = ['01_001.nss', '02_001.nss', '03_001.nss', '04_001.nss']

JP = re.compile(r'[\u3041-\u3096\u30a1-\u30fa\u4e00-\u9fff]')


def load_key_table(exe_path):
    d = open(exe_path, 'rb').read()
    t = d[KEYTAB_OFF:KEYTAB_OFF + 256]
    assert len(set(t)) == 256, 'key table not a permutation'
    inv = bytearray(256)
    for i, v in enumerate(t):
        inv[v] = i
    return bytes(inv)


def decrypt_name(pos, curfile, arc_key):
    key = 0xFC * pos
    for sh in (0x18, 0x10, 0x08, 0):
        key -= arc_key >> sh
    for sh in (0x18, 0x10, 0x08, 0):
        key -= curfile >> sh
    return key & 0xFF


def open_npa(path, keytab):
    d = open(path, 'rb').read()
    assert d[:4] == b'NPA\x01', 'not NPA'
    key1 = struct.unpack_from('<i', d, 7)[0]
    key2 = struct.unpack_from('<i', d, 11)[0]
    compressed = d[15]
    encrypted = d[16]
    total = struct.unpack_from('<i', d, 17)[0]
    dirsize = struct.unpack_from('<I', d, 37)[0]
    arc = (key1 * key2) & 0xFFFFFFFF
    cur = 41
    out = {}
    for i in range(total):
        ns = struct.unpack_from('<i', d, cur)[0]
        raw = bytearray(d[cur + 4:cur + 4 + ns])
        for x in range(ns):
            raw[x] = (raw[x] + decrypt_name(x, i, arc)) & 0xFF
        typ = d[cur + 4 + ns]
        fid, off, size, unp = struct.unpack_from('<IIII', d, cur + 5 + ns)
        cur += 4 + ns + 17
        if typ == 1:
            continue
        name = bytes(raw).decode('cp932')
        base = dirsize + off + 41
        buf = bytearray(d[base:base + size])
        if encrypted:
            key = NAMEKEY
            for b in raw:
                key -= b
            key = (key * len(raw)) & 0xFFFFFFFF
            key = ((key + arc) * unp) & 0xFFFFFFFF
            key &= 0xFF
            n = min(0x1000 + len(raw), size)
            for k in range(n):
                buf[k] = (keytab[buf[k]] - key - k) & 0xFF
        data = bytes(buf)
        if compressed:
            data = zlib.decompress(data)
            assert len(data) == unp
        out[name] = data
    return out


LABEL = re.compile(r'^\s*\[[^\]]*\]?\s*$', re.M)
TAG = re.compile(r'<[^>]*>')
BRACE = re.compile(r'\{[^{}]*\}', re.S)
RUBY = re.compile(r'<RUBY\s+text="[^"]*">(.*?)</RUBY>', re.S)


def strip_source(s):
    """去注释：// 行注释（保留 // 出现在字符串内的情况按行首/前置空白处理已够用）与 /* */ 块注释"""
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'(?m)^\s*//.*$', '', s)
    return s


def clean(chunk):
    t = RUBY.sub(r'\1', chunk)
    t = BRACE.sub('', t)
    t = TAG.sub('', t)
    t = t.replace('\u3000', '\u3000')
    parts = [p.strip(' \t\u3000') for p in t.split('\n')]
    return ''.join(p for p in parts if p)


def parse_nss(src):
    s = src.replace('\r\n', '\n').replace('\r', '\n')
    s = strip_source(s)
    out = []
    for m in re.finditer(r'<PRE[^>]*>(.*?)</PRE>', s, re.S):
        body = m.group(1)
        body = LABEL.sub('', body)
        for chunk in re.split(r'\n[ \u3000]*\n', body):
            t = clean(chunk)
            if t and (JP.search(t) or '「' in t):
                out.append(t)
    return out


def main():
    src = sys.argv[1]
    outpath = sys.argv[2]
    keytab = load_key_table(os.path.join(src, 'osu_trial.exe'))
    files = open_npa(os.path.join(src, 'nss.npa'), keytab)
    result = []
    stats = {}
    for name in STORY_ORDER:
        text = files[name].decode('cp932')
        ls = parse_nss(text)
        stats[name] = len(ls)
        result.extend(ls)
    d = os.path.dirname(os.path.abspath(outpath))
    os.makedirs(d, exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(result) + '\n')
    print('files=%d lines=%d' % (len(stats), len(result)))
    for k in STORY_ORDER:
        print('  %5d  %s' % (stats[k], k))


if __name__ == '__main__':
    main()
