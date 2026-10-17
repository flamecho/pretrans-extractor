# -*- coding: utf-8 -*-
"""
アンジェリーク ルトゥール (PSV, PCSG00696) 剧本正文+选项提取   [Koei Tecmo / Ruby Party 自研「pasc」节点流]
- 源: dec/script/**/*.sc  (gzip 压缩, 解压后为 'pasc' 节点流)
- 节点: [u32 type][u32 len][u32 size][u32 x][...extra...][string(len incl NUL)]
        header = size - align4(len);  next = pos + size;  链恰好吃掉整个文件
- 收: type 2/8 正文, 6 旁白, 54/58 选项提示, 56/60/63 选项, 4/5/7 内联变量
- 丢: 0(○制作注释) / 1(框容器=断框) / 12,15(语音) / 42,43,99,80(标签) / 46(条件) / 其余参数
- 一行 = 一个文本框; 框内 \\n 合并
- ★正文把句号写在 cp932 0x8140 槽(=全角空格 U+3000) => fix_period() 按语境还原为「。」
- 主角可改名: #GD30 -> アンジェリーク(默认); 其余动态名槽保留 〔#GDxx〕
- 0x8751/0x875f/0x8760 = 无字形码位 => 框内演出标记, 删除
- 排除: script/999/(调试) + 090/s090_000_000.sc(调试场景) + text_jp.pastbl(UI表)
"""
import gzip, struct, os, glob, sys, re, collections

def a4(x): return (x + 3) & ~3

HEADER = 32
T_TEXT   = {2, 8}             # 正文/旁白 (行内续写)
T_PROMPT = {54}               # 选项提示 (起新行, 后接行内续写)
T_OPTION = {56, 60, 63}       # 选项 (各占一行)
T_NARR   = {6}                # 旁白行 (自成一行; 空串表示断行)
T_VAR    = {4, 5, 7}          # 内联变量 (名字插入)
T_INVIS  = {9}                # 行内结构标记 (透明, 不参与成行)
T_COMMENT= {0}                # ○ 制作注释 -> 丢弃

# 主角可改名: #GD30 = 主角名, 默认 アンジェリーク
VAR_SUB = {'#GD30': 'アンジェリーク'}

# 内联控制码(字体 font/system.paf 中无对应字形 ⇒ 非显示码, 见报告):
#   0x8751 / 0x875f / 0x8760 = 框内演出标记(如 `…ちょっとうれしい⑱）` 出现在右括号之前,
#   且与 \n 并存 ⇒ 非换框) —— 透明化(删除), 不参与成行
BOX_BREAK = ''
# 框内演出控制码(无字形): 0x8751 / 0x875f / 0x8760
CONTROL_RE = '[%s]' % re.escape(''.join(bytes([0x87, b]).decode('cp932') for b in (0x51, 0x5f, 0x60)))

def parse_nodes(d):
    """返回 [(type, string_or_None)] 顶层节点序列"""
    n = len(d); pos = HEADER; out = []
    while pos < n:
        if pos + 12 > n: break
        t, l, s, x = struct.unpack_from('<4I', d, pos)
        if s < 12 or pos + s > n: break
        hs = s - a4(l); st = None
        if l >= 1 and 12 <= hs <= 200 and hs % 4 == 0:
            e = pos + hs + l - 1
            if e < n and d[e] == 0:
                try: st = d[pos + hs:e].decode('cp932')
                except Exception: st = None
        out.append((t, st))
        pos += s
    return out

# ★ 句号还原: 本作**正文节点(t=2/6/8/56/60/63)把句号写在了 cp932 0x8140 槽**(=全角空格 U+3000),
#   而注释节点(t=0)才用标准 0x8142(=U+3002)。实测: 正文节点内 U+3002 = **0 个**, 而 0x8140 有 4 万+;
#   位置分布 87% 落在行尾/节点尾 —— 行尾不可能有"填充空格"(且多行节点里仅 22% 每行都有) ⇒ 语义即句号。
#   还原规则(必须在合并 \n 之前跑, 依赖 \n 定位行首):
#     ① 前一字为句末标点 / 位于行首(前接 \n) / 位于文本开头 ⇒ 删除(标点已足, 或为续行缩进)
#     ② 其余 ⇒ 「。」
_SENT_END = '？！…‥～♪」』】）)'


def fix_period(s):
    """把正文里的 0x8140(U+3000) 按语境还原为「。」或删除"""
    if '\u3000' not in s:
        return s
    out = []
    for i, ch in enumerate(s):
        if ch != '\u3000':
            out.append(ch); continue
        prev = s[i - 1] if i > 0 else ''
        if prev == '' or prev == '\n' or prev in _SENT_END or (out and out[-1] == '。'):
            continue                        # 行首缩进 / 标点后停顿 / 已有句号
        out.append('。')
    return ''.join(out)


def clean_line(s):
    s = fix_period(s)                      # ★ 句号还原(须先于合并 \n)
    s = s.replace('\n', '')                # 合并同一文本框内的软换行
    s = re.sub(CONTROL_RE, '', s)          # 去框内演出控制码(无字形码位)
    s = s.strip('\u3000')
    return s

def split_box(s):
    """按换框控制码拆分为多行 (本作为空 -> 恒一行)"""
    if not BOX_BREAK:
        return [s]
    return re.split('[%s]' % re.escape(BOX_BREAK), s)

T_PROMPT_EXTRA = {58}         # 选项提示(菜单B)

def extract_file(path):
    d = gzip.decompress(open(path, 'rb').read())
    ns = parse_nodes(d)
    lines = []
    cur = []

    def flush():
        if cur:
            txt = ''.join(cur)
            for part in split_box(txt):
                part = clean_line(part)
                if part.strip() != '':
                    lines.append(part)
            cur.clear()

    for t, st in ns:
        if t in T_VAR:
            if st is not None:
                cur.append(VAR_SUB.get(st, '\u3014%s\u3015' % st))
        elif t in T_INVIS:
            continue
        elif t in T_PROMPT or t in T_PROMPT_EXTRA:
            flush()
            if st is not None:
                cur.append(st)
        elif t in T_OPTION:
            flush()
            if st is not None:
                for part in split_box(st):
                    part = clean_line(part)
                    if part.strip() != '':
                        lines.append(part)
        elif t in T_NARR:
            flush()
            if st:
                for part in split_box(st):
                    part = clean_line(part)
                    if part.strip() != '':
                        lines.append(part)
        elif t in T_TEXT:
            cur.append(st or '')
        else:
            flush()
    flush()
    return lines

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'dec/script'
    out = sys.argv[2] if len(sys.argv) > 2 else None
    skip_dirs = {'999'}  # 调试
    skip_files = {'090/s090_000_000.sc'}  # 调试用「パートナー設定」场景(非剧本)
    files = sorted(glob.glob(os.path.join(root, '**', '*.sc'), recursive=True))
    all_lines = []
    for f in files:
        rel = os.path.relpath(f, root).replace('\\', '/')
        d0 = os.path.basename(os.path.dirname(f))
        if d0 in skip_dirs or rel in skip_files:
            continue
        ls = extract_file(f)
        all_lines.extend(ls)
    print('files:', len(files), 'lines:', len(all_lines))
    cnt = collections.Counter()
    for l in all_lines:
        for m in re.findall(r'\u3014[^\u3015]+\u3015', l):
            cnt[m] += 1
    print('unresolved vars:', cnt.most_common(20))
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
            fh.write('\n'.join(all_lines) + '\n')
        print('wrote', out)
    return all_lines

if __name__ == '__main__':
    main()
