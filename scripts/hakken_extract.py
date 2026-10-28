#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""転生八犬士封魔録 (PS2-JP, SLPM_663.96) —— SC.AFS 全文本提取。

字节码（u16 LE，<0xFF00 = 字符码；>=0xFF00 = 指令）:
  FFFF <run>            正文框开始（= 一次点击）
  FFFE <run>            框内换行（软换行；run 常以 U+3000 缩进起头 → 合并时去一个）
  FFFB                  消息结束（点击点）
  FFF0 <style> <name>   名札（独立名字窗）→ 整条丢弃
  FFE7 / FFE6           主角 姓 / 名 占位（桐沢 / 結奈；默认名表见 ELF 0x12ed98）
  FFEF <icon> <opt1>    选项组开始；后续连续 FFFF 各为一条选项
                        （选项行前缀 [0000][style<0x10] 为装饰，剥除）
  FF98                  地点名（画面标签＝UI，不收）
  FF89                  对战对手名（台词窗外的名牌，不收）
字符集 = cp932 有效双字节码原码序（0 偏移，无 Special 基线）；
二级区 3456+ 逐槽定值见 SLOTS（文脉仲裁，报告登记）。
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stormlover_charset import build_charset

CHARSET = build_charset()
NC = len(CHARSET)

C_NAME, C_BOX, C_BR, C_SEP = 0xFFF0, 0xFFFF, 0xFFFE, 0xFFFB
C_MACRO_SUR, C_MACRO_GIV = 0xFFE7, 0xFFE6
C_CHOICE = 0xFFEF
UNDEC = '\u3014\u672a\u89e3\u6790\u3015'   # 〔未解析〕

# 主角默认名（ELF 名字表 + vndb/ymgal：桐沢 結奈）
MACRO_SUB = {C_MACRO_SUR: '桐沢', C_MACRO_GIV: '結奈'}

# 二级区 3456+ 逐位置定值复元（本作字体自用槽；cp932 基线在此是假象）
# 逐条证据见 解析报告 §槽表
SLOTS = {
    3457: '綺',   # 丐麗→綺麗 / ほら、丐麗な月
    3459: '璧',   # 牡丹の个→牡丹の璧（八犬士の証）
    3460: '辣',   # 丱腕家→辣腕家 / 辛丱な発言→辛辣
    3462: '摯',   # 真丼な愛→真摯な愛
    3463: '騙',   # 丿す/丿される→騙す/騙される
    3464: '憑',   # 信乂性→信憑性
    3465: '罠',   # 仕掛けた乖→仕掛けた罠
    3466: '全',   # 完乘→完全
    3467: '礼',   # 失亂→失礼
    3468: '磋',   # 切亅琢磨→切磋琢磨
    3470: '吠',   # 犬の亊り声→犬の吠り声
    3471: '絆',   # なんの舒もない→なんの絆もない
    3472: '喩',   # いい比弍だな→いい比喩だな
    3473: '作',   # 夕飯は俺が于ってやる→作ってやる
    3474: '淹',   # 亞れてくれるお茶→淹れてくれるお茶
    3475: '枷',   # 自分に亟をはめれば→枷をはめる
    3476: '囮',   # 先生を亠に→先生を囮に
    3477: '届',   # 不亢者→不届者
    3478: '几',   # 亰帳面→几帳面
    3479: '諦',   # 亳めてる→諦めてる
}
# 3458（丕: こっちを丕んでる）／3469（豫: 豫々しいお姫様）未能定值 → 〔未解析〕
UNRESOLVED_SLOTS = {3458, 3469}


def dec(run):
    out = []
    for v in run:
        if v in MACRO_SUB:
            out.append(MACRO_SUB[v])
        elif v in SLOTS:
            out.append(SLOTS[v])
        elif v in UNRESOLVED_SLOTS:
            out.append(UNDEC)
        elif 0 <= v < NC:
            out.append(CHARSET[v])
        else:
            out.append(UNDEC)
    return ''.join(out)


def _run_at(vals, i):
    r = []
    while i < len(vals) and vals[i] < 0xFF00:
        r.append(vals[i]); i += 1
    return r, i


STYLE_LO, STYLE_HI = 0x02, 0x2F      # 选项装饰码区间（。，．・：；？！゛゜´｀¨＾￣＿ヽヾ…‥“”［］ 等）


def _is_style(v):
    return STYLE_LO <= v <= STYLE_HI


def _decorated(vals, i):
    """该 FFFF 行是否带 [0000][style] 选项装饰。"""
    if i >= len(vals) or vals[i] != C_BOX:
        return False
    r, j = _run_at(vals, i + 1)
    return len(r) >= 3 and r[0] == 0 and _is_style(r[1])


def _opt_tail(vals, i):
    """消费紧随其后的选项行，返回 (选项文本列表, 新下标)。"""
    opts = []
    n = len(vals)
    while i < n and vals[i] == C_BOX:
        r, j = _run_at(vals, i + 1)
        nxt = vals[j] if j < n else None
        if nxt in (C_BR, C_SEP):
            break                          # 真·正文框，组结束
        if len(r) >= 2 and r[0] == 0 and r[1] == 0:   # style 0 = 组尾填充行
            i = j
            break
        if len(r) >= 2 and r[0] == 0 and _is_style(r[1]):
            body = r[2:]
        else:
            body = r
        opts.append(dec(body))
        i = j
    return opts, i


def parse(path):
    d = open(path, 'rb').read()
    vals = struct.unpack_from('<%dH' % (len(d) // 2), d, 0)
    n = len(vals)
    i = 0
    out = []            # [(kind, text)]
    while i < n:
        v = vals[i]
        if v == C_CHOICE:
            run, i = _run_at(vals, i + 1)
            opts = [dec(run[1:])] if len(run) > 1 else []
            tail, i = _opt_tail(vals, i)
            opts += tail
            for t in opts:
                t = t.strip('\u3000 ')
                if t:
                    out.append(('opt', t))
            continue
        if v == C_BOX:
            run, j = _run_at(vals, i + 1)
            nxt = vals[j] if j < n else None
            if nxt in (C_BR, C_MACRO_SUR, C_MACRO_GIV, C_SEP):
                i = j
                segs = [dec(run)]
                while i < n and vals[i] != C_SEP:
                    if vals[i] == C_BR:
                        i += 1
                        r2, i = _run_at(vals, i)
                        segs.append(dec(r2).lstrip('\u3000'))
                    elif vals[i] in (C_MACRO_SUR, C_MACRO_GIV):
                        segs.append(dec([vals[i]])); i += 1
                        r2, i = _run_at(vals, i)
                        segs.append(dec(r2))
                    else:
                        break                 # 名札/其余指令 → 本框结束
                if i < n and vals[i] == C_SEP:
                    i += 1
                t = ''.join(segs).strip()
                if t:
                    out.append(('msg', t))
                continue
            if nxt == C_BOX and _decorated(vals, j):
                # 无 FFEF 前缀的选项组（战斗指令/分支选择）
                opts = [dec(run)]
                tail, i = _opt_tail(vals, j)
                opts += tail
                for t in opts:
                    t = t.strip('\u3000 ')
                    if t:
                        out.append(('opt', t))
                continue
            i = j
            continue
        if v >= 0xFF00:
            i += 1
            r, i = _run_at(vals, i)
            continue
        i += 1
    return out


def build(scdir):
    lines = []
    for f in sorted(os.listdir(scdir)):
        if not f.endswith('.bin'):
            continue
        for kind, t in parse(os.path.join(scdir, f)):
            lines.append(t)
    return lines


if __name__ == '__main__':
    scdir, outpath = sys.argv[1], sys.argv[2]
    lines = build(scdir)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        for t in lines:
            f.write(t + '\n')
    print('lines:', len(lines))
