# -*- coding: utf-8 -*-
"""
[JP]Perfect Prince (GimmickHouse 2002) — TextScript(c-system) 全文本提取器
=========================================================================
容器链: WinRAR SFX(RAR5) -> InstallShield i6 CAB -> script.saf
       script.saf = 312 entries / 24B 索引(4..7492) / 数据区自 8192 起(2048 对齐)
       每个文件 = 自描述头 + zlib 压缩流; 剧本块为 cp932 明文源码
       用 zlib 签名(78 9c/da/01) + eof 自校验定位全部有效块(287), 其中 158 为源码块

L0 断框判据 (代码级, 见解析报告):
  * '#...' / '##...' = 消息文本行(一次输出到消息窗)
  * 连续 # 行组 = 同一文本框 -> 合并为一行(框内换行合并, 不拆)
  * 空行 / 非 # 命令(voice,call,window,if,jump,messwait,makemenu...) = 框界
  * 行尾 '/p' = 页等待(点击) -> 该行即一框, 立即收框
  * 行内 '/p2' = 页等待 -> 按 /p2 分段, 每段一框
  * '##/p' = 空页等待, 无文本, 不产出行
  * '#/c$@c_XX|字面名|/c$@c_base' 纯名札行 = 独立名字窗 -> 剔除
  * '#　...' 前导全角空格 = 框内续行缩进, 合并时剥离
  * textmenu/picmenu str="..." = 选项 -> 每条独立一行
  * 含运行时变量($score/$day_str/...)的框 -> withheld/, 不猜填不混入成品

输出: 提取结果/[JP]Perfect Prince.txt  (utf-8-sig, LF, 一框一行)
      提取结果/withheld/[JP]Perfect Prince.txt  (变量未解项)
用法: python scripts/perfect_prince_extract.py [--saf PATH] [--out PATH]
"""
import argparse
import os
import re
import sys
import zlib
from collections import Counter

SAF_DEFAULT = r"_work_perfectprince/cab/Program_Executable_Files/script.saf"
OUT_DEFAULT = r"提取结果/[JP]Perfect Prince.txt"
WITHHELD_DEFAULT = r"提取结果/withheld/[JP]Perfect Prince.txt"

ZLIB_SIG = re.compile(rb"\x78(?:\x9c|\xda|\x01)")
SCRIPT_HEAD = re.compile(rb"^\s*;", re.S)
NAMEPLATE = re.compile(r"^#{1,2}/c\$@c_[A-Za-z0-9_]+\|[^|]*\|/c\$@c_base$")
RUNTIME_VAR = re.compile(r"\$(?:@[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)")
MENU_STR = re.compile(r'^\s*(?:textmenu|picmenu)\s+str="([^"]*)"')
# 系统 UI 菜单(音乐室/返回按钮): str 值含排版对齐空格(3+) 或为纯 ASCII
UI_MENU = re.compile(r"(?:^[\x20-\x7e]+$)|(?: {3,})")
LEADING_IDEO = "　"


def load_script_blocks(path):
    """返回 [(offset, cp932_text), ...]，按归档物理顺序。"""
    raw = open(path, "rb").read()
    mv = memoryview(raw)
    blocks = []
    for m in ZLIB_SIG.finditer(raw):
        off = m.start()
        try:
            d = zlib.decompressobj()
            out = d.decompress(mv[off:off + 600000])
            if not (d.eof and len(out) >= 64):
                continue
        except zlib.error:
            continue
        head = out[:200].lstrip()
        if not (head.startswith(b";") or b"Mode:" in head):
            continue
        try:
            txt = out.decode("cp932")
        except UnicodeDecodeError:
            continue
        blocks.append((off, txt))
    blocks.sort()
    return blocks


def strip_msg_prefix(line):
    """返回 (是否消息行, 去掉 # 前缀后的正文)。"""
    if line.startswith("##"):
        return True, line[2:]
    if line.startswith("#"):
        return True, line[1:]
    return False, line


def clean_segment(seg):
    """清掉一段消息正文里的引擎控制码/缩进。"""
    seg = seg.strip()
    # 名札宏若内联(非纯名札行)则保留字面名: /c$@c_xx|名前|/c$@c_base
    seg = re.sub(r"/c\$@c_[A-Za-z0-9_]+\|([^|]*)\|/c\$@c_base", r"\1", seg)
    # 前导全角空格 = 框内续行缩进
    seg = seg.lstrip(LEADING_IDEO)
    return seg.strip()


def extract_block(txt):
    """把一个源码块文本转成 [(frame_text, is_choice), ...]。"""
    frames = []
    pending = []          # 当前框内累计的段
    in_block_comment = False
    in_debug = False

    def flush():
        if pending:
            text = "".join(pending)
            if text:
                frames.append((text, False))
            pending.clear()

    for raw in txt.splitlines():
        line = raw.strip()
        # /* ... */ 块注释: 整块跳过(含被注释掉的旧版菜单/调试串)
        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
            continue
        if line.startswith("/*"):
            flush()
            if "*/" not in line:
                in_block_comment = True
            continue
        if not line:
            flush()
            continue
        # 行注释
        if line.startswith(";") or line.startswith("*"):
            flush()
            continue
        # 调试标签 :testN 段: 整段跳过直到 return(内含 #ON/#OFF 等调试串)
        if re.match(r"^:test\d+", line, re.I):
            flush()
            in_debug = True
            continue
        if in_debug:
            if line == "return" or line.startswith("return "):
                in_debug = False
            continue
        # 选项
        m = MENU_STR.match(line)
        if m:
            flush()
            val = m.group(1)
            # 系统 UI 菜单(对齐空格/纯 ASCII)不收, 其余为剧情选项
            if not UI_MENU.search(val):
                frames.append((val.strip(), True))
            continue
        is_msg, body = strip_msg_prefix(line)
        if not is_msg:
            # 任何非 # 命令 = 框界
            flush()
            continue
        # 纯名札行 = 独立名字窗 -> 剔除(但仍属同一框组, 不打断连续组)
        if NAMEPLATE.match(line):
            continue
        # 空页等待 '##/p'
        if body.strip() in ("/p", ""):
            flush()
            continue
        # 页等待: /p /P 与 /p2
        has_p2 = "/p2" in body.lower()
        if has_p2:
            parts = re.split(r"/p2", body, flags=re.I)
            for i, part in enumerate(parts):
                seg = clean_segment(part)
                if seg:
                    pending.append(seg)
                    flush()
                elif i == 0:
                    flush()
            continue
        has_p = re.search(r"/p(?!\d)", body, re.I) is not None
        body = re.sub(r"/p(?!\d)", "", body, flags=re.I)
        seg = clean_segment(body)
        if seg:
            pending.append(seg)
        if has_p:
            flush()
    flush()
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saf", default=SAF_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--withheld", default=WITHHELD_DEFAULT)
    ap.add_argument("--stats", default=r"_work_perfectprince/stats.txt")
    args = ap.parse_args()

    blocks = load_script_blocks(args.saf)
    all_frames = []
    per_block = []
    for off, txt in blocks:
        fr = extract_block(txt)
        per_block.append((off, len(fr)))
        all_frames.extend(fr)

    clean, held = [], []
    for text, is_choice in all_frames:
        if RUNTIME_VAR.search(text):
            held.append(text)
        else:
            clean.append(text)

    for path in (args.out, args.withheld):
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
    with open(args.out, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(clean) + "\n")
    with open(args.withheld, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(held) + "\n")

    widths = sorted(len(x) for x in clean)
    stats = [
        "script blocks: %d" % len(blocks),
        "frames total: %d" % len(all_frames),
        "clean frames: %d" % len(clean),
        "withheld frames (runtime var): %d" % len(held),
        "choices: %d" % sum(1 for _, c in all_frames if c),
        "width min/median/max: %d/%d/%d" % (widths[0], widths[len(widths) // 2], widths[-1]),
        "output bytes: %d" % os.path.getsize(args.out),
        "",
        "=== per-block frame counts (offset, count) ===",
    ]
    stats += ["%d %d" % (o, n) for o, n in per_block]
    if args.stats:
        os.makedirs(os.path.dirname(args.stats) or ".", exist_ok=True)
        with open(args.stats, "w", encoding="utf-8") as f:
            f.write("\n".join(stats) + "\n")
    print("\n".join(stats[:7]))
    print("\n=== first 15 clean frames ===")
    for x in clean[:15]:
        print("  ", x[:100])
    print("\n=== withheld ===")
    for x in held:
        print("  ", x[:100])


if __name__ == "__main__":
    main()
