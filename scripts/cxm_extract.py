# -*- coding: utf-8 -*-
"""Collar x Malice for Nintendo Switch (NS-JP) 全文本提取

容器：rar → NSP(PFS0) → Program NCA（body 明文，KeyArea 0/1/3 全 0）
     → RomFS → CONTENTS/{STORY_01,STORY_02}.cpk → SCRIPT/*.DAT
引擎：STCM2L `May 18 2015 17:17:25` / UTF-8

★ 断行判据（唯一，L0 结构级；见 S4-stcm2l-cases.md「一行 ＝ 一段连续 BODY 记录」）

    记录流按 `[pre][TAG][N][size]` 步进（步进 = size）。
    BODY = 文本记录 且 TAG == 本文件正文 TAG。
      · 相邻的两条 BODY        ⇒ 同一显示行的前后半段 ⇒ **合并**
      · 两条 BODY 之间夹任何记录 ⇒ **新行**（无论夹的是空记录 / 命令 / 0x1F4）

    **不用** 0x1F4 当断行码（本作它是段落/页面级，稀疏且不均）；
    **不用** 字数、行宽、框容量、括号配平 —— 渲染层猜测，已由用户明令禁止。

正文 TAG：结构量选出（相邻次数最多 + 总字数最多），见 cxm_stream.body_tag。
"""
import os, re, sys, json
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib.cxm_stream import records, body_tags

ROOT = os.path.join(VNTRANS_HOME, '_w_cxm')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]Collar x Malice for Nintendo Switch.txt')
HEROINE = '市香'

TAG = re.compile(r'#[A-Za-z]+\[[^\]]*\]')
NL = re.compile(r'#n')


def clean(s):
    """剥富文本标记与记录内换行（`#n` 是记录内排版换行，合并成一行后无意义）"""
    s = s.replace('#Name[1]', HEROINE)
    s = TAG.sub('', s)
    s = NL.sub('', s)
    return s.replace('\\n', '')


def build():
    rows = []
    st = {'files': 0, 'records': 0, 'body': 0, 'merged': 0, 'tags': {}}
    for sub in ('story1', 'story2'):
        sd = os.path.join(ROOT, sub, 'SCRIPT')
        if not os.path.isdir(sd):
            continue
        for f in sorted(os.listdir(sd)):
            if not f.endswith('.DAT'):
                continue
            st['files'] += 1
            d = open(os.path.join(sd, f), 'rb').read()
            rec = records(d)
            st['records'] += len(rec)
            bts = set(body_tags(rec))
            st['tags'][sub + '/' + f] = [hex(t) for t in sorted(bts)]
            if not bts:
                continue
            cur = ''
            prev_body = False
            for i, pre, tag, size, txt in rec:
                if txt is not None and tag in bts:
                    st['body'] += 1
                    piece = clean(txt)
                    if prev_body:
                        # 同一显示行被拆成前后半段：后半段开头的排版缩进去掉
                        cur += piece.lstrip('\u3000')
                        st['merged'] += 1
                    else:
                        cur = piece
                    prev_body = True
                else:
                    if cur.strip():
                        rows.append(cur.lstrip('\u3000'))
                    cur = ''
                    prev_body = False
            if cur.strip():
                rows.append(cur.lstrip('\u3000'))
    return [r for r in rows if r.strip()], st


if __name__ == '__main__':
    rows, st = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(rows) + '\n')
    import collections
    tg = collections.Counter(t for v in st['tags'].values() for t in v)
    print(json.dumps({'files': st['files'], 'records': st['records'], 'body': st['body'],
                      'merged_adjacent': st['merged'], 'out': len(rows),
                      'chars': sum(len(x) for x in rows),
                      'tag_kinds': len(tg), 'top_tags': tg.most_common(6)},
                     ensure_ascii=False))
