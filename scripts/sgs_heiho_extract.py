"""三国恋戦記～オトメの兵法！～ (NS-JP) —— SCRIPT.PAK 全文本提取

引擎：自研 `.PAK` ＋ UTF-16LE 明文脚本 ＋ 2 字节 opcode VM（`selfpak-utf16-vm` 第 4 例）

容器 romfs/SCRIPT.PAK（与本族前几例同形，块表细节见引擎册 §9）：
  0x00 u32 dataStart / 0x04 u32 块数 185 / 0x08 u32 1 / 0x0C u32 4
  0x20 u32 0x200（常量）/ 0x24 u32 名称表起点
  0x28 起 185 × {u32 未知, u32 size}；切分 start[i+1] = align4(start[i]+size[i])
  名称表：NUL 结尾；**本作混排 UTF-8 与 cp932**（173 号块名是 cp932）
  数据区后段 174〜184 是系统表块（_ARFLAG/_VARNUM/_VARSTR/_QUAKE/_TALKNAME/_CGMODE/
  _SCR_LABEL/_VOICE_PARAM/_BUILD_COUNT/_TASK/_KEYWORD）

脚本记录（L0）：
  消息    [u16 L][u16 0x0060][u16 × (L-1) 文本][u16 0]      L = 字数 + 1
  选项组  [u16 0x4000][u16 L][u16 × L 文本][u16 0]           组内 $d 分隔

文本内标记：
  名前@本文      名字与正文同串（**本作只有这一种**，无前导 @）
  $1 / $2        主角的姓 / 名 ⇒ 山田 / 花（vndb v2089 同一主角）
  $[漢字$/よみ$] 注音（读音用 `_` 分词，如 `げん_とく`）⇒ 只留漢字
  $K<数字>…$K0   用語辞典链接 ⇒ 去标记留字
  $S $C $d       字号 / 颜色 / 换行 ⇒ 去
  0x0A           软换行 ⇒ 合并
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct

ROMFS = r"<本地路径>"
PAK = os.path.join(ROMFS, "SCRIPT.PAK")
OUTDIR = os.path.join(VNTRANS_HOME, "提取结果")
NAME = "[NS-JP]三国恋戦記～オトメの兵法！～"
OUT = os.path.join(OUTDIR, NAME + ".txt")
WORK = os.path.join(VNTRANS_HOME, "_work_sgs")

SURNAME = "山田"
GIVEN = "花"

# 字体缺字位（游戏字体把字形放在制表符码位；读音由 $[字$/よみ$] 给出）
GAIJI = {
    "\u250f": "兗",   # ┏  $[┏州$/えんしゅう$]      ⇒ 兗州（青州・徐州・兗州）
    "\u2517": "譙",   # ┗  $[┗$/しょう$]郡         ⇒ 譙郡（豫州東部、孟徳の故郷）
    "\u2533": "鄴",   # ┳  $[┳$/ぎょう$]           ⇒ 鄴（銅雀台の地）
    "\u2523": "邳",   # ┣  $[下┣$/かひ$]           ⇒ 下邳（徐州）
}

MSG_TAG = 0x0060
OPT_TAG = 0x4000
N_SCRIPT = 174          # 0〜173 是脚本，174 起是系统表
IDX_GLOSSARY = 184


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
        raw = d[q:e]
        try:
            names.append(raw.decode("utf-8"))
        except UnicodeDecodeError:
            names.append(raw.decode("cp932", "replace"))
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
            if k == "1":
                out.append(SURNAME)
                i += 2
                continue
            if k == "2":
                out.append(GIVEN)
                i += 2
                continue
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
            i += 2
            continue
        if c in "\n\r\u2028\u2029":
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(GAIJI.get(c, c) for c in "".join(out))


def strip_cond(s):
    """去掉选项前的显示条件前缀 [(...),]（条件里可含 && 与嵌套括号）"""
    if s.startswith("[("):
        j = s.find("),]")
        if j >= 0:
            return s[j + 3:]
    return s


def ok_text(s):
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
        if head is None:
            if ruby is None:
                continue
            head = clean(ruby)
        ents.append((P, head, desc))
    ents.sort()
    return ents


def run():
    d, starts, sizes, names = load(PAK)
    lines = []
    stats = []
    nmsg = nopt = nskip = 0

    for idx in range(N_SCRIPT):
        s, sz = starts[idx], sizes[idx]
        u = struct.unpack_from("<%dH" % (sz // 2), d, s)
        k = 2
        c = o = 0
        while k < len(u) - 4:
            if u[k] == MSG_TAG:
                L = u[k - 1]
                if 4 <= L < 400 and k + L < len(u) and u[k + L] == 0:
                    raw = "".join(chr(x) for x in u[k + 1:k + L])
                    if "@" in raw:
                        nm, body = raw.split("@", 1)
                    else:
                        nm, body = "", raw
                    body = clean(nm) + clean(body)
                    if body.strip() and ok_text(body):
                        lines.append(body)
                        c += 1
                    elif body.strip():
                        nskip += 1
                    k += L
                    continue
            if 0x4000 <= u[k] <= 0x40FF:      # 选项组：标签低字节是组号，不恒定
                L = u[k + 1]
                if 1 < L < 3000 and k + 2 + L < len(u) and u[k + 2 + L] == 0:
                    raw = "".join(chr(x) for x in u[k + 2:k + 2 + L])
                    if "$d" not in raw or raw.startswith("\x60"):
                        k += 1
                        continue
                    for part in raw.split("$d"):
                        part = strip_cond(part)
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
    for P, head, desc in gloss:
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

    print("脚本 %d / 正文 %d 行 / 选项 %d 行 / 辞典 %d 条 / 丢弃误判 %d"
          % (N_SCRIPT, nmsg, nopt, len(glines), nskip))
    print("合计 %d 行 / %d 字节" % (len(lines) + len(glines), os.path.getsize(OUT)))


if __name__ == "__main__":
    run()
