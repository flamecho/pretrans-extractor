#!/usr/bin/env python3
"""月影の鎖 -狂爛モラトリアム- (NS) 文本提取 — Takuyo gss / SCR 2.00 / LSDARC V.100

链路：hactool(xci) → RomFS/SCRDATA.BIN(索引) + SCRDATA.ARC(脚本) → SCR 2.00 反汇编
      → 0x5a/0xfc 正文、0xf0 扉文、0x5c 选项 → 一次点击一行。

同引擎（SCR 2.00 + LSDARC V.100）复用：gss_lsdarc.py 索引读法、himehibi_disasm.py 逐条前进。
可直接套用到同系列 [NS-JP]月影の鎖 -錯乱パラノイア-（改 ROMFS/OUT 即可）。
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from himehibi_disasm import disasm  # noqa: E402
import gss_lsdarc as L  # noqa: E402

# ---------------- 名字槽（PRG_ROUTE.SCR: 0x132(1802,'冬浦') / 0x132(0c02,'めぐみ')） -------------
NAME_SLOTS = {"1802": "冬浦", "0c02": "めぐみ"}

# ---------------- 收录顺序（＝PRG_ROUTE 的路线块顺序 ＋ PSP_TOP 段） ----------------
def build_order(names):
    have = {n.upper(): n for n in names}
    order = []
    def add(n):
        k = n.upper()
        if k in have and have[k] not in order:
            order.append(have[k])

    # 1 共通（L_KYOUDAI）
    for i in range(1, 8):
        add("01NEW_COM%03d" % i)
    # 2 藤堂雅（L_KYOUDAI_MIY）
    miy = ["MIY%03d" % i for i in range(1, 22)] + [
        "MIY022_LV", "MIY023_LV", "MIY024_LV", "MIY025_LVED", "MIY026_LVEP",
        "MIY027_IZ", "MIY028_IZ", "MIY029_IZ", "MIY030_IZED"]
    for s in miy:
        add("01NEW_" + s)
    # 3 藤堂樹（L_KYOUDAI_ITU）
    itu = ["ITU%03d" % i for i in range(1, 27)] + [
        "ITU027END", "ITU028EP", "ITU029IZ", "ITU030IZ"]
    for s in itu:
        add("02NEW_" + s)
    # 4 大井川本編（PSP_TOP 段）：001–035 / 036A・036B（无 036）/ 037–040 / 041END・042EP・043IZED
    for i in list(range(1, 36)) + list(range(37, 41)):
        add("ANI_%03d" % i)
    add("ANI_036A")
    add("ANI_036B")
    add("ANI_041END")
    add("ANI_042EP")
    add("ANI_043IZED")
    return order


def build_tail(names):
    have = {n.upper(): n for n in names}
    order = []
    def add(n):
        k = n.upper()
        if k in have and have[k] not in order:
            order.append(have[k])

    # 5 ANOTHER 共通（L_ANOTHER）
    for i in range(0, 7):
        add("02ANOTHER_COM%03d" % i)
    # 6 ANOTHER 各角色（L_ANOTHER_KAG/MOT/INO/HAR/ANI）
    blocks = [
        ("KAG", ["%03d" % i for i in range(1, 13)] + ["013LV", "014LV", "015LVED", "016LVEP",
                                                      "017IZ", "018IZ", "019IZ", "020IZED"]),
        ("MOT", ["%03d" % i for i in range(1, 13)] + ["013_LV", "014_LV", "015_LVED", "016_LVEP",
                                                      "017_IZ", "018_IZ", "019_IZ", "020_IZED"]),
        ("INO", ["%03d" % i for i in range(1, 15)] + ["015_LV", "016_LVED", "017_LVEP",
                                                      "018_IZ", "019_IZ", "020_IZED"]),
        ("HAR", ["%03d" % i for i in range(1, 15)] + ["015LV", "016LV", "017LVEP",
                                                      "018IZ", "019IZ", "020IZED"]),
        ("ANI", ["%03d" % i for i in range(1, 13)] + ["013_LV", "014_LV", "015_LV", "016_LVEP",
                                                      "017_IZ", "018_IZ", "019_IZ", "020_IZED"]),
    ]
    for pref, items in blocks:
        for s in items:
            add("02ANOTHER_%s%s" % (pref, s))
    # 7 大井川 AFTER
    for i in range(1, 5):
        add("03AFTER_ANI%03d" % i)
    add("03AFTER_ANI005EP")
    # 8 各角色 AFTER
    for pref, cnt in (("KAG", 6), ("MOT", 5), ("INO", 5), ("HAR", 5)):
        for i in range(1, cnt + 1):
            add("AFTER%s_%s%02d" % ({"KAG": "01", "MOT": "02", "INO": "03", "HAR": "04"}[pref], pref, i))
    # 9 各角色 ANOTHER
    for pref, no, cnt in (("KAG", "01", 8), ("MOT", "02", 8), ("INO", "03", 7),
                          ("HAR", "04", 7), ("ANI", "05", 7)):
        for i in range(1, cnt + 1):
            ep = "EP" if i == cnt else ""
            add("ANOTHER%s_%s%02d%s" % (no, pref, i, ep))
    # 10 観光（KANKOU）
    for i in range(0, 8):
        add("KANKOU%02d" % i)
    return order


EXCLUDE = {
    "AUTOEXEC", "INIT", "RELOAD", "PRG_BG", "PRG_EFFECT", "PRG_NAME", "PRG_ROUTE",
    "PRG_STAND", "SELECT2", "CERO", "DEBUG",
}

RUBY = re.compile(r"#[a-zA-Z]?([^|#]*)\|[^#]*#")


def strip_fmt(s):
    s = RUBY.sub(r"\1", s)
    return s.replace("\\n", "")


def emit(line, seg, stats, key):
    for seg in seg.split("\\c"):
        seg = strip_fmt(seg).strip()
        if seg:
            line.append(seg)
            stats[key] += 1


def load(romfs):
    binp = os.path.join(romfs, "SCRDATA.BIN")
    arcp = os.path.join(romfs, "SCRDATA.ARC")
    ents_l, _ = L.read_index(binp)
    arc = open(arcp, "rb").read()
    ents, order = {}, []
    for e in ents_l:
        ents[e["name"].upper()] = (e["name"], e)   # 保留条目字典，打包时走 gss_codec
        order.append(e["name"])
    return arc, ents, order


def script_of(arc, e):
    return L.unpack_entry(arc, e)


def pick_disasm(code_bytes):
    """按脚本头选反汇编器：SCR 2.00（5B 头）/ SCR 3.00（6B 头）。"""
    ver = code_bytes[:8]
    if ver == b"SCR 3.00":
        import gss_scr3
        return gss_scr3.disasm, "SCR 3.00"
    if ver == b"SCR 2.00":
        return disasm, "SCR 2.00"
    raise SystemExit("未知脚本头 %r" % ver)


def main(romfs, out):
    arc, ents, all_names = load(romfs)
    names = [ents[k][0] for k in ents]
    seq = build_order(names) + build_tail(names)
    # 未被上述规则覆盖的故事脚本（若有）追加在尾部，避免静默漏取
    rest = [n for n in names if n.upper() not in EXCLUDE and n not in seq]
    seq += sorted(rest)

    lines, stats = [], {"5a": 0, "fc": 0, "f0": 0, "5c": 0, "c": 0}
    ver_seen = set()
    for name in seq:
        _, e = ents[name.upper()]
        code_bytes = script_of(arc, e)
        dis, ver = pick_disasm(code_bytes)
        ver_seen.add(ver)
        code, err = dis(code_bytes)
        if err:
            raise SystemExit("反汇编失步 %s: %r" % (name, err))
        for _o, op, _sz, _id, ops in code:
            if op == 0x5a:
                emit(lines, ops[0][1], stats, "5a")
            elif op == 0xfc:
                t = ops[0][1]
                slots = [NAME_SLOTS.get(v, "") for tp, v in ops[1:] if tp == 6]
                it = iter(slots)
                t = re.sub(r"%s", lambda m: next(it, ""), t)
                emit(lines, t, stats, "fc")
            elif op == 0xf0:
                t = strip_fmt(ops[0][1]).strip()
                if t:
                    lines.append(t)
                    stats["f0"] += 1
            elif op == 0x5c:
                for tp, v in ops[1:]:
                    if tp != 3:
                        continue
                    txt = v.rsplit(" ,", 1)[0].strip()
                    if txt:
                        lines.append(txt)
                        stats["5c"] += 1

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("files=%d lines=%d %s ver=%s" % (len(seq), len(lines), stats, sorted(ver_seen)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
