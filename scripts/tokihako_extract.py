#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
時函 -Time Capsule-  (Ray, 2009 / PC / NScripter)  全文本提取

用法:
    python tokihako_extract.py <游戏app目录> [输出txt] [报告md]

输入:
    <app>/nscript.dat     NScripter 主脚本（整文件 XOR 0x84，cp932）
    <app>/manual/*.htm    取扱説明書（教程/登场人物介绍）
    <app>/readme.htm

输出:
    全文本：一次点击 = 一行（UTF-8 BOM / 纯 LF / 行内换行合并）
    末尾附「取扱説明書（教程）」与「システム表示テキスト（UI）」

NScripter 文本语义（本作 *define 内无 clickstr / linepage）:
    '@'  显示并等待点击（文本框不清除，内容继续向下累加）
    '\\'  显示并等待点击（翻页：清掉之前显示的内容）
    '/'  取消行末换行（与下一行拼接，不等待）
    '_'  取消紧接着的一次等待
    'br' 在文本框内插入一个空行（不等待）
    → 一处 '@' / '\\' = 一次点击 = 一行输出（行内换行合并）。
"""
import os
import re
import sys
import html

XOR_KEY = 0x84

# ------------------------------------------------------------------ 变量默认值
# 游戏中通过 $var 在运行时插入人名/文本片段。分支/玩家输入决定取值，
# 无法唯一确定 → 仅对「脚本内明确定义了默认值」的人物名做替换，其余保留原 token。
VARMAP = {
    "$skyeye": "すかちゃん",          # input 默认值 / 脚本 19563 行显式兜底
    "$morningstar": "もーちゃん",      # input 默认值
    "$angel": "すかちゃん",           # = 選択された天使名（默认按スカイアイ分支）
    "$angel_short": "すか",           # mid $angel_short,$angel,0,2
    "$tomo01": "ト　モ", "$tomo02": "トモくん", "$tomo03": "、トモくん",
    "$tomo04": "トモくん", "$tomo05": "朋", "$tomo06": "トモくん",
    "$tomo07": "トモ", "$tomo08": "トモくん、", "$tomo09": "トモくん",
    "$tomo10": "トモ", "$tomo11": "トモく", "$tomo12": "トモ、くん",
}

_re_ruby = re.compile(r"\(([^()/]{1,16})/([^()/]{1,24})\)")
_re_bang = re.compile(r"![A-Za-z]+[0-9]*")
_re_color = re.compile(r"#[0-9A-Fa-f]{6}")
_re_var = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*")
_re_tok = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_re_quoted = re.compile(r'"([^"]*)"')

# if / notif 条件表达式（用于识别 `if <cond> <正文文本>` 这种尾随文本写法）
_TERM = r'(?:"[^"]*"|[$%?]?[A-Za-z_0-9]+(?:\[[^\]]*\])*|-?\d+)'
_COMP = _TERM + r'\s*(?:==|!=|>=|<=|>|<)\s*' + _TERM
_re_cond = re.compile(
    r'(?:' + _COMP + r'(?:\s*(?:&{1,2}|\|{1,2})\s*' + _COMP + r')*)'
)
_re_nametag = re.compile(r'^#[0-9A-Fa-f]{6}【[^】]*】\s*$')


def is_text_start(rest):
    """判断命令尾随部分是否为画面文本（而非另一条命令）。"""
    if not rest:
        return False
    c = rest[0]
    if c in "@\\/":
        return True
    if c == "\u3000":
        return True
    if ord(c) > 0x2000 and not c.isascii():
        return True
    if _re_color.match(rest):
        return True
    return False

# csel / selgosub 等选项命令
CHOICE_CMDS = {"csel", "sel", "select", "selgosub"}
# 弹出式系统对话框命令（消息串会显示给玩家）
DIALOG_CMDS = {"input", "inputstr", "inputnum", "mesbox", "mesbox2", "textfield"}
# 文本控制 / 刷出点：遇到这些命令先把当前积累的文本作为一个文本框输出
FLUSH_CMDS = {"csel", "sel", "select", "selgosub", "input", "inputstr",
              "inputnum", "mesbox", "mesbox2", "textfield", "textclear",
              "click", "wait", "resettimer"}
# 精灵文字（UI 文本）命令
UI_TEXT_CMDS = {"lsp", "lsph", "strsp", "strsph", "spstr"}


def decode_nscript(path):
    raw = open(path, "rb").read()
    dec = bytes(b ^ XOR_KEY for b in raw)
    return dec.decode("cp932", errors="replace")


_re_selassign = re.compile(r"\b(?:mov|add|sub|mid)\s+(\$(?:select_text|seltext_sp)[1-4])\s*,")
_re_selvar = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*")


def _split_plus(s):
    """按顶层 '+' 切分（忽略引号内的 +）。"""
    parts, cur, inq = [], "", False
    for ch in s:
        if ch == '"':
            inq = not inq
            cur += ch
        elif ch == "+" and not inq:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def eval_rhs(rhs):
    """求值形如  "文字+"..." / $var+"文字"  的右值；含未知标识符则返回 None。"""
    out = []
    for p in _split_plus(rhs):
        if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
            out.append(p[1:-1])
        elif _re_selvar.fullmatch(p) and p in VARMAP:
            out.append(VARMAP[p])
        else:
            return None
    return "".join(out) if out else None


def rhs_of(line, start):
    """取 line[start:] 中第一个引号外 ':' 之前的右值部分。"""
    buf, inq = [], False
    for ch in line[start:]:
        if ch == '"':
            inq = not inq
        if ch == ":" and not inq:
            break
        buf.append(ch)
    return "".join(buf)


def clean(t, sub=None):
    """去掉格式码 / 注音 / 内联命令，替换变量。sub 为 {varname: value} 替换表。"""
    if sub is None:
        sub = VARMAP
    t = re.sub(r"^:s/[^;]*;", "", t)      # 精灵文字绘制参数
    t = _re_ruby.sub(r"\1", t)            # (漢字/よみ) → 漢字
    t = _re_bang.sub("", t)               # !s0 / !d300 ...
    t = _re_color.sub("", t)              # #RRGGBB
    def _sub(m):
        v = sub.get(m.group(0))
        return v if isinstance(v, str) else m.group(0)
    t = _re_var.sub(_sub, t)
    t = t.replace("/", "").replace("\\", "")   # '/'=取消换行；'\\'=字符串内换行(精灵文字)
    return t.strip(" \u3000\t\r")


# ------------------------------ 字符串变量数据流（求各 $var 的默认值 / 当前值） ----
_re_assign = re.compile(r"\b(mov|add)\s+(\$[A-Za-z_][A-Za-z0-9_]*)\s*,")
_re_input_default = re.compile(r'\binput\s+(\$[A-Za-z_][A-Za-z0-9_]*)\s*,\s*"[^"]*"\s*,\s*"([^"]*)"')
_re_input_nodflt = re.compile(r'\b(inputstr|inputnum|getparam|getlog|itoa2?|itoa)\s+(\$[A-Za-z_][A-Za-z0-9_]*)')
UNKNOWN = object()          # 该变量此刻值不确定（运行时计算 / 追加 / 玩家输入）


def scan_assign(line):
    """解析本行对 $var 的赋值 → [(var, value|None=不确定), ...]（按出现顺序）。"""
    res = []
    for m in _re_input_default.finditer(line):
        res.append((m.group(1), m.group(2)))
    for m in _re_assign.finditer(line):
        op, var = m.group(1), m.group(2)
        val = None if op == "add" else eval_rhs(rhs_of(line, m.end()).strip())
        res.append((var, val))
    for m in _re_input_nodflt.finditer(line):
        res.append((m.group(2), None))
    return res


def collect_defaults(lines):
    """每个 $var 的『默认值』= 脚本中首次能静态确定的赋值。返回 (defaults, occ)。"""
    defaults, occ = {}, {}
    for l in lines:
        for var, val in scan_assign(l):
            occ[var] = occ.get(var, 0) + 1
            if var not in defaults and val is not None:
                defaults[var] = val
    return defaults, occ


def classify(s):
    c = s[0]
    if c == "*":
        return "label"
    if c == ";":
        return "comment"
    if c in "~:":
        return "skip"
    if c == '"':
        return "cont"
    if c.isascii() and (c.isalpha() or c == "_"):
        return "cmd"
    return "text"


def first_cmd(s):
    m = _re_tok.match(s)
    return m.group(0) if m else ""


def main():
    app = sys.argv[1] if len(sys.argv) > 1 else "game/app"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "時函 -Time Capsule-_全文本.txt"
    report_path = sys.argv[3] if len(sys.argv) > 3 else None

    lines = decode_nscript(os.path.join(app, "nscript.dat")).split("\n")

    defaults, occ = collect_defaults(lines)
    varval = dict(defaults)                 # 首次赋值 = 默认值
    varval.update(VARMAP)                   # 已知人物名优先

    out = []
    buf = ""

    def flush():
        nonlocal buf
        raw = buf
        t = clean(raw, varval)
        if t:
            out.append(t)
        elif clean(raw, {}):                # 替换后为空但原文有内容 → 退回保留 token
            out.append(clean(raw, {}))
        buf = ""

    def feed(content):
        """按 '@' / '\\' 点击标记切开，每段 = 一次点击 = 一行。"""
        nonlocal buf
        content = content.replace("_@", "").replace("_\\", "")
        parts = re.split(r"[@\\]", content)
        for k, p in enumerate(parts):
            if p and all(ord(ch) < 128 for ch in p) and len(p) <= 3:
                p = ""                      # 孤儿 ASCII 残留（如 '？\4' 的 '4'）
            buf += p
            if k != len(parts) - 1:
                flush()

    def emit_select(s):
        """本作自研选择系统：mov $select_textN,"选项" / mov $seltext_spN,"提问" 后 gosub *select。"""
        items = []
        for m in _re_selassign.finditer(s):
            var = m.group(1)
            rhs = eval_rhs(rhs_of(s, m.end()).strip())
            if rhs is None:
                continue
            t = clean(rhs, varval)
            if t:
                items.append((var, t))
        if not items:
            return False
        flush()                             # 先把此前积累的正文文本框输出
        for var, t in items:
            if var.startswith("$seltext_sp"):
                # 提示语常与正文重复（同框折行被拆）→ 已出现过则跳过
                if any(t in ln for ln in out[-40:]):
                    continue
                if t.startswith("【") and t.endswith("】"):
                    continue
            out.append(t)
        return True

    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].lstrip("\t ")
        if not s:
            i += 1
            continue
        kind = classify(s)

        if kind not in ("label", "comment"):
            # 更新字符串变量数据流（最近一次赋值）；已知人物名（VARMAP）不被覆盖
            for var, val in scan_assign(s):
                if var not in VARMAP:
                    varval[var] = val
            emit_select(s)

        if kind == "label":
            # 进入新标签 = 新的显示上下文：分支 / 随机台词互为互斥，
            # 若当前这一段还没被点击标记收尾，就在这里收尾，
            # 避免线性扫描把互斥分支（如黑杰克 *kuro_wdNN）拼成一行。
            if buf:
                flush()
            i += 1
            continue

        if kind in ("comment", "skip", "cont"):
            i += 1
            continue

        if kind == "cmd":
            tok = first_cmd(s)
            low = tok.lower()

            if low in ("if", "notif"):
                tail = s[len(tok):].lstrip()
                m = _re_cond.match(tail)
                if m:
                    rest = tail[m.end():]
                else:
                    m2 = re.match(r"\S+\s*(.*)$", tail)
                    rest = m2.group(1) if m2 else ""
                rest = re.split(r":(?=[A-Za-z_])", rest, maxsplit=1)[0].lstrip()
                if is_text_start(rest) and not _re_nametag.match(rest):
                    feed(rest)          # `if <条件> <正文>` 这类行尾随文本
                i += 1
                continue

            if low in CHOICE_CMDS:
                flush()
                j = i
                strs = []
                while j < n:
                    ln = lines[j].lstrip("\t ")
                    mm = _re_quoted.findall(ln)
                    if j == i:
                        strs += mm
                    elif ln.startswith('"'):
                        strs += mm
                    else:
                        break
                    if not ln.rstrip().endswith(","):
                        j += 1
                        break
                    j += 1
                for t in strs:
                    t = clean(t, varval)
                    if t:
                        out.append(t)
                i = j
                continue

            if low in DIALOG_CMDS:
                flush()
                mm = _re_quoted.findall(s)
                if mm:
                    t = clean(mm[0], varval)   # 只取第一段（提示语），忽略预填默认值/标题
                    if t and any(ord(ch) > 0x2000 for ch in t):
                        out.append(t)
                i += 1
                continue

            if low in FLUSH_CMDS:
                flush()
            i += 1
            continue

        # ---- 文本行 ----
        feed(s.rstrip("\r"))
        i += 1
    flush()

    # ---------------------------------------------------------- 取扱説明書（教程）
    manual_sections = [
        ("はじめに・免責事項・著作権", ["manual/top.htm"]),
        ("ストーリー", ["manual/story.htm"]),
        ("登場人物紹介", ["manual/chara.htm"]),
        ("ゲームの進め方", ["manual/use.htm"]),
        ("システム紹介", ["manual/works_f6.htm"]),
        ("セットアップ", ["manual/setup.htm"]),
        ("サポート", ["manual/supp.htm"]),
        ("スタッフ／謝辞", ["manual/staff.htm"]),
    ]

    def html_text(fp):
        raw = open(fp, "rb").read()
        try:
            t = raw.decode("cp932")
        except Exception:
            t = raw.decode("utf-8", errors="replace")
        t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
        t = re.sub(r"(?i)<br\s*/?>", "\n", t)
        t = re.sub(r"(?i)</(p|div|tr|h[1-6]|li|table)>", "\n", t)
        t = re.sub(r"<[^>]+>", "", t)
        t = html.unescape(t)
        t = t.replace("\u00a0", " ")
        t = re.sub(r"[ \t\u3000]+", " ", t)
        lines_ = [x.strip() for x in t.split("\n")]
        lines_ = [x for x in lines_ if x]
        return "\n".join(lines_)

    manual_out = []
    for title, files in manual_sections:
        chunks = []
        for f in files:
            p = os.path.join(app, f)
            if os.path.exists(p):
                chunks.append(html_text(p))
        if chunks:
            manual_out.append("[■ " + title + "]")
            manual_out.append("\n".join(chunks))

    manual_extra = []
    for f in ["ご購入ありがとうございました.txt", "../ご購入ありがとうございました.txt"]:
        p = os.path.join(app, f)
        if os.path.exists(p):
            raw = open(p, "rb").read()
            try:
                t = raw.decode("cp932")
            except Exception:
                t = raw.decode("utf-8", errors="replace")
            t = "\n".join(x.strip() for x in t.split("\n") if x.strip())
            if t:
                manual_extra.append(t)

    # ------------------------------------------------- システム表示テキスト（UI）
    ui = []
    seen = set()
    for l in lines:
        s = l.lstrip("\t ")
        if not s or not (s[0].isascii() and (s[0].isalpha() or s[0] == "_")):
            continue
        tok = first_cmd(s)
        if tok.lower() not in UI_TEXT_CMDS:
            continue
        for raw_s in _re_quoted.findall(s):
            t = raw_s.replace("\\", "\n")
            t = re.sub(r"^:s/[^;]*;", "", t)     # 去掉 :s/... 绘制参数
            t = _re_color.sub("", t)
            t = _re_bang.sub("", t)
            t = "\n".join(x.strip(" \u3000") for x in t.split("\n"))
            t = t.strip()
            if t and any(ord(ch) > 0x2000 for ch in t) and t not in seen:
                seen.add(t)
                ui.append(t)

    # ------------------------------------------------------------------ 写文件
    blocks = ["\n".join(out)]
    if manual_out or manual_extra:
        blocks.append("■ 取扱説明書（教程）\n\n" + "\n\n".join(manual_out + manual_extra))
    if ui:
        blocks.append("■ システム表示テキスト（スプライト文字／設定ヘルプ等）\n\n" + "\n".join(ui))

    text = "\n\n".join(blocks)
    with open(out_path, "wb") as f:
        f.write(b"\xef\xbb\xbf" + text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))

    # --------------------------------------------------- 变量默认值统计（供报告）
    used = {}
    for l in lines:
        s = l.lstrip("\t ")
        if not s:
            continue
        if classify(s) == "text" or _re_selassign.search(s):
            for m in _re_var.finditer(l):
                used[m.group(0)] = used.get(m.group(0), 0) + 1
    var_rows = []
    for v, c in sorted(used.items(), key=lambda kv: (-kv[1], kv[0])):
        if _re_selassign.search("mov %s," % v):    # 选项系统内部变量，不算作文本变量
            continue
        if v in VARMAP:
            d = VARMAP[v] + "（已知人物名，直接替换）"
        elif v in defaults:
            d = defaults[v] if defaults[v] != "" else "（空串）"
        else:
            d = "（无静态默认：运行时计算 / 分支赋值）"
        var_rows.append((v, c, d))

    n_main = len(out)
    n_manual_sec = sum(1 for x in manual_out if x.startswith("[■ "))
    print("main text lines:", n_main)
    print("ui text lines:", len(ui))
    print("manual sections:", n_manual_sec)
    print("written:", out_path, os.path.getsize(out_path), "bytes")

    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 時函 -Time Capsule- 解析报告\n\n")
            f.write("| 项目 | 值 |\n|---|---|\n")
            f.write("| 引擎 | NScripter（nscript.dat，整文件 XOR 0x84，cp932） |\n")
            f.write("| 安装包 | Inno Setup 5.2.3（TC_setup.exe，innoextract 解包） |\n")
            f.write("| 主文本行数（一次点击 = 一行） | %d |\n" % n_main)
            f.write("| システム表示テキスト（スプライト文字/UI） | %d |\n" % len(ui))
            f.write("| 取扱説明書章节 | %d |\n" % n_manual_sec)
            f.write("\n## 说明\n")
            f.write("- `@` = 显示并等待点击（不清框）；`\\` = 显示并等待点击（翻页清框）；\n")
            f.write("  `/` 取消换行；`_` 取消一次等待；`br` 框内空行。\n")
            f.write("- 输出规则：**一次点击 = 一行**（在 `@` / `\\` 两处切分），行内换行合并。\n")
            f.write("- 另：**进入新 `*label` 时结页**（若该段尚未被点击标记收尾）——\n")
            f.write("  分支 / 随机台词互为互斥（如黑杰克小游戏的 `*kuro_wdNN` 每条显示后 `goto *mor_libend`\n")
            f.write("  = `delay 800:textclear`），线性扫描若不结页会把几十条互斥台词并成一行。\n")
            f.write("  此规则仅影响 20 处、净增 54 行；最长行由 589 字降到 187 字。\n")
            f.write("- 选项：`csel`/`selgosub`（少量）＋本作自研选择系统 `mov $select_textN,\"…\"` → `gosub *select`；\n")
            f.write("  提问横幅 `mov/add $seltext_spN,\"…\"` 一并收录（与正文重复者跳过）。\n")
            f.write("- 变量：两步解析 ——\n")
            f.write("  ① 脚本内已明确的人物名（$skyeye→すかちゃん、$morningstar→もーちゃん、$angel→すかちゃん、$tomo01–12→トモ 系）直接替换；\n")
            f.write("  ② 其余 `$var` 用『最近一次赋值』数据流解析（含默认值 = 脚本首次可静态求值赋值，如 $skyeye 的 input 默认值）；\n")
            f.write("     一旦遇到运行时计算（itoa/getparam/追加/玩家输入）即转为不确定 → 保留原 token。\n")
            f.write("     输出中凡无法静态确定者（运行时 itoa/getparam/玩家输入）保留 token，本作仅 9 行。\n")
            f.write("\n## 字符串变量默认值一览\n\n")
            f.write("> 「默认值」= 脚本中该 `$var` 首次可静态求值的赋值（初始化）。\n")
            f.write("> 输出取的是**该处之前最近一次赋值**；下表列出脚本中所有出现过的文本变量。\n\n")
            f.write("| 变量 | 脚本中出现次数 | 默认值（首次静态赋值） |\n|---|---|---|\n")
            for v, c, d in var_rows:
                f.write("| `%s` | %d | %s |\n" % (v, c, d))
            f.write("- 文本落位：`nscript.dat` 为唯一剧本源（219,155 行）；`arc*.nsa` 仅为图像/音频（无文本）。\n")
            f.write("  一次点击 = 一个文本框 = 一行；行内换行合并；保留日文原文；不加说话人前缀。\n")
            f.write("\n## 输出文件结构\n")
            f.write("1. 正文/选项/提问（按脚本顺序，一次点击一行）\n")
            f.write("2. `■ 取扱説明書（教程）` — manual/*.htm 共 8 节：")
            f.write("／".join(x[1:-1] for x in manual_out if x.startswith("[■ ")) + "\n")
            f.write("3. `■ システム表示テキスト（スプライト文字／設定ヘルプ等）` — lsp/lsph/strsp/strsph 内日文串（去重）\n")
            f.write("\n## 复现\n")
            f.write("```\n")
            f.write("7z x \"[PC-JP]時函 -Time Capsule-.rar\" -o rar\n")
            f.write("innoextract -e -d game \"rar/時函 -Time Capsule-/TC_setup.exe\"\n")
            f.write("python scripts/tokihako_extract.py game/app \"時函 -Time Capsule-_全文本.txt\"\n")
            f.write("```\n")
        print("report:", report_path)


if __name__ == "__main__":
    main()
