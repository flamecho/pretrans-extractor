# -*- coding: utf-8 -*-
"""Pentagon Syndrome（LiveMaker/LiveNovel LSB v117）成行器

断框判据（全为 L0：字节码字段 / 游戏自带事件处理脚本）
  A 类（清框+点击）：TWdOpeReturn break_type==1  (<PG>)          19,631
  B 类（框内点击，不清框）：内联 TWdOpeEvent "PAUSE"            465
     依据 ノベルシステム\メッセージボックス\イベント.lsb：
       "PAUSE" → SetProp 81 1 / 続きカーソル，无清屏；
       "TEXTCLEAR" → 只置 強制テキストクリア 标志，无等待
  换行（不点击）：TWdOpeReturn break_type==0 (<BR>)              11,425 → 合并
  名札：TWdOpeEvent NAMELABEL（独立名前窗，DB名前代替 → 【…】）→ 整条丢弃
  变量：TWdOpeVar '■■■'（序章由玩家输入“彼の名前”，4 字）→ 代入正解「湊」
  选项：Calc AddArray(_tmp, "…") 字面串，随后的 選択メニュー\■選択実行 调用即该项组
"""
import sys, os, re, glob, json
from livemaker.lsb import LMScript
from livemaker.lsb.core import ParamType, OpeFuncType

VAR_NAME = "湊"        # 玩家输入“彼の名前”的正解（正文后期揭示：諸星湊）

# 系统/导航菜单（非剧情选项）：ED 后「次の話へ／部屋へ戻る／個別ルートへ」
NAV_MENUS = {"000003AD.lsb", "0000077F.lsb"}

# 作者写在正文流里的演出便条（舞台指示，非台词）：00000042.lsb
#   源：「真ん中140右からイン　640→280左からイン　-360→0中央から左へはける」+ MOTION 指令
MEMO = {"真ん中140右からイン　640→280左からイン　-360→0中央から左へはける"}


def addarray_literals(parser):
    temps, out = {}, []
    for ent in getattr(parser, "entries", []):
        ops = list(getattr(ent, "operands", []))
        if getattr(ent, "func", None) is None and len(ops) == 1 and getattr(ops[0], "type", None) == ParamType.Str:
            temps[ent.name] = ops[0].value
        if getattr(ent, "func", None) == OpeFuncType.AddArray and len(ops) >= 2:
            v = temps.get(getattr(ops[1], "value", None))
            if v is not None:
                out.append(v)
    return out


def split_box(body):
    """按 A 类（PG）切框；返回 [[glyph,...], ...]"""
    boxes, cur = [], []
    for e in body:
        if type(e).__name__ == "TWdOpeReturn" and e.break_type == 1:
            boxes.append(cur)
            cur = []
        else:
            cur.append(e)
    boxes.append(cur)
    return boxes


def is_pause(e):
    return (type(e).__name__ == "TWdOpeEvent"
            and e.event.split("\r")[0].split("\n")[0].strip("\x01").strip() == "PAUSE")


def box_segments(box):
    """按 B 类（PAUSE）切段，BR 合并；返回 [str,...]"""
    segs, cur = [], []
    for e in box:
        t = type(e).__name__
        if t == "TWdChar":
            cur.append(e.ch)
        elif t == "TWdOpeVar":
            cur.append(VAR_NAME)
        elif is_pause(e):
            segs.append("".join(cur))
            cur = []
        # BR / 名札 / 其它演出 op / 内联图 → 丢弃
    segs.append("".join(cur))
    return [s for s in (clean(x) for x in segs) if s]


def clean(s):
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    return s.strip(" \t\u3000")


def build(files, mode):
    """mode: click（A+B 断）/ page（仅 A 断）/ dual（同框先列段再列合并行）"""
    lines = []
    st = dict(boxes=0, multi=0, segs=0, chars=0)
    for p in files:
        s = LMScript.from_file(p)
        pending_opts = []
        for cmd in s.commands:
            n = type(cmd).__name__
            if n == "Calc":
                pending_opts.extend(addarray_literals(cmd.args["Calc"]))
            elif n == "Call" and "選択実行" in cmd.args["Page"].get("Page", ""):
                if pending_opts and os.path.basename(p) not in NAV_MENUS:
                    for o in pending_opts:
                        o = clean(o)
                        if o and o not in MEMO:
                            lines.append(o)
                pending_opts = []
            elif n == "TextIns":
                for box in split_box(cmd.args["Text"]._body):
                    segs = box_segments(box)
                    if not segs:
                        continue
                    if len(segs) == 1 and segs[0] in MEMO:
                        continue
                    st["boxes"] += 1
                    st["chars"] += sum(len(x) for x in segs)
                    if len(segs) > 1:
                        st["multi"] += 1
                    if mode == "page":
                        lines.append("".join(segs))
                    elif mode == "click":
                        lines.extend(segs)
                    else:  # dual
                        lines.extend(segs)
                        if len(segs) > 1:
                            lines.append("".join(segs))
    st["segs"] = len(lines)
    return lines, st


def main():
    srcdir, outdir = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(srcdir, "*.lsb")))
    os.makedirs(outdir, exist_ok=True)
    res = {}
    for mode in ("page", "click", "dual"):
        lines, st = build(files, mode)
        path = os.path.join(outdir, f"{mode}.txt")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\ufeff" + "\n".join(lines) + "\n")
        st["lines"] = len(lines)
        res[mode] = st
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
