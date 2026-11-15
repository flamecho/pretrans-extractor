#!/usr/bin/env python3
"""Himauri Script Engine (.him) → 文本

依据：FritzTom/himauri-tools  editor.py（.him 头与包结构、0x33 / 0x34 串提取）
      CoffeeFlux/Fushigi-Tools parser.py / unpacker.py（HXP 容器与 LZ）

.him 文件头
  +0x00  8B  'Himauri\\0'
  +0x08  u24 文件总长（BE）
  +0x0B  12B  固定 `00 00 00 00 00 03 1E FF 00 54 FF 00`
  +0x17  u16 正文区起点（BE）= 30 + 3*偏移数
  +0x19  3B  `05 10 FF`
  +0x1C  u16 偏移数（BE）
  +0x1E  偏移表（每项 3B BE）
正文区 = 包序列，**包分隔符是字节对 `0A 0D`**，包第 3 字节 = 命令 id
  0x33  消息：... `00 01` <串> `00` ；串 = `名前\\n本文行…`（`\\n` 是字面的反斜杠+n）
  0x34  选项：前缀 `0A 0D 34 FF 02 01 FF 01` 时，其后到 `00` = 选项文本
  0x36  演出命令（bgm/bg/立絵/音声）：带 ASCII 资源名，不收
  0x32 / 0x35  控制（含跳转 INITIAL.HXP），不收

用法
  python scripts/himscript.py <dir_with_him> <out.txt>
"""
import os
import re
import sys

MSG = 0x33
OPT = 0x34
OPT_PREFIX = b"\x0a\x0d\x34\xff\x02\x01\xff\x01"


# 命令 id（包第 3 字节）。只有这些值才算真正的包起点。
CMD_IDS = {0x32, 0x33, 0x34, 0x35, 0x36}


def packets(d):
    """按 `0A 0D` 切包 —— 但 `0A 0D` 后面必须紧跟合法命令 id 才算分隔符。

    反例（sc20_1e022_a.him）：包头有 `ff 02 0E <u16 BE 递增序号>` 字段，序号走到 0x0A0D 时
    字节正好是 `0A 0D`，盲目按字节对切会把一条消息截成两半
    （实测把 `Numata Hiroshi\n'Himehara--no! I can't!...'` 整条切碎）。
    """
    sdo = int.from_bytes(d[0x17:0x19], "big")
    data = d[sdo:]
    if not data.startswith(b"\x0a\x0d"):
        return []
    idx = [0]
    i = 0
    n = len(data)
    while i < n - 2:
        if data[i] == 0x0A and data[i + 1] == 0x0D and data[i + 2] in CMD_IDS:
            if i != 0:
                idx.append(i)
            i += 3
            continue
        i += 1
    return [data[st:(idx[k + 1] if k + 1 < len(idx) else n)] for k, st in enumerate(idx)]


def msg_string(pk):
    """0x33 包 → 串（cp932）。起点＝首个 `00 01` 之后，终点＝`00`。"""
    j = pk.find(b"\x00\x01")
    if j < 0:
        return None
    t = pk[j + 2:]
    z = t.find(b"\x00")
    if z >= 0:
        t = t[:z]
    try:
        return t.decode("cp932")
    except UnicodeDecodeError:
        return None


def opt_string(pk):
    if not pk.startswith(OPT_PREFIX):
        return None
    t = pk[len(OPT_PREFIX):]
    z = t.find(b"\x00")
    if z >= 0:
        t = t[:z]
    try:
        return t.decode("cp932")
    except UnicodeDecodeError:
        return None


def merge(s):
    """`\\n`（字面反斜杠+n）是框内换行 ⇒ 按「一框一行」合并。
    英文换行点原本是空格，故合并用单空格，并压缩重复空格。"""
    parts = [p.strip() for p in s.split("\\n")]
    parts = [p for p in parts if p != ""]
    out = " ".join(parts)
    return re.sub(r" {2,}", " ", out).strip()


def scene_key(name):
    """场景阅读顺序：sc<N> → sca<N> → scend_*。"""
    m = re.match(r"^sc(\d+)", name)
    if m:
        return (0, int(m.group(1)), name)
    m = re.match(r"^sca(\d+)", name)
    if m:
        return (1, int(m.group(1)), name)
    return (2, 0, name)


def run(src_dir, out_path):
    files = [f for f in os.listdir(src_dir)
             if f.lower().endswith(".him") or open(os.path.join(src_dir, f), "rb").read(7) == b"Himauri"]
    files.sort(key=scene_key)
    lines = []
    stat = {"msg": 0, "opt": 0, "files": len(files), "dup_files": []}
    seen = set()
    for fn in files:
        d = open(os.path.join(src_dir, fn), "rb").read()
        # 整文件行序逐条全等 ⇒ 同一脚本为两个分支各存一份，只出一份（不是相似度，是全等）
        fl = [merge(msg_string(pk)) for pk in packets(d)
              if len(pk) > 2 and pk[2] == MSG and msg_string(pk)]
        key = tuple(x for x in fl if x)
        if key and key in seen:
            stat["dup_files"].append(fn)
            continue
        if key:
            seen.add(key)
        for pk in packets(d):
            if len(pk) < 3:
                continue
            cid = pk[2]
            if cid == MSG:
                s = msg_string(pk)
                if s is None:
                    continue
                ln = merge(s)
                if ln:
                    lines.append(ln)
                    stat["msg"] += 1
            elif cid == OPT:
                s = opt_string(pk)
                if s:
                    ln = merge(s)
                    if ln:
                        lines.append(ln)
                        stat["opt"] += 1
    with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[i] 文件 {stat['files']}  消息 {stat['msg']}  选项 {stat['opt']}  总行 {len(lines)} -> {out_path}")
    if stat["dup_files"]:
        print(f"[i] 整文件重复（已跳过）{len(stat['dup_files'])}: {stat['dup_files']}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    run(sys.argv[1], sys.argv[2])
