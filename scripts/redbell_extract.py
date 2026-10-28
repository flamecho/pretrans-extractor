#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""レッドベルの慟哭 —— Naninovel Script(ScriptableObject) → 全文本。

bundle `16c23591…`(6.38MB) 内含 74 个 Script 资产（另 1 个在 6c9456…），
UnityPy 可从 bundle 自带 typerTree 直接 read_typetree（无需 IL2CPP 元数据）。

行类型：
  GenericTextScriptLine  → 台词（inlinedCommands 里的 PrintText）
  CommandScriptLine      → @命令；其中 AddChoice 的 ChoiceSummary = 选项
  CommentScriptLine/EmptyScriptLine/LabelScriptLine → 不取
"""
import io, os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import redbell_romfs as M
import UnityPy
from naninovel_extract import render_parts

OUT = '提取结果/[NS-JP]レッドベルの慟哭.txt'
TARGET = ('16c23591ce9a8fa8d81c72b2d7320813', '6c945603')


def load_env(v, files):
    envs = []
    for key in TARGET:
        cand = [(n, o, s) for n, o, s in files if key in n and n.endswith('.bundle')]
        if not cand:
            continue
        n, o, s = cand[0]
        envs.append(UnityPy.load(io.BytesIO(v.read(o, s))))
    return envs


def main():
    rd = M.Rd()
    ents, total, nb = M.parse_buckets(rd)
    v = M.Virt(rd, ents, total)
    files = M.parse_romfs(v)
    scripts = {}
    for env in load_env(v, files):
        for obj in env.objects:
            if obj.type.name != 'MonoBehaviour':
                continue
            try:
                t = obj.read_typetree()
            except Exception:
                continue
            if 'lines' not in t:
                continue
            name = t.get('m_Name') or ''
            tm = (t.get('textMap') or {}).get('idToText') or {}
            idt = dict(zip(tm.get('keys', []), tm.get('values', [])))
            R = {r['rid']: r for r in (t.get('references') or {}).get('RefIds', [])}
            lines = []
            for ref in t['lines']:
                r = R.get(ref['rid'])
                if not r:
                    continue
                cls = r['type']['class']
                data = r['data']
                if cls == 'GenericTextScriptLine':
                    for ic in data.get('inlinedCommands', []):
                        c = R.get(ic['rid'])
                        if not c or c['type']['class'] != 'PrintText':
                            continue
                        parts = (((c['data'].get('Text') or {}).get('raw') or {}).get('parts') or [])
                        txt, miss = render_parts(parts, idt, {})
                        if txt.strip():
                            lines.append(('t', txt))
                elif cls == 'CommandScriptLine':
                    c = R.get((data.get('command') or {}).get('rid'))
                    if c and c['type']['class'] == 'AddChoice':
                        parts = (((c['data'].get('ChoiceSummary') or {}).get('raw') or {}).get('parts') or [])
                        txt, miss = render_parts(parts, idt, {})
                        if txt.strip():
                            lines.append(('c', txt))
            if lines:
                scripts[name] = lines
    allout = []
    for name in sorted(scripts):
        for kind, txt in scripts[name]:
            allout.append(txt)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(allout) + '\n')
    nt = sum(1 for s in scripts.values() for k, _ in s if k == 't')
    nc = sum(1 for s in scripts.values() for k, _ in s if k == 'c')
    print('脚本 %d / 台词 %d / 选项 %d / 合计 %d 行' % (len(scripts), nt, nc, len(allout)))
    print('->', OUT)


if __name__ == '__main__':
    main()
