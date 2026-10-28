# -*- coding: utf-8 -*-
"""一行多个框的拆行（独白 `（A）（B）` / 台词 `「A」「B」`）。

用户给的四个探针里，`(?!^)「` 与 `(?<!^)(」)(?!$)` 指向「句中还有引号」，
结构上等价于：**一行里有 ≥2 个顶层段落**。其中：
  - 合法：叙述里内联引用（`「はい」とも「いいえ」とも言えず`）、名言注（`リュウ・クロア（子供時代）（…）`）
  - 缺陷：两个独立的框被粘在一行（`（A）（B）`、`「A」「B」`）⇒ 必须拆

判据（只处理缺陷）：
1. 顶层段 ≥2；
2. **段与段之间只有空白**（没有 `と`/`って`/`、` 之类的连接成分）⇒ 说明是并列的两个框；
3. 若第一段之前是「纯人名」且第一段短（≤10 字、无句读）⇒ 那是「角色名+状态注」，整段剥掉（本批不显示说话人），不输出；
4. 其余情况原样保留（合法内联引用）。

用法：
  python scripts/fix_multi_brackets.py <txt> [--ch 括号|引号] [--dry] [-v]
"""
import argparse
import io
import re
import shutil
import sys

OPEN = {'括号': '（', '引号': '「'}
CLOSE = {'括号': '）', '引号': '」'}
NAME_RE = re.compile(r'^[\u3040-\u30ff\u4e00-\u9fff・０-９0-9Ａ-Ｚａ-ｚ]{1,20}$')
ANNO = re.compile(r'^[^。、！？…]{1,10}$')


def top_pairs(s, op, cl):
    stack, out = [], []
    for i, ch in enumerate(s):
        if ch == op:
            stack.append(i)
        elif ch == cl and stack:
            out.append((stack.pop(), i))
    out.sort()
    return out


def split_line(line, op, cl):
    """返回 ('split', [行...]) / ('strip', [行...]) / None"""
    if line.count(op) < 2 or line.count(op) != line.count(cl):
        return None
    segs = top_pairs(line, op, cl)
    if len(segs) < 2:
        return None
    # 段之间必须只有空白
    between = []
    prev = 0
    for i, j in segs:
        between.append(line[prev:i])
        prev = j + 1
    tail = line[prev:]
    if tail.strip():
        return None
    if any(b.strip() for b in between[1:]):
        return None

    head = between[0]
    pieces = [line[i:j + 1] for i, j in segs]
    # 人名 + 状态注：`リュウ・クロア（子供時代）（…）`
    if head.strip() and NAME_RE.match(head.strip()) and ANNO.match(pieces[0][1:-1]) and len(pieces) >= 2:
        return 'strip', pieces[1:]
    if not head.strip():
        return 'split', pieces
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--ch', default='括号', choices=list(OPEN))
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('--limit', type=int, default=6)
    a = ap.parse_args()

    op, cl = OPEN[a.ch], CLOSE[a.ch]
    L = [x for x in io.open(a.path, encoding='utf-8-sig').read().split('\n') if x.strip()]
    out, acts = [], []
    for i, x in enumerate(L, 1):
        r = split_line(x, op, cl)
        if r:
            how, pieces = r
            out.extend(pieces)
            acts.append((how, i, x, pieces))
        else:
            out.append(x)

    print('%s：拆分 %d 行｜剥人名注 %d 行｜行数 %d → %d' % (
        a.ch,
        sum(1 for t in acts if t[0] == 'split'),
        sum(1 for t in acts if t[0] == 'strip'),
        len(L), len(out)))
    if a.verbose:
        for k, (how, i, x, ps) in enumerate(acts[:a.limit]):
            print('  %-5s L%-6d %s' % (how, i, x[:80]))
            for p in ps:
                print('        → %s' % p[:80])

    if a.dry:
        print('（dry run，未写盘）')
        return 0
    if acts:
        tag = a.path.split('/')[-1][:-4]
        shutil.copy(a.path, '_bak_patch/%s.preMultiSplit' % tag)
        io.open(a.path, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(out) + '\n')
        print('已写回', a.path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
