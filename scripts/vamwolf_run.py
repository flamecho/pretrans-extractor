#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Vamwolf Cross† (PSV PCSG00467, D3P 系) —— sc.cpk → 全文本。

与 プリンス・オブ・ストライド 同族（CRI CPK + 自建字符集 + 自建位图字体），
但命令分配**不同**（逐作核）：

  FFF0 <plate> [FFE6 <NAME>]   说话人名牌（丢弃；plate 为名牌 id/装饰码）
  FFFF (空)                    文本框开始（＝一次点击）
  FFFF <payload>               选项（连续 FFFF 链；首条无前缀，其余 `　`+样式符 2 码）
  FF95 <maxlen><nlines><x> <TEXT>   正文（**固定 3 码前缀**）
  FFFE <TEXT>                  框内换行（合并；去行首全角空格）
  FFFB                         框结束
  FFE6 / FFE7                  主角 姓 / 名 宏（正文内联）→ 填默认名；名牌内则属名牌
  其余 FFxx / 装饰                     丢弃

条目录入：0x2000 B 头 + u16 LE 码流，尾 16 B 哈希。
基础字符集 = `stormlover_charset.CHARSET`（cp932 原序剔 4 组）；二级区逐作独立。
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK
from stormlover_charset import CHARSET      # 基础区＝cp932 原序剔 4 组（与 D3P 系同版，实证）

HDR = 0x2000
LEVEL2_START = 3456
CTRL = 0xFE00

# 本作二级区自用槽（字形渲染 + 文脉仲裁 + 「level-2 槽序==cp932 升序」窗口压缩，三证合一；
# 见 提取结果/解析报告/[PSV-JP]Vamwolf Cross†_解析报告.md）
SPECIAL = {
    3459: '隔', 3460: '動', 3461: '傲', 3463: '刹', 3464: '呟', 3465: '呻', 3466: '咄',
    3467: '咥', 3468: '唸', 3469: '喘', 3470: '喉', 3471: '嗅', 3472: '嗟', 3473: '嗜',
    3474: '責', 3475: '囁', 3476: '囮', 3477: '垢', 3478: '埒', 3479: '塹', 3480: '墟',
    3481: '奢', 3482: '媚', 3483: '孕', 3484: '寥', 3485: '屓', 3486: '峙', 3487: '赦',
    3488: '彷', 3489: '徨', 3490: '恍', 3491: '悍', 3492: '悸', 3493: '愕', 3495: '憑',
    3496: '憫', 3497: '後', 3498: '戮', 3499: '拗', 3500: '掟', 3501: '呑', 3502: '揶',
    3503: '揄', 3504: '攣', 3505: '朦', 3506: '朧', 3507: '棍', 3508: '欒', 3509: '騒',
    3510: '殲', 3511: '洒', 3512: '淹', 3513: '漿', 3514: '炙', 3515: '炒', 3516: '煌',
    3517: '爛', 3518: '陛', 3519: '獰', 3520: '珀', 3521: '琥', 3522: '璧', 3523: '甦',
    3524: '疇', 3525: '疼', 3526: '痒', 3527: '痙', 3528: '痣', 3529: '痺', 3530: '癪',
    3531: '皺', 3532: '眈', 3533: '眩', 3534: '眷', 3535: '睨', 3536: '瞑', 3537: '礫',
    3538: '祟', 3539: '悪', 3540: '籠', 3541: '絆', 3542: '綺', 3543: '罠', 3544: '羞',
    3545: '翡', 3546: '傾', 3547: '腑', 3548: '舐', 3549: '苺', 3550: '蕁', 3551: '蓄',
    3552: '藪', 3554: '蜃', 3555: '褄', 3556: '訝', 3557: '錆', 3558: '贅', 3559: '贔',
    3560: '敗', 3561: '軋', 3562: '轢', 3564: '淋', 3565: '邁', 3567: '隕', 3568: '頷',
    3569: '颯', 3570: '毒', 3571: '拐', 3572: '麩',
}

NAME_SUB = {0xFFE6: '白河', 0xFFE7: 'セリ'}     # 主角 姓 / 名（白河 セリ = Shirakawa Seri）
UNDECODED = '\u3013'

EXCLUDE = {"0156"}   # 系统/教程模板条目（见 main 注释）
C_NAME, C_BOX, C_BR, C_SEP = 0xFFF0, 0xFFFF, 0xFFFE, 0xFFFB
C_SUR, C_GIV = 0xFFE6, 0xFFE7

TEXT_PUNCT = set('\u3000\u3001\u3002\u300c\u300d\u300e\u300f\uff08\uff09\u3010\u3011'
                 '\uff01\uff1f\uff1a\uff1b\u2026\u2025\u30fb\u30fc\uff5e\uff0c\uff0e'
                 '\u2018\u2019\u201c\u201d\u3014\u3015\u2500\u2501\u2502\u2503')


def dec_run(run):
    out = []
    for v in run:
        if v in SPECIAL:
            out.append(SPECIAL[v]); continue
        if 0 <= v < len(CHARSET):
            out.append(CHARSET[v])
        elif v >= CTRL or v >= LEVEL2_START:
            continue
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


def _is_text_ch(ch):
    o = ord(ch)
    if 0x3041 <= o <= 0x30fa or 0x4e00 <= o <= 0x9fff or o == 0x3005:
        return True
    if 0xff10 <= o <= 0xff5a or 0x41 <= o <= 0x7a or 0x30 <= o <= 0x39:
        return True
    return ch in TEXT_PUNCT and ch != '\u3000'


def strip_opt(s):
    """选项 run 去前缀：组内首条无前缀；其余恒为「　＋样式符」2 码 → 剥 2。"""
    had_lead = s.startswith('\u3000')
    s = s.lstrip('\u3000')
    if had_lead and s:
        s = s[1:]                       # 样式符
    return s.strip()


def clean(s):
    s = s.replace('\u3000', ' ')     # 行内全角空格保留（不影响正文）
    return s


def extract_entry(d, opts_out, opt_lines=None):
    lines = []
    T = toks(d)
    # 0x2000 起先是「样式/字符定义表」区（含 FFFF/FFE6/FF33 噪声）；脚本从首个 FFF0（名牌）开始。
    start = 0
    while start < len(T) and T[start][0] != C_NAME:
        start += 1
    if start >= len(T):
        return lines
    cur = None
    in_name = False
    i = start
    n = len(T)

    prev_macro = False
    while i < n:
        cm, run = T[i]
        if cm == C_NAME:
            in_name = True
            i += 1
            continue
        if cm in (C_SUR, C_GIV):
            # 行内宏：紧跟在 FF95/FFFE 之后，或紧接在同一宏链（姓+名）之后
            prev = T[i - 1][0] if i > 0 else -1
            ok = (not in_name) and cur is not None and (prev in (0xFF95, C_BR) or prev_macro)
            if ok:
                cur += NAME_SUB[cm] + dec_run(run)
            prev_macro = ok
            i += 1
            continue
        prev_macro = False
        if cm == C_BOX:
            if in_name:
                in_name = False
            if not run:
                if cur is not None:
                    lines.append(cur)
                cur = ''
                i += 1
                continue
            # 选项链
            j = i; chain = []
            while j < n and T[j][0] == C_BOX and T[j][1]:
                chain.append(dec_run(T[j][1]))
                j += 1
            if len(chain) >= 1:
                texts = [strip_opt(x) for x in chain]
                texts = [t for t in texts
                         if t and re.search(r'[ぁ-ゖァ-ヺ一-龥0-9Ａ-Ｚａ-ｚ]', t)]
                # 链尾填充 run（大量全角空格）
                texts = [t for t in texts if t.count('\u3000') < 6 and ' ' == ' ']
                if texts and not any(_is_sys(t) for t in texts) \
                        and not any(_is_sys_opt(t) for t in texts):
                    if cur is not None and cur.strip():
                        lines.append(cur)
                    cur = None
                    for t in texts:
                        lines.append(t)
                        opts_out.append(1)
                        if opt_lines is not None:
                            opt_lines.append(t)
                    i = j
                    continue
            i = j if j > i else i + 1
            continue
        if cm == 0xFF95:
            txt = dec_run(run[3:]) if len(run) > 3 else ''
            if cur is None:
                cur = ''
            cur += txt
            i += 1
            continue
        if cm == C_BR:
            txt = dec_run(run).lstrip('\u3000')
            if cur is not None:
                cur += txt
            i += 1
            continue
        if cm == C_SEP:
            if cur is not None and cur.strip():
                lines.append(cur)
            cur = None
            in_name = False
            i += 1
            continue
        i += 1
    if cur is not None and cur.strip():
        lines.append(cur)
    return lines


SYS_LINES = set()
SYS_RE = [re.compile(r'^ばばば')]

# 系统菜单项（UI 表）：整链含其一 ⇒ 该链整段丢弃（坑 B26 同款处置）
SYS_OPT_RE = [
    re.compile(r'^次へ$'), re.compile(r'^前に戻る$'), re.compile(r'^指名に進む$'),
    re.compile(r'に質問する$'), re.compile(r'^あなたの役職は？$'),
]

# 原文笔误（源码该框末尾码＝`？`，确无 `」`；全篇其余 15k+ 行均有）→ 整行定值修正
FIX_LINES = {
    # 0077：源码该框末尾码＝`？`，确无 `」`（全篇其余 15k+ 行均有）→ 补
    '「優哉さんは……その、悩みごととか、ないですか？':
        '「優哉さんは……その、悩みごととか、ないですか？」',
    # 0087：同一框（FF95+FFFE＝一次点击）内多出一个 `」`（`「A」B」`）→ 去中间一个（一框＝一段引用）
    '「ゆっ……ゆゆゆゆゆ、優哉、さん……っ！」み、みんなに、見られ……」':
        '「ゆっ……ゆゆゆゆゆ、優哉、さん……っ！み、みんなに、見られ……」',
}


def _is_sys_opt(s):
    return any(rx.match(s) for rx in SYS_OPT_RE)


def _is_sys(s):
    if s in SYS_LINES:
        return True
    return any(rx.match(s) for rx in SYS_RE)


def filter_lines(lines):
    res = []
    for s in lines:
        s = s.strip()
        if not s:
            continue
        if _is_sys(s):
            continue
        s = FIX_LINES.get(s, s)
        if not re.search(r'[ぁ-ゖァ-ヺ一-龥0-9Ａ-Ｚａ-ｚ]', s):
            continue
        res.append(s)
    return res


def fold_repeats(lines):
    out = []
    i = 0
    n = len(lines)
    while i < n:
        done = False
        maxk = min((n - i) // 2, 120)
        for k in range(maxk, 0, -1):
            if lines[i:i + k] == lines[i + k:i + 2 * k]:
                out.extend(lines[i:i + k]); i += 2 * k; done = True; break
        if not done:
            out.append(lines[i]); i += 1
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    optdst = sys.argv[3] if len(sys.argv) > 3 else None
    c = CPK(src)
    entries = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
                     key=lambda e: int(e['name']))
    all_lines = []
    options = []
    opt_lines = []
    for e in entries:
        # EXCLUDE：系统/教程模板条目（0156 头字段＝`voice_not_exist`，内容全为教程说明＝系统/UI 文本，§0 不收）。
        # 想收就删掉这个表项。
        if e['name'] in EXCLUDE:
            continue
        raw = c.raw(e)
        d = raw[HDR:-16] if len(raw) > HDR + 16 else raw[HDR:]   # 尾 16B = 哈希（勿并入码流）
        all_lines.extend(filter_lines(extract_entry(d, options, opt_lines)))
    # 本作**无「同段双写」**（实测双写块 = 0），故不做整段折叠（折叠反而会误删行）。
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(all_lines)); f.write('\n')
    if optdst:
        with open(optdost := optdst, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(opt_lines)); f.write('\n')
    print('entries %d  lines %d (选项 %d) -> %s' % (len(entries), len(all_lines), len(options), dst))


if __name__ == '__main__':
    main()
