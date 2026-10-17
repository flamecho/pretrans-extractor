#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 naninovel_extract.py 的 _scripts.json 组装成 §0 规范成品 txt。

用法:
  naninovel_assemble.py --scripts <_scripts.json> --managed <Script.*.txt> \
                        --tips <Tips.*.txt> --outout <成品.txt>
规则:
  * 顺序: 共通(s_com0..8) → 光明編(s_e1..14) → 救世編(s_i1..13) → 追憶編(s_m1..13)
          → 希求編(s_v1..13) → s_n1 → ss_1
  * 互斥分支去重: after_else 且与上一条已输出正文完全相同 ⇒ 丢弃
  * 行内标记: 去 <space=..>、<br>；<tip="..">X</tip> ⇒ X
  * {t_*} ⇒ Script managed text 解析；{g_name} 已由提取器替换
  * 用語辞典: 【見出し語】解説文 一行一条、去读音、并入末尾
"""
import argparse, json, re, sys

ORDER = (['s_com%d' % i for i in range(0, 9)] +
         ['s_e%d' % i for i in range(1, 15)] +
         ['s_i%d' % i for i in range(1, 14)] +
         ['s_m%d' % i for i in range(1, 14)] +
         ['s_v%d' % i for i in range(1, 14)] +
         ['s_n1', 'ss_1'])

SPACE = re.compile(r'<space=[^>]*>')
BR = re.compile(r'<br\s*/?>')
TIP_OPEN = re.compile(r'<tip="[^"]*">')
TIP_CLOSE = re.compile(r'</tip>')
ANYTAG = re.compile(r'</?[A-Za-z][^>]*>')


def clean_tags(s):
    s = SPACE.sub('', s)
    s = BR.sub('', s)
    s = TIP_OPEN.sub('', s)
    s = TIP_CLOSE.sub('', s)
    return s


def load_managed(path):
    """key: value 格式的 Naninovel managed text（日文版，无 '; localization document' 头）。"""
    m = {}
    for line in open(path, encoding='utf-8', errors='replace').read().split('\n'):
        line = line.rstrip('\r')
        if not line or line.startswith(';'):
            continue
        k, _, v = line.partition(':')
        m[k.strip()] = v.strip()
    return m


def load_tips(path):
    """Tips managed text: key: 見出し語 | カテゴリ | 解説  → [(見出し語, 解説)]"""
    out = []
    for line in open(path, encoding='utf-8', errors='replace').read().split('\n'):
        line = line.rstrip('\r')
        if not line or line.startswith(';'):
            continue
        _, _, v = line.partition(':')
        parts = [p.strip() for p in v.split('|')]
        if len(parts) < 3:
            continue
        term, cat, desc = parts[0], parts[1], '|'.join(parts[2:])
        term = re.sub(r'[（(][^）)]*[）)]', '', term).strip()   # 去读音
        if term and desc:
            out.append((term, desc))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scripts', required=True)
    ap.add_argument('--managed', required=True)
    ap.add_argument('--tips', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--skip', default='')
    a = ap.parse_args()

    data = json.load(open(a.scripts, encoding='utf-8'))
    managed = load_managed(a.managed)
    tips = load_tips(a.tips)

    out_lines = []
    stats = {'text': 0, 'choice': 0, 'dedup': 0, 'unresolved': 0, 'tagleft': 0, 'scripts': 0}
    unresolved_names = set()
    missing_scripts = []

    for name in ORDER:
        if name not in data:
            missing_scripts.append(name)
            continue
        stats['scripts'] += 1
        prev = None
        for rec in data[name]['lines']:
            kind = rec['kind']
            txt = rec.get('text', '')
            # 解析 {t_*}
            for m in re.findall(r'\{([^{}]*)\}', txt):
                if m in managed:
                    txt = txt.replace('{%s}' % m, managed[m])
                else:
                    stats['unresolved'] += 1
                    unresolved_names.add(m)
            txt = clean_tags(txt).strip()
            if ANYTAG.search(txt):
                stats['tagleft'] += 1
            if not txt:
                continue
            # 互斥分支去重（在「清理后的文本」层比较）
            if kind == 'text' and rec.get('after_else') and prev is not None and txt == prev:
                stats['dedup'] += 1
                continue
            out_lines.append(txt)
            stats['text' if kind == 'text' else 'choice'] += 1
            if kind == 'text':
                prev = txt

    # 用語辞典 并入末尾
    gloss = ['【%s】%s' % (t, d) for t, d in tips]
    out_lines.extend(gloss)

    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out_lines) + '\n')

    print('scripts=%d text=%d choice=%d dedup=%d gloss=%d total=%d' % (
        stats['scripts'], stats['text'], stats['choice'], stats['dedup'], len(gloss), len(out_lines)))
    print('unresolved exprs:', stats['unresolved'], sorted(unresolved_names)[:20])
    print('leftover <tags> lines:', stats['tagleft'])
    if missing_scripts:
        print('MISSING scripts:', missing_scripts)


if __name__ == '__main__':
    main()
