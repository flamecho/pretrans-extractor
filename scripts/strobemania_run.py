#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""スト☆マニ ～Strobe☆Mania～（PSP / ULJM-05961）—— 全文本提取。

容器链路
  ISO9660 -> PSP_GAME/USRDIR/pack.pck
    pack.pck = **1534 个 gzip member**，逐个 0x800 对齐，空隙填 0x30（'0'）
      ⇒ 需「顺序走 member」（不能按连续 gzip 拼；trailer 的 ISIZE 被改成 ASCII '0000'）
    解出条目头：`OBJ\\0`(248 = 剧本) / `MIG.`(746 = 图像) / `@UTF`(234 = 表) / `PKG `(35)
  剧本条目（OBJ）：
    +0x00 "OBJ\0"  +0x04 u32 条目全长  +0x08 u32 哈希  +0x0C u32 序号
    +0x13 起为记录流：`<cp932 文本>` `0x0A` `15 01 01 00` `...记录参数...` `01 <u16 下一文本字节数> 00` `<下一文本>`
    ⇒ 文本 = 到 `0x0A 15 01 01 00` 为止的 cp932 串；`15 01 01 00` = 文本（= 一次点击）op
    ⚠ 部分记录尾部带 `58 xx 00`/`91 00 ff ff` 等演出参数，靠「长度字段自校验」跳记录（不用固定步长）

编码：**明文 cp932**（无自建字符集；USRDIR/font.pgf = 系统字体）

用法：python scripts/strobemania_run.py <pack.pck> <out.txt>
"""
import os, sys, struct, re, zlib


def members(raw):
    """顺序遍历 gzip member（0x800 对齐 + 0x30 填充）。"""
    p, out = 0, []
    while p + 3 <= len(raw):
        if raw[p:p + 3] != b'\x1f\x8b\x08':
            np = (p // 0x800 + 1) * 0x800
            if np <= p:
                break
            p = np
            continue
        d = zlib.decompressobj(-15)
        try:
            b = d.decompress(raw[p + 10:])
            b += d.flush()
        except Exception:
            break
        out.append(b)
        used = len(raw) - p - 10 - len(d.unused_data)
        p = (p + 10 + used + 0x7ff) // 0x800 * 0x800
    return out


def dec(b):
    """cp932 解码；框内软换行 0x0A 直接合并（= 同一文本框）。"""
    try:
        s = b.decode('cp932')
    except Exception:
        return None
    if any(ord(c) < 0x20 and c != '\n' for c in s):
        return None
    return s.replace('\n', '')


PROTAG = 'セリ'      # 天野 セリ（vndb v8576 / Name can be changed）
SURNAME = '天野'
# 行内插入宏（实测）：`70 39`＝姓「天野」 / `70 3a`＝名「セリ」（相邻＝全名；
#   证：`[70 3a]ちゃん、お～はよう！` / `[70 39]さん。如月先輩と何話してたの？`）
NAME_OPS = ((b'\x70\x39', SURNAME), (b'\x70\x3a', PROTAG))
# 其余 `70 02`..`70 09` = 同一「主角名」宏的**逐角色称呼变体**（本人名表在 eboot，未能取值）：
#   其后续文本必以 「、/。！」 起（= 名字被吃掉留下的接续符）⇒ 按名札口径**丢弃该称呼**并剥掉紧随的「、」。
NAME_DROP = tuple(b'\x70' + bytes([c]) for c in (0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09))


def parse_obj(d):
    """返回该 OBJ 的文本块（= 一次点击 = 一行）。

    记录流：`<记录参数><01><u16 文本字节数><00><cp932 文本>` `0x0A` `15 01 01 00` ...
    ⇒ 先按 `0x0A 15 01 01 00` 切「框」，框内可有多个文本段（中间夹行内命令，如 `70 3a`＝主角名）
      ⇒ 每段用「01 + u16 L + 00 + L 字节」取出，段间命令里出现 `70 3a` 则插入主角名。
    """
    blocks = []
    for part in d[0x10:].split(b'\x0a\x15\x01\x01\x00'):
        L = len(part)
        if L < 5:
            continue
        segs = []
        pos = 0
        while pos < L - 3:
            hit = None
            for j in range(pos, L - 3):
                if part[j] != 0x01:
                    continue
                ln = struct.unpack_from('<H', part, j + 1)[0]
                if not (2 <= ln <= 3000):
                    continue
                # 长度含行尾 0x0A，而切分时已把它当分隔符吃掉 ⇒ 允许差 1
                if j + 3 + ln == L + 1:
                    ln -= 1
                elif j + 3 + ln > L:
                    continue
                raw = part[j + 3:j + 3 + ln].strip(b'\x00')
                if raw.endswith(b'\x0a'):
                    raw = raw[:-1]
                s = dec(raw)
                if s is None:
                    continue
                if not any('\u3041' <= c <= '\u3096' or '\u4e00' <= c <= '\u9fff'
                           or '\u30a1' <= c <= '\u30fa' for c in s):
                    # 纯括号/标点的短段：仅当紧跟行内插入宏（名字）时保留，如 `（` + [名]
                    if not (len(s) <= 2 and part[j + 3 + ln:j + 4 + ln] == b'\x70'):
                        continue
                hit = (j, ln, s)
                break
            if hit is None:
                break
            j, ln, s = hit
            seg = part[pos:j]
            hits = []
            for op, val in NAME_OPS:
                k = seg.find(op)
                if k >= 0:
                    hits.append((k, val))
            if hits:
                prefix = ''.join(v for _, v in sorted(hits))
                s = prefix + s
            elif any(op in seg for op in NAME_DROP):
                s = s.lstrip('\u3001\u3002')
            segs.append(s)
            pos = j + 3 + ln
        s = ''.join(x.lstrip('\u3000') if k else x for k, x in enumerate(segs)).strip()
        if s:
            blocks.append(s)
    return blocks


def main():
    src, dst = sys.argv[1], sys.argv[2]
    raw = open(src, 'rb').read()
    items = members(raw)
    lines, nobj = [], 0
    for b in items:
        if b[:4] == b'OBJ\x00':
            nobj += 1
            lines.extend(parse_obj(b))
    out = []
    for s in lines:
        if out and out[-1] == s:
            continue
        out.append(s)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('members', len(items), 'obj', nobj, 'lines', len(out), '->', dst)


if __name__ == '__main__':
    main()
