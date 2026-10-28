#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""忍び、恋うつつ (NS) STCM2L 提取：一次点击 = 一行。

L0 链路
  XCI(hactool/prod_fixed.keys) -> NCA -> RomFS/CONTENTS/STORY_01|02.cpk -> SCRIPT/*.DAT
  （STCM2L，UTF-8）
L1 记录形状（自定界）
  指令 = [u32 op][u32 nparams][u32 len]，len=整条字节数（4 对齐）；全文件按此平铺，末尾恰好
  落在 EXPORT_DATA 前（1001.DAT: 0xbb8f0），故可整段走完不断帧
  串记录（payload 内）= [u32 L/4][u32 1][u32 L][utf8][NUL pad]
L0 断框（一次点击）
  op 0x1F4（np=0、无串）= 等待/点击；两次 0x1F4 之间的正文行 = 同框 ⇒ 合并成一行
  op 0x6（goto）= 互斥分支边界 ⇒ 也断开（随后按「相邻同文去重」保留一条）
  op 0x10678/0x10688（按文件平移）= 名札（独立名窗）⇒ 丢弃
  op 0x2EC3C（np=8）= 两名版正文组（#Name 宏版 / 直写名版）⇒ 取一组
  含 sureNN 且带正文的指令 = 选项
"""
import sys, os, glob, re, struct
from collections import Counter

A4 = lambda n: (n + 3) & ~3
MACRO = re.compile(r'#[A-Za-z]+\[[^\]]*\]')
NAME_MACRO = re.compile(r'#Name\[(\d+)\]')
SURE = re.compile(r'^sure\d+$')
HERO = {1: '片桐', 2: 'かえで'}
WAIT = 0x1F4
GOTO = 0x6

# 系统/UI/调试串（直接上屏但非正文）
SYS = re.compile(
    r'(?:がよろしいですか？$'
    r'|移行しますか？$'
    r'|タイトルに戻ります'
    r'|が解放されました。$'
    r'|をクリアしてから$)'
)


def scan_strings(body, base):
    out, i, n = [], 0, len(body)
    while i + 12 <= n:
        l4, one, L = struct.unpack_from('<3I', body, i)
        if one == 1 and L == l4 * 4 and 4 <= L <= 0x8000 and i + 12 + L <= n:
            raw = body[i + 12:i + 12 + L].rstrip(b'\x00')
            if raw:
                try:
                    s = raw.decode('utf-8')
                except Exception:
                    s = None
                if s is not None and A4(len(raw) + 1) == L and all(ord(c) >= 0x20 for c in s):
                    out.append((base + i, s))
                    i += 12 + L
                    continue
        i += 4
    return out


def walk(path):
    d = open(path, 'rb').read()
    i = d.find(b'CODE_START_')
    o, n, recs = i + 16, len(d), []
    while o + 12 <= n:
        op, np_, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n or np_ > 64:
            break
        recs.append((o, op, np_, ln, scan_strings(d[o + 12:o + ln], o + 12)))
        o += ln
    return recs


def has_jp(s):
    for ch in s:
        if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff'):
            return True
    return False


def dialogueish(s):
    if len(s) >= 8:
        return True
    return s[:1] in '\u300c\u300e\uff08\u3000\u2026'


TEXT_PUNCT = set('\u2026\u2025\u3001\u3002\uff01\uff1f\u300c\u300d\u300e\u300f'
                 '\uff08\uff09\u3008\u3009\u300a\u300b\u30fb\u30fc\uff5e\u301c'
                 '\uff1a\uff1b\uff0f\uff3c\u203b\u2605\u2606\u266a\u25c6\u25c7'
                 '\u25a0\u25a1\u25cf\u25cb\u2015\u2014')


def is_text(s):
    """正文用字判定：含假名/汉字，或含全角标点（纯记号行如「（……。」也是正文）。"""
    for c in s:
        if ('\u3040' <= c <= '\u30ff') or ('\u4e00' <= c <= '\u9fff') or c in TEXT_PUNCT:
            return True
    return False


def clean(s):
    s = NAME_MACRO.sub(lambda m: HERO.get(int(m.group(1)), ''), s)
    return MACRO.sub('', s)


def classify(recs):
    cnt = Counter()
    for o, op, np_, ln, ss in recs:
        if np_ != 1:
            continue
        for _, s in ss:
            if has_jp(s) and dialogueish(s) and not SURE.match(s):
                cnt[op] += 1
    text_op = cnt.most_common(1)[0][0] if cnt else None
    lead = Counter()
    for k, (o, op, np_, ln, ss) in enumerate(recs):
        if op == text_op or np_ != 1 or len(ss) != 1:
            continue
        s = clean(ss[0][1])
        if len(s) > 14 or any(c in s for c in '\u300c\u300d\u300e\u300f\uff08\uff09\u3000\u2026'):
            continue
        for o2, op2, np2, ln2, ss2 in recs[k + 1:]:
            if op2 == WAIT or op2 == GOTO:
                break
            if op2 == text_op:
                lead[op] += 1
                break
    name_op = lead.most_common(1)[0][0] if lead else None
    if name_op and lead[name_op] < 3:
        name_op = None
    arr_ops = set()
    for o, op, np_, ln, ss in recs:
        if np_ < 4 or op in (text_op, name_op):
            continue
        jp = [s for _, s in ss if has_jp(s) and dialogueish(s) and not SURE.match(s)]
        if len(jp) >= 3:
            arr_ops.add(op)
    return text_op, name_op, arr_ops


def period_collapse(items):
    """同一框内「同名版 / 直写名版」等重复块：若以 p 为周期自重复，只留一份。"""
    n = len(items)
    for p in range(1, n // 2 + 1):
        if n % p:
            continue
        if all(clean(items[i]) == clean(items[i + p]) for i in range(n - p)):
            return items[:p]
    return items


def split_variant(strs):
    """np>=4 的正文组：字符串表恒为「两份等长变体」。取含 #Name 宏的一半。"""
    n = len(strs)
    if n < 2 or n % 2:
        return strs
    h = n // 2
    a, b = strs[:h], strs[h:]
    same = sum(1 for x, y in zip(a, b) if clean(x) == clean(y))
    if same < max(1, h - 1):
        return strs
    return b if any('#Name[' in s for s in b) else a


def boxes(recs, text_op, name_op, arr_ops):
    out, cur = [], []

    def flush():
        if not cur:
            return
        cur[:] = period_collapse(cur)
        line = ''.join(clean(s).lstrip('\u3000') if k else clean(s)
                       for k, s in enumerate(cur))
        cur.clear()
        if not line.strip():
            return
        if out and out[-1] == line:
            return
        out.append(line)

    for o, op, np_, ln, ss in recs:
        if op == WAIT or op == GOTO:
            flush()
            continue
        if not ss:
            continue
        strs = [s for _, s in ss]
        if any(SURE.match(s) for s in strs):
            opts = [s for s in strs if not SURE.match(s) and has_jp(s)]
            if opts:
                flush()
                for s in opts:
                    out.append(clean(s))
            continue
        if op == name_op:
            continue
        if op == text_op:
            for s in strs:
                if is_text(s) and dialogueish(s):
                    cur.append(s)
            continue
        if op in arr_ops:
            grp = [s for s in strs if has_jp(s) and dialogueish(s)]
            if not grp:
                grp = strs
            if len(strs) >= 2 and len(strs) % 2 == 0:
                grp = split_variant(strs)
                grp = [s for s in grp if is_text(s)]
            for s in grp:
                cur.append(s)
    flush()
    return out


def extract(path):
    recs = walk(path)
    text_op, name_op, arr_ops = classify(recs)
    rows = boxes(recs, text_op, name_op, arr_ops)
    out, pend = [], 0
    for r in rows:
        if SYS.search(r):
            pend = 6
            continue
        if pend and r in ('はい', 'いいえ'):
            pend -= 1
            continue
        pend = 0
        out.append(r)
    return out, text_op, name_op, arr_ops


if __name__ == '__main__':
    root = sys.argv[1]
    files = sorted(glob.glob(os.path.join(root, 'SCRIPT', '*.DAT')),
                   key=lambda p: (len(os.path.basename(p)), os.path.basename(p)))
    total = 0
    for p in files:
        rows, top, nop, arr = extract(p)
        print('%-10s %4d  text=0x%-6x name=%s arr=%s' %
              (os.path.basename(p), len(rows), top or 0, hex(nop) if nop else '-',
               [hex(a) for a in sorted(arr)]))
        total += len(rows)
    print('TOTAL', total)
