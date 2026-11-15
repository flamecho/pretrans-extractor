# -*- coding: utf-8 -*-
"""NScripter（nscript.dat，整文件 XOR <key>）-> 「双版对照」全文本

用法: python scripts/ns_dual.py <nscript.dat> <out.txt> [xor_key=0x84]

口径（skill references/S6-lines-dual.md）:
- A 类 = `\\`（改行＋等待，清框/换页）        -> 框界
- B 类 = `@`（等待点击，文字原地续写不清框）  -> 框内段界
- 行末不带 @/\\ 的文本行 = 同框软换行        -> 直接拼接
- 框内 ≥2 段 => 先列各段，再列合并行（A,B,C,ABC）；单段框只列一次
- `textclear` / 新 `*label`（缓冲非空）=> 隐式框界
- 选项（csel/select）各占一行、按出现顺序，前后先结算当前框
- 名札走 lsp 文本精灵，不进正文流 => 无前缀可去
- 不再以「引号未闭合」为由合并（跨段引号是原文写法）
- `--blank-seg`：把同一屏内「连续 ≥2 个 `br`（空行）」当**段界**（不切框）⇒
  作者用空行做段落停顿时，该屏也出双版（A / B / AB）。默认关闭（`br` 一律合并）。
"""
import sys, re

# `!` 也是 NScripter 命令前缀（`!w4000` 待ち／`!s300` SE待ち）。不加则这些行会被当正文收进来
# （落下点2 实测 10 行：`!s300` / `!w500` 等）。
CMD = re.compile(r'^[!A-Za-z_/]')
SPRITE_TIME = re.compile(r'![sd]\d+')
COLOR = re.compile(r'#\$?[0-9A-Fa-f]{6}')
# 行内控制码（2026-10-22 用户以 [a-zA-Z] 检索发现）：NScripter 允许 `:ld_n 8:` 这类
# 冒号包裹的内联用户命令直接嵌在正文里（CAGE-OPEN L2981「俺は、@:ld_n 8:牧。牧敦義だ」），
# 以及 `@cl_g 1,3` 这种点击符后紧跟命令；两者都是控制码，必须剥掉，否则进正文。
INLINE_CMD = re.compile(r':[A-Za-z_][A-Za-z0-9_]*(?:\s[^:」』]*)?:')
# ルビ `(基底/よみ)`：NScripter 的 ruby 写法（`rubyon` 时才生效）⇒ 只留基底
RUBY = re.compile(r'\(([^()/\s]{1,10})/([^()/\s]{1,20})\)')
PURE_ASCII = re.compile(r'[A-Za-z0-9_/,\.\-\s"\']+')
# `csel` 的选项行（本作 70 处：`csel` 独占一行，选项逐行写在后面）
#   csel
#   "「分かりました」",*hatiok,
#   "「できません」",*hatino
OPTLN = re.compile(r'^"([^"]*)"\s*,\s*\*')
# 文字スプライト（直接上屏特效）：`lsp 1,":s/15,15,0;#ffffff腐った快苦の瀬で、",300,200`
SPRITE_TXT = re.compile(r'":s[^";]*;#(?:[0-9a-fA-F]{6})?([^"]*)"')


def decode(path, key=0x84):
    d = open(path, 'rb').read()
    return bytes(b ^ key for b in d).decode('cp932', 'replace')


def tidy(s):
    s = SPRITE_TIME.sub('', s)
    s = COLOR.sub('', s)
    s = RUBY.sub(r'\1', s)      # ルビ `(基底/よみ)` ⇒ 只留基底（本作 9 种 9 处）
    s = s.replace('\u3000\u3000', '\u3000').strip()
    return s


def extract(t, start_label=None, exclude=(), blank_seg=False, text_sprite=False,
            split_quotes=False):
    frames = []          # 每项 = [seg, seg, ...]
    opts = []            # (位置序号, 选项文本) —— 以 frames 长度定位
    segs, seg = [], ''
    started = not start_label
    skip = False
    n_cmd = n_soft = br_run = 0
    pend_csel = False    # 见下：`csel` 独占一行、选项写在后续行的写法
    sprites = []         # 同一屏的文字スプライト（`:s`）—— 同屏多行合并成一框

    def close_seg():
        nonlocal seg
        s = tidy(seg)
        seg = ''
        if s:
            segs.append(s)

    def close_frame():
        nonlocal segs
        close_seg()
        if segs:
            frames.append(segs)
        segs = []

    def flush_sprites():
        """同一屏的文字スプライト收成一框（同屏多行 ⇒ 合并，与框内换行同口径）"""
        nonlocal sprites
        if sprites:
            close_seg()
            segs.append(''.join(sprites))
            close_frame()
            sprites = []

    for raw in t.split('\n'):
        s = raw.strip()
        if not s:
            continue
        # ---- `csel` 独占一行、选项逐行写在本行之后（本作 70 处全是这种写法）----
        if pend_csel:
            m = OPTLN.match(s)
            if m:
                t2 = tidy(m.group(1).replace('\\', ''))
                if t2:
                    opts.append((len(frames), t2))
                n_cmd += 1
                continue
            pend_csel = False           # 不是选项行 ⇒ 本 csel 块结束，按普通行继续
        if s.startswith('*'):
            flush_sprites()
            close_frame()
            name = s.split(';')[0].strip().split('|')[0].lstrip('*')
            skip = name in exclude          # 系统区块（标题菜单/ギャラリー等）按 label 整体跳过
            if start_label and name == start_label:
                started = True
            continue
        if s.startswith(';') or s.startswith('~'):
            continue
        if not started or skip:
            continue
        if s.startswith('csel') or re.match(r'^select\s', s):
            flush_sprites()
            close_frame()
            body = s[s.find(' '):] if ' ' in s else ''
            found = re.findall(r'"([^"]*)"', body)
            for m in found:
                m = tidy(m.replace('\\', ''))
                if m:
                    opts.append((len(frames), m))
            if not found:               # 裸 `csel`：选项写在后面的行里
                pend_csel = True
            n_cmd += 1
            continue
        if s.startswith(':') or CMD.match(s):
            n_cmd += 1
            k = s.split()[0]
            # ---- 文字スプライト（`:s/…;#rrggbb本文`）＝直接上屏的扉文/特效，按一屏一框收 ----
            if text_sprite and k in ('lsp', 'lsph', 'spbtn'):
                m = SPRITE_TXT.search(s)
                if m:
                    sprites.append(m.group(1))
                    continue
                flush_sprites()          # 非文字スプライト ⇒ 画面变了
            elif k in ('csp', 'vsp', 'textclear', 'cl', 'clear', 'bg', 'bd', 'print'):
                if k in ('csp', 'vsp', 'textclear', 'cl', 'clear'):
                    flush_sprites()
            if k in ('textclear', 'cl', 'clear'):
                close_frame()
            elif k == 'br':
                # `br` = 同框换行（不点击）。连续 ≥2 个 `br` = **空行**，在 NScripter 里是作者做
                # 「段落停顿」的排版手段（同一屏内，中间常夹 `!w1000`）。默认仍按合并处理；
                # `blank_seg=True` 时把空行当**段界**（不切框）⇒ 该屏就出双版：A / B / AB。
                br_run += 1
                if blank_seg and br_run >= 2:
                    close_seg()
            continue
        # 正文行：先按 `;` 剔掉行内注释（NScripter 通用；命令行里也这么用：
        #   `dwave 1,"se\bosu36.wav";音：ドサッ`）。本作把注释写在**名札后面**——
        #   `[？？？];レイス`（12 处，作者的说话人备忘）、`[コジカ];（リ` / `[男];（ハゲ`（未写完的注记），
        #   不剥就会把旁注显示进正文，还会把「？？？」的身份直接剧透。
        # ⚠ 只能在这里剥：命令分支里的文字スプライト `:s/15,15,0;#ffffff…` 也含 `;`。
        if ';' in s:
            s = s.split(';', 1)[0].strip()
            if not s:
                continue
        # 正文行：按 @ / \ 切段，保留分隔符以区分 A/B 类
        flush_sprites()
        for piece in re.split(r'([@\\])', s):
            if piece in ('@', '\\'):
                if piece == '@':
                    close_seg()                     # B 类：段界（不清框）
                else:
                    close_frame()                   # A 类：框界（换页）
                br_run = 0
                continue
            body = piece
            if not body:
                continue
            body = INLINE_CMD.sub('', body)        # 剥内联 `:cmd args:`
            body = body.strip()
            if not body:
                continue
            if CMD.match(body) or body in ('"', "'"):
                close_seg()                         # 行内混入命令 / 孤立引号（源缺陷）
                continue
            if PURE_ASCII.fullmatch(body):
                close_seg()                         # 纯 ASCII 片段 = 命令/资源名，不是正文
                continue
            # `--split-quotes`：同一屏里有**多个完整的「…」台词行**时，一行台词＝一段
            #   （本作 5 处：H 场景里ドクの声连呼，一屏 2〜3 句）。判据是**结构**的：
            #   本行以「开头 且 当前段已以」收尾 ⇒ 上一句已闭合、本行另起一段。
            #   ⚠ 这不是引擎判据（本作屏内点击 `@`＝0），是用户指定「出双版」的口径。
            if split_quotes and seg and body.startswith('\u300c') and seg.rstrip().endswith('\u300d'):
                close_seg()
            if seg:
                if body[0] == '\u3000':
                    body = body.lstrip('\u3000')
                seg += body
                n_soft += 1
            else:
                seg = body
            br_run = 0      # 有正文落下 ⇒ 空行计数归零
    close_frame()
    return frames, opts, n_cmd, n_soft


def render(frames, opts):
    out = []
    by_pos = {}
    for pos, txt in opts:
        by_pos.setdefault(pos, []).append(txt)
    for i, segs in enumerate(frames):
        out.extend(by_pos.get(i, []))
        if len(segs) == 1:
            out.append(segs[0])
        else:
            out.extend(segs)
            out.append(''.join(segs))
    out.extend(by_pos.get(len(frames), []))
    return out


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    key = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x84
    # `--exclude a,b,c`：按 `*label` **整体跳过**系统区块（标题菜单/セーブ画面/ギャラリー等）。
    # 判据是 label 类型，不是文本内容 —— 2026-11-03 Crimson V 的 `*gallery_s`/`*gallery_h`
    # 里有一串 `次へ\`/`戻る\`（画廊翻页标签），不按区块排除就会被当正文收进尾部。
    excl = set()
    blank_seg = False
    text_sprite = False
    split_quotes = False
    for a in sys.argv[4:]:
        if a.startswith('--exclude'):
            v = a.split('=', 1)[1] if '=' in a else ''
            excl |= {x.strip() for x in v.split(',') if x.strip()}
        elif a == '--blank-seg':
            blank_seg = True
        elif a == '--split-quotes':
            # 一屏多个完整「…」台词行时按句切段 ⇒ 这些屏出双版（先列段行、再列合并行）
            split_quotes = True
        elif a == '--text-sprite':
            # 把 `lsp N,":s/…;#rrggbb本文",x,y`（文字スプライト）当直接上屏特效收进来；
            # 同一屏的多个 `:s` 精灵合并成一框。默认关闭（多数作品里 `:s` 是 UI 标签）。
            text_sprite = True
    frames, opts, nc, ns = extract(decode(src, key), exclude=excl, blank_seg=blank_seg,
                                   text_sprite=text_sprite, split_quotes=split_quotes)
    lines = render(frames, opts)
    multi = sum(1 for f in frames if len(f) > 1)
    click = sum(len(f) for f in frames) + len(opts)
    print('frames=%d segments=%d multi=%d opts=%d 点击版=%d 页版=%d 对照版=%d soft=%d cmd=%d excluded=%s'
          % (len(frames), sum(len(f) for f in frames), multi, len(opts),
             click, len(frames) + len(opts), len(lines), ns, nc, ','.join(sorted(excl)) or '-'), file=sys.stderr)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')
