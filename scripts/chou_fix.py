#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蝶の毒 華の鎖：復号後の局所的な文字化けを既知の正解で補正する表。

背景: XP3 内テキストは「zlib 展開後の cp932 平文に 1 バイト XOR」だが、
鍵はファイル内で区間一定ではなく、極少数のバイトだけ別鍵で書かれている
（原因は保護プラグイン poisonchain.tpm の内部にあり未解明）。
その結果 1〜3 バイトが壊れ、cp932 不正・半角カナ化・文字脱落が起きる。

本表は「文脈・ルビ・同型スクリプトの平行箇所」から一意に復元できた正解で、
復号バイト列をそのまま差し替える（推測ではなく根拠付き復元）。

値は (start, end, 正しい平文バイト列)。end は排他。
"""

# 単一/少数バイトの置換（key: (tag, filename)）
OVERRIDES = {
    # ルビ「げいごう」→ 迎合（迎=8c7d は正しく、合=8d87 の trail のみ破損）
    ('main', 'scenario/01_0.ks'):        [(13363, 13364, b'\x87')],
    # 行頭セパレータ ;■------（■=81a1 の trail 破損）
    ('main', 'scenario/01_true.ks'):     [(0, 3, b';\x81\xa1')],
    # 改行 \r\n の第2バイト（\n）破損
    ('main', 'scenario/02_hideo.ks'):    [(20770, 20771, b'\x0a')],
    # 舌を噛れる（噛=8a9a。ﾙ+不正 2 バイトを置換）
    ('main', 'scenario/02_shiba.ks'):    [(23526, 23528, b'\x8a\x9a')],
    # 離ればなれ（れ=82ea。trail 破損）
    ('main', 'scenario/03_0.ks'):        [(7006, 7007, b'\xea')],
    # 【百合子】（【=8179 の trail 破損）
    ('main', 'scenario/05_mizuhito_0.ks'): [(3200, 3201, b'\x79')],
    # 行頭セパレータ ;■------（07_0 は「;」自体も別鍵だった）
    ('main', 'scenario/07_0.ks'):        [(0, 3, b';\x81\xa1')],
    # 行中セパレータ ;----------... (1 バイト破損)
    ('main', 'scenario/07_tantei_0.ks'): [(57344, 57345, b'-')],
    # 改行 \r\n の第1バイト（\r）破損
    ('main', 'scenario/08_mizuhito.ks'): [(40068, 40069, b'\x0d')],
    # していなかった（い=82a2）/ 行中セパレータ（区切り記号の 1 バイト破損）
    ('main', 'scenario/08_shiba.ks'):    [(506, 507, b'\xa2'), (2659, 2660, b'-')],
    # ルビ「かがい」→ 花街（い=82a2）
    ('main', 'scenario/09_bondage.ks'):  [(444, 445, b'\xa2')],
    # 相変わらず美しく（美=94fc）/ 「そんな……」（…=8163）
    ('main', 'scenario/09_hideo.ks'):    [(17940, 17941, b'\x94'), (22984, 22985, b'c')],
    # ありがとう（が=82aa。が の trail 破損）
    ('main', 'scenario/09_mizuhito.ks'): [(54991, 54992, b'\xaa')],
    # 行頭セパレータ ;■------（1 バイト破損）
    ('main', 'scenario/10_hujita.ks'):   [(3, 4, b'-')],
    # [名前置換]（置=9275 の trail 破損）
    ('main', 'scenario/ed_hujita.ks'):   [(20495, 20496, b'\x75')],
    # [wait time=500]（9 本の同型 endroll が同一数列 → 500 で確定）
    ('main', 'scenario/endroll_f.ks'):   [(1024, 1025, b'5')],
    # [秀雄 奥 右500 ...]（右500 は本文中 158 例）
    ('toku', 'scenario/special.ks'):     [(15434, 15435, b'0')],
    # 行末セパレータの \r 破損（「…聞いたのか」+ 0x1E 0x0A → \r\n）
    ('main', 'scenario/04_mizuhito.ks'): [(4324, 4325, b'\x0d')],
}

HALFWIDTH_FIX = {
    ## 半角カナ化した「双バイト字の首バイト破損」を復元（多くは 0x82 = かな首バイト）
    # 金を作るしかないだろう
    ('main', 'scenario/01_0.ks'):            [(52709, 52710, b'\x82')],
    # あの薔薇の花は思いがけず
    ('main', 'scenario/02_mizuhito.ks'):     [(19743, 19744, b'\x82')],
    # お客様がいらっしゃっています
    ('main', 'scenario/04_0.ks'):            [(4062, 4063, b'\x82')],
    # 二人で出かけられたのだ！（られたの=82e7 82ea 82bd 82cc）
    # ／ お菓子のよう*ﾈ甘い → お菓子のよう[な]甘い
    ('main', 'scenario/05_hujita.ks'):       [(4927, 4935, b'\x82\xe7\x82\xea\x82\xbd\x82\xcc'),
                                              (11272, 11273, b'\x82')],
    # それでもどうなるか
    ('main', 'scenario/07_hujita.ks'):       [(23593, 23594, b'\x82')],
    # 百合子の意識は（識=8eaf）
    ('main', 'scenario/07_majima.ks'):       [(51108, 51109, b'\x8e')],
    # 指先は細かく震えている
    ('main', 'scenario/07_sonota.ks'):       [(791, 792, b'\x82')],
    # 今から二十五年（五=8cdc）
    ('main', 'scenario/07_tantei_0.ks'):     [(37273, 37274, b'\x8c')],
    # 子供っぽく笑う真島（ぽ=82db）
    ('main', 'scenario/08_0.ks'):            [(5729, 5730, b'\x82')],
    # [秀雄 私服+顔傷 横 のみ]
    ('main', 'scenario/08_hideo.ks'):        [(38539, 38540, b'\x82')],
    # 戦争目的が[曖昧'あいまい]で
    ('main', 'scenario/10_hideo.ks'):        [(49099, 49100, b'\x82')],
    # 斯波のあの、[傲慢'ごうまん]
    ('main', 'scenario/10_hujita.ks'):       [(20256, 20257, b'\x82')],
    # そっとその体を引き離すと（引=88f8） ／ [瑞人 voice=mizuhito1007]（i=69）
    ('main', 'scenario/10_mizuhito.ks'):     [(37742, 37743, b'\x88'), (38012, 38013, b'i')],
    # 行頭セパレータ ;■---
    ('main', 'scenario/11_mizuhito.ks'):     [(1, 2, b'\x81')],
    # タグ行の直前は \r\n（ﾓ/｣ は行末バイトの破損）
    ('main', 'scenario/03_true.ks'):         [(43184, 43186, b'\r\n')],
    ('main', 'scenario/_01_0.ks'):           [(44663, 44665, b'\r\n')],
    ('main', 'scenario/ed_regret.ks'):       [(24811, 24813, b'\r\n')],
    # ラベル名 *start_title（_ と t）
    ('main', 'sysscn/save.ks'):              [(28, 30, b'_t')],
    ('toku', 'sysscn/save.ks'):              [(28, 30, b'_t')],
    # 行頭セパレータ ;■endroll_z1
    ('main', 'scenario/endroll_z1.ks'):      [(49, 50, b'\x81')],
    # （こんなんじゃ……困るのに……）
    ('main', 'scenario/ed_hujita.ks'):       [(4614, 4615, b'\x82')],
    # [微'かす]かな[情事'じょうじ]
    ('main', 'scenario/ed_kura.ks'):         [(3548, 3549, b'\x82')],
    # しているような、おかしな感覚
    ('main', 'scenario/ed_mizuhito.ks'):     [(21792, 21793, b'\x82')],
    # 【百合子】の名前札（【=8179 の首バイトが 0x11 に化けていた）
    ('main', 'scenario/ed_hideo.ks'):        [(20113, 20114, b'\x81')],
    # コメント行頭の ; が : に化けていた（;■選択文章２）
    ('main', 'scenario/05_shiba_1.ks'):     [(31875, 31876, b';')],
    # [ev119aﾞ] → 表示外CGタグ。並びが [ev119b][ev119c] なので 1 バイト余剰。
    # 画面上に出ないため、タグとして解釈可能な空白に正規化（推定）。
    ('main', 'scenario/ed_butterflies.ks'):  [(11065, 11066, b' ')],
}

for _k, _v in HALFWIDTH_FIX.items():
    OVERRIDES.setdefault(_k, [])
    OVERRIDES[_k] = OVERRIDES[_k] + _v

# 区間ごと別鍵で読み直す（multi-byte 区間の例：first.ks の後半は鍵 0x18）
REKEY = {
    ('main', 'sysscn/first.ks'): [(574, 700, 0x18)],
    ('toku', 'sysscn/first.ks'): [(574, 700, 0x18)],
    # システム小スクリプトは本体鍵と「後半区間鍵」が別（2 段モデルが取り違える）
    ('main', 'sysscn/name.ks'): [(640, 798, 0x78)],
    ('toku', 'sysscn/name.ks'): [(640, 798, 0x78)],
    ('main', 'sysscn/loadinit.ks'): [(578, 822, 0xbf)],
    ('toku', 'sysscn/loadinit.ks'): [(578, 822, 0xbf)],
}


def apply_fix(tag, fn, buf, out):
    """buf=生の展開後バイト（暗号文）, out=復号済み平文 bytes -> 補正後 bytes"""
    o = bytearray(out)
    for a, b, key in REKEY.get((tag, fn), []):
        for i in range(a, min(b, len(buf))):
            o[i] = buf[i] ^ key
    for a, b, val in OVERRIDES.get((tag, fn), []):
        o[a:b] = val
    return bytes(o)


# ---------------------------------------------------------------------------
# 文字列レベル補正（復号後のテキストに対して。長さが変わる置換を含む）
#
# 1) 公式修正パッチ v1.01（初回生産版同梱 Patch.rar → patch.xp3）による誤字脱字の修正。
#    初回生産版の data.xp3 は誤植/文字化けを含み、公式パッチが 4 本の .ks を差し替えている。
#    各項は patch.xp3 内の該当 .ks を復号し、原文と突き合わせて確定（クリーニング鍵一意）。
# 2) 原本データで閉じ鉤括弧「」が脱落している 1 行の復元。
#    原文バイトは「…下さいね」+ CRLF（開き「 に対して閉じ 」なし）。XOR は長さを変えないため
#    欠落ではなく元データの欠陥と確定。同シーンの他の台詞はすべて 」 で閉じているため復元。
# ---------------------------------------------------------------------------
TEXT_PATCH = {
    # 公式パッチ v1.01：L193「斯波さまは…」→「斯波さんは…」
    ('main', 'scenario/05_0.ks'): [
        ('斯波さま', '斯波さん'),
    ],
    # 公式パッチ v1.01：L17「さり気なく噛察していた」→「観察していた」
    ('main', 'scenario/05_hideo_1.ks'): [
        ('噛察', '観察'),
    ],
    # 公式パッチ v1.01：L111「形見として[名前置換]もの」→「…のもの」／L1793「真島と*G用と」→「雑用」
    ('main', 'scenario/07_majima.ks'): [
        ('[名前置換]ものになっていた', '[名前置換]のものになっていた'),
        ('真島と*G用と', '真島と雑用と'),
    ],
    # 公式パッチ v1.01：L505「その目の済んだ輝き」→「澄んだ」／L1417「残酷で非常な」→「非情な」
    ('main', 'scenario/ed_shiba.ks'): [
        ('その目の済んだ輝き', 'その目の澄んだ輝き'),
        ('残酷で非常なところも', '残酷で非情なところも'),
    ],
    # 原本欠陥：閉じ鉤括弧の脱落を復元（開き「 に対応）
    ('main', 'scenario/05_shiba_1.ks'): [
        ('うちには来ないで下さいね\r\n', 'うちには来ないで下さいね」\r\n'),
    ],
}


def apply_text_patch(tag, fn, text):
    """復号後テキスト(str)に文字列レベル補正を適用して返す。"""
    for old, new in TEXT_PATCH.get((tag, fn), []):
        text = text.replace(old, new)
    return text
