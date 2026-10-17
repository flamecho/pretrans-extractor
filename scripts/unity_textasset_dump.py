#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unity `resources.assets` → 全 TextAsset 落盘（旁车 / managed text 导出）。

用于 Unity(IL2CPP) 游戏：把 `Data/resources.assets` 里的 TextAsset 全部导出为独立文件，
便于找 **Naninovel managed text**（`Script`＝`{t_*}` 变量 / 主角默认名、`Tips`＝用語辞典、
`CharacterNames`＝说话人名）等旁车表。

用法:
  python scripts/unity_textasset_dump.py <resources.assets> <out_dir>

★ TextAsset 有内建 typetree ⇒ `obj.read().m_Name / .m_Script` 直接可用（别手写偏移猜法）。
★ 同名 TextAsset 常成对：正文以 `; Japanese <ja> to English <en> localization document for …` 开头的
  是**英译工作稿**；不带头、值直接是日文的那份才是**默认日语**。
"""
import os
import sys

import UnityPy


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, out = sys.argv[1], sys.argv[2]
    env = UnityPy.load(src)
    os.makedirs(out, exist_ok=True)
    n = 0
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()                      # TextAsset 有内建 typetree
        nm = d.m_Name if isinstance(d.m_Name, str) else d.m_Name.decode('utf-8', 'replace')
        body = d.m_Script
        if isinstance(body, str):
            body = body.encode('utf-8', 'surrogateescape')
        with open(os.path.join(out, '%s.%d.txt' % (nm.replace('/', '_'), o.path_id)), 'wb') as f:
            f.write(body)
        n += 1
        print('%5d %-32s %7d' % (o.path_id, nm, len(body)))
    print('done: %d TextAsset -> %s' % (n, out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
