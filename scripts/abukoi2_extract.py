# -*- coding: utf-8 -*-
"""[PSV-JP]アブナイ恋の捜査室 ~Eternal Happiness~ 文本提取器

引擎: ASGARD 自研 TAT 文本 DSL（UTF-8-BOM 明文，<TAG> 指令 + [LABEL] + 裸文本行）
链路: PKG -> pkg2zip -> app/PCSG00591 (PFS 密文) -> psvpfsparser -z games.json[PCSG00591] -> dec/ UTF-8 明文

用法:
    python alicis2_extract.py <解密后 script_tat 目录> [输出.txt]
    输出默认锚定 <_Trans>/提取结果/[PSV-JP]アブナイ恋の捜査室 ~Eternal Happiness~.txt

成行判据（L0/L1，本作实证）:
  - 一次点击 = `<KW>`（KW=KeyWait）。28,697 个 KW，其中 28,600 与 <WinClear> 同行
    （28,595 段以 `<KW><WinClear>` 收尾 + 3 段仅 `<WinClear>` + 100 段仅 `<KW>`）。
  - **硬证据（本作结构自证，非统计）**：100 个 bare `<KW>` 中 98 个后面紧跟
    `<SltDel>/<SltAdd>/<SltRun>` 选择块 → `<Jump LABEL_…>` 到别的 label ⇒ **换页**
    （选择块本身要清屏重绘），另 2 个后面无正文（仅换场景图）。
    ⇒ 因此 `KW` 单独出现也＝页结束，与 `KW+WinClear` 同义（引擎里 KW 后必须 WinClear 才能
    继续显示新页，脚本省略 WinClear 时由选择指令隐式清屏）。
  - **软换行** = 同一页里多条物理文本行（无 KW/WinClear 分隔），例如
    `二人とも肩や首を回す。` + `すると、誰かが…` 同页 ⇒ 合并为一行。
    实测 27,455 页为单行、989 页 2 行、54 页 3 行。
  - **名札** = 独立成行 `【名前】`（`//∽[NAME=…]` 宏标注），2026-11-08 修订 **一律保留**
    → 与同行台词并列 `【名】「台词」`（本作名札为**文字**，不是图片）。
  - **选项** = `<SltAdd idx,LABEL,txt>` 第 3 字段（3 字段全库 306 条，无 4 字段 dev 菜单）。
  - **主角宏** `{LNAME}`/`{FNAME}`（9,393 / 337 处）⇒ 行内替换为 PSP 版同名主角 櫻井 / 翼
    （vndb v9197 char 页；本作无默认名入口，用户可自定；沿用 PSP 版即跨平台一致）。
  - 非显示控制码：无 `#C0-9`/`#S[0-9]`（本作 0 处）。
  - 排除：`test.tat`（dev harness：特殊文字/選択肢/ジャンプ 测试）、`misc.tat`（占位 1 行）。
  - `memorial/`：回想重播，与 `main/`+`sub/` 覆盖率 0.9915（2,467 页中 2,446 页逐字相同，
    21 页为版本差异措辞）⇒ **不收**（回想＝日志类载体）。
  - `sub/`：各角色 2/4/6 章后「おまけ」+ end 后「SUPER HAPPY 后」+ HAPPY 8 章后篇
    （标题带 `おまけ`/`●N章後●`/`SUPER HAPPY`/`HAPPY`），与 main 覆盖率 0.077 ⇒ **收**。
  - `main/H*`（9–12 日目：9日目・10日目・11日目・12日目）与 `main/N*`（HAPPY 线）
    是**不同分支**（HAPPY/H 路线是 9 日目之后的分歧），文本重合仅个位数行 ⇒ **全收**。
  - `main/STH*`（7 个 SUPERE HAPPY 后 epilogue）与 main/sub 重合 15–26 页（多为问好/场景复用）
    ⇒ **收**（v每次独立章节；与 main 不重复的文字约占 90%）。
"""
import os
import re
import sys

TAG = re.compile(r'<[^>]*>')
NAME_RE = re.compile(r'^【[^】]{1,40}】$')
SLTADD = re.compile(r'<SltAdd\s+([^>]*)>')
VOICE_RE = re.compile(r'//∽\[Voice="([^"]+)"\]')

NAME_FIRST = '翼'      # {FNAME}
NAME_FAMILY = '櫻井'    # {LNAME}

# 排除文件（basename, 全小写比对）
SKIP = {'test.tat', 'misc.tat', 'main.tat'}


def read(p):
    return open(p, 'rb').read().decode('utf-8-sig', errors='replace')


def split_comment(s):
    i = s.find('//')
    return s[:i] if i >= 0 else s


def strip_tags(s):
    return TAG.sub('', s)


def clean_text(s):
    s = strip_tags(s)
    s = s.replace('{LNAME}', NAME_FAMILY).replace('{FNAME}', NAME_FIRST)
    s = s.strip(' \u3000\t\r')
    return s


def parse(path):
    """Return list of ('line', text) / ('opt', text)."""
    raw = read(path)
    lines = raw.split('\n')
    out = []
    buf = []           # current page text pieces
    name = ''          # current nameplate (set before a text line)
    cur_voice = None   # voice currently assigned to this page
    pending_opts = []

    def flush_page():
        nonlocal buf, name, cur_voice
        if buf:
            body = ''.join(buf)
            out.append(('line', (name + body) if name else body))
        buf = []
        name = ''
        cur_voice = None

    for L in lines:
        # 隐藏分页：同一 KW 段内出现**另一条 Voice** 且已累积文本 ⇒ 作者漏写 <KW>，
        # 按 Voice 边界断页（本作实测仅 HHOZUMI11.TAT 1 例：ONO_1148 / ONO_1148_01）
        vm = VOICE_RE.search(L)
        if vm:
            v = vm.group(1)
            if cur_voice is not None and v != cur_voice and buf:
                flush_page()
            cur_voice = v
        # choice tags first (they may share a line with nothing else)
        for m in SLTADD.finditer(L):
            args = m.group(1)
            parts = [x.strip() for x in args.split(',')]
            if len(parts) == 3:
                t = clean_text(parts[2])
                if t:
                    pending_opts.append(t)
        if '<SltRun>' in L:
            for t in pending_opts:
                out.append(('opt', t))
            pending_opts = []
            continue
        if '<KW>' in L:
            flush_page()
            continue
        if '<WinClear>' in L:
            flush_page()
            continue
        code = split_comment(L).strip()
        if not code:
            continue
        if code.startswith('['):
            # [LABEL_x] / [Se=""] / [WATI=""] — non-display
            if code.startswith('[LABEL_'):
                flush_page()
            continue
        if NAME_RE.match(code):
            name = code.replace('{LNAME}', NAME_FAMILY).replace('{FNAME}', NAME_FIRST)
            continue
        t = clean_text(code)
        if t:
            # 源脚本笔误残渣：正文里孤立 1–2 个 ASCII 字母且同行夹着 <…> 指令
            # （实测全库仅 FUJIMORIend_a.TAT:882 行首误敲的 'x'）⇒ 丢弃
            if len(t) <= 2 and '<' in code and t.isascii() and t.isalpha():
                continue
            buf.append(t)
    flush_page()
    return out


def order_key(relpath):
    """Order: main/ (1.TAT, routes AKECHI..SMITH, H*, N*, STH*) then sub/."""
    p = relpath.replace('\\', '/')
    grp = p.split('/')[0]
    base = os.path.basename(p).upper()
    g = 0 if grp == 'main' else (1 if grp == 'sub' else 2)
    # route order matching CHARACTER_ORDER in game
    chars = ['1', 'AKECHI', 'FUJIMORI', 'HOZUMI', 'KISARAGI', 'OGASAWARA', 'ONOSE', 'SMITH']
    ci = 0
    for i, c in enumerate(chars):
        if base.startswith(c):
            ci = i
            break
    if base.startswith('STH'):
        ci = 90
    if base.startswith('H') and not base.startswith('HO'):
        ci = 50
    if base.startswith('N') and not base.startswith('NO'):
        ci = 60
    m = re.search(r'(\d+)', base)
    num = int(m.group(1)) if m else 0
    return (g, ci, num, base)


def main():
    if len(sys.argv) < 2:
        print('用法: python alicis2_extract.py <解密后 script_tat 目录> [输出.txt]', file=sys.stderr)
        return 2
    src = sys.argv[1]
    if len(sys.argv) >= 3:
        dst = sys.argv[2]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        dst = os.path.join(os.path.dirname(here), '提取结果',
                           '[PSV-JP]アブナイ恋の捜査室 ~Eternal Happiness~.txt')

    files = []
    for root, _, names in os.walk(src):
        for n in names:
            if not n.lower().endswith('.tat'):
                continue
            rel = os.path.relpath(os.path.join(root, n), src)
            if n.lower() in SKIP:
                continue
            if rel.replace('\\', '/').split('/')[0].lower() == 'memorial':
                continue
            files.append(rel)
    files.sort(key=order_key)

    rows = []
    stat = {'line': 0, 'opt': 0}
    for rel in files:
        for kind, t in parse(os.path.join(src, rel)):
            rows.append(t)
            stat[kind] += 1

    with open(dst, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(rows) + '\n').encode('utf-8'))
    print('files=%d  line=%d  opt=%d  total=%d' % (len(files), stat['line'], stat['opt'], len(rows)))
    print('written', dst)
    return 0


if __name__ == '__main__':
    sys.exit(main())
