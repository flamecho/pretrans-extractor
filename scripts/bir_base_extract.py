#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ビルシャナ戦姫 ～源平飛花夢想～ (NS, 本体) → 全文本

链路：romfs/common/{script.memfs,script.membody}
  memfs：`RSON` + 0x10 起重复 `{u32 tag=0x2002C800, u32 off, u32 size}`
  membody：每项 `RZ` + 2 字节长度 + zlib(deflate) → **UTF-8 BOM 纯文本脚本**
          （157/158 是 RZ；1 项是未压缩纯文本，两路都要吃）

脚本语法（本作实测，与 FD《一樹の風》同族）：
  纯文本行       ＝ 正文
  <KW> / #KW     ＝ 等待点击 ⇒ **一框结束**（两者同义，本作 #KW 59 处）
  <WinClear>     ＝ 清框（跟在 <KW> 后，不产生行）
  <命令 …>       ＝ 演出/控制；`//` 行注释；`/* */` 块注释；[label] 标签
  ｛名前｝       ＝ 行首名札（游戏另开名字窗 ⇒ 丢弃）
  #R(基底,よみ)  ＝ ルビ；只删标记，基底汉字保留
  #C(TR,0xff…)   ＝ 色标；整段删
  #T1 / #T2 / #T0 ＝ **名前差分の取词切换**（不是立绘标签！）
      #T1 ＝ 默认名版（正文里直接写「義経」）
      #T2 ＝ 改名版（正文写 ${FirstName} 宏）
      #T0 ＝ 共通段
      ⇒ 一次通关只显示一支，故**保留 #T1/#T0、丢弃 #T2**（默认名口径）
  ${FirstName} / ${FirstNameSub} ＝ 主角名宏，默认值 **義経**（证据见报告 §4）

判定：一条 <KW> ＝ 一次点击 ＝ 一行；框内真实换行与字面 \\n 一律合并。
"""
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, 'tools')
from matsurika_extract import parse_memfs          # noqa: E402

PLACEHOLDERS = {'スクリプト中で使用されていません。'}   # 未实装ギャラリー枠的占位
stats_note = {}
DEFAULT_NAME = '義経'      # 依据：common 里 `GAMESTR_HeroineFirstName == 義経` 默认名判定
DEFAULT_NAME_SUB = DEFAULT_NAME

BLOCK = re.compile(r'<KW>|#KW')
TAG = re.compile(r'<[^<>]*>')
TAG_OPEN = re.compile(r'<[^<>\n]*$')
NAMEPLATE = re.compile(r'｛[^｝\n]*｝')
RUBY = re.compile(r'#R\([^)]*\)')
COLOR = re.compile(r'#C\([^)]*\)')
CHARA_TAG = re.compile(r'#[Tt]\d+')
TAG_T = re.compile(r'^\s*#T(\d)\s?(.*)$')
LABEL = re.compile(r'^\[[^\]]*\]\s*$')
COMMENT = re.compile(r'^\s*//')
BLOCKCOMMENT = re.compile(r'/\*.*?\*/', re.S)
LINE_COMMENT = re.compile(r'\s*//.*$')
SLTADD = re.compile(r'^<SltAdd\s+\d+\s*,\s*[^,]+,\s*(.*?)\s*>\s*$')
MACRO = re.compile(r'\$\{(FirstNameSub|FirstName)\}')


def read_entry(body, off, size):
    raw = body[off:off + size]
    if raw[:2] == b'RZ':
        return zlib.decompressobj().decompress(raw[6:])
    return raw


def clean_line(s):
    """单行去标记。

    ★ 顺序要紧：**先砍 `//` 行尾注释，再剥命令**。
      注释里会内嵌命令（`<Mov GAMEINT_CurrentRouteId,0>\t// …共通ルートは<Mov …>として下さい)`），
      先剥标签会把注释里的命令当正文留下（残留 `として下さい)`）。
    ★ 行首命令按「最后一个 >」整段剥——条件式里有裸 `<`（`<If x,(GAMEINT_a < 140)`）。
    """
    if '//' in s:
        s = s[:s.index('//')].strip()
        if not s:
            return ''
    if s.startswith('<'):
        k = s.rfind('>')
        if k < 0:
            return ''                               # 整行是不闭合命令
        s = s[k + 1:]
        # ★ 作者手误：`<ChrInit><Update …,${X}>}` 多半个名札括号 ⇒ 剥掉行首残括号
        s = s.lstrip('｛｝{} ')
    s = TAG.sub('', s)                              # 成对 <命令>
    s = TAG_OPEN.sub('', s)                         # 行中未闭合 <命令（吃到行尾）
    s = NAMEPLATE.sub('', s)                        # 名札 ｛…｝
    s = LINE_COMMENT.sub('', s)
    s = COLOR.sub('', s)
    s = RUBY.sub('', s)
    s = CHARA_TAG.sub('', s)
    return s.strip()


def slt_text(s):
    """`<SltAdd 序号,标签,选项文本>` → 选项文本（本作 181 条真选项）。"""
    m = SLTADD.match(s)
    if not m:
        return None
    return m.group(1).strip()


def blocks(text):
    """按 <KW>/#KW 切框，返回每框（含 #T 变体裁决、去标记、合并）的文本。"""
    # ★ 块注释可能跨越 <KW>（`/*------\n【シナリオ分岐】<KW><WinClear>\n------*/`），
    #   必须在断框前整段删掉，否则注释正文会被当成台词。
    text = BLOCKCOMMENT.sub('', text)
    # ★ 行注释也必须在断框前删：注释里含被注释掉的 `<KW>`（`//…「１」<KW><WinClear>以下の場合→…`），
    #   先断框会把它当成真断点，把一个文本框拆成两行、还会把注释尾巴当正文（`以下の場合→■ed_00_02 へ`）。
    text = re.sub(r'//[^\n]*', '', text)
    for p in BLOCK.split(text):
        variant = None              # None=未标记（当共通）／0,1,2 = #T 编号
        units, cur, dropped = [], [], []   # units=已成行单元；cur=当前框；dropped=#T2（改名版）
        kept_any = False
        for raw_ln in p.split('\n'):
            s = raw_ln.strip()
            if not s:
                continue
            # ★ 注释判定必须在「未闭合 /* 截断」之前：`//********` 第 2 字符起就是 `/*`，
            #   先截断会把它切成 `/` 当正文留下（曾产出 `////` 这种假行）。
            if COMMENT.match(s) or LABEL.match(s):
                continue
            if '/*' in s:                           # 未闭合块注释的残尾
                s = s[:s.index('/*')].strip()
                if not s:
                    continue
            m = TAG_T.match(s)
            if m:
                variant = int(m.group(1))
                s = m.group(2).strip()
                if not s:
                    continue
            ch = slt_text(s)
            if ch is not None:
                if cur:
                    units.append(cur)
                    cur = []
                if variant != 2 and ch:
                    units.append([ch])              # 选项：单独一行
                    kept_any = True
                continue
            s = clean_line(s)
            if not s:
                continue
            # 变体裁决：#T2 = 改名版 ⇒ 丢；其余（#T1 默认名版 / #T0 共通 / 未标记）留
            if variant == 2:
                dropped.append(s)
            else:
                cur.append(s)
                kept_any = True
        if cur:
            units.append(cur)
        # 守门：整框只有 #T2（源侧缺 #T1/#T0）⇒ 退回保留，避免丢正文
        if not kept_any and dropped:
            units.append(dropped)
        for u in units:
            t = ''.join(u)
            t = MACRO.sub(lambda m: DEFAULT_NAME_SUB if m.group(1) == 'FirstNameSub' else DEFAULT_NAME, t)
            t = t.replace('\ufeff', '').strip()
            # 宏已替换，此时任何 ｛｝/{} 都只可能是名札残渣
            t = re.sub(r'[｛｝{}]', '', t).strip()
            if t == 'スクリプト中で使用されていません。':
                stats_note['placeholder'] = stats_note.get('placeholder', 0) + 1
                continue
            if t:
                yield t


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'romfs/common'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'out.txt'
    ents = parse_memfs(os.path.join(root, 'script.memfs'))
    body = open(os.path.join(root, 'script.membody'), 'rb').read()
    out, stats = [], {'scripts': len(ents), 'empty': 0, 'binary': 0, 't_only': 0}
    for off, size in ents:
        b = read_entry(body, off, size)
        if b.count(0) > 4:
            stats['binary'] += 1
            continue
        try:
            raw = b.decode('utf-8-sig')
        except UnicodeDecodeError:
            stats['binary'] += 1
            continue
        # 条目 128 是 `{"filepaths":[…]}` 的脚本目录 JSON，不是剧本
        if raw.lstrip()[:1] == '{':
            stats['json'] = stats.get('json', 0) + 1
            continue
        for c in blocks(raw):
            if c.startswith('{"') or '\ufffd' in c:
                continue
            out.append(c)
    d = os.path.dirname(out_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(out) + '\n')
    print('scripts %(scripts)d / binary %(binary)d / lines' % stats, len(out))


if __name__ == '__main__':
    main()
