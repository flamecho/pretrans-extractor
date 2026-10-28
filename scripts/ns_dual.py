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
PURE_ASCII = re.compile(r'[A-Za-z0-9_/,\.\-\s"\']+')


def decode(path, key=0x84):
    d = open(path, 'rb').read()
    return bytes(b ^ key for b in d).decode('cp932', 'replace')


def tidy(s):
    s = SPRITE_TIME.sub('', s)
    s = COLOR.sub('', s)
    s = s.replace('\u3000\u3000', '\u3000').strip()
    return s


def extract(t, start_label=None):
    frames = []          # 每项 = [seg, seg, ...]
    opts = []            # (位置序号, 选项文本) —— 以 frames 长度定位
    segs, seg = [], ''
    started = not start_label
    n_cmd = n_soft = 0

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

    for raw in t.split('\n'):
        s = raw.strip()
        if not s:
            continue
        if s.startswith('*'):
            close_frame()
            if start_label and s.split(';')[0].strip() == start_label:
                started = True
            continue
        if s.startswith(';') or s.startswith('~'):
            continue
        if not started:
            continue
        if s.startswith('csel') or re.match(r'^select\s', s):
            close_frame()
            body = s[s.find(' '):] if ' ' in s else ''
            for m in re.findall(r'"([^"]*)"', body):
                m = tidy(m.replace('\\', ''))
                if m:
                    opts.append((len(frames), m))
            n_cmd += 1
            continue
        if s.startswith(':') or CMD.match(s):
            n_cmd += 1
            if s.split()[0] in ('textclear', 'cl', 'clear'):
                close_frame()
            continue
        # 正文行：按 @ / \ 切段，保留分隔符以区分 A/B 类
        for piece in re.split(r'([@\\])', s):
            if piece in ('@', '\\'):
                if piece == '@':
                    close_seg()                     # B 类：段界（不清框）
                else:
                    close_frame()                   # A 类：框界（换页）
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
            if seg:
                if body[0] == '\u3000':
                    body = body.lstrip('\u3000')
                seg += body
                n_soft += 1
            else:
                seg = body
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
    frames, opts, nc, ns = extract(decode(src, key))
    lines = render(frames, opts)
    multi = sum(1 for f in frames if len(f) > 1)
    click = sum(len(f) for f in frames) + len(opts)
    print('frames=%d segments=%d multi=%d opts=%d 点击版=%d 页版=%d 对照版=%d soft=%d cmd=%d'
          % (len(frames), sum(len(f) for f in frames), multi, len(opts),
             click, len(frames) + len(opts), len(lines), ns, nc), file=sys.stderr)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')
