#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Confidential Money (PSP / Otomate 2012) `.evb` -> text.

同族：マスケティア（same MARC middleware / `.evb` / `ar999_0000.bin`）。
字符表逐字节一致（`musketeer_charset`），但成框规则不同：

  * 框尾 = `0A 00`（`0A` 是框内软换行，成行时合并）
  * 框首 = 从框尾向前反扫「连续字符码」的起点（遇非字符码即停）
  * `1D 00`        = 主角名插入（默认名 `ナタリー`，可改名）
  * `8DD7 … 8DD8`  = 強調/ルビ包裹 ⇒ 去壳留字（マスケティア 误当控制码丢弃，本作必须保留）
  * `0x1F`         = 框间分隔（同 マスケティア 的 PRE 集）
  * `0x9C00-0x9FFF`= 演出码，丢弃
"""
import sys
import os
import glob
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import musketeer_charset as M

NAME_MACRO = (0x1D, 0x00)
WRAP_OPEN, WRAP_CLOSE = 0x8DD7, 0x8DD8
DEFAULT_NAME = 'ナタリー'
UNRESOLVED = '〔未解析〕'

# 本作（Confidential Money）字符表相对 マスケティア 的差异槽 —— 全部由「已知明文」锚定：
#   8DF4  4{?}00pm / 6{?}00pm           -> ':'
#   8125  20{?}でもいい / 30{?}オフ     -> '%'
#   8126  クッキー{?}クリーム / レディス{?}ジェントルメン -> '＆'
#   8140  ほっぺチュー{?} / ハロウィン{?} / 野獣{?} -> '♪'（記号ブロック最終槽）
#   812D  ドナルド・マ{?}ティン          -> 'ー'
#   8DED  二人の{?}が強くなる / {?}を深めたい -> '絆'
#   8DF0/8DF1 家に入るとき{?}{?}しない？ -> '挨'/'拶'
#   8DDF  いつも俺に{?}らせてなかった？    -> '奢'
CHARSET_FIX = {
    0x8DF4: ':', 0x8125: '%', 0x8126: '＆', 0x8140: '♪', 0x812D: 'ー',
    0x8DED: '絆', 0x8DF0: '挨', 0x8DF1: '拶', 0x8DDF: '奢',
    # `アイテム{?}ラフ画（リズ）{?}を入手しました。` -> 『』（片假名块末尾）
    0x81DB: '『', 0x81DC: '』',
    # `ナタリー{?}巻キ込ンデタンダネ` / `ギンシャリ{?}、イタダキマス` -> '～'
    0x81D6: '～',
}


def _ch(d, i):
    """d[i:i+2] 是字符码则返回字符，否则 None。"""
    if i + 1 >= len(d) or not (0x81 <= d[i] <= 0x9F):
        return None
    v = (d[i] << 8) | d[i + 1]
    if v in CHARSET_FIX:
        return CHARSET_FIX[v]
    return M.decode_char(v)


def _skippable(d, i):
    """反扫时可以「跨过」的非字符单元（宏 / 包裹符）。"""
    if i + 1 >= len(d):
        return 0
    v = (d[i] << 8) | d[i + 1]
    if v in (WRAP_OPEN, WRAP_CLOSE) or (d[i], d[i + 1]) == NAME_MACRO:
        return 2
    return 0


def boxes_of(data):
    """前向扫描：一个文本框 = 直到 `0A 00` 的连续字符/换行串。

    前向扫（而非从 `0A 00` 反扫）是关键：反扫时 `(0x8c,0x0a)` 会被当成字符码
    而错位一格（`（` → `戊`、`（お` → `荏疏險`），且错位会向后传染整行。
    """
    n = len(data)
    buf = []
    i = 0
    while i < n - 1:
        if data[i] == 0x0A and data[i + 1] == 0x00:
            if buf:
                yield buf
            buf = []
            i += 2
            continue
        if data[i] in (0x0A, 0x1F):      # 框内软换行 -> 合并
            i += 1
            continue
        s = _skippable(data, i)
        if s == 2:
            buf.append(('m', data[i:i + 2]))
            i += 2
            continue
        if 0x81 <= data[i] <= 0x9F:       # 字符码域：不论可否解码都吃 2 字节
            buf.append(('c' if _ch(data, i) is not None else 'u', data[i:i + 2]))
            i += 2
            continue
        # 文本中途可能出现 ASCII 半角（本作实证：`No.2のカーティス` 的 `.`）。
        # 只在「已在文本串中」时接受，避免把命令参数字节吃进正文。
        if buf and 0x20 <= data[i] <= 0x7E:
            buf.append(('a', data[i:i + 1]))
            i += 1
            continue
        # 本作存在「不以 `0A 00` 收尾」的框（扉文/章题：`――日本。 00 00 FB FF`）。
        # 只在「缓冲末字是句末标点」时按 00 收框，避免把命令参数的 0x00 当框尾。
        if buf and data[i] == 0x00:
            kind, bs = buf[-1]
            if kind == 'a':
                lastch = chr(bs[0])
            elif kind == 'm':
                lastch = ''
            else:
                lastch = _ch(bs, 0) or ''
            if len(buf) >= 3 and lastch in '。！？）」…':
                yield buf
            buf = []
            i += 1
            continue
        if buf:
            buf = []
        i += 1


def decode(tokens, name):
    out = []
    unknown = 0
    for kind, bs in tokens:
        if kind == 'm':
            if bs == bytes(NAME_MACRO):
                out.append(name)
            continue
        if kind == 'a':
            out.append(chr(bs[0]))
            continue
        if kind == 'u':
            v = (bs[0] << 8) | bs[1]
            if v in CHARSET_FIX:
                out.append(CHARSET_FIX[v])
            elif not M.is_effect(v):
                unknown += 1
                out.append(UNRESOLVED)
            continue
        v = (bs[0] << 8) | bs[1]
        c = CHARSET_FIX.get(v) or M.decode_char(v)
        if c is not None:
            out.append(c)
            continue
        if not M.is_effect(v):
            unknown += 1
            out.append(UNRESOLVED)
    return ''.join(out), unknown


def _kana(s):
    return any('ぁ' <= c <= 'ゖ' or 'ァ' <= c <= 'ヺ' or c in 'ー、。！？…「」（）' for c in s)


# 系统/UI 串（§0 不收）：ゲームオーバー 与复活提示，单独成框且直接上屏
EXCLUDE = {
    'ゲームオーバー',
    'リトライを押してください。',
    '復活するには、リトライを押してください。',
}


# 原文缺陷（源数据侧多打一个 `）`，非提取缺陷）——按 00b⑧ 用「整行定值表」修，不用正则泛修。
LINE_FIX = {
    '（よくこんなんで仕事になってるな……たまに徹夜で書いてるみたいだけど……）ママってタフ……）':
        '（よくこんなんで仕事になってるな……たまに徹夜で書いてるみたいだけど……）ママってタフ……',
    '（広いシャワー室……大きめのベッドが二つ……））':
        '（広いシャワー室……大きめのベッドが二つ……）',
}


def main():
    srcdir = sys.argv[1] if len(sys.argv) > 1 else 'ca000'
    dst = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_NAME
    files = sorted(glob.glob(os.path.join(srcdir, 'ev*.evb')))
    rows, unresolved, dropped = [], 0, collections.Counter()
    seen = set()
    for f in files:
        last = None
        for toks in boxes_of(open(f, 'rb').read()):
            text, unk = decode(toks, name)
            text = text.strip()
            if not text:
                dropped['empty'] += 1
                continue
            if unk and unk / max(1, len(text)) > 0.25:
                dropped['garbage'] += 1
                continue
            if len(text) <= 3 and not _kana(text):
                dropped['short-nokana'] += 1
                continue
            text = LINE_FIX.get(text, text)
            if text in EXCLUDE:
                dropped['system'] += 1
                continue
            # 跨档全同去重（各角色线/各分支把同一段剧本各存一份，实证 5 个 ev07x_00x0 同文）。
            # 同档内「相邻重复」保留（`…………` 连发是每次点击各一框）。
            if text != last:
                if text in seen:
                    dropped['dup'] += 1
                    continue
                seen.add(text)
            last = text
            unresolved += unk
            rows.append(text)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(rows) + '\n')
    print('files', len(files), 'lines', len(rows), 'chars', sum(len(x) for x in rows),
          'unresolved', unresolved, 'dropped', dict(dropped))


if __name__ == '__main__':
    main()
