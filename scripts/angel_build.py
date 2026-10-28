# -*- coding: utf-8 -*-
"""Angel Profile (PS2) —— 生成交付文本。

顺序：DATA.BIN(AFS) 中脚本条目顺序（= 引擎 fileenum，与 label 表文件名表一致）
粒度：一个 [voice id][文本] = 一次点击；串内 '\n' 为同框软换行（合并）
剔除：mesname 名札、select 导航项（次へ/戻る/やめる）、脚本注释残留（'--' / '\t//'）
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import angel_extract as A

EXCLUDE_MOD = {'item_explanation'} | {'help_' + x for x in
              ('bujyutu', 'cook', 'kaiga', 'magic', 'music', 'reihou', 'zagaku')}

OPT_SPLIT = re.compile(r'\n\t;[^\n]*\n')
# 商店货架行（『道具名』値段 N G）＝UI 列表，非正文
UI_LINE = re.compile(r'^『[^』]+』\s*値段\s*[0-9０-９]+\s*G$')


def clean_text(s):
    out = []
    for ln in s.split('\n'):
        if '\t' in ln:
            ln = ln.split('\t')[0]
        t = ln.strip('\u3000 ')
        if not t:
            continue
        if t.startswith('--') or t.startswith(';') or t.startswith(':'):
            continue
        if t.startswith('//'):
            continue
        out.append(ln)
    return ''.join(out).strip('\u3000 ')


def clean_opts(s):
    if '\t;' in s:
        parts = OPT_SPLIT.split('\n' + s + '\n')
        res = []
        for p in parts:
            t = clean_text(p)
            if t:
                res.append(t)
        return res
    t = clean_text(s)
    return [t] if t else []


def main():
    afs = '_work_angel/x/DATA.BIN'
    ents = A.afs_index(afs)
    f = open(afs, 'rb')
    names = A.build_name_set(f, ents[7395:7746])
    lines = []
    files = 0
    for idx in range(7412, 7746):
        off, sz = ents[idx]
        f.seek(off)
        d = f.read(sz)
        if d[:4] != b'\x1bLua':
            continue
        mod = A.module_name(A.tokens(d))
        if mod in EXCLUDE_MOD:
            continue
        recs = A.extract(d, names)
        if not recs:
            continue
        buf = []
        for kind, v in recs:
            if kind == 'opt':
                buf.extend(clean_opts(v))
            else:
                t = clean_text(v)
                if t:
                    buf.append(t)
        if buf:
            files += 1
            lines.extend(buf)
    # 续接段（以句读开头，实为宏插值后的同框后段）并回上一行
    merged = []
    for l in lines:
        if merged and (l[0] in '。、'):
            merged[-1] += l
        else:
            merged.append(l)
    lines = [l for l in merged if not UI_LINE.match(l)]
    # 半角中点 → 全角（源为半角省略点，非化け）
    lines = [l.replace('\uff65', '\u30fb') for l in lines]
    lines = [l for l in lines if l]
    out = '\ufeff' + '\n'.join(lines) + '\n'
    dst = '提取结果/[PS2-JP]エンジェル・プロファイル.txt'
    os.makedirs('提取结果', exist_ok=True)
    with open(dst, 'w', encoding='utf-8', newline='\n') as w:
        w.write(out)
    print('files', files, 'lines', len(lines), 'chars', sum(len(l) for l in lines))


if __name__ == '__main__':
    main()
