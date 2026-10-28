#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Honey Vibes (NS 0100FB301E70A000) 剧本提取 —— Unity + 纯文本脚本。

链路: romfs/Data/StreamingAssets/Script/*.h (UTF-8) + Setting/{CHOICE,DICT,STORYFLOW}.csv

记录（L1：命令自定界）:
    SET_TALK( 角色ID, WIN, "显示名", 语音ID, "正文" )   ← 一次点击 = 一行
    反斜杠 = 框内软换行 ⇒ 删除并合并；其后若跟全角空格（行首缩进）也一并删
    CHOICE_JUMP( <番号>, ... )                        ← 该点弹选项，选项文本在 CHOICE.csv
    SET_TALK_CLR / WAIT(n) / 其它命令                  ← 演出，不取

取值:
    正文   = SET_TALK 第 5 参数，按 STORYFLOW.csv 的文件顺序拼接
    说话人 = SET_TALK 第 3 参数（表示名）；非空则接在正文前同行（名札印在正文框内）
             主角占位 ＆＆＆＆＆ → PROTAG_NAME
    选项   = CHOICE.csv「選択肢」列（一行一条；「問」与剧本里的 SET_TALK 重复，故不取）
    辞典   = DICT.csv → 末尾 `【WORD】COMMENT`（去读音、条内换行合并）

用法: python scripts/honeyvibes_extract.py <romfs/Data/StreamingAssets> <out.txt>
"""
import csv
import os
import re
import sys

# ---- 以下常量按本作实测，换作需重新核对 ----
PROTAG = '＆＆＆＆＆'          # 主角名占位（5 全角字符）
PROTAG_NAME = '天野 凪咲'      # 默认主角名：姓「天野」/ 名「凪咲」，5 字符与占位等宽
                              # 证据：romfs/Data/level3 → InputFamilyName.m_Text / InputName.m_Text
TALK = re.compile(r'SET_TALK\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*"((?:[^"\\]|\\.)*)"\s*,'
                  r'\s*([^,]+?)\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)')
# 兜底：源侧手误，正文引号后**缺 `)`** 或**多一个 `。`**（句号被写到了引号外）。
# 只认「整行到行尾」的形态，且必须仍是 5 参数结构，避免把别的不完整命令一并吞进来。
#   1) Script/EV002-006.h:89  ... "「……そ、それは……」"               ← 缺 )
#   2) Script/EV508-002.h:939  ... "…小さく爪を立てた"。 )             ← 句号在引号外
TALK_LOOSE = re.compile(r'SET_TALK\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*"((?:[^"\\]|\\.)*)"\s*,'
                        r'\s*([^,]+?)\s*,\s*"((?:[^"\\]|\\.)*)"(。?)\s*\)?\s*$')
# 兜底 2：正文**连右引号都没闭上**（整行到行尾即正文）。
#   Script/EV002-006.h:89  ... -1, "「……そ、それは……」        ← 缺 `"` 与 `)`
# 全库仅此 1 行命中（已逐文件核过，不会误吞别的命令）。
EMIT_SPEAKER = False           # 本批口径「不显示说话人」⇒ 不前置名牌名；置 True 可复原加前缀版
TALK_TRUNC = re.compile(r'SET_TALK\s*\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*"((?:[^"\\]|\\.)*)"\s*,'
                        r'\s*([^,]+?)\s*,\s*"(.*)$')
CHOICE_JUMP = re.compile(r'CHOICE_JUMP\s*\(\s*([^,)]+?)\s*,')


def unescape(s):
    s = s.replace('\\\u3000', '')     # 软换行 + 行首全角空格（缩进）
    s = s.replace('\\', '')           # 软换行
    s = s.replace('$', '')            # 强调标记 $…$（着点/变色）保留文字、剥掉标记
    return s


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))


def load_choices(sett):
    """返回 {番号: [选项, ...]}（按表内顺序；同番号的续行只带选项）。"""
    rows = read_csv(os.path.join(sett, 'CHOICE.csv'))
    out, cur = {}, None
    for r in rows[1:]:
        if len(r) < 4:
            continue
        if r[0].strip():
            cur = r[0].strip()
            out.setdefault(cur, [])
        if cur is None:
            continue
        opt = r[3].strip()
        if opt:
            out[cur].append(unescape(opt))
    return out


def load_dict(sett):
    """DICT.csv → [(見出し語, 解説)]。解说内的换行合并为一行。"""
    rows = read_csv(os.path.join(sett, 'DICT.csv'))
    out = []
    for r in rows[1:]:
        if len(r) < 3:
            continue
        w = r[1].strip()
        c = r[2].strip()
        if not w or not c:
            continue
        c = re.sub(r'\s*\n\s*', '', c)
        out.append((w, c))
    return out


def main():
    base = sys.argv[1]
    dest = sys.argv[2]
    scr = os.path.join(base, 'Script')
    sett = os.path.join(base, 'Setting')

    order = []
    for r in read_csv(os.path.join(sett, 'STORYFLOW.csv'))[1:]:
        if len(r) > 2 and r[2].strip():
            order.append(r[2].strip())
    have = {os.path.splitext(f)[0] for f in os.listdir(scr)}
    seq = [x for x in order if x in have]
    missing = [x for x in order if x not in have]
    extra = sorted(have - set(order))

    choices = load_choices(sett)
    lines = []
    used = {}
    emitted = set()          # 已输出过的番号（连续重复的 CHOICE_JUMP 只出一次）
    n_talk = n_opt = 0
    recovered = []           # 兜底规则救回来的源侧残缺行（应恰为 2 条）

    for name in seq:
        text = open(os.path.join(scr, name + '.h'), encoding='utf-8', errors='replace').read()
        # 逐行扫描，保持 SET_TALK 与 CHOICE_JUMP 的先后
        for lineno, ln in enumerate(text.splitlines(), 1):
            m = TALK.search(ln)
            who_raw = t_raw = None
            tail = ''                                        # 引号外被误写的句号
            if m:
                who_raw, t_raw = m.group(3), m.group(5)
            else:
                m = TALK_LOOSE.search(ln)
                if m:
                    who_raw, t_raw = m.group(3), m.group(5)
                    tail = m.group(6) or ''                  # 句号写在引号外 ⇒ 移回引号内
                    recovered.append((name, lineno, '句号在引号外', ln.strip()))
                else:
                    m = TALK_TRUNC.search(ln)
                    if m:
                        # 行尾残缺（连右引号都没闭上）：削掉残留的 " ) 。 与空格
                        body = m.group(5)
                        while body and body[-1] in '"）。) \u3000':
                            body = body[:-1]
                        if body:
                            who_raw, t_raw = m.group(3), body
                            recovered.append((name, lineno, '右引号/右括号缺失', ln.strip()))
                        else:
                            m = None
            if m:
                who = unescape(who_raw).strip()              # 第 3 参数 = 名牌表示名
                if who == PROTAG:
                    who = PROTAG_NAME                        # 主角占位 → 默认名
                t = unescape(t_raw).strip() + tail
                if t:
                    lines.append(f'{who}{t}' if (who and EMIT_SPEAKER) else t)  # 名札前置开关
                    n_talk += 1
                continue
            m = CHOICE_JUMP.search(ln)
            if m:
                cid = m.group(1).strip()
                if cid in choices and cid not in emitted:
                    for o in choices[cid]:
                        lines.append(o)
                        n_opt += 1
                    emitted.add(cid)
                    used[cid] = lines[-1] if choices[cid] else ''

    # 用語辞典并入末尾
    d = load_dict(sett)
    if d:
        for w, c in d:
            lines.append(f'【{w}】{c}')

    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    with open(dest, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'脚本 {len(seq)}/{len(order)} 个（缺 {len(missing)}，多为 CHAP 章题）；正文 {n_talk} 行')
    print(f'选项 {n_opt} 行 / {len(emitted)} 组（CHOICE.csv 共 {len(choices)} 组）')
    print(f'辞典 {len(d)} 条')
    print(f'合计 {len([x for x in lines if x])} 行 ->  {dest}')
    if recovered:
        print(f'兜底救回 {len(recovered)} 条源侧残缺命令:')
        for fn, ln, kind, src in recovered:
            print(f'  {fn}.h:{ln}  [{kind}]  {src}')
    if missing:
        print('未在磁盘的条目:', missing[:8])
    if extra:
        print('未列入 STORYFLOW 的脚本:', extra[:8])
    unused = [k for k in choices if k not in emitted]
    if unused:
        print(f'⚠ 未被任何 CHOICE_JUMP 引用的选项组 {len(unused)} 个:', unused[:6])
    return 0


if __name__ == '__main__':
    sys.exit(main())
