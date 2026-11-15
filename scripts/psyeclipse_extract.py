# -*- coding: utf-8 -*-
# PSYCHIC ECLIPSE (TyranoScript on Electron) extractor
# L0 判据（kag.parser.js / kag.tag.js 复核）：
#   - 逐行 $.trim；';'注释、'*'标签、'@'行=tag、'#'名札(name:face, 独立名字窗=>剔除)
#   - iscript..endscript 之间文本不渲染(tag.text 检查 is_script) => 跳过
#   - [l] = showNextImg+click wait 不清屏 => 段界(一次点击)
#   - [p] = flag_ref_page + click wait, 下一文本前清屏 => 页界
#   - [cm]/[ct]/[er] = clearMessageInnerLayer => 页界(无点击)
#   - [r] = <br> 框内换行 => 合并
#   - 裸换行 = 逐 text token 顺序追加 => 直接拼接
#   - 选项 = [button graphic=*.png] 图片式无字 => 跳过(glink text= 仅引擎示例文件, 已排除)
# 输出：双版对照(同一文件内"同页先列段行 A,B,C、再列合并行 ABC"；单段页不重复)
import re, glob, os, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SCN = os.path.join(VNTRANS_HOME, '_work_psyeclipse/scenario/data/scenario')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]PSYCHIC ECLIPSE-サイキックイクリプス-.txt')
# 排除：① 未被加载的引擎示例/旧版菜单；② 引擎/系统文件（无正文，且含 &var 宏参数会漏成假文本）
ORPHANS = {'000_debug.ks','first.ks','make.ks','scenemihon.ks',
           'special_tee.ks','special_teee.ks','special_teeee.ks',
           # 引擎/系统（消息层文本=PNG 位图菜单，无 .ks 正文）
           'backlog.ks','config.ks','config.BK','extra_cg.ks','extra_scene.ks',
           'replay.ks','title.ks','tyrano.ks','_preview.ks'}
# 菜单页（bg+button，无正文）——按族剔除
MENU_PREFIX = ('in_','prof_','special')
CLEAR = {'cm','ct','er'}
SEG_END = {'l'}
PAGE_END = {'p'}
TAG_RE = re.compile(r'\[([a-zA-Z_][a-zA-Z_0-9]*)')

def read_ks(fp):
    data = open(fp,'rb').read()
    try:
        return data.decode('utf-8'), 'utf-8'
    except UnicodeDecodeError:
        return data.decode('cp932'), 'cp932'

def process(fp):
    text, enc = read_ks(fp)
    pages = []          # list of page: list of segments (each segment = str)
    seg = []            # current segment chunks
    page = []           # current page segments
    in_script = False
    in_comment = False
    pending_discard = 0 # 文本残留在 cm/er/ct 处被清 => 应为 0
    def flush_seg():
        s = ''.join(seg); seg.clear()
        page.append(s)
    def flush_page():
        if page: pages.append(page[:])
        page.clear()
    for lineno, ln in enumerate(text.split('\n'),1):
        s = ln.strip()                      # 引擎 $.trim
        if in_script:
            if TAG_RE.match('['+s) if s.startswith('[') else False: pass
            if 'endscript' in s and s.startswith('['):
                in_script = False
            continue
        if not s: continue
        c0 = s[0]
        if in_comment:
            if s == '*/': in_comment = False
            continue
        if s == '/*': in_comment = True; continue
        if c0 == ';': continue
        if c0 == '*':
            # 标签行；[s] 处为强停（页界）
            if s.startswith('[s]') or s == 's': pass
            continue
        if c0 == '@':
            t = s[1:]
            m = TAG_RE.match('[' + t)
            name = m.group(1) if m else ''
            if name == 'iscript': in_script = True
            elif name in SEG_END:
                flush_seg()
            elif name in PAGE_END:
                flush_seg(); flush_page()
            elif name in CLEAR:
                if seg: pending_discard += 1
                seg.clear(); page.clear()
            continue
        if c0 == '#':
            # 名札：独立名字窗 => 剔除名，不输出
            continue
        # 正文行：扫描内联 tag
        i = 0; buf = []
        while i < len(s):
            if s[i] == '[':
                m = TAG_RE.match(s, i)
                if m:
                    name = m.group(1)
                    # 找匹配的 ']'（无嵌套简单处理）
                    j = s.find(']', m.end())
                    if j < 0:
                        # 未闭合 tag（作者笔误）：引擎 kag.parser 按行解析，整行 tag 被丢弃，
                        # 其后的文本也被吞进 tag_str 永不渲染 => 丢弃行内剩余部分
                        break
                    inner = s[m.end():j]
                    if name == 'iscript':
                        in_script = True
                    elif name in SEG_END:
                        if buf: seg.append(''.join(buf)); buf.clear()
                        flush_seg()
                    elif name in PAGE_END or name == 's':
                        if buf: seg.append(''.join(buf)); buf.clear()
                        flush_seg(); flush_page()
                    elif name in CLEAR:
                        if buf or seg:
                            pending_discard += 1
                            print('DISCARD', os.path.basename(fp), lineno, s[:60], file=sys.stderr)
                        buf.clear(); seg.clear(); page.clear()
                    # 'r' 与其它 tag 一律忽略（r=合并）
                    i = j + 1
                    continue
            buf.append(s[i]); i += 1
        if buf:
            seg.append(''.join(buf)); buf.clear()
    # 文件尾：flush
    if seg or page:
        flush_seg(); flush_page()
    return pages, enc, pending_discard

def main():
    files = sorted(glob.glob(os.path.join(SCN,'*.ks')))
    files = [f for f in files if os.path.basename(f) not in ORPHANS
             and not os.path.basename(f).startswith(MENU_PREFIX)]
    # 补入入口剧本 scene1.ks（title.ks *gamestart @jump storage="scene1.ks"）
    files = [f for f in files if f.endswith('.ks')]
    if os.path.join(SCN,'scene1.ks') not in files:
        files.append(os.path.join(SCN,'scene1.ks'))
    # 排序：序章 scene1 最前（入口），其余按文件名
    files.sort(key=lambda f: (0 if os.path.basename(f)=='scene1.ks' else 1, os.path.basename(f)))
    out_lines = []
    total_discard = 0
    nfiles = 0
    dual_pages = 0; single_pages = 0
    for fp in files:
        pages, enc, disc = process(fp)
        total_discard += disc
        nfiles += 1
        for pg in pages:
            segs = [x for x in pg if x.strip()]
            if not segs: continue
            if len(segs) == 1:
                out_lines.append(segs[0]); single_pages += 1
            else:
                out_lines.extend(segs)
                out_lines.append(''.join(segs))   # 合并行
                dual_pages += 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT,'w',encoding='utf-8-sig',newline='\n') as w:
        w.write('\n'.join(out_lines) + '\n')
    print(f'files={nfiles} pages_single={single_pages} pages_dual={dual_pages} lines={len(out_lines)} discard_at_clear={total_discard}')

if __name__ == '__main__':
    main()
