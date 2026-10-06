#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ときたま！～時函玉手箱～  (Ray, 2010 / PC / NScripter)  全文本提取

用法:
    python tokitama_extract.py <游戏app目录> [输出txt] [报告md]

输入:
    <app>/nscript.dat                     NScripter 主脚本（整文件 XOR 0x84，cp932）
    <app>/ときたま！ 取扱説明書.html        取扱説明書（教程；UTF-8）
    <app>/arc.nsa, <app>/arc1.nsa         资源归档（含 kara_type\\*.csv = 空函カラオケ歌詞）

输出（一次点击 = 一行，UTF-8 BOM / 纯 LF / 行内换行合并）:
    1. 正文/选项/提问（按脚本顺序）
    2. ■ 取扱説明書（教程）
    3. ■ システム表示テキスト（スプライト文字／設定ヘルプ等）
    4. ■ 空函 -Typing Karaoke- 歌詞

NScripter 文本语义（本作 *define 内无 clickstr / linepage）:
    '@'  显示并等待点击（文本框不清除，内容继续向下累加）
    '\\'  显示并等待点击（翻页：清掉之前显示的内容）
    '/'  取消行末换行（与下一行拼接，不等待）
    '_'  取消紧接着的一次等待
    'br' 在文本框内插入一个空行（不等待）
    → 一处 '@' / '\\' = 一次点击 = 一行输出（行内换行合并）。

NSA 归档（本作变体，非标准 "NSAr"）:
    头 6 字节；随后每条:
        name (NUL 结尾) + u8 pad + u32be offset(相对 datastart) + u32be size + u32be size
    datastart = 索引结束后第一字节。
"""
import os
import re
import sys
import struct
import html

XOR_KEY = 0x84

# ------------------------------------------------------------------ 变量默认值
# 游戏中通过 $var 在运行时插入人名/文本片段。分支/玩家输入决定取值，
# 无法唯一确定 → 仅对「脚本内明确定义了默认值」的人物名做替换，其余保留原 token。
VARMAP = {
    "$skyeye": "すかちゃん",          # mov $skyeye,$skyeye_gl；$skyeye_gl 静态默认 "すかちゃん"
    "$morningstar": "もーちゃん",      # mov $morningstar,$morningstar_gl；静态默认 "もーちゃん"
    "$angel": "すかちゃん",           # = 選択された天使名（默认按スカイアイ分支）
    "$angel_short": "すか",           # mid $angel_short,$angel,0,2
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
# 说话人名札模板行（*name / *name2 例程内，$0 = 运行时说话人名）→ 非正文，剔除
_re_nametag_line = re.compile(r'^#[0-9A-Fa-f]{6}【[^】]*】\s*(?:#[0-9A-Fa-f]{6})?\s*$')
# 「大判セリフ／掛け合い」演出：脚本先 `gosub *text_win_shade`（文本框设为不可见），
# 再把说话人名当普通文本行写进正文流（如 `【　椿　】`），随后紧跟台词行、中间无点击标记，
# `*big_words` 用 $seltext_sp1/$seltext_sp2 以大字号 sprite 描画。→ 该名字行视为说话人前缀剔除。
_re_bare_tag = re.compile(r'^【[^】]*】\s*$')
# gaiji（NSFont.dll 自定义字形替换槽）：define 内
#   exec_dll "dll\NSFont.dll/gaiji,騾,sys\heart.png"  → 騾 = ハート图标
GAIJI = {"\u9a3e": "\u2665"}   # 騾(U+9A3E) → ♥


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
    t = re.sub(r"^:[a-z]/[^;]*;", "", t)  # 其它绘制参数 (:a/2; 等)
    t = _re_ruby.sub(r"\1", t)            # (漢字/よみ) → 漢字
    t = _re_bang.sub("", t)               # !s0 / !d300 ...
    t = _re_color.sub("", t)              # #RRGGBB
    def _sub(m):
        v = sub.get(m.group(0))
        return v if isinstance(v, str) else m.group(0)
    t = _re_var.sub(_sub, t)
    t = t.replace("/", "").replace("\\", "")   # '/'=取消换行；'\\'=字符串内换行(精灵文字)
    for k, v in GAIJI.items():
        t = t.replace(k, v)
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


# ------------------------------------------------------------- NSA 归档解析 ----
def read_nsa(path):
    """返回 [(name, data), ...]。本作 NSA 变体，见模块 docstring。"""
    raw = open(path, "rb").read()
    p = 6
    recs = []
    while True:
        e = raw.find(b"\x00", p)
        if e < 0 or e == p:
            break
        name = raw[p:e]
        if any(b < 32 or b > 126 for b in name):
            break
        tail = raw[e + 1:e + 14]
        if len(tail) < 13:
            break
        _pad, off, size, _size2 = struct.unpack(">BIII", tail)
        recs.append((name.decode("ascii"), off, size))
        p = e + 1 + 13
    datastart = p
    return [(n, raw[datastart + o:datastart + o + s]) for n, o, s in recs]


def read_karaoke(app):
    """从 arc*.nsa 收集 kara_type\\*.csv 歌詞。返回 [(filename, [(t, lyric, rub), ...]), ...]。"""
    songs = []
    seen = set()
    for nsa in ("arc.nsa", "arc1.nsa"):
        fp = os.path.join(app, nsa)
        if not os.path.exists(fp):
            continue
        for name, data in read_nsa(fp):
            low = name.lower()
            if not (low.startswith("kara_type") and low.endswith(".csv")):
                continue
            if name in seen:
                continue
            seen.add(name)
            try:
                txt = data.decode("cp932")
            except Exception:
                txt = data.decode("utf-8", errors="replace")
            rows = []
            for line in txt.split("\n"):
                line = line.rstrip("\r")
                if not line.strip():
                    continue
                cells = line.split(",")
                rows.append(cells)
            songs.append((name, rows))
    return songs


def main():
    app = sys.argv[1] if len(sys.argv) > 1 else "game/app"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "ときたま！～時函玉手箱～_全文本.txt"
    report_path = sys.argv[3] if len(sys.argv) > 3 else None

    lines = decode_nscript(os.path.join(app, "nscript.dat")).split("\n")
    lines_src = "\n".join(lines)

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
            # 避免线性扫描把互斥分支拼成一行。
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
        if _re_nametag_line.match(s):       # 说话人名札模板（*name / *name2）→ 非正文
            i += 1
            continue
        if _re_bare_tag.match(s):           # 大判セリフ演出の裸名札 【人名】 → 说话人前缀，剔除
            i += 1
            continue
        feed(s.rstrip("\r"))
        i += 1
    flush()

    # ---------------------------------------------------------- 取扱説明書（教程）
    def html_text(fp, enc):
        raw = open(fp, "rb").read()
        try:
            t = raw.decode(enc)
        except Exception:
            t = raw.decode("utf-8", errors="replace")
        t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
        t = re.sub(r"(?i)<br\s*/?>", "\n", t)
        t = re.sub(r"(?i)</(p|div|tr|h[1-6]|li|table|td)>", "\n", t)
        t = re.sub(r"<[^>]+>", "", t)
        t = html.unescape(t)
        t = t.replace("\u00a0", " ")
        t = re.sub(r"[ \t\u3000]+", " ", t)
        lines_ = [x.strip() for x in t.split("\n")]
        lines_ = [x for x in lines_ if x]
        return "\n".join(lines_)

    manual_out = []
    for f, enc in [("ときたま！ 取扱説明書.html", "utf-8"),
                   ("manual/top.htm", "cp932")]:
        p = os.path.join(app, f)
        if os.path.exists(p):
            manual_out.append("[■ 取扱説明書]")
            manual_out.append(html_text(p, enc))
            break

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
            t = re.sub(r"^:[a-z]/[^;]*;", "", t)  # 去掉 :s/... / :a/... 绘制参数
            t = _re_color.sub("", t)
            t = _re_bang.sub("", t)
            t = "\n".join(x.strip(" \u3000") for x in t.split("\n"))
            t = t.strip()
            if t and any(ord(ch) > 0x2000 for ch in t) and t not in seen:
                seen.add(t)
                ui.append(t)

    # ------------------------------------------- 空函 -Typing Karaoke- 歌詞
    # 脚本中引用的曲目（kara_type\<name>）优先，按引用顺序；其余未引用数据附后。
    ref_order = []
    for m in re.finditer(r"kara_type\\([A-Za-z0-9_\-]+)", lines_src, re.I):
        k = m.group(1).lower()
        if k not in ref_order:
            ref_order.append(k)

    songs = read_karaoke(app)

    def _stem(n):
        return os.path.splitext(os.path.basename(n.replace("\\", "/")))[0].lower()

    songs.sort(key=lambda it: (ref_order.index(_stem(it[0]))
                               if _stem(it[0]) in ref_order else len(ref_order), _stem(it[0])))

    kara_blocks = []
    for name, rows in songs:
        title, credit = "", ""
        lyric_lines = []
        for cells in rows:
            if len(cells) >= 2 and re.fullmatch(r"\d+", cells[0].strip()):
                if not title:
                    # 首行为标题行：time, 曲名, 作詞/作曲
                    title = cells[1].strip()
                    credit = cells[2].strip() if len(cells) >= 3 else ""
                    continue
                rub = cells[2].strip() if len(cells) >= 3 else ""
                if not rub:
                    continue            # フリガナ空 = 游戏内跳过（前奏注记 / おわり 标记等）
                lyric = cells[1].strip()
                if lyric:
                    lyric_lines.append(lyric)
        head = "── %s ──" % name
        tline = "【%s】%s" % (title or _stem(name), credit)
        kara_blocks.append(head + "\n" + tline + "\n" + "\n".join(lyric_lines))

    # ------------------------------------------------------------------ 写文件
    blocks = ["\n".join(out)]
    if manual_out or manual_extra:
        blocks.append("■ 取扱説明書（教程）\n\n" + "\n\n".join(manual_out + manual_extra))
    if ui:
        blocks.append("■ システム表示テキスト（スプライト文字／設定ヘルプ等）\n\n" + "\n".join(ui))
    if kara_blocks:
        blocks.append("■ 空函 -Typing Karaoke- 歌詞\n\n" + "\n\n".join(kara_blocks))

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
    n_kara = len(kara_blocks)
    print("main text lines:", n_main)
    print("ui text lines:", len(ui))
    print("manual sections:", n_manual_sec)
    print("karaoke songs:", n_kara)
    print("written:", out_path, os.path.getsize(out_path), "bytes")

    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# ときたま！～時函玉手箱～ 解析报告\n\n")
            f.write("| 项目 | 值 |\n|---|---|\n")
            f.write("| 引擎 | NScripter（nscript.dat，整文件 XOR 0x84，cp932） |\n")
            f.write("| 安装包 | Inno Setup 5.2.3（tokitama_DL_SETUP.exe，innoextract 解包） |\n")
            f.write("| 主文本行数（一次点击 = 一行） | %d |\n" % n_main)
            f.write("| システム表示テキスト（スプライト文字/UI） | %d |\n" % len(ui))
            f.write("| 取扱説明書章节 | %d |\n" % n_manual_sec)
            f.write("| 空函カラオケ歌詞（曲数） | %d |\n" % n_kara)
            f.write("\n## 说明\n")
            f.write("- `@` = 显示并等待点击（不清框）；`\\` = 显示并等待点击（翻页清框）；\n")
            f.write("  `/` 取消换行；`_` 取消一次等待；`br` 框内空行。\n")
            f.write("- 输出规则：**一次点击 = 一行**（在 `@` / `\\` 两处切分），行内换行合并。\n")
            f.write("- 进入新 `*label` 时结页（若该段尚未被点击标记收尾）——分支 / 随机台词互为互斥，\n")
            f.write("  线性扫描若不结页会把互斥分支拼成一行。\n")
            f.write("- 选项：本作自研选择系统 `mov $select_textN,\"…\"` → `gosub *select`；\n")
            f.write("  提问横幅 `mov/add $seltext_spN,\"…\"` 一并收录（与正文重复者跳过）。\n")
            f.write("- 变量：已知人物名（$skyeye→すかちゃん、$morningstar→もーちゃん、"
                    "$angel→すかちゃん、$angel_short→すか）直接替换；\n")
            f.write("  其余 `$var` 用『最近一次赋值』数据流解析；运行时计算（itoa/getparam/玩家输入）保留原 token。\n")
            f.write("- 文本落位：`nscript.dat` 为唯一剧本源；`arc*.nsa` 内除 `kara_type\\*.csv`（歌詞）外"
                    "均为图像/音频；Lua 文件仅含开发注释（非玩家文本）。\n")
            f.write("- gaiji：`define` 内 `exec_dll \"dll\\NSFont.dll/gaiji,騾,sys\\heart.png\"` → "
                    "字符 `騾`(U+9A3E) 为 NSFont.dll 自定义字形替换槽（心脏图标），输出替换为 `♥`（正文中 2 处）。\n")
            f.write("- 空函カラオケ歌詞取自 `kara_type\\*.csv`（列：时刻ms,歌詞,フリガナ）；脚本共引用 14 曲，"
                    "另有 2 曲数据（`bernarda.csv` / `funi-kura.csv`，为 `_s` 版的加长版）未被脚本引用，一并附于末尾。\n")
            f.write("- 说话人名札模板行（`*name` / `*name2` 例程内 `#RRGGBB【$0】…`，$0 = 运行时说话人名）非正文，已剔除。\n")
            f.write("- 「大判セリフ／掛け合い」演出（`gosub *text_win_shade` + `*big_words`，共 8 处）：脚本把说话人名"
                    "当普通文本行写入正文流（如 `【　椿　】`），与其后台词同属一个文本框；按「不加说话人前缀」约定，"
                    "该裸名札行已剔除（其余对白的人名一律由 `name \"…\",0` 命令设定、本就不进正文）。\n")
            f.write("  一次点击 = 一个文本框 = 一行；行内换行合并；保留日文原文；不加说话人前缀。\n")
            f.write("\n## 输出文件结构\n")
            f.write("1. 正文/选项/提问（按脚本顺序，一次点击一行）\n")
            f.write("2. `■ 取扱説明書（教程）` — ときたま！ 取扱説明書.html\n")
            f.write("3. `■ システム表示テキスト（スプライト文字／設定ヘルプ等）` — lsp/lsph/strsp/strsph 内日文串（去重）\n")
            f.write("4. `■ 空函 -Typing Karaoke- 歌詞` — arc.nsa/arc1.nsa 内 `kara_type\\*.csv` 歌詞"
                    "（剔时间/读音；脚本引用者在前，共 %d 曲）\n" % n_kara)
            f.write("\n## 字符串变量（正文中出现者）\n\n")
            f.write("| 变量 | 出现次数 | 默认值（首次静态赋值） |\n|---|---|---|\n")
            for v, c, d in var_rows:
                f.write("| `%s` | %d | %s |\n" % (v, c, d))
            f.write("\n## 复现\n")
            f.write("```\n")
            f.write("7z x \"[PC-JP]ときたま！～時函玉手箱～.zip\" -o zip\n")
            f.write("innoextract.exe -e -d game \"zip/…/tokitama_DL_SETUP.exe\"\n")
            f.write("python scripts/tokitama_extract.py game/app \"ときたま！～時函玉手箱～_全文本.txt\"\n")
            f.write("```\n")
        print("report:", report_path)


if __name__ == "__main__":
    main()
