#!/usr/bin/env python3
"""sugar_build.py —— PAC 0x0425 文本流 → 一次点击一行。

断框判据（L0，字节码级）：
  · 0x0425/sub2 文本记录之间 **无任何指令字节** ⇒ 同一文本框内的排版换行（同框多行同时上屏）
  · 之间出现 0x0425/sub4（清窗）或 0x0025/sub1（等待点击）⇒ 新框
  · 0x0425/sub1 = 独立名札窗（丢弃）；0x0425/sub6 = 菜单/调试标签（丢弃）

版式：**单版**——一次点击＝一框＝一行。框内换行（相邻记录 gap 0）只是排版换行，
直接删去拼接进同一行，不拆行、不出「段行 + 合并行」。
清理：&S..H..R..G..B..# 前缀、&/# 后缀、<汉字^读音> ruby 取汉字。
"""
import glob
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct

PAC = os.environ.get('SUGAR_PAC', os.path.join(VNTRANS_HOME, '_work_sugar/pac'))
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PS2-JP]シュガシュガルーン -恋もおしゃれもピックアップ！.txt')

# 非剧本 / 纯 UI / 数据表 / 调试菜单 的 PAC
SKIP = {
    7026,  # DOLL_FSM_01  カメラ・レイアウト設定（@tag DSL）
    7027,  # DOLL_FSM_02
    7028,  # DOLL_FSM_03 / ADVENTURE_MAIN（@tag DSL）
    7029,  # FLASH_VIEWER 演出台本（@tag DSL）
    7030,  # デバッグメニュー（"進行" / "ミヤケデバッグ" / error 串）
    7031,  # 所持アイテム一覧（S0 商品名 540 条）
    7051,  # エクル所持数ステータス画面
    7072,  # 家具 ID テーブル
}

TAG = re.compile(r'^&S\d+H\d+R\d+G\d+B\d+#')
RUBY = re.compile(r'<([^<>^]*)\^[^<>]*>')
DROP = [
    re.compile(r'^[\s　０-９]+$'),          # 状态栏数字/空白
    re.compile(r'^エクル$'),
    re.compile(r'^「[^「」]{1,20}」$'),      # 商品名のみ（データ表のダンプ）
    re.compile(r'^進行フラグリセットします'),
    re.compile(r'(編|ＯＰ)　エンド$'),        # 脚本节标签
    re.compile(r'^を(もらった|探しあてた|見つけた|あげた|手渡した|使った)'),
    re.compile(r'^(そこそこうれしい|ちょっとうれしい|すっごいうれしい！|そんした気分…)$'),
    re.compile(r'^・+[！？…]*$'),          # タイピング演出の破片
]


def records(d):
    out = []
    p = 0
    while True:
        p = d.find(b'\x25\x04', p)
        if p < 0:
            break
        sub = struct.unpack_from('<H', d, p + 2)[0]
        if sub in (1, 2, 6):
            e = d.find(b'\x00', p + 4)
            if e < 0:
                break
            try:
                st = d[p + 4:e].decode('cp932')
            except UnicodeDecodeError:
                p += 2
                continue
            out.append((p, e + 1, sub, st))
            p = e + 1
        else:
            p += 2
    return out


def clean(s):
    s = TAG.sub('', s)
    s = s.replace('&/#', '')
    s = RUBY.sub(r'\1', s)
    return s.strip()


def boxes(fn):
    """返回 [[第1行, 第2行, ...], ...]——一个内层列表 = 一个文本框（一次点击）"""
    d = open(fn, 'rb').read()
    recs = [r for r in records(d) if r[2] == 2]
    out = []
    cur = []
    prev_end = None
    for p, e, sub, st in recs:
        t = clean(st)
        if prev_end == p:
            cur.append(t)
        else:
            if cur:
                out.append(cur)
            cur = [t]
        prev_end = e
    if cur:
        out.append(cur)
    return out


def keep(segs):
    joined = ''.join(segs)
    if not joined:
        return False
    return not any(r.search(joined) for r in DROP)


GRAM = 12


def dedupe_common(blocks):
    """共通ブロック（同一 12 框連続が 4 本以上に出る）は初出のみ残す。blocks = [(pid, [box,...])]"""
    from collections import defaultdict

    def key(b):
        return ''.join(b)

    seen_in = defaultdict(set)
    for pid, bs in blocks:
        for i in range(len(bs) - GRAM + 1):
            seen_in[tuple(key(b) for b in bs[i:i + GRAM])].add(pid)
    multi = {g for g, s in seen_in.items() if len(s) >= 4}
    flat = []
    gram_pos = {}
    out = []
    dropped = []
    for pid, bs in blocks:
        res = []
        i = 0
        while i < len(bs):
            g = tuple(key(b) for b in bs[i:i + GRAM]) if i + GRAM <= len(bs) else None
            if g and g in multi and g in gram_pos:
                p = gram_pos[g]
                L = GRAM
                while i + L < len(bs) and p + L < len(flat) and key(bs[i + L]) == flat[p + L]:
                    L += 1
                dropped.append((pid, i, L))
                i += L
                continue
            if g and g in multi and g not in gram_pos:
                gram_pos[g] = len(flat)
            res.append(bs[i])
            flat.append(key(bs[i]))
            i += 1
        out.append((pid, res))
    return out, dropped


def merge(bs):
    """同框多行 -> 一行（框内换行＝排版换行，直接拼接）"""
    out = []
    for b in bs:
        s = ''.join(x for x in b if x)
        if s:
            out.append(s)
    return out


def main():
    files = sorted(glob.glob(os.path.join(PAC, 'pac_*.bin')))
    blocks = []
    for fn in files:
        i = int(re.search(r'pac_(\d+)', fn).group(1))
        if i in SKIP:
            continue
        bs = boxes(fn)
        kept = [b for b in bs if keep(b)]
        print(i, len(bs), len(kept), sum(1 for b in kept if len(b) > 1))
        blocks.append((i, kept))
    red, dropped = dedupe_common(blocks)
    lines = []
    nbox = 0
    for pid, bs in red:
        nbox += len(bs)
        lines.extend(merge(bs))
    for d in dropped:
        print('dedupe drop pac_%d off %d len %d' % d)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('boxes', nbox, 'lines', len(lines))


if __name__ == '__main__':
    main()
