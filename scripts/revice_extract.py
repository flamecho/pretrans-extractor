# -*- coding: utf-8 -*-
"""RE:VICE[D]  (PSV, PCSG00382, Otomate / Idea Factory)  剧本文本提取

容器链路
  VPK (zip) -> data/GAME.cpk  [CRI CPK, CRILAYLA]
  CPK 内 script/1-scenario/*.DAT (82) = 正文;  0-init/*.DAT = 系统初始化(无正文)
  script/2-scene/*.DAT (69) = 场景 stub(仅 '\u3000') -> 排除
  脚本格式 = STCM2L (Idea Factory 系, PSV 变体)

STCM2L (PSV) 结构 —— 与 Norn9 同族，但 opcode 常量不同、文本编码为 CP932
  0x00  'STCM2L <date>\0..'  0x20 export_addr  0x24 ?  0x28 ?  0x2c collection_addr
  0x50  'GLOBAL_DATA\0'  ...  'CODE_START_\0' (+12) -> 指令流
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length] + nparams*[p0,p1,p2]
         + data (p0 为指令内局部指针 -> [0][L/4][1][L][cp932 text][pad])

  归一化 opcode（全 82 文件稳定）：
      0x4ba  push 文本片段；空串（[0][1][1][4]+4×0）= 换框符     0x4bc  push 人名(丢弃)
      0x4cf  选项      0x4bb  换框/等待点击 (np=0,len=16)      0x6  goto (builtin)
      0x41c  按名访问变量/资源的通用 op（param0 = 名：'switch' / 'res_*' / 'XX好感度' / '覚醒度'…）
             ★ 它出现在两条文本之间 ⇒ 断框（其后所跟状态 op 0x457/0xa538 或新 NAME 属「下一框」）
      is_call==1 且 op∈{0xb9bc,0x19c8c} = 显示文本的辅助函数调用
         0xb9bc: np=8 恒等，参数分两组 [id][文本…][id] 互斥变体(直写名 / #Name[1])
         0x19c8c: np=2，p0=文本、p1=控制字节

  ★ 断框判据（一次点击=一行）＝以下任一，**全部为字节码层证据**：
      ① 0x4bb（换框/等待点击）      ② 空文本记录 0x4ba
      ③ 0x4bc 人名札（新框起点）    ④ 0x41c 变量访问 op（换框点的编译产物）
    连续的 0x4ba / 文本调用之间**无上述 op** ⇒ 同一文本框（软换行）合并。

文本变量：#Name[1] -> アイカ (主角, 可改名)   #Color[n] -> 丢弃(显示属性)

输出：一次点击=一行(连续 0x4ba/文本调用 合并)；不加说话人前缀；保留日文；
      UTF-8-BOM / LF。
"""
import struct
import re
import os
import sys
import glob

TEXT_OP = 0x4BA     # push 文本片段
NAME_OP = 0x4BC     # push 人名
OPT_OP = 0x4CF      # 选项
WAIT_OP = 0x4BB     # 换框/点击
GOTO_OP = 0x0006    # goto (builtin)
VAR_OP = 0x41C      # 按名访问变量/资源的通用 op（param0 = 名；'switch' = 选择结果变量）
NOP_OP = 0x0000     # 空 op；紧随 VAR_OP 出现
CALL_TEXT_OPS = (0xB9BC, 0x19C8C)   # is_call=1 的文本辅助函数

HERO = 'アイカ'      # #Name[1]

RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_NAME = re.compile(r'#Name\[(\d+)\]')
RE_COLOR = re.compile(r'#Color\[\d+\]')


def parse(d):
    """返回 [(offset, is_call, opcode, nparams, length)]"""
    out = []
    export_addr = struct.unpack_from('<I', d, 0x20)[0]
    if d.find(b'CODE_START_') < 0:
        return out
    p = d.find(b'CODE_START_') + 12
    end = min(len(d), export_addr)
    while p < end:
        if p + 16 > len(d):
            break
        ic, op, np, ln = struct.unpack_from('<4I', d, p)
        if ln < 16 or ln % 4 or p + ln > len(d) or np > 0x100:
            break
        out.append((p, ic, op, np, ln))
        p += ln
    return out


def raw_str(d, p, np, ln, k):
    """第 k 个参数指向的字符串记录 [a][b][c][L][text]；b==L//4 且 c==1 为签名。"""
    if k >= np:
        return None
    q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
    if not (p < q < p + ln) or q + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, q)
    if c != 1 or b != L // 4 or not (0 < L <= 0x4000) or q + 16 + L > len(d):
        return None
    return L, d[q + 16:q + 16 + L]


def text_at(d, p, np, ln, k):
    r = raw_str(d, p, np, ln, k)
    if not r:
        return None
    L, raw = r
    try:
        s = raw.split(b'\x00')[0].decode('cp932')
    except Exception:
        return None
    return s


def is_text_param(d, p, np, ln, k):
    """L>4 且可解码出非空文本的参数。"""
    r = raw_str(d, p, np, ln, k)
    if not r:
        return None
    L, raw = r
    if L <= 4:
        return None
    try:
        s = raw.split(b'\x00')[0].decode('cp932')
    except Exception:
        return None
    return s


def clean(s):
    s = RE_COLOR.sub('', s)
    s = RE_NAME.sub(lambda m: HERO if int(m.group(1)) == 1 else m.group(0), s)
    return s


def text_groups(d, p, np, ln):
    """把参数按「二进制记录(L<=4)」切分成若干「连续文本」组。
    0xb9bc 标准形 = [idA][文本…][idB][文本…]：两组 = 互斥双写变体。"""
    groups = []
    cur = []
    for k in range(np):
        s = is_text_param(d, p, np, ln, k)
        if s is not None and s.strip() != '':
            cur.append(s)
        else:
            if cur:
                groups.append(''.join(cur))
                cur = []
    if cur:
        groups.append(''.join(cur))
    return groups


def call_text(d, p, np, ln):
    """辅助函数(0xb9bc / 0x19c8c)的文本参数 -> 一行。
    互斥双写变体：优先取「不含 #Name」的直写版（全篇 inline 口径；实测恒为第 1 组）。"""
    gs = text_groups(d, p, np, ln)
    if not gs:
        return None
    for g in gs:
        if '#Name' not in g:
            return clean(g)
    return clean(gs[0])


def extract_file(path):
    """返回 [str 正文 | ('OPT', text), ...]"""
    d = open(path, 'rb').read()
    ins = parse(d)
    if not ins:
        return []
    lines = []
    cur = []

    def flush():
        if cur:
            t = ''.join(cur).strip(' \u3000\t')
            if t and t.strip('\u3000') != '':
                lines.append(t)
            del cur[:]

    for (p, ic, op, np, ln) in ins:
        if op == TEXT_OP:
            s = text_at(d, p, np, ln, 0)
            if s is None:
                pass
            elif s.strip(' \u3000\t') == '':
                flush()                 # 空文本记录 = 换框标记
            else:
                cur.append(clean(s))
        elif ic == 1 and op in CALL_TEXT_OPS:
            t = call_text(d, p, np, ln)
            if t:
                cur.append(t)
        elif op == NAME_OP:
            flush()                     # 人名札：新框起点（人名本身不加前缀）
        elif op == OPT_OP:
            flush()
            s = text_at(d, p, np, ln, 0)
            if s is not None and s.strip():
                lines.append(('OPT', clean(s).strip(' \u3000\t')))
        elif op == WAIT_OP:
            flush()
        elif op == VAR_OP:
            # 按名访问变量的通用 op（'switch'/'res_*'/'XX好感度'…）。它出现在两条文本之间时，
            # 其后的状态 op（立绘 0x457 / 背景 0xa538 …）或新 NAME 都属于「下一框」，
            # 说明该处是「上一框已完整 → 换框」的编译产物 ⇒ 断框。
            flush()
        elif op == GOTO_OP:
            pass
    flush()
    return lines


def wanted(f):
    return os.path.basename(os.path.dirname(f)).lower() == '1-scenario'


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     '..', '_work_revice', 'script')
    out = sys.argv[2] if len(sys.argv) > 2 else None
    files = [f for f in sorted(glob.glob(os.path.join(src, '**', '*.DAT'),
                                         recursive=True)) if wanted(f)]
    all_lines = []
    for f in files:
        ls = extract_file(f)
        for x in ls:
            all_lines.append(x[1] if isinstance(x, tuple) else x)
    nopt = sum(1 for _ in ())  # noqa
    print('files=%d lines=%d' % (len(files), len(all_lines)))
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
            fh.write('\n'.join(all_lines) + '\n')
        print('->', out)


if __name__ == '__main__':
    main()
