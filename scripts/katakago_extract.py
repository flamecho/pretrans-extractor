# -*- coding: utf-8 -*-
"""[PC-JP]貴方の鳥籠（LiveMaker 3 / VF ver=102 / TpWord 102）驱动。

复用 `livemaker_extract.py` 的通用实现，本作增量只有两项：
  1. 系统菜单按结构区段剔除（标题 / エンドリスト / アルバム / おまけ 共 30 条「選択値」），
     证据＝各区段内的引擎资源串（スタート画面・エンドリスト.gal・スチル.gal・プレビューメニュー），
     详见解析报告 §选项；
  2. 玩家输入姓名 `名字`/`名前`（1357/1277 次 TWdOpeVar）落 ⟨名字⟩/⟨名前⟩ 占位，不猜填。

用法：
    python scripts/katakago_extract.py --verify
    python scripts/katakago_extract.py --out "提取结果/[PC-JP]貴方の鳥籠.txt"
"""
import argparse
import sys

import livemaker_extract as L

# 系统菜单区段（选项记录 position 判据；段内无任何剧情 TpWord / 剧情选项）
SYSTEM_SPANS = [
    (0xB400, 0xC800),    # タイトル画面（はじめから/続きから/オプション/アルバム/エンドリスト/おまけ×2）
    (0x245400, 0x245800),  # エンドリスト（TRUEEND/NormalEnd/BadEnd/地雷１/地雷２/戻る）
    (0x2FC000, 0x2FF000),  # アルバム（スチル１〜１１/戻る）
    (0x30C300, 0x30C600),  # おまけ（ミカゲ/がにまた/黒兵衛/戻る）
]
VAR_REPL = {'⟦VAR:名字⟧': '中西', '⟦VAR:名前⟧': '美奈'}

# エンドリスト／おまけの「回想再播放」副本（与正文块逐页相同）。
# 判据（L1）：① 每块前置 1.2 KB 内出现 エンドリスト／スタッフロール 菜单代码（资源串）；
#            ② 该块 pages 与某个保留块 **逐页相等**（零文本损失）。详见解析报告 §排除。
REPLAY_BLOCKS = {
    0x245AA5,  # ＝0x1ECCE1（NormalEnd 正篇）
    0x27777C,  # ＝0x1C3CDF（BadEnd 正篇）
    0x2A095D,  # ＝0x1A5400（地雷END 正篇）
    0x2BF4A1,  # ＝0x0F1E62（正篇）
    0x2DB790,  # ＝0x164296（正篇）
    0x3019B2,  # ＝0x2F1DB5（TrueEnd 后日谈正篇；此副本在 おまけ キャストトーク 之后）
    0x30CAD0,  # ＝0x21EAD9（TrueEnd 正篇；此副本在 スタッフロール 之后）
}


def main():
    ap = argparse.ArgumentParser(description='[PC-JP]貴方の鳥籠 提取驱动')
    ap.add_argument('--exe', required=True)
    ap.add_argument('--out')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    L.DUAL_PAUSE = False     # PAUSE 全在空页（CG 等待点击），无「同框追加」⇒ 不出双版
    L.SPLIT_LINE = False     # <L>＝框内显示换行（名札 3028 处独占一行）⇒ 合并，一框一行
    L.INLINE_PH = True       # 姓名变量必须可见，不许静默丢字
    L.OPT_SKIP['00000001.lsb'] = SYSTEM_SPANS

    _scan = L.scan_tpwords

    def scan_filtered(b, *a, **k):
        return [t for t in _scan(b, *a, **k) if t[0] not in REPLAY_BLOCKS]

    L.scan_tpwords = scan_filtered

    stats, lines = L.run(a.exe, None if a.verify else a.out)
    if not a.verify:
        path = a.out
        raw = open(path, 'rb').read()
        assert raw[:3] == b'\xef\xbb\xbf'
        body = raw[3:].decode('utf-8')
        for k, v in VAR_REPL.items():
            body = body.replace(k, v)
        with open(path, 'wb') as f:
            f.write(b'\xef\xbb\xbf' + body.encode('utf-8'))
        left = body.count('⟦')
        print('占位替换后残留 ⟦ 计数 = %d' % left)
        print('成品 %d 行 / %d 字' % (body.count('\n'), sum(len(x) for x in body.split('\n'))))
        assert left == 0

if __name__ == '__main__':
    main()
