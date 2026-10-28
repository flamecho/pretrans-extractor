# -*- coding: utf-8 -*-
"""O*G*A 鬼ごっこロワイアル (PSP, Idea Factory/Otomate "oni") —— .tob 字节码级框提取

字节码格式（本作唯一，已在 271 个 tob 上验证）：
    [u8 n][u8 opcode][(n-1)*2 bytes args]
  n = 1 → 无参指令；n = 5 → 4 个 u16 参数。

框界（由用户逐条核对游戏文本框确认）：
    op 0x3e <wordOff>   显示串表 wordOff 处的串（wordOff = 串表内字节偏移 / 4）
    op 0x3f             框结束（等待点击）
    op 0x41             框结束（等待点击，含清屏）
  实测（tob 0xceec）：401 392 387 → 0x41 ；405 → 0x3f ；409 413 → 0x3f ；420 → 0x41
  与游戏内 3 行框 / 单行感叹 / 2 行框 完全一致。

代码区起点可变（0x30 / 0x34 / 0x38 / 0x3c）：头部长度 16~32 字节，
用「能完整解析的起点里尾部残留最少」自动判定。

用法：
    python oga_tob_extract.py <STS.DAT> <out.txt>
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oga_sts_extract as O  # noqa: E402  复用 tob 遍历 / 半角转换 / 人名

XOR = 0xDA

# 系统 / 调试 / 共通脚本（非正文）
EXCLUDE = {"d00", "sts_deb", "sts_omake", "scene_play", "sts_cmn", "r1_t1_01"}

CAND_STARTS = (0x30, 0x34, 0x38, 0x3c, 0x2c, 0x28, 0x40, 0x24, 0x44, 0x48, 0x4c)


def strtab(d, p, hdr):
    """串表 -> [(byteOff, text)]；4 字节对齐 NUL 串，全字节 XOR 0xDA。"""
    so, eo = hdr[4], hdr[7]
    seg = bytes(v ^ XOR for v in d[p + so:p + eo])
    out, off = [], 0
    while off < len(seg):
        e = seg.find(b"\x00", off)
        if e < 0:
            break
        out.append((off, seg[off:e].decode("cp932", "replace")))
        off = (e + 1 + 3) & ~3
    return out


def _walk(c):
    """返回 (消费字节数, 是否成功)。尾部剩余全 0 视为正常结束。"""
    i = 0
    while i < len(c):
        if all(x == 0 for x in c[i:]):
            return i, True
        if i + 1 >= len(c):
            return i, False
        n = c[i]
        if n < 1 or n > 0x12:
            return i, False
        alen = (n - 1) * 2
        if i + 2 + alen > len(c):
            return i, False
        i += 2 + alen
    return i, True


def code_start(d, p, hdr):
    so = hdr[4]
    best_cov, got = -1, None
    for st in CAND_STARTS:
        if st >= so:
            continue
        used, ok = _walk(d[p + st:p + so])
        if ok:
            cov = so - st - used
            if best_cov < 0 or cov < best_cov:
                best_cov, got = cov, st
    return got


def disasm(c):
    i, out = 0, []
    while i < len(c):
        if all(x == 0 for x in c[i:]):
            break
        if i + 1 >= len(c):
            break
        n = c[i]
        if n < 1 or n > 0x12:
            break
        alen = (n - 1) * 2
        if i + 2 + alen > len(c):
            break
        out.append((i, c[i + 1], c[i + 2:i + 2 + alen]))
        i += 2 + alen
    return out


def frames(d, p, hdr):
    """-> [[str, str, ...], ...]，每个内层列表 = 一次点击（一框）。"""
    recs = strtab(d, p, hdr)
    wmap = {o // 4: s for o, s in recs}
    st = code_start(d, p, hdr)
    if st is None:
        return []
    cur, out = [], []
    for _, op, a in disasm(d[p + st:p + hdr[4]]):
        if op == 0x3E and len(a) >= 2:
            s = wmap.get(struct.unpack("<H", a[:2])[0])
            if s:
                cur.append(s)
        elif op in (0x3F, 0x41):
            if cur:
                out.append(cur)
                cur = []
    if cur:
        out.append(cur)
    return out


def extract(d):
    lines = []
    for p, hdr in O.iter_tobs(d):
        recs = strtab(d, p, hdr)
        name = next((s for s in [r[1] for r in recs[:3]] if s.lower().endswith(".tob")), "")
        name = name.replace("./../tob/", "")[:-4]
        if name in EXCLUDE:
            continue
        for box in frames(d, p, hdr):
            # op 0x3e 引用的必然是显示串；classify 只用来剥开头的样式码，判 skip 时保留原串
            parts = []
            for s in box:
                k, b = O.classify(s)
                parts.append(O.half_to_full(b if k == "text" else s))
            txt = O.fix_name("".join(parts))
            if txt.strip():
                lines.append(txt)
    return lines


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    out = extract(open(src, "rb").read())
    with open(dst, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("lines", len(out))
