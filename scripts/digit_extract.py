#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[NS-JP]数乱digit For Nintendo Switch —— SCD 字节码文本提取

引擎链路：RomFS/Data/SCD/*.lzs -> LZS 解压 -> "SCD 容器"
  容器头 0x00: u32 cnt / u32 bcOff / u32 bcSize / u32 pad
  0x10 起 cnt × 64B 条目：char name[48] + u32 a + u32 off + u32 size + u32 idx
  [bcOff, bcOff+bcSize) 为线性字节码区

字节码指令：u16 op + u16 len(含 4B 头) + payload
  0x0010 / 0x0011 = 消息（唯一含文本的两条指令）
    实测：0x0011 共 378 条，**每一条**都被紧随其后的 0x0010 同文复述
    （label 亦成对：0x11 "004_01_014" / 0x10 "004_01E014"）⇒ 0x11 只登记语音·口型，
    不承担显示；成行只取 0x10，避免同句两行。
    payload:
      0x00 u32  entry id
      0x04 u16  id
      0x06 u16  p1  （角色/说话人槽；0xfffe/0xffff 见下）
      0x08 u16  p2
      0x0a u16  label_len   （语音/口型标签长度；无名时 2 = "-1"）
      0x0c char label[label_len]   e.g. "104_10_036" 或 "-1"
           u16  name_len          （名札长度，含结尾 NUL；0 = 无名札）
           char name[name_len]
           u16  text_len
           char text[text_len]    （UTF-8）
  p1 = 0xffff -> 地の文（无名札）；0xfffe -> 主角 零崎&；其它 = 说话人槽 id

文本内标记：
  '\\'      = 同框软换行（后接 U+3000 为缩进）—— 成行时合并、丢弃
  '#...#'   = 着重号（圏点）富文本标记 —— 成行前剥净
  '&'       = 主角名插入槽（名札 "零崎&" 可证 & = 名 "紘可"），inline 替换

取舍：
  * EV8xxxxx 共 86 个文件与正篇逐行 100% 重合（章回顾 / 章Index 重播载体）-> 整包剔除
  * 选项：全部为图片式 UI（Data/UI/CHAPTERCHOICE.lzs 仅含 DDS），脚本内无可渲染选项文本
  * 用語辞典：本作无该功能（UI 仅 CHAPTERCHOICE/EXTRA/GALLERY*/NAMEENTRY/OPTION/SAVELOAD）
"""
import os
import struct
import sys
import glob

SCD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_work_digit', 'scd')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '提取结果',
                   '[NS-JP]数乱digit For Nintendo Switch.txt')

HEROINE_GIVEN = '紘可'   # vndb / ymgal：零崎 紘可（Reisaki Hiroka）；名札 "零崎&"


def read_container(path):
    d = open(path, 'rb').read()
    cnt, bc_off, bc_size, _pad = struct.unpack_from('<4I', d, 0)
    if not (0 < bc_off <= len(d) and bc_off + bc_size <= len(d)):
        raise ValueError('bad container: %s' % path)
    return d[bc_off:bc_off + bc_size]


def walk(bc):
    off = 0
    n = len(bc)
    while off + 4 <= n:
        op, ln = struct.unpack_from('<HH', bc, off)
        if ln < 4 or off + ln > n:
            break
        yield op, bc[off + 4:off + ln]
        off += ln


def parse_msg(pl):
    """-> (p1, name_bytes, text_bytes) or None"""
    if len(pl) < 12:
        return None
    p1 = struct.unpack_from('<H', pl, 0x06)[0]
    lab_len = struct.unpack_from('<H', pl, 0x0a)[0]
    pos = 0x0c + lab_len
    if pos + 2 > len(pl):
        return None
    name_len = struct.unpack_from('<H', pl, pos)[0]
    pos += 2
    if pos + name_len + 2 > len(pl):
        return None
    name = pl[pos:pos + name_len]
    pos += name_len
    text_len = struct.unpack_from('<H', pl, pos)[0]
    pos += 2
    if pos + text_len > len(pl):
        return None
    return p1, name, pl[pos:pos + text_len]


def clean(text):
    t = text.decode('utf-8')
    t = t.rstrip('\x00')
    t = t.replace('#', '')          # 着重号标记
    t = t.replace('&', HEROINE_GIVEN)  # 主角名槽
    t = t.replace('\\\u3000', '')   # 软换行 + 缩进
    t = t.replace('\\', '')         # 软换行
    return t.strip()


def main():
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(SCD_DIR, '*')))
    files = [f for f in files if not f.startswith('EV8')]
    lines = []
    stat = {'files': 0, 'msg': 0, 'empty': 0}
    for f in files:
        bc = read_container(os.path.join(SCD_DIR, f))
        stat['files'] += 1
        for op, pl in walk(bc):
            if op != 0x10:          # 0x11 = 语音/口型登记，正文由其后的 0x10 显示
                continue
            r = parse_msg(pl)
            if r is None:
                continue
            stat['msg'] += 1
            _p1, _name, tb = r
            t = clean(tb)
            if not t:
                stat['empty'] += 1
                continue
            lines.append(t)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines))
        fh.write('\n')
    print('files=%d msg=%d empty=%d lines=%d' % (stat['files'], stat['msg'], stat['empty'], len(lines)))
    print('bytes=%d' % os.path.getsize(OUT))


if __name__ == '__main__':
    sys.exit(main())
