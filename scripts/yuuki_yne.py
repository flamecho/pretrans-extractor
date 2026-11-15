#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yuuki! Novel (ゆうき！ノベル) 引擎 —— `.yne` WorkFile 解析（脚本读取）。

文件头（解密后）：
  0x00  `\\x13`                       1 B
  0x01  "YuukiNovel WorkFile" 空格填充到 0x20
  0x20  u32 A / 0x24 u32 B / 0x28 u32 C   （alto: 2336 / 256000 / 307200 → 窗口相关尺寸）
  0x2C  u8 n + cp932 场景名（alto: プロローグ）
  其后  资源表（名字 + 图形文件 + 定位串），含角色名（博士/アルト/アクア/ヴィッツ/シエル）
  之后  脚本正文：CRLF 分隔的 `.Command` 行 + 裸文本行

正文判据（L0，反汇编 0x48D758 `cmp byte ptr [eax],0x2e` 判 `.` 命令）：
  行首 `.`      = 命令
  行尾 `@`      = 本框待点击（等价于「一次点击」），是唯一分页符
  `.WindowSet "名"` = 开名字窗；`.WindowHide` = 关窗
  其余          = 正文文本

★ 二进制块：正文流里夹着「分支记录」，以单字节 < 0x09 开头，结构为
      [u8 tag][u8 sub]  ...  [u32 1][u32 len][标签][u32 a][u32 b][u32 c][紧随的脚本行]
  tag/sub 三型：
      00 01  选项组：每项 = [u32 len][cp932 显示文本][u32 len][cp932 跳转标签]，项间以 0x00 填充 + 0x01 分隔
      01 01  分支入口：只带进入标签，无显示文本
      02 01  结局/分支入口：只带进入标签（常全 0）
  只有 `00 01` 的显示文本会渲染到画面（＝选项），其余仅为跳转标签，不进成品。
"""
import struct

MAGIC = b'YuukiNovel WorkFile'
CMDS = (b'.WindowSet', b'.WindowHide', b'.CharSet', b'.CharDelete',
        b'.CharClear', b'.GraphLoad', b'.GraphFill', b'.Wait')


def body_start(b):
    """正文起点：全部已知命令 token 的最早出现位置。"""
    pos = [b.find(c) for c in CMDS]
    pos = [p for p in pos if p >= 0]
    return min(pos) if pos else -1


def header(b):
    """返回 dict(magic_ok, fields, title)。结构解析：魔数 + 空格填充 + 3×u32 + u8 长度 + cp932 场景名。"""
    i = b.find(MAGIC)
    res = {'magic_ok': i >= 0, 'fields': [], 'title': ''}
    if i < 0:
        return res
    p = i + len(MAGIC)
    n = len(b)
    while p < n and b[p] == 0x20:          # 空格填充
        p += 1
    if p + 12 > n:
        return res
    res['fields'] = list(struct.unpack_from('<III', b, p))
    p += 12
    if p + 1 > n:
        return res
    ln = b[p]
    p += 1
    if 0 < ln <= 64 and p + ln <= n:
        try:
            res['title'] = b[p:p + ln].decode('cp932')
        except UnicodeDecodeError:
            pass
    return res


def strip_click(text):
    """去掉行尾点击符 `@`。

    ★ 必须在**解码后**按字符判断：cp932 的尾字节也可能是 0x40
    （`81 40` ＝ 全角空格 U+3000），按字节剥会把双字节字劈开。
    解码成 str 后结尾的 '@' 才是真的 ASCII 点击符。
    """
    return text[:-1] if text.endswith('@') else text


def split_tail(item):
    """把「二进制块 + 紧随脚本行」拆开。返回 (block, tail)。

    定位：最后一个 `01 00 00 00` 起，[u32 len][标签][u32 a][u32 b][u32 c] 之后即脚本行。
    交叉验证：该后缀必须能被 cp932 严格解码、非空、且以 `.` 开头或 `@` 结尾、无控制字节。
    """
    q = item.rfind(b'\x01\x00\x00\x00')
    if q < 0:
        return item, b''
    p = q + 4
    if p + 4 > len(item):
        return item, b''
    n = struct.unpack_from('<I', item, p)[0]
    p += 4 + n + 12
    if n == 0 or n > 64 or p > len(item):
        return item, b''
    tail = item[p:]
    if not tail or any(c < 0x20 for c in tail):
        return item, b''
    try:
        tail.decode('cp932')
    except UnicodeDecodeError:
        return item, b''
    if not (tail.startswith(b'.') or tail.endswith(b'@')):
        return item, b''
    return item[:p], tail


def parse_choices(blk):
    """解析 `00 01` 选项组 → [(显示文本, 跳转标签)]。"""
    out = []
    p = 2
    while p + 4 <= len(blk):
        n = struct.unpack_from('<I', blk, p)[0]
        if n == 0 or n > 4096 or p + 4 + n > len(blk):
            break
        try:
            disp = blk[p + 4:p + 4 + n].decode('cp932')
        except UnicodeDecodeError:
            break
        p += 4 + n
        if p + 4 > len(blk):
            break
        n2 = struct.unpack_from('<I', blk, p)[0]
        if n2 > 4096 or p + 4 + n2 > len(blk):
            break
        lab = blk[p + 4:p + 4 + n2].decode('cp932', 'replace')
        p += 4 + n2
        out.append((disp, lab))
        while p < len(blk) and blk[p] == 0:      # 填充
            p += 1
        if p < len(blk) and blk[p] == 1:         # 分隔符
            p += 1
    return out


def iter_script(b):
    """按正文顺序产出事件：

        ('line',  文本, 说话人)        裸文本行（已去行尾 `@`）
        ('choice', [(显示, 标签)], 序号) 选项组
        ('cmd',   命令名, 参数串)      其余命令（供报告统计）
    """
    st = body_start(b)
    if st < 0:
        return
    speaker = None
    for item in b[st:].split(b'\r\n'):
        if not item:
            continue
        if item[0] < 0x09:
            blk, tail = split_tail(item)
            if blk[:2] == b'\x00\x01':
                opts = parse_choices(blk)
                if opts:
                    yield ('choice', opts, 0)
            if not tail:
                continue
            item = tail
        if item.startswith(b'.'):
            parts = item.split(b' ', 1)
            name = parts[0].decode('ascii', 'replace')
            arg = parts[1].decode('cp932', 'replace') if len(parts) > 1 else ''
            if name == '.WindowSet':
                speaker = arg.strip('"')
                continue
            if name == '.WindowHide':
                speaker = None
            yield ('cmd', name, arg)
            continue
        if not item.strip(b' \t'):
            continue
        text = strip_click(item.decode('cp932', 'replace'))
        if not text.strip():
            continue
        yield ('line', text, speaker)
