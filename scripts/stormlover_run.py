#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STORM LOVER V (PSV PCSG00735) —— 从 sc.cpk 产出全文本（2026-10-11）。

字符集见 stormlover_charset.py（cp932 原序，剔 0x81FC/Greek/Cyrillic/0x849F，0 偏移）。

命令结构（≥0xFF00，实测）：
  fff0 <style> <NAME>   说话人名字段 → 丢（不加说话人前缀）
  ffff       <BODY>     正文框开始（= 一次点击）；其 run 恒为正文
  fffe       <TEXT>     框内换行；其 run 恒为正文
  fffb                  消息分隔
  其它命令(ff33/ff32/ff68/ff31/ff08/…)：**run 含平假名 ⇒ 正文（ff08=一人称「私」），
      否则为脚本参数（图标/坐标等 gaiji），丢弃。**
主角 = 五十嵐 由奈（vndb c14782 / ELF 名字输入表）；只经宏 FFE6(姓)/FFE7(名) 出现。
字面「猪狩」= 配角 **猪狩 澪**（男，vndb c6095 / 名字槽 3458），**不可批量替换**。
清洗：`弌`(0x5F0C) 为ルビ结束标记 → 删；PUA/越界码 → `〔未解析〕`；纯符号/单字符行 → 删。
"""
import os, sys, struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stormlover_charset import CHARSET, SPECIAL, LEVEL2_START
from cpk import CPK

C_NAME, C_BOX, C_BR, C_SEP = 0xFFF0, 0xFFFF, 0xFFFE, 0xFFFB

# 内联命令（其 run 是正文，会插入在文本中间，如名字插入 / ルビ）；其余 0xFFxx 命令的
# run 全是脚本参数（图标 id / 坐标等 gaiji），丢弃。
INLINE_CMDS = {C_BOX, C_BR, 0xFFE6, 0xFFE7, 0xFFFD}
# FF08 = 主角「一人称」宏（游戏默认「私」）；FFE6/FFE7 = 主角「姓名」占位（姓 / 名）
# 三者均为运行时宏，随玩家设定变化；此处填游戏默认值（主角 = 五十嵐 由奈，见 vndb c14782）。
NAME_SUB = {0xFF08: '\u79c1', 0xFFE6: '\u4e94\u5341\u5d50', 0xFFE7: '\u7531\u5948'}

# 输出层改名 —— 留空（**切勿**对「猪狩」做批量替换：字面「猪狩」= 配角 猪狩 澪（いかり），
# 是另一个角色；主角姓「五十嵐」只经宏 FFE6 出现，故只需设 NAME_SUB 即可）。
RENAME = {}
RUBY_MARK = '\u5f0c'          # 弌
UNDECODED = '\u3014\u672a\u89e3\u6790\u3015'   # 〔未解析〕


def _hira(v, n):
    return 0 <= v < n and '\u3041' <= CHARSET[v] <= '\u3096'


def _kata(v, n):
    return 0 <= v < n and '\u30a1' <= CHARSET[v] <= '\u30fa'


def toks(d):
    """→ [(cmd, [words]), ...]；cmd=0 为文件头裸数据（丢弃）。"""
    n = len(CHARSET)
    N = len(d) // 2
    vals = struct.unpack_from('<%dH' % N, d, 0)
    out = []
    i = 0
    cur = 0
    run = []
    while i < N:
        v = vals[i]
        if v >= 0xFF00:
            out.append((cur, run))
            run = []
            cur = v
        else:
            run.append(v)
        i += 1
    out.append((cur, run))
    return out


def _is_unknown_slot(v):
    if v in SPECIAL:
        return False
    return v >= LEVEL2_START        # 二级区 = 游戏自用字形槽


def words_to_text(ws):
    """段内文本；**段尾的未知字形槽 / 越界码**（邮件签尾图标等）一并剔除。"""
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
        if v >= n:
            out.append(UNDECODED); continue
        if v >= LEVEL2_START:
            out.append(UNDECODED); continue
        ch = CHARSET[v]
        o = ord(ch)
        if 0xE000 <= o <= 0xF8FF or ch == '\u3013':   # PUA / geta → 未解析
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
    """剥离行首的脚本参数符号（选项 ID / 头像标记等 gaiji），保留正文。"""
    i = 0
    while i < len(s):
        if s.startswith(UNDECODED, i) or not _is_text_ch(s[i]):
            i += len(UNDECODED) if s.startswith(UNDECODED, i) else 1
        else:
            break
    return s[i:].strip()


def extract_entry(d):
    n = len(CHARSET)
    boxes = []
    cur = None
    in_name = False        # 名札区（C_NAME..C_BOX/C_SEP）内的内容一律丢弃
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
        # 其它命令：内联命令 → 正文
        #   ff08 = 一人称「私」；ffe6/ffe7 = 主角 姓/名「五十嵐 / 由奈」（均为运行时宏）
        #   先插入宏值，再续其 run（run 中是紧随其后的正文）
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
    import re
    for lines in boxes:
        s = ''.join([lines[0]] + [x.lstrip('\u3000') for x in lines[1:]])
        s = s.replace(RUBY_MARK, '').strip()
        s = _strip_symbols(s)
        while s.endswith(UNDECODED):          # 行尾字形槽（图标/签尾）剔除
            s = s[:-len(UNDECODED)].rstrip()
        if re.fullmatch(r'.{1,4}\uff1a', s):        # 名字札 X：
            continue
        if s in (NAME_SUB[0xFFE6] + NAME_SUB[0xFFE7], NAME_SUB[0xFFE6], NAME_SUB[0xFFE7]):
            continue                                # 纯姓名行（名札 / UI 列表残留）
        if UNDECODED * 3 in s:                      # 姓名输入用汉字表等网格（系统/UI）→ 剔除
            continue
        # 系统/UI 残留：目録・分类行（以 ・/＝/】 开头或含 ▼）、姓名表（含 ゛）、分类图标 → 剔除
        if re.search(r'^[\u30fb\uff1d\u3011]|\u25bc|[\u309b\u2261\u2266\u2267\u221e\u2234\u2642\uffe2\u266d\u2208]', s):
            continue
        # 纯汉字、无假名、且含 ≥2 连续未知槽（姓名输入表网格行）→ 剔除
        if UNDECODED + UNDECODED in s and not any(
                '\u3041' <= c <= '\u3096' or '\u30a1' <= c <= '\u30fa' for c in s):
            continue
        # 表格行：几乎无假名（≤1）且含未知槽（姓名/コード表网格、符号汤行）→ 剔除
        if UNDECODED in s and sum(
                1 for c in s if '\u3041' <= c <= '\u3096' or '\u30a1' <= c <= '\u30fa') <= 1:
            continue
        # 短行含数学/记号图表符号（≠∋¶∧∀∇⊃℃…，記号一覧/表格残留）→ 剔除
        if len(s) <= 6 and any(c in s for c in '\u2260\u220b\u00b6\u2227\u2200\u2207\u2283\u2208'
                                              '\u223d\u2229\u222a\u2103\u2032\u2033\u2211\u221a'):
            continue
        # 表格行：以句读开头、≤4 字符、无假名（`。Ｌ≪` 型記号表残留）→ 剔除
        if len(s) <= 4 and s[:1] in '\u3002\u3001\uff0c\uff0e\u00b7' and not any(
                '\u3041' <= c <= '\u3096' or '\u30a1' <= c <= '\u30fa' for c in s):
            continue
        # 表格行：≤4 字符且含记号/图形字符（∃Å⌒ 等記号表残留）→ 剔除
        if len(s) <= 4 and any(
                0x2100 <= ord(c) <= 0x23FF or 0x2460 <= ord(c) <= 0x24FF
                or 0x25A0 <= ord(c) <= 0x27BF or 0x2E00 <= ord(c) <= 0x2E7F for c in s):
            continue
        body = s.replace(UNDECODED, '').replace('\u3000', '')
        if body and sum(1 for c in body if _is_text_ch(c)) < len(body) * 0.5:
            continue
        if len(s) >= 2 and _has_content(s):
            for _a, _b in RENAME.items():
                s = s.replace(_a, _b)
            res.append(s)
    return res


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
    # 1178 = 按码序的字符集清单（系统/UI，非台词）→ 不收
    entries = sorted([e for e in c.entries if e['name'].isdigit() and e['name'] != '1178'],
                     key=lambda e: int(e['name']))
    all_lines = []
    for e in entries:
        all_lines.extend(extract_entry(c.raw(e)))
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(all_lines) + '\n')
    print('entries', len(entries), 'lines', len(all_lines), '->', dst)


if __name__ == '__main__':
    main()
