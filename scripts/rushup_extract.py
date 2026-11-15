# [JP]RUSH×UP！ (KiriKiri2/KAG3, O.M.D Ver.1.1) 全文本提取
# 源: rush.exe PE+尾挂 XP3 @0x34d800 → 1839 成员；正文=scenario/chapter_*.ks 34 本
# L0 断框: MainWindow.tjs p=showPageBreak(点击清屏) / l=showLineBreak(点击不清屏)
#   np 宏=[er][label][er] 清屏⇒页界; plc 宏=[p][cm]⇒点击+清屏; cm/er/ct⇒页界
#   Config.tjs ignoreCR 注释掉=默认 false ⇒ 物理换行=框内换行(合并); [r]=框内换行
#   [l] 仅 3 处(chapter_1001×1/chapter_1002×2)=同框多击 ⇒ 双版 3 处
# 名札: name/name2 宏=[image layer=4/5] 独立名札**画像** ⇒ 正文无名前缀, 无需剔
# 选项: 全部 [button graphic=...] 图片式无字选项(50 处) ⇒ 按规则跳过;
#   [link] 仅 chapter_1001 *chapter_00 的 OP 跳过系统菜单 2 条 ⇒ 剔(SKIP_OPTS)
# [graph alt=...] alt 只写 historyLayer(履歴) 不上屏 ⇒ 丢; ruby text=读音 ⇒ 丢注留基底
# 0*_scene.ks=回想专用复制(正文已在 chapter_5xxx/12xx 本篇内) ⇒ 不收; op.ks 0 文本
import sys, os, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ks_kag_text import parse, read_ks, load_macros, macro_events, macro_texts, render

SKIP_OPTS = {'転校初日から始める', 'オープニングを見る'}  # OPスキップ系统菜单

def main():
    scen = sys.argv[1] if len(sys.argv) > 1 else 'x/scenario'
    files = sorted(f for f in os.listdir(scen) if re.match(r'^chapter_', f))
    macros = load_macros(scen)
    ev, mt = macro_events(macros), macro_texts(macros)
    allpages, allopts = [], []
    dual_log = []
    for f in files:
        pages, opts, st = parse(read_ks(os.path.join(scen, f)), ev, macro_txt=mt)
        for i, p in enumerate(pages):
            if len(p) > 1:
                dual_log.append((f, i, p))
        allopts += [(pos + len(allpages), t) for pos, t in opts if t not in SKIP_OPTS]
        allpages += pages
    lines, multi = render(allpages, allopts, 'dual')
    # 源码 3 处 `[button …]]` 双右括号笔误 ⇒ 多出的 `]` 被当文本记号, 剔除(脚本残留)
    lines = [l for l in lines if l.strip() != ']']
    out = Path(__file__).resolve().parent.parent / '提取结果/[JP]RUSH×UP！.txt'
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('files', len(files), 'pages', len(allpages),
          'segs', sum(len(p) for p in allpages), 'multi', multi,
          'opts', len(allopts), 'lines', len(lines))
    for f, i, p in dual_log:
        print('DUAL', f, i, [s[:40] for s in p])

if __name__ == '__main__':
    main()