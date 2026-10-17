#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""神凪ノ杜 五月雨綴り (NS-JP, Unity 2021 IL2CPP, Matatabi) 剧本正文 + 选项提取。

格式（script AssetBundle 内 624 个 TextAsset，UTF-8-BOM 纯文本脚本）：
  ;...            注释（不上屏；含文件头元信息与制作备忘）
  @talk [args]    文本框开始（args: voice=/name=/real=）
  <正文行...>      文本框内容（框内软换行 → 合并为一行）
  @hitret / @hitre 文本框结束（@hitre 为源内笔误，同义）
  @choice text=X file=Y   选项（一行一条，按序）
  其余 @命令 / *标签|     非文本，跳过
宏：<pf> = 主角名（姓「木南」字面固定；<pf> 为名，默认「瑞希」，vndb v22311 确认）

用法: python scripts/kannagi_extract.py <script_txt_dir|bundle> <out.txt> [--name 瑞希]
"""
import os
import re
import sys

PF_DEFAULT = '瑞希'
OPTS = 0

# 原文笔误修正（整行定值表；源自 km_t10_19 一处多余的右引号）
OVERRIDES = {
    '「……そういえば、さっきはすごく怯えてたみたいだったけど、どうしてか理由を聞いてもいい？」」':
    '「……そういえば、さっきはすごく怯えてたみたいだったけど、どうしてか理由を聞いてもいい？」',
}


def fix(s):
    return OVERRIDES.get(s, s)


def natural_key(name):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', name)]


def parse_text(path, name):
    """返回该脚本的 (行列表, 异常统计)。"""
    with open(path, 'rb') as f:
        raw = f.read()
    t = raw.decode('utf-8-sig', 'replace')
    out = []
    in_talk = False
    buf = []
    box_args = ''
    anomalies = []
    for ln in t.split('\n'):
        s = ln.rstrip('\r')
        st = s.strip()
        if in_talk:
            if st.startswith('@hitret') or st.startswith('@hitre'):
                body = ''.join(buf).replace('<pf>', name)
                out.append(('T', body, box_args) if body.strip() else ('E', '', box_args))
                buf = []
                box_args = ''
                in_talk = False
                continue
            if st.startswith(';') or st == '':
                continue                       # 框内注释 / 空行
            if st.startswith('@'):
                # 框内出现命令（多为源内漏写 @hitret）⇒ 先闭合当前框，再按命令处理
                anomalies.append(('cmd_in_box', st))
                body = ''.join(buf).replace('<pf>', name)
                out.append(('T', body, box_args) if body.strip() else ('E', '', box_args))
                buf = []
                box_args = ''
                in_talk = False
                # 落到下方统一处理该命令
            else:
                buf.append(s)
                continue
        # ---- 非框内 ----
        if st.startswith('@talk'):
            in_talk = True
            buf = []
            box_args = st
        elif re.match(r'@choice\b(?!End)', st):
            m2 = re.search(r'text=(.*?)(?: file=|$)', st)
            val = (m2.group(1) if m2 else '').strip()
            if val:
                out.append(('C', val.replace('<pf>', name), st))
            else:
                anomalies.append(('choice_no_text', st))
        # 其它全部跳过
    if in_talk:
        anomalies.append(('unclosed_box', path))
    return out, anomalies


def main():
    src = sys.argv[1]
    out = sys.argv[2]
    name = PF_DEFAULT
    if '--name' in sys.argv:
        name = sys.argv[sys.argv.index('--name') + 1]
    files = sorted([f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))],
                   key=natural_key)
    lines = []
    n_box = n_choice = n_empty = 0
    anom = []
    empties = []
    for fn in files:
        st = fn.rsplit('.', 1)[0]
        if st.startswith('test_vitaOV') or st.startswith('test'):
            continue                            # 测试脚本
        rows, a = parse_text(os.path.join(src, fn), name)
        for kind, body, arg in rows:
            if kind == 'E':
                n_empty += 1
                empties.append((fn, arg[:70]))
                continue
            lines.append(fix(body))
            if kind == 'T':
                n_box += 1
            else:
                n_choice += 1
        for k, v in a:
            anom.append((fn, k, v[:60]))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('files=%d  boxes=%d  choices=%d  empty=%d  lines=%d'
          % (len(files), n_box, n_choice, n_empty, len(lines)))
    print('anomalies=%d' % len(anom))
    for x in anom:
        print('  ', x)
    print('empty boxes:')
    for x in empties[:30]:
        print('  ', x)


if __name__ == '__main__':
    main()
