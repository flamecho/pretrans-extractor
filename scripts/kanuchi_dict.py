#!/usr/bin/env python3
"""カヌチ 二つの翼 用語辞典（ライブラリ）提取
DICT/Lib_*.bin:
  条目 = [u16 idx][u8 見出し語長][見出し語 cp932][3B][0x7F][本文...]
  条目间以 ff 00 填充分隔；本文按 128 字节定长块存储，每块第 128 字节为填充（跳过）
输出: 一行一条  【見出し語】解説文
"""
import re, sys

MACRO = {'&': 'アキ', '%': 'ミヤズ', '@': 'カヤナ', '$': 'アキ'}


def unpad(body):
    out = bytearray()
    i = 0
    while i < len(body):
        if i >= 127 and (i - 127) % 128 == 0:
            i += 1
            continue
        out.append(body[i])
        i += 1
    return bytes(out)


def parse(path):
    b = open(path, 'rb').read()
    out = []
    for chunk in re.split(rb'(?:\xff\x00)+', b):
        if not chunk:
            continue
        term = body = None
        for k in range(0, 7):
            if k >= len(chunk):
                break
            L = chunk[k]
            if not (2 <= L <= 40) or k + 1 + L + 3 > len(chunk):
                continue
            try:
                t = chunk[k + 1:k + 1 + L].decode('cp932')
            except UnicodeDecodeError:
                continue
            if not any(('\u3041' <= c <= '\u309f') or ('\u30a1' <= c <= '\u30fa') or ('\u4e00' <= c <= '\u9fff') for c in t):
                continue
            if chunk[k + 1 + L + 2] != 0x7F:
                continue
            term, body = t, chunk[k + 1 + L + 3:]
            break
        if term is None:
            continue
        raw = unpad(body)
        txt = raw.decode('cp932', 'replace').replace('\ufffd', '')
        txt = txt.replace('\x00', '').split('\xff')[0]
        txt = txt.replace('\\\\', '').replace('\\', '')
        for k, v in MACRO.items():
            txt = txt.replace(k, v)
        txt = re.sub(r'#([^#]*)#', r'\1', txt).replace('#', '').strip()
        if txt:
            out.append('【%s】%s' % (term, txt))
    return out


if __name__ == '__main__':
    for line in parse(sys.argv[1]):
        print(line)
