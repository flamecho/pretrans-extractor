#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出 Unity AssetBundle / .assets 内的对象（type + name/path_id），不 dump 内容。低 token。

用法: python scripts/unity_list.py <bundle|assets> [--top N] [--types T1,T2]
"""
import sys
import collections
import UnityPy


def main():
    src = sys.argv[1]
    top = 60
    types = None
    if '--top' in sys.argv:
        top = int(sys.argv[sys.argv.index('--top') + 1])
    if '--types' in sys.argv:
        types = set(sys.argv[sys.argv.index('--types') + 1].split(','))
    env = UnityPy.load(src)
    cnt = collections.Counter()
    rows = []
    for o in env.objects:
        tn = o.type.name
        cnt[tn] += 1
        if types and tn not in types:
            continue
        if tn == 'TextAsset':
            try:
                d = o.read()
                nm = d.m_Name
                sz = len(d.m_Script) if isinstance(d.m_Script, (bytes, bytearray)) else len(str(d.m_Script))
            except Exception as e:
                nm, sz = 'ERR:' + str(e)[:30], -1
            rows.append((tn, nm, sz, o.path_id))
        else:
            rows.append((tn, '', -1, o.path_id))
    print('== %s ==' % src)
    for tn, c in cnt.most_common():
        print('  %-20s %d' % (tn, c))
    print('  --- sample ---')
    for tn, nm, sz, pid in rows[:top]:
        print('  %-16s %-48s %8s %d' % (tn, nm, sz, pid))
    return 0


if __name__ == '__main__':
    sys.exit(main())
