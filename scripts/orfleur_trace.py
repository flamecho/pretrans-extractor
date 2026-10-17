#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orfre/DCVM 执行序追踪（CFG 走块 + 调用捕获）——用于确定「一次点击=一行」的显示序。

用法: python scripts/orfleur_trace.py <chunk.bin> [--dump N] [--calls]
  --dump N   顺序打印前 N 条「带文本参数的调用」
  --calls    打印全部调用目标统计
"""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orfleur_extract as OE

OP_JMP, OP_JMPT, OP_JMPF = 45, 46, 47
OP_PUSHIW, OP_PUSHIH, OP_PUSHIB, OP_PUSHNIH, OP_PUSHNIB = 48, 49, 50, 51, 52
OP_PUSHR = 54
OP_STR, OP_PUSHRET = 55, 56
OP_CALL, OP_PCALL = 11, 71
OP_RET, OP_END, OP_ENTRY = 12, 8, 7
OP_SP = 63
OP_LD, OP_ST = 61, 62
PUSHES = (OP_PUSHIW, OP_PUSHIH, OP_PUSHIB, OP_PUSHNIH, OP_PUSHNIB, OP_PUSHR)
JUMPS = (OP_JMP, OP_JMPT, OP_JMPF)
CODE_BASE = 0x14          # 跳转目标 / FTBL 局部地址的共同基准
NAME = ("ABORT NOP TYPE TYPE_POP INIT TERM LOOP ENTRY END IS_NULL_TYPE SYSCALL CALL RET ADD SUB "
        "MUL DIV MOD NEG INV AND OR XOR NOT LS RS POST_INC PRE_INC ADDA SUBA MULA DIVA MODA ANDA "
        "ORA XORA LSA RSA LNOT EQ NEQ LE LEQ GE GEQ JMP JMPT JMPF PUSHIW PUSHIH PUSHIB PUSHNIH "
        "PUSHNIB PUSH_NULL PUSHR STR PUSHRET VAR_AUTO VAR_LOCAL VAR_ARG VAR_GLOBAL LD ST SP POP "
        "SWAP DUP RTOI ITOR ENTRY_INFO PSETUP PCALL CHECK_STACK_BEGIN CHECK_STACK_END CHECK_INDEX "
        "LINE FILE LDRET VAR_PERSISTENT VAR_INITIALIZE").split()


def load(path):
    data = open(path, 'rb').read()
    S = OE.secs(data)
    co, cs = S['CODE']; code = data[co+8:co+cs]
    so, ss = S['STR']; parts = data[so+8:so+ss].split(b'\0')
    ft = []
    if 'FTBL' in S:
        fo, fs = S['FTBL']; n = (fs-8)//12
        for k in range(n):
            o = fo+8+12*k
            a = int.from_bytes(data[o:o+4], 'little')
            nid = int.from_bytes(data[o+4:o+8], 'little')
            nm = parts[nid].decode('cp932', 'replace') if nid < len(parts) else '?'
            ft.append((a, nm))
    return code, parts, ft


def build(ops):
    """返回 (blocks, block_of_off)。block = (start_i, end_i_exclusive, edges)"""
    off2i = {off: i for i, (off, _, _) in enumerate(ops)}
    n = len(ops)
    leaders = set([ops[0][0]] if ops else [])
    for i, (off, op, arg) in enumerate(ops):
        nxt = ops[i+1][0] if i+1 < n else None
        if op in JUMPS:
            if i >= 1 and ops[i-1][1] == OP_PUSHIW:
                t = ops[i-1][2] + CODE_BASE
                if t in off2i:
                    leaders.add(t)
            if nxt is not None:
                leaders.add(nxt)
        elif op in (OP_RET, OP_END) and nxt is not None:
            leaders.add(nxt)
    leaders = sorted(leaders)
    blocks = []
    for bi, st in enumerate(leaders):
        end = leaders[bi+1] if bi+1 < len(leaders) else n
        si = off2i[st]
        ei = off2i[end] if end in off2i else n
        blocks.append([si, ei, None])
    # edges
    sec = {}
    for bi, (si, ei, _) in enumerate(blocks):
        for i in range(si, ei):
            sec[ops[i][0]] = bi
    for bi, (si, ei, _) in enumerate(blocks):
        edges = []
        last = ops[ei-1]
        if last[1] in JUMPS:
            if ei-2 >= si and ops[ei-2][1] == OP_PUSHIW:
                t = ops[ei-2][2] + CODE_BASE
                if t in sec:
                    edges.append(sec[t])
            if last[1] in (OP_JMPT, OP_JMPF):
                if ei < n:
                    edges.append(sec.get(ops[ei][0]))
        elif last[1] not in (OP_RET, OP_END):
            if ei < n:
                edges.append(sec.get(ops[ei][0]))
        blocks[bi][2] = [e for e in edges if e is not None]
    return blocks, sec


def span(b, a):
    return a.encode('cp932', 'replace') if isinstance(a, str) else a


def trace(path, maxsteps=2000000):
    code, parts, ft = load(path)
    ops = OE.vm_ops(code)
    blocks, sec = build(ops)
    # DFS 预序
    # 入口 = 体量最大的块（跳过 ENTRY;PUSHIB;RET;END 桩表）
    entry = max(range(len(blocks)), key=lambda b: blocks[b][1] - blocks[b][0])
    order = []
    seen = set()
    stack = [entry]
    while stack:
        bi = stack.pop()
        if bi in seen or bi >= len(blocks):
            continue
        seen.add(bi)
        order.append(bi)
        # 先 fallthrough 后 target 更像源码序
        for e in reversed(blocks[bi][2]):
            if e not in seen:
                stack.append(e)
    stmts = []
    for bi in order:
        si, ei, _ = blocks[bi]
        buf = []
        for i in range(si, ei):
            off, op, arg = ops[i]
            if op in PUSHES:
                buf.append(('int', arg))
            elif op == OP_STR:
                if buf and buf[-1][0] == 'int':
                    k = buf[-1][1]
                    ok = isinstance(k, int) and 0 <= k < len(parts)
                    buf[-1] = ('str', parts[k].decode('cp932', 'replace') if ok else '?')
            elif op in (OP_CALL, OP_PCALL, 10):
                fid = buf[-1][1] if buf and buf[-1][0] == 'int' else None
                args = buf[:-1]
                nm = ft[fid][1] if isinstance(fid, int) and 0 <= fid < len(ft) else '?'
                txt = [v for kd, v in args if kd == 'str']
                stmts.append((off, NAME[op], fid, nm, args, txt))
                buf = []
            else:
                buf = []
    return ops, parts, ft, blocks, order, stmts


def main():
    path = sys.argv[1]
    ops, parts, ft, blocks, order, stmts = trace(path)
    print("ops=%d blocks=%d visited=%d stmts=%d" % (len(ops), len(blocks), len(order), len(stmts)))
    if '--calls' in sys.argv:
        c = collections.Counter((s[3], s[1]) for s in stmts)
        for (nm, op), v in c.most_common(25):
            print("   %-30s %-6s %d" % (nm[:30], op, v))
    if '--func' in sys.argv:
        want = sys.argv[sys.argv.index('--func')+1]
        rng = range(len(ft))
        n = 0
        for off, op, fid, nm, args, txt in stmts:
            hit = (nm == want) if not want.isdigit() else (fid == int(want))
            if not hit:
                continue
            tt = [t for t in txt if t and sum(1 for ch in t if '\u3040' <= ch <= '\u30ff'
                                              or '\u4e00' <= ch <= '\u9fff') >= 4]
            if not tt:
                continue
            print("%s" % (tt[0][:78],))
            n += 1
    elif '--dump' in sys.argv:
        N = int(sys.argv[sys.argv.index('--dump')+1])
        n = 0
        for off, op, fid, nm, args, txt in stmts:
            tt = [t for t in txt if t and sum(1 for ch in t if '\u3040' <= ch <= '\u30ff'
                                              or '\u4e00' <= ch <= '\u9fff') >= 4]
            if not tt:
                continue
            print("%#08x %-6s %-26s | %s" % (off, op, nm[:26], tt[0][:70]))
            n += 1
            if n >= N:
                break


if __name__ == '__main__':
    main()
