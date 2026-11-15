# -*- coding: utf-8 -*-
"""
[JP]ViSTA+1.20 全文本提取  (KiriKiri / KAG3, 明文 cp932, 无 OTag 加扰)
=============================================================================
源：RAR5 SFX(otoame) -> data.xp3(867文件/65 .ks) + patch.xp3(301文件/9 .ks, 1.20追加) + ViSTA.eXe
引擎：吉里吉里 KAG3（标准宏在引擎内；自定义宏 冒頭/基本セリフ/黒背景フォント/スチル枠 仅设 position/font）
断框 L0（kag3 标准 + 本作实测宏定义）：
  - 框（文本框/点击）界：[0](=[l][cm], clear) / [er] / [ct] / [cm] / [p] / [e] / [np] / [pe] / [ple] / [clear]
    —— [0] 是 [macro name=0]=[l][cm]，本作每句对话行尾终结符（data.xp3 出现 6277 次），即“一次点击=一框=一行”的边界。
  - 框内换行（不点击，合并）：[r](改行+待) / [l](改行不待) / [waitclick](待不换页)
    —— 同框的一次点击：用户口径（Recall 裁定）[r] 为框内合并，多句合并成一行。
  - 其余（[image]/[backlay]/[trans]/[wt]/[wc]/[wait]/[jump]/[position]/[font]/[resetfont]/
    [quake]/[delay]/[freeimage]/[locate]/[button]/[s]…）演出/控制/布局 ⇒ 忽略。
  - 富文本：[ruby text="X"]Y ⇒ 留基字 Y 去振假名 X；[emb exp="..."] 是 TJS 表达式（代码，剥）；
    [emb]text[/emb] ⇒ 留 text。
  - 选项：[link]…[endlink] 内**字面日文**（非 [emb exp=] 代码）⇒ 选项；本作 [link] 均为书签/导航（含 exp 代码）⇒ 0 选项。
    [button graphic=…] 图按钮 ⇒ 跳过。无 [select]/[choice]。
  - [iscript]…[endscript] / @iscript ⇒ TJS 代码 ⇒ 剔除。
  - *label|… 标签行 ⇒ 场景跳转点，非文本，flush 当前框。
输出：单行＝一框（[0]/[er]/[ct]/[cm]/[p] 界），UTF-8 BOM / 纯 LF。单版（[r]/[l] 框内合并）。
"""
import sys, re
sys.path.insert(0, "tools")
from xp3 import XP3

DATA_XP3 = r"_work_vista/src/[JP]ViSTA+1.20/data.xp3"
PATCH_XP3 = r"_work_vista/src/[JP]ViSTA+1.20/patch.xp3"
OUT = r"提取结果/[JP]ViSTA+1.20.txt"
ENC = "cp932"

BOX_BREAK = {"0", "er", "e", "np", "p", "pe", "ple", "clear", "ct", "cm"}
INBOX_NL = {"r", "l", "waitclick", "wait", "wt", "wc"}
LINK_OPEN = {"link"}
LINK_CLOSE = {"endlink", "/link"}

TAG_RE = re.compile(r"\[([^\[\]\r\n]{0,200})\]")


def split_tags(s):
    """平衡括号 tokenizer；未配平标签整段丢弃（防脚本残留）。"""
    out, i, n, buf = [], 0, len(s), ""
    while i < n:
        c = s[i]
        if c != "[":
            buf += c; i += 1; continue
        j, depth = i, 0
        while j < n:
            if s[j] == "[":
                depth += 1
            elif s[j] == "]":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:               # 未配平（缺 ]）⇒ 丢弃整段
            break
        if buf:
            out.append(("text", buf)); buf = ""
        inner = s[i + 1:j]
        m = re.match(r"([^\s=\[\]]+)", inner)
        out.append(("tag", m.group(1) if m else "", inner))
        i = j + 1
    if buf:
        out.append(("text", buf))
    return out


def clean_text(s: str) -> str:
    # 半角引号归一全角（源偶用 ｢｣ 混同 「」；统一口径，便于引号配对）
    s = s.replace("｢", "「").replace("｣", "」")
    return s.replace("\r", "").replace("\n", "")


def parse_kag(text):
    boxes, opts = [], []
    seg = []
    in_link = False
    in_script = False   # @iscript … @endscript（或 [iscript]…[endscript]）
    in_macro = False    # @macro … @endmacro（宏定义体，非上屏）

    def flush_box():
        line = "".join(seg)
        if line.strip():
            boxes.append(line)
        seg.clear()

    for raw in text.split("\n"):
        s = raw.strip()
        # 标签行（场景跳转点）——非文本
        if s.startswith("*"):
            flush_box()
            continue
        # KAG / TJS 注释行（; 或 // 起首）——作者注记，非上屏文本
        if s.startswith(";") or s.startswith("//"):
            continue
        # @ 指令行
        if s.startswith("@"):
            cmd = s[1:].strip()
            low = cmd.lower()
            if low.startswith("iscript"):
                in_script = True
                continue
            if low.startswith("endscript"):
                in_script = False
                continue
            if low.startswith("macro"):
                in_macro = True
                continue
            if low.startswith("endmacro"):
                in_macro = False
                continue
            # 其余 @cmd → [cmd] 交给 tokenizer（@else/@endif/@nowait/@eval/@jump…）
            raw = "[" + cmd + "]"
        # 跳过 TJS 代码块与宏定义体
        if in_script or in_macro:
            continue
        # 逐 token
        for tok in split_tags(raw):
            if tok[0] == "text":
                t = clean_text(tok[1])
                if in_link:
                    # [link]…[endlink] 是导航/书签/读取菜单 UI（含 LOADしないで戻る），
                    # 非对白选项、非正文 ⇒ 整段丢弃（系统 UI 不收）
                    continue
                else:
                    seg.append(t)
            else:
                name = tok[1].lower()
                inner = tok[2]
                if name == "emb":
                    # [emb exp=...] 是 TJS 表达式（代码）⇒ 忽略；
                    # [emb]text[/emb] ⇒ 留 text（tokenizer 自然保留内部文本）
                    if "exp=" in inner:
                        continue
                    continue
                elif name in ("/emb",):
                    continue
                elif name in BOX_BREAK:
                    flush_box()
                elif name in INBOX_NL:
                    pass
                elif name in LINK_OPEN:
                    in_link = True
                elif name in LINK_CLOSE:
                    in_link = False
                # 其余标签忽略
        # 行尾
    flush_box()  # EOF flush
    return boxes, opts


def main():
    data = XP3(DATA_XP3)
    patch = XP3(PATCH_XP3)
    ks = set()
    for x in (data, patch):
        for f in x.files:
            if f.lower().endswith(".ks"):
                ks.add(f)
    boxes_all, opts_all = [], []
    stats = {"ks": 0, "boxes": 0, "opts": 0, "chars": 0, "excluded": 0}
    for name in sorted(ks):
        if name in data.files:
            b = data.read(name)
        else:
            b = patch.read(name)
        text = b.decode(ENC, "replace")
        boxes, opts = parse_kag(text)
        stats["ks"] += 1
        stats["boxes"] += len(boxes)
        stats["opts"] += len(opts)
        boxes_all.extend(boxes)
        opts_all.extend(opts)
    stats["chars"] = sum(len(b) for b in boxes_all)
    # 输出（正文行 ＋ 选项行，末尾不插空行）
    out_lines = boxes_all + opts_all
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("﻿")
        f.write("\n".join(out_lines))
        if out_lines:
            f.write("\n")
    print(f"[done] ks={stats['ks']} boxes={stats['boxes']} opts={stats['opts']} "
          f"chars={stats['chars']} lines={len(out_lines)} -> {OUT}")


if __name__ == "__main__":
    main()
