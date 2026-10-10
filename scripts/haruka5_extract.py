# -*- coding: utf-8 -*-
"""遙かなる時空の中で5 (PSP / ULJM-05821, Koei / Ruby Party) 全文本提取器

容器链路
--------
[PSP-JP]遙かなる時空の中で5.iso
  └ PSP_GAME/USRDIR/DATA.BIN  = **Koei CDAR v4**
       header : "CDAR" + u32 ver(4) + u32 count
       表     : 16 字节头 + count×u32 数组之后, count × 12 字节 {off, ds, size}
                ds = 解压后长度, size = 磁盘长度; 首字节 0x78 → zlib
       子条目可为嵌套 CDAR(zlib 或明文) → 递归 (深度 3) + md5 去重

脚本 VM (与 コルダ オクターヴ / 下天の華 / 遥か6 DX 同族)
--------------------------------------------------------
指令 = <u8 opcode><u32 operand> (定长 5B)，文本 = [04][u16 len][cp932][00]
消息(一次点击)边界: gap 内出现
    1e 2224058b (BOUND) / 1e 744709c7 (C7) / 1e a0bd0b91 (M91)  → 断开新框
    上一条记录之后若不紧跟 1e 4c8707f9 (CLOSE)                  → 上一条独立成行

内联插入(本作关键，两套表)
    op1  1e 05290204  前置 02 <id>  → **脚本用语表**(52B 定长记录)
    op2  1e 05b2027e  前置 02 <id>  → **用語辞典表**(64B 定长记录)
    INS  1e 0a021ecf (=字节 1e cf 02 1e 0a) 后跟 02/1e 指令链 → 主人公名等
两套表都在 **同一个「母表」leaf**(size 167270, 内含 章题/地图名/角色表/年表) 内:
    52B 脚本用语表 base = 0x1c9e6, 记录 = [名 19B][読み 33B]      (0..499, 空槽='仮')
    64B 用語辞典表 base = 0x149e0, 记录 = [flag 1B][見出し語 19B][読み 32B][半角カナ]
                                        (0..367, 空槽为 '用語予約NNN')

用語辞典解説文 = 单 04 记录 + 末尾 `CLOSE+C7+1e 5e9008d3` 的 leaf (311 条)
系统/UI 文本  = 末尾 `CLOSE+M91+1e 5e9008d3` 的 leaf (231 个，整体排除)

用法:
    python haruka5_extract.py DATA.BIN OUT.txt
"""
import sys, os, struct, zlib, hashlib, re, collections

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
C7 = b'\x1e\xc7\x09\x47\x74'
M91 = b'\x1e\x91\x0b\xbd\xa0'
TERMOP = b'\x1e\x04\x02\x29\x05'     # op1
GLOSSOP = b'\x1e\x7e\x02\xb2\x05'    # op2
INS = b'\x1e\xcf\x02\x1e\x0a'
TAIL_DEF = bytes.fromhex('1ef907874c1ec70947741ed308905e')
TAIL_SYS = bytes.fromhex('1ef907874c1e910bbda01ed308905e')
TABLE_LEAF_MIN = 0x1c9f0
TBL52_BASE, TBL52_SIZE = 0x1c9e6, 52
TBL64_BASE, TBL64_SIZE = 0x149e0, 64

NAME_FAMILY, NAME_GIVEN = '蓮水', 'ゆき'
NAME_FULL = '蓮水ゆき'
VAR_TEXT = {0x329007e7: NAME_GIVEN, 0x01ea0153: NAME_GIVEN, 0x05fa0288: NAME_GIVEN,
            0x01cb013a: NAME_FAMILY, 0x1d76056e: NAME_FAMILY, 0x2a0d06bc: NAME_GIVEN,
            0x2350067d: NAME_FULL, 0x1d950587: NAME_FULL, 0x0b49032e: NAME_FULL,
            0x42820847: NAME_FULL}
INS_CONSTS = {0x15500462, 0x1af9056c, 0x0d6503f2, 0x13d404bc, 0x019200ff, 0x1f470562,
              0x00000002}
PLACEHOLDER = '〔未解析〕'


# ---------------- 容器 ----------------
def load_leaves(datapath, maxdepth=3):
    d = open(datapath, 'rb').read()
    cnt = struct.unpack_from('<I', d, 8)[0]
    b2 = 16 + cnt * 4
    ents = [struct.unpack_from('<III', d, b2 + 12 * i) for i in range(cnt)]
    leaves, seen = [], set()

    def maybe_z(u):
        if len(u) > 1 and u[0] == 0x78:
            try:
                return zlib.decompress(u)
            except Exception:
                return u
        return u

    def parse_cdar(u):
        if len(u) < 16 or u[:4] != b'CDAR':
            return None
        c = struct.unpack_from('<I', u, 8)[0]
        bb = 16 + c * 4
        if c == 0 or bb + 12 * c > len(u):
            return None
        return [struct.unpack_from('<III', u, bb + 12 * k) for k in range(c)]

    def walk(u, path, depth):
        u = maybe_z(u)
        e = parse_cdar(u)
        if e is not None and depth < maxdepth:
            for k, (o, ds, s) in enumerate(e):
                if s > 0 and o + s <= len(u):
                    walk(u[o:o + s], path + '/' + str(k), depth + 1)
            return
        h = hashlib.md5(u).hexdigest()
        if h in seen:
            return
        seen.add(h)
        leaves.append((path, u))

    for i, (o, ds, s) in enumerate(ents):
        walk(d[o:o + s], str(i), 0)
    return leaves


# ---------------- 记录扫描 ----------------
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
        return (i, e, body.decode('cp932'))
    except Exception:
        return None


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


def clean(s):
    s = re.sub(r'[\u3000]*\n[\u3000]*', '', s)
    return s.replace('\n', '')


# ---------------- 两张内联表 ----------------
def load_tables(leaves):
    TL = None
    for p, b in leaves:
        if len(b) > TABLE_LEAF_MIN and b[TBL52_BASE:TBL52_BASE + 6] == b'\x8c\xe4\x8e\x67\x82\xa2':
            TL = b
            break
    assert TL is not None, 'table leaf not found'
    TERM = {}
    for k in range(0, 600):
        o = TBL52_BASE + TBL52_SIZE * k
        if o + TBL52_SIZE > len(TL):
            break
        hw = TL[o:o + 0x13].split(b'\x00')[0]
        if not hw:
            break
        try:
            s = hw.decode('cp932')
        except Exception:
            break
        if s != '仮':
            TERM[k] = s
    GLOSS = {}
    for k in range(0, 400):
        o = TBL64_BASE + TBL64_SIZE * k
        if o + TBL64_SIZE > len(TL):
            break
        hw = TL[o + 6:o + 25].split(b'\x00')[0]
        if not hw:
            continue
        try:
            s = hw.decode('cp932')
        except Exception:
            continue
        if s.startswith('用語予約'):
            continue
        try:
            r = TL[o + 25:o + 57].split(b'\x00')[0].decode('cp932').strip()
        except Exception:
            r = ''
        GLOSS[k] = (s, r)
    return TERM, GLOSS


def collect(gap, TERM, GLOSS):
    items = []
    for pat, tbl, use in ((TERMOP, TERM, 't'), (GLOSSOP, GLOSS, 'g')):
        pos = 0
        while True:
            k = gap.find(pat, pos)
            if k < 0:
                break
            if k >= 5 and gap[k - 5] == 0x02:
                tid = struct.unpack_from('<I', gap, k - 4)[0]
                v = tbl.get(tid) if use == 't' else (tbl[tid][0] if tid in tbl else None)
                items.append((k, v if v else PLACEHOLDER))
            pos = k + len(pat)
    pos = 0
    while True:
        k = gap.find(INS, pos)
        if k < 0:
            break
        p = k + len(INS)
        s, got, args = '', False, False
        while p + 5 <= len(gap) and gap[p] in (0x02, 0x1e):
            op = gap[p]
            v = struct.unpack_from('<I', gap, p + 1)[0]
            if v in VAR_TEXT:
                s += VAR_TEXT[v]
                got = True
            elif op == 0x02 and v not in INS_CONSTS:
                args = True
            p += 5
        if args and not got:
            s = PLACEHOLDER
        items.append((k, s))
        pos = p if p > k else k + 1
    items.sort()
    return [v for _, v in items]


def process(b, TERM, GLOSS, with_flag=False):
    recs = find_records(b)
    if not recs:
        return []
    msgs, cur, flags = [], [], []
    cur_flag = False

    def flush():
        msgs.append(''.join(cur))
        flags.append(cur_flag)

    for i, (s, e, t) in enumerate(recs):
        gap = b[(recs[i - 1][1] if i > 0 else 0):s]
        sep = (BOUND in gap) or (C7 in gap) or (M91 in gap)
        if i > 0 and not gap.startswith(CLOSE):
            sep = True
        if sep and cur:
            flush()
            cur, cur_flag = [], False
        ins = collect(gap, TERM, GLOSS)
        if ins:
            cur.extend(ins)
            cur_flag = True
        cur.append(t)
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        if not b[e:nxt].startswith(CLOSE):
            flush()
            cur, cur_flag = [], False
    if cur:
        flush()
    out = []
    for m, f in zip(msgs, flags):
        m = clean(m)
        if m:
            out.append((m, bool(f)) if with_flag else m)
    return out


# ---------------- 过滤 ----------------
RE_HELP_LINE = re.compile(
    r'([0-9０-９]/[0-9０-９]\s*$)'
    r'|(ボタン|→［|メニュー|コマンド|操作方法|禁呪状態|ポイント調査時|デバッグ用|画像のような|'
    r'消費集中力|設定をします|情報を見ます|を見ます|を使います|を入れ替えます|を変更します|'
    r'表示します|豆辞典|ヘルプ|パスワード|携帯サイト|音量|台詞表示|サウンド|'
    r'データのセーブ|データをロード|最初からプレイ|メモリースティック|インストール|'
    r'この章のあらすじ|現在プレイ中の章|※章開始後|気力と集中力の回復|どのイベントを見ますか)')
RE_TITLE_HELP = re.compile(r'(について|の結果|の表示|の選択|一覧|設定|概要|説明)$')
SYS_KW = ['メモリースティック', 'インストール', 'サスペンド', 'スリープ', '電源を切',
          'セーブできません', 'ロードできません', 'よろしいですか', '中止しますか',
          '初期状態', '環境設定', 'タイトル画面', 'スキップ', 'オート切替', 'キャンセル',
          '前ページ', '次ページ', '人物詳細', '特殊行動', 'クイックセーブ', 'クイックロード',
          'メッセージ履歴', 'オート切替え', '入力完了', 'デバッグ', '禁呪状態',
          'ポイント調査時', '画像のような', '※章開始後', '現在プレイ中の章']
RE_DROP = [
    re.compile(r'^イベント・'),
    re.compile(r'^(何周目？|どちらルート？|どのルート？|見るのは――|何章？)$'),
    re.compile(r'^[0-9０-９]+周目'),
    re.compile(r'^(してる|してない|発生済み|未発生|済み|した|あります|ありません)$'),
    re.compile(r'(済みであるか？|成功してる？|成功した？|発生した？)$'),
    re.compile(r'との絆'),
    re.compile(r'^[①-⑰]'),
    re.compile(r'^(壁紙|写真データ|画像集|楽曲集|回想録|配信イベント|ロードが終了|'
               r'データを作成|コメント入力|主人公名|誕生日|封印の結果|特殊なボス|'
               r'戦闘の結果|技と五行属性|能力について|武器変化|連鎖術|仲間の行動|'
               r'敵の強さ|戦闘の強さ|システムデータ|神子との絆|絆の上げ方|'
               r'設定をします|情報を見ます|音量|台詞表示)'),
    re.compile(r'^(団結|離脱|加入)$'),
    re.compile(r'(この章のあらすじは表示できません)'),
    re.compile(r'^「」表示'),
    re.compile(r'^・'),
    re.compile(r'^(能力|技|特殊行動|連鎖術|奥義|アイテム)(の)?(強化|使用|一覧|説明)$'),
    re.compile(r'(耐性を持つ|戦闘能力上昇|を習得|再生されます|含まれます|状態になる)$'),
]


def leaf_is_help(ms):
    for m in ms:
        if RE_HELP_LINE.search(m):
            return True
    if len(ms) <= 12 and ms and RE_TITLE_HELP.search(ms[0]):
        return True
    return False


def is_drop(m):
    if len(m) <= 3 and not re.search(r'[「『]', m):
        return True
    if any(r.search(m) for r in RE_DROP):
        return True
    return any(k in m for k in SYS_KW)


def norm_paren(t):
    """原文数据里与全角（ 错配对的半角 ')'（游戏脚本自身笔误）统一成全角。"""
    if '（' in t and '）' not in t and ')' in t:
        t = t.replace(')', '）')
    return t


def jp_ratio(t):
    if not t:
        return 0.0
    jp = sum(1 for ch in t
             if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff')
             or ('\u3000' <= ch <= '\u303f') or ('\uff01' <= ch <= '\uff60')
             or ch in '─―…‥')
    return jp / len(t)


def extract(datapath):
    leaves = load_leaves(datapath)
    TERM, GLOSS = load_tables(leaves)
    story, defs, diag = [], [], collections.Counter()
    for p, b in leaves:
        if len(b) < 8 or len(b) > 0x2000000:
            continue
        if b[:3] == b'GXT' or b[:4] == b'TIM2':
            continue
        recs = find_records(b)
        if not recs:
            continue
        if b.endswith(TAIL_DEF):                       # 用語辞典 解説文
            t = clean(recs[0][2])
            if (t and len(t) > 4 and not re.match(r'^【[^】]{1,8}】', t)
                    and t.count('「') == t.count('」')
                    and not re.search(r'(モバイルジョイ|メモリースティック|インストール)', t)):
                defs.append(t)
            continue
        if TAIL_SYS in b[-48:]:                        # 系统/UI leaf
            diag['sys_leaf'] += 1
            continue
        ms = process(b, TERM, GLOSS, with_flag=True)
        if not ms:
            continue
        if leaf_is_help([m for m, _ in ms]):
            diag['help_leaf'] += 1
            continue
        kept, prev = [], None
        for m, flag in ms:
            if not m:
                continue
            if is_drop(m):
                diag['drop'] += 1
                continue
            if jp_ratio(m) < 0.30 and not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', m):
                diag['drop_jp'] += 1
                continue
            if flag and m == prev:
                diag['drop_dup_variant'] += 1
                continue
            m = norm_paren(m)
            kept.append(m)
            prev = m
        if ms and len(ms) <= 40 and len(kept) < len(ms) * 0.5:
            diag['drop_leaf_half'] += 1
            continue
        story.extend(kept)
    # 一封信跨两个文本框 → 合并
    out, i = [], 0
    while i < len(story):
        if (story[i].count('「') > story[i].count('」') and i + 1 < len(story)
                and story[i + 1].count('」') > story[i + 1].count('「')):
            out.append(story[i] + story[i + 1])
            i += 2
        else:
            out.append(story[i])
            i += 1
    story = out
    # 分支重复载体去重（文本完全一致）
    dedup = []
    for m in story:
        if dedup and dedup[-1] == m:
            diag['drop_adj_dup'] += 1
            continue
        dedup.append(m)
    story = dedup
    heads = [GLOSS[k][0] for k in sorted(GLOSS)]
    return story, heads, defs, diag


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    data, out_path = sys.argv[1], sys.argv[2]
    story, heads, defs, diag = extract(data)
    lines = list(story)
    lines.append('■用語辞典（見出し語／用語ＩＤ順）')
    lines.extend(heads)
    lines.append('■用語辞典（解説文／見出し語との対応表はデータ内に存在しないため順不同）')
    lines.extend(defs)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('lines=%d story=%d heads=%d defs=%d' % (len(lines), len(story), len(heads), len(defs)))
    print('diag', dict(diag))


if __name__ == '__main__':
    main()
