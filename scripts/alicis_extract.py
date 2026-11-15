# -*- coding: utf-8 -*-
"""[PC-JP]籠の中のアリシス（WillPlus / AdvHD, WSC）文本提取器 —— 自包含、argv 式。

用法:
    python alicis_extract.py <Rio.arc> [输出.txt]
    输出默认锚定 <_Trans>/提取结果/[PC-JP]籠の中のアリシス.txt

引擎（本作实证，非套旧作）:
  - 容器 Rio.arc: u32 extGroupCount=1 → 组[ext 4B 'WSC'][count u32=685][tableOffset u32=0x10]
    条目 21B: [name 13B][size u32][offset u32]。闭合: 表尾 0x10+685*21=0x3841==首条 offset;
    末条 offset+size==文件长 6679472。
  - 解密: 每字节 rotl_8(c,6)（(c<<6|c>>4)&0xFF 的逆；等价原版 ror2）。
  - 字节码: opcode 驱动，本作表相对 Lip/Gloss/Rouge 基表有 5 处差异（均在本作 644 本剧情脚本
    走到 EOF 实证；全 685 本仅系统 MAINMENU 在 0xAB 失步，与同族既有记录一致）:
        0x4B 长度 20（基表 16）; 0x66 长度 22（基表 18/AM2 32）;
        0x71 = STRING(0)（基表无）; 0x78 = GENERIC(8)（基表无）; 0x79 = GENERIC(1)（基表无）。
  - 正文: op41(4 参)+单串=旁白; op42(5 参)+名串+台词串=台词(名窗); op02=选项。
    串尾恒为 %K%P（一次点击+送页）; 串内 \\n(0x5C 0x6E) 为软换行, 后接全角空格缩进 ⇒ 合并。
    本作 31,835 条正文记录 100% 以 %K%P 收尾、串内 %K/%P=0 ⇒ 一记录=一页=一次点击 ⇒ 单版。
  - 名札(2026-11-08 修订): 一律保留, op42 的名字与台词同行并列 `名「台词」`。
  - 选项: op02 每项 [2B]+选项\0+[3B 头]+目标指令; 收选项文本一条一行。
  - 排序: 按容器条目原始顺序（= 剧情自然流 T01→T07）。
"""
import struct
import sys
import os
import re

# ---- 本作实证明 opcode 表（基表见 scripts/advhd.py，此处覆写本作差异）----------
GENERIC = {
    0x03: 7, 0x06: 5, 0x08: 2, 0x0A: 1, 0x0C: 3, 0x22: 4, 0x26: 2, 0x45: 4,
    0x47: 2, 0x49: 3, 0x4F: 4, 0x51: 5, 0x52: 2, 0x74: 2, 0x82: 3, 0x83: 1,
    0x84: 1, 0x8B: 1, 0xE2: 1, 0xB8: 3, 0x30: 4, 0x4E: 4, 0x62: 1, 0x85: 2,
    0x86: 2, 0x88: 3, 0x89: 1, 0x8A: 1, 0x8C: 3, 0x8E: 1, 0xBC: 4, 0xBD: 2,
    0xBE: 1, 0xE5: 1, 0x4A: 6, 0x4B: 20, 0xB1: 5, 0x68: 9, 0x65: 8, 0x67: 8,
    0x66: 22, 0x4C: 8, 0x63: 3, 0xB9: 3, 0x64: 8, 0xA6: 1, 0x19: 5, 0x4D: 13,
    0xD0: 9, 0x28: 5, 0xFF: 8, 0xB4: 12, 0xE4: 2, 0x76: 17, 0x01: 10, 0xA8: 16,
    0x0B: 2, 0x05: 2, 0x70: 8, 0x29: 4, 0xB5: 7, 0x55: 1, 0xBB: 1, 0x2C: 12,
    0x8D: 1, 0x04: 0, 0x72: 1, 0xB3: 2, 0xA9: 1, 0xE6: 2, 0x0D: 7,
    0x78: 8, 0x79: 1,                                   # 本作新增
}
STRING = {
    0x50: 0, 0x54: 0, 0x61: 1, 0x73: 9, 0xB6: 2, 0x09: 2, 0xE0: 0, 0x41: 4,
    0x43: 6, 0x46: 9, 0x48: 11, 0x23: 9, 0x21: 10, 0x07: 0, 0xB2: 2, 0x25: 11,
    0xBA: 11, 0x71: 0,                                  # 本作新增 0x71
}
DOUBLESTRING = {0x42: 5}

SUB = re.compile(r'%[A-Za-z]{1,2}')


def rotl8(c, n):
    return ((c << n) | (c >> (8 - n))) & 0xFF


def decrypt(b):
    """WSC 每字节 rotl_8(c,6) 还原明文。"""
    return bytes(rotl8(c, 6) for c in b)


def parse_arc(d):
    """返回 (entries_in_file_order, filesize)。entries=[(name, size, offset)] 按容器原序。"""
    ng = struct.unpack_from('<I', d, 0)[0]
    out = []
    for g in range(ng):
        tag, cnt, toff = struct.unpack_from('<4sII', d, 4 + g * 12)
        ext = tag.split(b'\x00')[0].decode('latin1')
        for k in range(cnt):
            p = toff + k * 21
            name = d[p:p + 13].split(b'\x00')[0].decode('cp932', 'replace')
            sz, off = struct.unpack_from('<II', d, p + 13)
            out.append((name, sz, off, ext))
    return out


def _skip_one(b, i):
    """从 i 处按表分派一条指令, 返回新 i；不合规则抛异常。"""
    op = b[i]; i += 1
    if op in STRING:
        i += STRING[op]
        i = b.index(b'\x00', i) + 1
    elif op in GENERIC:
        i += GENERIC[op]
    elif op in DOUBLESTRING:
        i += DOUBLESTRING[op]
        i = b.index(b'\x00', i) + 1
        i = b.index(b'\x00', i) + 1
    else:
        raise ValueError('unknown sub op %02x' % op)
    return i


def walk_text(b):
    """产出 ('narr', text) / ('line', name, text) / ('opt', text)。"""
    i = 0
    n = len(b)
    while i < n:
        op = b[i]; i += 1
        try:
            if op == 0x02:                       # 选项组
                nch = struct.unpack_from('<H', b, i)[0]; i += 2
                for _ in range(nch):
                    i += 2                        # [2B]
                    e = b.index(b'\x00', i)
                    s1 = b[i:e]; i = e + 1
                    i += 3                        # [3B 头]
                    i = _skip_one(b, i)           # 目标指令
                    yield ('opt', s1)
            elif op == 0x41:
                i += STRING[op]
                e = b.index(b'\x00', i)
                s = b[i:e]; i = e + 1
                yield ('narr', s)
            elif op == 0x42:
                i += DOUBLESTRING[op]
                e = b.index(b'\x00', i)
                nm = b[i:e]; i = e + 1
                e = b.index(b'\x00', i)
                s = b[i:e]; i = e + 1
                yield ('line', nm, s)
            elif op in STRING:
                i += STRING[op]
                i = b.index(b'\x00', i) + 1
            elif op in GENERIC:
                i += GENERIC[op]
            elif op in DOUBLESTRING:
                i += DOUBLESTRING[op]
                i = b.index(b'\x00', i) + 1
                i = b.index(b'\x00', i) + 1
            else:
                return                            # 未知 op ⇒ 停（仅系统脚本会到此）
        except Exception:
            return


def clean(s):
    """去控制码 %K/%P/%p…; 软换行 \\n 及其后的全角空格缩进合并；去首尾空白。"""
    s = s.replace('%K', '').replace('%P', '').replace('%p', '')
    s = SUB.sub('', s)                            # 兜底：其余 %XX 控制码
    s = re.sub(r'\\n[\u3000 ]*', '', s)           # 字面 \n + 缩进 ⇒ 合并
    s = s.strip(' \u3000\t\r\n')
    return s


def main():
    if len(sys.argv) < 2:
        print('用法: python alicis_extract.py <Rio.arc> [输出.txt]', file=sys.stderr)
        return 2
    arc = sys.argv[1]
    if len(sys.argv) >= 3:
        out = sys.argv[2]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        out = os.path.join(os.path.dirname(here), '提取结果', '[PC-JP]籠の中のアリシス.txt')

    d = open(arc, 'rb').read()
    ents = parse_arc(d)

    lines = []
    stat = {'narr': 0, 'line': 0, 'opt': 0, 'scripts': 0, 'no_text': 0}
    for name, sz, off, ext in ents:
        if ext != 'WSC':
            continue
        dec = decrypt(d[off:off + sz])
        got = 0
        for rec in walk_text(dec):
            if rec[0] == 'narr':
                t = clean(rec[1].decode('cp932', 'replace'))
                if t:
                    lines.append(t); stat['narr'] += 1; got += 1
            elif rec[0] == 'line':
                nm = clean(rec[1].decode('cp932', 'replace'))
                t = clean(rec[2].decode('cp932', 'replace'))
                if t:
                    lines.append((nm + t) if nm else t)
                    stat['line'] += 1; got += 1
            else:  # opt
                t = clean(rec[1].decode('cp932', 'replace'))
                if t:
                    lines.append(t); stat['opt'] += 1; got += 1
        stat['scripts'] += 1
        if got == 0:
            stat['no_text'] += 1

    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('scripts=%d no_text=%d' % (stat['scripts'], stat['no_text']))
    print('narr=%d line=%d opt=%d total_lines=%d' % (stat['narr'], stat['line'], stat['opt'], len(lines)))
    print('written', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
