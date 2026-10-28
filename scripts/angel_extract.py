# -*- coding: utf-8 -*-
"""Angel Profile (PS2) 文本抽取 —— 常量池顺序还原。

判定依据（L1，记录自定界）：
  * 正文 = 常量池中紧跟数值（voice id）的 cp932 字符串记录；
    同一句内软换行用 '\n' 存放（需合并）。
  * 选项 = 'select' 键之后的字符串（[选项id][文本][道具id] 三元组）。
  * 名札 = 'mesname' 键之后的字符串（独立名字窗）→ 丢弃。
  * 数据表（[名][价] 交替）不以 voice id 引导，靠长度/标点规则自然排除。
"""
import re
import struct

JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
PUNC = re.compile(r'[。、！？…「」『』（）\n]')
NAV = {'次へ', '戻る', 'やめる', '戻る\t', '次へ\t'}
PROMPT = re.compile(r'^[\u3000\s]*(どうしますか|どれにしますか)[？?]?[\u3000\s]*$')


def afs_index(path):
    with open(path, 'rb') as f:
        h = f.read(8)
        if h[:4] != b'AFS\0':
            raise SystemExit('not AFS')
        n = struct.unpack_from('<I', h, 4)[0]
        head = f.read(n * 8)
    return [struct.unpack_from('<II', head, i * 8) for i in range(n)]


def tokens(d):
    p = 0
    n = len(d)
    out = []
    while p < n - 5:
        t = d[p]
        if t == 4:
            L = struct.unpack_from('<I', d, p + 1)[0]
            if 2 <= L <= 4000 and p + 5 + L <= n:
                raw = d[p + 5:p + 5 + L]
                if raw[-1] == 0 and b'\x00' not in raw[:-1]:
                    try:
                        out.append(('S', raw[:-1].decode('cp932')))
                        p += 5 + L
                        continue
                    except UnicodeDecodeError:
                        pass
        elif t == 3 and p + 5 <= n:
            out.append(('N', struct.unpack_from('<f', d, p + 1)[0]))
            p += 5
            continue
        p += 1
    return out


KEY = re.compile(r'^[a-z_][a-z0-9_]{1,30}$')


def is_key(s):
    return bool(KEY.match(s))


def module_name(tk):
    for t, v in tk[:40]:
        if t == 'S' and v.startswith('/test2/'):
            return v[7:]
    return None


def build_name_set(f, ents):
    names = set()
    for off, sz in ents:
        f.seek(off)
        d = f.read(sz)
        if d[:4] != b'\x1bLua':
            continue
        tk = tokens(d)
        for i, (t, v) in enumerate(tk[:-1]):
            if t == 'S' and v == 'mesname':
                j = i + 1
                while j < len(tk) and tk[j][0] == 'N':
                    j += 1
                if j < len(tk) and tk[j][0] == 'S' and tk[j][1].strip():
                    names.add(tk[j][1])
    names |= {'客A', '客B', 'モブA', 'モブB'}
    return names


def extract(d, names):
    """-> [(kind, text)]  kind: text / opt"""
    tk = tokens(d)
    out = []
    i = 0
    n = len(tk)
    while i < n:
        ty, v = tk[i]
        if ty == 'S' and v == 'select':
            j = i + 1
            while j < n:
                t2, v2 = tk[j]
                if t2 == 'S' and is_key(v2):
                    break
                if t2 == 'S' and JP.search(v2) and v2 not in NAV and v2 not in names:
                    out.append(('opt', v2))
                j += 1
            i = j
            continue
        if ty == 'S' and v == 'mesname':
            j = i + 1
            while j < n and tk[j][0] == 'N':
                j += 1
            if j < n and tk[j][0] == 'S':
                i = j + 1
                continue
        if ty == 'S' and v == 'text':
            j = i + 1
            while j < n:
                t2, v2 = tk[j]
                if t2 == 'S' and is_key(v2):
                    break
                if t2 == 'S' and JP.search(v2) and v2 not in names and not PROMPT.match(v2):
                    out.append(('text', v2))
                j += 1
            i = j
            continue
        if ty == 'N' and i + 1 < n and tk[i + 1][0] == 'S':
            s = tk[i + 1][1]
            if is_key(s):
                i += 1
                continue
            if JP.search(s) and s not in names and s not in NAV and not PROMPT.match(s):
                if len(s) >= 13 or PUNC.search(s):
                    out.append(('text', s))
            i += 2
            continue
        i += 1
    return out
