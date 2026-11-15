# -*- coding: utf-8 -*-
"""[JP]Dual Colors (PC / SaiSys / chiffon 2001) 正文提取

用法：
    python scripts/saisys_ssb_text.py --ssb <script/Data.ssb> --out <成品.txt>
    python scripts/saisys_ssb_text.py --ssb ... --span 1639,24855 --stats

判据链（全部代码级）：
  L0-1  Data.ssb 整体 XOR 0xAA（0xAA→0x00＝NUL 补白；判别见 --check-key）
  L0-2  记录＝NUL 自定界串，相邻起点差 gcd＝4（4 字节对齐）
  L0-3  **一条正文恒定两份**：第二份＝第一份把 0x0D 换成 3 字节 `\\nn`（647 例）
        或把 0x0D 换成 0x0D 0x0D（306 例），余下逐字节全等（5,439 例）
        ⇒ 一份显示一份回想；取首份
  L0-4  **选项＝连续 ≥2 条「只有一份」的短记录**（成对者必有副本；选项不存副本），
        且不以「/（ 开头（台词必带引号）
  L1    断框：记录内部 0x0D 个数 0:5,038 / 1:1,495 / 2:168，**硬上限 2 ⇒ 文本窗 3 行**；
        单段最长 **36 字** 也是 3 行窗的宽度 ⇒ 0x0D 是**框内换行**，合并；一次记录＝一次点击 ⇒ 单版
"""
import argparse
import re
import sys

KEY = 0xAA
SPAN = (1639, 24855)   # 正文段记录区间 [a, z)
MAXSEG = 36            # 框内单行宽度上限（实测峰值，用于验收）
INDENT = '\u3000'


def records(data, key=KEY):
    d = bytes(b ^ key for b in data)
    out, i, n = [], 0, len(d)
    while i < n:
        if d[i]:
            j = i
            while j < n and d[j]:
                j += 1
            out.append(d[i:j])
            i = j
        else:
            i += 1
    return out


def is_text(b):
    """正文候选：含 ≥0x80 字节（正文段内素材/标签一律纯 ASCII，如 hrobi01/pffuka/vfuk1197）

    ⚠ 不能加「必须含假名/汉字」——本作有 142 条只由标点构成的台词（`「！？」`/`「？？？」`/
      `「ＯＫ。」`）与 `～ＢＡＤ　ＥＮＤ～` 卡，加了就会静默丢行。
    """
    return any(x >= 0x80 for x in b)


def norm(b):
    """把「显示／回想」两种换行编码归一：0x0D、`\\nn`、`\\n` 全部去掉"""
    return b.replace(b'\r', b'').replace(b'\\nn', b'').replace(b'\\n', b'')


def merge(b):
    """框内换行合并（0x0D 直接去掉，不留分隔符）；首尾全角空格为居中留白，去掉"""
    t = b.decode('cp932').replace('\r', '')
    return t.strip(INDENT + ' ')


def is_option_text(b):
    t = b.decode('cp932')
    return not t.startswith(('「', '（'))


def extract(recs, span=SPAN):
    a, z = span
    items = []          # [(kind, text)]  kind: 'line' | 'option'
    st = {'pair': 0, 'single': 0, 'opt': 0, 'dup': 0, 'skip': 0}
    k = a
    while k < z:
        b = recs[k]
        if not is_text(b):
            st['skip'] += 1
            k += 1
            continue
        # 副本判定：下一条与本体只差换行编码
        if k + 1 < z and is_text(recs[k + 1]) and norm(recs[k + 1]) == norm(b):
            items.append(('line', merge(b)))
            st['pair'] += 1
            k += 2
            continue
        st['single'] += 1
        items.append(('single', merge(b)))
        k += 1
    # 连续 single ⇒ 选项块（≥2 条且全部不带引号）
    out, i = [], 0
    while i < len(items):
        if items[i][0] != 'single':
            out.append(items[i][1])
            i += 1
            continue
        j = i
        while j < len(items) and items[j][0] == 'single':
            j += 1
        run = items[i:j]
        if len(run) >= 2 and all(not t.startswith(('「', '（')) for _, t in run):
            for _, t in run:
                out.append(t)
            st['opt'] += len(run)
        else:
            for _, t in run:
                out.append(t)
        i = j
    return out, st


def check_key(data):
    print('%-6s %-8s %-8s %-8s %s' % ('key', '假名', '汉字', 'cp932非法', '抽样'))
    for k in (0x8A, 0xAA):
        d = bytes(b ^ k for b in data)
        bad = 0
        for i in range(len(d) - 1):
            if d[i] >= 0x80:
                try:
                    d[i:i + 2].decode('cp932')
                except UnicodeDecodeError:
                    bad += 1
        s = d.decode('cp932', 'ignore')
        nk = len(re.findall(r'[\u3041-\u309f\u30a0-\u30ff]', s))
        nh = len(re.findall(r'[\u4e00-\u9fff]', s))
        print('0x%02X   %-8d %-8d %-8d %r' % (k, nk, nh, bad, s[0x50:0x62]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ssb', required=True)
    ap.add_argument('--out')
    ap.add_argument('--span', default='%d,%d' % SPAN)
    ap.add_argument('--check-key', action='store_true')
    args = ap.parse_args()

    data = open(args.ssb, 'rb').read()
    print('源 %s  %d B' % (args.ssb, len(data)))
    if args.check_key:
        check_key(data)
        return
    recs = records(data)
    span = tuple(int(x) for x in args.span.split(','))
    lines, st = extract(recs, span)

    # 验收：段长、CR 上限、空行
    seg = [len(p) for p in ''.join(lines).split('\r')]
    print('记录 %d / 正文段 %d..%d' % (len(recs), span[0], span[1] - 1))
    print('成对 %d / 单份 %d（其中选项 %d）/ 跳过素材·标签 %d'
          % (st['pair'], st['single'], st['opt'], st['skip']))
    print('输出 %d 行 / %d 字 / 最长行 %d'
          % (len(lines), sum(len(x) for x in lines), max(len(x) for x in lines) if lines else 0))
    over = [x for x in lines if len(x) > 3 * MAXSEG]
    print('超 3×%d 字的行 %d' % (MAXSEG, len(over)))
    for x in over[:5]:
        print('   ', repr(x[:80]))
    if args.out:
        body = '\n'.join(lines) + '\n'
        with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write(body)
        print('写出 %s  %d B' % (args.out, len(body.encode('utf-8'))))


if __name__ == '__main__':
    main()
