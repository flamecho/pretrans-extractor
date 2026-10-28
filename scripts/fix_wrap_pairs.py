# -*- coding: utf-8 -*-
"""框内软换行被切成两行的修复（跨行续行收拢 / 缺引号补齐）。

成因：引擎文本框内的软换行，提取时被当成独立行输出，于是出现
  `「そこまで言うんだ、きっと本心なんだろう。`   ← 「 开、无闭
  `……ありがとう、フィン」`                       ← 只有闭
用户给的两个探针（`(?!^)「` / `(?<!^)(」)(?!$)`）指的就是这类位置。
本工具按**行形态**判定，四种动作，逐条可列清单：

  join     行余 `op` 且下一行**不以 op 开头** ⇒ 视为续行，并成一行（可多行）
  joinup   行余 `cl` 且上一行**不以 cl 结尾** ⇒ 视为上一行的尾巴，并到上一行
  close    行余 `op` 但下一行**以 op 开头**   ⇒ 前框缺闭合，补一个 cl（--allow-close）
  trim     行余 `cl` 但上一行**以 cl 结尾**   ⇒ 后框缺开引号，删掉多余 cl（--allow-trim）

保护：字数守恒校验（去符号/空白后逐字相等，close/trim 除外时单独记数），失败即中止。
默认只做 join / joinup（不动原文），close / trim 需显式开启。

用法：
  python scripts/fix_wrap_pairs.py <txt> --ch 引号 [--allow-close] [--allow-trim] [--dry] [-v]
"""
import argparse
import io
import re
import shutil
import sys

OPEN = '「（(『'
SETS = {'引号': ('「', '」'), '括号': ('（', '）'), '角': ('『', '』')}


def fix(L, op, cl, allow_close, allow_trim):
    out, acts = [], []
    n = len(L)
    i = 0
    while i < n:
        x = L[i]
        o, c = x.count(op), x.count(cl)
        if o > c:
            nxt = L[i + 1] if i + 1 < n else ''
            if nxt and not nxt.startswith(op) and nxt.count(cl) > nxt.count(op):
                j, merged = i, x
                while merged.count(op) > merged.count(cl) and j + 1 < n and not L[j + 1].startswith(op):
                    j += 1
                    merged += L[j]
                if merged.count(op) == merged.count(cl) and j > i:
                    out.append(merged)
                    acts.append(('join', i + 1, j + 1))
                    i = j + 1
                    continue
            if allow_close and o - c == 1:
                out.append(x + cl)
                acts.append(('close', i + 1, 0))
                i += 1
                continue
            acts.append(('leave', i + 1, 0))
            out.append(x)
            i += 1
            continue

        if c > o:
            # 2026-10-27 修：joinup 的前提是「**上一行确实未闭合**」（op > cl）。
            # 原判据写成 `cl >= op`（即上一行**平衡**）⇒ 会把「地の文 + 独立括弧段」误并成一行。
            # 实证：テミラーナ L23795 —— 3 条独立记录（源记录 23762/23763/23764）被并成 147 字一行，
            # 且第 3 条源侧笔误 `（…？」`（开「（」用「」」收）触发 c>o，随后 trim 删掉「」」⇒ 括号失衡。
            if out and out[-1].count(op) > out[-1].count(cl) and not out[-1].endswith(cl):
                out[-1] = out[-1] + x
                acts.append(('joinup', i, i + 1))
                i += 1
                continue
            if allow_trim and c - o == 1 and x.endswith(cl):
                out.append(x[:-1])
                acts.append(('trim', i + 1, 0))
                i += 1
                continue
            acts.append(('leave', i + 1, 0))
            out.append(x)
            i += 1
            continue

        out.append(x)
        i += 1
    return out, acts



def repair(L, op, cl):
    """差恰为 1 时的修复。多出的闭符号按行首形态分流：
    - 行首是开引号/开括号 ⇒ 孤立多余，删掉；
    - 行首是地の文（假名）⇒ 视为「叙述 + 台词尾巴」两框合并，在最后一个句读处**拆行并给后半补开引号**；
    - 找不到句读 ⇒ 删。"""
    acts = []
    i = len(L) - 1
    while i >= 0:
        x = L[i]
        o, c = x.count(op), x.count(cl)
        if o == c + 1 and x.startswith(op):
            L[i] = x + cl
            acts.append(('close', i + 1, x[-26:], L[i][-26:]))
        elif c == o + 1:
            if x.endswith(cl) and x[0] in OPEN:
                L[i] = x[:-1]
                acts.append(('trim', i + 1, x[-26:], L[i][-26:]))
            elif x.endswith(cl) and op not in x:
                body = x[:-1]
                k = max(body.rfind('。'), body.rfind('！'), body.rfind('？'), body.rfind('…'))
                if 0 <= k < len(body) - 2:
                    L[i] = body[:k + 1]
                    L.insert(i + 1, op + body[k + 1:] + cl)
                    acts.append(('split', i + 1, x[-40:], L[i][-26:] + ' / ' + op + body[k + 1:k + 20]))
                else:
                    L[i] = body
                    acts.append(('trim', i + 1, x[-26:], L[i][-26:]))
            else:
                k = x.rfind(cl)
                L[i] = x[:k] + x[k + 1:]
                acts.append(('trimmid', i + 1, x[max(0, k - 16):k + 12], L[i][max(0, k - 16):k + 12]))
        elif o > c + 1:
            acts.append(('multi_o', i + 1, x[-26:], ''))
        elif c > o + 1:
            acts.append(('multi_c', i + 1, x[-26:], ''))
        i -= 1
    return acts


def core(s):
    return re.sub(r'[\s\u3000「」（）『』]', '', s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--ch', default='引号', choices=list(SETS))
    ap.add_argument('--repair', action='store_true', help='差恰为 1 时补齐/删除符号')
    ap.add_argument('--allow-close', action='store_true')
    ap.add_argument('--allow-trim', action='store_true')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('--limit', type=int, default=6)
    a = ap.parse_args()

    op, cl = SETS[a.ch]
    raw = io.open(a.path, encoding='utf-8-sig').read()
    L = [x for x in raw.split('\n') if x.strip()]
    out, acts = fix(L, op, cl, a.allow_close, a.allow_trim)
    if a.repair:
        acts += repair(out, op, cl)

    from collections import Counter
    cnt = Counter(a[0] for a in acts)
    print('%s：%s' % (a.ch, dict(cnt)))

    # 字数守恒：join/joinup 不改变字符；close/trim 会增删符号 ⇒ 用去符号后的核心比对
    if core(''.join(out)) != core(''.join(L)):
        print('!! 核心字数不守恒，中止')
        return 2

    if a.verbose:
        k = 0
        for it in acts:
            t, i = it[0], it[1]
            if t in ('close', 'trim', 'trimmid') and k < a.limit:
                print('  %-7s L%d' % (t, i))
                print('     旧| %s' % str(it[2]))
                print('     新| %s' % str(it[3]))
                k += 1

    print('行数 %d → %d（净 %+d）' % (len(L), len(out), len(out) - len(L)))
    if a.dry:
        print('（dry run，未写盘）')
        return 0
    if len(out) != len(L) or ''.join(out) != ''.join(L):
        tag = a.path.split('/')[-1][:-4]
        shutil.copy(a.path, '_bak_patch/%s.preWrapMerge' % tag)
        io.open(a.path, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(out) + '\n')
        print('已写回', a.path)
    else:
        print('无改动')
    return 0


if __name__ == '__main__':
    sys.exit(main())
