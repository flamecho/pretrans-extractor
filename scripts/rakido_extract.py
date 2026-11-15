"""RAKIDOMania black dog 文本提取器。

素材（scripts/woga_datunpack.py 解出）：
  package.dat → 7 个脚本段（`__label` 分段，UTF-8，标签式 DSL）
  system.dat  → 题库 CSV 段（`stage,id,date,question,correct,w1,w2,w3`）

脚本 DSL：
  __label                      段落标签
  //…                          注释
  ；…                          作者备注（全角分号，不收）
  @@cmd{json}                  演出指令
  @@message{"target":"textMain","label":"名前"}   开始一个文本框
                               （label＝独立名字窗内容，按交付口径不收）
  <TAB>一行文字                 框内的一行；行首的全角空格是排版缩进，合并时剥掉

成行口径：
  一个 @@message 块 ＝ 一个文本框 ＝ 一次点击 ＝ 输出一行；块内各行合并。
  非 TAB 开头的游离正文行（如结局「おしまい」）单独成一行。
  题库每题输出 5 行（题干 + 4 选项），保持原文顺序，不加符号。
"""
import json
import os
import re
import sys

MSG = re.compile(r'^@@message\s*(\{.*\})?\s*$')
IDEO_SP = '\u3000'


def parse_script(path):
    """返回 [(label, [box, …])]。"""
    t = open(path, 'rb').read().decode('utf-8')
    out = []
    cur_label = ''
    boxes = []
    cur = []

    def flush():
        nonlocal cur
        if cur:
            s = ''.join(cur).strip()
            if s:
                boxes.append(s)
            cur = []

    def close_section():
        nonlocal boxes
        flush()
        if boxes:
            out.append((cur_label, boxes))
            boxes = []

    for line in t.split('\n'):
        line = line.rstrip('\r')
        if line.startswith('__'):
            close_section()
            name = line[2:].strip()
            if name:
                cur_label = name
            continue
        if line.startswith('；') or line.startswith(';'):
            continue
        if line.startswith('//'):
            flush()
            continue
        if MSG.match(line):
            flush()
            continue
        if line.startswith('@@'):
            flush()
            continue
        if line.startswith('\t'):
            body = line[1:]
            if body.startswith(IDEO_SP):     # 续行缩进，剥掉一层
                body = body[1:]
            cur.append(body)
            continue
        if not line.strip():
            flush()
            continue
        # 游离正文（无 @@message 指令、无 TAB 前缀，如「サア！…」三连、结局「おしまい」）：
        # 连续多行属于同一个文本框，必须累加后合并，不能每行一框。
        cur.append(line.strip())
    close_section()
    return out


LINE = ('4', '5', '6')


def script_order(lines):
    """游戏流程：开场 → 每条线逐关（事件 → stage 前段/后段）→ 全通。

    `lines` 为实际存在的角色线编号（black dog 是 4/5/6，yellow star 是 1/2/3），
    由 label 集合动态推断，不写死。
    """
    seq = ['start']
    for ln in lines:                       # 多条线并列，线内逐关推进
        for m in range(1, 7):
            seq.append('ev_%s_%d' % (ln, m))           # 事件剧情
            seq.append('stage_%s_%d_start' % (ln, m))  # 挑战前
            seq.append('stage_%s_%d_end' % (ln, m))    # 过关后
    seq.append('allclear')
    return seq


def load_quiz(sysdir, idx):
    rows = []
    seen = set()
    for x in idx:
        if x['kind'] in ('png', 'mp3', 'ogg'):
            continue
        p = os.path.join(sysdir, 'seg%04d.bin' % x['i'])
        if not os.path.exists(p):
            continue
        b = open(p, 'rb').read()
        if not re.match(rb'\d+,\d+,', b):
            continue
        for line in b.decode('utf-8').split('\n'):
            line = line.strip()
            if not line:
                continue
            col = line.split(',')
            if len(col) < 8:
                continue
            qid = (col[0], col[1])
            if qid in seen:
                continue
            seen.add(qid)
            # 8 列＝4 选 1；11 列＝多选题（选项槽固定 7 个，不足留空）⇒ 统一「题干 + 全部非空选项」
            opts = [c.replace('\\n', '') for c in col[4:] if c.strip()]
            rows.append(dict(stage=int(col[0]), id=int(col[1]),
                             q=col[3].replace('\\n', ''), opts=opts))
    rows.sort(key=lambda r: (r['stage'], r['id']))
    return rows


def main():
    pkgdir, sysdir, story_dst, quiz_dst = sys.argv[1:5]
    pidx = json.load(open(os.path.join(pkgdir, '_index.json'), encoding='utf-8'))
    sidx = json.load(open(os.path.join(sysdir, '_index.json'), encoding='utf-8'))

    labeled = {}
    for x in pidx:
        if x['kind'] in ('png', 'mp3', 'ogg', 'json'):
            continue
        p = os.path.join(pkgdir, 'seg%04d.bin' % x['i'])
        if not os.path.exists(p):
            continue
        if not open(p, 'rb').read(4).startswith(b'__'):
            continue
        for label, boxes in parse_script(p):
            labeled.setdefault(label, []).extend(boxes)

    # 角色线编号从 label 动态推断（stage_<线>_<关>_...）
    lines = sorted({m.group(1) for lab in labeled
                    for m in [re.match(r'stage_(\d+)_\d+_', lab)] if m})
    seq = script_order(lines)
    rows = []
    extra = []
    for label in seq:
        if label in labeled:
            rows.extend(labeled[label])
    for label in labeled:
        if label not in seq:
            extra.append(label)
            rows.extend(labeled[label])

    with open(story_dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        for r in rows:
            f.write(r + '\n')

    quiz = load_quiz(sysdir, sidx)
    with open(quiz_dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        for r in quiz:
            f.write(r['q'] + '\n')
            for o in r['opts']:
                f.write(o + '\n')

    print('story: labels=%d boxes=%d -> %d lines' % (len(labeled), len(rows), len(rows)))
    print('quiz : %d questions -> %d lines' % (len(quiz), len(quiz)))
    if extra:
        print('未列入顺序表的 label:', extra)


if __name__ == '__main__':
    main()
