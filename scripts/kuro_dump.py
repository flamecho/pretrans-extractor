# -*- coding: utf-8 -*-
"""蒼黒の楔 (NS) — Unity AdvChapterData/AdvImportBook 剧本落盘。

结构：.chapter.asset (UnityFS bundle) -> MonoBehaviour(AdvImportBook) { m_Name, importGridList[] }
     每个 grid = 一幕(CSV 网格)，rows = [{rowIndex, strings[12], isEmpty, isCommentOut}]
     列：Command,Arg1..Arg6,WaitType,Text,PageCtrl,Voice,WindowType

用法: python scripts/kuro_dump.py <chapter.asset> <out.tsv>
产物行: book \t gridIdx \t rowIndex \t Command \t ... 原样 12 列
"""
import sys, os
import UnityPy

COLS = ['Command', 'Arg1', 'Arg2', 'Arg3', 'Arg4', 'Arg5', 'Arg6',
        'WaitType', 'Text', 'PageCtrl', 'Voice', 'WindowType']


def main():
    src, out = sys.argv[1], sys.argv[2]
    env = UnityPy.load(src)
    books = []
    for o in env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if 'importGridList' not in t:
            continue
        books.append(t)
    with open(out, 'w', encoding='utf-8', newline='') as f:
        f.write('\t'.join(['book', 'grid', 'row'] + COLS) + '\n')
        for t in books:
            nm = t.get('m_Name')
            for gi, g in enumerate(t.get('importGridList') or []):
                for r in g.get('rows') or []:
                    s = list(r.get('strings') or [])
                    s += [''] * (12 - len(s))
                    s = [x.replace('\t', ' ').replace('\n', '\\n') for x in s]
                    f.write('\t'.join([nm, str(gi), str(r.get('rowIndex'))] + s) + '\n')
    print('books=%d -> %s' % (len(books), out))


if __name__ == '__main__':
    main()
