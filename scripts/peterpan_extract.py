"""QuinRose Qoo (PSV) —— [PSV-JP]新装版 お菓子な島のピーターパン 剧本成行。

链路：zip(app 树) → psvpfsparser -z <zRIF> → DATA/KS.QPI+KS.QPK (Qoo QPK, CZL/zlib)
      → KAG 风格 .ks (cp932, CRLF)

断框：L0＝`[message ...]…[/message]`（每块必带 window=，97% 带 face/bf/ef/mf ⇒ 清框重绘）
      一次块＝一框＝一次点击；块内软换行（裸换行/[br]）合并；
      选项＝`[select word="…"]` 一行一条；`[select name="…"]` 为图片式无字选项，跳过。
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpk import QPK  # noqa: E402

NAME_FIRST = "ウェンディ"     # vndb v4671 / c12556 Wendy Darling（Nameable 默认名）
NAME_FAMILY = "ダーリング"

ROUTES = [("pet", "peter"), ("joh", "john"), ("mic", "michael"),
          ("hoo", "hook"), ("sci", "scissor"), ("tnk", "tink")]

HEAD = (["prologue.ks"]
        + ["op01.ks", "op01_02.ks", "op01_03.ks", "op02.ks", "op02_02.ks", "op02_03.ks",
           "op03.ks", "op03_02.ks", "op04.ks", "op04_02.ks"]
        + ["com01.ks", "com02.ks", "com03.ks", "com_map.ks"])

# 共通お菓子会議：各线第 4/13/19 章调用一次，只在首次出现处并入
OKASHI = {4: ["okashi01.ks", "okashi01_2.ks"],
          13: ["okashi02.ks", "okashi02_2.ks"],
          19: ["okashi03.ks", "okashi03.ks", "okashi03_2.ks", "okashi03_bro.ks"]}

# 只带标签头的分文件（无 `;name.ks` 首行），挂在父文件之后
FRAG_AFTER = {
    "hoo01.ks": ["hoo01_08_a"],
    "hoo03.ks": ["hoo03_03_a"],
    "hoo05.ks": ["hoo05_05_a"],
    "hoo07.ks": ["hoo07_03_a"],
    "hoo11.ks": ["hoo11_05_a"],
    "pet14.ks": ["peter14_02.kds"],
    "sci_bes.ks": ["scissor_bestend_02"],
}

TAIL = ["tru01.ks", "tru02.ks", "tru03.ks", "tru04.ks", "tru05.ks", "tru06.ks", "tru07.ks",
        "tru08.ks", "tru09.ks", "tru10.ks", "tru11.ks", "tru11_02.ks", "tru12.ks", "tru13.ks",
        "tru14.ks", "tru15.ks", "tru15_02.ks", "tru_end.ks", "tru_end_02.ks", "tru_ext.ks",
        "com_bes.ks", "com_bes_bro.ks", "com_goo.ks", "com_bad01.ks", "com_bad02.ks",
        "com_bad02_bro.ks", "ter_end.ks", "joh_comp.ks", "mic_comp.ks", "michael_comp.ks",
        "hoo_comp.ks", "sci_comp.ks", "scissor_comp.ks", "tnk_comp.ks", "tink_comp.ks",
        "full_comp.ks", "deadend.ks"]

SKIP_NAME = {"op_movie", "開発用テスト"}

TOKEN_RE = re.compile(
    r"\[message\b([^\]]*)\](.*?)\[/message\]"
    r"|\[select\b([^\]]*)\]", re.S | re.I)


def clean(s):
    s = re.sub(r'\[print\b[^\]]*?value="firstname"[^\]]*\]', NAME_FIRST, s, flags=re.I)
    s = re.sub(r'\[print\b[^\]]*?value="familyname"[^\]]*\]', NAME_FAMILY, s, flags=re.I)
    s = s.replace("\r", "")
    lines = [l.strip() for l in s.split("\n")]
    lines = [l for l in lines if l and not l.startswith(";")]   # `;` 行＝未启用
    s = "".join(lines)
    s = re.sub(r"\[br\b[^\]]*\]", "", s, flags=re.I)             # 框内换行
    s = re.sub(r"\[/?f\b[^\]]*\]", "", s, flags=re.I)            # 字号强调
    s = re.sub(r"\[[^\]]*\]", "", s)                             # 兜底
    return s.strip().strip("\u3000").strip()


def strip_comments(t):
    """整行 `;` 注释先删（含被整块注释掉的 [message]…[/message]）"""
    return "\n".join(l for l in t.replace("\r", "").split("\n")
                     if not l.strip().startswith(";"))


def parse(txt):
    out = []
    for m in TOKEN_RE.finditer(txt):
        if m.group(2) is not None:
            s = clean(m.group(2))
            if s:
                out.append(("T", s))
        else:
            a = m.group(3)
            wm = re.search(r'\bword="([^"]*)"', a, re.I)
            if wm:
                s = clean(wm.group(1))
                if s:
                    out.append(("S", s))
            # name="sel_xx.png" ⇒ 图片式无字选项，跳过
    return out


def load():
    base = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(base, "..", "_work_peterpan", "dec", "DATA")
    q = QPK(os.path.join(root, "KS.QPI"), os.path.join(root, "KS.QPK"))
    entries = []          # [ {name, txt} ]
    for i, e in enumerate(q.entries):
        raw = q.extract(e)
        if raw[:4] == b"AKB\x00":
            continue
        t = raw.decode("cp932", "replace")
        m = re.match(r";\s*([0-9A-Za-z_.]+\.(?:ks|kds))", t)
        if m:
            nm = m.group(1)
        else:
            lm = re.search(r"^\s*\*([0-9A-Za-z_]+)", t, re.M)
            nm = lm.group(1) if lm else "#%d" % i
        entries.append({"idx": i, "name": nm, "txt": strip_comments(t)})
    return entries


def build_order(entries):
    pool = {}
    for k, e in enumerate(entries):
        pool.setdefault(e["name"], []).append(k)
    order, used = [], set()

    def take(nm):
        lst = pool.get(nm)
        if not lst:
            return
        k = lst.pop(0)
        used.add(k)
        order.append(k)

    def take_all(nm):
        while pool.get(nm):
            take(nm)

    for nm in HEAD:
        take(nm)
    first = True
    for pre, _ in ROUTES:
        for n in range(1, 20):
            if first and n in OKASHI:
                for nm in OKASHI[n]:
                    take(nm)
            take("%s%02d.ks" % (pre, n))
            take_all("%s%02d_02.ks" % (pre, n))
            for nm in FRAG_AFTER.get("%s%02d.ks" % (pre, n), []):
                take_all(nm)
        # 该线其余文件（bes/goo/ext/…）按名序
        rest = sorted({e["name"] for e in entries
                       if e["name"].startswith(pre) and any(pool.get(e["name"]))})
        for nm in rest:
            take_all(nm)
        for nm in FRAG_AFTER.get("%s_bes.ks" % pre, []):
            take_all(nm)
        first = False
    for nm in TAIL:
        take_all(nm)
    left = [k for k in range(len(entries)) if k not in used]
    return order, left


def main():
    entries = load()
    order, left = build_order(entries)

    lines, nt, ns = [], 0, 0
    per = []
    for k in order:
        e = entries[k]
        got = parse(e["txt"])
        t = sum(1 for a, _ in got if a == "T")
        s = sum(1 for a, _ in got if a == "S")
        if e["name"] in SKIP_NAME or (not t and not s):
            per.append((e["name"], 0, 0))
            continue
        per.append((e["name"], t, s))
        nt += t
        ns += s
        lines.extend(v for _, v in got)
    for k in left:
        print("!! 未排入:", entries[k]["name"])
    print("条目", len(entries), "排入", len(order), "余", len(left))
    print("text", nt, "select", ns, "total", len(lines))

    base = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(base, "..", "提取结果",
                       "[PSV-JP]新装版 お菓子な島のピーターパン ~Sweet Never Land~.txt")
    with io.open(out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("->", out)
    with io.open(os.path.join(base, "..", "_work_peterpan", "per_file.tsv"),
                 "w", encoding="utf-8", newline="\n") as f:
        for nm, t, s in per:
            f.write("%s\t%d\t%d\n" % (nm, t, s))


if __name__ == "__main__":
    main()
