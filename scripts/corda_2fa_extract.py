# -*- coding: utf-8 -*-
"""金色のコルダ2f アンコール (PSP) 全文本提取器 v3.

容器: CDAR v4 (DATA.BIN, 递归嵌套, 内容级去重)
文本记录: 04 <u16 len> <cp932 bytes> 00
「一次点击」= 一个文本框: 若下一条记录的间隔含名字插入(INS)且无 BOUND/M91,
                        则与上一条记录属同一框(句中插入的名字); 否则开新框。
名字插入: 1e cf 02 1e 0a 之后的 02/1e 指令链 (尾 1e ff 00 92 01)。
内联标记: 1b b0-b9 = 高亮/用語链接边界 → 剥离。
用語辞典: 条目为「見出し語\\n（よみ）\\n解説…」→ 输出 【見出し語】解説。

用法: python corda2f_extract.py <DATA.BIN|ISO> <base> <main.txt> <gloss.txt>
"""
import sys, os, struct, re, zlib, collections, io

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
M91 = b'\x1e\x91\x0b\xbd\xa0'
C7 = b'\x1e\xc7\x09\x47\x74'
INS = b'\x1e\xcf\x02\x1e\x0a'
INS_TERM = b'\x1e\xff\x00\x92\x01'  # 名字插入块终结操作数 (1e 019200ff)
SETUP = b'\x1e\x97\x03\xef\x0c'   # 文本框显示设定末尾
APPEND = b'\x1e\x7e\x02\xb2\x05'  # 逐段追加(同一文本框续写, 如折行/句中插名)
ESC_RE = re.compile(rb'\x1b[\xb0-\xb9]')

# 主人公 = 日野 香穂子 (引擎级变量 ID, 与 オクターヴ 同构)
# 依据 DATA.BIN 内变量表「想い出用姓=日野 / 名=香穂子 / 愛称=香穂」
VAR_TEXT = {
    0x01cb013a: '日野', 0x01ea0153: '香穂子', 0x329007e7: '香穂子', 0x05fa0288: '香穂',
    0x1d76056e: '日野', 0x1d950587: '香穂子', 0x2a0d06bc: '香穂子',
    0x2350067d: '日野香穂子', 0x42820847: 'ひの　かほこ',
}
INS_CONSTS = {0x15500462, 0x1af9056c, 0x0d6503f2, 0x13d404bc, 0x019200ff, 0x0b49032e, 0x1f470562}
INS_CONSTS |= set(range(0x40))

SKIP_MAGIC4 = (b'TIM2', b'PSMF', b'G1T\x00', b'MIG.', b'OMG\x00', b'SCR\x00')
SKIP_MAGIC3 = (b'GIM',)


def read_leaves(rfile, base, path=''):
    rfile.seek(base)
    head = rfile.read(16)
    if head[:4] != b'CDAR':
        return
    cnt = struct.unpack_from('<I', head, 8)[0]
    rfile.seek(base + 0x10 + 4 * cnt)
    et = rfile.read(12 * cnt)
    for i in range(cnt):
        off, dec, sz = struct.unpack_from('<III', et, 12 * i)
        if sz == 0:
            continue
        rfile.seek(base + off)
        seg = rfile.read(sz)
        p = f'{path}{i}'
        if seg[:4] == b'CDAR' and len(seg) >= 8 and struct.unpack_from('<I', seg, 4)[0] == 4:
            yield from read_leaves(io.BytesIO(seg), 0, p + '/')
        else:
            data = seg
            if dec != sz and seg[:1] == b'\x78':
                try:
                    data = zlib.decompress(seg)
                except Exception:
                    pass
            yield (p, data)


def valid_record(b, i):
    n = len(b)
    if i + 3 > n or b[i] != 4:
        return None
    ln = struct.unpack_from('<H', b, i + 1)[0]
    if ln < 2 or ln > 4000:
        return None
    e = i + 3 + ln
    if e > n or b[e - 1] != 0:
        return None
    body = b[i + 3:e - 1]
    if b'\x00' in body:
        return None
    if any(x < 0x20 and x != 0x0a and x != 0x1b for x in body):
        return None
    return (i, e, body)


def find_records(b):
    out, i, n = [], 0, len(b)
    while i < n - 3:
        if b[i] == 4:
            r = valid_record(b, i)
            if r:
                out.append(r)
                i = r[1]
                continue
        i += 1
    return out


def decode_body(body):
    s = ESC_RE.sub(b'', body).decode('cp932', 'replace')
    for a, b in FONT_SLOT.items():
        s = s.replace(a, b)
    return s


# 字体替换槽 (cp932 码位上画其它字形) —— 仅「上下文可判定」者替换, 其余保留原字并出报告
FONT_SLOT = {
    'ε': '™',   # メモリースティックε → メモリースティック™ (同系列作品已确认)
}


def insert_text(gap):
    res, unres, pos = '', [], 0
    while True:
        k = gap.find(INS, pos)
        if k < 0:
            break
        p = k + len(INS)
        while p + 5 <= len(gap) and gap[p] in (0x02, 0x1e):
            op = gap[p]
            val = struct.unpack_from('<I', gap, p + 1)[0]
            if op == 0x02:
                if val not in INS_CONSTS:
                    if val in VAR_TEXT:
                        res += VAR_TEXT[val]
                    else:
                        res += '〓'
                        unres.append(val)
            else:
                if val in VAR_TEXT:
                    res += VAR_TEXT[val]
                elif val not in INS_CONSTS and val != 0:
                    res += '〓'
                    unres.append(val)
            p += 5
        pos = p if p > k else k + 1
    return res, unres


def clean(s):
    return re.sub(r'[\u3000]', '', s.replace('\n', '')).strip()


RE_LABEL = [
    re.compile(r'^イベント・'),
    re.compile(r'^回想録[0-9０-９]+$'),
    re.compile(r'^(ダミー|仮|予備|テスト)$'),
    re.compile(r'フラグ$'),
    re.compile(r'^(バグ発生|制服着用扱いとして|ミニキャラデバッグ$)'),
    re.compile(r'デバッグ時'),
    re.compile(r'デバッグ情報'),
    re.compile(r'回想データをセット'),
    re.compile(r'指定された背景は、対応していません'),
    re.compile(r'^[0-9A-Za-z_\-]+$'),
]
RE_TRIVIAL = re.compile(r'[！？…、。\s\u3000]*')


def is_label(t):
    """内部标签/调试文本 —— 既不断言内容, 也断开当前框。"""
    return any(r.search(t) for r in RE_LABEL)


def is_trivial(t):
    """只有标点/空白/读音括号 —— 单独成框时丢弃(停顿帧)。"""
    return RE_TRIVIAL.fullmatch(t) is not None or re.fullmatch(r'（[^）]*）', t) is not None


def process(b):
    """框重建: 新框 iff 间隔含 BOUND/M91/文本框设定(SETUP); 否则为同一框的续写(句中被拆的行)。"""
    recs = find_records(b)
    if not recs:
        return [], []
    msgs, unres, cur = [], [], None
    ins_open = False
    for i, (s, e, body) in enumerate(recs):
        gap = b[recs[i - 1][1]:s] if i > 0 else b[:s]
        t = decode_body(body)
        if is_label(clean(t)):          # 内部标签/调试文本: 断开当前框
            if cur is not None:
                msgs.append(cur)
                cur = None
            ins_open = False
            continue
        ins, u = insert_text(gap)
        unres += u
        # 「…」「。」这类只有标点的记录 = 框内文本更新/停顿帧。
        # 仅当当前框「尚未收句」(不以 。！？」』） 结尾) 时并入; 否则单独成框(稍后作停顿帧丢弃)。
        triv = is_trivial(clean(t))
        cur_open = bool(cur) and clean(cur)[-1:] not in '。！？」』）'
        new = (BOUND in gap) or (M91 in gap) or (C7 in gap) or (SETUP in gap)
        if triv and cur_open:
            new = False
            cont = True
        else:
            # 同一框续写: 追加码 / 名字插入块(含跨记录) / 间隔恰好只有 CLOSE
            cont = (not new) and (APPEND in gap or INS in gap or ins_open or gap == CLOSE)
        if cont and cur is not None:
            cur += ins + t
        else:
            if cur is not None:
                msgs.append(cur)
            cur = ins + t
        # 名字插入块可能「横跨一条文本记录」: 记录本身即插入块的字面量,
        # 其后间隔里只剩收尾的 02/1e 操作数 → 仍属同一框。
        if INS in gap:
            ins_open = True
        if INS_TERM in gap or new:
            ins_open = False
    if cur is not None:
        msgs.append(cur)
    return msgs, unres


def split_gloss(text):
    """若为「見出し語\\n（よみ）\\n解説」则返回 (head, body)；否则 None。"""
    lines = text.split('\n')
    if len(lines) < 2 or not lines[1].startswith('（'):
        return None
    j = 1
    while j < len(lines) and not lines[j].rstrip().endswith('）'):
        j += 1
    if j >= len(lines):
        return None
    if 'デバッグ' in lines[0] or 'バグ' in lines[0]:
        return None
    return lines[0].strip(), ''.join(lines[j + 1:])


def main():
    src, base = sys.argv[1], int(sys.argv[2])
    main_path, gloss_path = sys.argv[3], sys.argv[4]
    rfile = open(src, 'rb')
    seen = set()
    main_lines, gloss_lines = [], []
    unres_counter = collections.Counter()
    n_textfiles = 0
    for path, b in read_leaves(rfile, base):
        if len(b) < 8 or len(b) > 0x2000000:
            continue
        m4, m3 = b[:4], b[:3]
        if m4 in SKIP_MAGIC4 or m3 in SKIP_MAGIC3 or m4 in (b'RIFF', b'\x89PNG'):
            continue
        if BOUND not in b and CLOSE not in b:
            continue
        hh = hash(b)
        if hh in seen:
            continue
        seen.add(hh)
        n_textfiles += 1
        msgs, unres = process(b)
        for v in unres:
            unres_counter[v] += 1
        for m in msgs:
            g = split_gloss(m)
            if g:
                head, body = g
                body = clean(body)
                if head and body:
                    gloss_lines.append(f'【{head}】{body}')
                continue
            m2 = clean(m)
            if not m2 or is_label(m2) or is_trivial(m2):
                continue
            main_lines.append(m2)
    with open(main_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(main_lines) + ('\n' if main_lines else ''))
    with open(gloss_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(gloss_lines) + ('\n' if gloss_lines else ''))
    print(f'text-files={n_textfiles} main_lines={len(main_lines)} gloss_lines={len(gloss_lines)}')
    print('== 未解析插入值 (top) ==')
    for v, n in unres_counter.most_common(25):
        print(f'  0x{v:08x} x{n}')


if __name__ == '__main__':
    main()
