# -*- coding: utf-8 -*-
"""金色のコルダ3 (PSVita, PCSG01211) 全文本提取器
容器  : DATA.BIN = Koei CDAR v4 ('CDAR',ver=4,count,hash; count*u32 hashes; 12B/entry=(off,decSize,size); zlib)
引擎  : 金色のコルダ 2 ff / オクターヴ / 遥か6 DX 同族
文本记录: 04 <u16 len> <cp932 bytes> 00      (记录驱动扫描, 不失步; len 含结尾 00)
行内控制: 1b XX  (样式/记号槽, 剔除)
消息分隔: 1e8b052422 (BOUND) / 1ef907874c (CLOSE) / 1ec7094774 (C7) / 1e910bbda0 (M91)
名字插入: 1ecf021e0a 后的 02/1e <u32> 链
用語辞典: 记录内 `見出し語\n（読み）\n解説`  ->  `【見出し語】解説`
主角名  : 小日向 かなで / 愛称 ひな (名字:小日向 名前:かなで 愛称:ひな)
"""
import struct, zlib, re, sys, collections

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
C7 = b'\x1e\xc7\x09\x47\x74'
C7CLOSE = CLOSE + C7
M91 = b'\x1e\x91\x0b\xbd\xa0'
INS = b'\x1e\xcf\x02\x1e\x0a'
ZMAGIC = (b'\x78\x9c', b'\x78\x01', b'\x78\xda')

VAR_TEXT = {
    0x329007e7: 'かなで',    # 対話中通用名 (1348 处, 与 オクターヴ 同族锚定)
    0x01cb013a: '小日向',    # 姓
    0x01ea0153: 'かなで',    # 名
    0x05fa0288: 'ひな',      # 愛称
}
# 槽位/常量标记(非变量): 末尾出栈标记 0x15500462 / 0x019200ff、调用算子 0x1af9056c、
# 0x0d6503f2(deref 算子)、0x13d404bc、0x0b49032e、0x1f470562, 以及 0x00-0x3f 常量
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
    块内是后缀表达式: `02 <u32>`=压常量, `1e <u32>`=压变量/引用, `0d`=一元算子。
    仅当「去掉槽位/常量后恰好剩 1 个操作数且该操作数∈VAR_TEXT」时才替换为名字,
    否则整块产出 1 个占位符(不按操作数计,避免 〓〓〓)。"""
    res, unres = [], []
    pos = 0
    while True:
        k = gap.find(INS, pos)
        if k < 0:
            break
        p = k + len(INS)
        ops = []
        unknown = False
        while p + 5 <= len(gap) and len(ops) < 16:
            if gap[p] in (0x02, 0x1e):
                ops.append((gap[p], struct.unpack_from('<I', gap, p + 1)[0]))
                p += 5
            elif gap[p] == 0x0d:
                ops.append((0x0d, None))
                p += 1
            elif gap[p] == 0x07 and p + 3 <= len(gap):
                # 07 <u16> = 3 字节不定长指令(带下标), 结果为运行期值
                unknown = True
                ops.append((0x07, struct.unpack_from('<H', gap, p + 1)[0]))
                p += 3
            else:
                break
        vals = [v for o, v in ops if o in (0x02, 0x1e) and v not in INS_CONSTS]
        if len(vals) == 1 and vals[0] in VAR_TEXT and not unknown:
            res.append(VAR_TEXT[vals[0]])
        elif vals or unknown:
            res.append(PLACEHOLDER)
            unres.extend(vals)
        pos = p if p > k else k + 1
    return res, unres


def clean(s):
    s = re.sub(r'[\u3000]*\n[\u3000]*', '', s)
    s = s.replace('\t', '').replace('\n', '')
    return s


def flat(s):
    """把内部换行/制表/全角空格合并为单空格(辞典解说用)"""
    s = s.replace('\t', '')
    s = re.sub(r'[\u3000\s]*\n[\u3000\s]*', '', s)
    return s


# 用語辞典: 记录内 `見出し語\n（読み）\n解説` (読み为假名/长音符等)
RE_GLOSS = re.compile(
    r'^\s*([^\n（]{1,24})\n[（(]([ぁ-んゝゞー\u3099\u309a\u30fc\s\u3000]*)[）)](.*)$',
    re.S)


def gloss_split(raw):
    """返回 (見出し語, 解説) 或 None"""
    m = RE_GLOSS.match(raw)
    if not m:
        return None
    head = m.group(1).strip()
    rest = m.group(3)
    return head, rest


RE_NOISE = [
    re.compile(r'^イベント・'),
    re.compile(r'^追加イベント'),
    re.compile(r'^回想録[0-9０-９]+$'),
    re.compile(r'^配信イベント[0-9０-９]*$'),
    re.compile(r'^札[0-9０-９]+$'),
    re.compile(r'^(ダミー|仮|予備|テスト)$'),
    re.compile(r'^バグ発生'),
    re.compile(r'^システム_'),
    re.compile(r'^フィールド処理_'),
    re.compile(r'を朝遭遇候補者にセット$'),
    re.compile(r'^(新|神南|.*)出現不可$'),
    re.compile(r'出現不可フラグをセット$'),
    re.compile(r'フラグをセット$'),
    re.compile(r'.+恋愛段階更新$'),
    re.compile(r'.+恋愛段階が増加→$'),
    re.compile(r'.+親密度が増加→$'),
    re.compile(r'.+恋愛失敗$'),
    re.compile(r'.+恋愛進行度[０-９0-9１-９]$'),
    re.compile(r'.+恋愛段階[０-９0-9１-９]$'),
    re.compile(r'^.+の親密度が(増加|減少)'),
    re.compile(r'^.+の恋愛段階が(増加|減少)'),
    re.compile(r'^[？?]+[^　]'),   # 开发用「？？」占位串(真对白里的 '？　…' 不受影响)
    re.compile(r'^.+感動(済み|してない)$'),
    re.compile(r'^(感動してない|感動済み|整って(い)?る|整ってない|発生させる|発生させない'
               r'|進行している|進行していない|出現可|出現不可|１曲目|２曲目)$'),
    re.compile(r'恋愛[０-９0-9１-９](不協|珠玉)$'),
    re.compile(r'モバイルジョイキー'),
    re.compile(r'ユーザー特定用データ'),
    re.compile(r'フラグ$'),
]

# ---- 开发用「判定」菜单（每个事件脚本开头的调试块）----
DEBUG_Q = re.compile(
    r'^('
    r'主人公と.+は別フィールド？'
    r'|.+恋愛進行度.+？'          # 東金との恋愛進行度は？ / 七海の恋愛進行度は？
    r'|.+恋愛レベルは？|.+恋愛進行中？'
    r'|.+は[０-９0-9１-９]+曲目.*感動した？'
    r'|.+は[０-９0-9１-９]+曲目で感動した'
    r'|.+は[０-９0-9１-９]+曲目では感動してない'
    r'|[０-９0-9１-９]+曲目で感動した'
    r'|[０-９0-9１-９]+曲目では感動してない'
    r'|.+曲目の完成度は高かった？'
    r'|.+メイン[０-９0-9]+発生？'
    r'|.+発生？'
    r'|.+の起きる条件は？'
    r'|.+が感動したのは？'
    r'|.+との恋愛は進行してる？'
    r'|２人練習誘いメールきた？'
    r'|すでに練習済み？'
    r'|.+と.+は出現可？|.+は出現可？|.+は出現中？|.+は別フィールド？'
    r'|完成度高かった|完成度高くなかった'
    r')$')

DEBUG_OPT = re.compile(
    r'^('
    r'別フィールド|同じフィールド|きた|きていない|済み|まだ'
    r'|出現可|出現不可|発生させる|発生させない'
    r'|整って(い)?る|整ってない'
    r'|完成度高かった|完成度高くなかった|進行している|進行していない'
    r'|レベル[０-９0-9１-９]|恋愛[０-９0-9１-９]'
    r'|.+恋愛進行度[０-９0-9]|.+恋愛段階[０-９0-9]|.+恋愛レベル[０-９0-9]'
    r'|.+進行中|.+進行して(い)?ない|.+は不在|.+感動して(い)?ない|.+感動した'
    r'|.+ＭＦ未使用|.+ＭＦ使用済み|.+通常'
    r'|[０-９0-9１-９]+段階以上'
    r'|[０-９0-9１-９１２]+曲目'
    r')$')


def is_noise(t):
    if t.startswith('＜デバッグ時のみ表示＞'):
        return True
    if '場合別実行エラー' in t:
        return True
    if '正式版では表示されません' in t:
        return True
    if 'デバッグ' in t:
        return True
    if 'が呼ばれています' in t:
        return True
    return any(r.search(t) for r in RE_NOISE)


def drop_debug_blocks(msgs):
    """删除「判定问题 + 其后紧邻的短选项」这一调试块"""
    out = []
    i = 0
    while i < len(msgs):
        if DEBUG_Q.match(msgs[i][0].strip()):
            i += 1
            while i < len(msgs) and DEBUG_OPT.match(msgs[i][0].strip()):
                i += 1
            continue
        out.append(msgs[i])
        i += 1
    return out


def is_noise_rec(t):
    """纯脚本标签/内部标识记录（参与分段，但其文本不进入成品）"""
    if is_noise(t):
        return True
    if '_' in t and not re.search(r'[。！？]', t) and len(t) <= 40:
        return True
    return False


def is_texty(t):
    if len(t) < 2:
        return False
    good = sum(1 for ch in t if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff')
               or ('\u3000' <= ch <= '\u303f') or ('\uff01' <= ch <= '\uff60')
               or ch in '─―…‥→♥♪')
    bad = sum(1 for ch in t if (0xE000 <= ord(ch) <= 0xF8FF) or (0xFF61 <= ord(ch) <= 0xFF9F)
              or ord(ch) < 0x20)
    return good >= 2 and bad <= max(1, good * 0.2)


def process(b):
    """返回 [(clean_text, raw_text), ...], unres, n_gloss_rec"""
    recs = find_records(b)
    if not recs:
        return [], [], 0
    n_gloss_rec = sum(1 for _, _, t in recs if '\n（' in t or '\n(' in t)
    msgs, cur, unres = [], [], []
    for i, (s, e, t) in enumerate(recs):
        gap = b[recs[i - 1][1]:s] if i > 0 else b[:s]
        sep = False
        if BOUND in gap or C7CLOSE in gap or M91 in gap or C7 in gap:
            sep = True
        if i > 0 and not gap.startswith(CLOSE) and b[recs[i - 1][1]:recs[i - 1][1] + 5] != CLOSE:
            sep = True
        if sep and cur:
            msgs.append((''.join(x[0] for x in cur), '\n'.join(x[1] for x in cur)))
            cur = []
        ins, u = parse_inserts(gap)
        unres += u
        for x in ins:
            cur.append((x, x))
        if is_noise_rec(t):
            rec_txt = ''
        else:
            rec_txt = t
        cur.append((rec_txt, rec_txt))
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        tail = b[e:nxt]
        if not (tail.startswith(CLOSE) or tail.startswith(INS)):
            msgs.append((''.join(x[0] for x in cur), '\n'.join(x[1] for x in cur)))
            cur = []
    if cur:
        msgs.append((''.join(x[0] for x in cur), '\n'.join(x[1] for x in cur)))
    return msgs, unres, n_gloss_rec


def script_score(b):
    return b.count(CLOSE) + b.count(BOUND) + b.count(M91) + b.count(INS)


def main():
    data_path, out_path, gloss_path = sys.argv[1], sys.argv[2], sys.argv[3]
    main_lines, gloss_lines = [], []
    n_ent = n_gloss_ent = total_msgs = 0
    all_unres = collections.Counter()
    diag = collections.Counter()
    diag_samples = collections.defaultdict(list)
    seen = set()
    import hashlib
    for lab, b in load(data_path):
        if len(b) < 8 or len(b) > 0x4000000:
            continue
        h = hashlib.md5(b).digest()
        if h in seen:
            diag['dedup'] += 1
            continue
        seen.add(h)
        msgs, unres, n_gloss_rec = process(b)
        if not msgs:
            continue
        msgs = drop_debug_blocks(msgs)
        total_msgs += len(msgs)
        kept = []
        for c, raw in msgs:
            g = gloss_split(raw)
            if g:
                head, rest = g
                body = flat(rest).strip()
                if not body or body in ('（', ')'):
                    continue
                gloss_lines.append(f'【{head}】{body}')
                continue
            m2 = clean(c)
            if not m2:
                continue
            if PLACEHOLDER in m2 and not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', m2):
                diag['drop_fragment'] += 1
                continue
            if not is_texty(m2):
                diag['drop_binary'] += 1
                if len(diag_samples['drop_binary']) < 20:
                    diag_samples['drop_binary'].append((lab, m2[:60]))
                continue
            if is_noise(m2):
                diag['drop_noise'] += 1
                if len(diag_samples['drop_noise']) < 20:
                    diag_samples['drop_noise'].append((lab, m2[:60]))
                continue
            kept.append(m2)
        if kept:
            n_ent += 1
            main_lines.extend(kept)
        for v in unres:
            all_unres[v] += 1
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(main_lines) + '\n')
    with open(gloss_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(gloss_lines) + '\n')
    print(f'entries={n_ent} lines={len(main_lines)} glossary_lines={len(gloss_lines)} total_msgs={total_msgs}')
    print('diag:', dict(diag))
    for k in ('drop_binary', 'drop_noise'):
        print(f'-- {k} samples --')
        for lab, t in diag_samples[k][:8]:
            print(f'   {lab}: {t!r}')
    print('== 未解析插入值 ==')
    for v, n in all_unres.most_common(50):
        print(f'  0x{v:08x} x{n}')


if __name__ == '__main__':
    main()
