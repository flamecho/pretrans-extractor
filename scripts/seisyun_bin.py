#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seisyun_bin.py —— 《青春はじめました！》(PSP) cwin 脚本容器解析。

格式（实测：整文件顺序解析到 EOF，residual=0）:
  node  = tag(4) + nchild(u32) + code(u32) + nchild*field + u32(pad)
  field = tag(4) + type(u32) + payload
     type 1 = string : len(u32) + bytes，尾部补齐到 4 字节
     type 2 = u32
     type 3 = u32 (0/1)
  文件头: 'cwin00.1' + u32 + u32 + 'CMDS'(1) + 'SrcT'(type 2) + u32 + 节点流
  tag 右补 \0/空格 到 4 字节。

节点语义（按执行序）:
  DILG = 名札（Text 字段，空=无）
  DOC  = 一次点击的正文（Text 字段，\n 为框内软换行）
  WAIT = クリック待ち（Time/Wind/Skip/ClkC）
  EFCT = 特效（Numb/Time/Brea/Wind）  Brea/Wind 决定是否清框
  VOIC = 语音；BG/SCAL/COEF/MSC/SE/STB/MTRX/FACE/JMPS = 演出指令
"""
import struct
import sys

U32 = struct.Struct('<I')


def u32(b, o):
    return U32.unpack_from(b, o)[0]


def ok_tag(t):
    s = t.rstrip(b'\0 ')
    return bool(s) and all(33 <= c < 127 for c in s)


def parse_node(b, p):
    tag = b[p:p + 4].rstrip(b'\0 ').decode('latin-1')
    n = u32(b, p + 4)
    code = u32(b, p + 8)
    p += 12
    fs = []
    for _ in range(n):
        ft = b[p:p + 4].rstrip(b'\0 ').decode('latin-1')
        typ = u32(b, p + 4)
        p += 8
        if typ == 1:
            ln = u32(b, p)
            p += 4
            v = b[p:p + ln]
            p += ln
            p = (p + 3) & ~3
        elif typ in (2, 3):
            v = u32(b, p)
            p += 4
        else:
            raise ValueError('field type %d at %#x (tag %r)' % (typ, p - 8, ft))
        fs.append((ft, v))
    return tag, code, fs, p + 4


def events(path):
    b = open(path, 'rb').read()
    if b[:8] != b'cwin00.1':
        raise ValueError('bad magic %r' % b[:8])
    i = b.find(b'SrcT', 8, 64)
    if i < 0:
        raise ValueError('no SrcT')
    p = i + 16      # 'SrcT' + type + code + count 之后即节点流
    out = []
    while p < len(b):
        if not ok_tag(b[p:p + 4]):
            raise ValueError('bad tag at %#x' % p)
        tag, code, fs, p = parse_node(b, p)
        out.append((tag, code, fs))
    return out


def field(fs, name, default=None):
    for t, v in fs:
        if t == name:
            return v
    return default


if __name__ == '__main__':
    cmd = sys.argv[1]
    ev = events(sys.argv[2])
    if cmd == 'tree':
        lim = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        print('nodes=%d' % len(ev))
        for tag, code, fs in ev[:lim]:
            print('  %-5s %#06x %s' % (tag, code, [(t, v) for t, v in fs]))
    elif cmd == 'doc':
        for tag, code, fs in ev:
            if tag in ('DILG', 'DOC'):
                v = field(fs, 'Text') or b''
                print('%-5s %r' % (tag, v))
