#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""楽園男子 ～誰も知らない もう一つの楽園～ (PSP, Takuyo gss / LSDARC V.100 'SCR 2.00')

容器: PSP_GAME/USRDIR/SCRDATA.BIN (=LSDARC V.100 索引) + SCRDATA.ARC (脚本本体, 未压缩)
脚本: 'SCR 2.00' + 指令流 [u16 op][u8 size][u16 id][typed operands]
      operand: <u8 type><data>; type3 = NUL 结尾 cp932 串

本作 opcode（全库统计 571 脚本，与本引擎前作逐项复核）:
  0x5a  正文框文本  -> 一次点击 = 一行
  0xfc  带 %s 的正文 -> %s 由随后 operand type6 槽填充（本作 = 0x0c02）
  0x5c  选项组      -> 每串 "文本, 标志" ；一行一条取最后逗号前
  0xf0  场景标题卡  -> 直接上屏（每脚本 1 条）
  0xfd  名札/贴图    -> 独立名字窗 => 整条丢弃（不加前缀）
  0x89  跳转标签名（仅 DEBUG）  0x132 变量赋值（INIT: 冬浦 / めぐみ）
排除：PRG_*（含 Θ背景/☆SE 调试串）、SELECT2（字库残渣）、TIME_PASS/AUTOEXEC/
      INIT/RELOAD/YURASHI/DEBUG（系统程序，无正文）

主角名: INIT 脚本 `0x132 (6,'1802','冬浦') (6,'0c02','めぐみ')` ⇒ 姓=冬浦 名=めぐみ；
        正文只插 0x0c02 ⇒ %s = めぐみ
"""
import sys, os, re, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import himehibi_lsdarc as L
import himehibi_disasm as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, '_work_rakuen/PSP_GAME/USRDIR/SCRDATA.BIN')
ARC = os.path.join(ROOT, '_work_rakuen/PSP_GAME/USRDIR/SCRDATA.ARC')
OUT = os.path.join(ROOT, '提取结果/[PSP-JP]楽園男子 ～誰も知らない もう一つの楽園～.txt')

NAME_SLOT = {'1802': '冬浦', '0c02': 'めぐみ'}   # %s 填充源（INIT 实测：姓/名两槽）
DROP_SCRIPTS = {'PRG_BG', 'PRG_NAME', 'PRG_ROUTE', 'PRG_STAND', 'PRG_EFFECT',
                'PRG_EFFECTSTOP', 'PRG_PLATE', 'SELECT2', 'TIME_PASS', 'AUTOEXEC',
                'INIT', 'RELOAD', 'YURASHI', 'DEBUG'}

ESC_NL = re.compile(r'\\n')
ESC_CTRL = re.compile(r'\\[a-zA-Z]')
OPT_FLAG = re.compile(r',\s*[0-9A-Za-z_]+$')


def clean(s):
    s = ESC_NL.sub('', s)
    s = ESC_CTRL.sub('', s)
    return s.strip()


def subst(s, ops):
    """%s 由后续 type6 槽（=NAME_SLOT）依次填充；无槽则留空不替换"""
    srcs = []
    for t, v in ops[1:]:
        if t == 6:
            srcs.append(NAME_SLOT.get(v, ''))
        elif t == 1 and v == 'ffffffff':
            break
    it = iter(srcs)
    return re.sub(r'%s', lambda m: next(it, ''), s)


def main():
    ents, _ = L.read_index(BIN)
    d = open(ARC, 'rb').read()
    lines, st = [], collections.Counter()

    for e in ents:
        if e['name'] in DROP_SCRIPTS:
            continue
        blob = d[e['off']:e['off'] + e['usz']]
        ops, err = H.disasm(blob)
        if err:
            print('DISASM ERR', e['name'], err, file=sys.stderr)
        for off, op, size, ident, operands in ops:
            if op == 0x5a:                       # 正文
                t = clean(operands[0][1] if operands else '')
                if t:
                    lines.append(t)
                    st['text'] += 1
            elif op == 0xfc:                     # 正文（含 %s）
                raw = next((v for t, v in operands if t == 3), '')
                t = clean(subst(raw, operands))
                if t:
                    lines.append(t)
                    st['text'] += 1
            elif op == 0x5c:                     # 选项
                for t_, v in operands:
                    if t_ != 3:
                        continue
                    o = OPT_FLAG.sub('', v).strip()
                    if o:
                        lines.append(o)
                        st['opt'] += 1
            elif op == 0xf0:                     # 场景标题卡
                t = clean(operands[0][1] if operands else '')
                if t:
                    lines.append(t)
                    st['title'] += 1
            elif op == 0xfd:                     # 名札 -> 丢弃
                st['name'] += 1

    out = [l.strip() for l in lines if l.strip()]

    print('stats', dict(st), 'lines', len(out), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('->', OUT, file=sys.stderr)


if __name__ == '__main__':
    main()
