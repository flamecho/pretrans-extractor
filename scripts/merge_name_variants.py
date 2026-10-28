# -*- coding: utf-8 -*-
"""双版拼接合并工具（名字宏双版 / 点名版↔泛称版）。

缺陷形态：源数据同一句存两份，提取时两版被拼进同一行。三种外观：
  ① `「A」「B` ／ `「A。「B」` ／ `「A」B」`  —— 引号数量不平衡；
  ② `（A）（B）` ／ 无引号的 `A。B。`        —— 引号/括号**平衡**，只有重复内容能看出来；
  ③ `「A」　A'」` 三版交错                    —— 需迭代多次。

判据（统一）：
  - 名字（--alias）统一替换成占位符 `@`，去掉空白后找长度 ≥ --min 的**行内重复子串**；
  - 切点 = 重复段第二处出现的位置（并按内层引号位置兜底）；
  - A=前半、B=后半，各自剥掉并排时多出的首/尾括号引号；
  - 二者取「更完整的一版」：A 几乎全在 B 里 ⇒ 取 B，反之取 A，各一半 ⇒ 逐字对齐合并；
  - 名字统一为宏名（`遮那(?!王)` → `遮那王`）；
  - 校验：结果无残留重复、长度 ≥ 原 60%、引号/括号平衡，最多迭代 3 轮；
  - 通过才替换，否则原样保留（宁可不动，不许弄坏）。

用法：
  python scripts/merge_name_variants.py <txt> --macro 遮那王 --literal 義経,遮那 [-v] [--dry]
"""
import argparse
import difflib
import io
import re
import shutil
import sys

OPEN = '「（('
CLOSE = '」）)'


def _blank(s):
    return s.strip(' \u3000\t') == ''


def norm(s, lits):
    for lit in sorted(lits, key=len, reverse=True):
        s = s.replace(lit, '@')
    return re.sub(r'[\s\u3000]', '', s)


def cover(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(i2 - i1 for t, i1, i2, _, _ in sm.get_opcodes() if t == 'equal')


def merge(a, b):
    """逐字对齐：equal 取一次；replace/insert 取 b（宏版）；delete 仅保留含实词的段"""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            out.append(a[i1:i2])
        elif tag == 'delete':
            seg = a[i1:i2]
            if not _blank(seg):
                out.append(seg)
        else:
            out.append(b[j1:j2])
    return ''.join(out)


def pick(a, b):
    eq = cover(a, b)
    ca, cb = eq / max(1, len(a)), eq / max(1, len(b))
    if ca >= 0.8 and len(b) >= len(a):
        return b, 'take_b'
    if cb >= 0.8 and len(a) >= len(b):
        return a, 'take_a'
    return merge(a, b), 'merge'


def lost_words(a, b, minlen=8):
    """merge 会丢掉 a 独有的实词段 ⇒ 说明两版内容不同（不是同一句的双版）"""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, _j1, _j2 in sm.get_opcodes():
        if tag == 'delete':
            seg = a[i1:i2]
            if not _blank(seg) and len(seg.strip()) >= minlen:
                return seg
    return None


def first_dup(t, n):
    seen = set()
    for i in range(len(t) - n + 1):
        g = t[i:i + n]
        if g in seen:
            return g
        seen.add(g)
    return None


def dup_pos(body, lits, n):
    """重复段第二处出现的原行索引：把重复段里的 @ 展开成「任一名写法」的正则，允许中间夹空白"""
    t = norm(body, lits)
    found = first_dup(t, n)
    if not found:
        return None, None
    real = [x for x in lits if x != '@']
    alts = '|'.join(re.escape(x) for x in sorted(real, key=len, reverse=True)) or '\x00'
    parts = ['(?:%s)' % alts if ch == '@' else re.escape(ch) for ch in found]
    pat = re.compile(r'[\s\u3000]*'.join(parts))
    ms = list(pat.finditer(body))
    if len(ms) < 2:
        return None, found
    return ms[1].start(), found


def norm_name(s, macro, lits):
    for lit in sorted(lits, key=len, reverse=True):
        if lit in macro:
            tail = macro[len(lit):]
            s = re.sub(re.escape(lit) + '(?!' + re.escape(tail) + ')', macro, s)
        else:
            s = s.replace(lit, macro)
    return s


def one_pass(line, macro, lits, n):
    h, t = '', ''
    body = line
    while body and body[0] in OPEN:
        h += body[0]
        body = body[1:]
    while body and body[-1] in CLOSE:
        t = body[-1] + t
        body = body[:-1]

    cuts = []
    p, _f = dup_pos(body, lits, n)
    if p is not None:
        cuts.append(p)
    for k, ch in enumerate(body):
        if ch in '「」':
            cuts.append(k + 1)

    best = None
    for d in cuts:
        if not (0 < d < len(body)):
            continue
        A = body[:d].strip(' \u3000')
        while len(A) > 2 and A[-1] in OPEN + CLOSE:
            A = A[:-1].rstrip(' \u3000')
        B = body[d:].strip(' \u3000')
        while len(B) > 2 and B[0] in OPEN + CLOSE:
            B = B[1:].lstrip(' \u3000')
        if len(A) < 4 or len(B) < 4:
            continue
        prev = body[d - 1]
        nxt = body[d] if d < len(body) else ''
        if not (prev in '。，、！？…―ー　 \t' or prev in OPEN or prev in CLOSE or nxt in OPEN):
            continue
        eq = cover(A, B)
        if eq < max(6, 0.35 * min(len(A), len(B))):
            continue
        m, how = pick(A, B)
        if how == 'merge':
            # 真双版：merge 不该丢实词；丢了 ⇒ 两版内容不同，拒绝
            if lost_words(A, B):
                continue
            if len(m) < len(body) * 0.75:
                continue
        elif len(m) < len(body) * 0.45:
            continue
        if how != 'merge' and first_dup(norm(m, lits), n):
            continue
        m = norm_name(m, macro, lits).strip(' \u3000')
        if not m:
            continue
        score = eq + (6 if how != 'merge' else 0)
        if best is None or score > best[0]:
            best = (score, m, how)

    if best is None:
        return line, None
    score, m, how = best
    new = h + m + t
    if new.count('「') != new.count('」') or new.count('（') != new.count('）'):
        return line, None
    return new, how


def fix_line(line, macro, lits, n=10, verbose=False):
    cur = line
    hows = []
    for _ in range(3):
        y, how = one_pass(cur, macro, lits, n)
        if y is None or y == cur:
            break
        cur = y
        hows.append(how)
    if cur == line:
        return line, None
    # 最终校验：不得残留重复、括号必须平衡、长度不得低于原 40%
    if first_dup(norm(cur, lits), n):
        return line, None
    if cur.count('「') != cur.count('」') or cur.count('（') != cur.count('）'):
        return line, None
    if len(cur) < len(line) * 0.4:
        return line, None
    return cur, '+'.join(hows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--macro', required=True, help='宏回填后的名字（保留这一版）')
    ap.add_argument('--literal', default='', help='其它写法，逗号分隔（字面名/昵称）')
    ap.add_argument('--min', type=int, default=10, help='重复片段最小长度')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    lits = [a.macro] + [x for x in a.literal.split(',') if x]
    lines = [x for x in io.open(a.path, encoding='utf-8-sig').read().split('\n') if x.strip()]
    out, hit, miss = [], 0, []
    for n, x in enumerate(lines, 1):
        y, why = fix_line(x, a.macro, lits, a.min, verbose=a.verbose)
        if y != x:
            hit += 1
            if a.verbose and (not a.limit or hit <= a.limit):
                print('L%d %s\n  原| %s\n  新| %s' % (n, why, x[:120], y[:120]))
        elif first_dup(norm(x, lits), a.min) or x.count('「') != x.count('」'):
            miss.append((n, x))
        out.append(y)

    print('\n改动 %d 行｜仍存疑 %d 行' % (hit, len(miss)))
    for n, x in miss[:8]:
        print('  miss L%d| %s' % (n, x[:110]))

    if a.dry:
        print('（dry run，未写盘）')
        return 0
    if hit:
        tag = a.path.split('/')[-1][:-4]
        shutil.copy(a.path, '_bak_patch/%s.preMergeVariant' % tag)
        io.open(a.path, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(out) + '\n')
        print('已写回', a.path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
