#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バトラーズ～召しませお嬢様～ / ～ナイトモード～  (Tiaramode, BGI/Ethornell v0)
全テキスト抽出：PackFile(.arc) -> DSC -> **v0 バイトコード (u16 op + インライン串)** -> 表示順

使い方:
    python scripts/bt_extract.py <本篇目录> <ナイトモード目录> <out.txt>

要点（本作 v0、与ブラザーズ 的 v1 不同）:
  * 剧本在 data004.arc(本篇 626) / data104.arc(FD 193)；data001-003 是图像/立绘。
  * `0x0010 f_PrintMessage(win, mode, str)`：mode 1 = **新框（一次点击）**，mode 0 = **同框续行**。
  * `0x0014 f_SetName` = 独立名字窗 ⇒ 不输出；`0x00b0 f_Select` 参数即选项文本。
  * 排序 = 从 `Main` 按 f_CallScript/f_JumpScript DFS 前序；未覆盖但有正文者按名补末尾。
"""
import sys, os, re, struct, tempfile, shutil, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'bgi_v0'))
from brothers_kiss_extract import arc_read, dsc_decompress
import bgidis_v0 as DV
from bgiop_v0 import load_name_maps

MAPPING = os.path.join(HERE, 'bss_mapping_v0.json')
LINE = re.compile(r'^\t(\w+)\((.*)\);$')
EXCLUDE = {'debug'}          # 调试菜单（含「ナイトモード オン/オフ」「好感度設定」等）


def unesc(s):
    out = []; i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            if n == 'n': out.append('\n'); i += 2; continue
            if n == 't': out.append('\t'); i += 2; continue
            if n == '"': out.append('"'); i += 2; continue
            if n == '\\': out.append('\\'); i += 2; continue
        out.append(c); i += 1
    return ''.join(out)


def parse_args(s):
    args = []; buf = []; q = False; i = 0
    while i < len(s):
        c = s[i]
        if q:
            if c == '\\' and i + 1 < len(s): buf.append(s[i:i + 2]); i += 2; continue
            if c == '"': q = False; buf.append(c); i += 1; continue
            buf.append(c); i += 1; continue
        if c == '"': q = True; buf.append(c); i += 1; continue
        if c == ',': args.append(''.join(buf).strip()); buf = []; i += 1; continue
        buf.append(c); i += 1
    if buf: args.append(''.join(buf).strip())
    return args


def strarg(a):
    a = a.strip()
    if len(a) >= 2 and a[0] == '"' and a[-1] == '"':
        return unesc(a[1:-1])
    return None


def load_arc(arc_path, tmpdir, tag):
    d, ents, base = arc_read(arc_path)
    ev = {}
    for name, o, s in ents:
        blob = d[base + o:base + o + s]
        if blob[:16] != b'DSC FORMAT 1.00\x00':
            continue
        try:
            dec = dsc_decompress(blob)
        except Exception:
            continue
        raw = os.path.join(tmpdir, tag + '_' + name)
        open(raw, 'wb').write(dec)
        bsd = raw + '.bsd'
        try:
            DV.disassemble_file(raw, output_path=bsd, encoding='cp932', mapping_path=MAPPING)
        except Exception:
            continue
        items = []
        for ln in open(bsd, encoding='utf-8'):
            m = LINE.match(ln.rstrip('\n'))
            if not m:
                continue
            fn, args = m.group(1), m.group(2)
            if fn == 'f_PrintMessage':
                a = parse_args(args)
                if len(a) >= 3:
                    t = strarg(a[2])
                    if t is not None and a[1].lstrip('-').isdigit():
                        items.append(('T', int(a[1]), t))
            elif fn == 'f_Select':
                opts = [x for x in (strarg(y) for y in parse_args(args)) if x]
                if opts:
                    items.append(('C', opts))
            elif fn in ('f_CallScript', 'f_JumpScript'):
                a = parse_args(args)
                t = strarg(a[0]) if a else None
                if t:
                    items.append(('S', t))
        ev[name] = items
    return ev


def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    root_main, root_fd, outpath = sys.argv[1], sys.argv[2], sys.argv[3]
    tmpdir = tempfile.mkdtemp(prefix='bt_')
    try:
        ev_main = load_arc(os.path.join(root_main, 'data004.arc'), tmpdir, 'm')
        ev_fd = load_arc(os.path.join(root_fd, 'data104.arc'), tmpdir, 'f') if os.path.isdir(root_fd) else {}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    ev = dict(ev_main)
    tag_of = {k: 'main' for k in ev_main}
    for k, v in ev_fd.items():
        if k not in ev:
            ev[k] = v; tag_of[k] = 'fd'
    lo = {}
    for k in ev:
        lo.setdefault(k.lower(), k)

    out = []; visited = set(); st = collections.Counter()

    def emit(name):
        key = name if name in ev else lo.get(str(name).lower())
        if key is None or key in visited or key in EXCLUDE:
            return
        visited.add(key); st['scripts'] += 1
        pend = []          # mode=0：不等待，属于**本屏**，与紧跟的 mode=1 同行
        for it in ev[key]:
            if it[0] == 'T':
                mode, t = it[1], it[2].replace('\n', '')
                if mode == 1:
                    out.append(''.join(pend) + t); pend = []
                    st['open'] += 1
                else:
                    pend.append(t); st['cont'] += 1
            elif it[0] == 'C':
                if pend: out.append(''.join(pend)); pend = []
                for o in it[1]:
                    out.append(o); st['opt'] += 1
            else:
                if pend: out.append(''.join(pend)); pend = []
                emit(it[1])
        if pend: out.append(''.join(pend))
    emit('Main')
    rest = [k for k, v in ev.items()
            if k not in visited and k not in EXCLUDE and any(x[0] in ('T', 'C') for x in v)]
    rest.sort()
    for k in rest: emit(k)

    for k in visited:
        n = sum(1 for it in ev[k] if it[0] == 'T' and it[1] == 1) + \
            sum(len(it[1]) for it in ev[k] if it[0] == 'C')
        st['rows_' + tag_of.get(k, '?')] += n

    out = [x.replace('《', '').replace('》', '') for x in out]
    clean = [x for x in out if x.strip('　 ')]
    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(clean) + '\n')
    print(f'scripts={st["scripts"]} open={st["open"]} cont={st["cont"]} opt={st["opt"]} '
          f'rows={len(clean)} (raw {len(out)}, blank {len(out)-len(clean)}) leftover={len(rest)} -> {outpath}')
    print(f'按源: main={st["rows_main"]} fd={st["rows_fd"]}')


if __name__ == '__main__':
    main()
