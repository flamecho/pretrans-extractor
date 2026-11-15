# -*- coding: utf-8 -*-
"""[NS-JP]天使のプレゼント マール王国物語 —— talk.dat / script.dat → 成行

## talk.dat（台詞・調査テキスト）
```
0x00 u32 = 0x1896（6,294）
0x04 u32 = 0x1896
0x08 索引 6,294 × 32B：  +0 u16 / +2 u16 / +4 u32 / +8 u16 / +10 u16 /
                          +12 u32 / +16 u32 / +20 u32 / **+24 u32 文本偏移** / +28 u32
0x312D0 起为数据区（偏移相对此）—— 记录流，无长度前缀
```
记录流（L0）：
```
[<前缀>] 01 <cp932 正文> 00
```
`01` = 文本槽操作码（实测 11,749/11,812 处文本前恒为 01，其余 63 处是 ASCII 假命中）。
前缀的倒数第二字节区分**换页**：
  * `00`（上一句的终止符）⇒ 裸 `01` ⇒ **同一框的下一行**
  * 其它（`02 06 XX 01 01` / `02 05 29 06 XX 01 01` / `03 ...`）⇒ **强制换页（新框）**

**框高 3 行**（L1 验证）：以「强制换页」切段后，段内行数 3 的占绝大多数；
段长 ≥3 时 `len % 3 == 0` 占 **1,263/1,291 = 97.8%**（对照 H=2 → 66.2%、H=4 → 46.3%）。
逐行长度 中位 12 / 最大 27（＝框宽），与 3 行框自洽。

## script.dat（演出ナレーション）
```
0x00 u32 = 0xD98（3,480）… 后接 u32 偏移索引
文本槽： 32 <u8 L> <cp932 正文> 00         L = 正文字节数 + 1
```
663 槽 / 17,162 B，与 talk.dat 无重复串（正文覆盖 0 处未命中）。
"""
import re, struct, sys

ICON = re.compile(r'\|[0-9]')      # `|0`..`|3` = 内联图标（人間/人形使い/人形/モンスター）

TALK_DATA = 0x312D0
SCRIPT_OP = 0x32
BOX_LINES = 3


def load(path):
    return open(path, 'rb').read()


def talk_boxes(d):
    """按「文本槽 + 换页标记」还原成框，返回 [(框文本, 行数, 数据偏移)]。"""
    dat = d[TALK_DATA:]
    n = len(dat)
    boxes = []
    cur = []
    cur_n = 0
    start = None
    prev_end = -1                     # 上一个文本槽终止符之后的位置
    i = 0
    while i < n - 4:
        if dat[i] != 1:                      # 文本槽操作码
            i += 1
            continue
        # 试解：01 + 正文 + 00
        j = i + 1
        ok = True
        while j < n and dat[j] != 0:
            b = dat[j]
            if 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC:
                j += 2
            elif 0x20 <= b < 0x7F:
                j += 1
            else:
                ok = False
                break
        if not ok or j >= n:
            i += 1
            continue
        try:
            t = dat[i + 1:j].decode('cp932')
        except Exception:
            i += 1
            continue
        forced = (i != prev_end)            # 与上一槽不紧邻 ⇒ 中间有指令 ⇒ 强制换页
        if t and any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in t):
            if forced and cur:
                boxes.append((''.join(cur), cur_n, start))
                cur, cur_n = [], 0
            if not cur:
                start = i + 1
            cur.append(ICON.sub('', t))
            cur_n += 1
            if cur_n == BOX_LINES:
                boxes.append((''.join(cur), cur_n, start))
                cur, cur_n = [], 0
            prev_end = j + 1          # 只在「被采纳的槽」上推进，否则假命中会吞掉换页标记
        i = j + 1
    if cur:
        boxes.append((''.join(cur), cur_n, start))
    return boxes


def script_slots(d):
    """script.dat：`32 <u8 L> <正文> 00`，返回 [(起点, 终点, 文本)]。"""
    n = len(d)
    out = []
    i = 0
    while i < n - 3:
        if d[i] == SCRIPT_OP:
            L = d[i + 1]
            end = i + 2 + L
            if 3 <= L <= 0xFF and end <= n and d[end - 1] == 0:
                try:
                    t = d[i + 2:end - 1].decode('cp932')
                except Exception:
                    t = None
                if t and not any(ord(c) < 0x20 for c in t):
                    out.append((i, end, ICON.sub('', t)))
                    i = end
                    continue
        i += 1
    return out


def script_boxes(slots):
    """同一框 = 相邻（中间无其它指令）的连续 `32` 槽；有指令插入即换框。
    实测：旁白三连 `32` 之间无字节 ⇒ 同框；地图名之间夹着 `4d 03 …` ⇒ 各自成框。"""
    out = []
    cur = []
    for k, (a, b, t) in enumerate(slots):
        if cur and a != slots[k - 1][1]:
            s = ''.join(cur).strip()
            if s:
                out.append(s)
            cur = []
        cur.append(t)
    if cur:
        s = ''.join(cur).strip()
        if s:
            out.append(s)
    return out


if __name__ == '__main__':
    talk, script, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    boxes = talk_boxes(load(talk))
    rows = [b[0] for b in boxes]
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        for r in rows:
            f.write(r + '\n')
    print('talk: boxes=%d lines=%d' % (len(boxes), sum(b[1] for b in boxes)))
    slots = script_slots(load(script))
    sb = script_boxes(slots)
    with open(dst, 'a', encoding='utf-8', newline='\n') as f:
        for r in sb:
            f.write(r + '\n')
    print('script: slots=%d boxes=%d' % (len(slots), len(sb)))
    print('total output lines=%d' % (len(rows) + len(sb)))
