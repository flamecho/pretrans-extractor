#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""千銃士Rhodoknight (NS) —— SceneMasterVO.bin 全文本提取

格式（已实证，2026-10-16）：
  文件 = [u32 总记录数=125520] + 若干「记录」
  每条字符串字段 = [i32 描述符][u32 字符数][UTF-8 字节]
     描述符 = -(字节数 + 1)          ← 即 tag 不是字段号，而是「字节长」的冗余编码
     字符数 = 字符个数（用于 O(1) 索引）
  数值字段 = [i32 >=0]（自身即值，无载荷）等，与文本无关，扫描时自然跳过。

记录内字段语法（位置决定语义；无字段名）：
  ... [code_*_stories_* 场景ID] [flag] [bg] [name 名牌] [text 正文] [unit_*] [flag] [chara_*/voice_*] ...

成行规则：
  名字（名札）= 日文串 且 其「下一个字段」也是日文串
  正文        = 日文串 且 其「下一个字段」不是日文串 且 不在名字词表内
  ⇒ 一次点击（一个文本框，含 1 语音）= 一行；框内 '\n' = 框内换行，合并

宏：
  <player>    → 主角名占位（默认名见 PLAYER_NAME）
  <fpp>       → 第一人称占位（私/僕/俺/自分，默认取 0001 = 私）
  <birthday>  → 生日占位
  /1 /2 ...   → 选项序号（行尾），选项各成一行
"""
import json
import os
import re
import struct
import sys

# ---- 宏替换 ----
# <player> 与「マスター」同句共现（如「マスターである<player>でも」）⇒ 它是「可改名的主角名」，
# 全作数据（Master 全表 / IL2CPP 元数据 / Unity 基础 asset）均无默认名 ⇒ 按 04a C6 留全角占位。
PLAYER_NAME = '〔主人公名〕'
FPP = '私'                    # <fpp> 第一人称占位（PlayerFirstPersonMasterVO 0001 = 私）
BIRTHDAY = '〔誕生日〕'
UNKNOWN = '〔未解析〕'

IDRE = re.compile(r'^[A-Za-z0-9_/.]+$')
JPRE = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')          # 假名/汉字
OPT_TAIL = re.compile(r'/(\d+)\s*$')                        # 行尾 /N = 选项序号
MACRO_RE = re.compile(r'<[A-Za-z_]+>')
FPP_RE = re.compile(r'<fpp>')

# 源文笔误整行定值表（勿用正则泛修）：半角 "(" 应为全角 "（"（闭括号已是全角）
POSTFIX = {
    '(これ、誰のハナシだっけ……？……ああ、頭、ぼーっとする……）':
        '（これ、誰のハナシだっけ……？……ああ、頭、ぼーっとする……）',
    '(気のせい、か……？妙に重い圧みてぇなのを感じたが……）':
        '（気のせい、か……？妙に重い圧みてぇなのを感じたが……）',
    '(江戸みたいな街並みがあるなら……夢の神社も、自治区の中にあるだろうか……？）':
        '（江戸みたいな街並みがあるなら……夢の神社も、自治区の中にあるだろうか……？）',
}


def scan_fields(data):
    """扫描全部字符串字段：返回 [(offset, bytelen, text)]，按文件序（= 偏移序）。"""
    n = len(data)
    out = []
    i = 0
    while i + 8 <= n:
        tag = struct.unpack_from('<i', data, i)[0]
        if tag >= 0 or tag < -100000:
            i += 1
            continue
        blen = -tag - 1
        clen = struct.unpack_from('<I', data, i + 4)[0]
        if not (1 <= clen <= 100000) or i + 8 + blen > n:
            i += 1
            continue
        raw = data[i + 8:i + 8 + blen]
        try:
            s = raw.decode('utf-8')
        except UnicodeDecodeError:
            i += 1
            continue
        if len(s) != clen:               # 字符数必须与声明一致
            i += 1
            continue
        if any(ord(c) < 0x20 and c != '\n' for c in s):
            i += 1
            continue
        out.append((i, blen, s))
        i += 8 + blen
    return out


def classify(fields):
    """返回 (texts, names)。texts = [(off, str)] 正文；names = 名字词表。"""
    n = len(fields)
    names = set()
    for k in range(n):
        s = fields[k][2]
        if not JPRE.search(s) or IDRE.match(s):
            continue
        nxt = fields[k + 1][2] if k + 1 < n else ''
        if JPRE.search(nxt) and not IDRE.match(nxt):
            names.add(s)
    texts = []
    for k in range(n):
        off, _, s = fields[k]
        if not JPRE.search(s) or IDRE.match(s):
            continue
        nxt = fields[k + 1][2] if k + 1 < n else ''
        is_jp_next = bool(JPRE.search(nxt)) and not IDRE.match(nxt)
        if is_jp_next:
            continue                      # 后随日文 ⇒ 名字
        if s in names:
            continue                      # 名字词表（含名牌形态）
        texts.append((off, s))
    return texts, names


def expand_macros(s):
    s = FPP_RE.sub(FPP, s)
    s = s.replace('<player>', PLAYER_NAME)
    s = s.replace('<birthday>', BIRTHDAY)
    s = MACRO_RE.sub(UNKNOWN, s)          # 其余未知宏
    return s


def to_lines(s):
    """一个文本框 → 1 行；若含行尾 /N 选项标记 ⇒ 拆成多条选项，各 1 行。"""
    raw = s.replace('\r\n', '\n').split('\n')
    raw = [x for x in raw if x != '']
    opts = [(OPT_TAIL.search(x) is not None) for x in raw]
    if len(raw) > 1 and all(opts):
        return [OPT_TAIL.sub('', x) for x in raw]      # 纯选项块
    if any(opts):
        # 混合：把带 /N 的行拆出，其它合并
        res = []
        buf = []
        for x, isopt in zip(raw, opts):
            if isopt:
                if buf:
                    res.append(''.join(buf)); buf = []
                res.append(OPT_TAIL.sub('', x))
            else:
                buf.append(x)
        if buf:
            res.append(''.join(buf))
        return res
    return [''.join(raw)]                              # 框内换行 → 合并


def main():
    if len(sys.argv) < 3:
        print('usage: senjyushi_extract_text.py <SceneMasterVO.bin> <out.txt>')
        print('       senjyushi_extract_text.py <SceneMasterVO.bin> --names <out.txt>')
        print('         --names: 只导出名札词表（外核对用），不产出正文')
        return 1
    src, dst = sys.argv[1], sys.argv[2]
    dump_names = (len(sys.argv) > 3 and sys.argv[2] == '--names')
    if dump_names:
        dst = sys.argv[3]
    data = open(src, 'rb').read()
    fields = scan_fields(data)
    texts, names = classify(fields)
    if dump_names:
        from collections import Counter
        cnt = Counter()
        n = len(fields)
        for k in range(n - 1):
            s = fields[k][2]
            nx = fields[k + 1][2]
            if s in names and JPRE.search(nx) and not IDRE.match(nx):
                cnt[s] += 1          # 统计「处在名札位（后随日文）」的次数
        with open(dst, 'w', encoding='utf-8', newline='\n') as f:
            for s, c in cnt.most_common():
                f.write('%6d\t%s\n' % (c, s))
        print('名札词表 %d 条 -> %s' % (len(cnt), dst))
        return 0
    lines = []
    for off, s in texts:
        for ln in to_lines(s):
            ln = expand_macros(ln).strip()
            ln = POSTFIX.get(ln, ln)
            if ln:
                lines.append(ln)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('字段 %d / 名字词表 %d / 正文 %d / 成行 %d' % (len(fields), len(names), len(texts), len(lines)))
    print('->', dst)
    return 0


if __name__ == '__main__':
    sys.exit(main())
