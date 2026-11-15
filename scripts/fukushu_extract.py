"""復讐帝國（PC-JP / KiriKiri + RAT 系自定义 LineMode）文本提取器。

源：RAR5 自解压 → `data.xp3`（标准 XP3，索引明文，`scripts/xp3.py` 可读）
    正文在 `scenario/*.ks`（**cp932 平文**，无加密），共 41 个；其中
    `scenario/replay/*` 10 个是回想入口，**逐行与主线重复**（实测 99〜100%）⇒ 不收。

DSL（KAG 系，标签用 `[...]`；本作不用 `[p]/[l]/[r]`）：

    *label / :label             标签（分段，无文本）
    ;… / #… / /…                注释（KAG 的 `;` 也算）
    [ev]/[se]/[bgm]/[wait]/…    演出指令
    【名前/表示名】[语音id]      页首名字行：名字走独立名字窗，[语音id] 是 voice/…ogg
    <正文>                       文本行；行内 `[...]` 是标签（语音 id、表情、演出），不是文本
    [seladd text="…"] [select]  选项（text 即按钮文字）

★ 断框判据（L0，来自引擎脚本 `system/LineMode.tjs` 的 `parseR()`，LINEMODE_VN 分支）：
    文本行结束（KAG 隐式 `[r]`）后遇到**第一个空行** ⇒ `parseP()`（改页＝等点击）；
    连续空行被忽略（`prevEmptyLine` 抑制）。⇒ **一页（空行分隔的段落）= 一次点击 = 一行**。
    `parseCh()` 另证：`【…】` 触发 `addParseTag("dispname")`（独立名字窗），**不进正文**。

成行口径：页内各行直接相接（框内换行＝排版换行），剥掉行内标签与页首名字。
    空页（只有标签/名字没有正文）丢弃。

用法：
    python scripts/fukushu_extract.py <data.xp3> <out.txt>
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3

NAME = re.compile(r'^【[^】]*】')
TAG = re.compile(r'\[[^\]]*\]')
SELADD = re.compile(r'^\[seladd\b([^\]]*)\]')
SELECT = re.compile(r'^\[select\b([^\]]*)\]')
ATTR = re.compile(r'text="([^"]*)"')


def page_text(lines):
    body = ''.join(lines).strip()
    return body


def parse_ks(text):
    """返回 [(kind, payload)]：kind='box' 正文一页；'opt' 选项一条。"""
    rows = []
    page = []

    def flush():
        nonlocal page
        if page:
            s = page_text(page)
            if s:
                rows.append(('box', s))
        page = []

    for raw in text.split('\n'):
        s = raw.rstrip('\r')
        if not s.strip():
            flush()                       # 空行＝改页（连续空行由 flush 幂等吸收）
            continue
        c = s[0]
        if c in ':*':                     # 标签行：分段
            flush()
            continue
        if c in ';#/@':                   # 注释（KAG 的 `;`）／RAT 予約コマンド `@`
            continue
        if c == '[':
            m = SELADD.match(s)
            if m:
                flush()
                t = ATTR.search(m.group(1))
                if t and t.group(1).strip():
                    rows.append(('opt', t.group(1)))
                continue
            m = SELECT.match(s)
            if m:
                flush()
                t = ATTR.search(m.group(1))
                if t and t.group(1).strip():
                    rows.append(('opt', t.group(1)))
                continue
            continue                      # 其它＝演出指令，无文本
        body = s
        m = NAME.match(body)              # 页首名字行 ⇒ 名字进独立窗，剔
        if m:
            body = body[m.end():]
        body = TAG.sub('', body).strip()
        if body:
            page.append(body)
    flush()
    return rows


def main():
    src, dst = sys.argv[1], sys.argv[2]
    x = XP3(src)
    # 排除：回想入口（逐行与主线重复 99〜100%）／宏定义与花标（无正文）／bootstrap（60B 二进制）
    SKIP = ('scenario/macro.ks', 'scenario/parsermacro.ks',
            'scenario/gototitle.ks', 'scenario/start.ks')
    files = sorted(n for n in x.files
                   if n.startswith('scenario/') and n.lower().endswith('.ks')
                   and '/replay/' not in n and n not in SKIP)
    lines = []
    stats = []
    for n in files:
        t = x.read(n).decode('cp932', 'replace')
        rows = parse_ks(t)                 # 已按出现顺序：正文页与选项混排
        box = sum(1 for k, _ in rows if k == 'box')
        opt = sum(1 for k, _ in rows if k == 'opt')
        lines += [p for _, p in rows]
        stats.append((n, box, opt))
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(lines) + '\n')
    for n, box, opt in stats:
        print('%-30s pages=%-4d opts=%d' % (n, box, opt))
    print('TOTAL pages=%d  bytes=%d  chars=%d'
          % (len(lines), os.path.getsize(dst), sum(len(s) for s in lines)))


if __name__ == '__main__':
    main()
