# -*- coding: utf-8 -*-
"""LoverPretend (NS-JP) 文本提取 —— 定稿 v2

链路：XCI → nstool --secure → Program NCA → /1/CONTENTS/STORY.cpk → SCRIPT/*.DAT（118 个）

格式 STCM2L（Idea Factory 自研 / UTF-8）：
  指令流每条尾部固定三元组 [op][0x13a][id][0x10]（按文件偏移单调、id 单调递增）
  0x104        = 正文（一屏内的一行）
  0x3f/0x10a   = 框终止（等待点击）  ← 一框 1~3 行，3 行满了即翻页（句子可跨框）
  0x13f/0x13b/0x13d/0x147 = 名札/章节名/资源名（独立名字窗，剔除）
剔除：99.DAT（存档 UI：`ファイルを選択して下さい。` + ■ 进度条，27 行）、854/855.DAT（无正文）
后附：用語辞典（SYSTEM.cpk → DATABASE/dbDictionary.gbin，45 条）
"""
import os, re, sys, json
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib.lpv_stream import stream

SD = os.path.join(VNTRANS_HOME, '_w_lpv/story/SCRIPT')
DICT = os.path.join(VNTRANS_HOME, '_w_lpv/sysx/DATABASE/dbDictionary.gbin')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]LoverPretend.txt')
HEROINE = 'ちゆき'

BOX_END = {0x3f, 0x10a}
SKIP_FILES = {'99.DAT'}
TAGHEAD = re.compile(r'#[A-Za-z]+\[')


def _bracket(s, i):
    """s[i] 处是 '['，返回配对 ']' 之后的位置"""
    depth = 0
    while i < len(s):
        if s[i] == '[':
            depth += 1
        elif s[i] == ']':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(s)


def clean(s):
    """`#Ruby[基底,#Type[2]读音]` 只留基底；其余 `#Xxx[..]` 全删。
    注意 `#Ruby[..,#Type[2]..]#Type[1]` 与 `#Ruby[..,#Type[2]..#Type[1]]` 两种收尾都有。"""
    s = s.replace('#Name[1]', HEROINE)
    out = []
    i = 0
    while i < len(s):
        if s.startswith('#Ruby[', i):
            j = _bracket(s, i + 5)
            head = s[i + 6:j - 1].split(',')[0]
            out.append(head)
            i = j
            m = re.match(r'#Type\[\d+\]', s[i:])
            if m:
                i += m.end()
            continue
        if s[i] == '#':
            m = TAGHEAD.match(s, i)
            if m:
                i = _bracket(s, m.end() - 1)
                continue
        out.append(s[i])
        i += 1
    return ''.join(out)


def build():
    rows = []
    stats = {'files': 0, 'lines': 0, 'boxes': 0, 'skipped': []}
    for f in sorted(os.listdir(SD)):
        if not f.endswith('.DAT'):
            continue
        if f in SKIP_FILES:
            stats['skipped'].append(f)
            continue
        stats['files'] += 1
        d = open(os.path.join(SD, f), 'rb').read()
        cur = []
        for p, op, i, s in stream(d):
            if op == 0x104 and s is not None:
                cur.append(s)
            elif op in BOX_END:
                if cur:
                    rows.append(box(cur))
                    stats['boxes'] += 1
                    stats['lines'] += len(cur)
                    cur = []
        if cur:
            rows.append(box(cur))
            stats['boxes'] += 1
            stats['lines'] += len(cur)
    return rows, stats


def box(lines):
    parts = []
    for ln in lines:
        ln = clean(ln.lstrip('\u3000'))
        if ln:
            parts.append(ln)
    return ''.join(parts)


def dictionary():
    d = open(DICT, 'rb').read()
    body = d[0xb00:]
    cut = body.rfind(b'GBNL')
    segs = body[:cut].decode('utf-8').split('\x00')
    out = []
    for k in range(0, len(segs) - 1, 2):
        head = segs[k].strip()
        desc = segs[k + 1].replace('#n', '').strip()
        if head and desc:
            out.append(head)
            out.append(desc)
    return out


if __name__ == '__main__':
    rows, stats = build()
    main = [r for r in rows if r.strip()]
    dic = dictionary()
    out = main + dic
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')
    stats['out'] = len(out)
    stats['chars'] = sum(len(x) for x in out)
    stats['dict_terms'] = len(dic) // 2
    print(json.dumps(stats, ensure_ascii=False))
    print('正文 %d 行 / 辞典 %d 行 / 合计 %d' % (len(main), len(dic), len(out)))
