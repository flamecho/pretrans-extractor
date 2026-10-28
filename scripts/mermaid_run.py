#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""マーメイドプリズム (PS2-JP) 全文本提取。

链路：ISO9660 -> ADVIMG.ADP（538 条目）-> 条目内嵌 VML（0x20 头 + op 流 + JIS7 字符串池）
成行：0x66 = 一枠（＝一次点击）起点；0x68 = 正文段；0x69/0x6c = 同框换行/接续（合并）；
      0x6a/0x6b = 主角 姓/名 宏；0x64/0x65 = 名札（独立名字窗，丢弃）；
      0x1f6 [idx][textid] = 选项，0x1f7 = 选项结束。
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mermaid_scan as MS
import mermaid_vml as V

NAME_SEI = '\u901f\u6c34'   # 速水
NAME_MEI = '\u77b3'         # 瞳
NAME_RUI = '\u30eb\u30a4'   # ルイ（異世界名）


def blocks(d, s, T, C):
    """把一段 VML 切成 [(msgid, [textpieces], [options])]。"""
    strs = V.parse_strings(d, s, T, C)
    seq = V.ops_of(d, s, T)
    out = []
    cur = None
    for p, op, a in seq:
        if op == 0x66:
            if cur is not None:
                out.append(cur)
            cur = {'msg': None, 'parts': [], 'opts': []}
        elif cur is None:
            continue
        elif op == 0x190:
            cur['msg'] = a
        elif op == 0x68:
            if a < len(strs):
                cur['parts'].append(strs[a])
        elif op == 0x6a:
            cur['parts'].append(NAME_SEI)
        elif op == 0x6b:
            cur['parts'].append(NAME_MEI)
        elif op == 0x6c:
            cur['parts'].append(NAME_RUI)
        elif op == 0x1f6:
            # 选项：8 字节记录，第二字为文本 id
            tid = struct.unpack_from('<I', d, s + p + 8)[0]
            if tid < len(strs):
                cur['opts'].append(strs[tid])
    if cur is not None:
        out.append(cur)
    return out


def entry_order(e):
    nm = e['name']
    if nm.startswith('S') and nm[1:].isdigit():
        return (0, int(nm[1:]))
    return (1, nm)


def vml_blocks(d, s, T, C):
    """取该 VML 的有效块序列（含选项），并在 msgid 回退处切分副本。

    同一 VML 内常见「完整版 + 短缩版」两份（msgid 完全相同、后份更短），
    属互斥分支的多版本正文 ⇒ 只保留首份（完整）；首份之后若出现全新 msgid 再补入。
    """
    bs = blocks(d, s, T, C)
    seen = set()
    cut = None
    for i, b in enumerate(bs):
        m = b['msg']
        if m not in (0xFFFFFFFF, -1):
            if m in seen:
                cut = i
                break
            seen.add(m)
    if cut is None:
        return bs
    # 副本常以若干 msgid=-1 的重复句开头：按文本相似度向前扩切点
    import difflib
    texts = [''.join(b['parts']) for b in bs]
    while cut > 0:
        prev = texts[cut - 1]
        if not prev:
            break
        best = 0.0
        for k in range(max(0, cut - 120), cut - 1):
            r = difflib.SequenceMatcher(None, prev, texts[k]).ratio()
            if r > best:
                best = r
        if best < 0.75:
            break
        cut -= 1
    head = bs[:cut]
    tail = []
    for b in bs[cut:]:
        if b['msg'] not in (0xFFFFFFFF, -1) and b['msg'] not in seen:
            tail.append(b)
            seen.add(b['msg'])
    return head + tail


def main():
    f = open(MS.ISO, 'rb')
    ent = MS.adp_entries(f)
    parsed = []
    for e in ent:
        f.seek(e['off'])
        d = f.read(e.get('span', e['size']))
        vmls = V.find_vml(d)
        if not vmls:
            continue
        seq = []
        first = None
        for s, T, C in vmls:
            for b in vml_blocks(d, s, T, C):
                t = ''.join(b['parts']).strip()
                if t:
                    seq.append((b['msg'], t))
                for o in b['opts']:
                    seq.append(('OPT', o.strip()))
                if first is None and b['msg'] not in (0xFFFFFFFF, -1):
                    first = b['msg']
        parsed.append((first if first is not None else 1 << 30, e['name'], seq))
    parsed.sort(key=lambda x: (x[0], x[1]))
    out = sys.argv[1] if len(sys.argv) > 1 else '_work_mp/mermaid_raw.txt'
    n = 0
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as w:
        for _, nm, seq in parsed:
            for m, t in seq:
                if t:
                    w.write(t + '\n')
                    n += 1
    print('lines', n, 'entries', len(parsed))
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w', encoding='utf-8') as w:
            for first, nm, seq in parsed:
                w.write('%s\t%d\t%d\n' % (nm, first, len(seq)))


if __name__ == '__main__':
    main()
