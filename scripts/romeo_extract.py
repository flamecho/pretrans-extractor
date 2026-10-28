"""QuinRose Qoo (PSV) —— ロミオVSジュリエット 剧本成行。

链路：zip → PFS 解密 (psvpfsparser) → DATA/KS.QPI+KS.QPK (Qoo QPK, CZL/zlib)
      → KAG 风格 .ks (cp932)

断框：L0＝`[message ...]…[/message]` 一次＝一框＝一次点击（框内换行/[br] 合并）；
      选项＝`[select word="…"]` 一行一条；`[select name="…"]` 为图片选项，跳过。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qpk import QPK  # noqa: E402

FULL = "ジュリエット"          # vndb c12544 default（firstname）
SURNAME = "キャピュレット"

SKIP_FILES = ("278", "279", "280", "281", "282")   # ; 開発用テスト

MSG_RE = re.compile(r"\[message\b([^\]]*)\](.*?)\[/message\]", re.S | re.I)
SEL_RE = re.compile(r"\[select\b([^\]]*)\]", re.I)
TOKEN_RE = re.compile(r"\[message\b[^\]]*\].*?\[/message\]|\[select\b[^\]]*\]", re.S | re.I)


def clean(s):
    s = re.sub(r'\[print\b[^\]]*?value="([A-Za-z_]+)"[^\]]*\]', FULL, s, flags=re.I)
    s = re.sub(r"\[br\b[^\]]*\]", "", s, flags=re.I)
    s = re.sub(r"\[/?f\b[^\]]*\]", "", s, flags=re.I)
    s = re.sub(r"\[/?[A-Za-z_]+\b[^\]]*\]", "", s)
    s = s.replace("\r", "").replace("\n", "")
    s = re.sub(r"[ \t\u3000]+", " ", s)
    return s.strip()


def parse(txt):
    out = []
    for m in TOKEN_RE.finditer(txt):
        tok = m.group(0)
        if tok.lower().startswith("[message"):
            body = re.search(r"\[message\b[^\]]*\](.*?)\[/message\]", tok, re.S | re.I).group(1)
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            lines = [l for l in lines if not l.startswith(";")]   # 注释行＝未启用
            if not lines:
                continue
            s = clean("".join(lines))
            if s:
                out.append(s)
        else:
            am = re.search(r'\bword="([^"]*)"', tok, re.I)
            if am:
                s = clean(am.group(1))
                if s:
                    out.append(s)
    return out


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(base, "..", "_work_romeo", "dec", "DATA")
    q = QPK(os.path.join(root, "KS.QPI"), os.path.join(root, "KS.QPK"))
    lines = []
    files = 0
    for idx, e in enumerate(q.entries):
        try:
            raw = q.extract(e)
        except Exception:
            continue
        if not raw or raw[:4] == b"AKB\x00":
            continue
        if raw[:1] != b";":
            continue
        head = raw[:40].decode("cp932", "replace")
        if any(k in head for k in SKIP_FILES):
            pass
        if re.search(r"開発用テスト", raw[:200].decode("cp932", "replace")) or \
           re.search(r'window="test"', raw.decode("cp932", "replace")):
            continue
        txt = raw.decode("cp932", "replace")
        got = parse(txt)
        files += 1
        lines.extend(got)
    print("files", files, "lines", len(lines))
    out = os.path.join(base, "..", "提取结果", "[PSV-JP]ロミオＶＳジュリエット.txt")
    with open(out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("->", out)


if __name__ == "__main__":
    main()
