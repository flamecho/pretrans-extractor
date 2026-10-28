# -*- coding: utf-8 -*-
"""崖っぷち令嬢は無気力悪魔で乙女を捨てたい（YU-RIS / YPF v500）全文本提取。

链路：
  pac/scenario.ypf  → YPF 索引（[u32 crc][name][00 01][u32 usize][u32 csize][u32 off][u32 hash]）
                    → zlib 条目 → **明文 cp932 场景源码脚本**（不是 YSTB 字节码）
  → 逐行扫：`\\\\命令` 行跳过；`//` 注释、`#ラベル`、`/* */` 块注释跳过
  → 正文行 = 一次点击（1 行 1 框）；`\\R` = 框内手动换行（同框软换行，删）
  → `\\STRG(123)` = 主角名输入变量 → 就地替换
  → `\\SEL(a, b)` = 选项（成行）

用法：python gakeppuchi_extract.py <工作目录> <主角名>
"""
import struct
import sys
import os
import re
import zlib

NAME_VAR = r'\STRG(123)'
INLINE_R = re.compile(r'\\R')
INLINE_ANY = re.compile(r'\\[A-Za-z_][A-Za-z0-9_.]*(\[[^\]]*\])?(\([^)]*\))?')


def unpack_ypf(path):
    """按索引顺序返回 [(usize, csize, off)] 与解压后的数据列表。"""
    d = open(path, 'rb').read()
    assert d[:4] == b'YPF\x00'
    count = struct.unpack_from('<I', d, 8)[0]
    doff = struct.unpack_from('<I', d, 12)[0]
    out = []
    p = 0x20
    while p + 30 < doff:
        e = d.find(b'\x00\x01', p + 5, doff)
        if e < 0:
            break
        usize, csize, off, _ = struct.unpack_from('<IIII', d, e + 2)
        if not (off >= doff and off + csize <= len(d) and csize > 0
                and usize >= csize):
            p = e + 2
            continue
        blob = d[off:off + csize]
        try:
            raw = zlib.decompress(blob)
        except zlib.error:
            raw = blob[:usize]
        out.append((usize, csize, off, raw))
        p = e + 22
    # 注：ysbin.ypf 头写 count=270，实际索引 269 条即闭合（末条结束位 == 数据区起点），
    # 少 1 条是源档自身现象（其它 YPF 均 count==实条目）；允许 count-1。
    assert count - 1 <= len(out) <= count, (len(out), count)
    return out


def extract_text(lines, name):
    """源码行 → 正文行（一次点击一行）。"""
    res = []
    stat = {'text': 0, 'opt': 0, 'name': 0, 'r_merge': 0, 'skip_cmd': 0}
    in_block = False
    for ln in lines:
        s = ln.strip()
        if in_block:
            if '*/' in s:
                in_block = False
            continue
        if s.startswith('/*'):
            if '*/' not in s:
                in_block = True
            continue
        if not s or s.startswith('//') or s.startswith('#'):
            continue
        if s.startswith('\\'):
            stat['skip_cmd'] += 1
            if s.startswith('\\SEL('):          # 选项：\SEL(文1, 文2)
                body = s[s.index('(') + 1:]
                body = body[:body.rfind(')')] if ')' in body else body
                for opt in body.split(','):
                    opt = opt.strip()
                    if opt:
                        res.append(opt)
                        stat['opt'] += 1
            continue
        t = s
        if NAME_VAR in t:
            stat['name'] += t.count(NAME_VAR)
            t = t.replace(NAME_VAR, name)
        if '\\R' in t:
            stat['r_merge'] += t.count('\\R')
            t = INLINE_R.sub('', t)
        t = INLINE_ANY.sub('', t)               # 其余行内命令一律剥除
        t = t.strip()
        if t:
            res.append(t)
            stat['text'] += 1
    return res, stat


def tips_entries(work):
    """用語辞典：ysbin.ypf 里唯一一个以 es.TIPS.TX.DEF.SET 注册词条的 YSTB。

    YSTB v555 与 v0x199 同构（32B 头 + code/args/res/off 四段），唯一差别是
    XOR 键：本作 `0xb9 0xf3 0xd0 0x82`（非 Diary 的默认 0x96ac6fd3）。
    判据：解密后 code 段每条指令的 [2][3] 字节恒为 0（0xd0/0x82 的异或反推）、
    且 res 段字符串成片可读。
    """
    key = bytes([0xb9, 0xf3, 0xd0, 0x82])
    pac = os.path.join(work, 'pac', 'ysbin.ypf')
    out = []
    for usize, csize, off, raw in unpack_ypf(pac):
        if raw[:4] != b'YSTB':
            continue
        dec = raw[:32] + bytes(c ^ key[i % 4] for i, c in enumerate(raw[32:]))
        if b'es.TIPS.TX.DEF.SET' not in dec:
            continue
        inst, csz, asz, rsz, osz, _ = struct.unpack_from('<6I', dec, 8)
        assert 32 + csz + asz + rsz + osz == len(dec)
        res = dec[32 + csz + asz: 32 + csz + asz + rsz]
        p, M = 0, []
        while p + 3 <= len(res):
            t = res[p]
            ln = struct.unpack_from('<H', res, p + 1)[0]
            p += 3
            if p + ln > len(res):
                break
            if t == 0x4D:
                M.append(res[p:p + ln].decode('cp932', 'replace').strip('"'))
            p += ln
        for i, v in enumerate(M):
            if v == 'es.TIPS.TX.DEF.SET' and i + 1 < len(M):
                body, k = M[i + 1], ''
                for j in range(i + 2, min(i + 40, len(M))):
                    if M[j] == 'es.TIPS.DEF.SET':
                        k = M[j + 1]
                        break
                if k:
                    out.append('【%s】%s' % (k, body))
    return out


def main():
    work = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else 'セシリア'
    pac = os.path.join(work, 'pac', 'scenario.ypf')
    entries = unpack_ypf(pac)
    # 索引顺序不是剧本顺序：按数据偏移排序＝源文件顺序（aruma01→13、cris01→06）
    entries.sort(key=lambda x: x[2])
    all_lines, stat = [], {'text': 0, 'opt': 0, 'name': 0, 'r_merge': 0, 'skip_cmd': 0}
    per_file = []
    for usize, csize, off, raw in entries:
        if off >= 286000:            # 尾部 3 个＝系统文件（op_senntaku／回想一览／启动 logo），不进正文
            print('  skip system file off=%d' % off)
            continue
        text = raw.decode('cp932', 'replace')
        head = text.split('\r\n')[0]
        lines, st = extract_text(text.split('\r\n'), name)
        for k in stat:
            stat[k] += st[k]
        per_file.append((head, len(lines), len(raw)))
        all_lines.extend(lines)
    print('ypf entries', len(entries))
    for h, n, sz in per_file:
        print('  %-16s lines=%-5d bytes=%d' % (h[:16], n, sz))
    print('stat', stat)
    tips = tips_entries(work)
    print('tips', len(tips))
    if tips:
        all_lines.extend(tips)             # 末尾用語辞典块（【見出し語】解説文）
    print('total', len([l for l in all_lines if l]))
    out = os.path.join(work, '_out.txt')
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + ('\n'.join(all_lines) + '\n').encode('utf-8'))


if __name__ == '__main__':
    main()
