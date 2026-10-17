#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""プリンス・オブ・ストライド (PSV PCSG00491) —— sc.cpk → 全文本（2026-10-12）。

引擎 = D3P/5pb 系「CRI CPK + 自建字符集 + 自建位图字体」同族（与 STORM LOVER 同源）：
  - 字符集基础区 = cp932 有效双字节码原码序，剔 0x81FC / Greek / Cyrillic / 0x849F（=─）
  - 二级区（code ≥ 3456）= 本作自用字形槽，**槽序 == 字在 cp932 中的序号升序**（已证 57 槽严格单调）
  - 字形图集 USRDIR/lt.bin：**392 B/字形 = 28 行 × 14 B（4bpp，28×28）**，无头部，索引 == 游戏码；
    文件尾 192 B 零填充 + 16 B 哈希
  - 文本 = 条目内 u16 LE 码流；条目 = **0x2000 B 头 + 码流**（头含 u32 参数表，解码自然跳过）

命令集（实测）：
  FFF0 <样式><NAME>  名札 → 丢弃（不加说话人前缀）
  FFFF <TEXT>        文本框开始（一次点击）
  FFFE <TEXT>        框内换行（合并）
  FFFB               消息分隔
  FF4D <样式><KW>    行内关键词/人名插入 → 保留
  FF4C <TEXT>        行内续写 → 保留
  FFE6 / FFE7        主角 姓 / 名 占位（ゲーム内定名 桜井 奈々）
  其余 FFxx / ≥0xFE00 → 参数·UI，丢弃

选项：连续 FFFF 链；每条前置一个「　+記号」的装饰符（首条可能无）；纯装饰/填充 run 丢弃。
主角 = **桜井 奈々**（vndb / 动画官网，固定名；正文中名字为字面出现）。
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK
from stormlover_charset import CHARSET

LEVEL2_START = 3456
CTRL = 0xFE00

# 本作二级区自用槽（字形读 + 文脉 + 「槽序==cp932 序号升序」三证合一；见 解析报告）
SPECIAL = {
    3456: '─', 3457: '丼', 3458: '侘', 3459: '侑', 3460: '俯', 3461: '劍', 3462: '吽',
    3463: '唸', 3464: '嗅', 3465: '埃', 3466: '埒', 3467: '奢', 3468: '姜', 3469: '屓',
    3470: '彷', 3471: '彿', 3472: '憬', 3473: '憑', 3474: '憫', 3475: '拗', 3476: '拉',
    3477: '拮', 3478: '掟', 3479: '摯', 3480: '杞', 3481: '椒', 3483: '鬱', 3484: '沁',
    3485: '洒', 3486: '滲', 3487: '瑕', 3488: '瑣', 3489: '璧', 3490: '疇', 3491: '眩',
    3492: '睨', 3493: '瞑', 3494: '瞰', 3495: '磋', 3496: '籠', 3497: '絆', 3498: '綺',
    3499: '翔', 3500: '腑', 3501: '舅', 3502: '舐', 3504: '茹', 3505: '莉', 3506: '蛛',
    3507: '袂', 3508: '詭', 3509: '誅', 3510: '貪', 3511: '贅', 3512: '贔', 3514: '躓',
    3515: '颯', 3516: '騙', 3517: '黎',
}

C_NAME, C_BOX, C_BR, C_SEP = 0xFFF0, 0xFFFF, 0xFFFE, 0xFFFB
C_KW, C_KW2 = 0xFF4D, 0xFF4C          # 行内关键词插入 / 续写
NAME_SUB = {0xFFE6: '桜井', 0xFFE7: '奈々'}   # 主角 姓 / 名（游戏内定名）
UNDECODED = '〔未解析〕'
RUBY_MARK = '\u5f0c'                  # 弌（假名注音结束标记）

HDR = 0x2000


TEXT_PUNCT = set('\u3000\u3001\u3002\u300c\u300d\u300e\u300f\uff08\uff09\u3010\u3011'
                 '\uff01\uff1f\uff1a\uff1b\u2026\u2025\u30fb\u30fc\uff5e\uff0c\uff0e'
                 '\u2018\u2019\u201c\u201d\u3014\u3015')

# 选项文本前恒接 1 个引擎样式符（游戏字体符号）。样式符不含开括号（除非该开括号未配对＝样式）。
OPEN_END = {'（': '）', '「': '」', '『': '』', '【': '】', '〔': '〕', '〈': '〉', '《': '》', '｛': '｝'}


def _strip_opt_lead(s):
    i = 0
    while i < len(s) and i <= 3:
        c = s[i]
        o = ord(c)
        if 0x3041 <= o <= 0x30fa or 0x4e00 <= o <= 0x9fff:
            break
        if 0x30 <= o <= 0x39 or 0x41 <= o <= 0x7a:
            break
        if 0xff10 <= o <= 0xff5a:                 # 全角英数：形如「ｍ．」= 列表标签
            if i + 1 < len(s) and s[i + 1] == '．':
                i += 2
                continue
            break
        if c in OPEN_END and s.count(c) <= s.count(OPEN_END[c]):
            break                                  # 开括号已配对 ⇒ 正文首字
        i += 1
    return s[i:].strip()


def _is_text_ch(ch):
    o = ord(ch)
    if 0x3041 <= o <= 0x30fa or 0x4e00 <= o <= 0x9fff:
        return True
    if 0xff10 <= o <= 0xff5a or 0x41 <= o <= 0x7a or 0x30 <= o <= 0x39:
        return True
    return ch in TEXT_PUNCT


def _strip_lead_symbols(s):
    """剥离行首装饰符（选项圆点/样式符），直到遇到正文首字。"""
    i = 0
    while i < len(s) and not _is_text_ch(s[i]):
        i += 1
    return s[i:].strip()


LEAD_KEEP = set('「」『』（）〔〕【】〈〉《》［］｛｝、。，．・：；？！…‥ー―‐〜～'
                '＋－±×÷＝≠＜＞°℃￥＄％＃＆＊＠§☆★○●◎△▲▽▼※〒→←↑↓♪♭♯')


def _is_lead_keep(ch):
    """行首首字是否应保留（正文首字）。否则视为引擎样式符 → 剥离。"""
    o = ord(ch)
    if 0x3041 <= o <= 0x30FA or 0x4E00 <= o <= 0x9FFF:
        return True
    if 0x30 <= o <= 0x39 or 0x41 <= o <= 0x7A:
        return True
    if 0xFF10 <= o <= 0xFF19 or 0xFF21 <= o <= 0xFF3A or 0xFF41 <= o <= 0xFF5A:
        return True
    return ch in LEAD_KEEP


def _strip_one_lead(s):
    if s and not _is_lead_keep(s[0]):
        return s[1:]
    return s


def _is_punct_or_symbol(s):
    return bool(re.fullmatch(r'[\u3000-\u303f\uff01-\uff65\u2010-\u203b'
                             r'\u2500-\u257f\u25a0-\u27bf\u2e00-\u2e7f]*', s))


def words_to_text(ws):
    n = len(CHARSET)
    k = len(ws)
    while k > 0:
        v = ws[k - 1]
        if v >= CTRL or v >= n or (LEVEL2_START <= v < CTRL and v not in SPECIAL):
            k -= 1
        else:
            break
    out = []
    for v in ws[:k]:
        if v in SPECIAL:
            out.append(SPECIAL[v]); continue
        if v >= CTRL or v >= n or v >= LEVEL2_START:
            continue                       # 二级未定义槽 / ≥0xFE00 → 丢弃
        ch = CHARSET[v]
        o = ord(ch)
        if 0xE000 <= o <= 0xF8FF or ch == '\u3013':
            out.append(UNDECODED)
        else:
            out.append(ch)
    return ''.join(out)


def toks(d):
    N = len(d) // 2
    vals = struct.unpack_from('<%dH' % N, d, 0)
    out = []; cur = 0; run = []
    for v in vals:
        if v >= 0xFF00:
            out.append((cur, run)); run = []; cur = v
        else:
            run.append(v)
    out.append((cur, run))
    return out


def clean(s):
    s = s.replace(RUBY_MARK, '').strip()
    s = s.lstrip('\u3000')
    s = _strip_one_lead(s)
    return s


def extract_entry(d, opts_out):
    """返回本条目正文行；同时把选项追加到 opts_out。"""
    lines = []
    T = toks(d)
    cur = None            # 当前打开的文本框内容（None = 无）
    in_name = False       # 名札区（形如 FFF0 <样式> [FFFF 空] FF4D <NAME>）
    seen_text = False     # 条目内是否已出现正文（用于跳过开头的系统菜单选项）
    i = 0
    n = len(T)
    while i < n:
        cm, ws = T[i]
        txt = words_to_text(ws)
        if cm in (C_BOX, C_BR, C_KW, C_KW2) and '\u3000' * 6 in txt:
            i += 1                              # 条目尾的填充 run（全角空格 + 杂码）
            continue
        if cm == C_NAME:
            in_name = True
            i += 1
            continue
        if cm == C_SEP:
            in_name = False
            if cur:
                lines.append(clean(cur))
            cur = None
            i += 1
            continue
        if cm == C_BOX:
            if in_name and not txt:
                # 名札变体：FFF0 <样式> FFFF(空) FF4D <NAME>；继续留名札模式丢弃
                i += 1
                continue
            in_name = False
            # 连续 FFFF 链 = 选项
            j = i
            chain = []
            while j < n and T[j][0] == C_BOX:
                chain.append(words_to_text(T[j][1]))
                j += 1
            if len(chain) >= 2:
                # 链末尾常为「填充 run（大量全角空格 + 个别杂码）」→ 剔除
                chain = [x for x in chain if '\u3000' * 6 not in x]
                # 以「单符号 run」为组分隔符切组
                groups = []
                cur_g = []
                for x in chain:
                    t = clean(x)                      # clean 已去「　」与 1 个样式符
                    if len(t) <= 1:                   # 分隔符 run（仅样式符）
                        if cur_g:
                            groups.append(cur_g); cur_g = []
                        continue
                    cur_g.append(x)
                if cur_g:
                    groups.append(cur_g)
                chain_texts = []
                for g in groups:
                    if len(g) < 2 or not seen_text:
                        continue
                    texts = []
                    for k, x in enumerate(g):
                        s = x.replace(RUBY_MARK, '').lstrip('\u3000').strip()
                        if k > 0 and s:
                            s = s[1:]                 # 组内首条无样式符，其余恒有 1 个
                        s = _strip_one_lead(s.strip()).strip()
                        if s and len(s) >= 2 and not _is_punct_or_symbol(s) \
                                and UNDECODED not in s \
                                and re.search(r'[ぁ-ゖァ-ヺ一-龥]', s):
                            texts.append(s)
                    if texts:
                        chain_texts.append(texts)
                # 同一条链内若含系统菜单项（场景选择/确认），整链丢弃
                if not any(_is_sys(t) for ts in chain_texts for t in ts):
                    for ts in chain_texts:
                        for s in ts:
                            lines.append(s)               # 选项就地输出（忠于剧情顺序）
                            opts_out.append(1)
                if any(len(g) >= 2 for g in groups):
                    if cur:
                        lines.append(clean(cur))
                    cur = None
                    i = j
                    continue
            if cur:
                lines.append(clean(cur))
            cur = txt
            _c = clean(txt)
            if len(_c) >= 12 and not _is_sys(_c):
                seen_text = True
            i += 1
            continue
        if cm == C_BR:
            if not in_name and cur is not None:
                cur += txt
            i += 1
            continue
        if cm in NAME_SUB:
            if not in_name and cur is not None:
                cur += NAME_SUB[cm] + txt    # 宏值 + 紧随其后的正文 run
            i += 1
            continue
        if cm in (C_KW, C_KW2):
            if not in_name and cur is not None:
                if cm == C_KW and txt:
                    txt = txt[1:]           # FF4D run = <样式符><关键词>（样式符恒为首字）
                cur += txt
            i += 1
            continue
        i += 1
    if cur:
        lines.append(clean(cur))
    return lines


SYS_LINES = {
    'ばばば、',
    'シーンスキップしました。',
    'クリアデータが存在するため、ゲームの開始地点を選択することができます。',
    'どのシーンからゲームを開始しますか？',
    'ゲームを最初から開始します。よろしいですか？',
    '前回までのプレイの結果、このスタート地点からゲームを始めた場合、',
    '以上のキャラクターのシナリオへ分岐することができます。',
    'このスタート地点からゲームを開始してもよろしいですか？',
}
SYS_RE = [
    re.compile(r'^「ＶＳ.+」.*戦後の、?シーン\d+からゲームを開始します。$'),
    re.compile(r'^試合「.+」をスキップしますか？$'),
    re.compile(r'^(桜井)?(奈々)?(桜井)?(奈々)?$'),
    # 场景选择菜单（系统 UI）：整组丢弃
    re.compile(r'^(最初から開始する|シーン\d+から開始する)$'),
]


# 原文笔误（括号不配对；已逐条核对原始码流确认为脚本自身缺陷）→ 整行定值修正
FIX_LINES = {
    '明日、号外出すから。『美人すぎるリレーショナー……':
        '明日、号外出すから。『美人すぎるリレーショナー……』',
    'たっすん！　俺のリード、あとはヨロリン！）':
        '（たっすん！　俺のリード、あとはヨロリン！）',
    '（……どうしよう）私……すごく、ずるいんじゃないかな）':
        '（……どうしよう。私……すごく、ずるいんじゃないかな）',
    '今では「プリンス・オブ・ストライド」なんて呼ばれてる）':
        '（今では「プリンス・オブ・ストライド」なんて呼ばれてる）',
}


def _is_sys(s):
    if s in SYS_LINES:
        return True
    for rx in SYS_RE:
        if rx.match(s):
            return True
    return False


def _style_strip(t):
    """名札 / FF4D 的 run 恒以 1 个引擎样式符开头 → 无条件剥首字。"""
    t = t.replace(RUBY_MARK, '').lstrip('\u3000')
    if t:
        t = t[1:]
    return t.strip()


def collect_cast(d, out):
    """名札表整表导出（零成本 cast 核对源）。
    结构：(a) FFF0 <样式><NAME>  (b) FFF0 <样式> FFFF(空) FF4D <样式><NAME> FF4C"""
    T = toks(d)
    in_name = False
    namebox = False
    for cm, ws in T:
        if cm == C_NAME:
            in_name = True
            namebox = False
            t = _style_strip(words_to_text(ws))
            if t:
                out.add(t)
            continue
        if not in_name:
            continue
        if cm == C_BOX:
            if not words_to_text(ws).strip():
                namebox = True          # 空框 ⇒ 名字可能随后由 FF4D 给出
            else:
                in_name = False
        elif cm == C_KW and namebox:
            t = _style_strip(words_to_text(ws))
            if t:
                out.add(t)
            in_name = False
        elif cm == C_SEP:
            in_name = False


def filter_lines(lines, cast):
    res = []
    for s in lines:
        if not s:
            continue
        s = s.strip()
        if not s:
            continue
        if _is_sys(s):
            continue
        s = FIX_LINES.get(s, s)
        if s in cast:                     # 菜单残行 / 名札漏网
            continue
        if _is_punct_or_symbol(s) and not re.search(r'[ぁ-ゖァ-ヺ一-龥]', s):
            continue
        if not re.search(r'[ぁ-ゖァ-ヺ一-龥0-9Ａ-Ｚａ-ｚ]', s):
            continue
        res.append(s)
    return res


def fold_repeats(lines):
    """本作脚本把同一段场景发射两次：一次名字用字面、一次经 FFE6/FFE7 宏。
    归一化后两段全同 ⇒ 按「整段全同」折叠（坑 B24）。仅在紧邻重复时折叠。"""
    out = []
    i = 0
    n = len(lines)
    while i < n:
        done = False
        maxk = min((n - i) // 2, 120)
        for k in range(maxk, 0, -1):
            if lines[i:i + k] == lines[i + k:i + 2 * k]:
                out.extend(lines[i:i + k])
                i += 2 * k
                done = True
                break
        if not done:
            out.append(lines[i])
            i += 1
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    c = CPK(src)
    entries = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
                     key=lambda e: int(e['name']))
    all_lines = []
    options = []
    cast = set()
    for e in entries:
        collect_cast(c.raw(e)[HDR:], cast)
    for e in entries:
        d = c.raw(e)[HDR:]
        lines = extract_entry(d, options)
        all_lines.extend(filter_lines(lines, cast))
    all_lines = fold_repeats(all_lines)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(all_lines))
        f.write('\n')
    print('entries %d  lines %d (其中选项 %d) -> %s'
          % (len(entries), len(all_lines), len(options), dst))


if __name__ == '__main__':
    main()
