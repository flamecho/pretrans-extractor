# -*- coding: utf-8 -*-
"""金色のコルダ2 ff (PSVita, PCSG01124) 全文本提取器
容器  : DATA.BIN = Koei CDAR v4 ('CDAR',ver=4,count,hash; count*u32 hashes; 12B/entry=(off,decSize,size); zlib)
引擎  : 金色のコルダ オクターヴ / 遥か6 DX 同族
文本记录: 04 <u16 len> <cp932 bytes> 00      (记录驱动扫描, 不失步; len 含结尾 00)
行内控制: 1b XX  (样式/记号槽, 剔除; 主要 1b b4 / 1b b5 = 术语强调括)
消息分隔: 1e8b052422 (BOUND) / 1ef907874c (CLOSE) / 1ec7094774 (C7) / 1e910bbda0 (M91)
名字插入: 1ecf021e0a 后的 02/1e <u32> 链
主角名  : 姓=日野 名=香穂子 愛称=香穂   (变量表 entry7368; 默认名说明 entry11328)
用語辞典: `見出し語（読み）解説` -> `【見出し語】解説`
"""
import struct, zlib, re, os, sys, collections

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
C7 = b'\x1e\xc7\x09\x47\x74'
C7CLOSE = CLOSE + C7
M91 = b'\x1e\x91\x0b\xbd\xa0'
INS = b'\x1e\xcf\x02\x1e\x0a'
ZMAGIC = (b'\x78\x9c', b'\x78\x01', b'\x78\xda')

VAR_TEXT = {
    0x01cb013a: '日野',      # 姓
    0x01ea0153: '香穂子',    # 名
    0x05fa0288: '香穂',      # 愛称
    0x1d76056e: '日野',      # 想い出用姓
    0x1d950587: '香穂子',    # 想い出用名
    0x2a0d06bc: '香穂',      # 想い出用愛称
    0x329007e7: '香穂子',    # 対話中通用名 (名前) -> 香穂子
}
# 变量表(entry7368)实测的变量名 -> 语义占位标签(运行期取值, 静态不可求)
# 仅保留"单操作数插入且语义明确"者; 结构体/数值类(0x1005037a 等)不贴标签, 保持 〓
VAR_LABEL = {
    0x15af050d: '残り日数',
    0x16690522: '同伴相手',
    0x29e606b9: '人物',
}
INS_CONSTS = {
    0x15500462, 0x1af9056c, 0x0d6503f2, 0x13d404bc, 0x019200ff,
    0x0b49032e, 0x1f470562,
} | {i for i in range(0x00, 0x40)}
PLACEHOLDER = '〓'


# ---------------- 容器 ----------------
def parse_cdar_bytes(data, label, depth=0):
    if data[:4] != b'CDAR':
        return
    unk1, count, unk2 = struct.unpack_from('<III', data, 4)
    base = 16 + count * 4
    for i in range(count):
        o, ds, sz = struct.unpack_from('<III', data, base + 12 * i)
        if sz == 0 or o + sz > len(data):
            continue
        raw = data[o:o + sz]
        if raw[:2] in ZMAGIC:
            try:
                d = zlib.decompress(raw)
            except Exception:
                d = raw
        else:
            d = raw
        lab = f'{label}#{i:05d}'
        if d[:4] == b'CDAR' and depth < 4:
            yield from parse_cdar_bytes(d, lab, depth + 1)
        else:
            yield lab, d


def load(path):
    return parse_cdar_bytes(open(path, 'rb').read(), 'root')


# ---------------- 文本记录 ----------------
_CTRL_OK = {0x09, 0x0a, 0x1b}


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
    # 拒绝含行内控制字节(除 \n / ESC) -> 剔除把二进制误当文本的记录
    for x in body:
        if x < 0x20 and x not in _CTRL_OK:
            return None
    try:
        t = decode_rec(body)
    except Exception:
        return None
    return (i, e, t)


def decode_rec(body):
    """cp932 + 行内 1b XX 控制码(剔除)"""
    out = []
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == 0x1b:
            i += 2
            continue
        if c < 0x20:
            out.append(chr(c))
            i += 1
            continue
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            if i + 2 <= n:
                out.append(body[i:i + 2].decode('cp932', errors='replace'))
            i += 2
        else:
            out.append(chr(c))
            i += 1
    return ''.join(out)


def find_records(b):
    out = []
    i, n = 0, len(b)
    find = b.find
    while True:
        i = find(b'\x04', i)
        if i < 0 or i >= n - 3:
            break
        r = valid_record(b, i)
        if r:
            out.append(r)
            i = r[1]
        else:
            i += 1
    return out


def parse_inserts(gap):
    """每个 1e cf 02 1e 0a 块 = 一个插入值。
    块内为通用指令流,操作数按定长消费: 02 <u32>(常量/字段选择子) / 1e <u32>(变量引用)
    / 0d <u16> / 07 <u16>(带下标取值)。★ 只认 02 会静默丢掉主角名(名字槽走 1e 通道)。
    单值 -> 名字/语义标签; 多值 -> 单个占位符。"""
    res, unres = [], []
    pos = 0
    while True:
        k = gap.find(INS, pos)
        if k < 0:
            break
        p = k + len(INS)
        parts = []
        while p < len(gap):
            op = gap[p]
            if op == 0x02 and p + 5 <= len(gap):
                val = struct.unpack_from('<I', gap, p + 1)[0]
                if val not in INS_CONSTS:
                    parts.append(val)
                p += 5
            elif op == 0x1e and p + 5 <= len(gap):
                val = struct.unpack_from('<I', gap, p + 1)[0]
                if val not in INS_CONSTS:
                    parts.append(val)
                p += 5
            elif op == 0x07 and p + 3 <= len(gap):
                # u16 操作数(带下标取值): 静态不可求 -> 占位
                parts.append(None)
                p += 3
            elif op == 0x0d:
                # 1 字节无操作数指令
                p += 1
            else:
                break
        if len(parts) == 1:
            v = parts[0]
            if isinstance(v, int) and v in VAR_TEXT:
                res.append(VAR_TEXT[v])
            elif isinstance(v, int) and v in VAR_LABEL:
                res.append('〔' + VAR_LABEL[v] + '〕')
                unres.append(v)
            else:
                res.append(PLACEHOLDER)
                if isinstance(v, int):
                    unres.append(v)
        elif len(parts) > 1:
            res.append(PLACEHOLDER)
            unres.extend(x for x in parts if isinstance(x, int))
        pos = p if p > k else k + 1
    return res, unres


def clean(s):
    s = re.sub(r'[\u3000]*\n[\u3000]*', '', s)
    s = s.replace('\t', '').replace('\n', '')
    return s


# 用語辞典: `見出し語（読み）解説`
# 読み 可能含: 平假名/片假名/长音符/浊点(U+309B)/半浊点(U+309C)/中点・/空白
_READ = r'[ぁ-んァ-ヶゝゞー゛゜\u3099\u309a・\u3000\s]'
GLOSS = re.compile(r'^(.{1,20}?)（(' + _READ + r'+)）(.*)$')
RE_GLOSS_REC = re.compile(r'^[^\n（]{1,20}\n?（' + _READ + r'{1,40}）')

RE_NOISE = [
    re.compile(r'^イベント・'),
    re.compile(r'^回想録[0-9０-９]+$'),
    re.compile(r'^配信イベント[0-9０-９]*$'),
    re.compile(r'^札[0-9０-９]+$'),
    re.compile(r'^(ダミー|仮|予備|テスト)$'),
    re.compile(r'^バグ発生'),
    re.compile(r'フラグ$'),
]


def is_noise(t):
    if t.startswith('＜デバッグ時のみ表示＞'):
        return True
    if '場合別実行エラー' in t:
        return True
    if '正式版では表示されません' in t:
        return True
    return any(r.search(t) for r in RE_NOISE)


def jp_ratio(t):
    if not t:
        return 0.0
    jp = sum(1 for ch in t if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff')
             or ('\u3000' <= ch <= '\u303f') or ('\uff01' <= ch <= '\uff60') or ch in '─―…‥')
    return jp / len(t)


def is_texty(t):
    """剔除二进制误命中：要求有足够日文字符，且异常字符(PUA/半角片假名/〓/控制)占比低"""
    if len(t) < 2:
        return False
    good = sum(1 for ch in t if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff')
               or ('\u3000' <= ch <= '\u303f') or ('\uff01' <= ch <= '\uff60')
               or ch in '─―…‥→♥♪')
    bad = sum(1 for ch in t if (0xE000 <= ord(ch) <= 0xF8FF) or (0xFF61 <= ord(ch) <= 0xFF9F)
              or ord(ch) < 0x20)
    return good >= 2 and bad <= max(1, good * 0.2)


def gloss_format(t):
    m = GLOSS.match(t)
    if m:
        return '【' + m.group(1) + '】' + m.group(3)
    return t


def process(b):
    recs = find_records(b)
    if not recs:
        return [], [], 0
    n_gloss_rec = sum(1 for _, _, t in recs if RE_GLOSS_REC.match(t))
    msgs, cur, unres = [], [], []
    for i, (s, e, t) in enumerate(recs):
        gap = b[recs[i - 1][1]:s] if i > 0 else b[:s]
        sep = False
        if BOUND in gap or C7CLOSE in gap or M91 in gap or C7 in gap:
            sep = True
        if i > 0 and not gap.startswith(CLOSE) and b[recs[i - 1][1]:recs[i - 1][1] + 5] != CLOSE:
            sep = True
        if sep and cur:
            msgs.append(''.join(cur)); cur = []
        ins, u = parse_inserts(gap)
        unres += u
        for x in ins:
            cur.append(x)
        cur.append(t)
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        after = b[e:nxt]
        # 记录后紧跟 CLOSE(继续同框) 或 INS(该行插入名/变量后再接文本) 都不换行
        if not (after.startswith(CLOSE) or after.startswith(INS)):
            msgs.append(''.join(cur)); cur = []
    if cur:
        msgs.append(''.join(cur))
    return msgs, unres, n_gloss_rec


def script_score(b):
    return b.count(CLOSE) + b.count(BOUND) + b.count(M91) + b.count(INS)


def main():
    data_path, out_path, gloss_path = sys.argv[1], sys.argv[2], sys.argv[3]
    main_lines, gloss_lines = [], []
    n_ent = n_gloss_ent = total_recs = 0
    all_unres = collections.Counter()
    diag = collections.Counter()
    diag_samples = collections.defaultdict(list)
    noise_dump = []
    seen = set()
    import hashlib
    for lab, b in load(data_path):
        if len(b) < 8 or len(b) > 0x4000000:
            continue
        # 嵌套 CDAR 会带来大量逐字节副本 -> 按内容去重(保留首次出现)
        h = hashlib.md5(b).digest()
        if h in seen:
            diag['dedup'] += 1
            continue
        seen.add(h)
        msgs, unres, n_gloss_rec = process(b)
        if not msgs:
            continue
        total_recs += len(msgs)
        is_script = script_score(b) >= 3
        # 该条目是否用語辞典条目：多数记录为 `見出し語（読み）解説` 形态
        is_gloss = n_gloss_rec >= max(3, len(msgs) * 0.5)
        kept = []
        for m in msgs:
            m2 = clean(m)
            if not m2:
                continue
            if not is_texty(m2):
                diag['drop_binary'] += 1
                if len(diag_samples['drop_binary']) < 20: diag_samples['drop_binary'].append((lab, m2[:60]))
                continue
            if is_noise(m2):
                diag['drop_noise'] += 1
                if len(diag_samples['drop_noise']) < 20: diag_samples['drop_noise'].append((lab, m2[:60]))
                noise_dump.append(m2)
                continue
            kept.append(m2)
        if not kept:
            continue
        for v in unres:
            all_unres[v] += 1
        if is_gloss:
            n_gloss_ent += 1
            gloss_lines.extend(gloss_format(x) for x in kept)
        else:
            n_ent += 1
            main_lines.extend(kept)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(main_lines) + '\n')
    with open(gloss_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(gloss_lines) + '\n')
    print(f'entries={n_ent} lines={len(main_lines)} glossary_entries={n_gloss_ent} glossary_lines={len(gloss_lines)} total_msgs={total_recs}')
    print('diag:', dict(diag))
    for k in ('drop_binary', 'drop_noise'):
        print(f'-- {k} samples --')
        for lab, t in diag_samples[k][:8]:
            print(f'   {lab}: {t!r}')
    print('== 未解析插入值 ==')
    for v, n in all_unres.most_common(40):
        print(f'  0x{v:08x} x{n}')


if __name__ == '__main__':
    main()
