# -*- coding: utf-8 -*-
"""[NS-JP]花笑む彼と & bloom（Him the Smile & Bloom）文本提取 —— Utage（宴）

## 容器链
  源：XCI（0100DEF01D0C6000，1.48 GB）＋ DLC nsp ＋ 更新 nsp 1.1.1
  ⚠ 本作 Program NCA（keygen 2 / key_area_crypto）用 hactool / nstool 解 romfs 都报
    `Failed to read RomFS directory cache!` / `Hash layer 4 failed`（ExeFS 段可解）
    ⇒ 直接用**用户模拟器 dump 的 romfs**：%APPDATA%/eden/dump/0100DEF01D0C6000/romfs
  → `Data/sharedassets1.assets`（16.8 MB）里 6 个 Utage `.book` MonoBehaviour ＋ 2 个 `.chapter`

## 结构（Utage 标准 .book，`dd_utage.parse_book`）
  `Boot.chapter`    → 章节顺序：hanakare(共通) / gin / hok / ten / wat
  `dlc.chapter`     → DLC：hanakare_scenario_dlc
  每个 book = 若干 sheet（= .xls 的 sheet，按出现顺序即剧情顺序）
  表头行：Command | Arg1〜Arg6 | WaitType | Text | PageCtrl | Voice | WindowType | Japanese | English

## 成行判据（L0）
  **一条 Text 命令行 = 一个 AdvPage = 一次点击**；单元格内 `\\n`（含紧随的全角缩进）是框内
  排版换行 ⇒ 合并进同一行（本作格内换行最大 2，`「` 数 ≥2 的格只有 5 个 —— 那是 LINE 消息
  列表 / 引号套引号，仍在同一页）。
  - 正文：Command ∈ ('', 'Text', 'TextMultiVoice', 'TextVoiceIfDefaultName') 且 Text 非空
  - 选项：Command == 'Selection'（Arg1 = `**选项文本`，Text 列同文）
  - 章节标题：Command 以 `*` 开头且 Text 非空（`美波天弥 Ch.01\\n夢見た『いつか』`）⇒ 直接上屏，收；
    同一 sheet 内多条 label 共用同一标题 ⇒ **按 sheet 去重只出一次**
  - 名字：Utage 的名字窗走 Arg1（独立列）⇒ 本作正文未用 Arg1，无需剔除

## 宏
  `<param=familyname_{线}>` / `<param=name_{线}>` → 该线的**官方默认名**（从 Boot.chapter 的
  param 表 `defaultfamilyName_{线}_Japanese` / `defaultName_{线}_Japanese` 读，见 DEFAULTS）
  行内富文本 `<color=…>` `<speed=…>` 剥净；`<ruby=よみ>漢字</ruby>` ⇒ 保留汉字
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import UnityPy
from _lib.dd_utage import parse_book

ROOT = (r'<本地路径>'
        r'/Data/sharedassets1.assets')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]花笑む彼と & bloom.txt')

TEXT_CMDS = ('', 'Text', 'TextMultiVoice', 'TextVoiceIfDefaultName')
SEL_CMD = 'Selection'

# Boot.chapter 的 param 表（path_id 734，偏移 0x797a8 起）读出的官方默认名
DEFAULTS = {
    'wataru': ('碧木', '星利奈'),
    'gin':    ('明石', '亜未'),
    'hokuto': ('春芳', '風花'),
    'tenya':  ('雪平', '実紅'),
}

PARAM_PAT = re.compile(r'<param=(familyname|name)_([A-Za-z]+)>')
RUBY_PAT = re.compile(r'<ruby=[^>]*>(.*?)</ruby>')
TAG_PAT = re.compile(r'</?(?:color|size|speed|ruby|tips|b|i|u)[^>]*>')


def clean(t):
    """剥标记 + 展开主角名宏 + 合并框内换行。"""
    t = RUBY_PAT.sub(r'\1', t)

    def rep(m):
        fam, name = DEFAULTS.get(m.group(2).lower(), ('', ''))
        return fam if m.group(1) == 'familyname' else name
    t = PARAM_PAT.sub(rep, t)
    t = TAG_PAT.sub('', t)
    t = t.replace('\r\n', '\n').replace('\r', '\n').replace('\\n', '\n')
    t = re.sub(r'\n[\u3000 ]*', '', t)      # 框内排版换行（含缩进）⇒ 合并
    return t.strip('\u3000 \t')


def read_str(d, p):
    n = struct.unpack_from('<I', d, p)[0]
    p += 4
    s = d[p:p + n].decode('utf-8', 'replace')
    return s, ((p + n + 3) // 4) * 4


def read_chapter(d):
    """{7×u32}{name:str}{label:str}{count:u32}{count×(u32 fileID, i64 pathID)}"""
    p = 0x1C
    _, p = read_str(d, p)
    _, p = read_str(d, p)
    cnt = struct.unpack_from('<I', d, p)[0]
    p += 4
    ids = []
    for _ in range(cnt):
        _, pid = struct.unpack_from('<Iq', d, p)
        p += 12
        ids.append(pid)
    return ids


def norm(s):
    return re.sub(r'[\s\u3000]', '', s)


def collect(book, out):
    """把一个 book 的所有 sheet 按顺序成行；处理 If/Else 互斥分支去重。

    互斥分支（本作 4 处，L0 判据）：`If familyname_X+name_X==defaultfamilyName_X_Japanese+defaultName_X_Japanese`
      → 字面默认名版 ／ `Else` → `<param=…>` 版 ⇒ 两支**渲染同文** ⇒ 只留一支（留 param 版）。
    判据 = 两支归一化（去空白）后**逐字相等**；不相等（真分支）则两支都收。
    """
    for sh in book['sheets']:
        sname = sh['name'].split(':')[-1]
        if sname.startswith('InputName'):
            continue                                   # 名字输入流程（系统 UI，且 param 展开是示例值）
        rows, hr = sh['rows'], sh['header_row']
        if not rows or hr >= len(rows):
            continue
        cols = {c.strip(): i for i, c in enumerate(rows[hr]['cells'])}
        ti = cols.get('Text', 8)
        title_done = False
        stack = []                                     # [{if:[], else:[], cur:'if'}]
        sink = out

        def emit(t):
            if stack:
                stack[-1][stack[-1]['cur']].append(t)
            else:
                sink.append(t)

        for r in rows:
            if r is rows[hr] or r['comment']:
                continue
            cs = r['cells']
            if not cs:
                continue
            cmd = cs[0]
            if cmd == 'If':
                stack.append({'if': [], 'else': [], 'cur': 'if'})
                continue
            if cmd in ('Else', 'ElseIf'):
                if stack:
                    stack[-1]['cur'] = 'else'
                continue
            if cmd == 'EndIf':
                if not stack:
                    continue
                br = stack.pop()
                a, b = br['if'], br['else']
                if a and b and ''.join(map(norm, a)) == ''.join(map(norm, b)):
                    emit_all = b                        # 互斥版本 ⇒ 只留 param 版
                else:
                    emit_all = a + b
                for t in emit_all:
                    emit(t)
                continue
            if ti >= len(cs) or not cs[ti]:
                continue
            if cmd.startswith('*'):
                if title_done:                          # 同 sheet 多条 label 共用同一标题
                    continue
                title_done = True
            elif cmd not in TEXT_CMDS and cmd != SEL_CMD:
                continue
            t = clean(cs[ti])
            if t:
                emit(t)


def main():
    env = UnityPy.load(ROOT)
    books, order = {}, {}
    for o in env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        d = o.get_raw_data()
        try:
            n0 = struct.unpack_from('<I', d, 0x1C)[0]
            nm = d[0x20:0x20 + n0].decode('utf-8', 'replace')
        except Exception:
            continue
        if nm in ('Boot.chapter', 'dlc.chapter'):
            order[nm] = read_chapter(d)
            continue
        try:
            b = parse_book(d)
        except Exception:
            continue
        if b['name'].endswith('.book') and b['end'] == len(d):
            b['path_id'] = o.path_id
            books[b['name']] = b

    byid = {v['path_id']: k for k, v in books.items()}
    seq = [byid[i] for i in order.get('Boot.chapter', []) if i in byid]
    print('[i] books=%d order=%s' % (len(books), seq), file=sys.stderr)

    rows_out, stat = [], {}
    for nm in seq:
        before = len(rows_out)
        collect(books[nm], rows_out)
        stat[nm] = len(rows_out) - before

    dlc = []
    for i in order.get('dlc.chapter', []):
        nm = byid.get(i)
        if nm:
            collect(books[nm], dlc)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(rows_out + dlc) + '\n')

    print('[i] 本篇 %d 行 %s' % (len(rows_out), stat))
    print('[i] DLC  %d 行' % len(dlc))
    print('[i] 合计 %d 行 -> %s' % (len(rows_out) + len(dlc), OUT))


if __name__ == '__main__':
    main()
