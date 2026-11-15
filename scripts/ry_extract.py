#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ロイヤルズ～愛しの王子さま～ ＆ ～誘惑の王子さま～  (Tiaramode, BGI/Ethornell v1)
全テキスト抽出：PackFile(.arc) -> DSC(Huffman) -> v1 命令列 -> 表示順

使い方:
    python scripts/ry_extract.py <本篇目录> <誘惑目录> <out.txt>

要点（本作 v1、与 バトラーズ 的 v0 不同）:
  * 脚本在 data01000.arc（両盤とも**同一ファイル**、1081 本）／追加分は 誘惑 側の data01100.arc（223 本）。
  * `f_PrintMessage(win, mode, ?, name, text)`：**呼び出し 1 回 ＝ テキスト窓 1 個 ＝ 1 行**。
    win/mode/? は全 46,852 回で `(1,1,0)` 固定（「待たない」変種が存在しない）、文字列に `\\n` は 0 件。
  * 第 4 引数は**名前窓**の名前（文字列 or 0）⇒ 本文には含めない（独立した名前窓）。
  * `slct::f_160()` の直前 `nargs(N)` 個の `push_string` が選択肢。
  * 誘惑 側 `<ID>_<char><nnn>t` は**同 ID 脚本の改訂版** ⇒ 同名（t を落とした名前）があれば差し替え、
    無ければ追加シナリオ。文言が同一なら差し替えない。
  * 並び＝脚本 ID 昇順（制作順）。テキスト列が完全一致する脚本は 1 本に畳む（9xxx の重複対策）。
"""
import sys, os, re, struct, tempfile, shutil, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path[:0] = [os.path.join(HERE, 'bgi_v1', 'src', 'common'),
                os.path.join(HERE, 'bgi_v1', 'src', 'v1')]
from brothers_kiss_extract import arc_read, dsc_decompress

PUSH = re.compile(r'^\tpush_(\w+)\((.*)\);$')
STR = re.compile(r'^\tpush_string\("(.*)"\);$')
NARGS = re.compile(r'^\tnargs\((\d+)\);$')
NUMPFX = re.compile(r'^(\d+)_')
# システム（インストーラ／アンインストーラ）メッセージ：`7900_sys01` 〜 `7950_sys06`
# 表示は BGIForInstalling.exe 側＝ゲーム本編の画面ではない ⇒ 収録しない
SYSNAME = re.compile(r'^\d+_sys\d+$')

# 文字列に含まれる主人公ハイライト記号（《渚》→ 渚）は括弧だけ外す
STRIP_CH = '《》'


def unescape(s):
    """反汇编器输出的 C 风格转义还原（实测只有 TAB，见报告 §坑）"""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            if n == 't':
                out.append('\u3000'); i += 2; continue
            if n == 'n':
                i += 2; continue
            if n in ('"', '\\'):
                out.append(n); i += 2; continue
        out.append(c); i += 1
    return ''.join(out)


def disassemble(bss_path, out_path):
    import bgidis
    bgidis.dis(bss_path, encoding='cp932', output_path=out_path)


def events_from_bsd(path):
    """1 スクリプト -> [('T', 本文) | ('C', (選択肢...))]"""
    L = [x.rstrip('\n') for x in open(path, encoding='utf-8')]
    out = []
    pend = []
    for i, s in enumerate(L):
        if PUSH.match(s):
            pend.append(s)
            continue
        t = s.strip()
        if t == 'f_PrintMessage();':
            a = pend[-5:]
            if len(a) == 5:
                m = STR.match(a[4])
                if m:
                    out.append(('T', m.group(1)))
            pend = []
            continue
        if t == 'slct::f_160();':
            # 直前の nargs(N) を探し、そこから上へ N 個の push_string を拾う
            j = i - 1
            n = None
            while j >= 0:
                mt = NARGS.match(L[j])
                if mt:
                    n = int(mt.group(1)); break
                if L[j].strip() and not L[j].startswith('\t'):
                    break
                j -= 1
            opts = []
            if n:
                k = j - 1
                while k >= 0 and len(opts) < n:
                    m = STR.match(L[k])
                    if m:
                        opts.append(m.group(1))
                    elif L[k].strip() and not L[k].startswith('\t'):
                        break
                    k -= 1
                opts.reverse()
            if opts:
                out.append(('C', tuple(opts)))
            pend = []
            continue
        if s.startswith('\t') and not s.startswith('\tline(') and not s.startswith('\tnargs('):
            pend = []
    return out


def read_arc(path):
    d, ents, base = arc_read(path)
    out = []
    for name, o, s in ents:
        out.append((name, d[base + o:base + o + s]))
    return out


def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(1)
    root_main, root_fd, outpath = sys.argv[1:4]
    tmpdir = tempfile.mkdtemp(prefix='ry_')
    acc = collections.Counter()
    try:
        ev = {}
        src = {}
        for tag, root, arc in (('m', root_main, 'data01000.arc'),
                               ('f', root_fd, 'data01100.arc')):
            p = os.path.join(root, arc)
            if not os.path.exists(p):
                continue
            for name, blob in read_arc(p):
                if blob[:16] != b'DSC FORMAT 1.00\x00':
                    continue
                try:
                    dec = dsc_decompress(blob)
                except Exception:
                    continue
                raw = os.path.join(tmpdir, tag + '_' + name + '.bss')
                open(raw, 'wb').write(dec)
                bsd = raw + '.bsd'
                try:
                    disassemble(raw, bsd)
                except Exception:
                    continue
                items = events_from_bsd(bsd)
                if tag == 'm':
                    ev[name] = items; src[name] = 'main'
                    acc['base_t'] += sum(1 for x in items if x[0] == 'T')
                else:
                    stem = name[:-1] if name.endswith('t') else None
                    acc['fd_t'] += sum(1 for x in items if x[0] == 'T')
                    if stem and stem in ev:
                        acc['same_t'] += 1
                        if items != ev[stem]:
                            acc['repl_out_t'] += sum(1 for x in ev[stem] if x[0] == 'T')
                            acc['repl_in_t'] += sum(1 for x in items if x[0] == 'T')
                            ev[stem] = items; src[stem] = 'fd改訂'
                    else:
                        ev[name] = items; src[name] = 'fd追加'
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # ---- 並び：ID 昇順（制作順）。非番号（main 等、本文 0）は除外 ----
    num = [n for n in ev if NUMPFX.match(n) and not SYSNAME.match(n)]
    for n in ev:
        if SYSNAME.match(n):
            acc['sys_t'] += sum(1 for x in ev[n] if x[0] == 'T')
    num.sort(key=lambda n: (int(NUMPFX.match(n).group(1)), n))

    # ---- 同一テキスト列の脚本を 1 本に畳む ----
    seen = {}
    order = []
    dup = 0
    folded_t = folded_c = 0
    for n in num:
        k = tuple(ev[n])
        if k in seen:
            dup += 1
            folded_t += sum(1 for x in ev[n] if x[0] == 'T')
            folded_c += sum(len(x[1]) for x in ev[n] if x[0] == 'C')
            continue
        seen[k] = n
        order.append(n)

    lines = []
    n_text = n_opt = 0
    for n in order:
        for it in ev[n]:
            if it[0] == 'T':
                t = unescape(it[1]).replace('\r', '').replace('\n', '')
                for ch in STRIP_CH:
                    t = t.replace(ch, '')
                t = t.strip('\u3000 ')
                if not t:
                    acc['blank_t'] += 1
                    continue
                lines.append(t); n_text += 1
            else:
                for o in it[1]:
                    o = o.strip()
                    if o:
                        lines.append(o); n_opt += 1

    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    by_src = collections.Counter()
    for n in order:
        by_src[src[n]] += 1
    print(f'scripts_total={len(num)} used={len(order)} dup_folded={dup} '
          f'rows={len(lines)} text={n_text} opt={n_opt}')
    print(f'folded_rows text={folded_t} opt={folded_c} '
          f'(raw text={n_text + folded_t} opt={n_opt + folded_c})')
    print('closure '
          f"base_t={acc['base_t']} sys_t={acc['sys_t']} "
          f"repl_out_t={acc['repl_out_t']} repl_in_t={acc['repl_in_t']} "
          f"fd_same={acc['same_t']} fd_t={acc['fd_t']} "
          f"blank_t={acc['blank_t']} folded_t={folded_t} text={n_text}")
    print('by_source ' + ' '.join(f'{k}={v}' for k, v in sorted(by_src.items())))
    print('->', outpath)


if __name__ == '__main__':
    main()
