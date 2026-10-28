#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ビルシャナ戦姫 ～一樹の風～ (NS) → 全文本
> **两版并存**：`bir_extract2.py` 是精简定稿（链路更短）；本版多带「块内空行不是分页」的
> 判定与 `stats['multiseg']` 人工复核计数（2026-10-27 加），排错时用这版。

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

ROOT = '_w_W3_bir/romfs/common'
OUT = '提取结果/[NS-JP]ビルシャナ戦姫 ～一樹の風～.txt'
TAG = re.compile(r'<[^<>]*>')
COMMENT = re.compile(r'^//')
LABEL = re.compile(r'^\[[^\]]*\]\s*$')


def chunks(text, stats=None):
    """按 <KW> 切框；返回每框的正文行列表。

    2026-10-27：块内「空行」不是分页（本作全篇只用 <KW> 断框），它只是排版分段。
    两条正文行之间若**只有空行**（没有命令行/注释），拼接会吃掉这段空行 ⇒
    记进 stats['multiseg'] 供人工复核（本作 24,558 块里真·混排仅 1 处）。
    """
    parts = re.split(r'<KW>', text)
    for p in parts:
        raw_lines = p.split('\n')
        lines, body_idx = [], []
        in_block = False
        for i, ln in enumerate(raw_lines):
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
            body_idx.append(i)
        if lines:
            if stats is not None:
                seg = 1
                for a, b in zip(body_idx, body_idx[1:]):
                    gap = raw_lines[a + 1:b]
                    if gap and all(not g.strip() for g in gap):
                        seg += 1
                if seg > 1:
                    stats['multiseg'] = stats.get('multiseg', 0) + 1
                    stats.setdefault('multiseg_samples', []).append(
                        '%d 段｜%s' % (seg, ''.join(lines)[:56]))
            t = ''.join(lines)
            t = re.sub(r'^｛[^｝]*｝', '', t)      # 行首名札 ⇒ 丢（独立名字窗）
            t = re.sub(r'#[Tt]\d+', '', t)        # 立ち絵/表情タグ
            t = t.replace('\ufeff', '')
            if t.strip():
                yield t


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else ROOT
    out_path = sys.argv[2] if len(sys.argv) > 2 else OUT
    stats = {}
    ents = parse_memfs(os.path.join(root, 'script.memfs'))
    body = open(os.path.join(root, 'script.membody'), 'rb').read()
    out = []
    for off, size in ents:
        b = read_entry(body, off, size)
        if b.count(0) > 4:
            continue                      # 非文本条目（二进制）
        try:
            raw = b.decode('utf-8-sig')
        except UnicodeDecodeError:
            continue
        for c in chunks(raw, stats):
            t = c.strip()
            if t.startswith('{"') or '\ufffd' in t:
                continue                  # JSON/二进制残留
            if t:
                out.append(t)
    d = os.path.dirname(out_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(out) + '\n')
    print('scripts', len(ents), 'lines', len(out))
    if stats.get('multiseg'):
        print('块内被空行分段 %d 处（需人工确认是否同框混排）：' % stats['multiseg'])
        for x in stats.get('multiseg_samples', [])[:10]:
            print('   ', x)


if __name__ == '__main__':
    main()
