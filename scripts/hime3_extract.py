# -*- coding: utf-8 -*-
"""星の王女3（美蕾 MADOKA GScript / CRPT type 3）文本提取。

结构判据：
- `.sce` 头 `CRPT`＋type 3；1024B/块独立 XOR key（复用 tsundere 的 LCG/散列/相似度恢复）。
- 字面池＝块 7042 起（尾部长约 1.9 MB），cp932 平文、NUL 自定界；一条字面＝一条消息（同族既定口径）。
- 池首 0..119 = 系统/UI/角色名表（标题、字体、章节表、调试串、`%S/%C/%N` 演出串、说话人名 roster）
  ⇒ 以首个「台词字面」为故事起点整段剔除。
- 人名宏（**字节层替换**）：`05 80 80 80 BE BC` = 姓、`05 80 80 80 BE BD` = 名
  （默认值未在源内给出 ⇒ 落 `⟨姓⟩`/`⟨名⟩` 占位，不猜填）。
- `\x08`＝显示换行（合并）；其它控制符剥离；串首 `01 XX` 演出码按字节去 2 字节。
- 独立名札：紧跟「台词」前的独立短串（无引号/句读、≤16 字），同值 ≥3 ⇒ 名札窗剔除；
  连续 ≥2 条 ⇒ 选项组保留；单次短串 ⇒ 章题/扉文保留。
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

SRC = os.path.join(VNTRANS_HOME, '_work_hime3/src/星の王女3/MP1_星の王女3.sce')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]星の王女3 ～天・地・人の創世記～＋星の約束.txt')
BLOCK_START = 7042
MACRO = {b'\x05\x80\x80\x80\xbe\xbc': '〔姓〕'.encode('cp932'),
         b'\x05\x80\x80\x80\xbe\xbd': '〔名〕'.encode('cp932')}


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
    t = t.replace('\x08', '')
    t = re.sub(r'[\x00-\x1f\u0080-\u009f]', '', t)
    return t.strip()


def is_short_label(t):
    return (len(t) <= 16 and not any(c in t for c in '「」『』、。！？…―（）')
            and t.strip() != '')


def main():
    jp = load_jp()
    start = next(i for i, t in enumerate(jp) if t.lstrip().startswith(('「', '『')))
    print('系统/角色名表剔除 %d 条（池首 → 首个台词）' % start)
    raw = [clean(t) for t in jp[start:]]
    raw = [t for t in raw if t]

    n = len(raw)
    labels = [is_short_label(t) for t in raw]
    cnt = Counter(t for t, lab in zip(raw, labels) if lab)
    name_drop = set()
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
        if run == 1 and followed and cnt[raw[i]] >= 3:
            name_drop.add(raw[i])
        i = j
    print('名札候选 %d 种 ⇒ 剔除 %d 种：%s' % (len(cnt), len(name_drop),
                                        '、'.join(sorted(name_drop))))

    lines = [t for t in raw if t not in name_drop]

    out = []
    i, n = 0, len(lines)
    while i < n:
        grp = [lines[i]]
        j = i + 1
        while j < n and j <= i + 3:
            joined = ''.join(grp)
            need_q = (joined.count('「') + joined.count('｢')) > (joined.count('」') + joined.count('｣'))
            need_p = (joined.count('（') + joined.count('(')) > (joined.count('）') + joined.count(')'))
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
