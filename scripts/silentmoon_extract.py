# -*- coding: utf-8 -*-
"""Silent Moon (Boys3) 正文提取：ACT_A..H.txt + 同名 .spt 记录。
L0: op=1 = 一个文本框 = 一次点击；p1!=0x0d 时首行为独立名札（丢弃），其余为框内折行（合并）。
"""
import struct, re, os, io, json, collections, argparse
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

ap = argparse.ArgumentParser()
ap.add_argument('--dec', default=os.path.join(VNTRANS_HOME, '_work_silentmoon/dec'))
ap.add_argument('--out', default=os.path.join(VNTRANS_HOME, '提取结果/[JP]Silent Moon.txt'))
ap.add_argument('--stats', default=os.path.join(VNTRANS_HOME, '_work_silentmoon/extract_stats.json'))
A = ap.parse_args()
BASE = A.dec
OUT = A.out
INDENT = '\u3000'

stats = collections.Counter()
rows = []
per_letter = collections.Counter()
option_rows = []

def spt_records(sp):
    b = open(os.path.join(BASE, sp), 'rb').read()
    n = struct.unpack_from('<I', b, 0)[0]
    return [struct.unpack_from('<8I', b, 4 + 32 * k) for k in range(n)]

def merge_body(body):
    """框内折行合并；续行首的全角空格＝悬挂缩进，剥 1 个（首行保留）。"""
    assert body
    s = body[0]
    for x in body[1:]:
        if x.startswith(INDENT):
            x = x[1:]
            stats['stripped_indent'] += 1
        s += x
    return s

for letter in 'ABCDEFGH':
    path = os.path.join(BASE, 'ACT_%s.txt' % letter)
    lines = [x.decode('cp932') for x in open(path, 'rb').read().split(b'\r\n')]
    labels = [(i, l) for i, l in enumerate(lines) if l.startswith('***')]
    seen = set()
    for pos, lab in labels:
        m = re.match(r'\*\*\*(SC|SL)_([A-Z]\d{4})_(\d+)', lab)
        if not m:
            continue
        kind, base_id, sid = m.group(1), m.group(2), m.group(3)
        sp = '%s_%s.spt' % (base_id, sid)
        if sp in seen or not os.path.exists(os.path.join(BASE, sp)):
            continue
        seen.add(sp)
        for k, r in enumerate(spt_records(sp)):
            op, p1, p2, p3, off, cnt, p6, p7 = r
            if op != 1:
                continue
            body = lines[off:off + cnt]
            if p1 != 0x0d:
                body = body[1:]          # 独立名札行整体丢弃
            stats['boxes'] += 1
            stats['bodylines'] += len(body)
            if not body:
                stats['empty_box'] += 1
                continue
            if kind == 'SL':
                # 选项块：一行一条，不合并
                n_opt = 0
                for x in body:
                    if x.strip():
                        rows.append(x)
                        option_rows.append(x)
                        n_opt += 1
                stats['sl_boxes'] += 1
                stats['options'] += n_opt
                per_letter[letter] += n_opt
            else:
                merged = merge_body(body)
                if len(body) >= 2:
                    stats['multi_boxes'] += 1
                stats['chars'] += len(merged)
                rows.append(merged)
                per_letter[letter] += 1
                if p1 != 0x0d:
                    stats['dia_rows'] += 1
                else:
                    stats['nar_rows'] += 1

text = '\n'.join(rows) + '\n'
with open(OUT, 'wb') as f:
    f.write(b'\xef\xbb\xbf' + text.encode('utf-8'))

# 统计与自检
stats['rows'] = len(rows)
stats['chars_file'] = len(text)
stats['lines_file'] = len(rows)
stats['q_open'] = text.count('「'); stats['q_close'] = text.count('」')
stats['p_open'] = text.count('（'); stats['p_close'] = text.count('）')
stats['dup_adjacent'] = sum(1 for i in range(1, len(rows)) if rows[i] == rows[i-1])
bad_q = [i for i, l in enumerate(rows) if l.count('「') != l.count('」')]
bad_p = [i for i, l in enumerate(rows) if l.count('（') != l.count('）')]
stats['row_q_unbal'] = len(bad_q); stats['row_p_unbal'] = len(bad_p)
report = dict(stats=dict(stats), per_letter=dict(per_letter),
              options=option_rows, q_unbal_rows=[(i+1, rows[i][:80]) for i in bad_q][:10])
with open(A.stats, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print('rows', len(rows), 'chars', stats['chars'], 'opts', stats['options'])
print('q', stats['q_open'], stats['q_close'], 'p', stats['p_open'], stats['p_close'],
      'unbal rows', len(bad_q), len(bad_p))
