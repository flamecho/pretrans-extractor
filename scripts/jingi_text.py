#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP]仁義なき乙女 恋恋三昧（Madoka GScript / CRPT .sce）全文本提取。

引擎/容器：美蕾 Madoka GScript；剧本 `恋恋三昧.sce` 为 CRPT(type=0x30001) 加密，逐 1024B：
  链式解扰(ORDER 0x43+0x17*i) → LCG 256×u32 表异或（seed 0x915354A9/MUL 0x41C64E6D/ADD 0x3039）
  → 逐块 seed（运行时派生，无静态公式；按日文标点/假名/汉字似然枚举 0..255 复元）。
文本区＝尾部连续高分块（本作 block 6179 起）；串表以 NUL 自定界（L1）。

记录形态（记录自定界＋交叉验证，L1）：
  [名字串(独立名字窗)] [语音id ASCII] [正文串]；名字串＝短、无句读/引号、紧邻语音 id ⇒ 剔除；
  `\x08`＝框内换行（合并）；`\x10 base \x11 read \x12`＝注音（留 base）；
  主角名宏 `\x05\x80\x80\x80\xC5\xB9`→小泉、`...\xC5\xBA`→沙紀（默认名，wiki/游戏内名称表）。
  一条 NUL 串＝一条消息记录＝一次点击一框 ⇒ 单版（`[l]` 类同框多点击在本引擎串表中无对应，
  跨框断引号/括号成组检测 0）⇒ 不产合并行。

用法: python jingi_text.py <恋恋三昧.sce> <out.txt>
"""
import sys, re, argparse
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import numpy as np
import asuka_extract as A

VOICE = re.compile(r'^[$]?[A-Z0-9]{2,5}-[A-Z]{2,4}-[A-Z0-9]{3,6}-\d{3}$')
NAME_PUNCT = re.compile(r'[。、！？…「」『』（）()]')
SYS_EXACT = {
    'データベースが開けませんでした。',
    'ＭＳ 明朝', 'ＭＳ ゴシック',
    'アナザーメニューへ戻ります。よろしいですか？',
    'タイトル画面へ戻ります。よろしいですか？',
    '回想メニューへ戻ります。よろしいですか？',
    '終了します。よろしいですか？',
    '次のセリフは■(重複セリフ)指定のメッセージですが、まだファイル名が指定されていません。',
    'ルール画像 : 「', '」が存在しません。',
}
SYS_RE = re.compile(r'^(test_|SEF_|存在しないキャラクターIDです|フィルターの指定が)')
MACRO_SUR = b'\x05\x80\x80\x80\xc5\xb9'
MACRO_GIV = b'\x05\x80\x80\x80\xc5\xba'


def decrypt(path):
    data = open(path, 'rb').read()
    assert data[:4] == b'CRPT'
    pay = data[0x20:]
    NB = len(pay) // 0x400
    blocks = np.frombuffer(pay[:NB * 0x400], dtype=np.uint8).reshape(NB, 0x400)
    full = bytearray()
    scores = []
    for bi in range(NB):
        base = np.frombuffer(A.decrypt_block(bytes(blocks[bi])), dtype=np.uint8)
        k, sc = A.score_block(base)
        full += bytes(c ^ k for c in base)
        scores.append(int(sc))
    return bytes(full), scores, NB


def pool_start(scores):
    best, s = None, None
    for i, sc in enumerate(scores):
        if sc >= 150:
            if s is None:
                s = i
        else:
            if s is not None and (best is None or (i - s) > (best[1] - best[0])):
                best = (s, i)
            s = None
    if s is not None and (best is None or (len(scores) - s) > (best[1] - best[0])):
        best = (s, len(scores))
    return best[0]


def clean(b):
    b = b.replace(MACRO_SUR, '小泉'.encode('cp932')).replace(MACRO_GIV, '沙紀'.encode('cp932'))
    try:
        t = b.decode('cp932')
    except Exception:
        return None
    t = re.sub(r'\x10(.*?)\x11.*?\x12', r'\1', t)
    t = t.replace('\x08', '').replace('%s名前%', '沙紀')
    return re.sub(r'[\x00-\x1f]', '', t)


def extract(path):
    full, scores, NB = decrypt(path)
    ps = pool_start(scores)
    raw = full[ps * 0x400:].split(b'\x00')
    dec = []
    for s in raw:
        try:
            dec.append(s.decode('cp932'))
        except Exception:
            dec.append(None)
    lines, nname = [], 0
    for i, t in enumerate(dec):
        if t is None or len(t) < 1:
            continue
        if raw[i][0] < 0x20:
            continue
        if VOICE.match(t):
            continue
        nt = dec[i + 1] if i + 1 < len(dec) else None
        if (nt and VOICE.match(nt) and len(t) <= 12 and not NAME_PUNCT.search(t)):
            nname += 1
            continue
        if t in SYS_EXACT or SYS_RE.match(t):
            continue
        if 'は廃止されました' in t or 'を使用してください' in t:
            continue
        cj = sum(1 for ch in t if 0x3040 <= ord(ch) <= 0x9fff or ch in '、。「」『』…―・')
        if cj < 1:
            continue
        t2 = clean(raw[i])
        if t2:
            lines.append(t2)
    return lines, ps, nname


def cross_box_dual(lines):
    def q(t):
        return (t.count('「') - t.count('」'), t.count('『') - t.count('』'),
                t.count('（') - t.count('）'))
    out, i, ngrp = [], 0, 0
    while i < len(lines):
        a = lines[i]
        if i + 1 < len(lines):
            b = lines[i + 1]
            da, db = q(a), q(b)
            for k in range(3):
                if (da[k] > 0 and db[k] < 0 and da[k] + db[k] == 0
                        and da[0] + db[0] == 0 and da[1] + db[1] == 0 and da[2] + db[2] == 0):
                    out.extend([a, b, a + b]); ngrp += 1
                    i += 2
                    break
            else:
                out.append(a); i += 1
            continue
        out.append(a); i += 1
    return out, ngrp


def main():
    ap = argparse.ArgumentParser(description='[PC-JP]仁義なき乙女 恋恋三昧 (Madoka GScript/CRPT) extractor')
    ap.add_argument('sce', help='恋恋三昧.sce')
    ap.add_argument('out', help='输出 txt（UTF-8 BOM / LF）')
    args = ap.parse_args()
    lines, ps, nname = extract(args.sce)
    res, groups = cross_box_dual(lines)
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for l in res:
            f.write(l + '\n')
    print('pool_block=%d lines=%d names_dropped=%d dual_groups=%d -> %s'
          % (ps, len(res), nname, groups, args.out))


if __name__ == '__main__':
    main()
