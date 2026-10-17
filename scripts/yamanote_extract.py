#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TOKYOヤマノテBOYS for V MAIN DISC（PSV / PCSG01048）全文本提取。

引擎：Unity 5.4.4p2 + 自研「LTE」脚本引擎（纯文本标签脚本，UTF-16LE）
链路：
  1) pkg2zip -x <pkg> <zRIF>            → app/PCSG01048/（PFS 加密）
  2) psvpfsparser -i PCSG01048 -o dec -z <zRIF> -f cma.henkaku.xyz   （前台/联网）
  3) 本脚本：
     a. 解 dec/archive.psarc（PSARC/zlib）→ Media/resources.assets
     b. 提取其中的 TextAsset（UTF-16LE 剧本）→ <work>/ta_txt/*.txt
     c. 解析 dec/Media/Managed/Assembly-CSharp.dll 的 .NET #US 字符串堆
        → 用語辞典（HM/SM/DC辞書：脚本 <tips> 锚定；Z辞書：三元组）
     d. LTE 脚本 → 「一次点击=一行」正文 + 选项 + 場所テロップ，末尾并入用語辞典

用法:
  python yamanote_extract.py --dec <解密后的 PCSG01048 目录> --out <成品.txt> [--work <缓冲目录>]
"""
import argparse, glob, json, os, re, sys

HEROINE = 'チヒロ'          # 主角默认名（外部核对：TYB 系列通称「チヒロ」；脚本内恒为 %name%）
INCLUDE_PREFIX = ('TYB_', 'TYBV_', 'TYBPSP_', 'book_', 'ifdata_')
EXCLUDE_EXACT = {'day', 'ScriptTop', 'ScriptBottom', 'LTStart', 'BTStart',
                 'BTStart2', 'ED_flag', 'test_Title'}

# 原作脚本笔误（半角/全角括号混用、『』↔「」混用）——整行定值表修正
LINE_FIX = {
    '『それはなによりです。　今回の件での、唯一の光ですね」':
        '『それはなによりです。　今回の件での、唯一の光ですね』',
    '（殺人鬼がつかまってないって、　ニュースで言ってたの、本当だったんだ)':
        '（殺人鬼がつかまってないって、　ニュースで言ってたの、本当だったんだ）',
    '（今日までは一生けんめい　がんばってはきたけど)':
        '（今日までは一生けんめい　がんばってはきたけど）',
    '(イエスくんって歩くの早いよね……。　やっぱり足が長いからかな）':
        '（イエスくんって歩くの早いよね……。　やっぱり足が長いからかな）',
}

# ---------- PSARC (Sony, big-endian) ----------
import struct, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import psarc_extract as _psarc
except Exception:
    _psarc = None


def psarc_extract(path, outdir):
    """复用同目录 psarc_extract.py（PSARC/zlib，条目 0 = 名字表）。"""
    if _psarc is None:
        raise RuntimeError('psarc_extract.py not found next to this script')
    _psarc.main(path, outdir)
    return [(os.path.relpath(p, outdir), os.path.getsize(p))
            for p in glob.glob(os.path.join(outdir, '**', '*'), recursive=True) if os.path.isfile(p)]


# ---------- Unity TextAsset 抽取 ----------
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


# ---------- .NET #US 字符串堆 ----------
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
    items = us_heap(dll)
    strs = [t for _, t in items]
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
        for m in re.finditer(r'<tips name="([^"]+)">(.*?)</tips>', txt, re.S):
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
        return ({'HM': 0, 'SM': 1, 'DC': 2, 'Z': 3}.get(p, 9), int(n))

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
    # Z 辞書（脚本未引用）: 堆窗口内三元组
    zi = [i for i, s in enumerate(strs) if s.startswith('Z辞書')]
    if zi:
        for i, rd, t, e in triples:
            if min(zi) - 8 <= i <= max(zi) + 8:
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
    g = 0 if b.startswith('TYB_Z') else 1 if b.startswith('TYB_') else \
        2 if b.startswith('TYBV_') else 3 if b.startswith('TYBPSP_') else \
        4 if b.startswith('book_') else 5
    return (g, b)


def list_scripts(txtdir):
    out = []
    for p in glob.glob(os.path.join(txtdir, '*.txt')):
        b = os.path.basename(p)[:-4]
        if b in EXCLUDE_EXACT or b.startswith('JumpSkip') or b.startswith('cero_'):
            continue
        if b.startswith(INCLUDE_PREFIX):
            out.append(p)
    return sorted(out, key=order_key)


def parse_scripts(files):
    lines, st = [], {'boxes': 0, 'options': 0, 'places': 0}
    for path in files:
        raw = open(path, encoding='utf-8').read().replace('\r\n', '\n').replace('\r', '\n')
        buf = []

        def flush():
            t = ''.join(buf).replace('%name%', HEROINE).rstrip(' 　\t')
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
                    t = seg.replace('%name%', HEROINE)
                    if t.strip(' 　\t'):
                        buf.append(t)
                nm = _TAGNAME.match(m.group(0)).group(1)
                at = dict(ATTR_RE.findall(m.group(0)))
                closing = m.group(0).startswith('</')
                pos = m.end()
                if nm in FLUSH_TAGS or (nm == 'wait' and 'key' in at) or nm == 'moshititle':
                    flush()
                elif nm == 'select' and not closing:
                    flush()
                elif nm == 'case':
                    v = at.get('value', '').replace('%name%', HEROINE)
                    if v.strip():
                        lines.append(v); st['options'] += 1
                elif nm == 'place':
                    v = at.get('name', '').replace('%name%', HEROINE)
                    if v.strip():
                        flush(); lines.append(v); st['places'] += 1
            seg = line[pos:]
            if seg and not is_remnant(seg):
                t = seg.replace('%name%', HEROINE)
                if t.strip(' 　\t'):
                    buf.append(t)
        flush()
    return lines, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dec', required=True, help='解密后的 PCSG01048 目录（含 eboot.bin/archive.psarc）')
    ap.add_argument('--out', required=True)
    ap.add_argument('--work', default=None)
    a = ap.parse_args()
    dec = a.dec
    work = a.work or os.path.join(os.path.dirname(os.path.abspath(a.out)), '_yamanote_work')
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
    print('[3] scripts: files=%d boxes=%d options=%d places=%d' % (len(files), st['boxes'], st['options'], st['places']))
    print('[4] dictionary ...')
    dic = build_dictionary(os.path.join(dec, 'Media', 'Managed', 'Assembly-CSharp.dll'), txtdir)
    print('    dict entries =', len(dic))
    lines = [LINE_FIX.get(l, l) for l in lines] + dic
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('->', a.out, 'lines =', len(lines))


if __name__ == '__main__':
    main()
