#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LukPlus ADV (SRX Rev / PSV) lua script -> text extraction.

Engine: LukPlus Co.,Ltd. ADV framework (Pndr), script = plaintext UTF-8 Lua.
Text op:  Msg(id, text[, wait])  with MsgName(name) in a SEPARATE name window
         stMsg(id, name, text)   omake wrapper (defined in script/omake_function.lua)
Option:  MsgSelect(t1, t2 ...)
Macros:  @Vs00 -> protagonist surname, @Vs01 -> given name, @K / @I stripped.

Verdict on break ops:
  A class = Msg without "@K"  -> MsgKeyWait(clearFlag=true) -> FontClear()  (清框)
  B class = Msg with    "@K"  -> MsgKeyWait(clearFlag=false) -> 文字留在画面上
  MsgAnimation always calls FontIdClear(FONT_MSG_TEXT) first => 每条 Msg 都重画，
  文字从不累加 => B 类不产生同框多段 => 单版。
"""
import os
import re
import sys

MAIN_SEI = "麻黄"
MAIN_MEI = "アキラ"


# ---------------------------------------------------------------- lua lexing
def read_text(path):
    b = open(path, "rb").read()
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return b.decode("utf-8", "replace")


def skip_ws(t, i):
    while i < len(t) and t[i] in " \t\r\n":
        i += 1
    return i


def parse_string(t, i):
    """return (value, next_index) for a lua string literal at i."""
    if t.startswith("[[", i):
        j = t.find("]]", i + 2)
        if j < 0:
            raise ValueError("unterminated long string")
        s = t[i + 2:j]
        if s.startswith("\r\n"):
            s = s[2:]
        elif s[:1] == "\n":
            s = s[1:]
        return s, j + 2
    q = t[i]
    j = i + 1
    out = []
    while j < len(t):
        c = t[j]
        if c == "\\":
            nxt = t[j + 1]
            m = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "'": "'", "\\": "\\"}
            if nxt in m:
                out.append(m[nxt]); j += 2; continue
            out.append(nxt); j += 2; continue
        if c == q:
            return "".join(out), j + 1
        out.append(c); j += 1
    raise ValueError("unterminated string")


LONG_OPEN = re.compile(r"\[(=*)\[")


def mask_comments(t):
    """replace lua comments by spaces (offsets & newlines preserved)."""
    out = list(t)
    i = 0
    n = len(t)
    while i < n:
        c = t[i]
        if c in "\"'":
            try:
                _, i = parse_string(t, i)
            except ValueError:
                i += 1
            continue
        if t.startswith("--", i):
            m = LONG_OPEN.match(t, i + 2)
            if m:
                close = "]" + m.group(1) + "]"
                j = t.find(close, i + 2)
                j = n if j < 0 else j + len(close)
            else:
                j = t.find("\n", i)
                j = n if j < 0 else j
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if c == "[":
            m = LONG_OPEN.match(t, i)
            if m:
                close = "]" + m.group(1) + "]"
                j = t.find(close, i + 2)
                i = n if j < 0 else j + len(close)
                continue
        i += 1
    return "".join(out)


def parse_args(t, i):
    """t[i] == '(' ; return (list of arg tokens, index after ')')."""
    assert t[i] == "("
    i += 1
    args = []
    while True:
        i = skip_ws(t, i)
        if i >= len(t):
            return args, i
        if t[i] == ")":
            return args, i + 1
        if t[i] in "\"'[":
            try:
                v, i = parse_string(t, i)
                args.append(("str", v))
            except ValueError:
                args.append(("raw", ""))
                return args, i
        else:
            st = i
            depth = 0
            while i < len(t):
                c = t[i]
                if c in "([{":
                    depth += 1
                elif c in ")]}":
                    if depth == 0:
                        if c == ")":
                            break
                        i += 1
                        continue
                    depth -= 1
                elif c == "," and depth == 0:
                    break
                i += 1
            args.append(("raw", t[st:i].strip()))
        i = skip_ws(t, i)
        if i < len(t) and t[i] == ",":
            i += 1
            continue


CALL_RE = re.compile(r"(?m)^[ \t]*([A-Za-z_]\w*)[ \t]*\(")
TEXT_OPS = {"Msg", "stMsg", "MsgSelect"}


def iter_calls(path):
    raw = read_text(path)
    t = mask_comments(raw)
    for m in CALL_RE.finditer(t):
        name = m.group(1)
        if name not in TEXT_OPS:
            continue
        try:
            args, _ = parse_args(raw, m.end() - 1)
        except ValueError:
            continue
        yield name, args


# ---------------------------------------------------------------- text clean
def clean_block(s):
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = s.split("\n")
    out = []
    for ln in lines:
        ln = ln.replace("\t", "")
        ln = ln.strip(" ")
        out.append(ln)
    # drop leading / trailing empties
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    s = "".join(out)
    s = s.rstrip("　")
    return s


def apply_macros(s):
    s = s.replace("@Vs00", MAIN_SEI).replace("@Vs01", MAIN_MEI)
    s = s.replace("主人公名前", MAIN_MEI)
    s = s.replace("@K", "").replace("@I", "")
    return s


def strip_blank_marks(s):
    # 富文本/占位：本作无 <fs> 类标记，保守剥除全角包裹符外的控制串
    s = s.replace("_r", "")  # 仅出现在 stMsg 的 '…' 串里，已另行转行
    return s


def main():
    root = sys.argv[1]
    outpath = sys.argv[2]
    report = {"msg": 0, "stmsg": 0, "opt": 0, "k": 0, "stray_at": [], "files": 0}
    order = ["game", "news", "special"]
    lines = []
    for sub in order:
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".lua"):
                continue
            p = os.path.join(d, fn)
            report["files"] += 1
            for name, args in iter_calls(p):
                if name == "Msg":
                    if len(args) < 2:
                        continue
                    text = args[1][1]
                    raw = text
                    if "@K" in raw:
                        report["k"] += 1
                    txt = apply_macros(clean_block(text))
                    if not txt:
                        continue
                    report["msg"] += 1
                    lines.append(txt)
                    for mm in re.findall(r"@\w+", txt):
                        report["stray_at"].append((fn, mm))
                elif name == "stMsg":
                    if len(args) < 3:
                        continue
                    text = args[2][1]
                    text = text.replace("_r", "\n")
                    txt = apply_macros(clean_block(text))
                    if not txt:
                        continue
                    report["stmsg"] += 1
                    lines.append(txt)
                elif name == "MsgSelect":
                    for kind, v in args:
                        if kind != "str":
                            report["opt_dyn"] = report.get("opt_dyn", 0) + 1
                            continue
                        v = apply_macros(clean_block(v))
                        if v:
                            report["opt"] += 1
                            lines.append(v)
    with open(outpath, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("files", report["files"], "msg", report["msg"], "stmsg", report["stmsg"],
          "opt", report["opt"], "opt_dyn", report.get("opt_dyn", 0), "K", report["k"])
    print("lines", len(lines))
    if report["stray_at"]:
        print("stray @:", report["stray_at"][:20], "total", len(report["stray_at"]))


if __name__ == "__main__":
    main()
