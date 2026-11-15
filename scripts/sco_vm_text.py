#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dolly Night / ドーリィナイト（パペット 2004）—— `main.sco` 文本提取。

引擎判据（全部来自 ScrCore.dll / standard.dll，L0）：
  · `sco` 文件头：`sco\\0` @0x00 / u32 指令数 @0x04 / u32 变量表数 @0x08 /
    u32 函数表数 @0x0c / u32 字符串数 @0x10
  · 指令 = 12 字节定长记录 `[op u32][a u32][m u32]`，从 **0x18** 起；
    `n*12 + 0x18` 正好落在字符串池起点（本作 365,234 × 12 + 0x18 = 0x42e070）
  · 字符串池 = `[u32 len][len 字节 cp932]` 顺序排列，无分隔，直到 EOF
  · op 表（ScrCore.dll step_run 跳转表 @RVA 0x53d8，22 项）：
      0=load 变量值 1=push 变量引用 2=push 常量(a=1 int / a=2 字符串索引)
      3=drop 4=store 5..10=add/sub/mul/div/mod/neg 11=比较 12=(栈标记)
      13=jmp 14/15=条件跳转 16=call 脚本函数(a=入口 pc, m=实参数) 18=ret
      20=call 命令(a=命令号, 实参数＝最后压栈的 int) 21=call 内建
  · 调用约定：实参先压，**最后压一个 int＝实参数**；实参＝`st[-(n+1):-1]`
  · op20 命令号 → 名字：standard.dll 导出表（EAT）第 (a-1) 项
    （实测 str_cat/pb_settext/ctl_messagebox/tf_erase/tf_addtext 等全部吻合）

成行判据（L1，记录自定界＋交叉验证）：
  · 脚本函数 fn@12536(文本 1 条) = 向文本框追加 **一行**（内部 str_cat→tf_flush）
  · 脚本函数 fn@12911(…) = **一条消息的显示与等待**：
        实体里 tf_erase(0) → tf_addtext(缓冲) → 轮询等待循环（fn@12781/adv_click）
    ⇒ **一次 fn@12911 调用 = 一次点击 = 一个文本框**
  · 因此：两个 fn@12911 之间的所有 fn@12536 = 同一文本框内的多行 ⇒ 合并成一行
  · 行数上限 4（15,019 段里最长 4）＝ 文本框 4 行容量（pb_layout(4,24,…)），
    与"框内换行"互相印证
  · fn@8338(名字) = 独立名字窗（pb_* 重绘名牌）⇒ 说话人**剔除**
  · fn@3519 = 语音（vo/xxx.wav）、fn@2815/fn@5114/fn@2682 = 图像 ⇒ 不收

用法：
  python scripts/sco_vm_text.py <main.sco> --out <txt> [--trace] [--cmdnames <json>]
"""
import argparse
import json
import os
import struct
import sys

MAGIC = b'sco\x00'
CODE_BASE = 0x18

# ScrCore step_run 的操作码（据跳转表与各 handler 反汇编整理）
OP = {0: 'load', 1: 'ref', 2: 'const', 3: 'drop', 4: 'store', 5: 'add', 6: 'sub',
      7: 'mul', 8: 'div', 9: 'mod', 10: 'neg', 11: 'cmp', 12: 'mark', 13: 'jmp',
      14: 'jcc', 15: 'jcc2', 16: 'call', 17: 'nop', 18: 'ret', 19: 'nop',
      20: 'cmd', 21: 'bi'}


def parse_sco(path):
    blob = open(path, 'rb').read()
    if blob[:4] != MAGIC:
        raise SystemExit('不是 sco：%r' % blob[:4])
    nins, nvar, nfun, nstr = struct.unpack_from('<IIII', blob, 4)
    ins = [struct.unpack_from('<III', blob, CODE_BASE + 12 * i) for i in range(nins)]
    pool_at = CODE_BASE + 12 * nins
    strs, o = [], pool_at
    while o + 4 <= len(blob):
        n = struct.unpack_from('<I', blob, o)[0]
        if o + 4 + n > len(blob):
            break
        strs.append(blob[o + 4:o + 4 + n])
        o += 4 + n
    meta = dict(nins=nins, nvar=nvar, nfun=nfun, nstr=nstr,
                pool_at=pool_at, pool_end=o, size=len(blob), nstr_real=len(strs))
    return ins, strs, meta


def call_args(ins, i, n):
    """取第 i 条 call 的实参。

    调用约定（ScrCore op20/op16）：实参依次压栈，**最后**再压一个 int＝实参数。
    所以向前收 n+1 个 push（op2/op0/op1），去掉末尾那个计数标记。
    """
    out, j = [], i - 1
    while j >= 0 and len(out) < n + 1:
        op, a, m = ins[j]
        if op == 2:
            out.append(('const', a, m))
        elif op == 0:
            out.append(('load', a, m))
        elif op == 1:
            out.append(('ref', a, m))
        else:
            break
        j -= 1
    out.reverse()
    if len(out) == n + 1 and out[-1] == ('const', 1, n):
        return out[:-1]
    return out[:n]


def sval(strs, idx, strict=False):
    if 0 <= idx < len(strs):
        try:
            return strs[idx].decode('cp932')
        except UnicodeDecodeError:
            if strict:
                raise
            return strs[idx].decode('cp932', 'replace')
    return None


def find_entry(ins):
    """入口＝末尾 `call X; ret` 里的 X（本作 365231 `call 47439` / 365233 `ret`）。"""
    n = len(ins)
    for i in range(n - 1, -1, -1):
        op, a, m = ins[i]
        if op == 16:
            return a
    return 0


def fn_ranges(ins, entry):
    """定义区（< entry）里每个被调用函数的 [start, end) 区间＝下一个函数起点。"""
    starts = sorted({a for op, a, m in ins if op == 16 and a < entry})
    end = {}
    for k, s in enumerate(starts):
        end[s] = starts[k + 1] if k + 1 < len(starts) else entry
    return end


def interesting_fns(ins, ranges, marks, entry):
    """定义区里「直接或间接会显示文本」的函数集合（不动点迭代）。

    只判「直接含 marks」会漏掉纯转发的包装函数：本作 fn@45499→fn@14514、
    fn@45692→fn@14514 都不直接含文本调用。
    """
    direct = set()
    called = {}
    for s, e in ranges.items():
        cs = set()
        for i in range(s, min(e, len(ins))):
            op, a, m = ins[i]
            if op == 16:
                if a in marks:
                    direct.add(s)
                elif a < entry and a in ranges:
                    cs.add(a)
        called[s] = cs
    good = set(direct)
    changed = True
    while changed:
        changed = False
        for s, cs in called.items():
            if s not in good and (cs & good):
                good.add(s)
                changed = True
    return good


def extract(ins, strs, text_fn=12536, box_fn=12911, name_fn=8338, trace=False,
            entry=None):
    """按**执行顺序**取文本框。

    边界（L1）：文本段在 **fn@12911（消息显示＋等待）** 与 **fn@8338（换名＝新消息）**
    处截断。两处都算：本作有 `[换名][4 行][换名（同名）][2 行][12911]` 的写法，
    只认 12911 会并出 6 行（超出 4 行容量），加 8338 后分布恢复 1..4。

    顺序（L0）：本作前 47,439 条指令是**函数定义区**，主脚本从 `call 47439` 的入口
    线性执行到末尾。故按「主区线性 + 遇定义区函数则原地下钻」还原播放顺序；
    否则会把共通场景（fn@14514，被 2 处调用）排到全篇最前。
    """
    if entry is None:
        entry = find_entry(ins)
    boxes, cur, speaker = [], [], None
    events = []
    active = set()

    def close():
        nonlocal cur, speaker
        if cur:
            boxes.append((speaker, cur))
            events.append(('box', None, speaker))
            cur = []

    def handle(op, a, m, i):
        nonlocal speaker
        if a == name_fn:
            close()
            args = call_args(ins, i, m)
            if len(args) == 1 and args[0][0] == 'const' and args[0][1] == 2:
                speaker = sval(strs, args[0][2])
            return True
        if a == text_fn:
            args = call_args(ins, i, m)
            if len(args) == 1 and args[0][0] == 'const' and args[0][1] == 2:
                t = sval(strs, args[0][2])
                if t is not None:
                    cur.append(t)
                    events.append(('line', i, t))
            return True
        if a == box_fn:
            close()
            return True
        return False

    def walk(pc, depth):
        while 0 <= pc < len(ins) and pc not in seen:
            seen.add(pc)
            op, a, m = ins[pc]
            if op == 16:
                if handle(op, a, m, pc):
                    pc += 1
                    continue
                if a < entry and depth < 5 and a not in seen:
                    walk(a, depth + 1)
                pc += 1
                continue
            if op == 13:                      # jmp：直接改 pc
                if a in seen:
                    return
                pc = a
                continue
            if op in (14, 15):                # 条件跳转：先走下一条，跳转目标排队
                if a not in seen:
                    pending.append((a, depth))
                pc += 1
                continue
            if op == 18:                      # ret
                return
            pc += 1

    seen = set()
    pending = [(entry, 0)]
    while pending:
        pc, d = pending.pop(0)
        walk(pc, d)
    close()
    if trace:
        return boxes, events
    return boxes, None


def to_line(parts):
    """框内换行合并：去掉每段末尾的 \\n（若有）后直接相连，不增删任何其它字符。"""
    out = []
    for p in parts:
        if p.endswith('\n'):
            p = p[:-1]
        out.append(p)
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sco')
    ap.add_argument('--out')
    ap.add_argument('--trace', action='store_true')
    ap.add_argument('--cmdnames', default='')
    ap.add_argument('--emit-names', action='store_true', help='调试：把说话人一并写出')
    a = ap.parse_args()

    ins, strs, meta = parse_sco(a.sco)
    print('指令 %d 条（0x18..0x%x）  字符串 %d 条（0x%x..0x%x）  size=0x%x'
          % (meta['nins'], meta['pool_at'], meta['nstr_real'], meta['pool_at'],
             meta['pool_end'], meta['size']))
    if meta['nstr_real'] != meta['nstr']:
        print('  ⚠ 头声明字符串数 %d ≠ 实际 %d' % (meta['nstr'], meta['nstr_real']))

    boxes, events = extract(ins, strs, trace=a.trace)
    nline = sum(len(b[1]) for b in boxes)
    print('文本框 %d 个 / 原始显示行 %d 条 / 合并后 %d 行' % (len(boxes), nline, len(boxes)))
    from collections import Counter
    c = Counter(len(b[1]) for b in boxes)
    print('每框行数分布:', dict(sorted(c.items())))
    spk = Counter(b[0] for b in boxes)
    print('说话人（独立名字窗，仅报告用）种数 %d，前 12：%s'
          % (len(spk), ', '.join('%s×%d' % (k, v) for k, v in spk.most_common(12))))

    lines = []
    for sp, parts in boxes:
        t = to_line(parts)
        if a.emit_names and sp:
            t = '【%s】%s' % (sp, t)
        lines.append(t)

    if a.out:
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('写出', a.out, len(lines), '行')
    if a.trace and events:
        print('--- 事件前 40 ---')
        for e in events[:40]:
            print('  ', e[0], e[1], (e[2] or '')[:40])


if __name__ == '__main__':
    main()
