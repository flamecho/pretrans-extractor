# -*- coding: utf-8 -*-
"""蝶々事件ラブソディック（PSV, L7CA + Lua5.3 变体字节码）正文提取。

链路：pkg2zip → psvpfsparser → data_release.l7c（L7CA/TaikoLz80，块 0x10000）
      → _data/script_b/story/NN/NNNN.bin（luac 5.3 变体：varint 串长、float32 数字）
      → 调用流（GETTABLE 取常量 + CLOSURE 收口）→ Msg_Set / Msg_NovelSet / Choice_Set
"""
import glob
import os
import re
import struct

WORK = '_work_chouchou'
SRC = os.path.join(WORK, 'ex/_data/script_b/story')
OUT = '提取结果/[PSV-JP]蝶々事件ラブソディック.txt'

TEXT_OPS = ('Msg_Set', 'Msg_NovelSet', 'Msg_NovelSetSpeedFixed')
HEROINE = 'えれな'
HEROINE_SURNAME = '香月'

RUBY = re.compile(r'\{([^{}/|]*)[/|][^{}]*\}')
BARE = re.compile(r'\{([^{}]*)\}')
TOKEN = re.compile(r'^(?:NAME_|SEL_|ADV_|BGM_|SE_|SPRITE_|FADE_|SHAKE_|WAIT_|'
                   r'FILTER_|METOJI$|SEL)')


def parse_chunk(d):
    """主 proto：code + 常量表。本作头长 26B（magic 4 + ver 2 + tail 6 + sizes 5
    + LUAC_INT 4 + LUAC_NUM 4），line/last 各 4B，参数域 3B。"""
    i = d.find(b'@C:')
    assert i > 0
    p = i - 1
    n = d[p]                       # 源串长度（含 NUL 计数，字节不存 NUL）
    p += 1 + (n - 1)
    p += 11
    ncode = struct.unpack_from('<i', d, p)[0]
    p += 4
    code = struct.unpack_from('<%dI' % ncode, d, p)
    p += 4 * ncode
    nconst = struct.unpack_from('<i', d, p)[0]
    p += 4
    consts = []
    for _ in range(nconst):
        t = d[p]
        p += 1
        if t == 0:
            consts.append(None)
        elif t == 1:
            consts.append(bool(d[p]))
            p += 1
        elif t == 3:
            consts.append(struct.unpack_from('<f', d, p)[0])
            p += 4
        elif t == 0x13:
            consts.append(struct.unpack_from('<i', d, p)[0])
            p += 4
        elif t in (4, 0x14):
            L = d[p]
            p += 1
            consts.append(d[p:p + L - 1].decode('utf-8'))
            p += L - 1
        else:
            raise ValueError('const type %d' % t)
    return code, consts


API = re.compile(r'^[A-Z][a-z]+_[A-Za-z]')


def call_stream(code, consts):
    """把 CLOSURE 之前的常量装载聚成一次调用：[name, arg...]。

    函数名走 CamelCase（Msg_Set / Choice_Set / System_WaitFrame），资源与名札全是
    大写（ADV_ / NAME_ / BGM_）⇒ 用「含小写」把调用名挑出来，顺带丢掉循环里
    混进缓冲的散值（如 LOADK 的 -1、计数器）。
    """
    cur = []
    for w in code:
        op = w & 0x3F
        c = (w >> 14) & 0x1FF
        bx = (w >> 14) & 0x3FFFF
        if op in (1, 5):
            cur.append(consts[bx] if bx < len(consts) else None)
        elif op == 6 and (c & 0x100):
            i = c & 0xFF
            cur.append(consts[i] if i < len(consts) else None)
        elif op == 36:
            for k, x in enumerate(cur):
                if isinstance(x, str) and API.match(x):
                    yield cur[k:]
                    break
            cur = []


def clean(text):
    """ruby {漢/よみ} → 漢；主角名宏还原；同框软换行合并。"""
    text = RUBY.sub(r'\1', text)
    text = text.replace('{@MYOUJI}', HEROINE_SURNAME)
    text = text.replace('{@NAME}', HEROINE)
    text = BARE.sub(r'\1', text)
    text = text.replace('\r', '')
    parts = [x for x in text.split('\n') if x.strip('\n') != '']
    return ''.join(parts).strip()


def split_defect(text):
    """修源缺陷：05/0200.bin 有一处把 Lua 调用文本误粘进台词串
    （`…優しい子ね」\\n\\nMsg_Set( NAME_SYUJINKOU,-1,[[\\n「いえ…」`）⇒ 拆成两条台词。"""
    if 'Msg_Set(' not in text:
        return [text]
    head, _, tail = text.partition('Msg_Set(')
    m = re.search(r'\[\[\s*(.*)', tail, re.S)
    body = (m.group(1) if m else '').strip()
    out = [head.strip('\n').strip()]
    if body:
        out.append(clean(body))
    return [x for x in out if x]


def file_lines(path):
    d = open(path, 'rb').read()
    code, consts = parse_chunk(d)
    out = []
    for args in call_stream(code, consts):
        op = args[0]
        if op in TEXT_OPS:
            text = None
            for a in args[1:]:
                if isinstance(a, str) and not TOKEN.match(a):
                    text = a
            if text:
                for s in split_defect(clean(text)):
                    if s:
                        out.append(s)
        elif op == 'Choice_Set':
            strs = [a for a in args[1:] if isinstance(a, str) and not TOKEN.match(a)]
            if not strs:
                continue
            lead = clean(strs[0])
            if lead:
                out.append(lead)
            for opt in strs[1:]:
                o = clean(opt)
                if o:
                    out.append(o)
    return out


def dedupe(seqs, n=8):
    """跨文件「共通导入块」只留一次（同文件内重复保留：回想/咏叹调）。"""
    accepted = []
    owner = []
    index = {}
    stats = {'removed': 0, 'runs': 0}
    result = []
    for fi, (name, lines) in enumerate(seqs):
        i = 0
        kept = []
        while i < len(lines):
            if i + n <= len(lines):
                g = tuple(lines[i:i + n])
                j = index.get(g)
                if j is not None and owner[j] != fi:
                    k = 0
                    while (i + k < len(lines) and j + k < len(accepted)
                           and lines[i + k] == accepted[j + k]):
                        k += 1
                    if k >= n:
                        stats['removed'] += k
                        stats['runs'] += 1
                        i += k
                        continue
            kept.append(lines[i])
            i += 1
        start = len(accepted)
        accepted.extend(kept)
        owner.extend([fi] * len(kept))
        for p in range(max(0, start - n + 1), len(accepted) - n + 1):
            index.setdefault(tuple(accepted[p:p + n]), p)
        result.append((name, kept))
    return result, stats


def build():
    files = sorted(glob.glob(os.path.join(SRC, '*/*.bin')))
    seqs = []
    for f in files:
        rel = os.path.relpath(f, SRC).replace('\\', '/')
        try:
            seqs.append((rel, file_lines(f)))
        except Exception as e:
            print('SKIP', rel, e)
    total_raw = sum(len(v) for _, v in seqs)
    deduped, stats = dedupe(seqs)
    lines = [x for _, v in deduped for x in v]
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('files %d raw %d dup_removed %d runs %d final %d'
          % (len(seqs), total_raw, stats['removed'], stats['runs'], len(lines)))


if __name__ == '__main__':
    build()
