# -*- coding: utf-8 -*-
"""金色のコルダ3 AnotherSky feat.神南/至誠館/天音学園 (PSVita PCSG01212) 全文本提取器

容器 : DATA.BIN / DATA_AS1-3.BIN = Koei CDAR v4
       ('CDAR', ver=4, count, hash; 0x10 起 count*u32 哈希表; 0x10+4n 起 count*12
        条目 {offset,decompSize,size}; offset 0x800 对齐; 多 zlib; 条目为 CDAR v4 = 嵌套递归)
引擎 : 金色のコルダ2 ff / オクターヴ / 遥か6 DX 同族
文本记录: 04 <u16 len> <cp932> 00   (len 含结尾 00; 记录驱动扫描, 不失步)
行内控制: 1b XX (b0/b1 与 b6/b7/b8/b9 = 强调/样式槽) -> 剔除
消息分隔: 1e8b052422(BOUND) / 1ef907874c(CLOSE) / 1ec7094774(C7) / 1e910bbda0(M91)
插入块 : 1ecf021e0a + 指令序列(02 u32 / 1e u32 / 07 u16 / 单字节op)
         终止 = 1e 019200ff 或 1e 1af9056c
主角名 : 姓=小日向 / 名=かなで / 愛称=ひな   (entry 内「名前を入力する画面で…」记录明确)
用語辞典: `見出し語\n（よみ）\n解説` 或 `「見出し語」\n（よみ）\n解説` -> 【見出し語】解説
"""
import struct, zlib, re, sys, collections, hashlib

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
C7 = b'\x1e\xc7\x09\x47\x74'
M91 = b'\x1e\x91\x0b\xbd\xa0'
INS = b'\x1e\xcf\x02\x1e\x0a'
TERM1 = 0x019200ff
TERM2 = 0x1af9056c
ZMAGIC = (b'\x78\x9c', b'\x78\x01', b'\x78\xda')

# --- 插入块变量 ID -> 文本 ---
NAME_MAP = {
    0x329007e7: 'かなで',    # 通用名(对话中称呼)
    0x01ea0153: 'かなで',    # 名前
    0x01cb013a: '小日向',    # 姓
    0x05fa0288: 'ひな',      # 愛称
    0x1d76056e: '小日向',    # 想い出用姓
    0x1d950587: 'かなで',    # 想い出用名
    0x2a0d06bc: 'ひな',      # 想い出用愛称
}
# 语义明确的运行期变量 -> 〔标签〕
SEM_MAP = {
    0x1b4504e7: 'プレゼント',
    0x292305e2: '練習アイテム',
    0x06010233: '楽曲',
    0x05750257: '楽曲',
    0x0d0b03ef: '楽曲',
    0x16530524: '楽曲',
    0x0cec03d6: '楽曲',
    0x42820847: '読み',
}
PLACEHOLDER = '〓'

# ================= 容器 =================
def parse_cdar(data, depth=0, out=None):
    if out is None:
        out = []
    if data[:4] != b'CDAR':
        return out
    ver, count, h = struct.unpack_from('<III', data, 4)
    base = 16 + count * 4
    for i in range(count):
        p = base + 12 * i
        if p + 12 > len(data):
            continue
        o, ds, sz = struct.unpack_from('<III', data, p)
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
        if d[:4] == b'CDAR' and depth < 4:
            parse_cdar(d, depth + 1, out)
        else:
            out.append((depth, i, d))
    return out


# ================= 文本记录 =================
_CTRL_OK = {0x09, 0x0a, 0x1b}


def decode_rec(body):
    out = []
    i, n = 0, len(body)
    while i < n:
        c = body[i]
        if c == 0x1b:          # 行内样式槽
            i += 2
            continue
        if c < 0x20:
            out.append(chr(c)); i += 1; continue
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            out.append(body[i:i + 2].decode('cp932', 'replace')); i += 2
        else:
            out.append(chr(c)); i += 1
    return ''.join(out)


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


def find_records(b):
    out = []
    i, n = 0, len(b)
    while True:
        i = b.find(b'\x04', i)
        if i < 0 or i >= n - 3:
            break
        r = valid_record(b, i)
        if r:
            out.append(r); i = r[1]
        else:
            i += 1
    return out


# ================= 插入块 =================
def parse_block(gap, start):
    """从 INS 之后解析指令序列, 返回 (operands, next_pos)"""
    p = start
    vals = []
    while p + 5 <= len(gap):
        op = gap[p]
        if op == 0x07:
            p += 3; continue
        if op == 0x1e:
            v = struct.unpack_from('<I', gap, p + 1)[0]
            p += 5
            if v == TERM1:
                break
            vals.append(v)
            if v == TERM2:
                break
            continue
        if op == 0x02:
            v = struct.unpack_from('<I', gap, p + 1)[0]
            p += 5
            vals.append(v)
            continue
        if op <= 0x0f:            # 单字节操作码
            p += 1
            continue
        break
    return vals, p


def ins_values(gap):
    """每个 1ecf021e0a 块 -> 一个插入字符串"""
    res, unres = [], []
    pos = 0
    while True:
        k = gap.find(INS, pos)
        if k < 0:
            break
        vals, p = parse_block(gap, k + len(INS))
        # 只保留像变量 ID 的值(排除小整数/常量)
        cand = [v for v in vals if v > 0xffff and v != TERM1 and v != TERM2]
        name = None
        for v in cand:
            if v in NAME_MAP:
                name = NAME_MAP[v]; break
        if name:
            res.append(name)
        else:
            sem = None
            for v in cand:
                if v in SEM_MAP:
                    sem = SEM_MAP[v]; break
            if sem:
                res.append('〔' + sem + '〕')
                unres.extend([v for v in cand if v not in SEM_MAP])
            else:
                if cand or vals:
                    res.append(PLACEHOLDER)
                unres.extend(cand)
        pos = p if p > k else k + 1
    return res, unres


# ================= 辞典 =================
RE_GLOSS = re.compile(r'^(?:「)?([^「」\n（]{1,20})(?:」)?\n（([^）]{1,40})）\n?(.*)$', re.DOTALL)


def gloss_form(t):
    m = RE_GLOSS.match(t)
    if m:
        return '【' + m.group(1) + '】' + m.group(3)
    return None


# ================= 清洗/过滤 =================
def clean(s):
    s = re.sub(r'[\u3000]*\n[\u3000]*', '', s)
    s = s.replace('\t', '').replace('\n', '')
    return s


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
    re.compile(r'^.+との(あいさつ|朝遭遇|再遭遇|夕遭遇|遭遇|恋愛失敗|友情失敗|恋愛成功|友情成功|出会い|会話|再会|デート)$'),
    re.compile(r'.+恋愛段階更新$'),
    re.compile(r'.+恋愛段階が増加→$'),
    re.compile(r'.+親密度が増加→$'),
    re.compile(r'.+恋愛失敗$'),
    re.compile(r'.+恋愛進行度[０-９0-9１-９]$'),
    re.compile(r'^.+との恋愛[がは]$'),
    re.compile(r'^.+珠玉ルート$'),
    re.compile(r'^.+逆注目ルート$'),
    re.compile(r'^(珠玉|逆注目)ルート$'),
    re.compile(r'^恋愛進行度$'),
    re.compile(r'^エリア有効フラグ'),
    re.compile(r'^現在の章は[?？]$'),
    re.compile(r'^ダミー条件$'),
    re.compile(r'^発生不可$'),
    re.compile(r'^(ＯＮ|ＯＦＦ)$'),
    re.compile(r'^ファイナル[０-９0-9１-９]+$'),
    re.compile(r'^[^\n]{1,8}(恋愛|珠玉|逆注目|友情)$'),
    re.compile(r'^[^\n]{1,14}[・](恋愛|珠玉|逆注目|友情)$'),
    re.compile(r'^ミニスチル・'),
    re.compile(r'章内[０-９0-9１-９]'),
    re.compile(r'章末[０-９0-9１-９]'),
    re.compile(r'イベント・'),
    re.compile(r'^オーナー移譲$'),
    re.compile(r'にセット$'),
    re.compile(r'フラグ$'),
    re.compile(r'をセット$'),
    re.compile(r'が呼ばれています$'),
    re.compile(r'ミニキャラ'),
    re.compile(r'^.+の(親密度|評価|恋愛段階)が(増加|減少)'),   # 开发日志(末尾接 〓→〓, 原 $ 锚点漏掉)
    re.compile(r'^[？?]+[^　]'),        # 开发用「？？」占位串(真对白 '？　…' 不受影响)
    re.compile(r'^[!！]+[^　]'),
]

# ---- 开发用「判定」菜单（每个事件脚本开头的调试块）----
DEBUG_Q = re.compile(
    r'^('
    r'主人公と.+は別フィールド？'
    r'|.+との恋愛進行度は？'
    r'|.+恋愛進行度.+？'
    r'|.+恋愛レベルは？|.+恋愛進行中？'
    r'|.+の(珠玉|逆注目)ルートは進行している？'
    r'|.+ルートは進行している？'
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
    r'|.+との恋愛(は|が)(進んでいる|進行している)？'
    r'|.+恋愛.{0,3}(進んでいる|進行している)？'
    r'|.+珠玉(イベント|恋愛)は進行している？'
    r'|.+との恋愛は[？…]'
    r'|.+の(珠玉|逆注目)ルートは進んでいる？'
    r'|.+珠玉ルートは進んでいる？|.+逆注目ルートは進んでいる？'
    r'|.+の恋愛進行度は…'
    r'|２人練習誘いメールきた？'
    r'|すでに練習済み？'
    r'|.+は参加している？|.+は参加してない'
    r'|.+と.+は出現可？|.+は出現可？|.+は出現中？|.+は別フィールド？'
    r'|完成度高かった|完成度高くなかった'
    r')$')

DEBUG_OPT = re.compile(
    r'^('
    r'別フィールド|同じフィールド|きた|きていない|済み|まだ'
    r'|出現可|出現不可|出現中|発生させる|発生させない'
    r'|整って(い)?る|整ってない'
    r'|完成度高かった|完成度高くなかった|進行している|進行していない'
    r'|進んでいる|進んでいない'
    r'|.+と進んでいる|.+と進んでいない|誰とも進んでいない|[０-９0-9１-９]まで進んでいる'
    r'|恋愛[０-９0-9１-９](以下)?|恋愛レベル[０-９0-9１-９]'
    r'|失敗or０|[０-９0-9１-９]+～[０-９0-9１-９]+'
    r'|.+恋愛進行度[０-９0-9]|.+恋愛段階[０-９0-9]|.+恋愛レベル[０-９0-9]'
    r'|.+進行中|.+進行して(い)?ない|.+は不在|.+感動して(い)?ない|.+感動した'
    r'|.+ＭＦ未使用|.+ＭＦ使用済み|.+通常'
    r'|[０-９0-9１-９]+曲目.*'
    r')$')


def drop_debug_blocks(msgs):
    out = []
    i = 0
    while i < len(msgs):
        if DEBUG_Q.match(msgs[i].strip()):
            i += 1
            while i < len(msgs) and DEBUG_OPT.match(msgs[i].strip()):
                i += 1
            continue
        out.append(msgs[i])
        i += 1
    return out


def is_noise(t):
    if t.startswith('＜デバッグ時のみ表示＞'):
        return True
    if '場合別実行エラー' in t:
        return True
    if '正式版では表示されません' in t:
        return True
    if 'デバッグ' in t:
        return True
    return any(r.search(t) for r in RE_NOISE)


def is_texty(t):
    if len(t) < 2:
        return False
    good = sum(1 for ch in t if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff')
               or ('\u3000' <= ch <= '\u303f') or ('\uff01' <= ch <= '\uff60')
               or ch in '─―…‥→♥♪〔〕')
    bad = sum(1 for ch in t if (0xE000 <= ord(ch) <= 0xF8FF) or (0xFF61 <= ord(ch) <= 0xFF9F)
              or ord(ch) < 0x20)
    return good >= 2 and bad <= max(1, good * 0.34)


# ================= 主流程 =================
def process(b):
    recs = find_records(b)
    if not recs:
        return [], [], 0
    n_gloss = sum(1 for _, _, t in recs if RE_GLOSS.match(t))
    msgs, cur, unres = [], [], []
    for i, (s, e, t) in enumerate(recs):
        gap = b[recs[i - 1][1]:s] if i > 0 else b[:s]
        sep = (BOUND in gap) or (M91 in gap) or (C7 in gap) or (CLOSE + C7 in gap)
        if not sep and i > 0:
            prev_end = recs[i - 1][1]
            if not gap.startswith(CLOSE) and b[prev_end:prev_end + 5] != CLOSE:
                sep = True
        if sep and cur:
            msgs.append(''.join(cur)); cur = []
        ins, u = ins_values(gap)
        unres += u
        cur.extend(ins)
        cur.append(t)
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        tail = b[e:nxt]
        # 记录后紧跟 CLOSE 或 INS 都算「同一框」→ 不换行
        if not (tail.startswith(CLOSE) or tail.startswith(INS)):
            msgs.append(''.join(cur)); cur = []
    if cur:
        msgs.append(''.join(cur))
    return msgs, unres, n_gloss


def main():
    out_path, gloss_path = sys.argv[1], sys.argv[2]
    inputs = sys.argv[3:]
    main_lines, gloss_lines = [], []
    stats = collections.Counter()
    samples = collections.defaultdict(list)
    all_unres = collections.Counter()
    drop_log = []
    seen = set()
    seen_gloss = set()
    for path in inputs:
        d = open(path, 'rb').read()
        for depth, idx, b in parse_cdar(d):
            if len(b) < 8 or len(b) > 0x4000000:
                continue
            h = hashlib.md5(b).digest()
            if h in seen:
                stats['dedup'] += 1
                continue
            seen.add(h)
            msgs, unres, n_gloss = process(b)
            if not msgs:
                continue
            stats['entries'] += 1
            msgs = drop_debug_blocks(msgs)
            kept = []
            for m in msgs:
                g = gloss_form(m)
                if g:
                    g = clean(g)
                    if g and is_texty(g) and g not in seen_gloss:
                        seen_gloss.add(g)
                        gloss_lines.append(g)
                    continue
                m2 = clean(m)
                if not m2:
                    continue
                if not is_texty(m2):
                    stats['drop_binary'] += 1
                    if len(samples['drop_binary']) < 15:
                        samples['drop_binary'].append((path, m2[:60]))
                    continue
                if is_noise(m2):
                    stats['drop_noise'] += 1
                    drop_log.append(m2)
                    if len(samples['drop_noise']) < 15:
                        samples['drop_noise'].append((path, m2[:60]))
                    continue
                kept.append(m2)
            for v in unres:
                all_unres[v] += 1
            main_lines.extend(kept)
    with open(out_path + '.noise', 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(drop_log) + '\n')
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(main_lines) + '\n')
    with open(gloss_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(gloss_lines) + '\n')
    print(f'main_lines={len(main_lines)}  glossary_lines={len(gloss_lines)}')
    print('stats:', dict(stats))
    for k in ('drop_binary', 'drop_noise'):
        print(f'-- {k} samples --')
        for p, t in samples[k][:6]:
            print(f'   {p}: {t!r}')
    print('== 未解析插入值 (top 30) ==')
    for v, n in all_unres.most_common(30):
        print(f'  0x{v:08x} x{n}')


if __name__ == '__main__':
    main()
