#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STORM LOVER 夏恋!!（PSP）—— 从 sc.cpk 产出全文本（2026-10-12）。

字符集见 stormlover_natsu_charset.py（基础区同 PSV 版；二级区=本作自用字形槽 SPECIAL）。

命令结构（≥0xFF00，与 PSV 同族，实测）：
  FFF0 <style> <NAME>   说话人名字段 → 丢（§0 不加说话人前缀）
  FFFF       <BODY>     正文框开始（= 一次点击）；其 run 恒为正文
  FFFE       <TEXT>     框内换行；其 run 恒为正文
  FFFB                  消息分隔
  FF0F                  主角一人称宏（私）——实证 `[FF0F]は…` `[FF0F]をここに` `[FF0F]が通う学校`
  FFE6 / FFE7           主角 姓 / 名 占位（五十嵐 / 由奈）——实证 `[FFE6]さん` `[FFE7]さんと一緒に`
  其余 0xFFxx           图标 id / 坐标等脚本参数 → 整段 run 丢弃

主角：**五十嵐 由奈**（vndb c14782，`Name can be changed`）——数据中**只以宏 FFE6/FFE7 出现**。
  ★ 字面「猪狩」＝**猪狩 澪**（vndb c6095，另一名男性角色），**不得混同/改名**（见下方 RENAME 注释）。

清洗：二级未定值槽 → 〔未解析〕；邮件装饰绘文字（3494..3527）→ 按同作 PSV 版口径落地
      （①..⑳・Ⅴ・Ⅹ → 句读「。」；Ⅲ/Ⅳ/Ⅷ → メール/携帯/雨；ｃｍ/ｋｇ・㊤/㊦ 按字面）；
      姓名输入字库网格 / 系统 UI 残留 → 剔除。
用法：python scripts/stormlover_natsu_run.py <sc.cpk> <out.txt>
"""
import os, sys, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stormlover_natsu_charset import CHARSET, SPECIAL, DECO, LEVEL2_START
from stormlover_natsu_charset import DECO_SEP, DECO_WORD
from cpk import CPK

C_NAME, C_BOX, C_BR, C_SEP = 0xFFF0, 0xFFFF, 0xFFFE, 0xFFFB
# 内联命令：其 run 仍为正文（FF0F=一人称宏、FFE6/7=姓名占位）
INLINE_CMDS = {C_BOX, C_BR, 0xFFE6, 0xFFE7, 0xFF0F}
NAME_SUB = {0xFF0F: '\u79c1',                     # 私
            0xFFE6: '\u4e94\u5341\u5d50',         # 五十嵐（主角 姓，玩家可改）
            0xFFE7: '\u7531\u5948'}               # 由奈（主角 名，玩家可改）
UNDECODED = '\u3014\u672a\u89e3\u6790\u3015'      # 〔未解析〕

# ★ 主角名 = **运行时宏**，绝不与字面姓名混同（2026-10-12 修正）：
#   字面 `猪狩`（数据中出现 74 框）＝ **猪狩 澪**（vndb c6095，另一名男性角色，
#   见内联槽 3475=澪、`２階には巳城、辰原、猪狩、卯都木の寝室`、`猪狩くん`），**不得改名**。
#   主角 = **五十嵐 由奈**（vndb c14782，`Name can be changed`）→ 仅出现于宏 `FFE6`(姓)/`FFE7`(名)，
#   故在 NAME_SUB 处填默认名。字面「五十嵐」在数据中 0 次出现。
RENAME = {}                                  # 本作无输出层改名（字面人名为他人，须保持原样）


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


def words_to_text(ws):
    """段内文本。段尾的未定值槽一并剔除（邮件签尾）。已定值字形（含装饰绘文字）保留。"""
    n = len(CHARSET)
    k = len(ws)
    while k > 0:
        v = ws[k - 1]
        if v in SPECIAL:
            break                                      # 已定值（含装饰绘文字）→ 保留给 fix_deco
        if v in DECO or v >= n or v >= LEVEL2_START:
            k -= 1
        else:
            break
    out = []
    for v in ws[:k]:
        if v in SPECIAL:
            out.append(SPECIAL[v]); continue
        if v in DECO:
            continue                                   # 装饰绘文字 → 丢弃
        if v >= n or v >= LEVEL2_START:
            out.append(UNDECODED); continue
        ch = CHARSET[v]
        o = ord(ch)
        if 0xE000 <= o <= 0xF8FF or ch == '\u3013':     # PUA / geta
            out.append(UNDECODED)
        else:
            out.append(ch)
    return ''.join(out)


TEXT_PUNCT = set('\u3000\u3001\u3002\u300c\u300d\u300e\u300f\uff08\uff09\u3010\u3011'
                 '\uff01\uff1f\uff1a\uff1b\u2026\u2025\u30fb\u30fc\uff5e\uff0c\uff0e'
                 '\u2018\u2019\u201c\u201d\u3014\u3015\u2015\u2500\u2501')


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
    s = s[i:].strip()
    # 选项「ID 前缀」：选项框首字符为标点标记（游戏码 1..5 = 、。，．・），剥掉
    s = s.lstrip('\u3001\u3002\uff0c\uff0e\u30fb').strip()
    return s


# —— 邮件装饰绘文字 → 对应文字（口径与同作 PSV《2nd V》一致）——
# 分隔类（①..⑳ / Ⅴ / Ⅹ）→ 按句读落「。」（前接 ？！。…、」』） 时不再重复；行首（前无内容）直接丢弃）。
# 对象类（Ⅲ=メール / Ⅳ=携帯 / Ⅷ=雨）→ 近义复现（同一小句 ~12 字内已出现同义词）时丢弃装饰，否则替词。
SEP_CHARS = {SPECIAL[k]: k for k in DECO_SEP if k in SPECIAL}
WORD_CHARS = {SPECIAL[k]: (s, w) for k, (s, w) in DECO_WORD.items() if k in SPECIAL}
_DECO_PUNCT = set('\u3002\uff01\uff1f\u2026\u3001\u300d\u300f\uff09\u3015')
_DECO_WIN = 12


def fix_deco(s):
    out = []
    for ch in s:
        if ch in SEP_CHARS:
            if out and out[-1] not in _DECO_PUNCT:
                out.append('\u3002')
            continue
        if ch in WORD_CHARS:
            word, dup = WORD_CHARS[ch]
            tail = ''.join(out[-_DECO_WIN:])
            if any(d in tail for d in dup):
                continue          # 已出现过同义词 ⇒ 装饰是重复强调，丢弃
            out.append(word)
            continue
        out.append(ch)
    return ''.join(out)


def extract_entry(d):
    boxes = []
    cur = None
    in_name = False        # 名札区（FFF0..FFFF/C_SEP）内一律丢弃
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
            elif cmd in INLINE_CMDS:
                cur.append(words_to_text(ws))
    if cur is not None:
        boxes.append(cur)

    res = []
    for lines in boxes:
        s = ''.join([lines[0]] + [x.lstrip('\u3000') for x in lines[1:]])
        s = s.strip()
        s = _strip_symbols(s)
        s = fix_deco(s)
        while s.endswith(UNDECODED):
            s = s[:-len(UNDECODED)].rstrip()
        if re.fullmatch(r'.{1,4}\uff1a', s):
            continue
        if s in (NAME_SUB[0xFFE6] + NAME_SUB[0xFFE7], NAME_SUB[0xFFE6], NAME_SUB[0xFFE7]):
            continue
        if UNDECODED * 2 in s:
            continue
        if re.search(r'^[\u30fb\uff1d\u3011]|\u25bc|[\u309b\u2261\u2266\u2267\u221e\u2234\u2642\uffe2\u266d\u2208]', s):
            continue
        if UNDECODED in s and not any(
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
        if UI_JUNK.search(s):
            continue
        body = s.replace(UNDECODED, '').replace('\u3000', '')
        if body and sum(1 for c in body if _is_text_ch(c)) < len(body) * 0.5:
            continue
        if len(s) >= 2 and _has_content(s):
            res.append(fix_line(s))
    return res


# —— 整行定值修正（原文笔误，非正则泛修）——
# 邮件正文共 6 处写作「（笑」而缺右括号（同作则写作「（笑）」），4 处在行尾、2 处在行中
# （`…気になるの？（笑まあ趣味は…` / `…俺の相手でもする？（笑ちょうど今…`）。
# 已核原始码流：`（笑` 之后紧跟命令码而非「）」码（0x2A）⇒ 属原文笔误，非提取缺陷。
_CHARS_LAUGH = '\uff08\u7b11'          # （笑
_LAUGH_FULL = '\uff08\u7b11\uff09'     # （笑）


def fix_line(s):
    if _CHARS_LAUGH in s and _LAUGH_FULL not in s:
        s = s.replace(_CHARS_LAUGH, _LAUGH_FULL)
    for _a, _b in RENAME.items():
        s = s.replace(_a, _b)
    return s


# 系统/UI 残留：入口头部网格（私×N + 制表符 + 记号）、姓名输入字库网格、演出/测试串
UI_JUNK = re.compile(
    r'\u2500-\u257f'                       # 制表符（正文中不出现）
    r'|\u9752[\u2580-\u259f]'              # 块元素
)


def _has_content(s):
    for ch in s:
        if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff') \
           or ('\uff10' <= ch <= '\uff5a') or ('A' <= ch <= 'z') \
           or ('\u3014' <= ch <= '\u3015'):
            return True
    return False


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
