#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP]Alice in Dreamworld —— KiriKiri/KAG3 cp932 脚本 → 全文本（一次点击一行）

L0 断页判据（读本作 `system/MainWindow.tjs` 分发表 + `scenario/macro.ks` 宏体实证）：
  [r]         processReturn()              页内换行（满行才翻页）      ⇒ 合并
  [l]         showLineBreak()              conductor.wait({click})    ⇒ 一次点击
  [lr]        macro = [l][r]               同上                        ⇒ 一次点击
  [waitclick] waitClick()                  一次点击
  [p]         showPageBreak()              wait(click)                ⇒ 页结束
  [cm]        clearMessageLayers(false)    清屏                        ⇒ 页界
  [ct]        clearMessageLayers(true)     清屏                        ⇒ 页界
  [er]        current.clear()              清屏                        ⇒ 页界
  [plc]       macro = [p][label][cm]       页结束 + 清屏               ⇒ 页界
  [s]         inSleep = true               选项/入力待ち               ⇒ 段界
  [nowait]/[endnowait]   enterNoWait/leaveNoWait 只改打字速度 ⇒ 不影响点击
  [hr]        historyLayer.reline()        只写历史层，屏幕不换行      ⇒ 合并
  [link target=…]文本[endlink]              beginHyperLink             ⇒ 选项（独立一行）

名札（正文内，保留）：角色宏宏体 = `[locate x=4][nowait][font size=22]
      [emb exp="'名'" cond=%visible|true][resetfont][r][locate y=52]…[indent]`
      ⇒ 名字画进 message0 正文页内（无独立名字窗 / 无 frame=name / 无 message3）
      ⇒ 保留并接同行台词前（names-and-macros.md "名札印在正文页内 ⇒ 保留"）
      ⚠ 宏参数 `visible="false"` ⇒ `cond` 为假 ⇒ [emb] 不画名（初登场只有声音）⇒ 不输出名
上屏字：角色宏尾 `「`；`mes_end` 宏 = `」[endindent][ボイス終了待ち]`
        心声宏（`_m`）尾 `（`；`mono_end` 宏 = `）[endindent]`
        `nare` 宏 = `[locate x=4][nowait][r][locate y=52]　[endnowait][indent]`（一个全角空格）
        `同時発言_同` 宏体只输出 `「+mes+」`（`name` 参数不上屏）
        `同時発言_別` 宏体只输出 `「+mes1+」　　「+mes2+」`（`name1/name2` 不上屏）
"""
import os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '_work_alice_dw/out_patch/main.ks'
OUT = sys.argv[2] if len(sys.argv) > 2 else '提取结果/[PC-JP]Alice in Dreamworld.txt'
DUAL = '--dual' in sys.argv

ROLES_QUOTE = ['愛梨', 'アリス', '白の騎士', '眠りネズミ', '帽子屋', '三月ウサギ', 'トイードル',
               'チシャ猫', 'ジャック', 'ジョーカー', 'パット', '白ウサギ', '女王', '善禎',
               '拓海', '沙樹', 'レオ', '新汰', '新良', '昌臣', '千代', '善之助', '祥', '亮',
               '鈴', 'つぐみ', '亮之介']
ROLE_PAREN = {'愛梨_m': '愛梨', 'アリス_m': 'アリス'}
ROLE_KIND = {r: 'quote' for r in ROLES_QUOTE}
ROLE_KIND.update({k: 'paren' for k in ROLE_PAREN})
ROLE_NAME = {r: r for r in ROLES_QUOTE}
ROLE_NAME.update(ROLE_PAREN)

PAGE_TAGS = {'p', 'cm', 'ct', 'er', 'plc'}
CLICK_TAGS = {'l', 'lr', 'waitclick', 's'}

# KAG 标签扫描：必须容忍 `[0]`（eval exp="…layers[0]…"）与源内笔误 `name2="X""]`
# ⇒ 先按「括号深度 + 引号状态」走；走不通（行内未闭合）退回「遇到第一个 ] 就收」。
def iter_tags(s):
    i, n = 0, len(s)
    while i < n:
        j = s.find('[', i)
        if j < 0:
            return
        depth, q, k, ok = 0, None, j + 1, False
        while k < n:
            c = s[k]
            if q:
                if c == '\\':
                    k += 2
                    continue
                if c == q:
                    q = None
            elif c in '"\'':
                q = c
            elif c == '[':
                depth += 1
            elif c == ']':
                if depth == 0:
                    ok = True
                    break
                depth -= 1
            k += 1
        if not ok:
            k = s.find(']', j + 1)
            if k < 0:
                return
        yield j, k + 1, s[j + 1:k]
        i = k + 1


def tag_name(p):
    m = re.match(r'([^\s=\]]+)', p.strip())
    return m.group(1) if m else ''


def unq(s):
    """参数值可能是 "\"'…'\"" 这种带内层单引号的字面（宏形参写法）⇒ 逐层剥"""
    s = s.strip()
    while len(s) >= 2 and s[0] == s[-1] and s[0] in '\'"':
        s = s[1:-1].strip()
    return s


def sstrip(s):
    # ASCII空白のみ除去。U+3000は原作の排版字（縮行/字卡間隔）なので残す
    return s.strip(' \t\r\n\x00')


def arg(p, key):
    m = re.search(r'\b' + key + r'\s*=\s*("[^"]*"|\'[^\']*\')', p)
    return unq(m.group(1)) if m else None


def extract(path):
    txt = open(path, 'rb').read().decode('cp932').replace('\r\n', '\n')
    pages = []            # list[list[(text, is_link)]] 页 → 段
    cur_page, cur_seg = [], []
    seg_is_link = [False]

    def flush_seg(link=False):
        nonlocal cur_seg
        s = sstrip(''.join(cur_seg))
        cur_seg = []
        if s:
            cur_page.append((s, link))

    def flush_page():
        nonlocal cur_page
        flush_seg()
        if cur_page:
            pages.append(cur_page)
        cur_page = []

    for ln in txt.split('\n'):
        st = ln.strip(' \t\r\n')
        if not st or st.startswith(';') or st.startswith('*') or st.startswith('//'):
            continue
        # 整行只有空白（含 U+3000）⇒ 无字形，等同空行（源 L16592/L28407 各 1 例作者遗留）
        # 注意：行「内」的 U+3000（如 `鈴　`）是排版字，必须保留 ⇒ 只判整行
        if not st.strip():
            continue
        tags = list(iter_tags(st))
        if not tags:
            # 裸文本行：上屏字。作者漏写 ';' 的注记行（本作仅 1 例 `※画面中央に文字FI`）⇒ 剔
            if st.startswith('※'):
                continue
            cur_seg.append(st)
            continue

        pos = 0
        for m_start, m_end, p in tags:
            if m_start > pos:
                cur_seg.append(st[pos:m_start])
            pos = m_end
            name = tag_name(p)
            if not name:
                continue

            if name == 'link':
                flush_seg()
                continue
            if name == 'endlink':
                # 选项/按钮文字：本段整体标记为 link，页末再决定「并列选项」还是「内联按钮」
                flush_seg(link=True)
                continue

            if name in ROLE_KIND:
                hidden = (arg(p, 'visible') or '').lower() == 'false'
                mark = '「' if ROLE_KIND[name] == 'quote' else '（'
                cur_seg.append(('' if hidden else ROLE_NAME[name]) + mark)
                continue
            if name == 'mes_end':
                cur_seg.append('」')
                continue
            if name == 'mono_end':
                cur_seg.append('）')
                continue
            if name == 'nare':
                cur_seg.append('\u3000')
                continue
            if name == 'その他':
                hidden = (arg(p, 'visible') or '').lower() == 'false'
                nm = arg(p, 'name') or ''
                cur_seg.append(('' if hidden else nm) + '「')
                continue
            if name == '同時発言_同':
                cur_seg.append('「' + (arg(p, 'mes') or '') + '」')
                continue
            if name == '同時発言_別':
                cur_seg.append('「' + (arg(p, 'mes1') or '') + '」\u3000\u3000「'
                               + (arg(p, 'mes2') or '') + '」')
                continue
            if name in CLICK_TAGS:
                flush_seg()
                continue
            if name in PAGE_TAGS:
                flush_page()
                continue
            # 其余（演出/样式/音声/立绘/条件/履歴出力…）= 不上屏，剥
        if pos < len(st):
            cur_seg.append(st[pos:])

    flush_page()
    return pages


def page_rows(segs):
    """页 → 行（L0 口径）。

    页界 = [p]/[cm]/[ct]/[er]/[plc]；段界 = [l]/[lr]/[waitclick]/[s]。
    · 同页 ≥2 个 [link]                    ⇒ 并列选项：每项一行
    · 同页 ≥2 段（非 link，来自 [l]/[lr]）  ⇒ 一页多次点击 ⇒ 双版：段行各一行 ＋ 整页行
    · 其余（含单 [link] 的「表单/确认按钮」）⇒ 整页一行（[link] 文字内联）
    """
    links = [x for x in segs if x[1]]
    if len(links) >= 2:
        return [t for t, _ in segs]
    plain = [x for x in segs if not x[1]]
    if len(plain) >= 2:
        rows = [t for t, _ in segs]
        rows.append(sstrip(''.join(t for t, _ in segs)))
        return rows
    merged = sstrip(''.join(t for t, _ in segs))
    return [merged] if merged else []


def main():
    pages = extract(SRC)
    rows, multi = [], 0
    for pg in pages:
        segs = [x for x in pg if x[0]]
        if not segs:
            continue
        if len(segs) >= 2:
            multi += 1
        rows.extend(page_rows(segs))
    data = '\n'.join(rows) + '\n'
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        f.write('\ufeff' + data)
    print('pages=%d rows=%d multi_seg_pages=%d bytes=%d maxw=%d' %
          (len(pages), len(rows), multi, len(data.encode('utf-8')),
           max((len(r) for r in rows), default=0)))


if __name__ == '__main__':
    main()
