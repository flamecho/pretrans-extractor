#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""赤い砂堕ちる月 (PC / NScripter + NSLua / Landkarte 2013) 全文本提取 —— 双版对照

链路：ISO(UDF) -> akaisuna/arc.nsa(NScripter NSA) -> scenalio/*.txt(cp932/CRLF)
      nscript.dat = 整文件 XOR 0x84（首行 `;mode800,value1000`）

成行口径（全部 L0，取自脚本本身）
--------------------------------
`lua/define_070textwindow.txt` 的 `parse_text()` 只看**一行正文的最后一个字符**：
    `＠`/`@`  -> is_click=1, is_page=0, is_br=1  ==> **B 类：框内等待点击，不清框**
    `￥`/`\`  -> is_click=1, is_page=1, is_br=0  ==> **A 类：清框换页**
    `／`/`/`  -> is_click=0, is_page=0, is_br=0  ==> 同行续写（软，不断行）
    其它       -> is_click=0, is_page=0, is_br=1  ==> 同框软换行（合并）
`nscript.txt:5120` `click_letter "」" "。" "）"`：行尾为这三个字之一 ⇒ 自动按 A 类
（is_click=1,is_page=1,is_br=0）。`numalias wd_row,3`＋`parse_text` 溢出 textclear
⇒ 框最多 3 行（实测源已自守，最长框恰 3 行）。

框＝A 类之间；段＝框内 B 类切分。双版对照＝同框 ≥2 段时「段1,段2,…,合并行」。
`●選択肢・名・选项…` 每项单独成行（单段框）；`●戦闘分岐/性格分岐/条件実行/選択分岐`
是**互斥块边界**（同一点击的多版本正文）⇒ 断框，且兄弟块首框同文只留一次。

剔除：`;` 注釈、`＊` 场景标签、`●` 分支指令、`【…】` 名札/立绘/演出标签。
主角名：`regist_replace2 "春霞＃＃＃",$playername`（默认 `春霞`，L3476/L4808）⇒ inline 替换。
注音：`regist_replace` 在运行时把基底语换成 `(基底语/よみ)` 交 `_rubyon`；源文本已是基底语。

用法：python akasuna_pc_extract.py <scenalio目录> <nscript.txt> <out.txt>
"""
import sys, os, re, glob, unicodedata

SKIP_TAGS = re.compile(r'【[^】]*】')
TAG_ONLY = re.compile(r'(?:【[^】]*】)+[＋+]?$')
HERO_PLACEHOLDER = '春霞＃＃＃'
HERO_DEFAULT = '春霞'
BRANCH_END = re.compile(r'・終了$')

STAT = {'row': 0, 'A': 0, 'B': 0, 'soft': 0, 'cont': 0, 'dup': 0}


def norm_compat(t):
    """CJK 互换汉字（U+FA00–FAFF 等）-> 统一汉字。本作 1 处 U+FA10 塚 -> 塚。同一字的编码规范化，非改写。"""
    if not any(0xFA00 <= ord(c) <= 0xFAFF or 0x2F800 <= ord(c) <= 0x2FA1F for c in t):
        return t
    return ''.join(unicodedata.normalize('NFKC', c)
                   if (0xFA00 <= ord(c) <= 0xFAFF or 0x2F800 <= ord(c) <= 0x2FA1F) else c
                   for c in t)


def clean_text(s):
    s = SKIP_TAGS.sub('', s)
    s = s.replace(HERO_PLACEHOLDER, HERO_DEFAULT)
    return norm_compat(s).strip(' \t')


def load_order(nscript_path):
    t = open(nscript_path, 'rb').read().decode('cp932', 'replace')
    return re.findall(r'regist_scenalio\s+"([^"]+)","([^"]+)"', t)


def extract(path, fkey):
    """-> frames=[(segs, dedupe_key|None)], opts=[(pos, text)]"""
    raw = open(path, 'rb').read().decode('cp932')
    frames, opts = [], []
    segs, seg = [], ''
    blk = 0          # 是否在分支区内（0=非分支区）
    uid = 0          # 分支块全局唯一号（不随「終了」归零，避免 key 撞号）
    tag = ''         # 分支标签前缀

    def close_seg():
        nonlocal seg
        if seg:
            segs.append(seg)
        seg = ''

    def close_frame():
        nonlocal segs
        close_seg()
        if segs:
            frames.append((segs, (fkey, tag, uid) if blk else None))
            segs = []

    for line in raw.split('\r\n'):
        s = line.strip(' \t\r')
        if not s:
            continue
        if s[0] in ';；':
            continue
        if s[0] in '＊*':
            close_frame()
            blk, tag = 0, ''
            continue
        if s[0] == '●':
            close_frame()                       # 互斥块边界：先按旧块结框
            if s.startswith('●選択肢・'):
                for o in s.split('・')[2:]:
                    o = clean_text(o)
                    if o:
                        opts.append((len(frames), o))
                blk, tag = 0, ''
                continue
            if BRANCH_END.search(s):            # ●…・終了 = 退出分岐状态
                blk, tag = 0, ''
                continue
            blk = 1
            uid += 1
            tag = s.split('・')[0]
            continue
        if TAG_ONLY.fullmatch(s):
            continue                            # 纯标签行（名札/演出/名字固定）
        body = clean_text(s)
        if not body:
            continue
        STAT['row'] += 1
        last = body[-1]
        if last in '＠@':
            STAT['B'] += 1
            seg += body[:-1]
            close_seg()                         # B 类
        elif last in '￥\\¥':
            STAT['A'] += 1
            seg += body[:-1]
            close_frame()                       # A 类
        elif last in '。」）':
            STAT['A'] += 1
            seg += body
            close_frame()                       # click_letter 自动清框
        elif last in '／/':
            STAT['cont'] += 1
            seg += body[:-1]
        else:
            STAT['soft'] += 1
            seg += body
    close_frame()
    return frames, opts


def render(frames, opts):
    by_pos = {}
    for pos, txt in opts:
        by_pos.setdefault(pos, []).append(txt)

    # 互斥块级去重：同一标签组的兄弟块「整块正文逐字相同」⇒ 只留第一块。
    # 只比第一框不够（多数块首句相同、后文不同），必须整块比。
    skip, group, prev = set(), None, None
    i = 0
    while i < len(frames):
        key = frames[i][1]
        if key is None:
            group = None
            i += 1
            continue
        j = i
        while j < len(frames) and frames[j][1] == key:
            j += 1
        if key[:2] != group:
            group, prev = key[:2], None
        body = '\x00'.join(''.join(frames[k][0]) for k in range(i, j))
        if body and body == prev:
            skip.add(key)                       # 仅「紧邻兄弟块」整块同文才算多版本
            STAT['dup'] += j - i
        else:
            prev = body
        i = j

    out = []
    for i, (segs, key) in enumerate(frames):
        for o in by_pos.get(i, []):
            out.append(o)
        if key in skip:
            continue
        text = ''.join(segs)
        if len(segs) == 1:
            out.append(text)
        else:
            out.extend(segs)
            out.append(text)
    out.extend(by_pos.get(len(frames), []))
    return out


def main(scdir, nscript, dst):
    order = load_order(nscript)
    have = {os.path.basename(p)[:-4]: p for p in glob.glob(os.path.join(scdir, '*.txt'))}
    seq, seen = [], set()
    for _, base in order:
        if base in have and base not in seen:
            seq.append(base)
            seen.add(base)
    seq += [b for b in sorted(have) if b not in seen]

    all_frames, all_opts = [], []
    for fi, base in enumerate(seq):
        frames, opts = extract(have[base], fi)
        off = len(all_frames)
        all_frames.extend(frames)
        all_opts.extend((off + p, t) for p, t in opts)

    lines = render(all_frames, all_opts)
    multi = sum(1 for f, _ in all_frames if len(f) > 1)
    segs = sum(len(f) for f, _ in all_frames)
    click = segs + len(all_opts)
    page = len(all_frames) + len(all_opts)
    print('files=%d frames=%d segs=%d multi=%d opts=%d dup_skip=%d'
          % (len(seq), len(all_frames), segs, multi, len(all_opts), STAT['dup']))
    print('点击版=%d 页版=%d 对照版=%d' % (click, page, len(lines)))
    print('正文行 row=%(row)d A=%(A)d B=%(B)d soft=%(soft)d cont=%(cont)d' % STAT)
    print('闭合 row == segs+soft: %s' % (STAT['row'] == segs + STAT['soft'] + STAT['cont']))
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
