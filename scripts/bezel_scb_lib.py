#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]恋してしまった星の王子 ～誓願院編～ 文本提取（Bezel Engine / SCNE / scb_）链路与判据。

★ 容器（L0，实测结构，2026-11-11）
  romfs/Archive/script.nxonnx32.bea
    0x00 'SCNE' 头；0x10 'SCNE' 大小端标记；0x18 段表起点；0x26e80 '_STR' 名表段
    0x163e0 起 ASST0 资源表，1422 条 × 48 B：
        +0x00 'ASST0'  +0x08 u64 recsize(=0x30)  +0x10 u16 a(=2) u16 b(=2)
        +0x14 u32 csize   +0x18 u32 usize   +0x1C u32 pad
        +0x20 u64 data_off（文件内绝对偏移，该处是一个独立 zstd 帧）
        +0x28 u64 name_off（指向 _STR 段，[u16 len][UTF-8]，无 NUL）
    ⇒ 每个成员各自是一条独立 zstd 流，不是整包压一层。

★ .scb 脚本（解压后）
  0x00 'scb_' + 10×u32 头：magic, 0, opS, opLen, tblOff, tblLen, strOff, strLen, poolOff, poolLen
    且 opS+opLen == tblOff（自证）; tblOff+tblLen == strOff; strOff+strLen == poolOff; poolOff+poolLen == 文件长
    strOff 处：u32 count + count×u32 偏移（相对 poolOff），每串 NUL 结尾 UTF-8
  字节码流：每条 [u16 tag][u16 wordcount][(wc-1)×u32 参数]，参数即字符串池索引

★ 成行判据（L0，字节码级）
  0x05  开一个文本框（2 参数：立绘 ID / 表情 ID，均为资源名，实测 0 条含假名）
  0x0b  名札串索引（每框最多 1 条）
  0x0c  正文串索引（每框恰 1 条）
  0x11 / 0x12  收框
  0x13  选项表：参数按 (选项文本, 分支标签, 共用标签) 三元组重复
  框内 '\n' = 排版软换行 ⇒ 合并进同一行（不拆）
  一框 = 一次点击 = 一行

★ 宏：#NAME[1] = 主角姓、#NAME[2] = 主角名（玩家可改名，游戏内无官方默认值）
       ⇒ 保留为【姓】【名】占位（用户口径：不留宏、不猜填）
"""
import struct
import zstandard

IP = None


def asst_entries(raw):
    """SCNE 明文资源表：0x163e0 起 1422×48B。返回 [(name, csize, usize, data_off)]"""
    assert raw[:4] == b'SCNE', raw[:4]
    out = []
    base = 0x163e0
    for k in range(1422):
        o = base + k * 48
        assert raw[o:o + 5] == b'ASST0', 'ASST0 @%x' % o
        csize, usize = struct.unpack_from('<II', raw, o + 20)
        doff = struct.unpack_from('<Q', raw, o + 32)[0]
        noff = struct.unpack_from('<Q', raw, o + 40)[0]
        L = struct.unpack_from('<H', raw, noff)[0]
        out.append((raw[noff + 2:noff + 2 + L].decode('utf-8'), csize, usize, doff))
    return out


def member(raw, csize, usize, doff):
    return zstandard.ZstdDecompressor().decompress(raw[doff:doff + csize], max_output_size=usize)


def parse_scb(d):
    h = struct.unpack_from('<10I', d, 0)
    assert h[0] == 0x5f626373, 'scb magic'
    opS, opLen, tOff, tLen, sOff, sLen, pOff, pLen = h[2:10]
    assert opS + opLen == tOff, ('oplen', opS, opLen, tOff)
    assert tOff + tLen == sOff, ('tbl', tOff, tLen, sOff)
    assert sOff + sLen == pOff, ('str', sOff, sLen, pOff)
    assert pOff + pLen == len(d), ('pool', pOff, pLen, len(d))
    cnt = struct.unpack_from('<I', d, sOff)[0]
    assert sLen == 4 + cnt * 4, ('strcnt', sLen, cnt)
    offs = struct.unpack_from('<%dI' % cnt, d, sOff + 4)
    strs = []
    for o in offs:
        e = d.index(b'\x00', pOff + o)
        strs.append(d[pOff + o:e].decode('utf-8', 'replace'))
    o, ops = opS, []
    while o < tOff:
        tag, wc = struct.unpack_from('<HH', d, o)
        assert 1 <= wc <= 64, ('wc', o, tag, wc)
        ops.append((o, tag, struct.unpack_from('<%dI' % (wc - 1), d, o + 4)))
        o += wc * 4
    assert o == tOff, 'opwalk'
    return ops, strs


# 主角默认名：取自本作自带 Archive/static~localize.bin.nxonnx32.bea 的
# NAMEENTRY_LASTNAME / NAMEENTRY_FIRSTNAME（姓名输入框预填值，紧邻
# 「苗字を入力してください」「名前を入力してください」两条提示，5/5 交叉验证）
#   #NAME[1] = 姓 = 立花    #NAME[2] = 名 = なつみ
# 自证：`#NAME[1]#NAME[2]` 连用处（自我介绍）读作「立花なつみです」完全通顺。
MACRO = {'#NAME[1]': '立花', '#NAME[2]': 'なつみ'}


def clean(s):
    for k, v in MACRO.items():
        s = s.replace(k, v)
    return s.replace('\n', '').strip('\u3000 \t')
