# -*- coding: utf-8 -*-
"""DDEngine / DDSystem（「Daylight」2008）—— dl_text.dat 全文本提取

用法:
  python scripts/ddengine_text.py <dl_text.dat> <out.txt> [--dump-raw <dir>] [--order name|file]

场景顺序: 记录名 sc<章1><场3><段3><a|b>（例 sc1001009a = 第1章-001场-009段-a）。
  容器表顺序是哈希顺序（乱序）；`--order name`（默认）按章/场/段排序 = 剧情顺序。
  证据：排序后「本记录某个跳转目标 == 下一条记录名」65/168，而文件顺序只有 2/168。

容器（DDP1）:
  0x00  "DDP1"
  0x04  u32 ×4（33 / 129 / 272 / 65，用途未明）
  0x110 文件表：变长条目 [u8 条目总长][u32 BE 偏移][名字 NUL]，条目间可能夹 1 个 0x00 填充
  条目指向的记录：
        [u32 csize][u32 usize][u8 标志(0x0b/0x09)]["DDSxSpt"][00 00][u16 BE][00] + 压缩流
        csize == 0 ⇒ 未压缩（前 8 字节后跟 "DDSxSpt"，本作 11 条，均为 46 B 的空场景）

压缩算法（从 DAYLIGHT.DAT 反汇编得出，VA 0x15900..0x15b60 的解压循环）:
  LZ77，控制字节 c：
    c < 0x1D          字面量长度 = c+1
    c == 0x1D         字面量长度 = 下一字节 + 0x1E
    c == 0x1E         字面量长度 = BE16 + 0x11E
    c == 0x1F         字面量长度 = BE32
    0x20..0x3F        距离 = ((c>>2)&7)+1，长度 = (c&3)+3
    0x40..0x5F        距离 = 下一字节+1，长度 = (c&0x1F)+7
    0x60..0x7F        距离 = ((c&0x1F)<<8|b)+1，长度 = L+7
    0x80..0xFF        距离 = ((c&0x1F)<<8|b)+1，长度 = ((c>>5)&3)+3
  其中 0x60.. 的 L：0xFE ⇒ BE16+0x102，0xFF ⇒ BE32，否则 +4，再统一 +3。
  ★ 校验：输出长度必须等于 usize（169 条记录全部精确吻合，差 0）。

文本（解压后）:
  `03 0d 36 ff 01 <ボイス名> 00  01 <本文> 00`   ⇒ 一次点击一条消息
  `03 0d 37 ff 02 01 ff 01 <選択肢> 00`         ⇒ 一條选项（组头是 idx=00、组尾 idx=02）
  正文内 `\\n` = 框内换行（15,219 条全部含且仅含此一种转义）⇒ 合并；`\\n　` 连缩进一起去掉。
"""
import os
import re
import struct
import sys

MAGIC = b'DDSxSpt'


def decompress(src, outsize):
    out = bytearray()
    i = 0
    n = len(src)
    while len(out) < outsize and i < n:
        c = src[i]
        i += 1
        if c < 0x1d:
            ln = c + 1
            out += src[i:i + ln]
            i += ln
        elif c == 0x1d:
            ln = src[i] + 0x1e
            i += 1
            out += src[i:i + ln]
            i += ln
        elif c == 0x1e:
            ln = (src[i] << 8 | src[i + 1]) + 0x11e
            i += 2
            out += src[i:i + ln]
            i += ln
        elif c == 0x1f:
            ln = int.from_bytes(src[i:i + 4], 'big')
            i += 4
            out += src[i:i + ln]
            i += ln
        else:
            if c >= 0x80:
                dist = (((c & 0x1f) << 8) | src[i]) + 1
                i += 1
                ln = ((c >> 5) & 3) + 3
            elif c >= 0x60:
                dist = (((c & 0x1f) << 8) | src[i]) + 1
                i += 1
                L = src[i]
                i += 1
                if L == 0xfe:
                    L = (src[i] << 8 | src[i + 1]) + 0x102
                    i += 2
                elif L == 0xff:
                    L = int.from_bytes(src[i:i + 4], 'big')
                    i += 4
                else:
                    L += 4
                ln = L + 3
            elif c >= 0x40:
                ln = (c & 0x1f) + 7
                dist = src[i] + 1
                i += 1
            else:
                ln = (c & 3) + 3
                dist = ((c >> 2) & 7) + 1
            if dist > len(out):
                raise ValueError('match distance %d > produced %d' % (dist, len(out)))
            for _ in range(ln):
                out.append(out[-dist])
    return bytes(out[:outsize])


def parse_table(d):
    pos = 0x110
    ents = []
    while pos < 0xC60:
        if d[pos] == 0:      # 条目之间可能有 1 字节 0 填充
            pos += 1
            continue
        ln = d[pos]
        if ln < 6:
            break
        off = int.from_bytes(d[pos + 1:pos + 5], 'big')
        name = d[pos + 5:pos + ln].rstrip(b'\0').decode('latin1')
        if not name.startswith('sc'):
            break
        ents.append((off, name))
        pos += ln
    return ents


def read_record(d, off):
    cs, us = struct.unpack_from('<II', d, off)
    if cs == 0:
        # 未压缩：前 8 字节后紧跟 "DDSxSpt"
        start = d.find(MAGIC, off + 8, off + 32)
        if start < 0:
            return None
        return d[start + 8:start + 8 + us]
    body = d[off + 8:off + 8 + cs]
    return decompress(body, us)


def parse_text(stream):
    """-> [(kind, text)]，kind ∈ {'msg','opt'}，按流内顺序。"""
    out = []
    i = 0
    n = len(stream)
    while i < n - 5:
        if stream[i:i + 5] == b'\x03\x0d\x36\xff\x01':
            j = stream.find(b'\x00', i + 5)
            k = stream.find(b'\x00', j + 1) if j > 0 else -1
            if j > 0 and k > j:
                try:
                    t = stream[j + 2:k].decode('cp932')
                except UnicodeDecodeError:
                    t = ''
                if t:
                    out.append(('msg', t))
                i = k + 1
                continue
        if stream[i:i + 8] == b'\x03\x0d\x37\xff\x02\x01\xff\x01':
            j = stream.find(b'\x00', i + 8)
            if j > 0:
                try:
                    t = stream[i + 8:j].decode('cp932')
                except UnicodeDecodeError:
                    t = ''
                if t:
                    out.append(('opt', t))
                i = j + 1
                continue
        i += 1
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    dump = None
    for k, a in enumerate(sys.argv[3:]):
        if a == '--dump-raw' and k + 4 <= len(sys.argv) - 1:
            dump = sys.argv[4 + k]
    order = 'name'
    for a in sys.argv[3:]:
        if a.startswith('--order='):
            order = a.split('=', 1)[1]
    d = open(src, 'rb').read()
    if d[:4] != b'DDP1':
        sys.exit('不是 DDP1 容器：%r' % d[:4])
    ents = parse_table(d)
    if order == 'name':
        pat = re.compile(r'^sc(\d)(\d{3})(\d{3})([a-z])$')
        ents.sort(key=lambda e: pat.match(e[1]).groups() if pat.match(e[1]) else ('9', '999', '999', e[1]))
    lines = []
    n_raw = 0
    for off, name in ents:
        stream = read_record(d, off)
        if stream is None:
            continue
        n_raw += 1
        if dump:
            os.makedirs(dump, exist_ok=True)
            open(os.path.join(dump, name + '.bin'), 'wb').write(stream)
        for kind, t in parse_text(stream):
            lines.append(t.replace('\\n\u3000', '').replace('\\n', ''))

    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')
    print('records=%d decompressed=%d lines=%d chars=%d'
          % (len(ents), n_raw, len(lines), sum(len(x) for x in lines)), file=sys.stderr)


if __name__ == '__main__':
    main()
