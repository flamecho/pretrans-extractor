#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Naninovel (Unity IL2CPP) 脚本文本提取器。
用法:
  naninovel_extract.py --il2cpp <main> --meta <global-metadata.dat> --unity 2022.3.42f1 \
                       --bundle <naninovel-scripts_*.bundle> --out <dir> [--name <主角名>]
输出:
  <dir>/_scripts.json   每脚本：名称、逐行 {lineIndex, kind, author, wait, text|choice}
"""
import argparse, json, os, sys, struct

def build_env(bundle, il2cpp, meta, unity):
    import UnityPy
    from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
    gen = TypeTreeGenerator(unity)
    with open(il2cpp, 'rb') as f: il2cpp_b = f.read()
    with open(meta, 'rb') as f: meta_b = f.read()
    gen.load_il2cpp(il2cpp_b, meta_b)
    env = UnityPy.load(bundle)
    env.typetree_generator = gen
    return env

def render_parts(raw_parts, idt, name_map):
    """把 Text.raw.parts 渲染成字符串。"""
    out = []
    missing = []
    for p in raw_parts:
        pid = p.get('id') or ''
        txt = p.get('text') or ''
        expr = p.get('expression') or ''
        if pid:
            out.append(idt.get(pid, txt))
        elif expr:
            if expr in name_map:
                out.append(name_map[expr])
            else:
                out.append('{%s}' % expr)
                missing.append(expr)
        else:
            out.append(txt)
    return ''.join(out), missing

def extract(bundle, il2cpp, meta, unity, name_map):
    env = build_env(bundle, il2cpp, meta, unity)
    scripts = {}
    for obj in env.objects:
        if obj.type.name != 'MonoBehaviour':
            continue
        d = obj.read_typetree()
        name = d['m_Name']
        tm = d.get('textMap', {}).get('idToText', {})
        idt = dict(zip(tm.get('keys', []), tm.get('values', [])))
        R = {r['rid']: r for r in d['references']['RefIds']}
        lines = []
        after_else = False   # 上一条记录是否为 @else/@elseif（互斥分支去重用）
        for ref in d['lines']:
            r = R[ref['rid']]
            cls = r['type']['class']
            li = r['data'].get('lineIndex')
            rec = None
            if cls == 'GenericTextScriptLine':
                for ic in r['data'].get('inlinedCommands', []):
                    c = R[ic['rid']]
                    if c['type']['class'] != 'PrintText':
                        continue
                    parts = c['data'].get('Text', {}).get('raw', {}).get('parts', [])
                    text, missing = render_parts(parts, idt, name_map)
                    rec = {
                        'lineIndex': li,
                        'kind': 'text',
                        'author': c['data'].get('AuthorId', {}).get('value') or '',
                        'wait': c['data'].get('Wait', {}).get('value'),
                        'text': text,
                        'missing': missing,
                        'after_else': after_else,
                    }
            elif cls == 'CommandScriptLine':
                c = R[r['data']['command']['rid']]
                if c['type']['class'] == 'AddChoice':
                    parts = c['data'].get('ChoiceSummary', {}).get('raw', {}).get('parts', [])
                    text, missing = render_parts(parts, idt, name_map)
                    gp = c['data'].get('GotoPath', {}).get('value', {})
                    rec = {
                        'lineIndex': li,
                        'kind': 'choice',
                        'text': text,
                        'goto': gp.get('value', {}).get('value', '') if gp else '',
                        'missing': missing,
                        'after_else': after_else,
                    }
            if rec:
                lines.append(rec)
                after_else = False
            elif cls == 'CommandScriptLine':
                c = R[r['data']['command']['rid']]
                if c['type']['class'] in ('Else', 'ElseIf'):
                    after_else = True
        scripts[name] = {'name': name, 'lines': lines}
    return scripts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--il2cpp', required=True)
    ap.add_argument('--meta', required=True)
    ap.add_argument('--unity', default='2022.3.42f1')
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', default='')
    a = ap.parse_args()
    name_map = {'g_name': a.name} if a.name else {}
    scripts = extract(a.bundle, a.il2cpp, a.meta, a.unity, name_map)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, '_scripts.json'), 'w', encoding='utf-8') as f:
        json.dump(scripts, f, ensure_ascii=False, indent=1)
    ntext = sum(1 for s in scripts.values() for l in s['lines'] if l['kind'] == 'text')
    nchoice = sum(1 for s in scripts.values() for l in s['lines'] if l['kind'] == 'choice')
    print("scripts=%d text=%d choice=%d" % (len(scripts), ntext, nchoice))

if __name__ == '__main__':
    main()
