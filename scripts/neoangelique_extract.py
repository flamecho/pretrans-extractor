#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ネオ アンジェリーク 天使の涙  (PSV-JP, PCSG01068, Otomate / Idea Factory)  全文本提取

容器链
------
  NoNpDrm zip(PCSG01068 目录) -> psvpfsparser -i <PCSG01068> -o dec -z <zRIF> -f cma.henkaku.xyz
    -> Data/CORE.DAT / Data/DATA.PAK  均为 zip
    -> DATA.PAK = 527 个「单文件 zip」顺序串联(每块 512B 对齐；7z 只认第一个)
    -> Data/CORE.DAT = 单文件 zip -> CORE.DAT_
    -> 内层 `DAT ` 归档: [u32 count] + count × (name[0x20] + u32 size + u32 offset) + 数据区

与 学園K V Edition(同引擎, engines/gakuenk-dat-scr.md) 的差异
------------------------------------------------------------
  * 名札不走 char_id，而是「记录内的 <u16 len> + "名前"」→ 名札串形如 `"レイン"` / `""` / `"&"`
  * 主角名宏: `&` = 名(默认 アンジェリーク) / `#` = 愛称(默认 アンジェ)；`%`(姓 セリーヌ) 正文未用
  * 无 DICT.BIN(用語辞典)；CORE 内为 QUOTE.BIN(无文本，非载体)
  * 追加载体: DATA.PAK 内 50 个 LT*.txt = 角色書簡(沙龙信件功能) / CORE 内 STORYFLOW.BIN = 章題

SCD 记录(UTF-8)
--------------
  记录头 = ff ff ff ff <u16 seq> <u16 kind>
  文本   = `02 00 2d 31 <u16 name_len> <name> <u16 text_len> <text>`
           name = `"..."`(名札) / `""`(旁白无名) / `"&"`(主角)
  選択肢 = `61 00 14 00 <u32 scene_id> <u32 idx> ...` -> CHOICE.BIN[(scene_id, idx)]
  行内   = `\` 框内软换行(合并) ; `\`+TAB 换行+缩进 ; 全角空格 U+3000 = 原文保留

用法
----
  python scripts/neoangelique_extract.py \
      --pak _work_neoang/dec/Data/DATA.PAK --core _work_neoang/dec/Data/CORE.DAT \
      --out "提取结果/[PSV-JP]ネオ アンジェリーク 天使の涙_全文本.txt" \
      [--given アンジェリーク --nick アンジェ] [--no-letters] [--no-titles]
r"""
import sys, os, re, struct, argparse, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gakuenk_extract as G       # 复用容器解析(_iter_single_zips / dat_entries / scan_strings / scan_choices / parse_choices)

LABEL = re.compile(r'^"([^"]*)"$')     # 名札(含 "" / "&")
U8RUN = re.compile(rb'(?:[\xe3-\xe9\xef\xf0][\x80-\xbf]{2,3})+')   # UTF-8(日文/全角)游程


def _ctls_ok(s):
    """允许 `\\`+控制字节(0x08 / 0x09) 的换行参数；其余控制字节=误命中。
    本作框内软换行有 3 形：`\\`(后接文字) / `\\`+0x08 / `\\`+0x09(TAB)。
    gakuenk.scan_strings 会因「含控制符」整条丢弃，导致静默漏收 40% 正文(实测 14141 条)。"""
    for k, c in enumerate(s):
        if ord(c) < 0x20 and c != '\n':
            if k == 0 or s[k - 1] != '\\':
                return False
    return True


def scan_strings(b, minlen=2, maxlen=6000):
    """同 gakuenk.scan_strings，但用 _ctls_ok 放宽 `\\`+控制字节。"""
    res, i, n = [], 0, len(b)
    while i + 4 < n:
        L = b[i] | (b[i + 1] << 8)
        if minlen <= L <= maxlen and i + 2 + L <= n:
            try:
                s = b[i + 2:i + 2 + L].decode('utf-8')
            except UnicodeDecodeError:
                i += 1
                continue
            s = s.rstrip('\0')
            if s and _ctls_ok(s):
                res.append((i, s))
                i += 2 + L
                while i < n and b[i] == 0:
                    i += 1
                continue
        i += 1
    return res

def is_label(s):
    m = LABEL.match(s)
    return bool(m) and len(m.group(1)) <= 16      # 名札都很短；正文用「」

def clean(s, given, nick):
    s = s.replace('\\', '')                       # 框内软换行(含 \0x08 / \TAB 参数) -> 合并
    s = ''.join(c for c in s if ord(c) >= 0x20)   # 去残留控制字节
    s = s.replace('&', given).replace('#', nick)  # 主角名 / 愛称
    s = s.strip()                                 # 兼去行首尾全角空格
    return TEXT_FIX.get(s, s)

def blank_like(x):
    return x.strip() == ''

# 原文笔误（缺/错引号）-> 按作者意图显式整行定值表修正（skill `04` §引号；勿正则泛修）
# 判据：同场景同类行引号齐备 / 同文副本(000000 版)引号齐备 -> 确为原作笔误，非提取缺陷
TEXT_FIX = {
    '「――それは『命令」か？」':
        '「――それは『命令』か？」',
    '「そして、こうなったからには、『遮断派」のレインやジェイドさんたちに胸を張れるよう、前に進んでいきましょう」':
        '「そして、こうなったからには、『遮断派』のレインやジェイドさんたちに胸を張れるよう、前に進んでいきましょう」',
    '『女王』を崇めるセレスティザム教団』の最高責任者、教団長を務める『ルネ』の協力。両親をなくした少女が世話になった家で遊んでくれた遠縁のお兄さん――『ベルナール』との再会。':
        '『女王』を崇める『セレスティザム教団』の最高責任者、教団長を務める『ルネ』の協力。両親をなくした少女が世話になった家で遊んでくれた遠縁のお兄さん――『ベルナール』との再会。',
    'エレボスの情報も大事ですけれど、ニクスさんの身体も大事ですから――）':
        '（エレボスの情報も大事ですけれど、ニクスさんの身体も大事ですから――）',
    'きっと、これまでのことを思い出し、もう兄さんの側を離れたくないという気持ちが溢れてしまったのかもしれない」':
        '「きっと、これまでのことを思い出し、もう兄さんの側を離れたくないという気持ちが溢れてしまったのかもしれない」',
    '何か分かれば、モンスターの発生を止めることができるかもしれないですから」':
        '「何か分かれば、モンスターの発生を止めることができるかもしれないですから」',
    'とても快適だよ。お菓子は美味しいし、みんなと楽しく過ごせているし……」':
        '「とても快適だよ。お菓子は美味しいし、みんなと楽しく過ごせているし……」',
}

# ------------------------------------------------------------------ SCD 成行

def scd_lines(blob, choices, given, nick):
    ev = [('text', o, s) for o, s in scan_strings(blob)
          if (not is_label(s)) and G.JP.search(s)]
    for o, sid, idx in G.scan_choices(blob):
        if (sid, idx) in choices:
            ev.append(('opt', o, list(choices[(sid, idx)])))
    ev.sort(key=lambda t: t[1])
    out, n_opt = [], 0
    for kind, _o, payload in ev:
        if kind == 'opt':
            for o in payload:
                o = clean(o, given, nick)
                if not blank_like(o):
                    out.append(o); n_opt += 1
        else:
            t = clean(payload, given, nick)
            if not blank_like(t):
                out.append(t)
    return out, n_opt

def letters_lines(lt, given, nick):
    """LT*.txt = 角色書簡；整封并作一行（去 CR/LF 与空行）"""
    out = []
    for name in sorted(lt):
        txt = lt[name].decode('utf-8', 'replace')
        one = txt.replace('\r', '').replace('\n', '')
        one = clean(one, given, nick)
        if not blank_like(one):
            out.append(one)
    return out

def storyflow_lines(sf, given, nick):
    """STORYFLOW.BIN = 章題/事件名（UTF-8 游程扫描：名称前无 NUL 分隔，紧跟二进制字段）"""
    out = []
    for m in U8RUN.finditer(sf):
        try:
            s = m.group().decode('utf-8')
        except UnicodeDecodeError:
            continue
        if len(s) >= 2 and G.JP.search(s) and not any(ord(c) < 0x20 for c in s):
            out.append(clean(s, given, nick))
    return out

# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pak', default='_work_neoang/dec/Data/DATA.PAK')
    ap.add_argument('--core', default='_work_neoang/dec/Data/CORE.DAT')
    ap.add_argument('--out', default='提取结果/[PSV-JP]ネオ アンジェリーク 天使の涙_全文本.txt')
    ap.add_argument('--given', default='アンジェリーク')   # & 名
    ap.add_argument('--nick',  default='アンジェ')          # # 愛称
    ap.add_argument('--no-letters', action='store_true')
    ap.add_argument('--no-titles', action='store_true')
    args = ap.parse_args()

    scds, lt = [], {}
    for _, blob in G._iter_single_zips(open(args.pak, 'rb').read()):
        for iname, sub in G.dat_entries(blob):
            if iname.endswith('.SCD'):
                scds.append((iname, sub))
            elif iname.endswith('.txt'):
                lt[iname] = sub
    scds.sort()

    core = {}
    for _, blob in G._iter_single_zips(open(args.core, 'rb').read()):
        for nm, sub in G.dat_entries(blob):
            core.setdefault(nm, sub)

    choices = G.parse_choices(core['CHOICE.BIN']) if 'CHOICE.BIN' in core else {}

    per_file, matched, n_opt = {}, set(), 0
    for iname, blob in scds:
        ls, n_o = scd_lines(blob, choices, args.given, args.nick)
        per_file[iname] = ls
        n_opt += n_o
        for _o, sid, idx in G.scan_choices(blob):
            matched.add((sid, idx))

    # 未被 61 00 引用的选项块 -> 置于同名场景文件末尾（找不到则整体末尾）
    unmatched = [(s, i) for (s, i) in sorted(choices) if (s, i) not in matched]
    tail = []
    for sid, idx in unmatched:
        opts = [clean(o, args.given, args.nick)
                for o in choices[(sid, idx)] if not blank_like(clean(o, args.given, args.nick))]
        fn = next((f'{sid:0{d}}.SCD' for d in (6, 7)
                   if f'{sid:0{d}}.SCD' in per_file), None)
        (per_file[fn].extend(opts) if fn else tail.extend(opts))
        n_opt += len(opts)

    lines = [l for iname in sorted(per_file) for l in per_file[iname]] + tail
    n_text = len(lines) - n_opt

    L, T = [], []
    if not args.no_letters:
        L = letters_lines(lt, args.given, args.nick)
        lines += L
    if not args.no_titles and 'STORYFLOW.BIN' in core:
        T = storyflow_lines(core['STORYFLOW.BIN'], args.given, args.nick)
        lines += T

    lines = [l for l in lines if not blank_like(l)]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'SCD={len(scds)}  選択肢ブロック={len(choices)}  (内联命中 {len(matched)}, 置场景末 {len(unmatched)})',
          file=sys.stderr)
    print(f'正文行={n_text}  选项行={n_opt}  書簡={len(L)}  章題={len(T)}  合计={len(lines)}', file=sys.stderr)
    print('wrote', args.out, file=sys.stderr)


if __name__ == '__main__':
    main()
