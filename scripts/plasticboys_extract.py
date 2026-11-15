# -*- coding: utf-8 -*-
"""[JP]Plastic Boys ～水色のキモチ～ 全文本提取
链路：STORY.txt(NOT 加密) -> cp932 台本 -> token 流 -> 框切分 -> 正文+选项
L0 判据（GAME.EXE 反汇编证据）:
  - 解密 = 逐字节 NOT（0x1AA70 `not dl` 循环；首字节 0x2A('*') 时跳过=明文）
  - 断框 = 等待指令 [] / [H\\d+*] / [?N] / [$lN]（点击/定时翻页/选项点/行内等待）
  - 名札 = 【…】整行（独立名字窗，剔）；* 行 = 台本注释，剔
  - 选项 = ★選択肢『…』★ / ★『…』★ / 【選択】『…』，取『』内容去重并末尾
  - 剔除区 = *スタッフロール 行起至文件尾（staff roll 位图化 + ヘルプ/CG UI）
"""
import re, sys, collections
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_work_plasticboys/_extract/STORY.txt')
DST = os.path.join(VNTRANS_HOME, '提取结果/[JP]Plastic Boys ～水色のキモチ～.txt')

WAIT = re.compile(r'\[\]|\[H\d+\*\]|\[\?\d+\]|\[\$l\d\]')
NAME = re.compile(r'【[^】]+】')
SEL1 = re.compile(r'★選択肢\s*『([^』]+)』★')
SEL2 = re.compile(r'★『([^』]+)』★')
SEL3 = re.compile(r'【選択】『([^』]+)』')
HIRA = re.compile(r'[ぁ-ん一-鿆]')

raw = bytearray(open(SRC, 'rb').read())
if raw[0] != 0x2A:                       # L0: 首字节 '*' 则明文
    for i, b in enumerate(raw):
        raw[i] = b ^ 0xFF
text = raw.decode('cp932')
lines = text.split('\r\n')

help_idx = next(i for i, l in enumerate(lines) if l.strip() == '*スタッフロール')

boxes, cur, sel, stats = [], [], [], collections.Counter()
for li, l in enumerate(lines):
    if li >= help_idx:
        stats['dropped_tail'] += 1
        continue
    for seg in re.split(r'(\[[^\[\]]*\])', l):
        if not seg:
            continue
        if seg.startswith('['):
            if WAIT.fullmatch(seg):
                if cur:
                    boxes.append(cur); cur = []
            continue
        s = seg.strip()
        if not s:
            continue
        if s.startswith('*') or re.match(r'E\d{3}　', s):
            # E702 注释漏写 '*'（上下行为星号线+跳转注释组，与 *E101…E802 同构）
            stats['comment'] += 1
            continue
        m = SEL1.match(s) or SEL2.match(s) or SEL3.match(s)
        if m:
            sel.append(m.group(1))
            stats['option'] += 1
            continue
        if NAME.fullmatch(s):
            stats['name'] += 1
            continue
        cur.append(s)                        # 其余一律收（拟态词/沉默框/上屏卡）
        stats['body'] += 1
if cur:
    boxes.append(cur)

seen, sel_uniq = set(), []
for s in sel:
    if s not in seen:
        seen.add(s); sel_uniq.append(s)

out = [''.join(b) for b in boxes] + sel_uniq
data = '\n'.join(out) + '\n'
open(DST, 'w', encoding='utf-8-sig', newline='\n').write(data)

print('source lines', len(lines), 'help_idx', help_idx)
print(dict(stats))
print('boxes', len(boxes), 'body lines in boxes', sum(len(b) for b in boxes))
dist = collections.Counter(len(b) for b in boxes)
print('box line dist', sorted(dist.items()))
print('options raw', len(sel), 'uniq', len(sel_uniq))
print('OUT lines', len(out), '->', DST)
