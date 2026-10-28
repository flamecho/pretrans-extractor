#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]恋の花咲く百花園 text extract (Takuyo gss / SCR 3.00, unpacked OBJ).

Chain:
  NSP (PFS0) -> Program NCA (Titlekey crypto) -> RomFS
    romfs/1/OBJ/*.OBJ   = SCR 3.00 scripts (plaintext, 155 files; SCRDATA.ARC 为打包镜像，不必用)
    romfs/1/compile.OBJ = 编译器输出清单（分组与顺序旁证：■00共通 / ■01青柳朔良 / ■02宮澤梓恩 /
                          ■03井荻和真 / ■04藤村かなえ / ■05おまけ小説）
    romfs/1/SCRDATA.LST = SCR_FILE## -> OBJ\\*.OBJ 索引（155 条，与 OBJ 目录逐条吻合）

Order (L0): PRG_ROUTE.OBJ 的 `0x1e <file> <label>` 调用顺序（引擎自己的派发脚本），线性扫描去重。
  COM001-006 -> SKR001-026 -> SON001-026 -> KZM001-026 -> KNE001-017,019-026,018
  -> おまけ小説 NKT000-009 / SHU000-012 / KZM100-104

Line rules:
  0x5a  message text                -> one click = one line
  0xfc  message text with %s        -> %s <- slot 0c02 (given name そら)
  0xf0  chapter title card (扉文/章題, 直接上屏)
  0x5c  choices                     -> "text ,flag" (text = before last ASCII comma)
  in-string codes:
    '\\n' = in-box soft wrap   -> merged (also eats the following full-width space)
    '\\d' = click wait, box kept (B) -> segment break only when text follows, else dropped
    '\\c' = page clear + wait (A)    -> segment break
  '#rBASE|READ#' = ruby -> keep BASE only.
  Boxes that break into >=2 segments (A/B) are emitted as 双版对照: segments, then merged line
  (A,B,C,ABC). Single-segment boxes (the overwhelming majority) are emitted once.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_scr3 as D

ROMFS = "_work_koibana/romfs/1"
ROOT = os.path.join(ROMFS, "OBJ")
OUT = "提取结果/[NS-JP]恋の花咲く百花園.txt"

NAME_SLOTS = {"0c02": "そら", "1802": "恋花"}   # debug.OBJ 默认名表：1802=恋花 / 0c02=そら

MSG_OPS = {0x5A, 0xFC}
TITLE_OP = 0xF0
OPT_OP = 0x5C

MAIN = (["com%03d.OBJ" % i for i in range(1, 7)]
        + ["skr%03d.OBJ" % i for i in range(1, 27)]
        + ["son%03d.OBJ" % i for i in range(1, 27)]
        + ["kzm%03d.OBJ" % i for i in range(1, 27)]
        + ["kne%03d.OBJ" % i for i in range(1, 18)]
        + ["kne%03d.OBJ" % i for i in range(19, 27)]
        + ["kne018.OBJ"])

EXTRA = (["nkt%03d.OBJ" % i for i in range(0, 10)]
         + ["shu%03d.OBJ" % i for i in range(0, 13)]
         + ["kzm%03d.OBJ" % i for i in range(100, 105)])

RE_RUBY = re.compile(r"#r([^|#]*)\|([^#]*)#")
RE_CTRL = re.compile(r"\\[a-zA-Z]")
RE_PCT = re.compile(r"%s")
SEP = "\u0001"          # placeholder: full-width space swallowed by a soft wrap


def decode_ruby(s):
    return RE_RUBY.sub(lambda m: m.group(1), s)


def prep(raw, ops):
    """resolve macros/ruby/soft-wraps inside ONE segment"""
    s = decode_ruby(raw)
    if "%s" in s:
        it = iter([NAME_SLOTS.get(v, "") for t, v in ops if t == 6])
        s = RE_PCT.sub(lambda m: next(it, ""), s)
    # soft wrap: drop the code and the display indent that follows it
    s = s.replace("\\n\u3000", "").replace("\\n ", "").replace("\\n", "")
    return s.strip().strip("\u3000").strip()


def segments(raw, ops):
    """split one message into click segments (A='\\c' clear+wait, B='\\d' wait)"""
    s = raw
    while s.endswith("\\d"):        # plain end-of-message wait -> drop
        s = s[:-2]
    parts = re.split(r"\\c|\\d", s)
    return [p for p in (prep(x, ops) for x in parts) if p]


def lines_of(name, scripts, stats):
    res, err = D.disasm(scripts[name])
    if err:
        raise RuntimeError("%s disasm error %r" % (name, err))
    for off, op, size, ident, o in res:
        ss = [v for t, v in o if t == 3]
        if op in MSG_OPS and ss:
            segs = segments(ss[0], o)
            if not segs:
                continue
            stats[op] = stats.get(op, 0) + 1
            if len(segs) == 1:
                yield op, segs[0]
            else:
                stats["dual"] = stats.get("dual", 0) + 1
                for x in segs:
                    yield op, x
                yield op, "".join(segs)
        elif op == TITLE_OP and ss:
            for x in segments(ss[0], o):
                stats["title"] = stats.get("title", 0) + 1
                yield op, x
        elif op == OPT_OP and ss:
            for item in ss:
                txt = prep(item.rsplit(",", 1)[0], [])
                if txt:
                    stats["opt"] = stats.get("opt", 0) + 1
                    yield op, txt


def main():
    scripts = {}
    for fn in os.listdir(ROOT):
        b = open(os.path.join(ROOT, fn), "rb").read()
        if b.startswith(b"SCR 3.00"):
            scripts[fn] = b

    stats, out, missing = {}, [], []
    for fn in MAIN + EXTRA:
        if fn not in scripts:
            missing.append(fn)
            continue
        out.extend(lines_of(fn, scripts, stats))

    # structural dedupe: 0x5a (fixed literal default name) -> 0xfc ('%s' variable name),
    # identical after slot substitution = mutually exclusive branch pair, keep one.
    kept, dedup = [], 0
    for op, txt in out:
        if kept and kept[-1][1] == txt and (kept[-1][0], op) == (0x5A, 0xFC):
            dedup += 1
            continue
        kept.append((op, txt))

    lines = [t for _, t in kept]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print("missing:", missing)
    print("stats:", stats)
    print("dedupe(0x5a,0xfc):", dedup)
    print("lines:", len(lines))


if __name__ == "__main__":
    main()
