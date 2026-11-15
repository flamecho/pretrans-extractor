# -*- coding: utf-8 -*-
"""[JP]エイプリルーるののこりもの（LiveMaker 3，2009 同人 / キタユメ。）文本提取驱动。

用法:
    python epriru_extract.py <nokorimono.exe> [输出.txt]
    python epriru_extract.py <nokorimono.exe> --verify

★ 本作与同族前 13 作的关键差异（全部本作 L0 实证，不套用）：

1. **名札＝内嵌图 `TWdImg`（0x09），默认提取器会当噪声丢弃 ⇒ 必须还原。**
   证据：`00000001.lsb` 的 TpWord 里 `glyph_other=50`，其中 46 个是
   `グラフィック\名前\フランス.gal`(27) / `グラフィック\名前\主人公.gal`(19)，
   位置恒在**每页行首**（页文本形如 `⟦IMG:…フランス.gal⟧いででででで…`）。
   还原表来自归档内 **`グラフィック\名前\名前.TXT`（59 B，非空模板）**：
       画像	文字列
       フランス.gal	フランス：
       主人公.gal	主人公：
   ⇒ 名札按 2026-11-08 修订「一律保留」，与台词同行：`フランス：いででで…`。

2. **`TWdOpeVar` 两种**：
   - `名前`（3 处）＝玩家输入变量。默认值取自 **`変数初期化.lsb` 的 `VarNew 名前` 初值
     `ピカルディ`**（命令参数串实证 @0x57a）⇒ 行内替换为 `ピカルディ`，不落占位。
     （输入流程 `Call ノベルシステム\メッセージボックス\文字列入力.lsb` 参数
      `貴方のお名前は？` ＋ `,1,9,名前,3`：首位空 ⇒ 输入框无自带默认，初值由 VarNew 给。）
   - `DBDirectGetStr("DB名前代替","画像","主人公.gal",FALSE,FALSE,"文字列","")`（1 处）
     ＝引擎查 `DB名前代替` 表取 `主人公.gal` 的「文字列」⇒ 同上表得 `主人公：`。
     该行整体就是名札（`NAMELABEL\r\n主人公` 事件同段），⇒ 还原为 `主人公：`。

3. **断页**：`break_type==1`(PAGE)=56、`==0`(LINE)=76（页内换行，合并）、
   `PAUSE`=0、其它 break=0、控制符=0 ⇒ 每页恒 1 击 ⇒ **单版**。
   空段 8（PAGE 但无字符）⇒ 56−8=48 页。

4. 选项：`AddArray` / `選択値` 两通道**均 0 命中**（本作无分支选项，仅名字输入）。
   `コントロール.lpm` 的 セーブ/ロード/スキップ/閉じる 是右键系统菜单（L0：PrevMenu XML），不收。
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import livemaker_extract as L

# 名札还原表（源：归档内 グラフィック\名前\名前.TXT）
NAME_MAP = {
    'グラフィック\\名前\\フランス.gal': 'フランス：',
    'グラフィック\\名前\\主人公.gal': '主人公：',
}
PLAYER_NAME = 'ピカルディ'      # 源：変数初期化.lsb 的 VarNew 名前 初值
DB_NAME_EXPR = 'DBDirectGetStr("DB名前代替","画像","主人公.gal",FALSE,FALSE,"文字列","")'

PH_RE = re.compile(r'\u27e6(IMG|VAR):([^\u27e7]*)\u27e7')


def restore(s):
    """把 ⟦IMG:…⟧ / ⟦VAR:…⟧ 占位按 L0 依据还原为文字。"""
    def sub(m):
        kind, val = m.group(1), m.group(2)
        if kind == 'IMG':
            if val in NAME_MAP:
                return NAME_MAP[val]
            raise SystemExit('未登记的名札图：%r（须先查 名前.TXT）' % val)
        if val == '名前':
            return PLAYER_NAME
        if val == DB_NAME_EXPR:
            return NAME_MAP['グラフィック\\名前\\主人公.gal']
        raise SystemExit('未登记的变量：%r' % val)
    return PH_RE.sub(sub, s)


def collect(arc, verify=False):
    story = L.discover(arc)
    order, edges, orphans = L.build_order(arc, story)
    print('正文脚本 %d 本：%s' % (len(story), ', '.join(order)))
    if orphans:
        print('未连通脚本：', orphans)

    rows = []
    stats = {'page': 0, 'page_empty': 0, 'line': 0, 'pause': 0, 'ctl': 0,
             'img': 0, 'var': 0, 'chars': 0, 'blocks': 0}
    for name in order:
        b, tps0, nchar0 = story[name]
        # 带占位重扫，确保内嵌物不被静默丢弃
        tps = L.scan_tpwords(b, inline_ph=True)
        for off, end, pages, nchar, st in tps:
            stats['blocks'] += 1
            stats['chars'] += nchar
            for k in ('page', 'page_empty', 'line', 'pause', 'ctl'):
                stats[k] += st.get(k, 0)
            for p in pages:
                nph = len(PH_RE.findall(p))
                stats['img'] += sum(1 for m in PH_RE.finditer(p) if m.group(1) == 'IMG')
                stats['var'] += sum(1 for m in PH_RE.finditer(p) if m.group(1) == 'VAR')
                rows.append(restore(p))
    print('TpWord 块 %d ／ TWdChar %d 字' % (stats['blocks'], stats['chars']))
    print('PAGE %d（空段 %d）／ LINE %d ／ PAUSE %d ／ 控制符 %d'
          % (stats['page'], stats['page_empty'], stats['line'], stats['pause'], stats['ctl']))
    print('内嵌还原：名札图 %d ／ 变量 %d' % (stats['img'], stats['var']))
    print('产行 %d' % len(rows))
    lhs = stats['page'] - stats['page_empty']
    print('闭合：PAGE %d − 空段 %d = %d，产行 %d ⇒ %s'
          % (stats['page'], stats['page_empty'], lhs, len(rows), 'OK' if lhs == len(rows) else '★不符★'))
    return rows, stats


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    exe = sys.argv[1]
    verify = '--verify' in sys.argv
    args = [a for a in sys.argv[2:] if not a.startswith('--')]
    if args:
        out = args[0]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        out = os.path.join(os.path.dirname(here), '提取结果', '[JP]エイプリルーるののこりもの.txt')

    arc = L.load(exe)
    print('VF: ver=%d, %d 项, 目录末 %#x' % (arc.ver, arc.count, arc.dir_end))
    rows, stats = collect(arc, verify)
    if verify:
        print('（--verify：未写文件）')
        return 0
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(rows) + '\n').encode('utf-8'))
    print('written', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
