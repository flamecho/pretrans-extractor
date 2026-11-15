# -*- coding: utf-8 -*-
"""Re;quartz After Love Story（Adobe AIR ＋ AIRNovel / anbooks「als」）全文本提取。

L0 判据（源码级，取自本作 main.an 宏定义与官方 AIRNovel 命令语义）：
  main.an:40-41  [char2macro char=@ name=l]   → `@` = 命令 `l` = 行末点击待ち（段界，不清屏）
  main.an:43-44  [char2macro char=\\ name=plc] → 反斜杠 = 命令 `plc` = [p]+[er] = 改ページ＋清屏（页界）
  [r]  = 框内换行（in-box newline）→ 合并，不拆
  [h_voice]…[end_h_voice] = 对白正文（「」内联）；[voice fn=…] 等其余标签 = 命令，剥净
  &save:  = 变量赋值（整行跳过）；; 行首 = 注释；*label = 标签（跳过）
  [wtime]/[jump]/[grp]/[lay]/[se]/[bgm]… = 命令，无正文

页 = 两次 反斜杠（plc）之间的全部文本；段 = 页内 `@[r]`（l）切出的点击单元。
页内 ≥2 段 ⇒ 双版对照（同页先列段行 A,B,C，再列合并行 ABC）。

用法：
  python extract_requartz.py <scenario_dir> <out_txt>
scenario_dir 含 alsmotoi.an / alsleito.an / alssaiki.an / alsyuzuki.an（按 main.an 路线顺序）。
"""
import io
import sys
import os

ROUTE_ORDER = ['alsmotoi.an', 'alsleito.an', 'alssaiki.an', 'alsyuzuki.an']


def extract_text(s):
    """从一行里抽取正文：剥净命令标签，保留 [h_voice]…[end_h_voice] 内文与裸文本。"""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '[':
            j = s.find(']', i)
            if j == -1:
                out.append(s[i:])  # 无闭合，整段当文本（防吞）
                break
            tag = s[i:j + 1]
            inner = tag[1:-1].lstrip()
            if inner.startswith('h_voice'):
                k = s.find('[end_h_voice]', j)
                if k != -1:
                    out.append(s[j + 1:k])
                    i = k + len('[end_h_voice]')
                    continue
                else:
                    i = j + 1
                    continue
            else:
                i = j + 1
                continue
        else:
            j = s.find('[', i)
            if j == -1:
                piece = s[i:]
                cut = piece.find(';')          # 行内 `;` 注释（标签/引号外）
                out.append(piece[:cut].rstrip() if cut != -1 else piece.rstrip())
                break
            piece = s[i:j]
            cut = piece.find(';')
            out.append(piece[:cut].rstrip() if cut != -1 else piece.rstrip())
            i = j
    return ''.join(out)


def parse_line(s):
    """返回 (正文, 点击标记)；点击标记 ∈ {'', '@'(段界), '\\'(页界)}。"""
    s = s.rstrip('\n').rstrip('\r')
    st = s.strip()
    if st == '':
        return ('', '')
    if st.startswith(';'):          # 整行注释
        return ('', '')
    if st.startswith('&save:'):     # 变量赋值
        return ('', '')
    if st.startswith('*'):          # 标签
        return ('', '')
    click = ''
    if st.endswith('@[r]'):
        click = '@'
        idx = s.rfind('@[r]')
        body = s[:idx].rstrip()
    elif st.endswith('\\'):
        click = '\\'
        idx = s.rfind('\\')
        body = s[:idx].rstrip()
    else:
        body = s
    return (extract_text(body), click)


def flush(page, out):
    if not page:
        return
    if len(page) == 1:
        out.append(page[0])
    else:
        for seg in page:
            out.append(seg)
        out.append(''.join(page))   # 合并行（双版对照）


def extract_file(path):
    L = io.open(path, encoding='utf-8').read().split('\n')
    out = []
    buffer = ''
    page = []
    for raw in L:
        txt, click = parse_line(raw)
        if click == '':
            buffer += txt           # 框内换行 / 同段续行 → 合并
        else:
            seg = buffer + txt
            buffer = ''
            if seg:                 # 跳过空段（空框）
                page.append(seg)
            if click == '\\':       # 页界 → 收页
                flush(page, out)
                page = []
    if buffer:
        page.append(buffer)
    flush(page, out)
    return out


def main():
    if len(sys.argv) < 3:
        print('usage: extract_requartz.py <scenario_dir> <out_txt>')
        sys.exit(2)
    sdir, outp = sys.argv[1], sys.argv[2]
    files = []
    for f in ROUTE_ORDER:
        p = os.path.join(sdir, f)
        if os.path.exists(p):
            files.append(p)
        else:
            print('! 缺少路线文件:', f)
    all_lines = []
    for p in files:
        all_lines.extend(extract_file(p))
    # 去重保护：双版合并行可能恰好等于某段行的重复？不，合并行 = 多段拼接，不会等于单段。
    # 但同一页内若有两个完全相同的段行，属原文（如「…………」反复），保留。
    data = '\n'.join(all_lines)
    open(outp, 'w', encoding='utf-8-sig', newline='\n').write(data + '\n')
    print('OK %d 行 -> %s' % (len(all_lines), outp))


if __name__ == '__main__':
    main()
