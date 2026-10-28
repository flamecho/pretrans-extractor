# -*- coding: utf-8 -*-
"""Pentagon Syndrome（LiveMaker/LiveNovel LSB v117）文本提取

结构（pylivemaker 解析）：
  命令流 → TextIns(Text=TpWord) 承载全部正文；一个 TpWord 内：
    TWdChar            一个字
    TWdOpeReturn(0)    <BR> 框内换行（软换行，合并）
    TWdOpeReturn(1)    <PG> 改页（清框 + 点击等待）← 框边界
    TWdOpeReturn(2)    <PS> 暂停等待
    TWdOpeReturn(3)    <CLR> 清框
    TWdOpeEvent PAUSE  {PAUSE} 框内点击等待（不清框）
    TWdOpeEvent 其它   演出（CHANGECG/MESON/PLAYSND…）不收
    TWdOpeHistChar     名札（独立名窗）→ 丢弃
    TWdOpeVar          主人公名插入（■■■）→ 替换
    TWdImg             内联小图 → 丢弃
  选项：Calc AddArray(_tmp, "…") 字面串，喂给 選択メニュー\■選択実行.lsb 调用
"""
import sys, os, re, glob, json
from livemaker.lsb import LMScript

MC_NAME = "湊"          # 待 vndb 核对
PAUSE_OPS = {"PAUSE"}
SPLIT_RET = {1, 2, 3}   # PG / PS / CLR


def toks(tpword):
    """把一个 TpWord 展平成 token 流：('ch',c) / ('br',) / ('click',kind) / ('var',)"""
    out = []
    for e in tpword._body:
        t = type(e).__name__
        if t == "TWdChar":
            out.append(("ch", e.ch))
        elif t == "TWdOpeReturn":
            if e.break_type == 0:
                out.append(("br",))
            else:
                out.append(("click", e.break_type))
        elif t == "TWdOpeEvent":
            head = e.event.split("\r\n")[0].split("\n")[0].strip("\x01").strip()
            if head in PAUSE_OPS:
                out.append(("click", "PAUSE"))
        elif t == "TWdOpeVar":
            out.append(("var",))
    return out


def segments(tpword):
    """按 click 切段；BR 直接丢弃（软换行合并）。返回 [(kind, text)]"""
    segs, cur, kind = [], [], None
    for tk in toks(tpword):
        if tk[0] == "ch":
            cur.append(tk[1])
        elif tk[0] == "var":
            cur.append(MC_NAME)
        elif tk[0] == "click":
            if "".join(cur).strip():
                segs.append((kind, "".join(cur)))
            cur, kind = [], tk[1]
    if "".join(cur).strip():
        segs.append((kind, "".join(cur)))
    return segs


def clean(s):
    s = s.replace("\u3000", " ")
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def str_literals(parser):
    """从 Calc 表达式里按顺序取字符串字面量（只认字面量，不认变量名）"""
    from livemaker.lsb.core import ParamType
    vals = []
    def walk(p):
        for ent in getattr(p, "entries", []):
            for op in getattr(ent, "operands", []):
                if isinstance(getattr(op, "type", None), ParamType) and op.type == ParamType.Str:
                    vals.append(op.value)
                else:
                    walk(op)
    walk(parser)
    return vals


def options_of(script):
    """遍历命令，收集 AddArray 组（一组 = 一个选择菜单）"""
    groups, cur = [], []
    for cmd in script.commands:
        name = type(cmd).__name__
        if name == "Calc":
            lits = str_literals(cmd.args["Calc"])
            if lits:
                cur.extend(lits)
        elif name == "Call" and "選択実行" in cmd.args["Page"].get("Page", ""):
            if cur:
                groups.append(cur)
                cur = []
        elif name == "Calc":
            pass
        else:
            if name in ("VarNew", "VarDel", "Label", "Jump", "If", "Elseif", "Else", "Wait"):
                pass
    return groups


def main():
    srcdir = sys.argv[1]
    outpath = sys.argv[2]
    stats = {"files": 0, "lines": 0, "chars": 0, "long": 0, "maxchars": 0}
    lines = []
    for p in sorted(glob.glob(os.path.join(srcdir, "*.lsb"))):
        s = LMScript.from_file(p)
        fname = os.path.basename(p)
        filelines = []
        for cmd in s.commands:
            if type(cmd).__name__ != "TextIns":
                continue
            segs = [(k, clean(t)) for k, t in segments(cmd.args["Text"])]
            segs = [(k, t) for k, t in segs if t]
            for k, t in segs:
                filelines.append(t)
                stats["chars"] += len(t)
                if len(t) > 120:
                    stats["long"] += 1
                    stats["maxchars"] = max(stats["maxchars"], len(t))
        if filelines:
            stats["files"] += 1
            lines.extend(filelines)
    stats["lines"] = len(lines)
    with open(outpath, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
