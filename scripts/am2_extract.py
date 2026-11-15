#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]AM2：00～猫と月夜のブランコ～ —— WillPlus AdvHD (WSC v1.0) 文本提取。

链路：SFX.exe → 7z → AMDISC1.iso → Rio.arc（17B 条目变体）→ rotl8(6) 解密 → WSC 字节码。

★ 本作与 scripts/advhd.py 基表（Butterfly 2012+）不同，必须用下面的覆写表：
  - WSC 版本 1.0（2005），opcode 参数长度整体更短
  - 0x41 = [u8 id][u16] + 单串（旁白）；参数 3，**不是** 4
  - 0x42 = [u32] + 名串 + 台词串（名字是独立名字窗 → 只取台词）
  - 0xB6 = [u8][u8] + 单串（与 0x41 交替出现的正文，必须收）
  - 0xFF 三重语义：末字节=结束 / 后跟 0xFF=标签(FF+4B+NUL名) / 其它=FileEnd(+8B)
  - 字符串内 `\\n` 是**框内软换行**（字面 0x5C 0x6E），一行=一个框 ⇒ 合并

断框判据（L0，代码级）：0x41 的前缀 u8 是递增消息 id，实测相邻同型 4997 对中
id 相同的 **0 对** ⇒ 没有任何「一框拆两条记录」的情况，一个 0x41/0x42/0xB6 = 一个显示框。

用法: python am2_extract.py --arc Rio.arc --out OUT.txt
"""
import argparse
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import advhd

# ---- 覆写表（本作实测，见模块 docstring）----
GEN_OVR = {0x00: 0, 0x4A: 4, 0x64: 2, 0x68: 2, 0x90: 4, 0x2C: 6, 0x4C: 1,
           0x20: 0, 0x5C: 2, 0x5E: 1, 0x81: 1, 0x96: 16,
           0xAB: 0, 0xC8: 0, 0xF4: 0, 0xFA: 7, 0xFD: 3, 0xFE: 3}
STR_OVR = {0x48: 10, 0x21: 3, 0x41: 3}
DBL_OVR = {0x42: 4}
STR_ADD = {0x23: 1}          # 0x23 在基表里是 9B 串；本作是 1B + 串

NARR = 0x41                  # 旁白 / 独白
DLG = 0x42                   # 名字 + 台词
NARR2 = 0xB6                 # 与 0x41 交替的正文
CHOICE = 0x02                # 选项块


def tables():
    G = dict(advhd.GENERIC); G.update(GEN_OVR); G.update(STR_ADD)
    S = dict(advhd.STRING); S.update(STR_OVR); S.pop(0x23, None)
    D = dict(advhd.DOUBLESTRING); D.update(DBL_OVR)
    D.pop(0x41, None)        # 0x41 是单串，绝不能留在双串表里
    return G, S, D


G, S, D = tables()


def load_arc(path):
    """Rio.arc 旧版变体：组头 [ext 4B]['WSC\\0'] + count + tableOffset，条目 17B。"""
    d = open(path, 'rb').read()
    cnt, st = struct.unpack_from('<II', d, 8)
    out, q = [], st
    for _ in range(cnt):
        nm = d[q:q + 9].split(b'\x00')[0].decode('cp932', 'replace')
        ln, so = struct.unpack_from('<II', d, q + 9)
        q += 17
        out.append((nm, ln, advhd.decrypt(d[so:so + ln])))
    return out


def _cstr(b, i):
    j = b.index(b'\x00', i)
    return b[i:j], j + 1


def parse(b):
    """返回 [(opcode, [str, ...])]（只含正文与选项）。顺带做闭合校验。"""
    i, n = 0, len(b)
    seq = []
    while i < n:
        op = b[i]; i += 1
        if op == 0xFF:
            if i == n:
                return seq, True
            if b[i] == 0xFF:                      # 标签指令
                i += 5
                _, i = _cstr(b, i)
                continue
            i += 8                                # FileEnd
            continue
        if op == CHOICE:
            nch = struct.unpack_from('<H', b, i)[0]; i += 2
            opts = []
            for _ in range(nch):
                i += 2
                s1, i = _cstr(b, i)
                i += 3
                o2 = b[i]; i += 1
                if o2 in D:
                    i += D[o2]; _, i = _cstr(b, i); _, i = _cstr(b, i)
                elif o2 in S:
                    i += S[o2]; _, i = _cstr(b, i)
                elif o2 in G:
                    i += G[o2]
                else:
                    raise ValueError('choice subop %02X @0x%X' % (o2, i))
                opts.append(s1)
            seq.append((CHOICE, opts))
            continue
        if op in D:
            i += D[op]
            _nm, i = _cstr(b, i)
            line, i = _cstr(b, i)
            seq.append((op, [line]))               # 名字是独立名字窗 → 丢弃
        elif op in S:
            i += S[op]
            s1, i = _cstr(b, i)
            if op in (NARR, NARR2):
                seq.append((op, [s1]))
        elif op in G:
            i += G[op]
        else:
            raise ValueError('unknown opcode %02X @0x%X' % (op, i))
        if i > n:
            raise ValueError('overrun @0x%X' % i)
    return seq, False


def to_text(raw):
    t = raw.decode('cp932', 'replace')
    t = t.replace('\\n', '')                       # 框内软换行 ⇒ 合并
    return t.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arc', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()

    ents = load_arc(a.arc)
    lines, stats, bad = [], {}, []
    for nm, ln, b in ents:
        try:
            seq, ok = parse(b)
        except ValueError as e:
            bad.append((nm, str(e)))
            continue
        if not ok:
            bad.append((nm, '未走到末字节'))
        for op, ss in seq:
            for s in ss:
                t = to_text(s)
                if t:
                    lines.append(t)
                    stats[op] = stats.get(op, 0) + 1

    data = '\n'.join(lines) + '\n'
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'wb') as fh:
        fh.write(b'\xef\xbb\xbf' + data.encode('utf-8'))

    if a.report:
        print('脚本 %d，闭合失败 %d' % (len(ents), len(bad)))
        for x in bad[:10]:
            print('  ', x)
        print('行数 %d' % len(lines))
        print('来源分布', {('%02X' % k): v for k, v in sorted(stats.items())})
        print('输出', a.out, os.path.getsize(a.out), 'B')


if __name__ == '__main__':
    main()
