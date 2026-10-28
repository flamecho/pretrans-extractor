#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""［PS2-JP］セイント ビースト ~螺旋の章~ —— SN.BIN 剧本提取

链路：ISO9660 → SN.BIN（CRI LSC 引擎，自研 LZSS）→ 解压 → 记录扫描 → 成行。

LZSS 参数（反汇编 SLPS_258.08 @0x123cd8 + MIPS 模拟对账确定）：
  [u32 out_size] 之后为位流；每读 1 字节 flag（0xff00|b），LSB 起 8 个 token。
  token bit=1 → 字面字节；bit=0 → 2 字节 [lo8][pk]
      off = lo8 | ((pk & 0xF0) << 4)   12bit 环形窗口绝对索引（窗口 4096）
      len = (pk & 0x0F) + 3
  窗口写指针初值 0xFEE，窗口预先清零。

脚本记录（SN.BIN 解压后）：
  正文   45 FF FF <u16 行号> <SJIS> 00
  名札   47 <u16 名札ID> <SJIS> 00        （丢弃：独立名札命令）
  选项   31 80 80 <u32 n> 之后 n 条 01 00 <u16 idx> <u32 id> <SJIS> 00
  章题   55 <SJIS> 00                     （扉文／章題カード）
  正文后固定串 4A FF FF / 6A FF FF FF FF / 49 FF FF FF FF ⇒ 一条正文＝一框＝一次点击。
  0x81 0x97（＠）＝可改名主人公的名字槽标记，成行前剥除（保留默认名 シェス／シェラ）。
"""
import struct, sys

WIN = 0x1000
FIRST_STORY = 0xF6B          # 0x0000–0x0F6A ＝ 表／调试菜单（本編スタート・デバッグ仕様でスタート…）
TITLE_HEAD = ('第', 'エピローグ', 'プロローグ', 'オープニング', 'ノーマルエンド', 'バッドエンド')


def decompress(src):
    size = struct.unpack_from('<I', src, 0)[0]
    n = len(src)
    i = 4
    win = bytearray(WIN)
    t2 = 0xFEE
    t3 = 0
    out = bytearray()
    while len(out) < size and i < n:
        t3 >>= 1
        if (t3 & 0x100) == 0:
            t3 = 0xFF00 | src[i]
            i += 1
            bit = t3 & 1
        else:
            bit = t3 & 1
        if bit:
            b = src[i]
            i += 1
            win[t2] = b
            t2 = (t2 + 1) & (WIN - 1)
            out.append(b)
        else:
            if i + 1 >= n:
                break
            lo = src[i]
            pk = src[i + 1]
            i += 2
            base = (lo | ((pk & 0xF0) << 4)) & 0xFFF
            ln = (pk & 0x0F) + 3
            for _ in range(ln):
                b = win[base]
                base = (base + 1) & 0xFFF
                win[t2] = b
                t2 = (t2 + 1) & (WIN - 1)
                out.append(b)
                if len(out) >= size:
                    break
    return bytes(out)


def _text(data, start):
    e = data.find(b'\x00', start)
    if e < 0 or e - start > 400:
        return None, start
    try:
        return data[start:e].decode('cp932'), e
    except UnicodeDecodeError:
        return None, start


def scan(data):
    n = len(data)
    items = []

    # ① 正文
    i = 0
    while True:
        p = data.find(b'\x45\xff\xff', i)
        if p < 0:
            break
        mid = struct.unpack_from('<H', data, p + 3)[0]
        t, e = _text(data, p + 5)
        if t:
            items.append((p + 5, 'msg', t, mid))
        i = p + 3

    # ② 选项
    i = 0
    while True:
        p = data.find(b'\x31\x80\x80', i)
        if p < 0:
            break
        i = p + 3
        if p + 9 > n:
            continue
        cnt = struct.unpack_from('<I', data, p + 3)[0]
        if not (1 <= cnt <= 8):
            continue
        q = p + 7
        ents = []
        for _ in range(cnt):
            if data[q:q + 2] != b'\x01\x00':
                ents = []
                break
            t, e = _text(data, q + 8)
            if not t:
                ents = []
                break
            ents.append((q + 8, t))
            q = e + 1
        for off, t in ents:
            items.append((off, 'choice', t, 0))

    # ③ 章题（两种锚点取并集：前置 01 00 55，或文本以章题词开头）
    seen = set()
    i = 0
    while True:
        p = data.find(b'\x01\x00\x55', i)
        if p < 0:
            break
        i = p + 3
        t, e = _text(data, p + 3)
        if t and p + 3 not in seen:
            seen.add(p + 3)
            items.append((p + 3, 'title', t, 0))
    i = 0
    while True:
        p = data.find(b'\x55', i)
        if p < 0:
            break
        i = p + 1
        t, e = _text(data, p + 1)
        if t and t.startswith(TITLE_HEAD) and p + 1 not in seen:
            seen.add(p + 1)
            items.append((p + 1, 'title', t, 0))

    items = [x for x in items if x[0] >= FIRST_STORY]
    items.sort()
    return items


def clean(t):
    return t.replace('\uFF20', '').strip()      # 0x8197 ＠：主人公可改名槽标记


def build(path_in, path_out):
    data = decompress(open(path_in, 'rb').read())
    items = scan(data)
    lines = []
    prev = None
    for off, kind, t, mid in items:
        t = clean(t)
        if not t:
            continue
        # 同一消息号(行号)＋同文的紧邻两条＝同一点击的立绘/表情分支 ⇒ 取一
        if kind == 'msg' and prev == (mid, t):
            continue
        if kind == 'msg':
            prev = (mid, t)
        else:
            prev = None
        lines.append(t)
    with open(path_out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    return len(lines), len(data), items


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'SN.BIN'
    dst = sys.argv[2] if len(sys.argv) > 2 else 'out.txt'
    n, dl, items = build(src, dst)
    print('lines', n, 'decomp', dl)
