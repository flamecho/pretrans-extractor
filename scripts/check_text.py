#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前自检（品检）—— 日文游戏剧本文本提取产物的通用检查器。

用法:
    python check_text.py OUT.txt [OUT2.txt ...]
        [--name 百合子 --name コノエ]   # 主角名「出现性」自检（至少一个应命中）
        [--maxlen 200]                 # 超长行阈值（默认 200 显示宽度）
        [--quiet]                      # 只输出 FAIL/WARN 行

退出码: 0 = 无 ERROR（WARN 不阻断）；1 = 有 ERROR。

检查项（全部来自历史「返工/被用户追加指出」的真实问题，别删）:
  [E] 文件形态      BOM 缺失 / 出现 CR / U+FFFD / `〓`(U+3013) / 控制符(C0, 除 \\n)
  [E] 半角假名      U+FF61-FF9F 残留（多为「双字节字首字节损坏」的化け，不是合法原文）
  [E] 私用区 PUA    U+E000-F8FF 残留（未映射字形槽）
  [E] 引号不配对    「」『』（）数量不等，或行首「未以」收尾（= 断行/行被吞）
  [E] 说话人残留    独立名字札行 `【…】`；行首 `【…】`+正文；行首 `名前：`/`名前「`
  [W] 主角名缺失    --name 指定却一次都没出现（多半是「主角名插入宏」被当空控制码丢了）
  [W] 空行          出现空行（本规范要求一行一文本，不留空行）
  [W] 超长行        超过 --maxlen 显示宽（可能是「多次点击被并成一行」）
  [W] 重复行        相邻完全相同的行（可能是日志载体/重复提取）
  [W] 非日文字符    拉丁/西里尔/希腊字母等（须逐条上下文复核，见 SKILL §3.5）
  [i] 统计          行数 / 字节 / 最长行 / 显示宽中位数

显示宽度: 全角=1、半角=0.5（近似日文文本框计数）。
"""
import argparse
import re
import sys
import unicodedata

C0_BAD = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
HALFWIDTH_KANA = re.compile(r'[\uFF61-\uFF9F]')
PUA = re.compile(r'[\uE000-\uF8FF]')
FFFD = '\ufffd'
GETA = '\u3013'          # 〓（历史遗留占位符）
NAME_PLATE = re.compile(r'^[!！]?【[^】]{1,20}】$')          # 独立名字札行
NAME_PREFIX_BRACKET = re.compile(r'^[!！]?【[^】]{1,20}】')   # 行首【名】＋正文
# 行首 名前：/名前「。前缀里出现句读符号（。、！？…）说明不是「名字札」而是正文
# （Norn9 的「人名。ジョブ：…」人物卡曾被此规则误报 → 2026-10-10 收紧）
NAME_PREFIX_COLON = re.compile(r'^[^\s。「、！？…‥（(【]{1,8}[：:]')
# 允许的常见「非假名/汉字」符号（日文正文里的正当字符）
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
    if 0x3040 <= o <= 0x30FF:   return True     # かな・記号
    if 0x4E00 <= o <= 0x9FFF:   return True     # 漢字
    if 0x3000 <= o <= 0x303F:   return True     # 和文約物
    if 0xFF01 <= o <= 0xFF60:   return True     # 全角形
    if 0x2010 <= o <= 0x203B:   return True     # 約物
    if 0x2190 <= o <= 0x21FF:   return True
    if 0x2460 <= o <= 0x24FF:   return True
    if 0x2500 <= o <= 0x25FF:   return True
    if o in (0x0100, 0x00D7, 0x00F7): return True
    return False


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
    c = len(PUA.findall(text))
    if c:
        err.append('私用区 PUA ×%d（未映射字形槽）' % c)

    # ---- 引号配对 ----
    for a, b in (('「', '」'), ('『', '』'), ('（', '）'), ('(', ')')):
        ca, cb = text.count(a), text.count(b)
        if ca != cb:
            err.append('引号不配对 %s=%d / %s=%d' % (a, ca, b, cb))
    # 行首「」但引号在行中已闭合（如「…」と、…）は正常。真に不均衡な行のみ報じる。
    openq = [l for l in lines if l.startswith('「') and l.count('「') > l.count('」')]
    if openq:
        err.append('行首「未闭合 ×%d（行被吞/断行）: %s'
                   % (len(openq), ' | '.join(l[:30] for l in openq[:3])))

    # ---- 说话人残留 ----
    plate = [l for l in lines if NAME_PLATE.match(l)]
    if plate:
        err.append('独立名字札行 ×%d: %s' % (len(plate), ' | '.join(plate[:3])))
    pre = [l for l in lines if NAME_PREFIX_BRACKET.match(l) and not NAME_PLATE.match(l)]
    if pre:
        err.append('行首【名】＋正文 ×%d: %s' % (len(pre), ' | '.join(l[:30] for l in pre[:3])))
    pre2 = [l for l in lines if NAME_PREFIX_COLON.match(l)]
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
