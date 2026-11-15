"""DIABOLIK LOVERS CHAOS LINEAGE (NS-JP) —— script.cpk 全文本提取

引擎：Nintendo「Bezel Engine」（romfs/boot.lua 含 BezelEngineInitializer）
容器：romfs/script.cpk（CRI CPK）→ 239 个 `cl_<角色>_<章>.dat` / `start.dat`
        · CPK 条目用 CpkMode=1 压缩，`scripts/cpk.py` 直接解出（ExtractSize > FileSize）

脚本 = 标准 STCM2L（Idea Factory 家族），**UTF-8 文本 → 本作是 CP932**
  `STCM2L Aug 24 2012 16:30:16\\0` + 头 + 'GLOBAL_DATA' 表 + 记录流

记录（顺序走查，每条的 `[+8]` 是记录总长，4 字节对齐）：
  [u32 kind][u32 k][u32 size][u32 ptr][f32 2.0][f32 2.0] … [0][L/4][1][L][文本 L 字节][pad]
  文本头 = 24 + 12k；`L = size - 32 - 12k`（自带三重自校验：`u32(iL-8)==L/4`、
  `u32(iL-4)==1`、`u32(iL-12)==0`，且 `u32(off+16)==u32(off+20)==0x40000000`）

本作 kind 表（全库实证，85,148 条文本节点）：
  0x4BA 正文行（一行一个节点）       → 收
  0x4BB 框终止＝等待点击（16 B 定长） → **框边界**
  0x4BC 話者名 id（payload 是整数，不是文本）→ 丢
  0x599 立绘/表情资源名（aya_WorB_01）／0x44E sureN／0x41D select/switch
  0x41B scenario_type/no／0x1A24・0x1C80 资源名／0x4DD・0x4BE 系统参数 → 丢
  0x427 `*_end` 结局标记 → 丢

成行（L0）：**一个框 = 0x4BC(名) + 若干 0x4BA(行) + 0x4BB(等待点击) ⇒ 一次点击**。
  框内多行必须**合并**（例：`オレ様が覇王に相応しいのは` + `当然だぜ` 是一句）。

说话人：名字是**独立名字窗**（0x4BC 的整数 id 指向名字表），正文串里不含名字；
  名字表不在 romfs（System/DevSystem.bea 解包后只有 FSHA/BNTX/FRES/SARC，无日文）
  ⇒ 按「有独立名字窗才剔」处理：**不输出说话人**。

选项：全库 198 处 `0x41D select` 附近**无任何文本节点**（W/B＝Word or Blood 系统的固定 UI），
  脚本内不存在选项文本。

用法：
  python scripts/dlcl_extract.py <script.cpk 解包目录> --out <txt>
"""
import os
import struct
import sys

# 主角名（玩家可改名）：游戏内字面证据＝「ユイさん」×133；姓「小森」原文 0 次 ⇒ 取 vndb c14695
NAME_MAP = {"#NAME[1]": "小森", "#Name[1]": "小森", "#NAME[2]": "ユイ"}
MACROS = [(k, v) for k, v in NAME_MAP.items()]

KIND_LINE = 0x4BA
KIND_NAME = 0x4BC
# 框边界：0x4BB＝等待点击；0x5A8＝清屏（同为 16 B `[kind][0][0x10][flag]`，紧随空行节点，
# 后接换背景/立絵或新名记录）。只认 0x4BB 会把「旁白＋清屏＋次场内心独白」并成一行。
KIND_BOX = {0x4BB, 0x5A8}


def read_dat(path):
    """返回 dict：boxes=[(name_id, 文本)]，records=int"""
    d = open(path, "rb").read()
    if d[:6] != b"STCM2L":
        return []
    u = lambda o: struct.unpack_from("<I", d, o)[0]

    def text_of(off, size):
        for k in range(1, 7):
            L = size - 32 - 12 * k
            if L < 0 or L % 4:
                continue
            iL = off + 24 + 12 * k
            if u(iL - 12) != 0 or u(iL - 4) != 1 or u(iL - 8) != L // 4:
                continue
            if u(off + 16) != 0x40000000 or u(off + 20) != 0x40000000:
                continue
            raw = d[iL + 4:iL + 4 + L].split(b"\0")[0]
            try:
                s = raw.decode("cp932")
            except UnicodeDecodeError:
                return None
            for k, v in MACROS:
                s = s.replace(k, v)
            return s
        return None

    boxes, cur, nm = [], [], 0
    off = 0x30
    while off < len(d) - 12:
        kind, size = u(off), u(off + 8)
        if 0 < size <= len(d) - off and size % 4 == 0:
            if kind == KIND_NAME:
                if cur:      # 名记录出现在正文之后 ⇒ 这是下一个框的开头（全库仅 1 例：cl_azu_10）
                    boxes.append((nm, "".join(cur)))
                    cur = []
                nm = u(off + 0x28)
            elif kind == KIND_LINE:
                t = text_of(off, size)
                if t and t.strip("　 ") != "":   # 纯空白节点＝框内空行占位（排版用），不是正文
                    cur.append(t)
            elif kind in KIND_BOX:
                if cur:
                    boxes.append((nm, "".join(cur)))
                    cur = []
            off += size
        else:
            off += 4
    if cur:
        boxes.append((nm, "".join(cur)))
    return boxes


def order_key(fn):
    """start → プロローグ → 各角色（字母序；角色内部 01..15 → ED1 → ED2 → heaven）"""
    stem = fn[:-4]
    if stem == "start":
        return (0, "")
    if stem.startswith("cl_plorogue"):
        return (1, stem)
    return (2, stem)


def main(src, out):
    files = sorted((f for f in os.listdir(src) if f.endswith(".dat")), key=order_key)
    lines, stats = [], []
    for f in files:
        bs = read_dat(os.path.join(src, f))
        for _nm, t in bs:
            lines.append(t)
        stats.append("%s\t%d" % (f, len(bs)))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="\n") as fh:
        for ln in lines:
            fh.write(ln + "\n")
    stats_path = os.path.join(os.path.dirname(os.path.abspath(src)), "stats.tsv")
    with open(stats_path, "w", encoding="utf-8") as fh:   # 分文件行数台账，落在解包目录旁
        fh.write("\n".join(stats))
    print("脚本 %d / 行 %d / 字节 %d" % (len(files), len(lines), os.path.getsize(out)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else sys.argv[2])
