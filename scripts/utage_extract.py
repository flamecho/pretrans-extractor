#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ハンサムロンダリング -the mystic lover- (NS / Unity + Utage) 剧本文本提取。

数据来源：romfs `Data/sharedassets1.assets`（SerializedFile）里 251 个 Utage `.book`
MonoBehaviour（`AdvImportScenarioSheet` 的二进制 book 格式，参考 storycraft/unity-utage-book）。

链路：
  XCI(secure @0x1F033) → NCA(section1, LZ4 桶树) → romfs → Data/sharedassets1.assets
  → UnityPy 取 MonoBehaviour 原始字节 → dd_utage.parse_book → 按章节表顺序成行

切行判据（L0）：Utage「一个 Text 命令行 = 一个 AdvPage = 一次点击」；单元格内 `\\n`
为框内排版换行 ⇒ 合并进同一行（详见解析报告「切行判据三行」）。

用法：
  python scripts/utage_extract.py <sharedassets1.assets> --out <txt> [--json <dump.json>]
"""
import sys, os, re, json, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import UnityPy
from dd_utage import parse_book

TEXT_CMDS = ('', 'Text', 'TextMultiVoice', 'TextVoiceIfDefaultName')
SEL_CMD = 'Selection'
# 主角名（可改名）宏 → 官方默认名（外部核对：天近美鈴＝学園秘密篇 / 天近綾乃＝禁断の幽香篇）
PARAMS = {
    'familyNameBirds': '天近',
    'nameBirds': '美鈴',
    'familyNameCats': '天近',
    'nameCats': '綾乃',
}
TAG_PAT = re.compile(r'</?(?:ruby|tips|color|size|speed)[^>]*>')


def clean(text):
    for k, v in PARAMS.items():
        text = text.replace('<param=%s>' % k, v)
    text = TAG_PAT.sub('', text)
    # 框内排版换行：`\n` + 紧随的全角缩进一并去掉（同一行）
    text = re.sub(r'\\n\u3000?', '', text)
    text = text.replace('\\n', '')
    return text.strip('\u3000 \t')


def read_str(d, p):
    n = struct.unpack_from('<I', d, p)[0]
    p += 4
    s = d[p:p + n].decode('utf-8', 'replace')
    p += n + ((4 - n % 4) % 4)
    return s, p


def read_chapter_order(d):
    """Boot.chapter：{7×u32}{name:str}{label:str}{count:u32}{count×PPtr(u32 fileID,u64 pathID)}"""
    p = 0x1c
    name, p = read_str(d, p)
    label, p = read_str(d, p)
    cnt = struct.unpack_from('<I', d, p)[0]
    p += 4
    ids = []
    for _ in range(cnt):
        fid, pid = struct.unpack_from('<Iq', d, p)
        p += 12
        ids.append(pid)
    return name, ids


def main():
    src = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None

    env = UnityPy.load(src)
    books, order = {}, None
    for o in env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        d = o.get_raw_data()
        if len(d) < 0x40:
            continue
        if order is None and len(d) > 0x40:
            try:
                n0 = struct.unpack_from('<I', d, 0x1c)[0]
                if 8 < n0 < 64 and d[0x20:0x20 + n0].endswith(b'.chapter'):
                    order = read_chapter_order(d)[1]
                    continue
            except Exception:
                pass
        try:
            b = parse_book(d)
        except Exception:
            continue
        if b['name'].endswith('.book') and b['end'] == len(d):
            b['path_id'] = o.path_id
            books[b['name']] = b

    print('[i] books=%d chapterOrder=%s' % (len(books), 'yes' if order else 'no'))
    names = sorted(books)
    if order:
        seq = [n for n in (next((k for k, v in books.items() if v['path_id'] == pid), None) for pid in order) if n]
    else:
        seq = names
    assert len(seq) == len(set(seq)), '章节表有重复'

    lines = []
    stat = {}
    for nm in seq:
        if not nm.startswith('Episode_'):
            continue
        b = books[nm]
        cnt = 0
        for sh in b['sheets']:
            rows = sh['rows']
            hrow = sh['header_row']
            if not rows or hrow >= len(rows):
                continue
            cols = {c.strip(): i for i, c in enumerate(rows[hrow]['cells'])}
            ti = cols.get('Text', 8)
            for r in rows:
                if r is rows[hrow] or r['comment']:
                    continue
                cells = r['cells']
                if not cells:
                    continue
                cmd = cells[0]
                if cmd.startswith('*'):
                    continue
                if cmd not in TEXT_CMDS and cmd != SEL_CMD:
                    continue
                if ti >= len(cells):
                    continue
                t = clean(cells[ti])
                if not t:
                    continue
                lines.append(t)
                cnt += 1
        stat[nm] = cnt

    print('[i] books with text=%d  lines=%d' % (sum(1 for v in stat.values() if v), len(lines)))
    if js:
        json.dump({'order': seq, 'stat': stat, 'lines': lines}, open(js, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[i] -> %s (%d lines)' % (out, len(lines)))


if __name__ == '__main__':
    main()
