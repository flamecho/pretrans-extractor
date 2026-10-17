#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
薄桜鬼 随想録 面影げ花 (PSV, PCSG00485, Idea Factory / Otomate)
STCM2L PSV/CP932 变体 —— 脚本正文本体提取

链路：PSV pkg -> pkg2zip -x <pkg> <zRIF> -> psvpfsparser -i app/PCSG00485 -o dec -z <zRIF> -f cma.henkaku.xyz
      -> dec/data/GAME.cpk (scripts/cpk.py 解 CRILAYLA) -> script/*.cl3 -> 本脚本

格式要点（实测）
  脚本头： generator 32B("STCM2L ...") + u32 export_addr@0x20 + ...
           "GLOBAL_DATA\0" ... "CODE_START_\0"(12B) -> 指令流起点 = CODE_START_ 偏移 + 12
  指令   = [u32 is_call][u32 opcode][u32 nparams][u32 length] + np*[p0,p1,p2](各 u32)
  文本记录 = [a][L/4][1][L][cp932][pad] （c==1 且 b==L/4 为签名）；param0 = 文件绝对偏移（记录多内联）

  opcode（本作）：
    0x4BA TEXT   正文片段；*空串/纯 #Color = 段分隔（见下）*
    0x4BC NAME   话者名札（丢弃，同时开启新「段」）
    0x4CF OPT    选项（np=2, p0=选项文本）
    0x4C0 TITLE  回想/章节标题 -> 收（扉文）
    0x4BB WAIT   换框 = 一次点击 -> 断「点击」
    0x41C VAR    按名访问变量（'switch'…） -> 断「点击」
    其余（0x3 Mif / 0x1EF / 0x462 / 0x469 …）= 分支·控制，不断点击

  ★★ 两套「分段」概念（本作核心）：
    ① 一次点击 = 0x4BB / 0x41C 之间的全部内容。
    ② 段 = 「点击」内按 *空 0x4BA* 或 *0x4BC* 切出的若干块。
       - 段间出现分支 op（0x3 / 0x1EF）⇒ 各段是**互斥备选**（A=字面默认名版 ↔ B=#Name[1]/关系称谓版）
         ⇒ 按口径「同段取一」（保留首段）。
       - 段间无分支 op ⇒ 段是**同一次点击内的连续地文（物語モード的整页文本）** ⇒ **合并成一行**。
       （实测：identical+branch=266 / diff+nobranch=118（全在 10700-10713 物語文件）/ diff+branch=14）
  ★ 少数文件（10700-10713）话者名也用 0x4BA 逐条发出（形如 `#Color[0]近藤　勇` 后紧跟 `「…」`）
    ⇒ 按「短·无句读·无假名 + 后随「」⇒ 名札」判据丢弃。
"""
import os
import re
import sys
import glob
import struct

# ---------------- opcode ----------------
TEXT_OP = 0x4BA
NAME_OP = 0x4BC
OPT_OP = 0x4CF
TITLE_OP = 0x4C0
WAIT_OP = 0x4BB
VAR_OPS = (0x41B, 0x41C, 0x41D)   # 按名访问变量/资源（'switch'/'flg_memory'/'file_cnt'/'scene_play'…）
CLICK_BREAK = {WAIT_OP} | set(VAR_OPS)
BRANCH_OPS = {0x3, 0x1EF}

HERO = '千鶴'          # #Name[1] 默认值（名札形如「雪村 #Name[1]」）

RE_NAME = re.compile(r'#Name\[(\d+)\]')
RE_MACRO = re.compile(r'#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]')
RE_KANA = re.compile(r'[\u3041-\u309f\u30a0-\u30ff]')
NAME_BAD = set('。「」『』（）()、！？…：;；')


def clean(s):
    s = RE_NAME.sub(lambda m: HERO if int(m.group(1)) == 1 else m.group(0), s)
    s = RE_MACRO.sub('', s)
    return s


def strip_only_macro(s):
    """纯 #Color 之类 -> 视为空"""
    return RE_MACRO.sub('', s).strip(' \u3000\t') == ''


def is_name_like(s):
    n = clean(s).strip(' \u3000\t')
    if not n or len(n) > 12:
        return False
    if RE_KANA.search(n):
        return False
    return not any(ch in NAME_BAD for ch in n)


# ---------------- 解析 ----------------
def parse_ins(d):
    cs = d.find(b'CODE_START_')
    if cs < 0:
        return []
    p = cs + 12
    out = []
    while p + 16 <= len(d):
        ic, op, np, ln = struct.unpack_from('<4I', d, p)
        if ln < 16 or ln % 4 or p + ln > len(d) or np > 0x100:
            break
        out.append((p, ic, op, np, ln))
        p += ln
    return out


def param_str(d, p, np, ln, k=0):
    if k >= np or p + 16 + 12 * k + 4 > len(d):
        return None
    q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
    if not (p <= q < p + ln + 4096) or q + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, q)
    if not (c == 1 and b == L // 4 and 0 < L <= 0x4000 and q + 16 + L <= len(d)):
        return None
    try:
        return d[q + 16:q + 16 + L].split(b'\x00')[0].decode('cp932')
    except Exception:
        return None


def read_events(d):
    """-> [(kind, payload)] ; kind ∈ TEXT/NAME/OPT/TITLE/WAIT/VAR/CTRL"""
    ev = []
    for (p, ic, op, np, ln) in parse_ins(d):
        if ic != 0:
            ev.append(('CALL', op))
            continue
        if op == TEXT_OP:
            ev.append(('TEXT', param_str(d, p, np, ln, 0)))
        elif op == NAME_OP:
            ev.append(('NAME', param_str(d, p, np, ln, 0)))
        elif op == OPT_OP:
            ev.append(('OPT', param_str(d, p, np, ln, 0)))
        elif op == TITLE_OP:
            ev.append(('TITLE', param_str(d, p, np, ln, 0)))
        elif op == WAIT_OP:
            ev.append(('WAIT', None))
        elif op in VAR_OPS:
            ev.append(('VAR', None))
        else:
            ev.append(('CTRL', op))
    return ev


def extract_file(path):
    """-> (lines, stats)"""
    d = open(path, 'rb').read()
    ev = read_events(d)
    lines = []
    segs = []      # [{'t':str,'alt':bool}]
    branch = False
    st = {'variant': 0, 'merged': 0, 'taken1': 0, 'names': 0}

    def new_seg():
        segs.append({'t': '', 'alt': branch})

    def flush():
        nonlocal branch
        g = [s for s in segs if s['t'].strip()]
        if not g:
            del segs[:]
            branch = False
            return
        if len(g) > 1:
            if any(s['alt'] for s in g[1:]):
                st['variant'] += 1
                kept = [g[0]]
                if len(set(clean(s['t']).strip() for s in g)) > 1:
                    st['taken1'] += 1
            else:
                st['merged'] += 1
                kept = g
        else:
            kept = g
        txt = clean(''.join(s['t'] for s in kept)).strip(' \u3000\t')
        if txt:
            lines.append(txt)
        del segs[:]
        branch = False

    for i, (kind, val) in enumerate(ev):
        if kind == 'TEXT':
            if val is None or strip_only_macro(val):
                if segs and segs[-1]['t'].strip():
                    new_seg()
                continue
            # 名札（0x4BA 形态）：短·无句读·无假名 且 下一条非空 TEXT 以 「『（ 开头
            if is_name_like(val):
                nxt = None
                for j in range(i + 1, min(i + 6, len(ev))):
                    if ev[j][0] == 'TEXT':
                        if ev[j][1] and not strip_only_macro(ev[j][1]):
                            nxt = ev[j][1]
                        break
                    if ev[j][0] in ('NAME', 'WAIT', 'VAR'):
                        break
                if nxt and nxt.lstrip('\u3000 ')[:1] in ('「', '『', '（'):
                    st['names'] += 1
                    flush()          # 0x4BA 形态名札 ⇒ 断「点击」（名札自带换框语义）
                    continue
            if not segs:
                new_seg()
            segs[-1]['t'] += val
        elif kind == 'NAME':
            if segs and segs[-1]['t'].strip():
                new_seg()
        elif kind == 'OPT':
            flush()
            if val:
                t = clean(val).strip(' \u3000\t')
                if t:
                    lines.append(t)
        elif kind == 'TITLE':
            flush()
            if val:
                t = clean(val).strip(' \u3000\t')
                if t:
                    lines.append(t)
        elif kind in ('WAIT', 'VAR'):
            flush()
        elif kind == 'CTRL':
            if val in BRANCH_OPS:
                branch = True
    flush()
    return lines, st


# ---------------- 覚書（用語辞典） ----------------
def glossary_entries(script_dir):
    """10013.cl3 = 見出し語＋読み（124B/条, 見出し語 在 +0x00..0x20）；
       10012.cl3 = 解説（60B/槽；槽尾 u32 eid,u32 0,u32 flag；flag==0 为条目分隔）"""
    hf = os.path.join(script_dir, '10013.cl3')
    bf = os.path.join(script_dir, '10012.cl3')
    if not (os.path.exists(hf) and os.path.exists(bf)):
        return []
    hd = open(hf, 'rb').read()
    n = struct.unpack_from('<I', hd, 0)[0]
    heads = []
    for i in range(n):
        off = 0x10 + i * 124
        if off + 32 > len(hd):
            heads.append('')
            continue
        try:
            heads.append(hd[off:off + 32].split(b'\x00')[0].decode('cp932').strip())
        except Exception:
            heads.append('')
    bd = open(bf, 'rb').read()
    s0, st = 0x14, 60
    nslots = (len(bd) - s0) // st
    slots = []
    for i in range(nslots):
        sw = bd[s0 + i * st:s0 + (i + 1) * st]
        try:
            txt = sw.split(b'\x00')[0].decode('cp932')
        except Exception:
            txt = ''
        slots.append((txt, struct.unpack_from('<III', sw, 0x30)[2]))
    delims = [i for i, (_, fl) in enumerate(slots) if fl == 0]
    bodies = []
    prev = -1
    for dpos in delims + [nslots]:
        bodies.append(''.join(t for (t, _) in slots[prev + 1:dpos]).strip(' \u3000\t'))
        prev = dpos
    out = []
    for i, b in enumerate(bodies):
        if not b:
            continue
        out.append((heads[i] if i < len(heads) else '', b))
    return out


# ---------------- おまけメニュー / UI 块过滤 ----------------
# 10110 与 10700-10721 内嵌「おまけメニュー（画像鑑賞/シーン再生/戦友絵巻）」块，属系统 UI
MENU_STRICT = re.compile(r'ボタン：|をプレイ済みですか。$')
MENU_VOCAB = {'はい', 'いいえ', '戻る', '選択してください。', '画像鑑賞', 'シーン再生',
              '戦友絵巻', 'おまけメニューに戻る', '決定', 'キャンセル'}


def drop_menu_blocks(lines):
    """strict 命中行 + 与其连通的 vocab 行（迭代扩展）整块剔除"""
    n = len(lines)
    dead = [False] * n
    for i, l in enumerate(lines):
        if MENU_STRICT.search(l):
            dead[i] = True
    changed = True
    while changed:
        changed = False
        for i, l in enumerate(lines):
            if dead[i] or l not in MENU_VOCAB:
                continue
            if (i > 0 and dead[i - 1]) or (i + 1 < n and dead[i + 1]):
                dead[i] = True
                changed = True
    return [l for i, l in enumerate(lines) if not dead[i]]


# ---------------- main ----------------
EXCLUDE = {
    '10000',   # 空壳（仅 #Color）
    '10010',   # 「新選組奇譚」あらすじ（メニュー閲覧用）
    '10011', '10014', '10015', '10016', '10017',   # 数据/flag
    '10050',   # 系统消息（自动存档等）
    '10051',   # 内部状态名（debug）
    '10099',   # 「指南書」＝帮助/教程
    '10012', '10013',   # 覚書（用語辞典）——末尾单独并入
}
EXCLUDE.update('106%02d' % i for i in range(0, 72))   # 10600-10671 空壳/小游戏


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     '..', '_work_hakuoki_sousouroku', 'script', 'script')
    out = sys.argv[2] if len(sys.argv) > 2 else None
    seen = {}
    for f in glob.glob(os.path.join(base, '*')):
        if os.path.splitext(f)[1].lower() == '.cl3':
            seen[os.path.basename(f).lower()] = f
    files = sorted(seen.values(),
                   key=lambda f: int(re.sub(r'\D', '', os.path.basename(f)) or 0))
    all_lines = []
    agg = {'variant': 0, 'merged': 0, 'taken1': 0, 'names': 0}
    used = []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        if stem in EXCLUDE:
            continue
        if open(f, 'rb').read(6) != b'STCM2L':
            continue
        ls, st = extract_file(f)
        for k in agg:
            agg[k] += st[k]
        used.append((stem, len(ls)))
        all_lines.extend(ls)
    gl = glossary_entries(base)
    n_before = len(all_lines)
    all_lines = drop_menu_blocks(all_lines)
    n_menu = n_before - len(all_lines)
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
            fh.write('\n'.join(all_lines) + '\n')
            for h, b in gl:
                fh.write('【%s】%s\n' % (h, b))
    print('files=%d lines=%d (menu_dropped=%d) glossary=%d  %s'
          % (len(used), len(all_lines), n_menu, len(gl), agg))
    if out:
        print('->', out)
    return used


if __name__ == '__main__':
    main()
