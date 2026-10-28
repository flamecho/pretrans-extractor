# -*- coding: utf-8 -*-
"""BYAKKO ～四神部隊炎恋記～ (NS-JP) 文本提取

记录形状（本作实测，STCM2L 变体）：
  [u32 self_off][u32 0x40000000][u32 0x40000000][u32 op][u32 0x15D][u32 seq][u32 0x10]
  [u32 k=L/4][u32 1][u32 L][utf8 text (NUL pad)]
  [u32 flag][u32 trailer]

op 语义（L0，全 249 脚本统计 7 种）：
  0x133  正文       trailer 0x1F4=本框结束（一次点击） / 0x16D9C=框内续行（软换行，合并）
  0x161..0x165     名札（独立名字窗）         → 丢弃
  0x15F  扉文/章题卡（`共通　序章　白虎`）    → 独占一行
  0x35/0x36/0x136  系统（色変化判定 / lock_xxx / シーン選択）→ 丢弃
选项：`switch` 块内 `[1][L][text]` + 紧随 `[1][L]sureNN`（立绘/语音资源名）
       ⇒ 文本记录后紧跟 sureNN 记录即选项，占一行。
用語辞典：system/DATABASE/dbDictionary.gbin，NUL 分隔三元组（見出し語 / 読み / 解説）。
"""
import argparse
import glob
import os
import re
import struct

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff01-\uff60]')
KANA = re.compile(r'^[ぁ-んァ-ヴー・]+$')
RUBY = re.compile(r'#Ruby\[([^,\]]*),[^\]]*\]')
NAME1, NAME2 = '佐野', 'ゆずりは'
DROP_OPS = {0x35, 0x36, 0x136}
NAME_OPS = {0x161, 0x162, 0x163, 0x164, 0x165}


def scan(d):
    """→ texts（正文/名札/扉文，带 op）/ 选项"""
    n = len(d)
    recs = []
    sure = set()
    for m in re.finditer(rb'sure\d+', d):
        q = m.start() - 8
        if q >= 0 and struct.unpack_from('<I', d, q)[0] == 1:
            sure.add(q)
    i = 0
    while i < n - 12:
        k, one, L = struct.unpack_from('<3I', d, i)
        if one == 1 and L % 4 == 0 and 4 <= L <= 0x8000 and k == L // 4 and i + 20 + L <= n:
            raw = d[i + 12:i + 12 + L].rstrip(b'\x00')
            if raw and all(b >= 0x20 for b in raw) and d[i - 8:i - 4] == b'\x10\x00\x00\x00':
                try:
                    s = raw.decode('utf-8')
                except Exception:
                    s = None
                if s and JP.search(s) and all(ord(c) >= 0x20 for c in s):
                    op = struct.unpack_from('<I', d, i - 20)[0]
                    tr = struct.unpack_from('<I', d, i + 16 + L)[0]
                    recs.append({'i': i, 'end': i + 12 + L, 'op': op, 'tr': tr, 's': s})
                    i += 12 + L
                    continue
        i += 4
    # 选项：文本记录后紧跟 `sureNN`
    opts = []
    seen = set()
    for q in sorted(sure):
        for back in range(8, 0x208, 4):
            p = q - back
            if p < 8:
                break
            one, L = struct.unpack_from('<II', d, p)
            if one != 1 or L % 4 or not (4 <= L <= 0x200):
                continue
            if p + 8 + L > q:
                continue
            gap = d[p + 8 + L:q]
            if len(gap) > 0x20 and any(gap):
                continue
            raw = d[p + 8:p + 8 + L].rstrip(b'\x00')
            try:
                t = raw.decode('utf-8')
            except Exception:
                continue
            if not (JP.search(t) and all(ord(c) >= 0x20 for c in t)):
                continue
            if p not in seen:
                seen.add(p)
                opts.append({'i': p, 's': t})
            break
    return recs, opts


def clean(s):
    s = RUBY.sub(r'\1', s)
    s = s.replace('#Name[1]', NAME1).replace('#Name[2]', NAME2)
    s = s.replace('#n', '')
    return s.strip()


def build(path):
    d = open(path, 'rb').read()
    recs, opts = scan(d)
    stream = [('t', r) for r in recs] + [('o', r) for r in opts]
    stream.sort(key=lambda x: x[1]['i'])
    lines = []
    box = []
    st = {'box': 0, 'name': 0, 'title': 0, 'sys': 0, 'opt': 0}

    def flush():
        nonlocal box
        if box:
            s = clean(''.join(box))
            if s:
                lines.append(s)
                st['box'] += 1
        box = []

    for kind, r in stream:
        if kind == 'o':
            flush()
            s = clean(r['s'])
            if s:
                lines.append(s)
                st['opt'] += 1
            continue
        op, tr = r['op'], r['tr']
        if op in NAME_OPS:
            st['name'] += 1
            continue
        if op == 0x133:
            box.append(r['s'])
            if tr == 0x1F4:
                flush()
        elif op == 0x15F:
            flush()
            s = clean(r['s'])
            if s:
                lines.append(s)
                st['title'] += 1
        else:
            st['sys'] += 1
    flush()
    return lines, st


def dictionary(path):
    d = open(path, 'rb').read()
    parts = [x for x in d.split(b'\x00')]
    strs = []
    for p in parts:
        if len(p) < 2:
            continue
        try:
            t = p.decode('utf-8')
        except Exception:
            continue
        if all(ord(c) >= 0x20 for c in t):
            strs.append(t)
    out = []
    i = 0
    while i + 2 < len(strs) + 1:
        if i + 2 < len(strs) and KANA.match(strs[i + 1]) and not KANA.match(strs[i]):
            head, body = strs[i], strs[i + 2]
            out.append('【%s】%s' % (clean(head), clean(body)))
            i += 3
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--script', default='_w_tri/byakko/story/SCRIPT')
    ap.add_argument('--dict', default='_w_tri/byakko/system/DATABASE/dbDictionary.gbin')
    ap.add_argument('--out', required=True)
    ap.add_argument('--no-dict', action='store_true')
    a = ap.parse_args()

    files = [p for p in sorted(glob.glob(os.path.join(a.script, '*.DAT')),
                               key=lambda p: int(os.path.splitext(os.path.basename(p))[0]))
             if int(os.path.splitext(os.path.basename(p))[0]) >= 100]   # 90/99 = 引擎测试/调试脚本
    lines = []
    tot = {'box': 0, 'name': 0, 'title': 0, 'sys': 0, 'opt': 0}
    for p in files:
        ls, st = build(p)
        lines.extend(ls)
        for k in tot:
            tot[k] += st.get(k, 0)
    dict_lines = [] if a.no_dict else dictionary(a.dict)
    print('files', len(files), 'lines', len(lines), 'dict', len(dict_lines), tot)
    body = '\n'.join(lines + dict_lines) + '\n'
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    open(a.out, 'wb').write(b'\xef\xbb\xbf' + body.encode('utf-8'))


if __name__ == '__main__':
    main()
