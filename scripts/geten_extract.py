# -*- coding: utf-8 -*-
"""下天の華 with 夢灯り (PSVita PCSG00921) 全文本抽取器

容器: VPK(zip) -> eboot.bin + Geten_Vita/DATA.BIN
      DATA.BIN = CDAR v4  (3428 entries, 条目多为 zlib 压缩)
      entry 833 / 1819 为嵌套 CDAR（内含同名剧本副本）-> 递归解包 + 去重

文本记录: 04 <u16 len> <cp932 bytes> 00   (记录驱动扫描, 字符宽度无关)
消息(一次点击)边界:
    gap 中 出现 1e8b052422(BOUND) / 1ec7094774(C7) / 1e910bbda0(M91) -> 断框
    上一条记录之后若非紧跟 1ef907874c(CLOSE) -> 上一条为独立框
术语高亮: 02 <u32 termid> 1e 4e 04 3a 14  <term text>  1e a6 04 a8 14
名字插入: 1e cf 02 1e 0a 后跟 02/1e <u32> 链; 0x01ea0153 = 主人公(ほたる)
用語辞典索引: entry 1089 @0x72492 (64B 记录, headword[20]+読み[26]+半角カナ[12]+flag)
"""
import struct, zlib, hashlib, re, sys, os, collections

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
C7 = b'\x1e\xc7\x09\x47\x74'
C7CLOSE = CLOSE + C7
M91 = b'\x1e\x91\x0b\xbd\xa0'
INS = b'\x1e\xcf\x02\x1e\x0a'
TERM = b'\x1e\x4e\x04\x3a\x14'
PLACEHOLDER = '〓'

# 主人公 初始名 (游戏中可改; "本バージョンでは初期名の「ほたる」")
VAR_TEXT = {
    0x01ea0153: 'ほたる',
}
# INS 链中的常量/槽位标记(非变量)
INS_CONSTS = {
    0x15500462, 0x1af9056c, 0x0d6503f2, 0x13d404bc, 0x019200ff,
    0x0b49032e, 0x1f470562,
} | set(range(0, 0x21))


def is_zlib(d):
    return len(d) > 1 and d[0] == 0x78


def maybe_z(d):
    if is_zlib(d):
        try:
            return zlib.decompress(d)
        except Exception:
            return d
    return d


def parse_cdar(u):
    if len(u) < 16 or u[:4] != b'CDAR':
        return None
    cnt = struct.unpack_from('<I', u, 8)[0]
    b2 = 16 + cnt * 4
    if cnt == 0 or b2 + 12 * cnt > len(u):
        return None
    return [struct.unpack_from('<III', u, b2 + 12 * k) for k in range(cnt)]


def walk(blob, path, depth, leaves, seen):
    u = maybe_z(blob)
    e = parse_cdar(u)
    if e is not None and depth < 3:
        for k, (o, ds, s) in enumerate(e):
            if s > 0 and o + s <= len(u):
                walk(u[o:o + s], path + '/' + str(k), depth + 1, leaves, seen)
        return
    h = hashlib.md5(u).hexdigest()
    if h in seen:
        return
    seen.add(h)
    leaves.append((path, u))


def load_leaves(data_path):
    f = open(data_path, 'rb')
    head = f.read(16)
    assert head[:4] == b'CDAR', 'not CDAR'
    count = struct.unpack_from('<I', head, 8)[0]
    base = 16 + count * 4
    f.seek(base)
    et = f.read(12 * count)
    ents = [struct.unpack_from('<III', et, 12 * i) for i in range(count)]
    leaves = []
    seen = set()
    for i, (o, ds, s) in enumerate(ents):
        f.seek(o)
        d = f.read(s)
        walk(d, str(i), 0, leaves, seen)
    return leaves


def valid_record(b, i):
    n = len(b)
    if i + 3 > n or b[i] != 4:
        return None
    ln = struct.unpack_from('<H', b, i + 1)[0]
    if ln < 2 or ln > 2000:
        return None
    e = i + 3 + ln
    if e > n or b[e - 1] != 0:
        return None
    body = b[i + 3:e - 1]
    if b'\x00' in body:
        return None
    if any(x < 0x20 and x != 0x0a for x in body):
        return None
    try:
        t = body.decode('cp932')
    except Exception:
        return None
    return (i, e, t)


def find_records(b):
    out = []
    i = 0
    n = len(b)
    while i < n - 3:
        if b[i] == 4:
            r = valid_record(b, i)
            if r:
                out.append(r)
                i = r[1]
                continue
        i += 1
    return out


def parse_inserts(gap):
    """返回 (插入串列表, 未解析值列表)。0x01ea0153 -> 主人公名。"""
    res, unres = [], []
    pos = 0
    while True:
        k = gap.find(INS, pos)
        if k < 0:
            break
        p = k + len(INS)
        parts = []
        while p + 5 <= len(gap) and gap[p] in (0x02, 0x1e):
            op = gap[p]
            val = struct.unpack_from('<I', gap, p + 1)[0]
            if op == 0x02 and val not in INS_CONSTS:
                parts.append(val)
            p += 5
        s = ''
        for val in parts:
            if val in VAR_TEXT:
                s += VAR_TEXT[val]
            else:
                s += PLACEHOLDER
                unres.append(val)
        if s:
            res.append(s)
        pos = p if p > k else k + 1
    return res, unres


def clean(s):
    # 行内换行合并 + 去全角空格包裹
    s = re.sub(r'[\u3000]*\n[\u3000]*', '', s)
    return s.replace('\n', '')


def process(b):
    recs = find_records(b)
    if not recs:
        return [], []
    msgs = []
    cur = []
    unres = []
    for i, (s, e, t) in enumerate(recs):
        gap = b[recs[i - 1][1]:s] if i > 0 else b[:s]
        sep = False
        if BOUND in gap or C7CLOSE in gap or M91 in gap:
            sep = True
        if i > 0 and not gap.startswith(CLOSE):
            sep = True
        if C7 in gap:
            sep = True
        if sep and cur:
            msgs.append(''.join(cur))
            cur = []
        ins, u = parse_inserts(gap)
        unres += u
        cur.extend(ins)
        cur.append(t)
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        after = b[e:nxt]
        if not after.startswith(CLOSE):
            msgs.append(''.join(cur))
            cur = []
    if cur:
        msgs.append(''.join(cur))
    return msgs, unres


RE_NOISE = [
    re.compile(r'^イベント・'),
    re.compile(r'^回想録[0-9０-９]+$'),
    re.compile(r'^配信イベント[0-9０-９]*$'),
    re.compile(r'^(ダミー|仮|予備|テスト)$'),
]
RE_NOISE_BIN = [
    re.compile(r'^[0-9A-Za-z_\-]+$'),
    re.compile(r'^[！？…、。\s\u3000]+$'),
]


def is_noise(t, binary=False):
    if t.startswith('＜デバッグ時のみ表示＞'):
        return True
    if '場合別実行エラー' in t:
        return True
    for r in RE_NOISE:
        if r.search(t):
            return True
    if binary:
        for r in RE_NOISE_BIN:
            if r.search(t):
                return True
    return False


def jp_ratio(t):
    if not t:
        return 0.0
    jp = sum(1 for ch in t if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff')
             or ('\u3000' <= ch <= '\u303f') or ('\uff01' <= ch <= '\uff60') or ch in '─―…‥')
    return jp / len(t)


# ---------- 用語辞典索引 (entry 1089 @0x72492, 64B 记录) ----------
def extract_glossary_index(leaves):
    """用語辞典索引: 権威来源 = entry 1089 の 64B レコード表 (record 1..382 = 用語ID 0..381)。"""
    for p, b in leaves:
        if len(b) != 153836 or b[72492 + 64:72492 + 68] != '高札'.encode('cp932'):
            continue
        base, S = 72492, 64
        out = []
        for k in range(1, 383):  # record 1..382
            r = b[base + k * S:base + (k + 1) * S]
            hb = r[0:20].split(b'\x00')[0]
            if not hb:
                continue
            try:
                h = hb.decode('cp932')
            except Exception:
                continue
            j = len(hb)
            while j < 46 and r[j] in (0x00, 0x20):
                j += 1
            rd = r[j:52].split(b'\x00')[0].decode('cp932', 'replace')
            rd = rd.strip().strip('\u3000').lstrip(' ').lstrip('@')
            out.append((h, rd))
        return out
    return []


DEF_TAIL = CLOSE + C7 + b'\x1e\xd3\x08\x90\x5e'


def collect_definitions(leaves):
    """用語辞典の解説文リソース: 単一レコード + 末尾 (CLOSE+C7+d3) を持つ entry。"""
    out = []
    seen = set()
    for p, b in leaves:
        if not b or b[0] != 4:
            continue
        r = valid_record(b, 0)
        if r and r[1] == len(b) - len(DEF_TAIL) and b[r[1]:] == DEF_TAIL:
            t = r[2]
            if t in seen:
                continue
            seen.add(t)
            out.append((p, t))
    return out


def main():
    data_path, out_main, out_gloss = sys.argv[1], sys.argv[2], sys.argv[3]
    leaves = load_leaves(data_path)
    print(f'leaves (unique) = {len(leaves)}')

    main_lines = []
    all_unres = collections.Counter()
    diag = collections.Counter()
    for p, b in leaves:
        if len(b) < 8 or len(b) > 0x2000000:
            continue
        if b[:3] == b'\x47\x58\x54':  # GXT texture
            continue
        msgs, unres = process(b)
        if not msgs:
            continue
        is_script = (CLOSE in b) or (BOUND in b) or (INS in b) or (TERM in b)
        kept = []
        for m in msgs:
            m2 = clean(m)
            if not m2:
                continue
            if not is_script and jp_ratio(m2) < 0.30 and not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', m2):
                diag['drop_jp'] += 1
                continue
            if is_noise(m2, binary=not is_script):
                diag['drop_noise'] += 1
                continue
            kept.append(m2)
        if not kept:
            continue
        for v in unres:
            all_unres[v] += 1
        main_lines.extend(kept)

    with open(out_main, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(main_lines) + '\n')

    # ---- 用語辞典 ----
    gl = extract_glossary_index(leaves)
    defs = collect_definitions(leaves)
    gloss_lines = []
    gloss_lines.append('■用語辞典・見出し語')
    for h, rd in gl:
        gloss_lines.append(f'【{h}】{rd}' if rd else f'【{h}】')
    gloss_lines.append('')
    gloss_lines.append('■用語辞典・解説文（見出し語との対応IDはデータ内に存在しないため順不同）')
    for p, t in defs:
        gloss_lines.append(clean(t))
    with open(out_gloss, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(gloss_lines) + '\n')

    print(f'main lines = {len(main_lines)}   glossary headwords = {len(gl)}   definitions = {len(defs)}')
    print('diag:', dict(diag))
    print('== 未解析 INS 值 ==')
    for v, n in all_unres.most_common(30):
        print(f'  0x{v:08x} x{n}')


if __name__ == '__main__':
    main()
