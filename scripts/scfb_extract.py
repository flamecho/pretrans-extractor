# -*- coding: utf-8 -*-
"""[JP]Silver Chaos Fan Box -Eternal Fantasia- 文本抽取

引擎：VividColor GameSystem（CMP 容器 = PE 壳 0x6400 + u32 raw + LZSS 变体 + 尾部 u32 索引偏移）
成行：一条 <RESOURCE>（首参 0）＋ 紧随 <FUNCTION name="MESSAGE"/> ＝ 一次点击 ＝ 一行
      一条 <RESOURCE>（首参 1）＋ <FUNCTION name="SELECT"/> ＝ 选项组（每项一行）
      SETQUIZQUESTION / SETQUIZANSER ＝ 小游戏题干/选项（[QUESTION]/[ANSER] 配置实测上屏）

用法：python scripts/scfb_extract.py <SCRIPT.CMP> <out.txt> [--no-quiz]
"""
import sys
import struct
import collections
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_cmp as P

PAYLOAD_START = 0x6400
QUIZ_FN = ('SETQUIZQUESTION', 'SETQUIZANSER')


def walk_members(d):
    idx = struct.unpack_from('<I', d, len(d) - 4)[0]
    off = PAYLOAD_START
    out = []
    while off < idx:
        raw = struct.unpack_from('<I', d, off)[0]
        body, used = P.decompress(d[off + 4:], out_len=raw)
        out.append((off, raw, used, body))
        off += 4 + used
    return idx, off, out


def main():
    cmp_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    with_quiz = '--no-quiz' not in sys.argv

    d = cmp_path.read_bytes()
    idx, end, members = walk_members(d)

    stats = collections.Counter()
    per_file = []
    lines = []
    problems = []

    for mi, (off, raw, used, body) in enumerate(members):
        try:
            root = ET.fromstring(body)
        except ET.ParseError as e:
            problems.append('xml parse fail @%d: %s' % (mi, e))
            continue
        stats['xml_ok'] += 1
        parent = {c: p for p in root.iter() for c in p}
        n0 = n1 = nq = 0
        for e in root.iter():
            if e.tag == 'RESOURCE':
                cs = list(e)
                if not cs:
                    continue
                first = cs[0].text
                if first == '0':
                    body_str = next((c.text or '' for c in cs if c.get('type') == 'STR'), None)
                    if body_str is None:
                        problems.append('RESOURCE(0) without STR @%d no=%s' % (mi, e.get('no')))
                        continue
                    lines.append(body_str)
                    n0 += 1
                    sibs = list(parent[e])
                    i = sibs.index(e)
                    nxt = sibs[i + 1] if i + 1 < len(sibs) else None
                    if nxt is None or nxt.tag != 'FUNCTION' or nxt.get('name') != 'MESSAGE':
                        problems.append('RESOURCE(0) not followed by MESSAGE @%d' % mi)
                elif first == '1':
                    strs = [c.text or '' for c in cs if c.get('type') == 'STR']
                    lines.extend(strs)
                    stats['opt_groups'] += 1
                    stats['opt_items'] += len(strs)
                    n1 += len(strs)
                    sibs = list(parent[e])
                    i = sibs.index(e)
                    nxt = sibs[i + 1] if i + 1 < len(sibs) else None
                    if nxt is None or nxt.tag != 'FUNCTION' or nxt.get('name') != 'SELECT':
                        problems.append('RESOURCE(1) not followed by SELECT @%d' % mi)
            elif e.tag == 'FUNCTION' and e.get('name') in QUIZ_FN:
                if not with_quiz:
                    continue
                t = next((c.text or '' for c in e if c.get('type') == 'STR'), None)
                if t is None:
                    problems.append('%s without STR @%d' % (e.get('name'), mi))
                    continue
                lines.append(t)
                if e.get('name') == 'SETQUIZQUESTION':
                    nq += 1
                    stats['quiz_q'] += 1
                else:
                    stats['quiz_a'] += 1
        per_file.append((mi, off, raw, n0, n1, nq))

    out_path.write_text('\ufeff' + '\n'.join(lines) + '\n', encoding='utf-8', newline='\n')

    print('members=%d payload=[0x%x,0x%x) walk_end=0x%x idx=0x%x %s'
          % (len(members), PAYLOAD_START, idx, end, idx, 'OK' if end == idx else 'MISMATCH'))
    print('xml_ok=%d lines=%d dialogue=%d opt_items=%d opt_groups=%d quiz_q=%d quiz_a=%d'
          % (stats['xml_ok'], len(lines), len(lines) - stats['opt_items'] - stats['quiz_q'] - stats['quiz_a'],
             stats['opt_items'], stats['opt_groups'], stats['quiz_q'], stats['quiz_a']))
    print('empty=%d nl=%d problems=%d' % (
        sum(1 for x in lines if not x),
        sum(1 for x in lines if '\n' in x or '\r' in x),
        len(problems)))
    for p in problems[:10]:
        print('  !', p)
    print('per-member: idx off raw dialogue opts quiz')
    for row in per_file:
        print('  s%02d %7d %8d %4d %3d %3d' % row)


if __name__ == '__main__':
    main()
