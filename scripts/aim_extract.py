#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""[JP]aim∴ai（KiriKiri/KAG3）全文本提取：.ks → 一次点击一行。

L0 判据（全部来自 scenario/macro.ks 与 plugin/，见解析报告 §格式结论）：
  ① 改页等待 = `[pre]` 宏的第一条 `[p]`（KAG3 标准「改ページ」＝清屏并等点击）。
  ② `[「]`/`[『]`/`[（]` 开括号宏 = 输出括号 + `[indent]`；
     闭括号宏 `[」]`/`[』]`/`[）]` = 输出括号 + `[endindent]` + **`[pre * cond="!mp.np"]`**
     ⇒ 「…」收尾处即一次点击。`np` 参数（全库 3 处）抑制改页 ⇒ 该框延到下一条 `[cm]`。
  ③ `[r]` = KAG3 标准改行（框内换行、不等点击）⇒ 合并不拆；`[nhr]`/`[hr]` 同理无字符。
  ④ `[cm]` = 标准メッセージ消去；正常只在框首出现。若它关掉了一个非空框，该框必须带过
     `np` 标记 —— `--audit` 校验此不变量。
  ⑤ `[eruby text=ルビ str=表示文字]`（plugin/eruby.ks 头注释）：上屏的是 **str**。
  ⑥ `[ch text=X]` = 输出字符 X（如 `――`）。
  ⑦ `[speak name="…" vc="…"]` = 独立名字窗（`[locate x=150]`+`[emb mp.name]`）+ 放音 ⇒ 名札剔除。
  ⑧ `[iscript]…[endscript]` 内是 TJS，非文本；行首 `;` = KAG 注释；行首 `*label|` = 标签。

标签扫描对「引号内的 `]`」安全（`[eval exp="a[1]"]` 这类不会截断）。
"""
import argparse
import collections
import glob
import io
import os
import re
import sys

DIRS = ["01_prolog", "02_nitijyou", "03_midori", "04_ueyama"]
BR_OPEN = {"「": "「", "『": "『", "（": "（"}
BR_CLOSE = {"」": "」", "』": "』", "）": "）"}
SOFT_BREAK = {"r", "nhr", "hr"}


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def parse_params(body):
    name = None
    m = re.match(r"\s*([^\]\s=]+)", body)
    if m:
        name = m.group(1)
    params, flags = {}, []
    for q1, v1, k2, v2, star in re.findall(
            r'(\w+)\s*=\s*"([^"]*)"|(\w+)\s*=\s*([^\s\]]+)|(\*)', body):
        if q1:
            params[q1] = v1
        elif k2:
            params[k2] = v2.strip('"')
        elif star:
            flags.append("*")
    return name, params, flags


def scan_tag(src, i):
    """src[i] == '['；返回 (tag 体, 新下标)。

    默认**引号感知**（`[ws cond="kag.se[sf.vc_buf].status == 'play'"]` 里的 `[..]` 不算结尾）。
    例外：源脚本里有引号未闭合的 typo（U_2.ks 的 `[eruby text="こつそしき" str="骨組織]`），
    引号感知会把下一个标签也吞进来 —— 判据是「body 里出现了带 `=` 的嵌套 `[...]`」，
    此时退回 KAG 的真实语义（**首个 `]` 收尾**）。KAG 标签内不可能有 `[key=value]`。
    """
    j = i + 1
    n = len(src)
    q = False
    while j < n:
        c = src[j]
        if c == '"':
            q = not q
        elif c == "]" and not q:
            body = src[i + 1:j]
            if re.search(r"\[[^\[\]]*=", body):
                k = src.find("]", i + 1)
                if 0 <= k < j:
                    return src[i + 1:k], k + 1
            return body, j + 1
        elif c == "\n" and not q:
            break
        j += 1
    # 行内引号自始至终没闭合（源脚本 typo）⇒ 退回 KAG 真实语义：**首个 `]` 收尾**。
    # 实例 U_2.ks:161 `[eruby text="こつそしき" str="骨組織]`（`骨組織` 前少一个 `"`）。
    k = src.find("]", i + 1)
    nl = src.find("\n", i + 1)
    if 0 <= k < n and (nl < 0 or k < nl):
        return src[i + 1:k], k + 1
    return None, i + 1


def is_residue(txt):
    """源脚本残留判定（不靠「像什么」，靠语料级硬指标）。

    本作日文正文 100% 含 cp932 双字节字符（假名／汉字／全角标点）——
    全成品 9,434 行里纯 ASCII 行**恰好 2 行**，且都是残留：
      · `]`                        ← `M_2.ks:852  [wait time=1000 canskip=true]]` 多一个 `]`
      · `..................................`  ← 34 × 0x2E 占位行，夹在 `[bg]`/`[chara]` 的注释区
    再加上同类的 `stopbgm]`（`U_3.ks:946` 缺前导 `[`）。
    因此判据＝**纯 ASCII 即残留**，可复算、不依赖具体字面。
    """
    return bool(txt) and all(ord(c) < 128 for c in txt)


def extract_file(path, out, names, stat):
    with io.open(path, encoding="utf-8", errors="replace") as f:
        src = f.read().lstrip("\ufeff")
    buf, box_np, who = [], False, None
    bad = []
    i, n = 0, len(src)
    at_start = True
    in_script = False

    def close_box(reason):
        nonlocal buf, box_np, who
        txt = "".join(buf).strip(" \t")
        if is_residue(txt):
            stat["dropped"].append(txt)
            txt = ""
        if txt:
            if reason == "cm" and not box_np:
                bad.append(("cm-close-without-np", txt[:40]))
            if reason == "speak":
                stat.setdefault("speakclose", []).append((os.path.basename(path), txt[:50]))
            out.append(txt)
            stat["by_reason"][reason] += 1
            stat["who"].append(who)
        buf, box_np, who = [], False, None

    while i < n:
        c = src[i]
        if c == "\r":
            i += 1
            continue
        if c == "\n":
            i += 1
            at_start = True
            continue
        if at_start:
            j = i
            while j < n and src[j] in " \t":
                j += 1
            if j < n and src[j] == ";":                      # 注释到行尾
                k = src.find("\n", j)
                i = n if k < 0 else k + 1
                at_start = True
                continue
            if j < n and src[j] == "*":                      # 标签
                k = src.find("|", j)
                nl = src.find("\n", j)
                stop = k + 1 if (0 <= k and (nl < 0 or k < nl)) else (nl if nl >= 0 else n)
                i = stop
                at_start = False
                continue
            if j < n and src[j] == "@":                      # @ 行内 TJS
                k = src.find("\n", j)
                i = n if k < 0 else k + 1
                at_start = True
                continue
            i = j
            at_start = False
            if i >= n:
                break
            c = src[i]

        if in_script:
            k = src.find("[endscript]", i)
            if k < 0:
                break
            i = k + len("[endscript]")
            in_script = False
            continue

        if c == "[":
            body, j = scan_tag(src, i)
            if body is None:
                buf.append("[")            # 不是合法标签 → 当普通字符
                i = j
                at_start = False
                continue
            i = j
            at_start = False
            name, params, flags = parse_params(body)
            stat["tags"][name] += 1
            if name in ("iscript", "tjs"):
                in_script = True
            elif name in BR_OPEN:
                buf.append(BR_OPEN[name])
            elif name in BR_CLOSE:
                buf.append(BR_CLOSE[name])
                if "np" in params or "np" in flags:
                    box_np = True
                else:
                    close_box("bracket")
            elif name == "eruby":
                buf.append(params.get("str", ""))
            elif name == "ch":
                buf.append(params.get("text", ""))
            elif name == "cm":
                if "".join(buf).strip():
                    close_box("cm")
            elif name == "pre":
                if "".join(buf).strip():
                    close_box("pre")
            elif name == "speak":
                if "".join(buf).strip():
                    close_box("speak")
                nm = params.get("name")
                if nm:
                    names[nm] += 1
                    who = nm
            elif name in ("sels", "sels3", "sels4"):
                keys = sorted((k for k in params if re.fullmatch(r"cap\d+", k)),
                              key=lambda k: int(k[3:]))
                for k in keys:
                    txt = params[k].strip()
                    if txt:
                        out.append(txt)
                        stat["choices"] += 1
                        stat["by_reason"]["choice"] += 1
                        stat["who"].append(None)
            elif name in SOFT_BREAK:
                pass
            else:
                stat["other"][name] += 1
            continue

        buf.append(c)
        i += 1
        at_start = False

    tail = "".join(buf).strip(" \t")
    if tail and not is_residue(tail):
        bad.append(("eof-open", tail[:40]))
    if tail:
        close_box("eof")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ksdir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()

    files = []
    for d in DIRS:
        fs = glob.glob(os.path.join(a.ksdir, "scenario", d, "*.ks"))
        for p in sorted(fs, key=lambda p: natkey(os.path.basename(p))):
            files.append(p)

    out, names = [], collections.Counter()
    stat = {"by_reason": collections.Counter(), "who": [], "tags": collections.Counter(),
            "other": collections.Counter(), "choices": 0, "dropped": []}
    allbad = []
    for p in files:
        for kind, txt in extract_file(p, out, names, stat):
            allbad.append((os.path.basename(p), kind, txt))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with io.open(a.out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    print("脚本 %d 个 → %d 行（其中选择肢 %d）" % (len(files), len(out), stat["choices"]))
    print("收框原因:", dict(stat["by_reason"]))
    print("名札种类 %d，实例 %d" % (len(names), sum(names.values())))
    if stat["dropped"]:
        print("排除脚本残留 %d 处: %s" % (len(stat["dropped"]), stat["dropped"][:5]))
    if allbad:
        print("!! 异常 %d 处:" % len(allbad))
        for f, k, t in allbad[:10]:
            print("   %s %s %r" % (f, k, t))
    else:
        print("异常 0（[cm] 收尾的框全带 np 标记 ⇒ 不变量成立）")
    if a.audit:
        if stat.get("speakclose"):
            print("\n== [speak] 关掉非空框（%d 处）==" % len(stat["speakclose"]))
            for f, t in stat["speakclose"]:
                print("   %s  %r" % (f, t))
        print("\n== 未消费标签 前 25 ==")
        for k, v in stat["other"].most_common(25):
            print("  %-18s %6d" % (k, v))
        print("\n== 名札表（前 30）==")
        for k, v in names.most_common(30):
            print("  %-22s %5d" % (k, v))


if __name__ == "__main__":
    main()
