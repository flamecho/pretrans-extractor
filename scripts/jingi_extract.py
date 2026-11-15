# -*- coding: utf-8 -*-
"""仁義なき乙女（美蕾 MADOKA GScript / CRPT type 3）文本提取。

结构判据：
- `.sce` = CRPT 头（32B）＋ 1024B/块 TScramble；逐块 seed 由日文相似度恢复（同 ツンデレ★Ｓ乙女）。
- 文本字面池 = 块 6528..末尾，NUL 自定界；每条日文字面 = 一条消息（同族既定口径：一框一次点击）。
  框内 `\x08` = 显示换行（合并）；`\x10基\x11读\x12` = 注音（留基字）。
- 人名宏在**字节层**替换：`05 80 80 80 C2 E3` = 小泉（姓）／`…C2 E4` = 沙紀（名）。
  ⚠ 必须先去宏再 cp932 解码，否则 `C2 E4 81 41` 会被拆成 `ﾂ`＋汉字＋`A`（实测化け）。
- 池首 0..28 共 29 条 = 系统/调试串（默认名、输入校验、SEF 废弃警告、ルール画像错误、脚本选择）⇒ 整段剔除。
- 独立名札：紧跟「台词」前的**单条**无引号/句读短串，且同值出现 ≥2 ⇒ 名札（独立名字窗）剔除；
  连续 ≥2 条同类短串 = **选项**，保留一行一条；单次出现的短串 = 章题/扉文，保留。
- 跨框断引号/括号：成行后若有「无」/（无）行，按 2–4 框成组出「段行＋合并行」双版。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
from tsundere_extract import decrypt_block, score_block

SRC = os.path.join(VNTRANS_HOME, '_work_jingi_honpen/src/仁義なき乙女/仁義なき乙女.sce')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]仁義なき乙女.txt')
BLOCK_START = 6528
HEAD = 29
MACRO = {b'\x05\x80\x80\x80\xc2\xe3': '小泉'.encode('cp932'),
         b'\x05\x80\x80\x80\xc2\xe4': '沙紀'.encode('cp932')}


def load_jp():
    data = open(SRC, 'rb').read()
    assert data[:4] == b'CRPT'
    pay = data[0x20:]
    nb = len(pay) // 0x400
    blocks = np.frombuffer(pay[:nb * 0x400], dtype=np.uint8).reshape(nb, 0x400)
    plain = []
    for bi in range(BLOCK_START, nb):
        base = decrypt_block(bytes(blocks[bi]))
        k, _sc = score_block(np.frombuffer(base, dtype=np.uint8))
        plain.append(bytes(c ^ k for c in base))
    out = []
    for p in b''.join(plain).split(b'\x00'):
        if len(p) < 2:
            continue
        # 串首 `01 XX` = 演出/样式控制码（XX 可能是前导字节，直接解码会把下一字节吃掉）
        if p[0] == 0x01:
            p = p[2:]
        for m, v in MACRO.items():
            p = p.replace(m, v)
        try:
            t = p.decode('cp932')
        except UnicodeDecodeError:
            continue
        if any(0x3040 <= ord(c) <= 0x9fff for c in t):
            out.append(t)
    return out


def clean(t):
    t = re.sub(r'\x10(.*?)\x11.*?\x12', r'\1', t)
    t = t.replace('\x08', '')
    t = re.sub(r'[\x00-\x1f\u0080-\u009f]', '', t)
    return t.strip()


def is_short_label(t):
    return (len(t) <= 16 and not any(c in t for c in '「」『』、。！？…―（）')
            and t.strip() != '')


def main():
    jp = load_jp()
    # 池首系统/调试串（默认名、输入校验、SEF 警告、ルール画像错误、脚本选择）整段剔除：
    # 以第一章题「とつぜん委員長」为故事起点
    start = next(i for i, t in enumerate(jp) if t.strip() == 'とつぜん委員長')
    jp = jp[start:]
    print('系统/调试串剔除 %d 条（池首 → 第一章题）' % start)
    raw = [clean(t) for t in jp]
    raw = [t for t in raw if t]

    # 名札 / 选项判定
    n = len(raw)
    labels = [is_short_label(t) for t in raw]
    cnt = Counter(t for t, lab in zip(raw, labels) if lab)
    name_drop = set()
    option_idx = set()
    i = 0
    while i < n:
        if not labels[i]:
            i += 1
            continue
        j = i
        while j < n and labels[j]:
            j += 1
        run = j - i
        followed = j < n and raw[j].startswith(('「', '『'))
        if run >= 2 and followed:
            option_idx.update(range(i, j))
        elif run == 1 and followed and cnt[raw[i]] >= 3:
            name_drop.add(raw[i])
        i = j
    print('名札候选 %d 种 ⇒ 剔除 %d 种' % (len(cnt), len(name_drop)))
    print('  名札:', '、'.join(sorted(name_drop)))
    print('  选项组行数:', len(option_idx))

    lines = [t for k, t in enumerate(raw)
             if t not in name_drop]

    # 跨框断引号/括号 → 段行＋合并行
    out = []
    i, n = 0, len(lines)
    while i < n:
        grp = [lines[i]]
        j = i + 1
        while j < n and j <= i + 3:
            joined = ''.join(grp)
            need_q = joined.count('「') > joined.count('」')
            need_p = joined.count('（') > joined.count('）')
            if not need_q and not need_p:
                break
            nxt = lines[j]
            if nxt.startswith('「') or nxt.startswith('（'):
                break
            grp.append(nxt)
            j += 1
        if len(grp) > 1:
            out.extend(('seg', x) for x in grp)
            out.append(('merged', ''.join(grp)))
            i = j
        else:
            out.append(('line', lines[i]))
            i += 1

    body = ''.join(v + '\n' for _k, v in out)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))

    print('成品 %d 行（段行 %d / 合并行 %d）/ %d 字 / %d B' % (
        len(out), sum(1 for k, _ in out if k == 'seg'),
        sum(1 for k, _ in out if k == 'merged'),
        sum(len(v) for _k, v in out), os.path.getsize(OUT)))
    b1 = [x for x in lines if '「' in x and '」' not in x]
    b2 = [x for x in lines if '（' in x and '）' not in x]
    print('含「无」 %d / 含（无） %d' % (len(b1), len(b2)))
    for x in b1[:8]:
        print('  Q', x[:80])
    for x in b2[:8]:
        print('  P', x[:80])


if __name__ == '__main__':
    main()
