# -*- coding: utf-8 -*-
"""[JP]Recall (KiriKiri / DropWave OTag 加扰 .ks) 全文本提取器。

流程：
  1. xp3.py 解 XP3 取 .ks（已解 zlib）→ 仍是 OTag 加扰流
  2. OTag 解扰（header `FE FE <mode> FF FE`；mode 1 = 每个 UTF-16LE 单元相邻比特互换，可逆）
  3. 解码 UTF-16LE → 标准 KAG3 脚本
  4. KAG 解析：box 以 [p]/[e]/[er]/[ct]/[cm] 为页界（一次点击＝一个文本框）；
     [r]/[l]=框内换行(不点击)⇒合并；[waitclick]=框内真点击⇒多段(双版)；
     [name]=独立名字窗(剔除)；[iscript]…[endscript] 为 TJS 代码(剔除)；
     [link]…[endlink] / [choice]=选项；[locate](x=/y= 定位文本，如合成一覧表逐行)⇒独立成行。
  5. 输出：每框＝一行（框内 [r]/[l] 换行已合并）；框内 [waitclick] 多段＝双版（各段行，不附合并行）；
     [locate] 定位文本独立成行。单框＝一行。

用法：python scripts/recall_extract.py
"""
import sys, os, re, io
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
OUT = os.path.join(VNTRANS_HOME, "提取结果/[JP]Recall.txt")

# ---- OTag 解扰 ----------------------------------------------------------------
def descramble(data: bytes) -> bytes:
    out = bytearray(data)
    n = len(out) // 2 * 2
    mode = out[2] if len(out) >= 3 and out[0:2] == b'\xfe\xfe' else None
    if mode == 1:
        for i in range(0, n, 2):
            c = out[i] | (out[i + 1] << 8)
            c = ((c & 0xAAAA) >> 1) | ((c & 0x5555) << 1)
            out[i] = c & 0xFF
            out[i + 1] = (c >> 8) & 0xFF
        return bytes(out[5:])           # 剥掉 FE FE 01 FF FE 头
    # mode 0 / 其他：原样（本作全 mode 1，留作兼容）
    return data


def read_ks(xp3, name):
    b = xp3.read(name)
    if b[:2] != b'\xfe\xfe':
        # 非加扰兜底：直接按字节解
        return b.decode('utf-16-le', 'replace')
    d = descramble(b)
    return d.decode('utf-16-le', 'replace')


# ---- KAG 解析 ----------------------------------------------------------------
TAG = re.compile(r'\[([^\[\]\r\n]{0,200})\]')
PAGE_BREAK = {'p', 'np', 'e', 'er', 'ct', 'cm', 'pe', 'ple', 'clear'}
# 本作语义（用户 2026-11-08 终审）：`[r]`/`[l]` 是**框内换行（不点击）** ⇒ 并入当前段（合并成一行）；
# 真正的一次点击＝一个文本框（框界 [e]/[p]/[er]/[ct]/[cm]）；框内真点击用 [waitclick]（多段＝双版）；
# `[locate]`（带 x=/y= 定位的独立文本，如合成一覧表的逐行）⇒ 独立成行。
SEG_BREAK = {'waitclick', 'locate'}
NOCLICK_NL = {'l', 'r'}
NAME_TAG = {'name', 'namelay'}
SCRIPT = {'iscript'}
# 上屏显示标签（任一出现 ⇒ 该 .ks 含渲染台词/导航，须纳入；全无 ⇒ 引擎 plugin / 宏·变量·函数定义 /
# 战斗动作逻辑等纯代码文件，日文仅存于注释/TJS/宏定义，非渲染台词 ⇒ 排除）。
DISP_TAGS = ('e', 'p', 'er', 'ct', 'cm', 'pe', 'ple', 'clear',
            'r', 'waitclick', 'link', 'l', 'select', 'button')

def split_tags(s):
    out, i, n = [], 0, len(s)
    buf = ''
    while i < n:
        c = s[i]
        if c != '[':
            buf += c; i += 1; continue
        # 找配平 ]
        j, depth = i, 0
        while j < n:
            if s[j] == '[':
                depth += 1
            elif s[j] == ']':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            # 未配平：本 [ 起的控制标签残缺（如缺收尾 ]，实证：[playse storage="空間歪み"[ws]）→
            # 当作标签整体丢弃，并从下一个 [ 或行尾继续，避免把标签名/属性当成文本泄漏进正文。
            k = s.find('[', i + 1)
            i = k if k != -1 else n
            continue
        if buf:
            out.append(('text', buf)); buf = ''
        inner = s[i + 1:j]
        m = re.match(r'([^\[\]\s=]+)', inner)
        out.append(('tag', m.group(1) if m else '', inner))
        i = j + 1
    if buf:
        out.append(('text', buf))
    return out


def clean_text(t):
    # KAG 行末 \ ＝排版换行（不点击）→ 去掉
    t = t.replace('\\', '')
    t = t.replace('\r', '').replace('\n', '')
    # 行首全角空格（[r]/行首缩进）在“框内换行合并”语境下去掉，避免伪空格
    t = t.lstrip('\u3000')
    return t


def parse_kag(text):
    """返回 (boxes, opts)。boxes = [[seg, seg, ...], ...]，单框多段即一框多次点击。

    页面/段界语义（已用正常剧本 EDカオス.ks 验证：[e]=379 页界、[r]=288 段界）：
      - PAGE_BREAK([p]/[e]/[er]/[ct]/[cm]/[pe]/[ple]/[clear]) = 文本框(页)界，flush 一框
      - SEG_BREAK([r]/[waitclick]) = 一次点击=一段，框内换行（同框多次点击）
      - NOCLICK_NL([l]) = 框内无点击换行，并入当前段
      - NAME_TAG([name]/[namelay]) = 独立名字窗，剔除（本作全为属性式 [name t=...]，不漏名）
      - [link]…[endlink] = 导航链接，内部文本进 opts（选项）
      - [choice a=/b=/c=/d=] = 玩家选择，a/b/c/d 属性文本进 opts
      - [ch text="…"] = 条件内联词，作为内联文本并入当前段
      - [iscript]…[endscript] = TJS 代码，剔除
    关键：文件末尾若仍累积未 flush 的段（战斗/会话池文件以 [r] 为主、无收尾页界），
          必须补 flush_box()，否则末尾一大段对话会整体丢失。
    """
    boxes, opts = [], []
    segs, cur = [], []
    in_script = False
    in_link = False

    def flush_seg():
        if cur:
            segs.append(''.join(cur))
            cur.clear()

    def flush_box():
        flush_seg()
        if segs:
            boxes.append(list(segs))   # 副本，避免后续 segs.clear() 清空已存 box
        segs.clear()

    for raw in text.split('\n'):
        line = raw.rstrip('\r')
        s = line.strip()
        if in_script:
            if 'endscript' in s.lower():
                in_script = False
            continue
        if not s or s.startswith(('*', ';')):
            continue
        if s.lower().startswith(('@iscript', '[iscript')):
            in_script = True
            continue
        if s.startswith('@'):
            line = '[' + s[1:].strip() + ']'
        for tok in split_tags(line):
            if tok[0] == 'text':
                t = clean_text(tok[1])
                if not t.strip():
                    continue
                if in_link:
                    opts.append(t)          # 链接内文本＝选项
                else:
                    cur.append(t)
            else:
                name = tok[1]
                if name in NAME_TAG:
                    continue                 # 独立名字窗，剔除
                if name == 'link':
                    in_link = True
                elif name == 'endlink':
                    in_link = False
                elif name == 'ch':
                    m = re.search(r'text\s*=\s*"([^"]*)"', tok[2])
                    if m and m.group(1).strip():
                        cur.append(m.group(1).strip())   # 条件内联词
                elif name == 'choice':
                    for k in ('a', 'b', 'c', 'd'):
                        m = re.search(k + r"\s*=\s*'([^']*)'", tok[2])
                        if not m:
                            m = re.search(k + r'\s*=\s*"([^"]*)"', tok[2])
                        if m and m.group(1).strip():
                            opts.append(m.group(1).strip())
                elif name in PAGE_BREAK:
                    flush_box()
                elif name in SEG_BREAK:
                    if not in_link:
                        flush_seg()
                elif name in NOCLICK_NL:
                    pass   # 框内无点击换行，并入当前段（后续 text 续接 cur）
                # 其余标签（playbgm/fade/ws/wait/image/fs/call/eval/button/…）忽略
    flush_box()   # ← EOF flush：回收末尾未收尾页界的 box（修复战斗/会话池文件丢文本）
    return boxes, opts


def main():
    xp3 = XP3(XP3_PATH)
    ks = [n for n in xp3.files if n.lower().endswith('.ks')]
    ks.sort()
    boxes_all, opts_all = [], []
    stats = dict(ks=0, boxes=0, dual_boxes=0, segs=0, opts=0, chars=0)
    for name in ks:
        text = read_ks(xp3, name)
        if not text.strip():
            continue
        # 排除纯系统/代码 .ks：无任何“上屏显示”标签 ⇒ 非渲染台词（引擎 plugin / 宏·变量·函数定义 /
        # 战斗动作逻辑 / 右クリック TJS 等）。已逐项核验（plugin 的 `{` 代码块、rclick_tjs21 的 171 个
        # TJS 块、各 戦闘* 动作脚本与 初期値変数代入/関数設定 等定义文件均 0 显示标签）。
        if not any('[' + t + ']' in text for t in DISP_TAGS):
            continue
        stats['ks'] += 1
        boxes, opts = parse_kag(text)
        boxes_all.extend(boxes)
        opts_all.extend(opts)
        stats['boxes'] += len(boxes)
        stats['opts'] += len(opts)
        for b in boxes:
            stats['segs'] += len(b)
            if len(b) >= 2:
                stats['dual_boxes'] += 1
            for seg in b:
                stats['chars'] += len(seg)

    # 输出：用户要求删去合并行 ⇒ 只输出逐段行（一框多次点击＝多行，不附合并拼接行）。
    # 单段页＝一行。
    lines = []
    for b in boxes_all:
        segs = [s for s in b if s.strip()]
        if not segs:
            continue
        for s in segs:
            lines.append(s)
    # 选项单起一行
    for o in opts_all:
        if o not in lines:
            lines.append(o)

    out = '\ufeff' + '\n'.join(lines) + '\n'
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(out)
    print("ks files parsed :", stats['ks'])
    print("boxes (pages)   :", stats['boxes'])
    print("  dual boxes    :", stats['dual_boxes'])
    print("segments total  :", stats['segs'])
    print("options         :", stats['opts'])
    print("chars (text)    :", stats['chars'])
    print("output lines    :", len(lines))
    print("->", OUT)


if __name__ == '__main__':
    main()
