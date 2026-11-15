# -*- coding: utf-8 -*-
"""[JP]SILVER CHAOS（PC / VividColor GameSystem 2003）全文本抽取

容器：`PACK/SCRIPT.com` ＝ MZP 壳 0x6400 ＋ 裸存成员 ＋ LZSS 压缩索引 ＋ "PACK" 尾指针
      索引条目 10 B：u32 off | u32 namelen(字符) | u16 flag | UTF-16LE 名
成员：`.scr` ＝ [UTF-16LE NUL 分隔 token 流（前段）][u32 布局数据（后段，无日文）]
      token 流 = 路径 | '' | 标签... | '' | 指令流
指令（26 个，取自 scrth.dll 0x2B6D4 名字表）：
      chr_set [名] / Setmes 正文 [语音名] / Putmes / Setsel 选项... / Change 目标 ...
成行（L1）：chr_set → Setmes → Putmes 构成一条记录；1:1:1（8,144 各）⇒ 一次点击＝一框＝一行
      说话人：NAME.TEXB 为独立名牌图集（1134×320 ARGB）⇒ 具名 `chr_set` 属独立名字窗，剔除

用法：python scripts/sc2003_extract.py <SCRIPT.com> <out.txt>
"""
import collections
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_cmp as P

PAYLOAD_START = 0x6400
OPS = {
    'EVScr', 'Ending', 'Scroll', 'Wait', 'BgdXY', 'Ccc', 'Resetflag', 'Getflag',
    'Setflag', 'Rch', 'Cch', 'Lch', 'LLdchr', 'RLdchr', 'Movie', 'Ldev', 'Change',
    'Playbgm', 'Fade', 'Setmes', 'Setsel', 'Ldbg', 'Ldchr', 'Playse', 'Putmes', 'chr_set',
}
JP = [(0x3000, 0x30FF), (0x4E00, 0x9FFF), (0xFF00, 0xFFEF), (0x2010, 0x203F), (0x2460, 0x24FF)]


def parse_index(data):
    if data[-8:-4] != b'PACK':
        raise SystemExit('尾部 "PACK" 缺失')
    idx = struct.unpack_from('<I', data, len(data) - 4)[0]
    declared = struct.unpack_from('<I', data, idx)[0]
    raw, _ = P.decompress(data[idx + 4:len(data) - 8], declared)
    if len(raw) != declared:
        raise SystemExit('索引解压 %d != %d' % (len(raw), declared))
    members, p = [], 0
    while p + 10 <= len(raw):
        off, nlen, flag = struct.unpack_from('<IIH', raw, p)
        p += 10
        if nlen == 0:
            break
        members.append((off, raw[p:p + nlen * 2].decode('utf-16le'), flag))
        p += nlen * 2
    return idx, members


def split_tokens(buf):
    toks, start, k = [], 0, 0
    while k + 1 < len(buf):
        if buf[k] == 0 and buf[k + 1] == 0:
            toks.append(buf[start:k].decode('utf-16le', 'replace'))
            start, k = k + 2, k + 2
        else:
            k += 2
    if start < len(buf):
        toks.append(buf[start:].decode('utf-16le', 'replace'))
    return toks


def front_tokens(buf):
    """切掉尾部 u32 布局数据：第一处「连续 6 个 ≤1 字符 token」即后段起点。"""
    toks = split_tokens(buf)
    for i in range(4, len(toks) - 6):
        if all(len(t) <= 1 for t in toks[i:i + 6]):
            return toks[:i], toks[i:]
    return toks, []


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    d = src.read_bytes()
    idx, members = parse_index(d)

    lines = []
    stats = collections.Counter()
    problems = []
    per_file = []
    names = collections.Counter()

    for mi, (off, name, flag) in enumerate(members):
        nxt = members[mi + 1][0] if mi + 1 < len(members) else idx
        buf = d[off:nxt]
        toks, tail = front_tokens(buf)
        if any(0x3000 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF
               for t in tail for c in t):
            problems.append('%s: 后段含日文' % name)

        # header: 路径 | '' | 标签... | ''
        if not toks or not toks[0].startswith('txt\\'):
            problems.append('%s: 头部路径缺失 %r' % (name, toks[:2]))
            continue
        i = 1
        if i < len(toks) and toks[i] == '':
            i += 1
        labels = []
        while i < len(toks) and toks[i] != '':
            labels.append(toks[i])
            i += 1
        i += 1  # 跳过标签表结束的空串
        stats['labels'] += len(labels)

        n_here = 0
        while i < len(toks):
            t = toks[i]
            if t == '':
                i += 1
                continue
            if t not in OPS:
                problems.append('%s: 指令流出现未知 token %r @%d' % (name, t, i))
                i += 1
                continue
            i += 1
            if t == 'chr_set':
                if i < len(toks) and toks[i] and toks[i] not in OPS:
                    names[toks[i]] += 1
                    i += 1
            elif t == 'Setmes':
                if i >= len(toks):
                    problems.append('%s: Setmes 无正文' % name)
                    break
                text = toks[i].rstrip('\t')
                i += 1
                while i < len(toks) and toks[i] and toks[i] not in OPS:
                    i += 1          # 语音名等
                if text.strip():
                    lines.append(text)
                    n_here += 1
                    stats['dialogue'] += 1
                else:
                    problems.append('%s: 空正文' % name)
            elif t == 'Setsel':
                opts = []
                while i < len(toks) and toks[i] not in OPS:
                    if toks[i]:
                        opts.append(toks[i])
                    i += 1
                if not opts:
                    problems.append('%s: Setsel 无选项' % name)
                lines.extend(opts)
                n_here += len(opts)
                stats['opt_groups'] += 1
                stats['opt_items'] += len(opts)
            elif t in ('Change', 'Ldchr', 'RLdchr', 'LLdchr', 'Ldbg', 'Ldev', 'Playse', 'Movie',
                       'Setflag', 'Getflag', 'Resetflag', 'Cch', 'Lch', 'Rch'):
                if i < len(toks) and toks[i] and toks[i] not in OPS:
                    i += 1
            elif t == 'Playbgm':
                while i < len(toks) and toks[i] and toks[i] not in OPS:
                    i += 1
            # 其余零参指令（Putmes/Fade/Ccc/Ending/...）直接跳过
        per_file.append((name, n_here, flag))

    out.write_text('\ufeff' + '\n'.join(lines) + '\n', encoding='utf-8', newline='\n')

    print('members=%d idx=0x%X' % (len(members), idx))
    print('lines=%d dialogue=%d opt_groups=%d opt_items=%d labels=%d'
          % (len(lines), stats['dialogue'], stats['opt_groups'], stats['opt_items'], stats['labels']))
    print('speakers=%d' % len(names))
    print('problems=%d' % len(problems))
    for p in problems[:20]:
        print('  !', p)
    print('%-18s %6s' % ('member', 'lines'))
    for name, n, flag in per_file:
        print('%-18s %6d' % (name, n))


if __name__ == '__main__':
    main()
