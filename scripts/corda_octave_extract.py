# -*- coding: utf-8 -*-
"""金色のコルダ オクターヴ (Switch) 全文本提取器 v3  (定稿候选)
容器: CDAR (DATA.BIN)
文本记录: 04 <u16 len> <cp932 bytes> 00   (记录驱动扫描, 不失步)
消息分隔: 1e8b052422 (BOUND) / close+C7 (1ef907874c 1ec7094774) / 1e910bbda0 (M91)
          / 上一条记录后无 close (独立行)
名字插入: 1e cf 02 1e 0a 后的 02/1e 5B 指令链
"""
import struct, re, os, sys, collections

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
C7 = b'\x1e\xc7\x09\x47\x74'
C7CLOSE = CLOSE + C7
M91 = b'\x1e\x91\x0b\xbd\xa0'
INS = b'\x1e\xcf\x02\x1e\x0a'

# 主人公(小日向かなで) 姓名默认值
VAR_TEXT = {
    0x01cb013a: '小日向',
    0x01ea0153: 'かなで',
    0x329007e7: 'かなで',
    0x05fa0288: 'かなで',
    0x1d76056e: '小日向',
    0x1d950587: 'かなで',
    0x2a0d06bc: 'かなで',
    0x2350067d: '小日向かなで',
    0x42820847: 'こひなた　かなで',
}
# 名字插入块内的"槽位/常量"标记(非变量)
INS_CONSTS = {
    0x15500462, 0x1af9056c, 0x0d6503f2, 0x13d404bc, 0x019200ff,
    0x0b49032e, 0x1f470562,
    0x00000000, 0x00000001, 0x00000002, 0x00000003, 0x00000004,
    0x00000005, 0x00000006, 0x00000007, 0x00000008, 0x00000009,
    0x0000000a, 0x0000000b, 0x0000000c, 0x0000000d, 0x0000000e,
    0x0000000f, 0x00000010, 0x00000011, 0x00000012, 0x00000013,
    0x00000014, 0x00000015, 0x00000016, 0x00000017, 0x00000018,
    0x00000019, 0x0000001a, 0x0000001b, 0x0000001c, 0x0000001d,
    0x0000001e, 0x0000001f, 0x00000020,
}
PLACEHOLDER = '〓'


class CDAR:
    def __init__(self, path):
        self.f = open(path, 'rb')
        head = self.f.read(16)
        assert head[:4] == b'CDAR', 'not CDAR'
        self.unk1, self.count, self.unk2 = struct.unpack_from('<III', head, 4)
        base = 16 + self.count * 4
        self.f.seek(base)
        et = self.f.read(12 * self.count)
        self.entries = [struct.unpack_from('<III', et, 12 * i) for i in range(self.count)]

    def data(self, i):
        o, ds, s = self.entries[i]
        self.f.seek(o)
        return self.f.read(s)


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
    res = []
    unres = []
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
            if op == 0x02:
                if val not in INS_CONSTS:
                    parts.append(val)
            elif val == 0x329007e7:
                parts.append(val)
            elif val == 0x05fa0288:
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
    s = re.sub(r'[\u3000]*\n[\u3000]*', '', s)
    return s.replace('\n', '')


# 用語辞典：読み -> 見出し語
# 数据来源：脚本内 `02 <术语ID> | 1e 143a044e | 04 <見出し語>` 记录（全脚本实测 72 个术语 ID），
# 与辞典条目自带的読み按读音配对；键已去除空白/换行归一化。
GLOSS_HEAD = {
    'みずしまあらた': '水嶋　新',
    'ぜんこくたいかい': '全国大会',
    'りんでんほーる': '菩提樹寮',
    'あい': 'Ai',
    'あまみやせい': '天宮　静',
    'ぺるせふぉねー': 'ペルセフォネー',
    'つちうらりょうたろう': '土浦梁太郎',
    'いおり': '伊織',
    'こひなたかなで': '小日向かなで',
    'ながみね': '長嶺',
    'しみずけいいち': '志水桂一',
    'おうさきしのぶ': '王崎信武',
    'ぴえとら': 'ピエトラ',
    'はーです': 'ハーデス',
    'みょうがれいじ': '冥加玲士',
    'あまねがくえん': '天音学園',
    'せみふぁいなる': 'セミファイナル',
    'とうがねちあき': '東金千秋',
    'ぶらぼーぽいんと': 'ＢＰ',
    'ぜんこくがくせいおんがくこんくーる': '全国学生音楽コンクール',
    'ほづみしろう': '火積司郎',
    'しせいかん': '至誠館',
    'しゅうじょう': '愁情',
    'ようせいおんがくえんしゅう': '妖精音楽演習',
    'ななみそうすけ': '七海宗介',
    'はるもにあ': 'ハルモニア',
    'あれくせい': 'アレクセイ',
    'ゆのきあずま': '柚木梓馬',
    'ひはらかずき': '火原和樹',
    'ひど': '氷渡',
    'きらあきひこ': '吉羅暁彦',
    'りり': 'リリ',
    'おぶりがーど': 'Obrigado',
    'じんなん': '神南',
    'やぎさわゆきひろ': '八木沢雪広',
    'がくないこんくーる': '学内コンクール',
    'かんぱねらがくえん': 'カンパネラ学園',
    'ふぁいなる': 'ファイナル',
    'おーけすとらぶ': 'オーケストラ部',
    'きさらぎきょうや': '如月響也',
    'せらぷおいふぁーれ': 'Ce la puoi fare',
    'あるじぇんと': 'アルジェント',
    'ふどうしょうま': '不動翔麻',
    'こんくーる': 'コンクール',
    'あぶさんと': 'アブサント',
    'ひのかほこ': '日野香穂子',
    'はせくらにあ': '支倉仁亜',
    'かんたれら': 'カンタレラ',
    'かなざわひろと': '金澤紘人',
    'ふぇっろ': 'フェッロ',
    'きさらぎりつ': '如月　律',
    'まえすとろふぃーるど': 'マエストロフィールド',
    'ねこじま': '猫島',
    'ときほうせい': '土岐蓬生',
    'うた': '歌',
    'みずしまはると': '水嶋悠人',
    'さいか': '彩華',
    'せりざわむつみ': '芹沢睦',
    'えとうきりや': '衛藤桐也',
    'もんど': 'モンド',
    'えうちあーも': 'Eu te amo',
    'まるとの': 'マルトノ',
    'きょくそう': '曲想',
    'こがっき': '古楽器',
    'ふゆうみしょうこ': '冬海笙子',
    'ごすとーぞ': 'Gostoso',
    'ちゃう': 'Tchau',
    'ふぁーた': 'ファータ',
    'かじあおい': '加地　葵',
    'せいれい': '清麗',
    'さかきだいち': '榊　大地',
    'つきもりれん': '月森　蓮',
    'せいそうがくいん': '星奏学院',
    'かのう': '狩野',
}


def gloss_format(t):
    """用語辞典条目：把行首的 （読み） 换成 【見出し語】（找不到对应则退回読み）"""
    m = re.match(r'^（([^）]*)）', t)
    if not m:
        return t
    reading = m.group(1)
    head = GLOSS_HEAD.get(re.sub(r'[\s\u3000]', '', reading), reading)
    return '【' + head + '】' + t[m.end():]


RE_NOISE = [
    re.compile(r'^イベント・'),
    re.compile(r'^回想録[0-9０-９]+$'),
    re.compile(r'^配信イベント[0-9０-９]*$'),
    re.compile(r'^札[0-9０-９]+$'),
    re.compile(r'^(ダミー|仮|予備|テスト)$'),
    re.compile(r'フラグ$'),
]
RE_NOISE_BIN = [
    re.compile(r'^[0-9A-Za-z_\-]+$'),
    re.compile(r'^[！？…、。\s]+$'),
]
RE_GLOSSARY = re.compile(r'^（[ぁ-んゝゞー\s　]{1,24}）')


def is_noise(t, binary=False):
    if t.startswith('＜デバッグ時のみ表示＞'):
        return True
    if '場合別実行エラー' in t:
        return True
    if any(r.search(t) for r in RE_NOISE):
        return True
    if binary and any(r.search(t) for r in RE_NOISE_BIN):
        return True
    return False


def jp_ratio(t):
    if not t:
        return 0.0
    jp = sum(1 for ch in t if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff')
             or ('\u3000' <= ch <= '\u303f') or ('\uff01' <= ch <= '\uff60') or ch in '─―…‥')
    return jp / len(t)


def process(b):
    recs = find_records(b)
    if not recs:
        return [], [], False
    is_gloss = bool(RE_GLOSSARY.match(recs[0][2]) or RE_GLOSSARY.match(recs[-1][2]))
    msgs = []
    cur = []
    unres = []
    for i, (s, e, t) in enumerate(recs):
        gap = b[recs[i - 1][1]:s] if i > 0 else b[:s]
        sep = False
        if BOUND in gap or C7CLOSE in gap or M91 in gap:
            sep = True
        if i > 0 and not gap.startswith(CLOSE) and not b[recs[i - 1][1]:recs[i - 1][1] + 5] == CLOSE:
            # 上一条记录后并非紧跟 close -> 上一条为独立行(已 flush)
            sep = True
        if C7 in gap:
            sep = True
        if sep and cur:
            msgs.append(''.join(cur)); cur = []
        ins, u = parse_inserts(gap)
        unres += u
        for x in ins:
            cur.append(x)
        cur.append(t)
        # 本条记录后是否紧跟 close
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        after = b[e:nxt]
        if not after.startswith(CLOSE):
            msgs.append(''.join(cur)); cur = []
    if cur:
        msgs.append(''.join(cur))
    return msgs, unres, is_gloss


def main():
    data_path, out_path, gloss_path = sys.argv[1], sys.argv[2], sys.argv[3]
    c = CDAR(data_path)
    main_lines = []
    gloss_lines = []
    n_ent = 0
    n_gloss_ent = 0
    all_unres = collections.Counter()
    total_recs = 0
    diag = collections.Counter()
    diag_samples = collections.defaultdict(list)
    for i in range(c.count):
        b = c.data(i)
        if len(b) < 8 or len(b) > 0x2000000:
            continue
        msgs, unres, is_gloss = process(b)
        if not msgs:
            continue
        total_recs += len(msgs)
        is_script = (CLOSE in b) or (BOUND in b) or (INS in b)
        kept = []
        for m in msgs:
            m2 = clean(m)
            if not m2:
                continue
            if not is_script and jp_ratio(m2) < 0.30 and not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', m2):
                diag['drop_jp'] += 1
                if len(diag_samples['drop_jp']) < 40: diag_samples['drop_jp'].append((i, m2[:60]))
                continue
            if is_noise(m2, binary=not is_script):
                diag['drop_noise'] += 1
                if len(diag_samples['drop_noise']) < 40: diag_samples['drop_noise'].append((i, m2[:60]))
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
    print(f'entries={n_ent} lines={len(main_lines)}  glossary_entries={n_gloss_ent} glossary_lines={len(gloss_lines)} total_msgs={total_recs}')
    print('diag:', dict(diag))
    for k in ('drop_jp','drop_noise'):
        print(f'-- {k} samples --')
        for i, t in diag_samples[k][:15]:
            print(f'   entry {i}: {t!r}')
    print('== 未解析插入值 ==')
    for v, n in all_unres.most_common(30):
        print(f'  0x{v:08x} x{n}')


if __name__ == '__main__':
    main()
