#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STORM LOVER 2nd V (PSV PCSG00736) —— 从 sc.cpk 产出全文本。

字符集见 stormlover2_charset.py（基础区同 V；二级自定义槽 SPECIAL 逐位置定值）。

命令结构（≥0xFF00，与 V 同族，实测）：
  fff0 <style> <NAME>   说话人名字段 → 丢（不加说话人前缀）
  ffff       <BODY>     正文框开始（= 一次点击）；其 run 恒为正文
  fffe       <TEXT>     框内换行；其 run 恒为正文
  fffb                  消息分隔
  内联命令（ffe6=姓 / ffe7=名 / fffd）：其 run 仍为正文；其余 0xFFxx 的 run 视为参数丢弃。

主角（外部核对 vndb/shionlib：嵐山 真理）：
  ffe6=姓『嵐山』 ffe7=名『真理』；默认名 = 嵐山真理。
清洗：弌(0x5F0C)=ルビ结束标记 → 删；二级未定值槽 → 〔未解析〕；表格/系统残留过滤。
"""
import os, sys, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stormlover2_charset import CHARSET, SPECIAL, LEVEL2_START, DECO_SEP, DECO_WORD
from cpk import CPK

C_NAME, C_BOX, C_BR, C_SEP = 0xFFF0, 0xFFFF, 0xFFFE, 0xFFFB
INLINE_CMDS = {C_BOX, C_BR, 0xFFE6, 0xFFE7, 0xFFFD, 0xFF0F}
# FF0F = 主角一人称宏（「私」）——实证：`[FF0F]は２年に編入予定の[FFE6][FFE7]です`
#        →「私は２年に編入予定の嵐山真理です」；`[FF0F]が通う学校`→「私が通う学校」
# FFE6/FFE7 = 姓/名占位（嵐山／真理）
NAME_SUB = {0xFF0F: '\u79c1', 0xFFE6: '\u5d50\u5c71', 0xFFE7: '\u771f\u7406'}
RUBY_MARK = '\u5f0c'          # 弌
UNDECODED = '\u3014\u672a\u89e3\u6790\u3015'   # 〔未解析〕


def toks(d):
    n = len(CHARSET)
    N = len(d) // 2
    vals = struct.unpack_from('<%dH' % N, d, 0)
    out = []
    cur = 0
    run = []
    for v in vals:
        if v >= 0xFF00:
            out.append((cur, run))
            run = []
            cur = v
        else:
            run.append(v)
    out.append((cur, run))
    return out


def _is_unknown_slot(v):
    return v >= LEVEL2_START


def words_to_text(ws):
    n = len(CHARSET)
    k = len(ws)
    while k > 0:
        v = ws[k - 1]
        if v >= n or _is_unknown_slot(v):
            k -= 1
        else:
            break
    out = []
    for v in ws[:k]:
        if v in SPECIAL:
            out.append(SPECIAL[v]); continue
        if v >= n or v >= LEVEL2_START:
            out.append(UNDECODED); continue
        ch = CHARSET[v]
        o = ord(ch)
        if 0xE000 <= o <= 0xF8FF or ch == '\u3013':
            out.append(UNDECODED)
        else:
            out.append(ch)
    return ''.join(out)


def run_is_text(cmd, ws):
    return cmd in INLINE_CMDS


TEXT_PUNCT = set('\u3000\u3001\u3002\u300c\u300d\u300e\u300f\uff08\uff09\u3010\u3011'
                  '\uff01\uff1f\uff1a\uff1b\u2026\u2025\u30fb\u30fc\uff5e\uff0c\uff0e'
                  '\u2018\u2019\u201c\u201d\u3014\u3015')


def _is_text_ch(ch):
    o = ord(ch)
    if 0x3041 <= o <= 0x30fa or 0x4e00 <= o <= 0x9fff:
        return True
    if 0xff10 <= o <= 0xff5a or 0x41 <= o <= 0x7a:
        return True
    return ch in TEXT_PUNCT


def _strip_symbols(s):
    i = 0
    while i < len(s):
        if s.startswith(UNDECODED, i) or not _is_text_ch(s[i]):
            i += len(UNDECODED) if s.startswith(UNDECODED, i) else 1
        else:
            break
    return s[i:].strip()


def extract_entry(d):
    boxes = []
    cur = None
    in_name = False
    for cmd, ws in toks(d):
        if cmd == C_NAME:
            in_name = True
            continue
        if cmd == C_SEP:
            in_name = False
            if cur is not None:
                boxes.append(cur); cur = None
            continue
        if cmd == C_BOX:
            in_name = False
            if cur is not None:
                boxes.append(cur)
            cur = [words_to_text(ws)]
            continue
        if cmd == 0 or in_name:
            continue
        if cmd == C_BR:
            if cur is not None:
                cur.append(words_to_text(ws))
            continue
        if cur is not None:
            if cmd in NAME_SUB:
                cur.append(NAME_SUB[cmd])
                if ws:
                    cur.append(words_to_text(ws))
            elif run_is_text(cmd, ws):
                cur.append(words_to_text(ws))
    if cur is not None:
        boxes.append(cur)

    res = []
    for lines in boxes:
        s = ''.join([lines[0]] + [x.lstrip('\u3000') for x in lines[1:]])
        s = s.replace(RUBY_MARK, '').strip()
        s = _strip_symbols(s)
        s = fix_deco(s)
        while s.endswith(UNDECODED):
            s = s[:-len(UNDECODED)].rstrip()
        if re.fullmatch(r'.{1,4}\uff1a', s):
            continue
        if s in (NAME_SUB[0xFFE6] + NAME_SUB[0xFFE7], NAME_SUB[0xFFE6], NAME_SUB[0xFFE7]):
            continue
        if UNDECODED * 3 in s:
            continue
        if re.search(r'^[\u30fb\uff1d\u3011]|\u25bc|[\u309b\u2261\u2266\u2267\u221e\u2234\u2642\uffe2\u266d\u2208]', s):
            continue
        if UNDECODED + UNDECODED in s and not any(
                '\u3041' <= c <= '\u3096' or '\u30a1' <= c <= '\u30fa' for c in s):
            continue
        if UNDECODED in s and sum(
                1 for c in s if '\u3041' <= c <= '\u3096' or '\u30a1' <= c <= '\u30fa') <= 1:
            continue
        if len(s) <= 6 and any(c in s for c in '\u2260\u220b\u00b6\u2227\u2200\u2207\u2283\u2208'
                                              '\u223d\u2229\u222a\u2103\u2032\u2033\u2211\u221a'):
            continue
        if len(s) <= 4 and s[:1] in '\u3002\u3001\uff0c\uff0e\u00b7' and not any(
                '\u3041' <= c <= '\u3096' or '\u30a1' <= c <= '\u30fa' for c in s):
            continue
        if len(s) <= 4 and any(
                0x2100 <= ord(c) <= 0x23FF or 0x2460 <= ord(c) <= 0x24FF
                or 0x25A0 <= ord(c) <= 0x27BF or 0x2E00 <= ord(c) <= 0x2E7F for c in s):
            continue
        body = s.replace(UNDECODED, '').replace('\u3000', '')
        if body and sum(1 for c in body if _is_text_ch(c)) < len(body) * 0.5:
            continue
        if len(s) >= 2 and _has_content(s) and not UI_SKIP.search(s) \
                and not UI_SKIP.search(s.strip('\u300c\u300d\u300e\u300f')):
            res.append(s)
    return res


# 系统 / UI / 调试残留（§0 不收）：演出测试串、选择支/分支标签、服装差分表、商店价格表、入口头部残留
UI_SKIP = re.compile(
    r'^[\u3041-\u3096]{1,2}[\u3002\u3001]$'
    r'|(\u6f14\u51fa\u3067\u3059\u3002?|\u6f14\u51fa\u7d42\u4e86\u3067\u3059\u3002?|\u306e\u30c6\u30b9\u30c8|\u30c6\u30b9\u30c8\u3067\u3059\u3002?)$'
    r'|(\u9078\u629e\u80a2[\uff10-\uff190-9]|\u5206\u5c90[\uff10-\uff190-9]|\u5206\u5c90\u3057\u307e\u3059\u3088|\u4e8c\u80a1\u9078\u629e|'
    r'\u30d0\u30ab\u30c3\u30d7\u30eb|\u6700\u521d\u306b\u623b\u308a\u307e\u3059|\u3053\u308c\u3067\u7d42\u308f\u308a\u3067\u3059|'
    r'\u4e57\u308a\u63db\u3048\u308b|\uff01\u30d0\u30fc\u30b9\u30c8\u3057\u305f|\uff1a\u4e8c\u80a1\u306b\u3059\u308b)'
    r'|^(\u304a\u91d1\u304c\u8db3\u308a\u307e\u305b\u3093|\u56fd\u8a9e\u304c\u4e0a\u304c\u308a\u307e\u3059|\u304a\u91d1\u304c\u5897\u3048\u307e\u3059|'
    r'\u304a\u91d1\u304c\u6e1b\u308a\u307e\u3059|\u89aa\u5bc6\u5ea6.*)$'
    r'|^\u4e8b\u4ef6\u30d1\u30fc\u30c8\u3092\u30b9\u30ad\u30c3\u30d7'
    r'|^[\uff0c\uff0e\u2025\u30fb\u3001]'
    r'|^[^\s]{1,8}\u3000+(\u5236\u670d|\u79c1\u670d|\u4f53\u64cd\u670d|\u4f53\u64cd\u7740|\u90e8\u5c4b\u7740|\u6c34\u7740|\u6d74\u8863|'
    r'\u30b8\u30e3\u30fc\u30b8|\u5bdd\u9593\u7740|\u51ac\u670d|\u590f\u670d)(\u3000|$)'
    r'|^[^\s]{0,12}\u3000+[\uff10-\uff190-9]+\u4e07\u5186?$'
    r'|^[^\s]{0,6}(\u79c1\u670d|\u5236\u670d|\u4f53\u64cd\u670d|\u30b8\u30e3\u30fc\u30b8)(\uff5c.*)?$'
)


def _has_content(s):
    for ch in s:
        if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff') \
           or ('\uff10' <= ch <= '\uff5a') or ('A' <= ch <= 'z') \
           or ('\u3014' <= ch <= '\u3015'):
            return True
    return False


# —— 邮件装饰绘文字 → 对应文字 ——
# 分隔类（①..⑳ / Ⅴ / Ⅹ）→ 按句读落「。」（前接 ？！。…、」』） 时不再重复）。
# 对象类（Ⅲ=メール / Ⅳ=携帯 / Ⅷ=雨）→ 近义复现（同一小句已出现同义词）时丢弃装饰，否则替词。
SEP_CHARS = {SPECIAL[k]: k for k in DECO_SEP if k in SPECIAL}
WORD_CHARS = {SPECIAL[k]: (s, w) for k, (s, w) in DECO_WORD.items() if k in SPECIAL}
_PUNCT = set('\u3002\uff01\uff1f\u2026\u3001\u300d\u300f\uff09\u3015')
_WIN = 12


def fix_deco(s):
    out = []
    for ch in s:
        if ch in SEP_CHARS:
            if out and out[-1] not in _PUNCT:
                out.append('\u3002')
            continue
        if ch in WORD_CHARS:
            word, dup = WORD_CHARS[ch]
            tail = ''.join(out[-_WIN:])
            if any(d in tail for d in dup):
                continue          # 已出现过同义词 ⇒ 装饰重复，丢弃
            out.append(word)
            continue
        out.append(ch)
    return ''.join(out)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    c = CPK(src)
    entries = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
                     key=lambda e: int(e['name']))
    all_lines = []
    for e in entries:
        all_lines.extend(extract_entry(c.raw(e)))
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(all_lines) + '\n')
    print('entries', len(entries), 'lines', len(all_lines), '->', dst)


if __name__ == '__main__':
    main()
