# -*- coding: utf-8 -*-
"""遙かなる時空の中で5 風花記 (PSP / ULJM-05950, Koei / Ruby Party) 全文本提取器

容器链路
--------
[PSP-JP]遙かなる時空の中で5 風花記.zip
  └ Harukanaru Toki no Naka de 5 Kazahanaki (Japan) (v1.01).iso
       └ PSP_GAME/USRDIR/DATA.BIN  = **Koei CDAR v4** (166,999,893 B, count=6514)
            header : "CDAR" + u32 ver(4) + u32 count
            表     : 16 字节头 + count×u32 之后, count × 12 字节 {off, ds, size}
            子条目可为嵌套 CDAR(zlib 或明文) → 递归 (深度 3) + md5 去重

脚本 VM (与 遥か5 本体 / コルダ オクターヴ / 下天の華 / 遥か6 DX 同族)
--------------------------------------------------------
指令 = <u8 opcode><u32 operand> (定长 5B)，文本 = [04][u16 len][cp932][00]
消息(一次点击)边界: gap 内出现
    1e 8b 05 24 22 (BOUND) / 1e c7 09 47 74 (C7) / 1e 91 0b bd a0 (M91)  → 断开新框
    上一条记录之后若不紧跟 1e f9 07 87 4c (CLOSE)                        → 上一条独立成行

★ 与本体最大的差异：**内联插入**
  遥か5 本体：正文插入走「两张定长表(52B/64B) + 02<id> + 1e 05290204/1e 05b2027e」。
  風花記  ：**无定长表插值**(TERMOP/GLOSSOP 计数 = 0)。插入词以**内联文本记录**给出：
      02 <u32 id>  1e 4e 04 3a 14  04 <u16 len> <語> 00      (APP1, 7,028 处)
      ...          1e a6 04 a8 14  04 <u16 len> <続き> 00    (APP2, 7,028 处)
  即「用語も続きも普通の 04 文本记录」⇒ 记录扫描 + 合并即可，无需查表。

主人公名变量 (INS = 1e cf 02 1e 0a)
    1e e7 07 90 32 (0x329007e7) / 02 53 01 ea 01 (0x01ea0153) → ゆき
    02 3a 01 cb 01 (0x01cb013a) → 蓮水
    0x0b49032e → 蓮水ゆき   (与本体同一套变量 ID 布局)

用語辞典
    見出し語 : 「母表」leaf (174,924 B) 内 stride 64B 定长表
               base 0x167c0, 记录 = [12B][見出し語 19B][読み 33B], id 0..511
               首条 = 桐生 瞬; id 0..23 为人物名, 其余为用語/英語表現
    解説文   : 末尾签名 `CLOSE + C7 + 1e 5e9008d3` 的 leaf (482 个, 469 个单记录)
    系统/UI  : 末尾签名含 `1e 5e9008d3` 的其他 leaf (整体排除)

用法:
    python kazahanaki_extract.py DATA.BIN OUT.txt
    python kazahanaki_extract.py DATA.BIN --sample 40
"""
import sys, os, struct, zlib, hashlib, re, collections

BOUND = bytes.fromhex('1e8b052422')
CLOSE = bytes.fromhex('1ef907874c')
C7 = bytes.fromhex('1ec7094774')
M91 = bytes.fromhex('1e910bbda0')
INS = bytes.fromhex('1ecf021e0a')
APP1 = bytes.fromhex('1e4e043a14')
APP2 = bytes.fromhex('1ea604a814')
TAIL_DEF = bytes.fromhex('1ef907874c1ec70947741ed308905e')
TRAILER = bytes.fromhex('1ed308905e')

NAME_FAMILY, NAME_GIVEN = '蓮水', 'ゆき'
NAME_FULL = '蓮水ゆき'
VAR_TEXT = {0x329007e7: NAME_GIVEN, 0x01ea0153: NAME_GIVEN, 0x05fa0288: NAME_GIVEN,
            0x01cb013a: NAME_FAMILY, 0x1d76056e: NAME_FAMILY, 0x2a0d06bc: NAME_GIVEN,
            0x2350067d: NAME_FULL, 0x1d950587: NAME_FULL, 0x0b49032e: NAME_FULL,
            0x42820847: NAME_FULL}
INS_CONSTS = {0x15500462, 0x1af9056c, 0x0d6503f2, 0x13d404bc, 0x019200ff, 0x1f470562,
              0x00000002, 0x01870af5}
PLACEHOLDER = '〔未解析〕'

GLOSS_BASE_MARK = '桐生 瞬'          # 見出し語表 首条
GLOSS_HW_OFF, GLOSS_RD_OFF, GLOSS_ST = 0x0C, 0x1F, 64
GLOSS_N = 512


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


# ---------------- 内联插入收集（仅主人公名） ----------------
def collect(gap):
    items = []
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


def process(b, override=None):
    """override: {記録索引: 差し替え本文} —— overlay leaf による冒頭修正用。"""
    recs = find_records(b)
    if not recs:
        return []
    msgs, cur = [], []

    def flush():
        msgs.append(cur)

    for i, (s, e, t) in enumerate(recs):
        if override and i in override:
            t = override[i]
        gap = b[(recs[i - 1][1] if i > 0 else 0):s]
        sep = (BOUND in gap) or (C7 in gap) or (M91 in gap)
        if i > 0 and not gap.startswith(CLOSE):
            sep = True
        if sep and cur:
            flush()
            cur = []
        ins = collect(gap)
        if ins:
            cur.extend(ins)
        cur.append(t)
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        if not b[e:nxt].startswith(CLOSE):
            flush()
            cur = []
    if cur:
        flush()
    return [clean(''.join(m)) for m in msgs]


# ---------------- 見出し語表 ----------------
def load_glossary(leaves):
    TL = None
    MK = GLOSS_BASE_MARK.encode('cp932')
    NX = '坂本龍馬'.encode('cp932')
    for p, b in leaves:
        if len(b) < 150000:
            continue
        pos = 0
        while True:
            off = b.find(MK, pos)
            if off < 0:
                break
            pos = off + 1
            if off < GLOSS_HW_OFF:
                continue
            if b[off + GLOSS_ST:off + GLOSS_ST + 16].split(b'\x00')[0] == NX:
                TL = (p, b, off - GLOSS_HW_OFF)
                break
        if TL:
            break
    assert TL is not None, 'glossary table leaf not found'
    p, b, base = TL

    def fld(off, n):
        s = b[off:off + n].split(b'\x00')[0]
        if not s:
            return ''
        try:
            return s.decode('cp932')
        except Exception:
            return ''

    heads = []
    for k in range(GLOSS_N):
        off = base + GLOSS_ST * k
        if off + GLOSS_ST > len(b):
            break
        hw = fld(off + GLOSS_HW_OFF, 19)
        if hw and '作成中' not in hw and hw != '仮':
            heads.append(hw)
    return heads, (p, base)


# ---------------- overlay（冒頭修正版 leaf）検出 ----------------
def build_overlays(leaves):
    """同一タイトル・同一冒頭構造で一部の行だけ異なる小さな leaf（修正/上書き版）を検出。

    風花記の実例: leaf 18『目覚め』(126 記録・本編) に対し lei 4999 が同タイトル・
    冒頭 6 記録が逐条対応（5/6 同一・1 条だけ改稿）＋ 末尾に入口ラベル
    「イベント・共通序章頭 / 共通序章内１００」を宣言 ⇒ 後者が前者の冒頭を上書きする。
    戻り値: (skip_paths, override_map)   override_map[target] = {record_index: text}
    """
    story = []
    for p, b in leaves:
        if len(b) < 8 or len(b) > 0x2000000:
            continue
        if b[:3] == b'GXT' or b[:4] == b'TIM2' or b[:4] == b'KSEF':
            continue
        recs = find_records(b)
        if not recs:
            continue
        if b.endswith(TAIL_DEF) or TRAILER in b[-8:]:
            continue
        story.append((p, b, recs))
    by_title = collections.defaultdict(list)
    for p, b, recs in story:
        t = clean(recs[0][2])
        if t and not t.startswith('イベント'):
            by_title[t].append((p, b, recs))
    skip, over = set(), {}
    for t, lst in by_title.items():
        for xp, xb, xr in lst:
            for yp, yb, yr in lst:
                if xp == yp or len(xr) >= len(yr):
                    continue
                n = len(xr)
                while n > 0 and (clean(xr[n - 1][2]).startswith('イベント・')
                                 or not clean(xr[n - 1][2])):
                    n -= 1
                if n < 4 or len(yr) < n:
                    continue
                x = [clean(xr[k][2]) for k in range(n)]
                y = [clean(yr[k][2]) for k in range(n)]
                if any(not s for s in x):
                    continue
                eq = sum(1 for k in range(n) if x[k] == y[k])
                if n - 2 <= eq < n:
                    skip.add(xp)
                    over.setdefault(yp, {}).update({k: x[k] for k in range(n)})
    return skip, over


# ---------------- 过滤 ----------------
RE_DROP = [
    re.compile(r'^イベント・'),
    re.compile(r'^イベント'),
    re.compile(r'^(何周目？|どちらルート？|どのルート？|どちらのバージョン？|何章？|見るのは――？)$'),
    re.compile(r'^[0-9０-９]+周目'),
    re.compile(r'^(してる|してない|発生済み|未発生|済み|した|あります|ありません)$'),
    re.compile(r'(済みであるか？|成功してる？|成功した？|発生した？)$'),
    re.compile(r'との絆'),
    re.compile(r'^[①-⑰]'),
    re.compile(r'^(壁紙|写真データ|画像集|楽曲集|回想録|配信イベント|ロードが終了|'
               r'データを作成|コメント入力|主人公名|誕生日|封印の結果|特殊なボス|'
               r'戦闘の結果|技と五行属性|能力について|武器変化|連鎖術|仲間の行動|'
               r'敵の強さ|戦闘の強さ|システムデータ|神子との絆|絆の上げ方|'
               r'設定をします|情報を見ます|音量|台詞表示|空ファイル)'),
    re.compile(r'^(団結|離脱|加入)$'),
    re.compile(r'(この章のあらすじは表示できません)'),
    re.compile(r'^「」表示'),
    re.compile(r'^・'),
    re.compile(r'^(能力|技|特殊行動|連鎖術|奥義|アイテム)(の)?(強化|使用|一覧|説明)$'),
    re.compile(r'(耐性を持つ|戦闘能力上昇|を習得|再生されます|含まれます|状態になる)$'),
    # ---- 風花記 追加：デバッグ／分岐メニュー（選択肢表示 op 1e c6 02 87 06 / 1e 72 03 91 0b）----
    re.compile(r'^(どのイベントを見ますか？|何を見る？|誰かの武器に反応しているみたい…|'
               r'その他orなし|誰もなし|ノーマル|象山|章頭|章間|フィルター確認|'
               r'進んでない|すすんでない|会ってない|進んでる|進んだけど失敗しちゃった)$'),
    re.compile(r'(見ますか？$|になってる？$|の量は？$|の残数は？$|進んでる？$|会ってる？$)'),
    re.compile(r'(恋愛は[？…]?$|恋愛が進展していない場合$|との恋愛は…?$|くんとの恋愛は…?$)'),
    re.compile(r'^(現在章をセット|現在地をセット|現在の状況をセット|五行属性をセット|'
               r'フラグをセット|情報表示フラグをセット|名前知りフラグをセット|'
               r'加入時レベルをセット|所有技初期化|主人公の所有技初期化|'
               r'用語辞典可視化|ヘルプ可視化|汎用連鎖術解禁フラグON|データの初期化終了)$'),
    re.compile(r'(が発生しました。$|イベントが呼ばれました$)'),
    re.compile(r'^(失敗[０-９0-9]|総司五章に入ってる|.*を仲間が知らない)$'),
    re.compile(r'(場合$|とき$)'),
    re.compile(r'^[０-９0-9一二三四五六七八九十]+周目$'),
    re.compile(r'^(リンドウ|龍馬|桜智|高杉|総司|チナミ|小松|天海|アーネスト|帯刀|瞬|祟|都)'
               r'(さん|くん|殿)?(の…|さんに聞きたいこと…|との恋愛は…?|さんとの恋愛は)?$'),
    re.compile(r'^[^\n]{1,6}(さん|くん)、[^\n]{1,6}(さん|くん)?から$'),
    re.compile(r'^(チナミくんか総司さん…？|小松さんか桜智さん…？|アーネストか高杉さん…？|'
               r'小松さんとアーネストに会ってる？|小松とアーネストに会っていない場合)$'),
    re.compile(r'^(命のかけら|時空の砂時計|睡蓮の花|燭龍|名前知り)'),
    re.compile(r'([0-9０-９]/[0-9０-９]\s*$)'),
    re.compile(r'^.{1,10}(離脱|が仲間に加わった|が解禁|を習得した)$'),
    re.compile(r'(武器レベル|行動を選ぶ際|武器封印|レベル上昇時|属性アイコン|'
               r'回復します|上昇します|下降します|消費します|習得します)'),
]
SYS_KW = ['メモリースティック', 'インストール', 'サスペンド', 'スリープ', '電源を切',
          'セーブできません', 'ロードできません', 'よろしいですか', '中止しますか',
          '初期状態', '環境設定', 'タイトル画面', 'スキップ', 'オート切替', 'キャンセル',
          '前ページ', '次ページ', '人物詳細', '特殊行動', 'クイックセーブ', 'クイックロード',
          'メッセージ履歴', 'オート切替え', '入力完了', 'デバッグ', '禁呪状態',
          'ポイント調査時', '画像のような', '※章開始後', '現在プレイ中の章',
          'モバイルジョイ', '特典を獲得', 'アイテムを追加', '取得しています',
          'ターン味方', '消費集中力', '集中力', '復興ゲージ', '建物の崩壊', 'ボタン',
          '仲間に加わった', '仲間から離脱', '仲間になりました',
          '命のかけら', '連鎖術', '状態異常', '戦列の', '燭龍に挑める', '異世界で建物に憑いた',
          '移動画面で⑩', '章変更', 'ミニイベント', 'メニュー→', '用語辞典', 'ヘルプ']


def is_drop(m):
    if len(m) <= 1:
        return True
    if any(r.search(m) for r in RE_DROP):
        return True
    return any(k in m for k in SYS_KW)


def jp_ratio(t):
    if not t:
        return 0.0
    jp = sum(1 for ch in t
             if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff')
             or ('\u3000' <= ch <= '\u303f') or ('\uff01' <= ch <= '\uff60')
             or ch in '─―…‥')
    return jp / len(t)


def norm_paren(t):
    """原文数据里与全角（ 错配对的半角 ')'（游戏脚本自身笔误）统一成全角。"""
    if '（' in t and '）' not in t and ')' in t:
        t = t.replace(')', '）')
    return t


RE_DEF_SYS = re.compile(
    r'(ゲーム中で見ていません|条件です$|この戦闘|できません|してください|していません|'
    r'入力して|逃走|終了しました|状態が終了|となります$|キャンセルでき|^【[^】]{1,8}】)')


def extract(datapath):
    leaves = load_leaves(datapath)
    heads, tinfo = load_glossary(leaves)
    skip_overlay, override = build_overlays(leaves)
    story, defs, diag = [], [], collections.Counter()
    for p, b in leaves:
        if len(b) < 8 or len(b) > 0x2000000:
            continue
        if b[:3] in (b'GXT',) or b[:4] == b'TIM2' or b[:4] == b'KSEF':
            continue
        recs = find_records(b)
        if not recs:
            continue
        if b.endswith(TAIL_DEF):                        # 用語辞典 解説文
            for s, e, t in recs:
                t = clean(t)
                if (t and len(t) > 3 and not re.match(r'^イベント・', t)
                        and not RE_DEF_SYS.search(t)
                        and t.count('「') == t.count('」')
                        and not re.search(r'(モバイルジョイ|メモリースティック|インストール)', t)):
                    defs.append(norm_paren(t))
            continue
        if TRAILER in b[-8:]:                           # 系统/UI / 教程
            diag['sys_leaf'] += 1
            continue
        if p in skip_overlay:                           # 冒頭修正版 leaf（本体へ上書き済み）
            diag['overlay_skip'] += 1
            continue
        ms = process(b, override.get(p))
        if not ms:
            continue
        kept, prev = [], None
        for m in ms:
            if not m:
                continue
            if is_drop(m):
                diag['drop'] += 1
                continue
            if jp_ratio(m) < 0.30 and not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', m):
                diag['drop_jp'] += 1
                continue
            m = norm_paren(m)
            kept.append(m)
            prev = m
        if ms and len(ms) <= 40 and len(kept) < len(ms) * 0.5:
            diag['drop_leaf_half'] += 1
            continue
        story.extend(kept)
    # 同一「一封信」跨两框 → 合并（开引号未闭 + 下一行闭引号）
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
    dedup = []
    for m in story:
        if dedup and dedup[-1] == m:
            diag['drop_adj_dup'] += 1
            continue
        dedup.append(m)
    story = dedup
    # 解説文 去重（保持首次出现顺序）
    seen_d, dq = set(), []
    for m in defs:
        if m in seen_d:
            continue
        seen_d.add(m)
        dq.append(m)
    defs = dq
    return story, heads, defs, diag


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    data = sys.argv[1]
    if len(sys.argv) >= 4 and sys.argv[2] == '--sample':
        story, heads, defs, diag = extract(data)
        n = int(sys.argv[3])
        print('story=%d heads=%d defs=%d' % (len(story), len(heads), len(defs)))
        print('diag', dict(diag))
        print('--- first %d story lines ---' % n)
        for m in story[:n]:
            print(m)
        return
    out_path = sys.argv[2]
    story, heads, defs, diag = extract(data)
    lines = list(story)
    lines.append('■用語辞典（見出し語／ＩＤ順）')
    lines.extend(heads)
    lines.append('■用語辞典（解説文／見出し語との対応表はデータ内に存在しないため順不同）')
    lines.extend(defs)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('lines=%d story=%d heads=%d defs=%d' % (len(lines), len(story), len(heads), len(defs)))
    print('diag', dict(diag))


if __name__ == '__main__':
    main()
