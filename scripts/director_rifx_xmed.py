"""Director RIFX(大端) + XMED「指令 DSL」文本提取器 —— GUISARD 本編（2003 / サンダルダッシュ）。

与 `director_xmed_dsl.py`（XFIR 小端，GUISARD Fandisc）**同族不同容器**：
  · 本作 `.cxt` = RIFX（大端），chunk tag 正常顺序（`mmap`/`CASt`/`XMED`）
  · mmap 表：`u16 hdrLen / u16 entryLen(=20) / u32 count`，条目 `u32 tag / u32 len / u32 off / u32 flags`（全大端）
  · 一个 XMED ＝**一个场景**的脚本（851 个成员 ＝ 426 场景 ×（内联版 ＋ 编译版））

XMED 体的结构（已验，见解析报告）：
  `XMED` + u32 len + [数字描述头] + 若干 「\\x00 + <hex 长度> + , + <n 字节 cp932>」run
  正文 run 之后依次是：字体名 run（首字节 **0x0f**）／64 字节零 run／68 字节样式数组
  ⇒ **判据：首个以 0x0f 开头的 run 之前的所有 run 都是正文**（长文按 ~4K 字节分块，可能切断
    多字节字符，必须先拼字节再解码）。实测 851/851 成员符合，无例外。

断框判据（L0，指令级）：
  · `<W>`＝等待点击（一次点击＝一个文本框）⇒ 切点，**行内精确**
  · `<P>`＝清屏；实测 `<W>` 12,603 / `<P>` 12,753、`<W>`→`<P>` 12,394（98.3%）⇒ **一页一次点击**
    ⇒ 无「一页 ≥2 次点击」⇒ 版式 **单版**（不出段行/合并行）
  · `//` ＝注释（不执行）⇒ 注释行一律不收；**编译版成员**（正文全被注释、只有 `<TEXT n>` 数字 id）
    因此产出 0 行，自动排除
  · `<talk 名前：>`＝**独立名字窗**（编译版对应 `<TALK n>` 数字 id，名字表在 `tx01.cxt`）⇒ 剔名
  · `<v voXXXX>`／`<TITLE>`／`<show_ch>` 等其余指令一律剔除
  · `<select 『A』,100,『B』,200>` ＝文本选项，每个 `『…』` 一行，按出现位置入列

用法：
  python scripts/director_rifx_xmed.py --dir <out_pr 目录> --out 成品.txt [--raw raw目录] [--only sc01]
"""
import argparse
import io
import os
import re
import struct
import sys

REC = re.compile(rb'\x00([0-9A-Fa-f]{1,8}),')
TAG = re.compile(r'<[^>\r]{1,200}>')
SPLIT = re.compile(r'<W>')
SEL = re.compile(r'<select\s+([^>\r]*)>')
SELTXT = re.compile(r'『([^』]{1,200})』')
FONT = b'\x0f'


def members(path):
    """按文件顺序返回 [(name, text)]；name＝`<SCENE scXXXX>` 的 id（无则 None）。

    容器两种字节序（**同一引擎的两种发行形态**，判据相同）：
      · `RIFX` 大端：chunk tag 正常序（`mmap`/`XMED`），表项 `>II`
      · `XFIR` 小端：chunk tag **反序**（`pamm`/`DEMX`），表项 `<II`   ← 按魔数自动选，别写死
    """
    d = io.open(path, 'rb').read()
    le = d[:4] == b'XFIR'
    e = '<' if le else '>'
    o = d.find(b'pamm' if le else b'mmap')
    if o < 0:
        raise SystemExit('%s: 无 mmap（魔数 %r）' % (path, d[:4]))
    hl, el, cnt = struct.unpack_from(e + 'HHI', d, o + 8)
    want = b'DEMX' if le else b'XMED'
    out = []
    for k in range(cnt):
        q = o + 8 + hl + k * el
        if q + el > len(d):
            break
        if d[q:q + 4] != want:
            continue
        ln, off = struct.unpack_from(e + 'II', d, q + 4)
        body = d[off:off + ln]
        runs = [(int(m.group(1), 16), m.end()) for m in REC.finditer(body)]
        pay = [body[s:s + n] for n, s in runs]
        cut = next((i for i, p in enumerate(pay) if p[:1] == FONT), len(pay))
        raw = b''.join(pay[:cut]).rstrip(b'\x00')
        txt = raw.decode('cp932', 'replace')
        m = re.search(r'<SCENE (\S+?)>', txt)
        out.append((m.group(1) if m else None, txt))
    return out


def clean_lines(seg):
    """一段（两次点击之间）→ 有效正文行：去标签、去空行、去 `//` 注释。

    `<select …>` 整条是**指令行**（选项文本已单独取出）⇒ 先整条删掉，再剥其余标签。
    """
    seg = SEL.sub('', seg)
    ls = []
    for ln in seg.split('\r'):
        s = TAG.sub('', ln)
        if not s.strip() or s.strip().startswith('//'):
            continue
        ls.append(s.rstrip())
    return ls


def scene_lines(txt):
    rows = []
    for seg in SPLIT.split(txt):
        # 选项：`<select 『A』,100,『B』,200>` ⇒ 每个 『…』 一行（在本次点击内原位置）
        for m in SEL.finditer(seg):
            items = SELTXT.findall(m.group(1))
            if items:
                rows.extend(x.strip() for x in items)
        ls = clean_lines(seg)
        if not ls:
            continue
        # 框内换行＝排版折行 ⇒ 合并（行首全角空格保留）
        t = ''.join(ls).strip('\u3000')
        if t:
            rows.append(t)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True, help='pr.exe decompile 输出目录（内含 .dir）')
    ap.add_argument('--only', help='只处理这些 cast（逗号分隔）')
    ap.add_argument('--raw', help='同时导出每个 cast 的成员原文（含标签）')
    ap.add_argument('--out', help='成品 txt（UTF-8 BOM ＋ 纯 LF）')
    a = ap.parse_args()

    order = [x.strip() for x in a.only.split(',')] if a.only else None
    files = sorted(f for f in os.listdir(a.dir) if f.lower().endswith('.dir'))
    if order:
        files = [f for f in files if f[:-4] in order]
        files.sort(key=lambda f: order.index(f[:-4]))
    if a.raw:
        os.makedirs(a.raw, exist_ok=True)

    rows, stat = [], {}
    seen = {}
    for fn in files:
        stem = fn[:-4]
        ms = members(os.path.join(a.dir, fn))
        if a.raw:
            with io.open(os.path.join(a.raw, stem + '.txt'), 'w',
                         encoding='utf-8', newline='') as f:
                f.write('\x1e'.join(t for _, t in ms))
        n0 = len(rows)
        skip = dup = 0
        for sid, txt in ms:
            # 只收「以 <SCENE 开头」的成员：其余是同 cast 里的数据表/配置
            # （本作 `sd0010sd0020…` 场景索引表、`<text_style page>` 样式配置），无 `<SCENE>` 头即非场景
            if not txt.lstrip().startswith('<SCENE'):
                skip += 1
                continue
            # 同一场景 id 且正文**逐字节相同** ⇒ 作者的复制残留，只保留第一份
            # （结构判据：同 id 同字节 ⇒ 引擎加载任意一份都是同一段文本）
            k = (sid, txt)
            if sid and k in seen:
                dup += 1
                continue
            seen[k] = 1
            rows.extend(scene_lines(txt))
        stat[stem] = len(rows) - n0
        print('%-8s members %-4d 非场景 %d 重复 %d lines %d'
              % (stem, len(ms), skip, dup, stat[stem]), file=sys.stderr)

    if not a.out:
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
