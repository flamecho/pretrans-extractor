# -*- coding: utf-8 -*-
"""[Director 8.5 / XFIR 小端] XMED 内的「尖括号指令 DSL」→ 成品正文（一次点击 = 一行）

与同目录 `director_xmed_text.py` 的区别（**别混用**）
  * `director_xmed_text.py`：RIFX **大端**，一个 `XMED` ＝ 一个 text 成员 ＝ 一屏（D.Zone，2026-11-03）。
  * 本脚本：XFIR **小端**，`XMED` 里装的是**整个剧本**（本作 msc.dir 仅 13 个 XMED 却含 3,100+ 屏），
    屏边界写在文本里的 `<W>` / `<PAGE>` 指令上。

适用：Macromedia Director 8.5 Afterburner 保护的 `.cxt`（先用 ProjectorRays 解成 `.dir`）
      已在 [JP]GUISARD Fandisc 实测（msc.cxt 剧情 4 条线 ＋ dc.cxt 附带资料）。

两条链路
  ① XMED → 文本 run：一个成员的正文被 Director **定长分块**（约 3.1K–4.0K 字节）切成多条 run，
     run 之间夹着字体表/样式表 ⇒ **必须按 offset 顺序全部拼接**，只取最长那条会丢 3/4 正文。
  ② run → 一次点击一行：正文里的 `\\r` 是**排版折行**（词中断行）必须合并；
     `<W>`（wait，恒在行尾，但也**会落在句中**）/ `<PAGE>`（清屏）才是「一次点击」的边界。

断框判据（L0，引擎指令；不依赖 `\\r`）
  * `<W>`    ＝ 等待点击 ⇒ 其左侧就是本次点击显示的末尾
  * `<PAGE>` ＝ 清屏换页
  * 切点必须**行内精确**：本作有 6 处 `<W>` 落在行中间
    （`「とりあえず……<W>こいつの身の振り方が気になるし、`），按行切会把它错放行尾。
  * 反向验证（不作正向切分依据）：段内折行 1..8 行、中位 1–2，与 20 全角字/行的排版宽自洽。

100 问（`★角色` + `▼そのＮ`）：`▼その` 是**记录自定界（L1）**，一条一行；
  条内 `<PAGE>`/`<W>` 只是翻页/停顿，不切条。判定阈值＝块内 ≥10 条。

用法
  python scripts/director_xmed_dsl.py --dir _work_gui/out_pr --out 提取结果/xxx.txt [--raw _work_gui/raw]
  python scripts/director_xmed_dsl.py --dir ... --dump          # 只打印每 cast 的 XMED/字符数
"""
import argparse
import io
import os
import re
import struct
import sys

REC = re.compile(rb'\x00([0-9A-Fa-f]{1,8}),')

TAG = re.compile(r'<[^>\r]{1,40}>')
RULE = re.compile(r'^[─━\s]{5,}$')
SPLIT = re.compile(r'<PAGE>|<W>')
ITEM_HEAD = re.compile(r'(?=(?:^|\r)▼その)')   # ★ re.M 的 `^` 只认 \n；本作记录分隔是 \r
# `-- END --` 是脚本的段落终止标记（会粘住下一段的 `///名字`），剔除
ENDMARK = re.compile(r'--\s*END\s*--(?:/{1,3}[^\r<]{0,20})?')
# 段标记有时被导成「粘在上一行行尾」⇒ 先补回行界；前后都排除 `/`，否则行首 `///透` 会被劈成 `/`+`//透`
GLUED = re.compile(r'([^\r/])(//[^\r/<\n][^\r<\n]{0,18})(?=\r)')
# 双版对照用：**整段就是一句完整台词**（首「尾」成对）。被折行的长台词只有首段以「开头、
# 末段以」收尾，中间段不闭合 ⇒ 不会误命中（判据同 ESCAPE 的 `--split-quotes`）。
QUOTE = re.compile(r'「[^「」]*(?:「[^」]*」[^「」]*)*」')


# ---------------------------------------------------------------- XMED → run
def mmap_le(d):
    """XFIR（小端）的 mmap 表。★ 小端时 chunk tag 在文件里是反序的（`imap`→`pami`、`CASt`→`tSAC`）。"""
    o = d.find(b'pamm')
    if o < 0:
        return []
    body = o + 8
    hl, el, cnt = struct.unpack_from('<HHI', d, body)
    out = []
    for k in range(cnt):
        q = body + hl + k * el
        if q + el > len(d):
            break
        cc = d[q:q + 4][::-1].decode('latin1', 'replace')
        ln, off = struct.unpack_from('<II', d, q + 4)
        if ln == 0:
            continue
        out.append((cc, off, ln))
    return out


def text_runs(body):
    """按 offset 顺序返回所有正文 run（跳过字体/样式表）。

    ★ 不能按长度过滤：正文 run 是定长分块，但**块尾可能是几个字节的残段**，
      按 `n >= 64` 过滤会把它们丢掉 ⇒ 段落粘连/缺字。
      判据改成「能 cp932 解码 ＋ 无 NUL ＋ 含日文/标签/全角标点」。
    """
    res = []
    for m in REC.finditer(body):
        n = int(m.group(1), 16)
        p = m.end()
        seg = body[p:p + n]
        if n == 0 or len(seg) != n or b'\x00' in seg:
            continue
        try:
            t = seg.decode('cp932')
        except UnicodeDecodeError:
            continue
        if not any(('\u3040' <= c <= '\u30ff') or ('\u4e00' <= c <= '\u9fff')
                   or c in '<>' or ('\uff01' <= c <= '\uff60') or c == '\u3000'
                   for c in t):
            continue
        res.append((m.start(), t))
    return res


def cast_text(path):
    d = open(path, 'rb').read()
    parts, nmed = [], 0
    for cc, off, ln in mmap_le(d):
        if cc != 'XMED':
            continue
        nmed += 1
        for _o, t in text_runs(d[off + 8:off + 8 + ln]):
            parts.append(t)
    return ''.join(parts), nmed


# ---------------------------------------------------------------- run → 成品
def split_marks(text):
    return GLUED.sub(lambda m: m.group(1) + '\r' + m.group(2), text)


def strip_line(s):
    s = ENDMARK.sub('', s)
    s = TAG.sub('', s)
    if RULE.match(s):
        return ''
    return s


def flush(buf):
    """段内排版折行合并成一行。首行保留行首缩进，续行剥行首全角空格。"""
    ls = [x for x in buf if x.strip()]
    if not ls:
        return None
    out = [ls[0].rstrip()]
    for ln in ls[1:]:
        out.append(ln.strip('\u3000') if ln.startswith('\u3000') else ln)
    t = ''.join(out).rstrip()   # ★ 只剥行尾：.strip() 会把行首 \u3000（旁白缩进）也吃掉
    return t or None


def collect(seg):
    buf = []
    for ln in seg.split('\r'):
        s = strip_line(ln)
        if s.strip('\u3000'):
            buf.append(s)
    return flush(buf)


def blocks(text):
    """按 `//…` / `★…` 切块（标记恒独占一行）：[(kind, head, body_text)]。"""
    out, cur = [], None
    for ln in text.split('\r'):
        if ln.startswith('//'):
            out.append(cur)
            cur = ['//', ln.lstrip('/').strip(), []]
            continue
        if ln.startswith('★'):
            out.append(cur)
            cur = ['★', ln[1:].strip(), []]
            continue
        if cur is None:
            cur = ['-', '', []]
        cur[2].append(ln)
    out.append(cur)
    return [(k, h, '\r'.join(v)) for e in out if e for k, h, v in (e,)]


def screen_mode(text, split_quotes=True):
    """一次点击 = 一段：在 `<W>` / `<PAGE>` 处**行内**精确切分。

    `split_quotes`（双版对照）：当**同一屏内的每一段都是完整台词**（`^「.*」$`，段数 ≥2）
    ⇒ 判为「一屏写了 2〜3 句台词」⇒ 先列段行 A、B，再列合并行 AB（单段屏不重复）。
    判据等同 ESCAPE 的 `--split-quotes`：被折行的长台词只有首段以「开头、末段以」收尾，
    中间段不闭合 ⇒ 不会误命中。
    """
    rows = []
    for seg in SPLIT.split(text):
        ls = [x for x in (strip_line(ln) for ln in seg.split('\r')) if x.strip('\u3000')]
        if not ls:
            continue
        t = flush(ls)
        if not t:
            continue
        if split_quotes and len(ls) >= 2 and all(QUOTE.fullmatch(x.strip()) for x in ls):
            rows.extend(x.strip() for x in ls)
        rows.append(t)
    return rows


def item_mode(text):
    """100 问：`▼その` 定界，一条一行（条内 `<PAGE>`/`<W>` 不切）。"""
    rows = []
    for seg in ITEM_HEAD.split(text):
        t = collect(seg)
        if t:
            rows.append(t)
    return rows


def to_lines(text, dual=True):
    rows = []
    for kind, head, body in blocks(split_marks(text)):
        if kind == '★':
            if not head:
                continue
            n_item = len(re.findall(r'(?:^|\r)▼その', body))
            # `★` 只是脚本里的块标记（与 `//` 同类），画面上渲染的是名字本身
            rows.append(head)
            rows.extend(item_mode(body) if n_item >= 10 else screen_mode(body, dual))
        else:
            rows.extend(screen_mode(body, dual))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True, help='解包后的 .dir 目录（ProjectorRays 输出）')
    ap.add_argument('--out', help='成品 txt（UTF-8 BOM ＋ 纯 LF）')
    ap.add_argument('--raw', help='同时导出每 cast 的原始文本（保留 \\r 与标签）')
    ap.add_argument('--only', help='只处理这些 cast（逗号分隔，如 msc,dc）')
    ap.add_argument('--dump', action='store_true', help='只打印各 cast 的 XMED/字符数')
    ap.add_argument('--no-split-quotes', dest='dual', action='store_false',
                    help='关掉双版对照（一屏多句不再拆段行）；默认开')
    a = ap.parse_args()

    # ★ 顺序敏感：成品是「剧情 cast → 附带资料 cast」，按 --only 的书写顺序处理，别用字母序
    order = [x.strip() for x in a.only.split(',')] if a.only else None
    only = set(order) if order else None
    if a.raw:
        os.makedirs(a.raw, exist_ok=True)
    rows, stat = [], {}
    files = sorted(f for f in os.listdir(a.dir) if f.lower().endswith('.dir'))
    if order:
        files.sort(key=lambda f: order.index(f[:-4]) if f[:-4] in only else len(order))
    for fn in files:
        if not fn.lower().endswith('.dir'):
            continue
        stem = fn[:-4]
        if only and stem not in only:
            continue
        txt, nmed = cast_text(os.path.join(a.dir, fn))
        print('%-8s XMED %-3d chars %d' % (stem, nmed, len(txt)), file=sys.stderr)
        if a.dump or not txt.strip():
            continue
        if a.raw:
            with io.open(os.path.join(a.raw, stem + '.txt'), 'w',
                         encoding='utf-8', newline='') as f:
                f.write(txt)
        n0 = len(rows)
        rows.extend(to_lines(txt, a.dual))
        stat[stem] = len(rows) - n0

    if a.dump or not a.out:
        return
    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for s in rows:
            f.write(s + '\n')
    L = sorted(len(x) for x in rows)
    print('per-cast %s' % stat, file=sys.stderr)
    print('lines %d / max %d / median %d -> %s'
          % (len(rows), L[-1], L[len(L) // 2], a.out), file=sys.stderr)


if __name__ == '__main__':
    main()
