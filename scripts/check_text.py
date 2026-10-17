#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前自检（品检）—— 日文游戏剧本文本提取产物的通用检查器。

用法: python check_text.py OUT.txt [...] [--name 主角名]... [--maxlen 200] [--quiet]
      --name 可多个（主角名「出现性」自检，至少一个须命中）。
退出码: 0=无 ERROR（WARN 不阻断）/ 1=有 ERROR。显示宽度: 全角=1、半角=0.5。

检查项（均来自历史返工点，**别删**；判据与由来见 skill `references/00b-pitfall-deliver.md`）:
  [E] BOM / CR / U+FFFD / `〓` / 控制符 / 半角假名(U+FF66-FF9F) / PUA / 引号不配对 /
      行首孤立标点 / 说话人残留 / 未解析插入宏·占位符
  [W] 主角名未出现 / 空行 / 超长行 / 重复行 / 非日文字符 / 标点健全性 / 半角引号 /
      半角标点(U+FF61-FF65 ｡｢｣､･——可能是原文用字)
"""
import argparse
import collections
import re
import sys
import unicodedata

C0_BAD = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
HALFWIDTH_KANA = re.compile(r'[\uFF66-\uFF9F]')   # 真·半角仮名（ｱｲｳ…／ｰﾞﾟ）
# ★ 2026-10-16（ソラ*ユメ）：U+FF61–FF65 是**半角标点**（｡｢｣､･），不是假名。
#   原文自带的半角标点（如 `（黙々と食べてる･･････）` 的 ･×6、`よし､号令！` 的 ､）
#   属**原文用字**、非 cp932 化け ⇒ 降为 [W]，**须人工核实而非盲目判 E**。
HALFWIDTH_PUNCT = re.compile(r'[\uFF61-\uFF65]')
PUA = re.compile(r'[\uE000-\uF8FF]')
FFFD = '\ufffd'
GETA = '\u3013'          # 〓（历史遗留占位符）
# ★ 2026-10-17（ウィル・オ・ウィスプ ポータブル）：括号内**含句读/省略号**者非名札 ——
#   本作演出上的「精灵之声」写作 `【カラダ……】`／`【カラダが、ホシイ……】`（原文上屏特效，须保留）。
#   判据＝名札是**裸名**（不含 。、…‥）；【？？？】仍算名札（？不是句读）。
_NAME_INNER = r'[^】。、…‥]{1,20}'
NAME_PLATE = re.compile(r'^[!！]?【' + _NAME_INNER + r'】$')          # 独立名札行（整行）
NAME_PREFIX_BRACKET = re.compile(r'^[!！]?【' + _NAME_INNER + r'】')   # 行首【名】＋正文（前缀）
# ★ 例外（ときメモGS4 实证，2026-10-15）：はばたきネットの店舗/商品ニュースは本文が `【ブティック・ジェス】「古典…」`
#   这样以「含『・』的店名」开头 ⇒ 非说话人残留。判据＝括号内含 '・' 或 '＠' 时不算。
NAME_PREFIX_BRACKET_OK = re.compile(r'^[!！]?【[^】]*[・＠][^】]*】')
# 行首「名前：」——前缀含句读符号/记号线 ⇒ 是正文非名札（Norn9 10-10；CRAZY CHA!N 10-14）
# 亦排除**全角拉丁字母/数字**前缀（ときメモGS3 10-15：乐队名 `ＲｅＤ：Ｃｒｏ’Ｚ…` 与句中
# `オレらのＲｅＤ：…` 被误报；名札不会是全角拉丁）。
NAME_PREFIX_COLON = re.compile(r'^[^\s。「、！？…‥（(【『」』）)〔〕［］《》〈〉—―‐−─～〜'
                               r'Ａ-Ｚａ-ｚ０-９]{1,8}[：:]')
ALLOWED_SYM = set('　、。・…‥—―‐−─～〜「」『』（）()［］[]｛｝{}〈〉《》【】〔〕'
                  '！？!?，,．.：:；;／/＼＊*＃#＠@＆&％%＋+＝=＜＞'
                  '＄￥￥￠￡№♪☆★○●◎◇◆□■△▲▽▼※→←↑↓〒〆々〻ヽヾゝゞ'
                  '０１２３４５６７８９')


def disp_width(s: str) -> float:
    w = 0.0
    for ch in s:
        w += 1.0 if unicodedata.east_asian_width(ch) in ('W', 'F') else 0.5
    return w


def is_jp(ch: str) -> bool:
    o = ord(ch)
    for a, b in ((0x3000, 0x30FF), (0x4E00, 0x9FFF), (0xFF01, 0xFF60),
                 (0x2010, 0x203B), (0x2190, 0x21FF), (0x2460, 0x24FF), (0x2500, 0x25FF)):
        if a <= o <= b:
            return True
    return o in (0x0100, 0x00D7, 0x00F7)


def check(path: str, names, maxlen: float, quiet: bool):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8-sig', 'replace')
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    err, warn = [], []

    # ---- 形态 ----
    if not raw.startswith(b'\xef\xbb\xbf'):
        err.append('BOM 缺失（应为 UTF-8 with BOM）')
    ncr = raw.count(b'\r')
    if ncr:
        err.append('出现 CR ×%d（必须纯 LF）' % ncr)
    for label, pat, sep in (('U+FFFD（解码失败）', None, FFFD),
                            ('`〓` 占位符', None, GETA)):
        c = text.count(sep)
        if c:
            err.append('%s ×%d' % (label, c))
    c = len(C0_BAD.findall(text))
    if c:
        err.append('控制符(C0) ×%d' % c)
    c = len(HALFWIDTH_KANA.findall(text))
    if c:
        err.append('半角假名 ×%d（疑「首字节损坏」化け）' % c)
    c = len(HALFWIDTH_PUNCT.findall(text))
    if c:
        warn.append('半角标点(U+FF61-65) ×%d（可能是原文用字，须人工核实；见 00b）' % c)
    c = len(PUA.findall(text))
    if c:
        err.append('私用区 PUA ×%d（未映射字形槽）' % c)

    # ---- 引号配对 ----
    # ★ 颜文字(kaomoji)行不计入括号配对（2026-10-17 アルコバレーノ! ポータブル）：
    #   颜文字的 `（￣Д￣；` / `＾・ω・）／` / `σ＾Д＾）σ` 本就单侧括号，属原文用字，
    #   与「台词引号」无关；同理「前綴是句读/记号 ⇒ 是正文」——是口径本身，非特例放行。
    #   判据＝行内含颜文字专用符号（￣ ω ∀ д σ ＾ ´ ｀ ﾟ ▽ △ 等）。
    KAOMOJI = set('￣￢ω∀∀дДσΣ＾´｀ﾟ▽△ヮ⌒')
    quote_text = '\n'.join(l for l in lines if not (KAOMOJI & set(l)))
    for a, b in (('「', '」'), ('『', '』'), ('（', '）'), ('(', ')')):
        ca, cb = quote_text.count(a), quote_text.count(b)
        if ca != cb:
            err.append('引号不配对 %s=%d / %s=%d' % (a, ca, b, cb))
    # 行中已闭合的正常；只报真正不均衡的行。
    openq = [l for l in lines if l.startswith('「') and l.count('「') > l.count('」')]
    if openq:
        err.append('行首「未闭合 ×%d（行被吞/断行）: %s'
                   % (len(openq), ' | '.join(l[:30] for l in openq[:3])))

    # ---- 半角引号 `"`（2026-10-14 用户指出）----
    # 日文正文引号一律「」；ASCII `"` 即疑脚本引号/参数解析错。实例 CRAZY CHA!N
    # EV006-004.h 行尾多写一个 `"`（`…」""`），旧解析器「首尾各去一引号」把它吃进正文。
    dq = [l for l in lines if '"' in l]
    if dq:
        warn.append('半角引号 `"` ×%d 行（日文正文应为「」；多为脚本引号/参数解析错）: %s'
                    % (len(dq), ' | '.join(l[:30] for l in dq[:3])))

    # ---- 行首孤立标点（2026-10-14 用户指出）----
    # 「一次点击 = 一行」⇒ 行首不会有 、。 等收束标点；出现即前文被切，常见原因＝
    # 主角名插入宏落在参数区被跳过（实例 マスケティア 名字宏 `1D 00`）。
    LEAD_PUNCT = ('、', '。', '，', '．', ',', '.', '）', ')', '」', '』', '】', '〕')
    leadp = [l for l in lines if l[:1] in LEAD_PUNCT]
    if leadp:
        err.append('行首孤立标点 ×%d（前文被切/源数据分页）: %s'
                   % (len(leadp), ' | '.join(l[:30] for l in leadp[:3])))

    # ---- 标点健全性（2026-10-12）----
    # 判据＝「句号 ≈ 行数量级」；三重拦截（计数 0 / 行尾 0 / 远少于顿号）。
    # 起因：アンジェリーク ルトゥール 句号写在 cp932 0x8140 槽 ⇒ 被当全角空格清洗。
    if len(lines) >= 300:
        n_period = text.count('。')
        n_comma = text.count('、')
        n_end_period = sum(1 for l in lines if l.endswith('。'))
        if n_period == 0:
            err.append('全篇 0 个句号「。」（%d 行）—— 疑句号被清洗（实例：写在 cp932 '
                       '0x8140 槽 ⇒ 解出全角空格后被当填充删掉）' % len(lines))
        elif n_end_period == 0:
            err.append('行尾 0 个句号「。」（全篇 %d 个）—— 疑行尾标点被清洗' % n_period)
        elif n_period < len(lines) * 0.05:
            warn.append('句号「。」仅 %d 个 / %d 行 —— 比例偏低，请人工确认' % (n_period, len(lines)))
        if n_period and n_comma > n_period * 5:
            warn.append('顿号「、」%d 远多于句号「。」%d（>5×）—— 疑句号丢失' % (n_comma, n_period))

    # ---- 说话人残留 ----（收紧由来见 00b-pitfall-deliver.md）
    HIRA_CHK = re.compile(r'[\u3040-\u309f]')
    lc = collections.Counter(lines)
    plate = [l for l in lines
             if NAME_PLATE.match(l) and lc[l] >= 2
             and not HIRA_CHK.search(l.strip('!！'))]
    if plate:
        err.append('独立名字札行 ×%d: %s' % (len(plate), ' | '.join(plate[:3])))
    pre = []
    # 名札 head 须 >=2 行；用語辞典 head 唯一 ⇒ 不算名札。
    _heads = collections.Counter(l.split('】', 1)[0] for l in lines if NAME_PREFIX_BRACKET.match(l))
    for l in lines:
        if (not NAME_PREFIX_BRACKET.match(l) or NAME_PLATE.match(l)
                or NAME_PREFIX_BRACKET_OK.match(l)):   # 含「・/＠」的店名/商品名 ⇒ 非说话人残留
            continue
        head = l.split('】', 1)[0]
        if HIRA_CHK.search(head):
            continue
        if _heads[head] < 2:
            continue
        rest = l.split('】', 1)[1] if '】' in l else ''
        if rest[:1] in ('', '「', '『', '（', '(', ' ', '\u3000'):
            pre.append(l)
    if pre:
        err.append('行首【名】＋正文 ×%d: %s' % (len(pre), ' | '.join(l[:30] for l in pre[:3])))
    pre2 = [l for l in lines
            if NAME_PREFIX_COLON.match(l)
            and re.search(r'[ぁ-んァ-ヶ一-龯]', NAME_PREFIX_COLON.match(l).group(0))
            # ★ 字段标签一律放行（2026-10-17 アルコバレーノ! ポータブル 邮件表：
            #   `＞意外だな送信者：室田　要…` / 书信 `注意：`・`追伸：`）——是正文的字段名，
            #   不是说话人名札残留；与 00b「前綴是句读/记号/非文字 ⇒ 是正文」同源。
            # ★ 章节标题 / 扉文（`第一幕：ミフターフ１日目`，ガーネット・クレイドル 2026-10-17）同理放行
            and not re.search(r'送信者|受信者|件名|宛先|差出人|本文|注意|追伸|ＰＳ|Ｑ|Ａ', 
                              NAME_PREFIX_COLON.match(l).group(0))
            and not re.search(r'^[第＃#]?[0-9一二三四五六七八九十０-９]{0,3}[幕章話節]',
                              NAME_PREFIX_COLON.match(l).group(0))
            # ★ 时刻（`4:00pm`／`5:56pm`）与 `No.2` 之类：冒号后紧跟数字 ⇒ 是正文
            #   （2026-10-18 Confidential Money：8DF4=':' 半角冒号，误报 11 行）
            and not re.match(r'.{0,8}[0-9０-９][：:][0-9０-９]', l)]
    if pre2:
        err.append('行首「名前：」×%d: %s' % (len(pre2), ' | '.join(l[:30] for l in pre2[:3])))

    # ---- 主角名 ----
    for nm in names:
        c = text.count(nm)
        if c == 0:
            warn.append('主角名 %r 未出现（疑插入宏被当空控制码丢弃）' % nm)
        elif not quiet:
            print('  [i] 主角名 %r 出现 %d 行' % (nm, sum(1 for l in lines if nm in l)))

    # ---- 行级 ----
    blank = sum(1 for l in lines if l.strip() == '')
    if blank:
        warn.append('空行 ×%d（规范要求不留空行）' % blank)
    longl = [(i + 1, disp_width(l)) for i, l in enumerate(lines) if disp_width(l) > maxlen]
    if longl:
        warn.append('超长行(>%g 宽) ×%d，例如 L%d (%g 宽): %s'
                    % (maxlen, len(longl), longl[0][0], longl[0][1], lines[longl[0][0] - 1][:40]))
    dup = [(i + 2, lines[i + 1]) for i in range(len(lines) - 1) if lines[i] and lines[i] == lines[i + 1]]
    if dup:
        warn.append('相邻重复行 ×%d: L%d %r' % (len(dup), dup[0][0], dup[0][1][:40]))
    leadsp = sum(1 for l in lines if l.startswith('　'))
    if leadsp and not quiet:
        print('  [i] 行首全角空格 ×%d（多为游戏内刻意缩排，可保留）' % leadsp)

    # ---- 未解析插入宏 / 占位符（2026-10-15 用户指出；カエル畑DEつかまえて☆彡）----
    # 由来：本作 0xf0 场景标题里用「@GameLast」这种**文本宏**写主角姓氏（0xf0 只有字符串操作数、
    # 没有槽位可替换，作者换了种写法）；提取驱动只处理 `%s` ⇒ 成品漏出 `@GameLast` 却过了品检。
    # 盲区＝下面「非日文字符」把 `o < 0x80` 全部跳过 ⇒ 任何 ASCII 都放行。
    # 只判「宏形状」，不否决普通 ASCII（OK / BGM / CG / 半角日期等照旧放行）。
    MACRO = re.compile(r'@[A-Za-z_]\w*'          # @GameLast 型
                       r'|%[-0-9.$*]*[A-Za-z]'   # %s / %d / %.1d / %1$s 型（未替换的插入宏）
                       r'|\\[A-Za-z]{1,}')       # `\n` `\c` 型残留控制码
    mac = [(i + 1, m.group()) for i, l in enumerate(lines) for m in [MACRO.search(l)] if m]
    if mac:
        err.append('未解析插入宏/占位符 ×%d（插入宏未被还原；若确为原文 ASCII 再单列）: %s'
                   % (len(mac), ' | '.join('L%d %r' % (i, s) for i, s in mac[:4])))

    # ---- 非日文字符 ----
    bad_chars = {}
    for i, l in enumerate(lines):
        for ch in l:
            o = ord(ch)
            if o < 0x80 or ch in ALLOWED_SYM or is_jp(ch):
                continue
            bad_chars.setdefault(ch, []).append(i + 1)
    if bad_chars:
        sample = ', '.join('%r(L%d)' % (ch, v[0]) for ch, v in list(bad_chars.items())[:8])
        warn.append('非日文字符 %d 种：%s' % (len(bad_chars), sample))

    # ---- 统计 ----
    widths = sorted(disp_width(l) for l in lines) or [0]
    print('=== %s ===' % path)
    print('  行数 %d / 字节 %d / 最长 %g 宽 / 中位 %g 宽'
          % (len(lines), len(raw), widths[-1], widths[len(widths) // 2]))
    for m in err:
        print('  [E] ' + m)
    for m in warn:
        print('  [W] ' + m)
    if not err and not warn:
        print('  ✅ 全部检查通过')
    return len(err) == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--name', action='append', default=[])
    ap.add_argument('--maxlen', type=float, default=200.0)
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    ok = True
    for f in a.files:
        ok &= check(f, a.name, a.maxlen, a.quiet)
        print()
    print('RESULT:', 'PASS' if ok else 'FAIL(有 ERROR)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
