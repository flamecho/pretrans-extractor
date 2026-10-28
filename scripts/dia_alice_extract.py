# -*- coding: utf-8 -*-
"""ダイヤの国のアリス ～Wonderful Mirror World～ (PSP) 全文本提取

链路: ISO9660 -> DATA0.cpk (CRI CPK) -> *.ks (cp932 明文 KAG 风格 DSL)
采集: [message ...]...[/message] = 一次点击一块; [br]/裸换行 = 框内软换行合并
      [select word=".."] = 选项; [print value="firstname|familyname"] = 主角名内联
丢弃: name= 属性(独立名字窗) / window= 样式 / face= / voice= / 注释 ; / test*.ks
"""
import os, re, sys, glob

SRC   = os.path.join(os.path.dirname(__file__), '..', '_work_dia', 'd0')
OUT   = os.path.join(os.path.dirname(__file__), '..', '提取结果',
                     '[PSP-JP]ダイヤの国のアリス ～Wonderful Mirror World～.txt')

FIRST = 'アリス'   # [print value="firstname"]  (vndb: Alice Liddell / アリス・リデル)
FAMILY = 'リデル'  # [print value="familyname"]

SKIP = {'test00', 'test01', 'test02', 'test03'}

MSG_RE = re.compile(r'\[message\b[^\]]*\](.*?)\[/message\]', re.S)
SEL_RE = re.compile(r'\[select\b([^\]]*)\]')
TAG_RE = re.compile(r'\[/?(?:br|f)\b[^\]]*\]|\[/f\]')
PRINT_RE = re.compile(r'\[print\b([^\]]*)\]')


def clean(body):
    # 框内注释行（; 起）整行丢弃，其余软换行合并
    body = '\n'.join(l for l in body.split('\r\n') if not l.strip().startswith(';'))
    body = TAG_RE.sub('', body)
    def _p(m):
        a = m.group(1)
        if 'firstname' in a:
            return FIRST
        if 'familyname' in a:
            return FAMILY
        return ''
    body = PRINT_RE.sub(_p, body)
    body = body.replace('\t', '').replace('\r', '').replace('\n', '')
    # 残余注释行（整行以 ; 起）已随换行删除，这里兜底切掉行内 ; 开头的尾巴
    return body.strip()


def parse(path):
    raw = open(path, 'rb').read()
    d = raw.decode('cp932', errors='replace')
    got = []
    for m in MSG_RE.finditer(d):
        s = clean(m.group(1))
        if s:
            got.append((m.start(), s))
    for m in SEL_RE.finditer(d):
        w = re.search(r'word="([^"]*)"', m.group(1))
        if w:
            got.append((m.start(), w.group(1)))
    got.sort(key=lambda x: x[0])
    return [t for _, t in got]


def sort_key(name):
    if name == 'prologue':
        return (0, 0, 0, name)
    if name.startswith('op'):
        return (1, 0, 0, name)
    m = re.match(r'^(com|ace|blo|bor|cry|dad|ell|gra|jer|jul|lake|nig|sid|pet)(\d\d)(_(\d))?(_\w+)?$', name)
    if m:
        pre, ch, _, sub, suf = m.groups()
        pre_order = {'com': 0, 'ace': 1, 'blo': 2, 'bor': 3, 'cry': 4, 'dad': 5,
                     'ell': 6, 'gra': 7, 'jer': 8, 'jul': 9, 'lake': 10, 'nig': 11,
                     'sid': 12, 'pet': 13}[pre]
        return (2, int(ch), pre_order * 10 + (int(sub) if sub else 0), name)
    if '_best' in name or name == 'com_best':
        return (3, 0, 0, name)
    if name == 'endroll':
        return (5, 0, 0, name)
    if name.startswith('mini'):
        return (6, 0, 0, name)
    return (4, 0, 0, name)


def main():
    files = {}
    for p in glob.glob(os.path.join(SRC, '*.ks')):
        files[os.path.basename(p)[:-3]] = p
    names = sorted((n for n in files if n not in SKIP), key=sort_key)
    lines, per = [], []
    for n in names:
        got = parse(files[n])
        per.append((n, len(got)))
        lines.extend(got)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('files', len(names), 'lines', len(lines))
    for n, c in per:
        print('%6d  %s' % (c, n))


if __name__ == '__main__':
    main()
