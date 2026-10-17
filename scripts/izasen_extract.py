#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""いざ、出陣！恋戦（PSP）全文本提取：逻辑流 → KAG 脚本 → 正文/选项

输入：izasen_stream.py 产出的 stream.bin（data.cpk 数据区按 2048 块拼接后的逻辑字节流）
输出：一行一次点击（[message] 块＝一行，块内 [br] 合并）；选项 [selectb word="…"] 一行一条

主角默认名：御柳 華（みやなぎ はな）⇒ [familyname]=御柳 / [firstname]=華
"""
import re
import sys

FAMILY = '御柳'
FIRST = '華'

PROT = re.compile(r'\[message([^\]]*)\](.*?)\[/message\]', re.S)
OPT = re.compile(r'\[selectb\s+word="([^"]*)"[^\]]*\]')
HDR = re.compile(rb'(?:^|(?<=[\r\n\x00])); ([A-Za-z0-9_\-]+\.ks)\r?\n')
DROP = re.compile(r'^(profile_.*|.*_check\d*\.ks|all_break.*\.ks|endroll_.*\.ks)$')
INLINE_DROP = re.compile(r'\\?\[(?:br|f|/f|se\d?|se\d*\s[^\]]*|ruby|/ruby|shake|flash|clearmessage)[^\]]*\]')


def clean(body):
    s = body
    s = s.replace('\r', '')
    s = s.replace('[br]', '')
    s = re.sub(r'\[/?(?:f|ruby)(?:\s[^\]]*)?\]', '', s)
    s = re.sub(r'\[(?:se\d?|shake|flash|clearmessage|wait)(?:\s[^\]]*)?\]', '', s)
    s = s.replace('[familyname]', FAMILY).replace('[firstname]', FIRST)
    s = s.replace('[inputname]', '')
    s = s.replace('\t', '')
    s = re.sub(r'[ \u3000]+$', '', s)
    s = s.strip(' \u3000')
    return s


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = open(src, 'rb').read()
    marks = list(HDR.finditer(data))
    bounds = [(m.start(), data.find(b'\n', m.start()) + 1, m.group(1).decode('ascii')) for m in marks]
    lines = []
    stats = {}
    for i, (start, hend, name) in enumerate(bounds):
        end = bounds[i + 1][0] if i + 1 < len(bounds) else len(data)
        if DROP.match(name):
            continue
        seg = data[hend:end]
        text = seg.decode('cp932', 'replace')
        for m in re.finditer(r'\[message([^\]]*)\](.*?)\[/message\]|\[selectb\s+word="([^"]*)"[^\]]*\]', text, re.S):
            if m.group(3) is not None:
                w = m.group(3).strip()
                if w:
                    lines.append(w)
                    stats['opt'] = stats.get('opt', 0) + 1
                continue
            body = clean(m.group(2))
            if not body or body in ('\n',):
                continue
            body = re.sub(r'\n+', '', body)
            lines.append(body)
            stats['msg'] = stats.get('msg', 0) + 1
    with open(dst, 'wb') as fh:
        fh.write('\ufeff'.encode('utf-8') + ('\n'.join(lines) + '\n').encode('utf-8'))
    print('lines', len(lines), stats)


if __name__ == '__main__':
    main()
