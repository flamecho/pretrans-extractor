# -*- coding: utf-8 -*-
"""
[JP]Qualia～クオリア～ テキスト抽出 (KiriKiri/KAG3, data.xp3 内嵌 PE ラップ)
抽出ルール (skill vn-custom-bytecode-text / S6-lines-dual):
  - 双版对照: 一次点击=1行(段行) ＋ 一页=1行(合并行); 一页内 ≥2 次点击 才列合并行
  - 页境界(L0 クリア/换页): [ct2]/[ct]/[cm]/[plc]/[p]  -> ページ確定(段行＋合并行 emit)
  - 段界(L0 框内点击): [l](改行待ち)                   -> 現在セグメント確定(同頁内、清屏せず)
  - 合并类(分割せず同一行内): [s](待機)/[r](行满自翻)   -> タグ除去のみ
  - 選択肢: [link ...]TEXT[endlink] -> TEXT を1行
  - ルビ: [ruby ...]漢字[/ruby] -> 漢字(基底)を保持、タグ除去
  - システムUI/回想/デバッグは除外: [image][trans][bgm][wt][wait][fadeoutbgm]
    [resetfont][er][nowait][move][playse][layer][hpart][button][position][window]
    [font][color] および @iscript..[endscript] コードブロック、*ラベル、;コメント
  - 名札窓なし([name]=0): 話者は「」内にインライン
  - [emb exp=...] 运行时变量(玩家名 sf.sname 等) -> 整页 withheld(不猜填)
    (注意: [eval exp=...] 是独立脚本赋值命令,不产生文本 -> 不触发 withheld)
  - 出力: UTF-8 BOM + LF
"""
import sys, importlib.util

spec = importlib.util.spec_from_file_location('xp3', 'scripts/xp3.py')
xp3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(xp3)

XP3_PATH = '_work_qualia/extracted/Qualia_data.xp3'
OUT_PATH = '提取结果/[JP]Qualia～クオリア～.txt'

# ★ 双版对照（skill S6-lines-dual §0.4 / §11）：一次点击＝一行（段行）；一页（显示框）内 ≥2 次点击
#   ⇒ 该页先列各次点击的段行、再列整页合并行。
# 页边界(L0 清屏/换页)：[ct2]/[ct]/[cm]/[plc]/[p]  → 关闭一页（emit 段行＋合并行）
# 段界(L0 框内点击)：[l](改行待ち)                  → 关闭当前段（同一页内，不清屏）
# 合并类（不切分，继续累积到当前段）：[s](待機)/[r](行满自翻) → 仅去除标签
PAGE_BREAK = {'[ct2]', '[ct]', '[cm]', '[plc]', '[p]'}
SEGMENT_BREAK = {'[l]'}
CHOICE_OPEN = '[link'
CHOICE_CLOSE = '[endlink]'
RUBY_OPEN = '[ruby'

STORY_FILES = [
    'scenario/first.ks',
    'scenario/ending.ks',
    'scenario/hisabad.ks',
    'scenario/hisagood.ks',
    'scenario/sekibad.ks',
    'scenario/sekigood.ks',
    'scenario/soubad.ks',
    'scenario/sougood.ks',
]

LEAK_MARKERS = ('storage=', 'layer=', 'page=', 'visible=', 'vertical=',
               'backvisible=', 'left=', 'top=', 'opacity=', 'frame=',
               'cond=', 'target=', 'buf=', 'sysbtn', 'exp=', 'edgecolor=',
               'face=', 'size=', 'color=', 'method=', 'time=', 'repage=',
               'storage="', 'layer=', 'page=')

def tokenize(logical_line):
    toks = []
    i = 0
    n = len(logical_line)
    while i < n:
        c = logical_line[i]
        if c == '[':
            j = logical_line.find(']', i)
            if j == -1:
                toks.append(('text', logical_line[i:]))
                break
            toks.append(('tag', logical_line[i:j+1]))
            i = j + 1
        elif c == '@':
            k = logical_line.find('[', i + 1)
            if k == -1:
                k = n
            toks.append(('at', logical_line[i:k]))
            i = k
        else:
            j = i
            while j < n and logical_line[j] not in '[@':
                j += 1
            toks.append(('text', logical_line[i:j]))
            i = j
    return toks

def clean_text(s):
    s = s.replace('\r', '').replace('\n', ' ')
    # 半角标点 -> 全角（源码混用风格统一；skill 规定日文正文用「」）
    s = s.replace('｢', '「').replace('｣', '」')   # U+FF62/63 半角角括号
    s = s.replace('､', '、').replace('｡', '。').replace('･', '・')  # U+FF64/61/65 半角逗号/句号/中点
    import re
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def extract_ks(text):
    out = []
    out_withheld = []
    raw_lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')

    # コード/マクロ定義ブロックを raw 行レベルでスキップ
    # 論理行マージは行わず、各行を独立に tokenize(末尾 \ は除去) -> マージによるタグ変質を防ぐ
    cur_page_segs = []   # 当前页的各段（段行）
    cur_seg = []         # 当前段字符
    box_has_var = False  # 整页含运行时变量([emb]) ⇒ 整页 withheld
    n_merge = 0         # 合并行数（≥2 段页，仅非 withheld 页）
    in_choice = False
    cur_choice = None
    in_block = False
    cur_label = None
    BS = chr(92)
    # 名前入力/セーブ消去等のシステム画面ラベル -> その区間は除外
    SYSTEM_LABELS = {'*inputname', '*delsave', '*retitle', '*return_name'}

    def finalize_segment():
        nonlocal box_has_var
        seg = clean_text(''.join(cur_seg))
        cur_seg.clear()
        if seg:
            cur_page_segs.append(seg)

    def finalize_page():
        nonlocal box_has_var, n_merge
        finalize_segment()  # 关闭本页最后一段
        if cur_page_segs:
            if box_has_var:
                # 含 [emb] 运行时变量（玩家名等）⇒ 整页进 withheld（不猜填、不混入成品）
                out_withheld.extend(cur_page_segs)
            else:
                for seg in cur_page_segs:
                    out.append(seg)                      # 段行（一次点击一行）
                if len(cur_page_segs) >= 2:
                    out.append(''.join(cur_page_segs))   # 合并行（一页一行）
                    n_merge += 1
        cur_page_segs.clear()
        box_has_var = False

    for ln in raw_lines:
        s = ln.strip()
        # ブロック境界
        if s.startswith('[iscript') or s.startswith('@iscript') or \
           s.startswith('[macro') or s.startswith('@macro'):
            in_block = True
            continue
        if s.startswith('[endscript]') or s.startswith('@endscript') or \
           s.startswith('[endmacro]') or s.startswith('@endmacro'):
            in_block = False
            continue
        if in_block:
            continue
        # ラベル更新(*label| の | 以降は切り捨て)
        if s.startswith('*'):
            cur_label = s.split('|')[0]
            continue
        # コメント/@コマンド行はスキップ(直前ボックスは既に確定済み)
        if s.startswith(';') or s.startswith('@'):
            continue
        # システム画面区間は除外
        if cur_label in SYSTEM_LABELS:
            continue
        # 末尾 \ を除去してから tokenize(継続は次行が自然に続く)
        line = ln[:-1] if ln.endswith(BS) else ln
        toks = tokenize(line)
        for kind, val in toks:
            if kind == 'at':
                continue
            if kind == 'tag':
                if val in PAGE_BREAK:
                    finalize_page()
                    continue
                if val in SEGMENT_BREAK:
                    finalize_segment()
                    continue
                if val == CHOICE_CLOSE:
                    if in_choice and cur_choice is not None:
                        t = clean_text(''.join(cur_choice))
                        if t:
                            out.append(t)
                    in_choice = False
                    cur_choice = None
                    continue
                if val.startswith(CHOICE_OPEN):
                    in_choice = True
                    cur_choice = []
                    continue
                if val.startswith(RUBY_OPEN) or val == '[/ruby]':
                    continue
                if val.startswith('[emb'):
                    # 内联嵌入运行时变量(プレイヤー名 sf.sname/f.sname 等) -> 整页 withheld
                    # 注意: [eval exp=...] 是独立脚本赋值命令(不产生文本) -> 不触发 withheld
                    box_has_var = True
                    continue
                # その他タグ(表示コマンド等)は除去
                continue
            else:  # text
                if not val:
                    continue
                val = val.replace('[', '').replace(']', '').replace(BS, '')
                if not val:
                    continue
                if val.startswith(';') or val.startswith('*'):
                    continue
                if in_choice:
                    if cur_choice is not None:
                        cur_choice.append(val)
                    continue
                cur_seg.append(val)
    finalize_page()
    return out, out_withheld, n_merge

# 純粋なシステムUI(名前入力プロンプト等)は除外
SYSTEM_PROMPT = ('苗字を入力して', '苗字は４文字', '名前を入力して', '名前は４文字',
                 '使用できません', '他の苗字に変更', '他の名前に変更', '入力してください')

def main():
    xp = xp3.XP3(XP3_PATH)
    all_lines = []
    all_withheld = []
    total_merge = 0
    for f in STORY_FILES:
        if f not in xp.files:
            print('WARN missing', f)
            continue
        raw = xp.read(f)
        try:
            t = raw.decode('cp932')
        except UnicodeDecodeError:
            t = raw.decode('utf-8', 'replace')
        ls, wl, n_merge = extract_ks(t)
        total_merge += n_merge
        kept = []
        for ln in ls:
            if any(m in ln for m in LEAK_MARKERS):
                continue
            if any(m in ln for m in SYSTEM_PROMPT):
                continue
            kept.append(ln)
        all_lines.extend(kept)
        all_withheld.extend(wl)
        print('  %-26s -> 段行+合并 %d (内合并 %d) / 変数框 %d' % (f.split('/')[-1], len(kept), n_merge, len(wl)))
    body = '\n'.join(all_lines)
    with open(OUT_PATH, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write(body + '\n')
    wh_path = '提取结果/withheld/[JP]Qualia～クオリア～.txt'
    import os
    os.makedirs('提取结果/withheld', exist_ok=True)
    wh_body = '\n'.join(all_withheld)
    with open(wh_path, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write(wh_body + ('\n' if wh_body else ''))
    print('TOTAL 本文 %d 行 (段行 %d + 合并行 %d) -> %s'
          % (len(all_lines), len(all_lines) - total_merge, total_merge, OUT_PATH))
    print('WITHHELD 変数框 %d 行 -> %s' % (len(all_withheld), wh_path))

if __name__ == '__main__':
    main()
