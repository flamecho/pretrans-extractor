# -*- coding: utf-8 -*-
"""ラスト・エスコート 〜黒蝶スペシャルナイト〜 全文本生成
用法：python scripts/build_text.py <adv目录> <输出txt>
规则：一次点击=一行（69/6A/6B/6C 合并）；名札不入正文；正文完全相同的文件折叠只留首次；
      过滤操作提示行。输出 UTF-8 BOM + LF。
"""
import sys, os, glob, hashlib, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lastescort_vml as L

UI = 'シャンパンコール中！□ボタンのスキップに注意して下さい。'

def main(root, out, stat_path=None):
    files = sorted(glob.glob(os.path.join(root, '*.VML')), key=L.natkey)
    lines, seen, dup, stat = [], {}, [], {}
    for f in files:
        name = os.path.basename(f)
        txt = [t for t, n, k in L.load(f) if t.strip() and t != UI]
        key = hashlib.md5('\n'.join(txt).encode()).hexdigest()
        if txt and key in seen:
            dup.append((name, seen[key])); continue
        if txt: seen[key] = name
        stat[name] = len(txt)
        lines.extend(txt)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(lines) + '\n')
    if stat_path:
        json.dump({'files': stat, 'collapsed': dup, 'lines': len(lines)},
                  open(stat_path, 'w'), ensure_ascii=False)
    print(f'保留 {len(stat)} 个文件 / 折叠 {len(dup)} 个 / 行数 {len(lines)}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
