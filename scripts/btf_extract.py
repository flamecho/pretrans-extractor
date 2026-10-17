#!/usr/bin/env python3
"""btf_extract.py —— [PSP-JP] Beyond The Future -Fix The Time Arrows- 全文本提取。

链路：ISO → INSDIR/INSTALL.BIN（PGD）→ scripts/btf_pgd.py 解密 → fileinfo.psb.m.json 按 umd_root 切分
      → *_body.bin 内条目（MDF/MT19937，seed = key + 名字 + expire_suffix）→ PSB → PsbDecompile → JSON
      → scenelist.json（master 顺序）逐 scene 取 texts[]，scene 级 selects[] 作为选项追加。

输出规范：一次点击＝一行；框内软换行(\n)合并；不加说话人前缀；$f.name; → 主角名。
用法: python scripts/btf_extract.py <scn_dir> <out.txt> [主角名]
"""
import json, os, sys, re

SKIP_STORAGE = {'testsozai.txt'}   # 素材展開用（開発テスト）

TAG_COLOR = re.compile(r'%\d+#[0-9A-Fa-f]{0,8};')
TAG_COLOR2 = re.compile(r'%\d+#')
TAG_NUM = re.compile(r'%\d+')
TAG_LETTER = re.compile(r'%[A-Za-z]')
TAG_WAIT = re.compile(r'\\w')


def strip_tags(s):
    s = TAG_COLOR.sub('', s)
    s = TAG_COLOR2.sub('', s)
    s = TAG_NUM.sub('', s)
    s = TAG_LETTER.sub('', s)
    s = TAG_WAIT.sub('', s)
    return s


def clean(s, name):
    s = s.replace('$f.name;', name)
    s = s.replace('\n', '')          # 框内软换行合并
    s = strip_tags(s)
    return s


def main():
    scn_dir, out, hero = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else 'リリス')
    sl = json.load(open(os.path.join(scn_dir, 'scenelist.json'), encoding='utf-8'))['list']
    cache = {}
    lines = []
    stats = {'scene': 0, 'text': 0, 'sel': 0, 'skip': 0}
    for e in sl:
        storage, target = e['storage'], e['target']
        if storage in SKIP_STORAGE:
            stats['skip'] += 1
            continue
        if storage not in cache:
            d = json.load(open(os.path.join(scn_dir, storage + '.json'), encoding='utf-8'))
            cache[storage] = {sc['label']: sc for sc in d.get('scenes', [])}
        sc = cache[storage].get(target)
        if sc is None:
            print('MISSING', storage, target)
            continue
        stats['scene'] += 1
        for t in sc.get('texts', []):
            txt = t[2]
            if not isinstance(txt, str):
                continue
            txt = clean(txt, hero)
            if not txt.strip():
                continue
            lines.append(txt)
            stats['text'] += 1
        last_sel = None
        for s in (sc.get('selects') or []):
            txt = clean(s.get('text') or '', hero)
            if not txt.strip():
                continue
            # 互斥备选（map/chara 等：同一文本按 eval 条件重复两条）折叠为一条
            if txt == last_sel:
                continue
            last_sel = txt
            lines.append(txt)
            stats['sel'] += 1
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(stats, 'lines', len(lines))
    # 残留检查
    left = [l for l in lines if '$' in l or '%' in l]
    print('with $ or %:', len(left), left[:3])


main()
