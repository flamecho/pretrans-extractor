"""スクール・ウォーズ ～全巻パック 本編＆卒業戦線～ (PSV, QuinRose / Courier "KS" engine)

KS.QPK (QPI index) → 278 KAG-like .ks scripts (CP932)
  [message window="togaki|kyara|heroine|monologue" name="…" …]
  <tab>text line[br]
  [/message]
  [select word="…"] / [select name="….png"]  (image buttons, skipped)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpk import QPK  # noqa: E402

FIRSTNAME = '栞'          # vndb v10950 / v12019: 一条 栞（可改名，默认 栞）
SKIP_FILES = {'trophy.ks', 'sc1_endroll.ks', 'sc2_endroll.ks',
              'op_movie.ks', 'sc1_fri_cal.ks',
              'prologue.ks'}   # 名字输入框＋按键说明＋跳过设定向导＝系统 UI

INLINE_F = re.compile(r'\[f size="\d+"\]|\[/f\]')
PRINT = re.compile(r'\[print value="firstname"\]')


def clean(text):
    t = text.replace('[br]', '')
    t = INLINE_F.sub('', t)
    t = PRINT.sub(FIRSTNAME, t)
    t = re.sub(r'\[[^\]]*\]', '', t)          # any other inline tag
    return t.strip(' \t\u3000')


def parse_ks(txt, out, stats):
    lines = txt.split('\r\n')
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if s.startswith(';'):
            i += 1
            continue
        if s.startswith('[message'):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith('[/message]'):
                inner = lines[i]
                if inner.strip().startswith(';'):
                    i += 1
                    continue
                if re.fullmatch(r'\s*\[[a-z/][^\]]*\]\s*', inner):
                    i += 1          # standalone block tag inside body
                    continue
                buf.append(inner.strip(' \t\u3000'))
                i += 1
            i += 1                   # consume [/message]
            # 一次点击＝一行：块内换行（[br]/裸换行）只是排版换行，直接拼接。
            text = clean(''.join(buf))
            if text:
                out.append(text)
                stats['msg'] += 1
            else:
                stats['empty'] += 1
            continue
        if s.startswith('[select '):
            m = re.search(r'word="([^"]*)"', s)
            if m:
                out.append(clean(m.group(1)))
                stats['opt'] += 1
            else:
                stats['opt_img'] += 1
            i += 1
            continue
        i += 1


def main(qpi, qpk_path, out_path):
    q = QPK(qpi, qpk_path)
    # 1) 收集（跳过 AKB 二进制条目 / 系统・开发脚本）
    items = []
    for idx, e in enumerate(q.entries):
        raw = q.extract(e)
        if raw[:3] == b'AKB':
            continue
        txt = raw.decode('cp932')
        name = txt.split('\r\n')[0].lstrip('; ').strip()
        if name in SKIP_FILES or name.startswith('開発用テスト'):
            continue
        items.append((idx, name, txt))
    # 2) 排序：本編 / 卒業戦線 各篇内「prologue → op01..03 → 源内登记顺序」
    #    （依据：prologue=「私の名前は？」名字输入＝开局；trophy.ks ▼1＝本編/オープニングを見た）
    split = next(i for i, (idx, nm, _) in enumerate(items) if nm == 'sc2_count.ks')
    head_order = {'prologue.ks': 0, 'op01.ks': 1, 'op02.ks': 2, 'op03.ks': 3}
    keyed = []
    for pos, (idx, nm, txt) in enumerate(items):
        part = 0 if pos < split else 1
        keyed.append(((part, head_order.get(nm, 9) if part >= 0 else 9, pos), nm, txt))
    keyed.sort(key=lambda x: x[0])

    out = []
    stats = {'msg': 0, 'opt': 0, 'opt_img': 0, 'empty': 0, 'files': 0}
    used = []
    for _, nm, txt in keyed:
        before = len(out)
        parse_ks(txt, out, stats)
        if len(out) > before:
            stats['files'] += 1
            used.append((nm, len(out) - before))
    data = '\n'.join(out) + '\n'
    with open(out_path, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + data.encode('utf-8'))
    print('files', stats['files'], 'msg', stats['msg'], 'opt', stats['opt'],
          'opt_img(skip)', stats['opt_img'], 'empty', stats['empty'])
    print('lines', len(out))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
