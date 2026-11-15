#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Director 上的「自研 DSL 脚本引擎」→ 一 MSG 一框的正文文本。

形态（EverLoyalty / Core 2002 实测，Director 8.5 `MV93`）
  * 逻辑不在 Lscr 里，而在**文本 cast 成员**里：`CAST/SCRIPT.CXT` 的每个成员是一段
    **纯文本 DSL**（`\\r` 分行的指令流），成员顺序＝事件顺序：
        BG / CHAR / CHARDEL / FADE / FADE2 / MSG / SELECT / QUAKE / MOVE / BGM / SE /
        BGMSTOP / SESTOP / EVENT / JUMP / FLAGJUMP / SELECTJUMP / FLAG / END /
        TITLE / WAIT / STAFF / EFFECT / EVENTEND     ← GAME.DXR 内的 handler 名表实测 24 个
  * 正文文本在另一份 cast 里（`CAST/TEXT.CXT`），每个成员一屏：
        `MSG  <成员名>`              ＝ 一个文本框 ＝ 一次点击（L0：DSL 的 MSG 指令）
        `SELECT <提问>,<选项1>,<选项2>,<选项3>`  ＝ 一屏选项，选项各占一行
  * 成员名从 CASt 的 info 块取（`XFIR` 小端文件，**但 CASt 头字段是大端**：
        b[8:12] type(BE) / b[12:16] infoLen(BE) / b[16:20] specLen(BE)，info 起于 b[20]，
        名字是 info+70 处的 pascal 串）。CASt 与 XMED 在文件里**同序等数**，按序配对。

判据（L0/L1）
  * 一次点击＝一个 MSG：每条 MSG 指向**独立 cast 成员**，成员内 `\\r` 是作者手断的排版换行
    （反向验证：全库每成员 1..4 段、每段 ≤35 全角字 ⇒ 一屏容纳，无内部翻页）⇒ 合并成一行。
  * 顺序＝DSL 行序（脚本是全分支并集，不追求单线）：JUMP/FLAGJUMP 只改变控制流，
    不改写文件里的先后；同名成员被多处引用时**每处各出一行**。
  * 未被任何 MSG/SELECT 引用的成员＝作者弃用（改稿残留）⇒ 不出，只在 `--list-unused` 里报。
  * 名字：`【ユーリス】\\r台词` —— 名字与台词**在同一个文本框内** ⇒ 保留并接在同行台词前。

用法
  python scripts/director_dsl_text.py --script CAST/SCRIPT.CXT --text CAST/TEXT.CXT \\
      --out out.txt [--stat] [--list-unused]
"""
import argparse
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from director_d8_text import chunks_of, xmed_text          # noqa: E402

MEMBER = re.compile(r'^[A-Za-z0-9_\-]{1,40}$')
OPVAR = re.compile(r'^[A-Z]+[A-Z0-9]*$')


# ---------- cast：成员名 ↔ 文本 ----------

def cast_texts(path):
    """→ [(成员名, 文本)]，按文件里的成员顺序（CASt 与 XMED 同序等数）。"""
    d = open(path, 'rb').read()
    ch = chunks_of(d)
    cast = [c for c in ch if c[0] == 'CASt']
    xmed = [c for c in ch if c[0] == 'XMED']
    if len(cast) != len(xmed):
        raise SystemExit(f'[E] {os.path.basename(path)}: CASt {len(cast)} != XMED {len(xmed)}')
    out = []
    for (_c1, o1, s1), (_c2, o2, s2) in zip(cast, xmed):
        b = d[o1:o1 + 8 + s1]
        try:
            info_len = struct.unpack_from('>I', b, 12)[0]
            info = b[20:20 + info_len]
            n = info[70]
            name = info[71:71 + n].decode('latin1')
        except (struct.error, IndexError):
            name = ''
        if not MEMBER.match(name or ''):
            name = _scan_name(info)
        out.append((name, xmed_text(d[o2 + 8:o2 + 8 + s2]) or ''))
    return out


def _scan_name(info):
    """兜底：在 info 块里找 `<len><ASCII 成员名>`（长度 1..40，字符集受限）。"""
    for i in range(len(info) - 2):
        n = info[i]
        if 1 <= n <= 40 and i + 1 + n <= len(info):
            s = info[i + 1:i + 1 + n].decode('latin1', 'replace')
            if MEMBER.match(s):
                return s
    return ''


# ---------- DSL ----------

def merge(t):
    """框内换行合并：`\\r` 是排版换行 ⇒ 去掉；行首全角空格是字下げ ⇒ 去掉。"""
    parts = [p for p in t.split('\r') if p.strip()]
    if not parts:
        return ''
    head = parts[0].strip('\u3000 ')
    tail = [p.lstrip('\u3000 ') for p in parts[1:]]
    return (head + ''.join(tail)).strip('\u3000 ')


def script_ops(path):
    """→ [(成员序号, 指令, 参数串)]，按 DSL 行序。"""
    d = open(path, 'rb').read()
    ops = []
    for i, (_cc, off, sz) in enumerate([c for c in chunks_of(d) if c[0] == 'XMED']):
        t = xmed_text(d[off + 8:off + 8 + sz]) or ''
        for line in t.split('\r'):
            s = line.strip()
            if not s or s.startswith(';') or s.startswith('*'):
                continue
            kw, _, rest = s.partition(' ')
            kw = kw.upper()
            if not OPVAR.match(kw):
                continue
            ops.append((i, kw, rest.strip()))
    return ops


def build(script_path, text_path, want_stat=False, list_unused=False):
    texts = cast_texts(text_path)
    name2text = dict(texts)
    lines, stat = [], {'msg': 0, 'sel': 0, 'opt': 0, 'miss': 0, 'empty': 0, 'ops': 0}
    miss, used = [], set()

    for idx, kw, rest in script_ops(script_path):
        stat['ops'] += 1
        if kw == 'MSG':
            ref = rest.split(',')[0].strip()
            used.add(ref)
            t = name2text.get(ref)
            if t is None:
                stat['miss'] += 1
                miss.append((idx, kw, ref))
                continue
            s = merge(t)
            if not s:
                stat['empty'] += 1
                continue
            lines.append(s)
            stat['msg'] += 1
        elif kw == 'SELECT':
            args = [a.strip() for a in rest.split(',')]
            for k, ref in enumerate(args):
                if not ref or ref.upper() == 'NULL':
                    continue
                used.add(ref)
                t = name2text.get(ref)
                if t is None:
                    stat['miss'] += 1
                    miss.append((idx, kw, ref))
                    continue
                s = merge(t)
                if not s:
                    stat['empty'] += 1
                    continue
                lines.append(s)
                if k == 0:
                    stat['sel'] += 1          # SELECT 的提问行（同一文本框）
                else:
                    stat['opt'] += 1          # 选项：一行一条

    unused = [(n, t) for n, t in texts if n not in used]
    if want_stat:
        print('# 指令 %d 条；MSG %d 行；SELECT 提问 %d 行；选项 %d 行；空文本 %d；缺成员 %d'
              % (stat['ops'], stat['msg'], stat['sel'], stat['opt'], stat['empty'], stat['miss']))
        print('# 成员 %d 个，被引用 %d 个，未引用 %d 个'
              % (len(texts), len(used & set(name2text)), len(unused)))
        for idx, kw, ref in miss:
            print('  [缺] script#%d %s %s' % (idx, kw, ref))
    if list_unused:
        for n, t in unused:
            print('  [未用] %-16s %r' % (n, merge(t)[:40]))
    return lines, stat, miss, unused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--script', required=True, help='DSL 文本 cast（如 CAST/SCRIPT.CXT）')
    ap.add_argument('--text', required=True, help='正文文本 cast（如 CAST/TEXT.CXT）')
    ap.add_argument('--out')
    ap.add_argument('--stat', action='store_true')
    ap.add_argument('--list-unused', action='store_true')
    a = ap.parse_args()

    lines, stat, miss, unused = build(a.script, a.text, a.stat, a.list_unused)
    if a.out:
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('写出 %s：%d 行' % (a.out, len(lines)))
    if not a.out or a.stat:
        print('行数 %d' % len(lines))


if __name__ == '__main__':
    main()
