#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP] DYNAMIC CHORD feat.Liar-S Append Disc（honeybee black / ASGARD, PC-ISO）

链路（本作实测）：
  ISO9660 直读（scripts/iso9660.py）→ RIO.ARC（4,219,116 B / 404 × WSC）
  → ext-group 表（u32 extCount=1 ／ "WSC\\0" ／ count=404 ／ tableOffset=0x10）
  → 每字节 rotl_8(c,6) → AdvHD 字节码
  → 0x41 地の文 / 0x42 名札＋台詞 / 0x02 選択肢 → 成行

与同系列 PC 前作的差异（三条表项，见报告 §2）：
  STRING[0x09]  = 0     （前作表 2；本作 0x09 后直接跟 NUL 串，取 2 会吃 2 字节）
  GENERIC[0x4B] = 20    （Double Score 系列同为 20；advhd 默认 16）
  GENERIC[0x00] = 0     （NOP 分隔符，脚本里成对出现）
  GENERIC[0xAB] = 0     （仅系统脚本 MAINMENU 出现）
  GENERIC[0x24] = 11    （画面矩形制御，11 字节）

用法:
  python scripts/dycls_extract.py [--src RIO.ARC] [--out 输出.txt] [--stats]
"""
import argparse
import collections
import hashlib
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HOME, 'tools'))
import advhd

SRC = os.path.join(HOME, '_work_dycls/iso/RIO.ARC')
OUT = os.path.join(HOME, '提取结果/[PC-JP]DYNAMIC CHORD feat.Liar-S Append Disc.txt')

# ---- 本作表项修正 ---------------------------------------------------------
STRING = dict(advhd.STRING); STRING[0x09] = 0
GENERIC = dict(advhd.GENERIC)
GENERIC.update({0x4B: 20, 0x00: 0, 0xAB: 0, 0x24: 11})
DOUBLESTRING = dict(advhd.DOUBLESTRING)

# ---- 收录顺序 -------------------------------------------------------------
# LKYO=共通線（12–15 章四个角色分支选项、20 章夏フェス收束）
# 之后按乐队编制：朔良(vo)→千哉(gt)→芹(ba)→宗太郎(dr)（同 NS Remaster 块序）
# E*  = ENCORE シナリオ（ENCORE.wsc 只调用 Esak_00/Echi_01/Eser_01/Esou_01）
# LOMK=おまけ（OMAKE01…，9 篇）
GROUPS = ['LKYO', 'LSAK', 'LCHI', 'LSER', 'LSOU',
          'ESAK', 'ECHI', 'ESER', 'ESOU', 'LOMK']

JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')


def natkey(nm):
    """章号自然序；ED/END 之类无编号者排在本组末（9999）"""
    m = re.match(r'^[A-Z]+_(\d+)([A-Z]*)$', nm)
    if not m:
        return (9999, 0, nm)
    return (int(m.group(1)), 0, m.group(2))


def order_names(ent):
    seq = []
    for g in GROUPS:
        sub = [n for n in ent if n.split('_')[0] == g]
        sub.sort(key=natkey)
        seq += sub
    return seq


def walk(b):
    """AdvHD 字节码 → (op, [strings])；文本记录自定界，永不失步"""
    i, n, recs = 0, len(b), []
    while i < n:
        op = b[i]; i += 1
        if op == 0x02:
            nch = struct.unpack_from('<H', b, i)[0]; i += 2
            ch = []
            for _ in range(nch):
                i += 2
                s1 = b[i:b.index(b'\x00', i)]; i += len(s1) + 1
                i += 3
                op2 = b[i]; i += 1
                if op2 in STRING:
                    i += STRING[op2]; s2 = b[i:b.index(b'\x00', i)]; i += len(s2) + 1
                elif op2 in GENERIC:
                    i += GENERIC[op2]; s2 = b''
                elif op2 in DOUBLESTRING:
                    i += DOUBLESTRING[op2]
                    i = b.index(b'\x00', i) + 1
                    s2 = b[i:b.index(b'\x00', i)]; i += len(s2) + 1
                else:
                    raise SystemExit('choice-sub 未识别 op 0x%02x @%d' % (op2, i))
                ch.append((s1, s2))
            recs.append((op, ch))
        elif op in STRING:
            i += STRING[op]
            s = b[i:b.index(b'\x00', i)]; i += len(s) + 1
            recs.append((op, [s]))
        elif op in GENERIC:
            i += GENERIC[op]
        elif op in DOUBLESTRING:
            i += DOUBLESTRING[op]
            a = b[i:b.index(b'\x00', i)]; i += len(a) + 1
            s = b[i:b.index(b'\x00', i)]; i += len(s) + 1
            recs.append((op, [a, s]))
        else:
            raise SystemExit('未识别 op 0x%02x @%d' % (op, i))
    return recs, i


def clean(t):
    t = re.sub(r'%[A-Z]{1,3}', '', t)                 # %K %P %O %LC
    t = re.sub(r'[\ue000-\uf8ff]', '', t)             # PUA 内联图标
    t = re.sub(r'\{([^{}:：="\'\s]+)[:：][^{}]*\}', r'\1', t)  # ruby {漢字:かんじ}
    t = re.sub(r'\\n\u3000?', '', t)                  # 框内软换行 + 行首缩进
    return t.strip('\u3000 ').strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=SRC)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--stats', action='store_true')
    a = ap.parse_args()

    d = open(a.src, 'rb').read()
    ent = advhd.parse_arc(d)
    seq = order_names(ent)

    lines, stats, bad, plates = [], [], [], 0
    choice_groups = 0
    kdist = collections.Counter()
    seen, dup = set(), []
    for nm in seq:
        _ext, ln, off = ent[nm]
        b = advhd.decrypt(d[off:off + ln])
        recs, pos = walk(b)
        if pos != ln:
            bad.append((nm, ln, pos))
        n_text = n_keep = 0
        block = []
        for op, ss in recs:
            if op in (0x41, 0x42):
                n_text += 1
                raw = ss[-1].decode('cp932')
                kdist[(raw.count('%K'), raw.count('%P'))] += 1
                if op == 0x42:
                    plates += 1
                got = clean(raw)
                if not got:
                    continue
                block.append(got)
            elif op == 0x02:
                choice_groups += 1
                for s1, _s2 in ss:
                    t = clean(s1.decode('cp932'))
                    if t:
                        block.append(t)
        # 同一段正文被拆成多个分支文件（本作 LKYO_20B/20C/20D 三件正文逐字相同，
        # 仅演出参数不同）⇒ 只留一次，避免整章三连重复
        hkey = hashlib.md5('\n'.join(block).encode('utf-8')).hexdigest() if block else None
        if hkey and hkey in seen:
            dup.append(nm)
            stats.append((nm, n_text, 0))
            continue
        if hkey:
            seen.add(hkey)
        lines += block
        n_keep = len(block)
        stats.append((nm, n_text, n_keep))

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    if a.stats:
        print('scripts %d  text_records %d  lines %d'
              % (len(seq), sum(s[1] for s in stats), len(lines)))
        print('名札 %d（整条丢弃）  選択肢組 %d' % (plates, choice_groups))
        print('%K/%P 分布', dict(kdist))
        print('失步', bad or '无')
        print('同文去重（只留一次）', dup or '无')
        print('组行数', {g: sum(s[2] for s in stats if s[0].split('_')[0] == g) for g in GROUPS})
    print('->', a.out, len(lines), '行')


if __name__ == '__main__':
    main()
