"""三国恋戦記～思いでがえし～＋学園恋戦記 (NS-JP) —— SCRIPT.PAK 全文本提取

容器 romfs/SCRIPT.PAK：
  [u32 dataStart][u32 count][u32 1][u32 x][0x10..0x1F 全 0]
  [0x20: u32 0x600][0x24: u32 nameTableOff]
  [0x28: count × 8B (u32 a, u32 size)]
  [nameTableOff: count 个 NUL 结尾 UTF-8 名称]（尾部接引擎系统变量名表 _build_count/_arflag/…）
  数据区：按条目顺序平铺，每本 size 字节，起点 4 字节对齐 ⇒ 末条结束正好 = 文件尾（闭合）

脚本 = u16 指令流，文本 UTF-16LE
  消息（L0）：[u16 0x0323][u16 a][u16 b][u16 c][u16 L][u16 × L][u16 0]
      L = 文本 u16 单元数（不含 NUL）；实测 3〜121，中位 21
  选项组：  [u16 0x4000][u16 L][u16 × L][u16 0]，组内 $d 分隔
  用語辞典：条目 470 `_keyword`，每条 = [u16 id][u16 nLen][語][00]
            [u16 rLen][$[語$/よみ$]][00][u16 dLen][【分類】$S$C$d解説][00]

文本内标记：
  @名前@本文       独立名字窗（名前可为 $(n) 宏）⇒ 去名保正文
  $(2)=姓 $(3)=名   玩家可改名 ⇒ 山田 / 花（vndb v12438・v21792）
  $[漢字$/よみ$]   注音 ⇒ 保留漢字
  $K<数字>…$K0     用語辞典链接 ⇒ 去标记留字
  $S $C $d         字号 / 颜色 / 换行 ⇒ 去
  0x0A             软换行 ⇒ 合并（框内换行）
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct

ROMFS = r"<本地路径>"
PAK = os.path.join(ROMFS, "SCRIPT.PAK")
OUTDIR = os.path.join(VNTRANS_HOME, "提取结果")
NAME = "[NS-JP]三国恋戦記～思いでがえし～＋学園恋戦記"
OUT = os.path.join(OUTDIR, NAME + ".txt")
WORK = os.path.join(VNTRANS_HOME, "_work_sgk")

SURNAME = "山田"
GIVEN = "花"

# 字体缺字位（游戏字体把下列常用漢字的字形放在制表符码位，正文里的读法由 $[字$/よみ$] 给出）
GAIJI = {
    "\u250f": "兗",   # ┏  $[┏州$/えんしゅう$]   ⇒ 兗州
    "\u252b": "涿",   # ┫  $[┫$/たく$]郡         ⇒ 涿郡
    "\u2525": "犍",   # ┥  $[┥為$/けんい$]郡     ⇒ 犍為郡
    "\u251d": "敔",   # ┝  $[┝$/ぎょ$]（楽曲の終わりに虎の背をこする楽器）
    "\u2530": "柷",   # ┰  $[┰$/しゅく$]（楽曲の始めに打つ楽器）
    "\u2533": "鄴",   # ┳  $[┳$/ぎょう$] 銅雀台の地
}

OP_MSG = 0x0323
OP_OPT = 0x4000
IDX_GLOSSARY = 470


def load(pak):
    d = open(pak, "rb").read()
    data_off, count = struct.unpack_from("<2I", d, 0)
    root = struct.unpack_from("<2I", d, 0x20)
    table = struct.unpack_from("<%dI" % (count * 2), d, 0x28)
    sizes = [table[2 * i + 1] for i in range(count)]
    starts, o = [], data_off
    for s in sizes:
        starts.append(o)
        o = (o + s + 3) & ~3
    names, q = [], root[1]
    for _ in range(count):
        e = d.index(b"\0", q)
        names.append(d[q:e].decode("utf-8", "replace"))
        q = e + 1
    assert o == len(d), ("未闭合", hex(o), hex(len(d)))
    return d, starts, sizes, names


def clean(t):
    out = []
    i, n = 0, len(t)
    while i < n:
        c = t[i]
        if c == "$" and i + 1 < n:
            k = t[i + 1]
            if k == "(":
                j = t.find(")", i)
                if j < 0:
                    i += 2
                    continue
                num = t[i + 2:j]
                out.append(SURNAME if num == "2" else GIVEN if num == "3" else "")
                i = j + 1
                continue
            if k == "[":
                j = t.find("$/", i)
                k2 = t.find("$]", i)
                if j < 0 or k2 < 0:
                    i += 2
                    continue
                out.append(t[i + 2:j])
                i = k2 + 2
                continue
            if k == "K":
                j = i + 2
                while j < n and t[j].isdigit():
                    j += 1
                i = j
                continue
            i += 2          # $d / $S / $C …
            continue
        if c in "\n\r\u2028\u2029":
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(GAIJI.get(c, c) for c in "".join(out))


def split_name(t):
    if t.startswith("@"):
        j = t.find("@", 1)
        if j > 0:
            return t[1:j], t[j + 1:]
        return None, t[1:]
    return None, t


def ok_text(s):
    """排除误判记录：控制符 / PUA / 半角片假名 一律视为非正文"""
    for c in s:
        o = ord(c)
        if o < 0x20 or 0x7F <= o <= 0x9F:
            return False
        if 0xE000 <= o <= 0xF8FF:
            return False
        if 0xFF61 <= o <= 0xFF9F:
            return False
    return True


def parse_glossary(d, s, size):
    def u16(off):
        return struct.unpack_from("<H", d, s + off)[0]

    def txt(off, L):
        return d[s + off:s + off + L * 2].decode("utf-16le", "replace")

    ents = []
    for P in range(2, size - 8, 2):
        L3 = u16(P - 2)
        if not (5 < L3 < 500) or P + L3 * 2 + 2 > size:
            continue
        if u16(P) != 0x3010 or u16(P + L3 * 2) != 0:
            continue
        desc = txt(P, L3)
        if u16(P - 4) != 0:
            continue
        ruby, pos = None, None
        for L2 in range(1, 90):
            q = P - 6 - L2 * 2
            if q < 2:
                break
            if u16(q) == L2:
                r = txt(q + 2, L2)
                if r.startswith("$[") and "$]" in r:
                    ruby, pos = r, q
                    break
        head = None
        if pos is not None and u16(pos - 2) == 0:
            for L1 in range(1, 60):
                q = pos - 4 - L1 * 2
                if q < 2:
                    break
                if u16(q) == L1:
                    t = txt(q + 2, L1)
                    if t and all(ord(c) > 0x20 for c in t):
                        head = t
                        break
        if head is None:            # 无独立语条：该串本身即「$[语$/よみ$]＋后缀」
            if ruby is None:
                continue
            head = clean(ruby)
        ents.append((P, head, ruby, desc))
    ents.sort()
    return ents


def run():
    d, starts, sizes, names = load(PAK)
    lines = []
    stats = []
    nmsg = nopt = nskip = 0

    order = [i for i in range(len(names)) if i not in range(455, len(names))]
    for idx in order:
        s, sz = starts[idx], sizes[idx]
        if d[s:s + 4] != b"\x04\x00\x1a\x00":
            stats.append("%d\t%s\tSKIP(非脚本)\t%d" % (idx, names[idx], sz))
            continue
        if names[idx] == "test":
            stats.append("%d\t%s\tSKIP(debug)\t%d" % (idx, names[idx], sz))
            continue
        u = struct.unpack_from("<%dH" % (sz // 2), d, s)
        k = 14
        c = o = 0
        while k < len(u) - 6:
            if u[k] == OP_MSG:
                L = u[k + 4]
                if 0 < L < 3000 and k + 5 + L < len(u) and u[k + 5 + L] == 0:
                    raw = "".join(chr(x) for x in u[k + 5:k + 5 + L])
                    nm, body = split_name(raw)
                    body = clean(body)
                    if nm:
                        body = clean(nm) + body
                    if body.strip() and ok_text(body):
                        lines.append(body)
                        c += 1
                    elif body.strip():
                        nskip += 1
                    k += 5 + L
                    continue
            if u[k] == OP_OPT and k + 2 < len(u):
                L = u[k + 1]
                if 1 < L < 3000 and k + 2 + L < len(u) and u[k + 2 + L] == 0:
                    raw = "".join(chr(x) for x in u[k + 2:k + 2 + L])
                    for part in raw.split("$d"):
                        part = re.sub(r"^\[\([^)]*\),\]", "", part)   # 选项前置显示条件
                        p = clean(part)
                        if p.strip() and ok_text(p):
                            lines.append(p)
                            o += 1
                    k += 2 + L
                    continue
            k += 1
        nmsg += c
        nopt += o
        stats.append("%d\t%s\tmsg=%d\topt=%d\t%d B" % (idx, names[idx], c, o, sz))

    gloss = parse_glossary(d, starts[IDX_GLOSSARY], sizes[IDX_GLOSSARY])
    glines = []
    for P, head, ruby, desc in gloss:
        body = clean(desc)
        if body.strip() and ok_text(body):
            glines.append("【%s】%s" % (head, body))

    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        for ln in lines:
            f.write(ln + "\n")
        for ln in glines:
            f.write(ln + "\n")

    with open(os.path.join(WORK, "stats.tsv"), "w", encoding="utf-8") as f:
        f.write("\n".join(stats))
        f.write("\n\n# glossary %d 条\n" % len(glines))
        for P, head, ruby, desc in gloss:
            f.write("%d\t%s\t%s\n" % (P, head, ruby or ""))

    print("脚本 %d / 正文 %d 行 / 选项 %d 行 / 辞典 %d 条 / 丢弃误判 %d"
          % (len(order), nmsg, nopt, len(glines), nskip))
    print("合计 %d 行 / %d 字节" % (len(lines) + len(glines), os.path.getsize(OUT)))


if __name__ == "__main__":
    run()
