# -*- coding: utf-8 -*-
"""遥かなる時空の中で6 DX —— 变体分支后处理：保留「默认名版」，删除「不含名字/泛指」的替代句。

背景：游戏对同一句存储多个运行时变体（名字版 / 泛指版），引擎按条件二选一。
提取器按「记录=行」全部输出，导致相邻出现两句。

本工具只处理**名字/呼称类**的明确对：
  对相邻两行 (A,B)，同时满足
    1) 去标点后的覆盖率 coverage(A,B) >= 0.85   （同一句的改写）
    2) 差异片段中，A 含主人公名（高塚梓/高塚/梓），B 不含
    3) A 的差异片段不含其他角色名（否则是「同行成员」分支，保留）
    4) B 的差异片段含泛指词（部屋/名前/患者/神子）
  → 删除 B（泛指/无名字版）。
其余近似对（昼夜、同行成员、不同角色台词、标点微差）一律不动。

用法: haruka6_dedup.py <in.txt> <out.txt> [<report.md>]
"""
import io, re, sys, difflib

HERO = ['高塚梓', '高塚', '梓']
OTHER_CHARS = ['ダリウス', 'コハク', '秋兵', 'ルード', '政虎', '虎', '九段', '村雨',
               '千代', '清四郎', '有馬', '駒野', '尚哉', 'カグツチ', '菊', '牡丹']
GENERIC = ['部屋', '名前', '患者', '神子']
PUNCT = re.compile(r'[、。．，…‥「」『』（）()!?！？\s\u3000]')

def norm(s):
    return PUNCT.sub('', s)

def cov(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb: return 0.0
    sm = difflib.SequenceMatcher(None, na, nb)
    m = sum(bl.size for bl in sm.get_matching_blocks())
    return m / min(len(na), len(nb))

def spans(a, b):
    sm = difflib.SequenceMatcher(None, a, b)
    A, B = [], []
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t != 'equal':
            A.append(a[i1:i2]); B.append(b[j1:j2])
    return ''.join(A), ''.join(B)

def process(lines):
    drop = {}
    for i in range(len(lines) - 1):
        a, b = lines[i], lines[i + 1]
        if not a or not b or len(a) < 5 or len(b) < 5: continue
        if cov(a, b) < 0.72: continue
        sa, sb = spans(a, b)
        a_hero = any(h in sa for h in HERO)
        b_hero = any(h in sb for h in HERO)
        if a_hero == b_hero: continue
        named_span, other_span = (sa, sb) if a_hero else (sb, sa)
        if any(o in named_span for o in OTHER_CHARS): continue      # 同行成员分支
        if not any(g in other_span for g in GENERIC): continue      # 泛指词
        drop[i + 1] = (i + 1, a, b)                                 # 删 B
    return drop

def main():
    inp, outp = sys.argv[1], sys.argv[2]
    rep = sys.argv[3] if len(sys.argv) > 3 else None
    raw = open(inp, 'rb').read()
    lines = raw.decode('utf-8-sig').split('\n')
    drop = process(lines)
    out = [l for k, l in enumerate(lines) if k not in drop]
    io.open(outp, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(out))
    print(f'{inp}: 删除 {len(drop)} 行 -> {outp}')
    for k in sorted(drop):
        _, a, b = drop[k]
        print(f'  行{k+1}: 删「{b}」  (保留「{a}」)')
    if rep:
        with io.open(rep, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write(f'# 变体分支处理记录 — {inp}\n\n')
            f.write(f'删除 {len(drop)} 行（保留默认名版）：\n\n')
            for k in sorted(drop):
                _, a, b = drop[k]
                f.write(f'- 行 {k+1}\n  - 保留：{a}\n  - 删除：{b}\n')
        print('report ->', rep)

if __name__ == '__main__':
    main()
