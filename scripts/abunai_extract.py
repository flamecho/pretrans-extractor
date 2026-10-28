# -*- coding: utf-8 -*-
"""アブナイ恋の捜査室 (PSP, QuinRose/Gigno) —— .ks 文本 DSL → 全文本

规则：
  - 一次点击 = 一个 `[message ...] ... [/message]` 块（L1：脚本记录自定界）
  - 块内 `[br]` 与物理换行 = 同框软换行 ⇒ 合并
  - `[select word="…"]` = 选项，一行一条，按脚本顺序
  - `[PRINT value="FAMILYNAME"/"FIRSTNAME"]` = 主角名宏，行内替换
  - 名札是图片（name="name_xxx.png"）⇒ 无文字，不加前缀
  - 其余标签（chara/bgimage/cg/se/bgm/set/exec/select 以外）一律丢
  - debug 脚本（test00–test06 / dbglovecheck）与 endroll（无文本）排除

用法：
  python scripts/abunai_extract.py _work_abunai/ks 提取结果/xx.txt
"""
import os
import re
import sys

FAMILY = '櫻井'
GIVEN = '翼'

SKIP_FILES = {'test00.ks', 'test01.ks', 'test02.ks', 'test03.ks', 'test04.ks',
              'test05.ks', 'test06.ks', 'dbglovecheck.ks', 'endroll_h.ks',
              'endroll_n.ks', 'endroll_b.ks', 'op_movie.ks'}

CHAR_ORDER = ['akechi', 'fujimori', 'ani', 'hozumi', 'kisaragi', 'ogasawara', 'onose']


def order_key(fn):
    base = fn[:-3]
    if base == 'prologue':
        return (0, 0, 0, 0, base)
    if base.startswith('prologue'):
        return (0, 0, int(base[8:]), 0, base)
    if base == 'op01':
        return (0, 1, 0, 0, base)
    if base == 'op02':
        return (2, 0, 0, 0, base)
    m = re.match(r'^([a-z]+)(\d\d)_(\d\d)([a-z]?)(_omake)?$', base)
    if m:
        who, season, num, suf, omake = m.groups()
        w = CHAR_ORDER.index(who) if who in CHAR_ORDER else 90
        sufv = {'': 0, 'n': 1, 'b': 2, 'h': 3}.get(suf, 9)
        return (1 if season == '01' else 3, w, int(num), sufv * 10 + (1 if omake else 0), base)
    if base.startswith('mini'):
        return (4, 0, 0, 0, base)
    return (5, 0, 0, 0, base)


def parse_body(body):
    body = re.sub(r'\[br\s*/?\]', '', body, flags=re.I)
    body = re.sub(r'\[PRINT\s+value="FAMILYNAME"\s*/?\]', FAMILY, body, flags=re.I)
    body = re.sub(r'\[PRINT\s+value="FIRSTNAME"\s*/?\]', GIVEN, body, flags=re.I)
    body = re.sub(r'\[[^\[\]]*\]', '', body)          # 其余标签
    parts = [p.strip() for p in body.split('\n')]
    s = ''.join(p for p in parts if p)
    s = s.replace('\u3000', '\u3000').strip()
    return s


TOKEN = re.compile(r'\[message\b([^\]]*)\](.*?)\[/message\]|\[select\b([^\]]*)\]', re.I | re.S)


def extract_file(path):
    raw = open(path, 'rb').read().decode('cp932', 'replace')
    # 去掉整行注释（; 开头）与行首标签行残留 —— 注释行里可能有 [message] 占位
    lines = []
    for ln in raw.split('\n'):
        if ln.lstrip().startswith(';'):
            continue
        lines.append(ln)
    text = '\n'.join(lines)

    out = []
    for m in TOKEN.finditer(text):
        if m.group(2) is not None:
            s = parse_body(m.group(2))
        else:
            w = re.search(r'word="([^"]*)"', m.group(3))
            s = w.group(1).strip() if w else ''
            s = re.sub(r'\[[^\[\]]*\]', '', s).strip()
        if s:
            out.append(s)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    files = sorted(os.listdir(src), key=order_key)
    lines = []
    stat = []
    for fn in files:
        if not fn.endswith('.ks') or fn in SKIP_FILES:
            continue
        got = extract_file(os.path.join(src, fn))
        stat.append((fn, len(got)))
        lines.extend(got)
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('files %d, lines %d, chars %d' % (len(stat), len(lines), sum(len(x) for x in lines)))
    print('empty files:', [s for s in stat if s[1] == 0][:10])


if __name__ == '__main__':
    main()
