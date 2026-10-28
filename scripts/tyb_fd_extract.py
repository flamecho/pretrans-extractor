#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOKYOヤマノテBOYS for V FAN DISC（PSV / PCSG01049）全文本提取。

引擎：Unity 5.4.4p2（Mono）＋ 自研「LTE」脚本引擎（TextAsset，UTF-16LE ＋ BOM）。
与 MAIN DISC（PCSG01048）同链，差异：脚本前缀为 TYBALL_ / TYBFD1..3_ / TYBV_ / book_ / chara*。

断行（本作实测）：
  <pb>                     = 页面分隔（清框）＝ 一次点击          97,773 处
  <wait key="true">        = 等待点击（不清框的推进指令）          1,761 处
  <select>/<case value=""> = 选项（一行一条）
  <place name="">          = 場所テロップ（直接上屏）
  ＠名前                    = 独立名字窗（名札行，整行丢弃；不入正文、不加前缀）
  %name%                   = 主角名宏 ⇒ チヒロ

用法: python tyb_fd_extract.py --dec <解密后 PCSG01049 目录> --out <成品.txt> [--work <缓冲>]
"""
import argparse
import glob
import os
import re
import struct
import sys

HEROINE = 'チヒロ'

# 主角名宏：%name% = 名（默认「チヒロ」）；%family% = 姓（本作默认未设姓，vndb 主角仅列「チヒロ」）
# ⇒ 组合式 `%family%%name%` 折叠为一次「チヒロ」，孤立 `%family%`（称呼语）亦取「チヒロ」。
MACRO_SEQ = (('%family%%name%', HEROINE), ('%name%', HEROINE), ('%family%', HEROINE))

# 半角片假名 → 全角（字幅归一；原文的颜文字／ギャル文字用半角片假名做视觉替换，字符不变）
_HW = 'ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝﾞﾟ'
_FW = 'ヲァィゥェォャュョッーアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン゛゜'
HW_MAP = str.maketrans(_HW, _FW)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import psarc_extract as _psarc
except Exception:
    _psarc = None


# ---------- PSARC ----------
def psarc_extract(path, outdir):
    _psarc.main(path, outdir)
    return [(os.path.relpath(p, outdir), os.path.getsize(p))
            for p in glob.glob(os.path.join(outdir, '**', '*'), recursive=True) if os.path.isfile(p)]


# ---------- Unity TextAsset ----------
def dump_textassets(assets, outdir):
    import UnityPy
    env = UnityPy.load(assets)
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        s = d.m_Script
        b = s if isinstance(s, bytes) else s.encode('utf-8', 'surrogateescape')
        if b[:2] == b'\xff\xfe':
            try:
                t = b[2:].decode('utf-16-le')
            except Exception:
                continue
            open(os.path.join(outdir, d.m_Name + '.txt'), 'w', encoding='utf-8', newline='\n').write(t)
            n += 1
    return n


# ---------- .NET #US 堆 ----------
def _us_walk(data, off, size):
    p, end, out = off + 1, off + size, []
    while p < end:
        b0 = data[p]
        if b0 == 0:
            p += 1
            continue
        if (b0 & 0x80) == 0:
            ln = b0; p += 1
        elif (b0 & 0xC0) == 0x80:
            ln = ((b0 & 0x3F) << 8) | data[p + 1]; p += 2
        elif (b0 & 0xE0) == 0xC0:
            ln = ((b0 & 0x1F) << 24) | (data[p + 1] << 16) | (data[p + 2] << 8) | data[p + 3]; p += 4
        else:
            p += 1; continue
        if ln == 0 or p + ln > end:
            p += 1; continue
        raw = data[p:p + ln - 1]
        p += ln
        out.append((p - ln - 1, raw.decode('utf-16-le', 'replace')))
    return out


def us_heap(dll):
    data = open(dll, 'rb').read()
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    coff = pe + 4
    nsec = struct.unpack_from('<H', data, coff + 2)[0]
    optsz = struct.unpack_from('<H', data, coff + 16)[0]
    opt = coff + 20
    magic = struct.unpack_from('<H', data, opt)[0]
    dd = opt + (0x60 if magic == 0x10B else 0x70)
    cli_rva = struct.unpack_from('<I', data, dd + 14 * 8)[0]
    secs = []
    so = opt + optsz
    for i in range(nsec):
        e = so + i * 40
        vsz, va, rsz, raw = struct.unpack_from('<IIII', data, e + 8)
        secs.append((va, vsz, raw, rsz))

    def r2o(rva):
        for va, vsz, raw, rsz in secs:
            if va <= rva < va + max(vsz, rsz):
                return raw + (rva - va)
        return None

    cli = r2o(cli_rva)
    md_rva = struct.unpack_from('<I', data, cli + 8)[0]
    md = r2o(md_rva)
    verlen = struct.unpack_from('<I', data, md + 12)[0]
    p = md + 16 + verlen
    nstreams = struct.unpack_from('<H', data, p + 2)[0]
    p += 4
    streams = {}
    for _ in range(nstreams):
        o, sz = struct.unpack_from('<II', data, p); p += 8
        nm = b''
        while data[p] != 0:
            nm += data[p:p + 1]; p += 1
        p += 1
        while (p - md) % 4:
            p += 1
        streams[nm.decode()] = (md + o, sz)
    return _us_walk(data, *streams['#US'])


# ---------- 用語辞典 ----------
def build_dictionary(dll, txtdir):
    strs = [t for _, t in us_heap(dll)]
    HIRA = re.compile(r'^[ぁ-ん゛゜ー・]+$')
    ID = re.compile(r'^([A-Z]{1,3})辞書(\d{1,4})$')

    def expl_like(s):
        return '<br>' in s or len(s) >= 18

    triples = []
    for i in range(2, len(strs)):
        e = strs[i]
        if not expl_like(e) or ID.match(e):
            continue
        t = strs[i - 1]
        if ID.match(t) or expl_like(t) or not t.strip() or len(t) > 26:
            continue
        triples.append((i, strs[i - 2] if HIRA.match(strs[i - 2]) else '', t, e))
    term2tri = {}
    for tr in triples:
        term2tri.setdefault(tr[2], tr)

    script_terms = {}
    for f in glob.glob(os.path.join(txtdir, '*.txt')):
        txt = open(f, encoding='utf-8').read()
        for m in re.finditer(r'<tips\s+name\s*=\s*"([^"]+)"\s*>(.*?)</tips>', txt, re.S):
            tid = m.group(1)
            term = re.sub(r'<[^>]+>', '', m.group(2))
            script_terms.setdefault(tid, {})
            script_terms[tid][term] = script_terms[tid].get(term, 0) + 1

    idpos = {}
    for i, s in enumerate(strs):
        m = ID.match(s)
        if m and m.group(1):
            idpos.setdefault(s, i)

    def keyf(k):
        p, n = k.split('辞書')
        return ({'ALL': 0, 'HM': 1, 'SM': 2, 'DC': 3, 'FG': 4, 'PR': 5, 'Z': 6}.get(p, 9), int(n))

    entries, seen = [], set()
    for rid in sorted(script_terms, key=keyf):
        term = max(script_terms[rid], key=lambda k: script_terms[rid][k])
        plain = re.sub(r'<[^>]+>', '', term)
        rec = None
        for k in (term, plain, plain.rstrip('。！？')):
            if k in term2tri:
                rec = term2tri[k]
                break
        if rec is None:
            j = idpos.get(rid)
            if j is not None and expl_like(strs[j - 1]) and not ID.match(strs[j - 2]):
                rec = (j, strs[j - 3] if HIRA.match(strs[j - 3]) else '', strs[j - 2], strs[j - 1])
        if rec:
            _, rd, t, e = rec
            e = e.replace('<br>', '').replace('｢', '「').replace('｣', '」')
            if (t, e) not in seen:
                seen.add((t, e)); entries.append('【%s】%s' % (t, e))
    return entries


# ---------- LTE 脚本 → 文本 ----------
FLUSH_TAGS = {'pb'}
TAG_RE = re.compile(r'</?[A-Za-z_][A-Za-z0-9_]*(?:"[^"]*"|[^>"]|\s)*?/?>')
ATTR_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"([^"]*)"')
_TAGNAME = re.compile(r'</?([A-Za-z_][A-Za-z0-9_]*)')
REMNANT = re.compile(r'^[\s"]*(?:[A-Za-z_][A-Za-z0-9_]*\s*=\s*"[^"]*"\s*)*>*[\s"]*$')

INCLUDE_PREFIX = ('TYBALL_', 'TYBFD', 'TYBV_', 'book_', 'chara', 'open')
EXCLUDE_EXACT = {'day', 'SCRIPT', 'test_Title', 'LTStart', 'BTStart'}


def strip_comment(line):
    out, depth, i = [], 0, 0
    while i < len(line):
        c = line[i]
        if c == '<':
            depth += 1; out.append(c)
        elif c == '>':
            depth = max(0, depth - 1); out.append(c)
        elif c == '/' and depth == 0 and i + 1 < len(line) and line[i + 1] == '/':
            break
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def is_remnant(seg):
    s = seg.strip()
    if not s or len(s) > 64 or not any(c in s for c in '">=<'):
        return False
    return bool(REMNANT.match(s))


def order_key(p):
    b = os.path.basename(p)[:-4]
    if b.startswith('TYBALL_'): g = 0
    elif b.startswith('TYBFD1'): g = 1
    elif b.startswith('TYBFD2'): g = 2
    elif b.startswith('TYBFD3'): g = 3
    elif b.startswith('TYBV_'): g = 4
    elif b.startswith('book_'): g = 5
    else: g = 6
    return (g, b)


def list_scripts(txtdir):
    out = []
    for p in glob.glob(os.path.join(txtdir, '*.txt')):
        b = os.path.basename(p)[:-4]
        if b in EXCLUDE_EXACT or b.startswith(('JumpSkip', 'cero_')):
            continue
        if not b.startswith(INCLUDE_PREFIX):
            continue
        out.append(p)
    return sorted(out, key=order_key)


def subst(t):
    for a, b in MACRO_SEQ:
        t = t.replace(a, b)
    return t.translate(HW_MAP).rstrip(' 　\t')


def parse_scripts(files):
    lines, st = [], {'boxes': 0, 'options': 0, 'places': 0, 'waits': 0}
    for path in files:
        raw = open(path, encoding='utf-8').read().replace('\r\n', '\n').replace('\r', '\n')
        buf = []

        def flush():
            t = subst(''.join(buf))
            if t.strip(' 　\t'):
                lines.append(t); st['boxes'] += 1
            buf.clear()

        for raw_line in raw.split('\n'):
            line = strip_comment(raw_line)
            if not line.strip() or line.lstrip().startswith(('＠', '@')):
                continue
            pos = 0
            for m in TAG_RE.finditer(line):
                seg = line[pos:m.start()]
                if seg and not is_remnant(seg):
                    t = seg
                    if t.strip(' 　\t'):
                        buf.append(t)
                nm = _TAGNAME.match(m.group(0)).group(1)
                at = dict(ATTR_RE.findall(m.group(0)))
                closing = m.group(0).startswith('</')
                pos = m.end()
                if nm in FLUSH_TAGS or (nm == 'wait' and 'key' in at):
                    if nm == 'wait':
                        st['waits'] += 1
                    flush()
                elif nm == 'select' and not closing:
                    flush()
                elif nm == 'case':
                    v = subst(at.get('value', ''))
                    if v.strip():
                        lines.append(v); st['options'] += 1
                elif nm == 'place':
                    v = subst(at.get('name', ''))
                    if v.strip():
                        flush(); lines.append(v); st['places'] += 1
            seg = line[pos:]
            if seg and not is_remnant(seg):
                t = seg
                if t.strip(' 　\t'):
                    buf.append(t)
        flush()
    return lines, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dec', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--work', default=None)
    a = ap.parse_args()
    dec = a.dec
    work = a.work or os.path.join(os.path.dirname(os.path.abspath(a.out)), '_tyb_work')
    os.makedirs(work, exist_ok=True)

    psarc = os.path.join(dec, 'archive.psarc')
    psarcout = os.path.join(work, 'psarc')
    if not os.path.exists(os.path.join(psarcout, 'Media', 'resources.assets')):
        print('[1] extract archive.psarc ...')
        print('   ', psarc_extract(psarc, psarcout))
    txtdir = os.path.join(work, 'ta_txt')
    if not os.path.isdir(txtdir) or not os.listdir(txtdir):
        print('[2] dump TextAssets ...')
        print('    n =', dump_textassets(os.path.join(psarcout, 'Media', 'resources.assets'), txtdir))
    files = list_scripts(txtdir)
    lines, st = parse_scripts(files)
    print('[3] scripts: files=%d boxes=%d options=%d places=%d waits=%d'
          % (len(files), st['boxes'], st['options'], st['places'], st['waits']))
    print('[4] dictionary ...')
    dic = build_dictionary(os.path.join(dec, 'Media', 'Managed', 'Assembly-CSharp.dll'), txtdir)
    print('    dict entries =', len(dic))
    # 品检硬性：括号必须配对。少数解说为问答体（`例）` `×）` `◎）` 标签），括号天然不闭合
    # ⇒ 不并入末尾，原文逐字登记到报告
    bad = [d for d in dic if d.count('（') != d.count('）')]
    for b in bad:
        print('    [skip-dict] ' + b)
    dic = [d for d in dic if d.count('（') == d.count('）')]
    print('    dict kept =', len(dic), 'skipped =', len(bad))
    lines = lines + dic
    txt = '\n'.join(lines) + '\n'
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    open(a.out, 'w', encoding='utf-8-sig', newline='\n').write(txt)
    print('-> %s lines = %d chars = %d' % (a.out, len(lines), len(txt)))


if __name__ == '__main__':
    main()
