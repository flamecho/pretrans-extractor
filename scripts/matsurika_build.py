# -*- coding: utf-8 -*-
"""マツリカの炯-kEi- 天命華燭伝 文本成行（在 matsurika_extract 之上）

成行依据（L0）：
  GuideMess / NameMess 各占一个文本框；紧随其后的 KW = 等待点击；WinClear = 清框。
  文本框内 '\\n' / '\\r\\n' 为框内软换行（引擎自动送行）→ 合并。
  富文本：#C(..)/#R(..)/#LC/#PY(n)/#P(x,y)/#KW 均为渲染控制 → 剥除；
          #R(よみ,...) 后紧跟基字（基字保留）。
  #T0/#T1/#T2 …：同一框的互斥文本变体（是否称呼主角名）→ 取 T0/T1 段，丢弃 T2+ 段（同段取一）。
  名札：NameMess 第 1 参数＝说话人名（独立名字窗）→ 丢弃，不加前缀。
  主角名宏 ${FirstName} → ナーヤ（vndb v52279 protagonist）。
"""
import os, sys, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matsurika_extract import parse_memfs, read_entry, parse_script

HEROINE = 'ナーヤ'

RE_CTRL = re.compile(r'#[A-Za-z]+(?:\([^)]*\))?')
RE_T = re.compile(r'#T(\d+)')


def parse_t(text):
    """#T 变体切分：返回保留段拼接结果（保留 T0/T1，丢 T2+）"""
    parts = RE_T.split(text)
    out = [parts[0]]
    for i in range(1, len(parts), 2):
        tag = int(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ''
        if tag <= 1:
            out.append(body)
    return ''.join(out)


def clean(s):
    s = parse_t(s)
    s = RE_CTRL.sub('', s)
    s = s.replace('${FirstName}', HEROINE)
    s = s.replace('\r', '').replace('\n', '')
    return s.strip()


def order_table(body, ents):
    """从 membody 内的全局符号表取 *.tat 顺序"""
    tab = None
    for off, size in ents:
        r = read_entry(body, off, size)
        if len(r) > 100000 and r[:4] != b'\xc1\xab\xde\xc0':
            tab = r
    names, i = [], 0
    while i < len(tab) - 1:
        ok, j = 0, i
        while j + 1 < len(tab):
            c = tab[j] | (tab[j + 1] << 8)
            if 0x20 <= c < 0x7f or 0x3000 <= c <= 0x30ff or 0x4e00 <= c <= 0x9fff or 0xff01 <= c <= 0xff60 \
               or c in (0x3001, 0x3002, 0x2026, 0x2015, 0x301c, 0x30fb):
                j += 2
                ok += 1
            else:
                break
        if ok >= 2:
            s = tab[i:j].decode('utf-16-le', 'replace')
            if '.tat' in s:
                names.append(s.split('.tat')[0].lstrip('"& '))
            i = j
        else:
            i += 2
    return names


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '_work_matsurika/patched/common'
    out = sys.argv[2] if len(sys.argv) > 2 else '_work_matsurika/out/matsurika.txt'
    body = open(os.path.join(root, 'script.membody'), 'rb').read()
    ents = parse_memfs(os.path.join(root, 'script.memfs'))
    order = order_table(body, ents)
    scripts = {}
    for off, size in ents:
        r = read_entry(body, off, size)
        if r[:4] != b'\xc1\xab\xde\xc0':
            continue
        nm = r[0x60:0x60 + 0x40].decode('utf-16-le').split('\x00')[0]
        if not nm.endswith('.tat'):
            continue
        scripts.setdefault(nm[:-4], r)  # 补丁包内同名重存条目正文一致，取首条

    seq = [n for n in order if n in scripts]
    extra = sorted(n for n in scripts if n not in seq)
    seq += extra
    lines, stats = [], {}
    for nm in seq:
        try:
            pool, ops = parse_script(scripts[nm])
        except Exception as e:
            stats.setdefault('bad', []).append(nm)
            continue
        n0 = len(lines)
        branch = False   # 自上次出文以来是否经过 互斥分支 指令
        for cmd, a in ops:
            if cmd in ('Jump', 'If', 'SltRun', 'SltDel'):
                branch = True
            if cmd == 'GuideMess' and a:
                t = clean(pool[a[0]])
            elif cmd == 'NameMess' and len(a) >= 2:
                t = clean(pool[a[1]])
            elif cmd == 'SltAdd' and len(a) >= 3:
                t = clean(pool[a[2]])
            else:
                continue
            if not t:
                continue
            # 互斥分支两条路径落到同一句 → 同一显示文本只留一次（同段取一）
            if branch and lines and t == lines[-1]:
                branch = False
                continue
            lines.append(t)
            branch = False
        stats[nm] = len(lines) - n0
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('scripts', len(seq), 'lines', len(lines))
    print('per-script min/max', min(stats.values()), max(stats.values()))
    print('bad', stats.get('bad'))
    print('order head', seq[:8])


if __name__ == '__main__':
    main()
