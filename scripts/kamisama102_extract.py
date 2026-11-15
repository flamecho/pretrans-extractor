# -*- coding: utf-8 -*-
"""NScripter 文本提取器（源自 [PC-JP]神様を殺す102の方式）

L0 判据（ONScripter 源码 ONScripter_text.cpp processText()）:
  '@'      -> clickWait()       点击等待，不清框            = 段界
  '\\'      -> clickNewPage()    点击等待 + 改页（清框）      = 页界，\\ 不上屏
  '」' '）' -> checkClickstr 命中后判 getRemainingLine() <= clickstr_line
              在 4 行窗口下恒真 => 必定 clickNewPage         = 页界，且该字先上屏
  clickstr "」）",4（*define）；setwindow ...,26,4,...  正文窗 26 列 x 4 行
  textclear / textoff / erasetextwindow 1  清屏 = 页界
  物理换行 = 画面换行（同一击内）=> 合并成一行，不加分隔符
  名札【名】= 正文框首行文字（换色 -> 名札 -> 台词），name 命令 0 处

交付口径:
  台词冠说话人名 / 旁白不冠；名札去【】直接接同行；
  一页 >= 2 次点击 => 双版（段行 + 整页行）

用法:
  python kamisama102_extract.py <result.txt> <out.txt> [--dry]
  # result.txt = NSDEC.exe 解 nscript.dat 得到的 cp932 明文脚本
"""
import os
import re
import sys
import collections

COLOR = re.compile(r'#[0-9A-Fa-f]{6}')
RUBY = re.compile(r'\(([^()/]+)/([^()/]+)\)')
NP_ONLY = re.compile(r'^((?:【[^】]*】)+)$')
BRACKET = re.compile(r'【([^】]*)】')
CLICKSTR = '」）'
ELECTION = re.compile(r'^(select|csel)\b')
CMD_HEAD = re.compile(r'^[A-Za-z_!]')
LSP_TEXT = re.compile(r'^(?:lsp|msp)\s+\d+\s*,\s*"(.*)"\s*(?:,|$)')
PAGE_CLEAR = re.compile(r'^(textclear|textoff|erasetextwindow\s+1)\b')
COND = re.compile(r'^if\s+(.+?)\s+(.+)$')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff「『]')

# 系统 UI 菜单标签：其下 lsp 文字是菜单项（非剧情）
SYS_LABELS = {'*menu', '*menu_2'}
# 系统状态行（非剧情），逐条登记
SYS_STATUS = re.compile(r'到達ＥＮＤ数')

# 主角默认名（本作 `if %9==0 mov $777,"理瀬"`）
PROTAGONIST = '理瀬'


def strip_markup(t):
    t = COLOR.sub('', t)
    t = RUBY.sub(r'\1', t)
    t = t.replace('$777', PROTAGONIST)
    return t


def finish(t):
    t = strip_markup(t)
    t = BRACKET.sub(r'\1', t)
    return t.strip()


def has_quote(t):
    return any(q in t for q in '「『」』')


def _starts_quote(t):
    return t[:1] in '「『（［'


def main(src, dst=None, dry=False):
    raw_lines = open(src, 'rb').read().decode('cp932').split('\r\n')

    out = []
    st = collections.Counter()
    excluded = []

    page_clicks = []      # [(text, speaker)]
    buf = []
    click_speaker = ''
    cur_name = ''         # 本页（文本框）的名札；页结束即清空
    cur_label = ''

    def add(ch):
        nonlocal click_speaker
        if not buf:
            click_speaker = cur_name
        buf.append(ch)

    def flush_click():
        nonlocal buf, click_speaker
        seg = finish(''.join(buf))
        buf = []
        if seg:
            page_clicks.append((seg, click_speaker))
        click_speaker = cur_name

    def emit_page():
        nonlocal page_clicks, cur_name
        flush_click()
        items = list(page_clicks)
        page_clicks = []
        if not items:
            cur_name = ''
            return
        st['pages'] += 1
        # 冠名（L0）：本页（同一文本框）出现过名札 ⇒ 台词页 ⇒ 冠名；否则旁白页 ⇒ 不冠名。
        # 且只加在「首段是台词」的页；首段是旁白时，整页行也不得给旁白加名。
        speaker = items[0][1] if items[0][1] else ''
        if speaker and not has_quote(items[0][0]) and not _starts_quote(items[0][0]):
            speaker = ''
        if len(items) == 1:
            t, nm = items[0]
            st['clicks'] += 1
            if speaker:
                out.append(speaker + t)
                st['named'] += 1
            else:
                out.append(t)
                st['narration'] += 1
            cur_name = ''
            return
        for t, nm in items:
            st['clicks'] += 1
            out.append(t)
        whole = ''.join(t for t, nm in items)
        if speaker:
            out[-(len(items))] = speaker + items[0][0]   # 段行首段冠名
            whole = speaker + whole
            st['named'] += 1
        else:
            st['narration'] += 1
        out.append(whole)
        st['dual_pages'] += 1
        cur_name = ''

    def feed(text):
        for ch in text:
            if ch == '@':
                flush_click()
            elif ch == '\\':
                emit_page()
            elif ch in CLICKSTR:
                add(ch)
                emit_page()
            else:
                add(ch)

    for raw in raw_lines:
        s = raw.strip()
        if not s:
            continue
        if s.startswith('*'):
            emit_page()
            cur_label = s.split(';')[0].split()[0]
            continue
        if s.startswith(';'):
            continue

        if ELECTION.match(s):
            emit_page()
            st['opt_pts'] += 1
            for q in re.findall(r'"([^"]*)"', s):
                if q.startswith('*') or q.startswith(':'):
                    continue
                t = finish(q)
                if t:
                    out.append(t)
                    st['opts'] += 1
            continue

        if PAGE_CLEAR.match(s):
            emit_page()
            continue

        s_nc = COLOR.sub('', s)
        if NP_ONLY.match(s_nc):
            names = [x for x in BRACKET.findall(s_nc) if x]
            cur_name = '・'.join(finish(x) for x in names)
            continue

        m = LSP_TEXT.match(s)
        if m:
            body = m.group(1)
            last = None
            for cm in COLOR.finditer(body):
                last = cm
            txt = finish(body[last.end():] if last else body)
            txt = txt.rstrip('\\').strip()
            if txt and JP.search(txt):
                if cur_label in SYS_LABELS:
                    st['sys_ui_lsp'] += 1
                else:
                    emit_page()
                    out.append(txt)
                    st['telop'] += 1
            continue

        if CMD_HEAD.match(s):
            cm = COND.match(s)
            if cm:
                body = cm.group(2)
                if JP.search(body) and not re.search(r'[A-Za-z]', body):
                    feed(body)
            continue

        if SYS_STATUS.search(s):
            excluded.append(s)
            st['sys_status'] += 1
            continue

        feed(raw)

    emit_page()

    print("output lines:", len(out))
    for k, v in sorted(st.items()):
        print(f"  {k}: {v}")
    if excluded:
        print("excluded:", excluded)

    if dry or not dst:
        return out

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print("written:", dst)
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        sys.exit(2)
    main(args[0], args[1] if len(args) > 1 else None, dry='--dry' in sys.argv)
