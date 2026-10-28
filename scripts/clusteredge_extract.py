#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cluster Edge (PS2, SLPS_256.54) —— DataChain + MSDA 文本提取。

链路：ISO9660 → DATA.DAT(DataChain) → DATA/**.msd(MSDA) → 正文
输出：一行＝一次点击（记录内 \n＝同框软换行，合并）／全库精确去重／
      @XXnnnn@ 演出・整文标记剥离／名札行整行丢弃／标签行排除。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

ISO = os.path.join(VNTRANS_HOME, "_work_ce/Cluster Edge - Kimi o Matsu Mirai e no Akashi (Japan).iso")
SEC = 2048
TAG = re.compile(r"@[A-Z]{1,2}[0-9A-Z]{0,40}@")
LABEL = re.compile(r"^(キーワード|会話)\d+「")
# 単語バンク（@PL…@ で囲まれた見出し語だけのレコード）
WORD = re.compile(r"^@PL\d+@[^@]+@PL9999@$")

# 名札（キャラ名そのものだけのレコード）
NAMES = {
    'アゲート', 'アウイン', 'ベリル', 'ベスビア', 'コーラル', 'クロム', 'エマ', 'フォン',
    'ハウライト', '人造兵Ａ', '人造兵Ｂ', '教師Ａ', '教師Ｂ', '生徒Ａ', '生徒Ｂ',
    '生徒Ｃ', '生徒Ｄ', '軍人Ａ', '軍人Ｂ', '軍人Ｃ', '軍人Ｄ', '軍学校生徒Ａ',
    '軍学校生徒Ｂ', '軍学校生徒Ｃ', '軍学校生徒Ｄ', 'ラピス', 'ロード', 'セラフィ',
    'カールス', 'ナレーション', '大公', 'クロム団セピア', '？？？', '？？',
}

# UI／システム文（demo_message.msd 内、メッセージ窓に出す確認プロンプト等）
SYS = {
    'これでいいですか？', 'よろしいですか？', 'やめますか？',
    'このキーワードを使いますか？', 'イベントをスキップしますか？',
    '校舎を出ますか？', '寮に帰りますか？', 'もう寝ますか？',
    'キーワードがいっぱいです。\nどれか捨ててください。',
    'カードがなくなりました。', 'を手に入れました。', '123456789',
    '空白',       # 名札／窓を空にするためのプレースホルダ
}


# ADV モード（demo_message.msd）：単語・文テンプレート・システム通知は単独表示されない
DEMO_DROP = re.compile(
    r"^(?:チュートリアル\d|今日の成果は|学園のことが|あいうえお|123456789|ベリルが)"
    r"|に影響します$|を減らします$|を上げます$"
)
END_OK = '。？！…ー」』）!?'


def load_index():
    f = open(ISO, 'rb')
    vd = f.read(17 * SEC)[16 * SEC:]
    root = vd[156:156 + vd[156]]
    lba = struct.unpack_from('<I', root, 2)[0]
    size = struct.unpack_from('<I', root, 10)[0]
    f.seek(lba * SEC)
    d = f.read(((size + SEC - 1) // SEC) * SEC)[:size]
    i = 0
    dat_lba = None
    while i < len(d) and d[i]:
        ln = d[i]
        r = d[i:i + ln]
        nm = r[33:33 + r[32]].decode('latin1')
        if nm.startswith('DATA.DAT'):
            dat_lba = struct.unpack_from('<I', r, 2)[0]
        i += ln
    base = dat_lba * SEC
    f.seek(base + 0x18)
    cnt = struct.unpack('<I', f.read(4))[0]
    f.seek(base + 0x800)
    idx = f.read(cnt * 64)
    ents = {}
    for k in range(cnt):
        e = idx[k * 64:(k + 1) * 64]
        nm = e[:0x30].split(b'\0')[0].decode('cp932', 'replace')
        off, sz = struct.unpack_from('<II', e, 0x30)
        ents[nm] = (off, sz)
    return f, base, ents


def records(f, base, off, size):
    f.seek(base + off)
    d = f.read(size)
    if d[:4] != b'MSDA':
        return []
    n = struct.unpack_from('<I', d, 8)[0]
    out = []
    for i in range(n):
        p = 0x14 + i * 12
        typ, _pad, toff, mid = struct.unpack_from('<HHII', d, p)
        raw = d[toff:d.index(b'\0', toff)]
        out.append((typ, mid, raw.decode('cp932', 'replace')))
    return out


def norm(t):
    t = TAG.sub('', t)
    t = t.replace('\n', '')
    t = t.replace('\u3000', '\u3000')  # 全角空格原样保留
    return t.strip()


def main():
    f, base, ents = load_index()
    chapters = ['DATA/EVENT/MESSAGE/chapter%d.msd' % i for i in range(7)]
    banks = sorted(n for n in ents
                   if n.startswith('DATA/EVENT/MESSAGE/')
                   and 'chapter' not in n and 'etc' not in n)
    order = chapters + banks + ['DATA/DEMO/demo_message.msd']

    seen = set()
    lines = []
    stat = []
    for path in order:
        if path not in ents:
            continue
        off, size = ents[path]
        recs = records(f, base, off, size)
        is_demo = path.endswith('demo_message.msd')
        kept = 0
        for idx, (typ, mid, raw) in enumerate(recs):
            if raw in NAMES:            # 名札
                continue
            if LABEL.match(raw):        # キーワード/会話 索引ラベル
                continue
            if WORD.match(raw):         # 見出し語バンク
                continue
            if raw in SYS:              # UI 確認プロンプト
                continue
            t = norm(raw)
            if not t:
                continue
            if is_demo and DEMO_DROP.search(t):
                continue                # 文テンプレート・システム通知・書体見本
            if is_demo and t not in ('はい', 'いいえ') and t[-1] not in END_OK:
                continue                # 主語スロット付き文テンプレート／未完成断片
            if t in seen:
                continue
            seen.add(t)
            lines.append(t)
            kept += 1
        stat.append((path, len(recs), kept))

    out = os.path.join(VNTRANS_HOME, '提取结果/[PS2-JP]クラスターエッジ 〜君を待つ未来への証〜.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as g:
        g.write('\n'.join(lines) + '\n')

    for p, n, k in stat:
        print('%5d -> %5d  %s' % (n, k, p[5:]))
    print('TOTAL lines', len(lines))


if __name__ == '__main__':
    main()
