#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orfre/DCVM 线性走链器：用于恢复「一次点击 = 一行」的文本序。

依据（已实证）：
  - 显示语句形态（8 字节）：PUSHIB <池id>; STR; PUSHIB a; PUSHIB <全局函数id>; CALL|PCALL
  - 跳转 = PUSHIW <imm>; JMP|JMPT|JMPF ，目标 = code[imm + 0x14]
  - `PUSHIW <下一行addr>; JMPF` 的语义 ≈「若条件成立则跳到下一行」⇒ 一律取目标可沿链直走

策略：从「每个显示语句」各起走一次，取「覆盖去重文本最多」的一条作为该场正文。
用法: python scripts/orfleur_vm.py <chunk.bin> [--dump N] [--all]
"""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orfleur_extract as OE

OP_STR = 55
OP_PUSHIW, OP_PUSHIB = 48, 50
OP_CALL, OP_PCALL = 11, 71
OP_RET, OP_END = 12, 8
JUMPS = (45, 46, 47)
BASE = 0x14


def load(path):
    data = open(path, 'rb').read()
    S = OE.secs(data)
    co, cs = S['CODE']; code = data[co+8:co+cs]
    so, ss = S['STR']; parts = data[so+8:so+ss].split(b'\0')
    return code, parts, S


def istext(parts, k):
    if not (0 < k < len(parts)):
        return False
    try:
        t = parts[k].decode('cp932')
    except Exception:
        return False
    return len(t.strip()) > 3 and any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff'
                                      for c in t)


def display_stmts(ops, parts):
    """返回 {offset: pool_id}（仅 8 字节显示语句，且文本像日文）"""
    m = {}
    for i in range(4, len(ops)):
        off, op, arg = ops[i]
        if op not in (OP_CALL, OP_PCALL):
            continue
        if ops[i-1][1] == OP_PUSHIB and ops[i-2][1] == OP_PUSHIB and \
           ops[i-3][1] == OP_STR and ops[i-4][1] == OP_PUSHIB:
            k = ops[i-4][2]
            if istext(parts, k):
                m[ops[i-4][0]] = k
    return m


def walk(ops, off2i, stmts, start, max_steps=400000):
    i = off2i.get(start)
    if i is None:
        return []
    out = []; steps = 0
    seen_off = collections.Counter()
    while 0 <= i < len(ops) and steps < max_steps:
        steps += 1
        off, op, arg = ops[i]
        seen_off[off] += 1
        if seen_off[off] > 2:
            break
        if off in stmts:
            out.append(stmts[off])
        if op == OP_PUSHIW and i+1 < len(ops) and ops[i+1][1] in JUMPS:
            t = arg + BASE
            j = off2i.get(t)
            if j is None or t <= off:      # 只跟随前向跳转（排除循环回跳）
                i += 1
                continue
            i = j
            continue
        if op == OP_RET:
            break
        i += 1
    return out


def best_walk(code, parts, verbose=False):
    ops = OE.vm_ops(code)
    off2i = {o: i for i, (o, _, _) in enumerate(ops)}
    stmts = display_stmts(ops, parts)
    cand = []
    for start in sorted(stmts):
        w = walk(ops, off2i, stmts, start)
        if not w:
            continue
        # 去重相邻
        d = [k for j, k in enumerate(w) if j == 0 or k != w[j-1]]
        cand.append((len(set(d)), len(d), start, d))
    cand.sort(reverse=True)
    return ops, stmts, cand


def main():
    path = sys.argv[1]
    code, parts, S = load(path)
    ops, stmts, cand = best_walk(code, parts)
    print("display stmts=%d  code=%#x  candidates=%d" % (len(stmts), len(code), len(cand)))
    if '--all' in sys.argv:
        for nd, nl, st, d in cand[:8]:
            print("  start=%#08x distinct=%d lines=%d" % (st, nd, nl))
    if not cand:
        return
    nd, nl, st, d = cand[0]
    print("BEST start=%#08x distinct=%d lines=%d" % (st, nd, nl))
    N = int(sys.argv[sys.argv.index('--dump')+1]) if '--dump' in sys.argv else 40
    for k in d[:N]:
        if not (0 <= k < len(parts)):
            continue
        try:
            t = parts[k].decode('cp932')
        except Exception:
            continue
        print(OE.hankaku_to_hiragana(OE.TAG_RE.sub('', t)))


if __name__ == '__main__':
    main()
