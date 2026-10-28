"""QuinRose Qoo (PSV) —— [PSV-JP]源氏恋絵巻 剧本成行。

链路：zip(app 树) → psvpfsparser -k → DATA/KS.QPI+KS.QPK (Qoo QPK, CZL/zlib)
      → KAG 风格 .ks (cp932, CRLF)

断框：L0＝`[message ...]…[/message]`（每块必重设 window/face/bf/ef/mf ⇒ 清框重绘）
      一次块＝一框＝一次点击；块内软换行（裸换行）合并；
      选项＝`[select word="…"]` 一行一条；`[select name="…"]` 为图片式无字选项，跳过。
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpk import QPK  # noqa: E402

NAME = "千影"          # vndb v16509 c53210（Nameable / 默认名）

# 剧本顺序：序（prologue→序一/序二）→ 共通 → 六条线（CSV3 顺序）→ 副角色 → 终
ORDER = [
    "prologue.ks",
    "op01.ks", "op01_1.ks", "op01_2.ks", "op02.ks", "op02_1.ks", "op02_2.ks",
    "com00.ks", "com01.ks", "com03.ks",
    "mur01.ks", "mur02.ks", "mur03.ks", "mur04.ks", "mur05.ks", "mur06.ks",
    "mur07.ks", "mur08.ks", "mur09.ks", "mur10.ks", "mur11.ks", "mur12.ks",
    "mur13.ks", "mur14.ks",
    "aoi01.ks", "aoi02.ks", "aoi03.ks", "aoi04.ks", "aoi05.ks", "aoi06.ks",
    "aoi07.ks", "aoi08.ks", "aoi09.ks", "aoi10.ks", "aoi11.ks", "aoi12.ks",
    "aoi13.ks",
    "aka01.ks", "aka02.ks", "aka03.ks", "aka04.ks", "aka05.ks", "aka05_2.ks",
    "aka06.ks", "aka07.ks", "aka08.ks", "aka09.ks", "aka10.ks", "aka11.ks",
    "aka12.ks", "aka12_2.ks", "aka13.ks",
    "obo01.ks", "obo02.ks", "obo03.ks", "obo04.ks", "obo05.ks", "obo06.ks",
    "obo07.ks", "obo08.ks", "obo09.ks", "obo10.ks", "obo11.ks", "obo12.ks",
    "obo13.ks",
    "yug01.ks", "yug02.ks", "yug03.ks", "yug04.ks", "yug05.ks", "yug06.ks",
    "yug07.ks", "yug08.ks", "yug09.ks", "yug10.ks", "yug11.ks", "yug12.ks",
    "yug12_2.ks", "yug13.ks",
    "rok01.ks", "rok02.ks", "rok03.ks", "rok03_2.ks", "rok04.ks", "rok05.ks",
    "rok06.ks", "rok07.ks", "rok08.ks", "rok09.ks", "rok10.ks", "rok11.ks",
    "rok12.ks", "rok13.ks",
    "tok01.ks", "tok02.ks", "tok03.ks", "tok04.ks", "tok05.ks", "tok06.ks",
    "tok07.ks", "tok08.ks", "tok09.ks", "tok10.ks", "tok11.ks", "tok12.ks",
    "tok12_2.ks", "tok13_2.ks", "tok13.ks",
    "hik_fuz01.ks", "hik_fuz02.ks", "hik_fuz03.ks", "hik_fuz04.ks", "hik_fuz05.ks",
    "yui01a.ks", "yui01b.ks", "yui02a.ks", "yui02b.ks", "yui03a.ks", "yui03b.ks",
    "final.ks",
]

WITH_BACKLOG = "--backlog" in sys.argv   # 默认不收 [backlog]（文字已烘入全屏图，属日志载体）

TOKEN_RE = re.compile(
    r"\[message\b([^\]]*)\](.*?)\[/message\]"
    r"|\[select\b([^\]]*)\]"
    r"|\[backlog\b([^\]]*)\](.*?)\[/backlog\]",
    re.S | re.I)


def clean(s):
    s = re.sub(r'\[print\b[^\]]*?value="firstname"[^\]]*\]', NAME, s, flags=re.I)
    s = s.replace("\r", "")
    lines = [l.strip() for l in s.split("\n")]
    lines = [l for l in lines if l and not l.startswith(";")]   # `;` 行＝未启用
    s = "".join(lines)
    s = re.sub(r"\[/?f\b[^\]]*\]", "", s, flags=re.I)           # 字号强调
    s = re.sub(r"\[br\b[^\]]*\]", "", s, flags=re.I)            # 框内换行
    s = re.sub(r"\[[^\]]*\]", "", s)                            # 兜底
    return s.strip().strip("\u3000").strip()


def parse(txt):
    out = []
    for m in TOKEN_RE.finditer(txt):
        if m.group(2) is not None:
            s = clean(m.group(2))
            if s:
                out.append(("T", s))
        elif m.group(3) is not None:
            wm = re.search(r'\bword="([^"]*)"', m.group(3), re.I)
            if wm:
                s = clean(wm.group(1))
                if s:
                    out.append(("S", s))
            # name="sel_xx.png" ⇒ 图片式无字选项，跳过
        elif WITH_BACKLOG and m.group(5) is not None:
            s = clean(m.group(5))
            if s:
                out.append(("T", s))
    return out


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(base, "..", "_work_genji", "dec", "DATA")
    q = QPK(os.path.join(root, "KS.QPI"), os.path.join(root, "KS.QPK"))

    files = {}
    for e in q.entries:
        raw = q.extract(e)
        if raw[:1] != b";":
            continue                     # AKB 二进制
        m = re.match(rb";\s*([0-9A-Za-z_]+\.ks)", raw)
        if not m:
            continue
        files[m.group(1).decode("ascii")] = raw.decode("cp932", "replace")

    missing = [f for f in ORDER if f not in files]
    extra = [f for f in files if f not in ORDER]
    print("files", len(files), "ordered", len(ORDER), "missing", missing, "extra", extra)

    lines, nt, ns = [], 0, 0
    for fn in ORDER:
        for kind, s in parse(files[fn]):
            lines.append(s)
            if kind == "T":
                nt += 1
            else:
                ns += 1
    print("text", nt, "select", ns, "total", len(lines))

    out = os.path.join(base, "..", "提取结果", "[PSV-JP]源氏恋絵巻.txt")
    with io.open(out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("->", out)


if __name__ == "__main__":
    main()
