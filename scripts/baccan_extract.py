#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""爽海バッカニアーズ! 剧本文本提取（テキスト方式ADV / プチレーヴ）。

用法: python scripts/baccan_extract.py <cmp.psarc解包目录> <输出.txt> [--names]

链路：cmp.psarc → script/*.txt (UTF-16LE, 1 行 = 1 步)。
行语义：① 指令行（bgm/image/se/effect/chara/scrlst 标签，或全大写命令、脚本名、裸数字）
       ② 话者名行（短、无句读、且下一个非指令行以「开头）→ 丢弃
       ③ 文本行 → 输出（`\` = 框内软换行 → 合并；<dicNNN>..</dic> 标签剥离留词）
"""
import os, re, sys, glob, collections

# 用法: python scripts/baccan_extract.py <cmp.psarc 解包目录> <输出.txt>
BASE = sys.argv[1] if len(sys.argv) > 1 else '.'
SYS = os.path.join(BASE, 'system')
SCR = os.path.join(BASE, 'script')


def rd(p):
    d = open(p, 'rb').read()
    if d[:2] == b'\xff\xfe':
        return d[2:].decode('utf-16-le', 'replace')
    if d[:3] == b'\xef\xbb\xbf':
        return d[3:].decode('utf-8', 'replace')
    try:
        t = d.decode('utf-8')
        return d.decode('utf-16-le', 'replace') if '\x00' in t else t
    except Exception:
        return d.decode('utf-16-le', 'replace')


def rows(fname):
    return [l for l in rd(os.path.join(SYS, fname)).replace('\r', '').split('\n') if l]


# ---- 指令标签集合 ----
SOFT = set()   # 表现类标签（BG/BGM/SE/演出/表情）—— 名字探测时可跳过
LAB = set()    # 全部指令标签 —— 最终过滤用


def _fillset(dst, fname, cols):
    for l in rows(fname):
        c = l.split(',')
        for i in cols:
            if i < len(c) and c[i].strip():
                dst.add(c[i].strip())


# 表现类（软）
_fillset(SOFT, 'image.csv', [0])
_fillset(SOFT, 'bgm.csv', [0])
_fillset(SOFT, 'se.csv', [0])
_fillset(SOFT, 'effect.csv', [0])
_fillset(SOFT, 'chara.csv', [1, 2, 3])
# 结构/数据类（硬，但同样属于指令，最终过滤）
_fillset(LAB, 'scrlst.csv', [0])
_fillset(LAB, 'talk_mode.csv', [0, 1])
_fillset(LAB, 'talk_text.csv', [0, 1, 2])
_fillset(LAB, 'personal.csv', [0])
_fillset(LAB, 'scene_set.csv', [0, 1, 2])
_fillset(LAB, 'album_set.csv', list(range(0, 8)))
_fillset(LAB, 'eventcg.csv', list(range(0, 8)))

# 少量未登记项（SE/演出/表情变体，人工核对后加入）
EXTRA_INSTR = {'洞窟内での足音1', '人の足音4_走り室内1', 'ビンタ1', 'フレデリック自信21',
               '洞窟内での足音2', 'ビンタ2', '縦揺れ', '横揺れ', '縦横', '移動モード'}
SOFT |= EXTRA_INSTR
LAB |= SOFT | EXTRA_INSTR

RE_CAPS = re.compile(r'^[A-Z][A-Z_0-9]*$')
RE_SCRIPT = re.compile(r'^\d\d_[a-z]+_\d+(_\d+)?$')
RE_SCRIPT2 = re.compile(r'^\d\d_[a-z]+_(move|set|last|end)$')
RE_NUM = re.compile(r'^[0-9]+$')
RE_PUNCT = re.compile(r'[。、！？…「」『』（）]')


def is_soft(l):
    """表现类指令（可被名字探测跳过）。"""
    return l in SOFT


def is_instr(l):
    if not l:
        return True
    if l in LAB:
        return True
    if RE_CAPS.match(l) or RE_SCRIPT.match(l) or RE_SCRIPT2.match(l) or RE_NUM.match(l):
        return True
    return False


def is_speaker_cand(l):
    return len(l) <= 15 and not RE_PUNCT.search(l) and '\\' not in l


def load_scripts():
    order = [x.strip() for x in rows('scrlst.csv') if x.strip()]
    cache = {}
    for name in order:
        p = os.path.join(SCR, name + '.txt')
        if os.path.exists(p):
            cache[name] = rd(p).replace('\r', '').split('\n')
    return order, cache


def lookahead(lines, i):
    """返回 i 之后第一个「非表现类指令」行（只跳过 SOFT 标签；遇结构指令即停）。"""
    j = i + 1
    while j < len(lines) and (not lines[j] or is_soft(lines[j])):
        j += 1
    return lines[j] if j < len(lines) else ''


def mine_names(order, cache):
    """脚本内迭代挖掘「话者名/名札」集合。

    判据：候选短行（无 。、「」『』（） 与 \\）的下一非指令行以「/『/（ 开头，
          或该下一行已经是已知话者名（处理「内部ID + 显示名」双行形态）。
    """
    names = set()
    for _ in range(6):  # 迭代至收敛
        changed = False
        for name in order:
            lines = cache[name]
            for i, l in enumerate(lines):
                if l in names or not is_speaker_cand(l) or is_instr(l):
                    continue
                nxt = lookahead(lines, i)
                if nxt[:1] in ('「', '『', '（') or nxt in names:
                    names.add(l)
                    changed = True
        if not changed:
            break
    return names


def extract_script(name, names, cache):
    """返回该脚本的显示文本行列表（丢弃指令行与话者名行）。"""
    lines = cache[name]
    out = []
    for l in lines:
        if not l or is_instr(l) or l in names:
            continue
        out.append(l)
    return out


def clean(t):
    t = re.sub(r'<dic[0-9]+>', '', t)
    t = t.replace('</dic>', '')
    t = t.replace('\\', '')
    t = t.replace('\uff65', '\u30fb')  # 半角中点 → 全角（原文 02_cr_042 单处，含 6 个 U+FF65）
    return t


def main(outpath, dump_names=False):
    order, cache = load_scripts()
    names = mine_names(order, cache)
    if dump_names:
        print('mined names (%d):' % len(names))
        for w in sorted(names):
            print('   ', w)
        return
    all_lines = []
    for name in order:
        if name not in cache:
            continue
        for l in extract_script(name, names, cache):
            c = clean(l)
            if c:
                all_lines.append(c)
    # 用語辞典：f6=詳細解説（上屏正文）；f5 为「分类+读音」式列表短注，按 §0「不带读音」不取
    dic = []
    for l in rows('dic.csv'):
        c = l.split(',')
        if len(c) >= 7 and c[0].strip():
            head = c[0].strip()
            body = c[6].replace('\\n', '')
            if not body:
                body = c[5].replace('\\n', '')
            dic.append(f'【{head}】{body}')
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(all_lines))
        if dic:
            f.write('\n')
            f.write('\n'.join(dic))
        f.write('\n')
    print(f'scripts={len(order)} textlines={len(all_lines)} dic={len(dic)} -> {outpath}')


if __name__ == '__main__':
    # argv[1] = cmp.psarc 解包目录；argv[2] = 输出路径（或 '--names' 仅导出话者词典）
    if len(sys.argv) > 2 and sys.argv[2] == '--names':
        main(None, dump_names=True)
    else:
        main(sys.argv[2] if len(sys.argv) > 2 else 'out.txt')
