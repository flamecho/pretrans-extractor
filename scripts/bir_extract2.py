#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ビルシャナ戦姫 ～一樹の風～ (NS) → 全文本

链路：NSP → NCA → romfs/common/{script.memfs,script.membody}
  memfs：`RSON` + 0x10 起重复 `{tag 0x2002C800, u32 off, u32 size}`
  membody：每项 `RZ` + zlib 压缩的 **纯文本脚本**（UTF-8 BOM）
脚本语法（本作实测）：
  纯文本行      ＝ 正文（地の文／台詞）
  <KW>          ＝ 等待点击 ⇒ **一框结束**
  <WinClear>    ＝ 清框（跟在上一条 <KW> 后）
  <...>         ＝ 命令；// 与 /* */ ＝ 注释；[label] ＝ 标签
"""
import os
import re
import sys
import glob

sys.path.insert(0, 'tools')
from matsurika_extract import parse_memfs, read_entry

ROOT = '_w_W3_bir/newscript'
OUT = '提取结果/[NS-JP]ビルシャナ戦姫 ～一樹の風～.txt'
TAG = re.compile(r'<[^<>]*>')
COMMENT = re.compile(r'^//')
LABEL = re.compile(r'^\[[^\]]*\]\s*$')


def chunks(text):
    """按 <KW> 切框；返回每框的正文行列表。"""
    parts = re.split(r'<KW>', text)
    for p in parts:
        lines = []
        in_block = False
        for ln in p.split('\n'):
            s = ln.strip()
            if s.startswith('/*'):
                in_block = True
            if in_block:
                if '*/' in s:
                    in_block = False
                continue
            if not s or COMMENT.match(s) or LABEL.match(s):
                continue
            if s.startswith('<') and s.endswith('>'):
                continue
            if s.startswith('<'):
                # 行首是命令、后半是正文（少见）：取命令之后的部分
                s = TAG.sub('', s).strip()
                if not s or s.startswith('//'):
                    continue
            lines.append(s)
        if lines:
            t = ''.join(lines)
            t = re.sub(r'^｛[^｝]*｝', '', t)      # 行首名札 ⇒ 丢（独立名字窗）
            t = re.sub(r'#[Tt]\d+', '', t)        # 立ち絵/表情タグ
            t = t.replace('\ufeff', '')
            if t.strip():
                yield t


def main():
    ents = parse_memfs(os.path.join(ROOT, 'script.memfs'))
    body = open(os.path.join(ROOT, 'script.membody'), 'rb').read()
    out = []
    for off, size in ents:
        b = read_entry(body, off, size)
        if b.count(0) > 4:
            continue                      # 非文本条目（二进制）
        try:
            raw = b.decode('utf-8-sig')
        except UnicodeDecodeError:
            continue
        for c in chunks(raw):
            t = c.strip()
            if t.startswith('{"') or '\ufffd' in t:
                continue                  # JSON/二进制残留
            if t:
                out.append(t)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(out) + '\n')
    print('scripts', len(ents), 'lines', len(out))


if __name__ == '__main__':
    main()
