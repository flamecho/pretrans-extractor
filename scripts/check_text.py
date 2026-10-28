#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前自检（品检）—— 日文游戏剧本文本提取产物的通用检查器。

用法: python check_text.py OUT.txt [...] [--name 主角名]... [--maxlen 200] [--quiet]
      --name 可多个（主角名「出现性」自检，至少一个须命中）。
退出码: 0=无 ERROR（WARN 不阻断）/ 1=有 ERROR。显示宽度: 全角=1、半角=0.5。

检查项（均来自历史返工点，**别删**；判据与由来见 skill `references/00b-pitfall-deliver.md`）:
  [E] BOM / CR / U+FFFD / `〓` / 控制符 / 半角假名(U+FF66-FF9F) / PUA / 引号不配对 /
      脚本·资源残留（party_xxx / `:ld_n 8:` / `if …==` / `a/b.png` / `cmd 123`） /
      行首孤立标点 / 说话人残留 / 未解析插入宏·占位符
  [W] 主角名未出现 / 空行 / 超长行 / 重复行 / 非日文字符 / 标点健全性（含「台词引号内
      末句不写。」的引擎判据登记 `#@no-final-period`，见 --allow 说明）/ 半角引号 /
      含拉丁字母 `[a-zA-Z]`（错误指示器：逐行判定 原文/脚本残留/控制码；--allow 可豁免原文行） /
      半角标点(U+FF61-FF65 ｡｢｣､･——可能是原文用字)
"""
import argparse
import collections
import io
import re
import sys
import os
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


def check(path: str, names, maxlen: float, quiet: bool, allow=(), inline_name=False,
          dual=False, expect_dual=False, report=None, engine=None, init_charset=False):
    engine = engine or {}   # `#@` 声明集合；未传时为 None，直接 .get() 会崩（2026-10-27 回归抓到）
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8-sig', 'replace')
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    err, warn = [], []
    # ---- 白名单（2026-10-20 薄桜鬼 遊戯録 NS）----
    # 只豁免两条**形态类**判据的命中行：①独立`【…】`行被误判说话人残留（实为 0x4C0 扉文/章題カード，
    # 名札是另一个 op 0x4BC，已整体丢弃）；②「行首「未闭合」实为原文跨框断引号（源缺陷，不改写）。
    # 校验方式＝逐行精确匹配，且白名单行必须在成品中存在；不影响其他判据。
    ALLOW = {l.rstrip('\r') for l in allow}
    ENGINE = dict(engine or {})

    # ---- 语种判定（2026-10-20）----
    # 本器判据以日文正文为前提。PC-EN 作品（正文全英文，假名/汉字占比≈0）里
    # 「行首 . …」「全篇 0 个句号」等属**口径不适用**，不是解码错：
    #   `...` 独立成行＝英文省略号台词；英文用 `.` 收句、`"` 引号。
    # 故当假名+汉字占比 < 1% 时：句号健全性整条跳过、行首孤立标点由 [E] 降 [W]。
    # 形态类判据（BOM/CR/U+FFFD/〓/控制符/半角假名/PUA/引号配对/说话人残留）不受影响。
    _cjk = sum(1 for ch in text if '\u3040' <= ch <= '\u30ff' or '\u4e00' <= ch <= '\u9fff')
    is_en = len(text) > 0 and _cjk < len(text) * 0.01

    # ---- 形态 ----
    if not raw.startswith(b'\xef\xbb\xbf'):
        err.append('BOM 缺失（应为 UTF-8 with BOM）')
    ncr = raw.count(b'\r')
    if ncr:
        err.append('出现 CR ×%d（必须纯 LF）' % ncr)
    for label, pat, sep in (('U+FFFD（解码失败）', None, FFFD),
                            ('`〓` 占位符', None, GETA)):
        # `〓` 与半角假名同属形态类判据：白名单行（人工核实过的原文用字）豁免。
        # 实例：Panic Palette L21541 是原文的「记号连打」演出
        # 「！！！！　※◆＄〒◎☆♂仝＊＠〓〆♪＜∑」，源字节 0x81AC＝U+3013。
        if sep is GETA:
            c = sum(l.count(sep) for l in lines if l not in ALLOW)
        else:
            c = text.count(sep)
        if c:
            err.append('%s ×%d' % (label, c))
    c = len(C0_BAD.findall(text))
    if c:
        err.append('控制符(C0) ×%d' % c)
    # 半角假名：按行判定，便于 --allow 豁免「原文颜文字 o(･ﾛ･)o」这类真实用字
    hw_lines = [l for l in lines if HALFWIDTH_KANA.search(l) and l not in ALLOW]
    if hw_lines:
        err.append('半角假名 ×%d（疑「首字节损坏」化け）: %s'
                   % (sum(len(HALFWIDTH_KANA.findall(l)) for l in hw_lines),
                      hw_lines[0][:30]))
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
    quote_text = '\n'.join(l for l in lines
                           if not (KAOMOJI & set(l)) and l not in ALLOW)
    # ★ 双版对照（`A,B,C,ABC`，用户 2026-10-22）：「段行」天生是句子的一段
    #   ⇒ 段行可只开不闭（`「…@次段…」`）、合并行才闭合；此时不配对/行首未闭合**属预期**，
    #   降为 [W] 并打印计数（差值须能归因到源缺陷或段切分，由人核对），不是解码错。
    for a, b in (('「', '」'), ('『', '』'), ('（', '）'), ('(', ')')):
        ca, cb = quote_text.count(a), quote_text.count(b)
        if ca != cb:
            (warn if (dual or engine.get('open-quote')) else err).append(
                '引号不配对 %s=%d / %s=%d%s'
                % (a, ca, b, cb, '（双版对照：段行可半闭，合并行闭合；差 %+d 需归因）' % (cb - ca) if dual else ''))
    # 行中已闭合的正常；只报真正不均衡的行。
    openq = [l for l in lines if l.startswith('「') and l.count('「') > l.count('」')
             and l not in ALLOW]
    if openq:
        (warn if (dual or engine.get('open-quote')) else err).append(
            '行首「未闭合 ×%d%s: %s'
            % (len(openq), '（双版对照：段行预期）' if dual else '（行被吞/断行）',
               ' | '.join(l[:30] for l in openq[:3])))

    # ---- 脚本 / 资源残留（2026-10-22 用户以 `[a-zA-Z]` 检索发现）----
    # 进正文的 ASCII 未必都是错：英文台词、厂牌/乐队（聖飢魔ii）、CM/DVD/Gパン、ml、
    # 颜文字 o(･ﾛ･)o、『KANE DE BOO』都属原文。真正要抓的是**脚本/资源/调试串**：
    #   party_chiriko／party_hotohori（分支资源标签）、`:ld_n 8:`（内联控制码）、
    #   `if 0821kei0-1通過 == 0 next00`（脚本代码）、`maki/maki_t_001`（资源路径）。
    RESIDUE = [
        (re.compile(r'^[a-z][a-z0-9]*_[a-z0-9_]+$'), '资源/分支标签'),
        (re.compile(r':[A-Za-z_][A-Za-z0-9_]*(?:\s[^:」』]*)?:'), '内联控制码'),
        (re.compile(r'^\s*(?:if|goto|gosub|resume|lsp|csp|mov|textclear)\b.*$'), '脚本代码'),
        (re.compile(r'[A-Za-z0-9_]+/[A-Za-z0-9_.]+\.(?:png|bmp|jpg|gif|wav|ogg|mp3)',
                    re.I), '资源路径'),
        (re.compile(r'^\s*[A-Za-z_]\w*\s+\d[\d,]*\s*$'), '命令+参数'),
        # 带目录前缀的资源名：`|52/FUR_00270.`（うみねこ 立绘/表情码，2026-10-24 用户发现，
        # 旧规则因"扩展名是句点而非 .png"且嵌在行首而全部漏检）
        (re.compile(r'\|[A-Za-z0-9]{1,10}/[A-Za-z0-9_]{1,24}\.?'), '目录号+资源码'),
        # 整行的大写下划线资源名：FUR_00270 / KIN_A11 之类
        (re.compile(r'^[A-Z][A-Z0-9]*_[A-Z0-9_]+$'), '大写资源代号'),
    ]
    res = [(l, k) for l in lines if l not in ALLOW
           for rgx, k in RESIDUE if rgx.search(l)]
    if res:
        byk = {}
        for l, k in res:
            byk.setdefault(k, []).append(l)
        err.append('脚本/资源残留 ×%d（%s）: %s'
                   % (len(res), '／'.join('%s %d' % (k, len(v)) for k, v in byk.items()),
                      ' | '.join(res[i][0][:28] for i in range(min(3, len(res))))))

    # ---- 内联标记残留（2026-10-22 用户发现 `<fs 75>…</fs>` 混进正文）----
    # 引擎富文本（字号/颜色/字体）必须在成行前剥净；残留即解析未清。
    MARKUP = re.compile(r'</?[A-Za-z][^>]{0,24}>')
    mk = [(i, l) for i, l in enumerate(lines, 1) if MARKUP.search(l) and l not in ALLOW]
    if mk:
        err.append('内联标记残留 ×%d 行（如 %s）: L%d %s'
                   % (len(mk), '、'.join(sorted({m.group(0) for m in
                                                 (MARKUP.search(x[1]) for x in mk)})[:4]),
                      mk[0][0], mk[0][1][:30]))

    # ---- 含拉丁字母（`[a-zA-Z]` 指示器；用户 2026-10-22 指定为错误探针）----
    # 不是「一有就错」：英文台词/歌词、厂牌乐队（聖飢魔ii）、CM/DVD/ml、颜文字都属原文。
    # 但**每一个含字母的行都必须被人眼判过一次**——三类：①原文 ②脚本/资源残留 ③控制码。
    # 上面 RESIDUE 已把 ②③ 判 E；这里兜住剩下的，给行号当待查清单。
    asc = [(i, l) for i, l in enumerate(lines, 1)
           if re.search(r'[A-Za-z]', l) and l not in ALLOW]
    if asc:
        warn.append('含拉丁字母 ×%d 行（须逐行判定：①原文 ②脚本/资源残留 ③控制码；'
                    '行号 %s…）: %s'
                    % (len(asc), ','.join(str(x[0]) for x in asc[:8]),
                       ' | '.join(x[1][:26] for x in asc[:3])))

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
    leadp = [l for l in lines if l[:1] in LEAD_PUNCT and l not in ALLOW]
    if leadp:
        msg = ('行首孤立标点 ×%d（前文被切/源数据分页）: %s'
               % (len(leadp), ' | '.join(l[:30] for l in leadp[:3])))
        if is_en:
            warn.append(msg + '（英文作品：`...` 独立成行为省略号台词，非切行）')
        else:
            err.append(msg)

    # ---- 标点健全性（2026-10-12）----
    # 判据＝「句号 ≈ 行数量级」；三重拦截（计数 0 / 行尾 0 / 远少于顿号）。
    # 起因：アンジェリーク ルトゥール 句号写在 cp932 0x8140 槽 ⇒ 被当全角空格清洗。
    # ★ 例外（2026-10-22 令嬢探偵）：日式 ADV 惯例「台词引号内末句不写。」——正文每块
    #   ＝[0x012c]…[0x012d]（＝字形槽 300/301「」），故**块尾无句号而块内句号正常**。
    #   该情形与「行尾标点被清洗」在聚合计数上无法区分 ⇒ 须**逐作举证**后在 allow 文件
    #   登记 `#@no-final-period: <证据要点>`，判据降为 [W]（数字照打，不静默吞掉）。
    if len(lines) >= 300 and not is_en:
        n_period = text.count('。')
        n_comma = text.count('、')
        n_end_period = sum(1 for l in lines if l.endswith('。'))
        # 行尾「其他」收束标点：用来区分「行尾清理生效」与「只有句号被清」
        n_end_other = sum(1 for l in lines if l[-1:] in ('、', '…', '‥', '！', '？', '」', '』', '）'))
        if n_period == 0:
            # 2026-10-24 拡張：`#@no-final-period` 登记后，0 个数同样降 W（数字照打）。
            # 前提＝该作全篇以「框」断句、句末根本不写句号；举证口径同下行。
            msg = ('全篇 0 个句号「。」（%d 行；行尾其他收束标点 %d 行）'
                   % (len(lines), n_end_other))
            if ENGINE.get('no-final-period'):
                warn.append(msg + '—— 已登记引擎判据 `#@no-final-period`：%s'
                            % ENGINE['no-final-period'])
            else:
                err.append(msg + '—— 疑句号被清洗（实例：写在 cp932 '
                           '0x8140 槽 ⇒ 解出全角空格后被当填充删掉）')
        elif n_end_period == 0:
            msg = ('行尾 0 个句号「。」（全篇 %d 个；行尾其他收束标点 %d 行）'
                   % (n_period, n_end_other))
            if ENGINE.get('no-final-period'):
                warn.append(msg + '—— 已登记引擎判据 `#@no-final-period`：%s'
                            % ENGINE['no-final-period'])
            else:
                err.append(msg + '—— 疑行尾标点被清洗（若确为原文：先在报告 §品检 举证'
                                 '「块内句号正常／块尾其他标点齐全／非分页切断」，'
                                 '再在 allow 文件登记 `#@no-final-period: 证据要点`）')
        elif n_period < len(lines) * 0.05:
            warn.append('句号「。」仅 %d 个 / %d 行 —— 比例偏低，请人工确认' % (n_period, len(lines)))
        if n_period and n_comma > n_period * 5:
            warn.append('顿号「、」%d 远多于句号「。」%d（>5×）—— 疑句号丢失' % (n_comma, n_period))

    # ---- 说话人残留 ----（收紧由来见 00b-pitfall-deliver.md）
    HIRA_CHK = re.compile(r'[\u3040-\u309f]')
    lc = collections.Counter(lines)
    plate = [l for l in lines
             if NAME_PLATE.match(l) and lc[l] >= 2
             and not HIRA_CHK.search(l.strip('!！')) and l not in ALLOW]
    # ★ 例外（2026-10-20 自律機動戦車イヅナ）：独立 `【…………………………】`／`【・・・・・・・・・・！】`
    #   一类**括号内全为符号**的行是原文的「无言」演出上屏（正文参数位，非说话人），
    #   判据＝括号内无假名/汉字/拉丁数字，全部字符落在 ALLOWED_SYM。名札必有文字。
    _INNER = re.compile(r'^[!！]?【(.*)】$')
    def _is_fx(l):
        m = _INNER.match(l)
        return bool(m.group(1)) and all(ch in ALLOWED_SYM for ch in m.group(1))
    fx = [l for l in plate if _is_fx(l)]
    plate = [l for l in plate if not _is_fx(l)]
    if fx:
        warn.append('符号のみ括弧行（无言演出，保留） ×%d: %s' % (len(fx), ' | '.join(fx[:3])))
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
        if rest[:1] in ('', '「', '『', '（', '(', ' ', '\u3000') and l not in ALLOW:
            pre.append(l)
    if pre:
        if inline_name:
            # ★ 正文内名札（无独立名字窗）——2026-10-21 ガーネット・クレイドル PC（GsWin）：
            #   引擎无 name 命令、无 SYSNAMEWND 素材，名字以 `#F【名】#F\n` 直接印在正文框首行
            #   ⇒ 按 `S6-lines-names.md` 的三条形态判据属「正文内名札」，保留并接同行。此开关默认关闭。
            if not quiet:
                print('  [i] 行首【名】＋正文 ×%d（--inline-name：正文内名札，保留）' % len(pre))
        else:
            err.append('行首【名】＋正文 ×%d: %s' % (len(pre), ' | '.join(l[:30] for l in pre[:3])))
    pre2 = [l for l in lines
            if NAME_PREFIX_COLON.match(l)
            and re.search(r'[ぁ-んァ-ヶ一-龯]', NAME_PREFIX_COLON.match(l).group(0))
            # ★ 字段标签一律放行（2026-10-17 アルコバレーノ! ポータブル 邮件表：
            #   `＞意外だな送信者：室田　要…` / 书信 `注意：`・`追伸：`）——是正文的字段名，
            #   不是说话人名札残留；与 00b「前綴是句读/记号/非文字 ⇒ 是正文」同源。
            # ★ 章节标题 / 扉文（`第一幕：ミフターフ１日目`，ガーネット・クレイドル 2026-10-17）同理放行
            # ★ ブログ/掲示板系のフィールド名（2026-10-20 うたプリ Debut：`コメント：…` が
            #   本文内ラベルなのに名札扱いされた）も放行。
            and not re.search(r'送信者|受信者|件名|宛先|差出人|本文|注意|追伸|ＰＳ|Ｑ|Ａ'
                              r'|コメント|返信|投稿者|作成者|タイトル|日時|件名'
                              r'|日程|予定|場所|日付|時刻',   # 掲示/手紙のフィールド名（2026-10-22 楽園男子 `日程：十二月十三日、十四日`）
                              NAME_PREFIX_COLON.match(l).group(0))
            and not re.search(r'^[第＃#]?[0-9一二三四五六七八九十０-９]{0,3}[幕章話節]',
                              NAME_PREFIX_COLON.match(l).group(0))
            # ★ 时刻（`4:00pm`／`5:56pm`）与 `No.2` 之类：冒号后紧跟数字 ⇒ 是正文
            #   （2026-10-18 Confidential Money：8DF4=':' 半角冒号，误报 11 行）
            and not re.match(r'.{0,8}[0-9０-９][：:][0-9０-９]', l)
            # ★ --allow 白名单同样豁免本形态判据（2026-10-22 いっしょにごはん。地图菜单
            #   `街：遊び` / `街：仕事`：0xE7 三槽选项文本，非名札残留）
            and l not in ALLOW]
    if pre2:
        err.append('行首「名前：」×%d: %s' % (len(pre2), ' | '.join(l[:30] for l in pre2[:3])))

    # ---- 主角名 ----
    for nm in names:
        c = text.count(nm)
        if c == 0:
            warn.append('主角名 %r 未出现（疑插入宏被当空控制码丢弃）' % nm)
        elif not quiet:
            print('  [i] 主角名 %r 出现 %d 行' % (nm, sum(1 for l in lines if nm in l)))

    # ---- 版式：单版 / 双版对照（A,B,C,ABC）（2026-10-22 用户要求入品检，防忘）----
    # 检出法：某个正文行逐字等于**紧邻上方 2–4 行**的拼接 ⇒ 这就是对照版的「合并行」。
    # 有合并行 ⇒ 双版对照；没有 ⇒ 单版。两者都必须与 `--dual` 声明一致，
    # 否则引号/重复行的判据会各自误报（单版被按双版放水，或双版被按单版判 E）。
    merged = 0
    for i in range(2, len(lines)):
        cur = lines[i]
        if not cur:
            continue
        for k in (2, 3, 4):
            if i - k < 0:
                break
            parts = lines[i - k:i]
            if cur != ''.join(parts):
                continue
            # 排除巧合同文：`……` + `…………` = `………………` 这类（长度短/单字重复/碎片太短）
            if len(cur) < 10 or len(set(cur)) <= 2:
                break
            if sum(1 for x in parts if len(x) >= 4) < 2:
                break
            merged += 1
            break
    # 阈值：单版作里偶有「某句正好＝上两句拼接」的巧合（ヘタリア 实测 1 处/25,144 行），
    # 故 ≥max(3, 行数×0.1%) 才算双版；1–2 处只当「疑似」提示人工看一眼。
    # 例外（2026-10-23）：**显式 `--dual` 是人工核过的声明**，优先于比例阈值——
    # 「局部双版」作（如 恋の花咲く百花園 22.8k 行仅 14 框需对照，占 0.06%）比例永远过不了线，
    # 但它确实是双版（源里 `\c` 段间等待）。故 dual 声明 + merged≥1 ⇒ 认双版；
    # merged==0 时仍按下面第 355 行报 E（声明与结构不符）。
    is_dual = merged >= max(3, len(lines) * 0.001)
    if dual and merged >= 1:
        is_dual = True
    if not quiet:
        print('  [i] 版式：%s' % ('双版对照（%d 个合并行＝上方 2–4 段拼接）' % merged
                                 if is_dual else '单版（未达双版阈值；合并行 %d 处）' % merged))
    if merged and not is_dual:
        warn.append('疑似合并行 ×%d（低于双版阈值，多为巧合同文；请确认不是把相邻两句误并）' % merged)
    if dual and not is_dual:
        err.append('`--dual` 声明为双版对照，但未检出足够的合并行（%d 处）；版式不符或合并行被删/被拆' % merged)
    if is_dual and not dual:
        err.append('检出双版对照结构 %d 处但未加 `--dual`（引号类判据会误报；若本作本无双版，'
                   '须查是否把相邻两句误并成一行）' % merged)
    if expect_dual and not is_dual:
        err.append('`--expect-dual`：本作应有双版对照，但未检出足够的合并行（%d 处）' % merged)
    if report:
        try:
            rt = open(report, encoding='utf-8', errors='replace').read()
        except OSError:
            rt = ''
        if not re.search(r'版式[^\n]{0,60}(双版对照|单版|単版)', rt):
            err.append('报告未声明版式（缺「版式：双版对照／单版」这一行）: %s' % report)

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
                       r'|\\[A-Za-z]{1,}'        # `\n` `\c` 型残留控制码
                       # 2026-10-26 新增：改名槽的其它写法（本轮实测漏检过的形态）
                       r'|＆{2,}'                  # 全角＆重复（Honey Vibes 8,756 处）
                       r'|&&'                     # 半角双＆（テミラーナ昵称槽 319 处）
                       r'|\*\*[A-Z]{2,}'           # **AA（スチームプリズン姓槽）
                       r'|#\s*[Nn]ame\[\d+\]'     # #Name[1]（十三支/ラディアンテイル系）
                       r'|\$\{[^}]{1,24}\}'         # ${FirstName}（ビルシャナ）
                       r'|%[a-z][a-z_]{2,}%'      # %name% / %family%
                       r'|<[a-z]{3,12}>')         # <firstname>（スチーム -Beyond-）
    mac = [(i + 1, m.group()) for i, l in enumerate(lines)
           for m in [MACRO.search(l)] if m and l not in ALLOW]
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

    # ---- 非日文字符台账（whitelist；2026-10-26 用户要求）----
    # 由来：MACRO 是「已知形状黑名单」，`%&` / `{GivenName}` / `#R(a,b)` / `<a,b>` / `(#6!=1)` 全漏；
    #      原「非日文字符」检查又 `o < 0x80` 全跳过 ⇒ 所有 ASCII 变量在盲区、且只报 [W]。
    # 做法：把「kana/汉字/CJK标点/全角符号」以外的**每个字符**都进台账，与 per-work 基线比对；
    #      基线里没有的字符 ⇒ [E]（新出现的变量/乱码必须人工过一遍再登记）。
    CJK = lambda ch: (0x3040 <= ord(ch) <= 0x30ff) or (0x3400 <= ord(ch) <= 0x4dbf) \
        or (0x4e00 <= ord(ch) <= 0x9fff) or (0x3000 <= ord(ch) <= 0x303f) \
        or (0xff01 <= ord(ch) <= 0xff60) or (0xffe0 <= ord(ch) <= 0xffee)
    inv = {}
    for i, l in enumerate(lines):
        for ch in l:
            if ch == '\n' or ch == '\r' or CJK(ch):
                continue
            inv.setdefault(ch, []).append(i + 1)
    base_path = os.path.join(os.path.dirname(os.path.abspath(path)), '..', '解析报告', 'allow',
                             os.path.basename(path)[:-4] + '.charset')
    base = None
    if os.path.exists(base_path):
        base = set()
        for l2 in io.open(base_path, encoding='utf-8'):
            l2 = l2.rstrip('\n')
            if l2 and not l2.startswith('#'):
                base.add(l2[0])
    if init_charset:
        os.makedirs(os.path.dirname(base_path), exist_ok=True)
        io.open(base_path, 'w', encoding='utf-8', newline='\n').write(
            '# 非日文字符台账（每行一个字符，首字符生效；人工核对后生成）\n'
            + '\n'.join('%s\t%d' % (ch, len(v)) for ch, v in sorted(inv.items(), key=lambda kv: -len(kv[1])))
            + '\n')
        print('  [i] 非日文字符台账已生成：%s（%d 种）' % (base_path, len(inv)))
    elif base is None:
        err.append('非日文字符台账缺失（%s）；先人工核对非日文字符后用 --init-charset 生成' % os.path.basename(base_path))
    else:
        fresh = {ch: v for ch, v in inv.items() if ch not in base}
        if fresh:
            sample = ', '.join('%r×%d(L%d)' % (ch, len(v), v[0]) for ch, v in
                               sorted(fresh.items(), key=lambda kv: -len(kv[1]))[:8])
            err.append('未备案的非日文字符 ×%d 种：%s' % (len(fresh), sample))
    if inv and not quiet:
        top = ', '.join('%r×%d' % (ch, len(v)) for ch, v in sorted(inv.items(), key=lambda kv: -len(kv[1]))[:12])
        print('  [i] 非日文字符台账 %d 种：%s' % (len(inv), top))

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
    ap.add_argument('--init-charset', action='store_true', help='生成该作的「非日文字符台账」基线（人工核对后使用）')
    ap.add_argument('--allow', help='白名单文件：每行一条精确匹配的正文（仅豁免形态类误报）。'
                                    '另可写 `#@` 引擎判据行登记「聚合类」口径，格式 '
                                    '`#@no-final-period: 证据要点`（本作台词引号内末句不写「。」；另 `#@open-quote: 证据要点`＝本作「句首「」不收尾」风格，引号类判据降 W；'
                                    '须先在报告 §品检 举证：块内句号正常、块尾其他标点齐全、非分页切断）')
    ap.add_argument('--inline-name', action='store_true', help='名札内嵌正文框（无独立名字窗）⇒ 行首【名】＋正文 不算残留')
    ap.add_argument('--dual', action='store_true', help='双版对照（A,B,C,ABC）：段行可半闭引号，引号类判据降为 W')
    ap.add_argument('--expect-dual', action='store_true', help='本作应有双版对照（缺合并行即报 E）')
    ap.add_argument('--report', help='解析报告 md：要求内含「版式：双版对照／单版」声明')
    a = ap.parse_args()
    allow = []
    engine = {}
    if a.allow:
        raw_allow = [l.rstrip('\r') for l in
                     open(a.allow, encoding='utf-8-sig').read().split('\n') if l.strip()]
        # `#@key: 说明` ＝ 引擎级（聚合判据）口径登记，不参与逐行精确匹配。
        for l in raw_allow:
            if l.startswith('#@'):
                k, _, v = l[2:].partition(':')
                engine[k.strip()] = v.strip()
        allow = [l for l in raw_allow if not l.startswith('#@')]
        print('白名单 %d 条 + 引擎判据 %d 条（%s）' % (len(allow), len(engine), a.allow))
    ok = True
    for f in a.files:
        ok &= check(f, a.name, a.maxlen, a.quiet, allow, a.inline_name, a.dual,
                    a.expect_dual, a.report, engine, a.init_charset)
        print()
    print('RESULT:', 'PASS' if ok else 'FAIL(有 ERROR)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
