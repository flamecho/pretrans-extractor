#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""WillPlus / RIO.ARC（WSC 脚本）文本提取。

格式（全部由本项目实测确认，见 解析报告 §三）：
  容器：u32 ngroups
        ngroups × { char tag[4]; u32 count; u32 table_off }
        table_off 处：count × { char name[13]; u32 size; u32 offset }
  条目：整段 **每字节循环右移 2 位** 即为明文（无压缩、等长）：
        plain = ((b >> 2) | ((b & 3) << 6)) & 0xFF
  文本：`0F` 起、`00` 止；若 0F 后紧跟第二个 0F ⇒ 带名字子块（名字 NUL 结尾，随后是正文）
        `\\n`(5C 6E) = 框内软换行 ⇒ 合并；`%K`=クリック待ち、`%P`=ページ送り ⇒ 剥离
  选项：`02 03 00` 起，每项 `<u16 idx> 00 <文本> 00`，项间夹 `01 <u16> 03 07 <label> 00`

用法：
  python scripts/will_rio_arc.py --arc RIO.ARC --raw _work_vs/raw --out 成品.txt
"""
import argparse
import io
import os
import re
import struct
import sys

TAG = re.compile(rb'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
JP = re.compile(rb'[\x81-\x9f\xe0-\xfc]')


def ror2(b):
    return bytes(((x >> 2) | ((x & 3) << 6)) & 0xFF for x in b)


def entries(arc):
    """返回 [(name, size, offset)]，按文件顺序。"""
    d = io.open(arc, 'rb').read()
    if len(d) < 16:
        raise SystemExit('%s: 太短' % arc)
    ng = struct.unpack_from('<I', d, 0)[0]
    if not (1 <= ng <= 64):
        raise SystemExit('%s: 组数异常 %d' % (arc, ng))
    out = []
    for g in range(ng):
        tag, cnt, toff = struct.unpack_from('<4sII', d, 4 + g * 12)
        for k in range(cnt):
            p = toff + k * 21
            if p + 21 > len(d):
                raise SystemExit('表越界')
            nm = d[p:p + 13].rstrip(b'\x00').decode('latin1')
            sz, off = struct.unpack_from('<II', d, p + 13)
            out.append((nm, sz, off, tag.rstrip(b'\x00').decode('latin1')))
    return out, d


CTRL = re.compile(rb'%[A-Za-z]+[0-9A-Fa-f]*')


def clean_text(b):
    """正文清洗：剥 `%` 控制码（%K/%P/%CF00F/%CFFFF/%XS30/%XE/%LC…）、折 \\n 软换行。
    返回 None 表示这段不是可显示的正文（二进制误命中）。"""
    seg = CTRL.sub(b'', b)
    if any(x < 0x20 or x == 0x7F for x in seg):
        return None                      # cp932 正文不含控制字节 ⇒ 是二进制
    try:
        t = seg.decode('cp932')
    except UnicodeDecodeError:
        return None
    t = t.replace('\\n', '').replace('\r', '').replace('\n', '')
    t = t.strip('\u3000 ')
    if not t:
        return None
    jp = sum(1 for ch in t
             if 0x3040 <= ord(ch) <= 0x30FF or 0x4E00 <= ord(ch) <= 0x9FFF
             or 0xFF01 <= ord(ch) <= 0xFF60 or ch == '\u3000')
    if jp == 0:
        return None
    return t


def parse_script(b):
    """从一个脚本明文里取 [(kind, text)]；kind='line' 正文、'opt' 选项。"""
    rows = []
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if c == 0x0F:
            k = i + 1
            if k < n and b[k] == 0x0F:      # 名字子块：跳过到 NUL
                ne = b.find(b'\x00', k + 1)
                if ne < 0:
                    break
                k = ne + 1
            e = b.find(b'\x00', k)
            if e < 0:
                break
            t = clean_text(b[k:e])
            if t:
                rows.append(('line', t))
            i = e + 1
            continue
        if b[i:i + 3] == b'\x02\x03\x00':   # 选项组
            p = i + 3
            while p + 3 <= n:
                if b[p:p + 1] == b'\xff':
                    break
                if b[p:p + 1] == b'\x01':    # 选项间的跳转描述，跳过
                    q = b.find(b'\x00', p)
                    if q < 0:
                        break
                    p = q + 1
                    continue
                # <u16 idx> 00 <text> 00
                e = b.find(b'\x00', p)
                if e < 0:
                    break
                hdr = b[p:e]
                if len(hdr) > 2:
                    # 直接是文本（无 u16 头）
                    seg, p = hdr, e + 1
                else:
                    s2 = e + 1
                    e2 = b.find(b'\x00', s2)
                    if e2 < 0:
                        break
                    seg, p = b[s2:e2], e2 + 1
                t = clean_text(seg)
                if t:
                    rows.append(('opt', t))
            i = p
            continue
        i += 1
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arc', required=True)
    ap.add_argument('--raw', help='把每个脚本解码后存到此目录（.txt）')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    ents, d = entries(a.arc)
    if a.raw:
        os.makedirs(a.raw, exist_ok=True)
    rows, stat = [], []
    for nm, sz, off, tag in ents:
        dec = ror2(d[off:off + sz])
        if a.raw:
            with io.open(os.path.join(a.raw, nm + '.bin'), 'wb') as f:
                f.write(dec)
        got = parse_script(dec)
        stat.append((nm, tag, sz, len(got)))
        rows.extend(t for _, t in got)

    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as w:
        for t in rows:
            w.write(t + '\n')
    for nm, tag, sz, k in stat:
        print('%-12s %-4s %7d  %5d 行' % (nm, tag, sz, k), file=sys.stderr)
    print('总计 %d 行' % len(rows), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
