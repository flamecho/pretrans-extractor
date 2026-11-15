# -*- coding: utf-8 -*-
"""RATW 提取：分离式 VF（game.ext 目录 + game.dat 数据）→ 复用 livemaker_extract 多脚本管线。

用法：python ratw_extract.py [--verify]
双版判据：PAUSE 事件 = 同框「继续」点击（引擎书 §4 L0）⇒ --dual-pause 段行＋合并行。
"""
import sys, zlib, argparse
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from pathlib import Path
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import livemaker_extract as lm

SRC = Path(os.path.join(VNTRANS_HOME, '_work_ratw/[JP]Round Around the World'))
OUT = Path(os.path.join(VNTRANS_HOME, '提取结果/[JP]Round Around the World.txt'))


class SplitArc:
    """game.ext = VF 目录（offsets 相对 game.dat）；trailer 全零。

    目录里每个成员有 `/name` 与 `name` 两条（字节相同，仅 7B 例外且无正文）⇒ 归一化为无斜杠名。
    """
    def __init__(self):
        self.dir = lm.VFArchive((SRC / 'game.ext').read_bytes())
        self.dat = (SRC / 'game.dat').read_bytes()
        assert self.dir.offsets[0] == 0 and self.dir.offsets[-1] == len(self.dat)
        assert not any(self.dir.encflags)
        self.ver = self.dir.ver
        self.count = self.dir.count
        self.dir_end = self.dir.dir_end
        self.offsets = self.dir.offsets
        self.names = [n.lstrip('/\\') for n in self.dir.names]
        self.index = {}
        for i, n in enumerate(self.names):
            self.index.setdefault(n, i)

    def check(self):
        errs = []
        if self.offsets[0] != 0:
            errs.append('首项 offset != 0')
        if self.offsets[-1] != len(self.dat):
            errs.append('末项 offset != game.dat 长度')
        if any(self.offsets[i] > self.offsets[i + 1] for i in range(self.count)):
            errs.append('offsets 非单调')
        return errs

    def read(self, name):
        i = self.index[name]
        raw = self.dat[self.offsets[i]:self.offsets[i + 1]]
        return zlib.decompress(raw) if self.dir.ctypes[i] == 0 else raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()
    lm.DUAL_PAUSE = True
    # 00000003 = 标题枢纽：start/load 属 スタートメニュー.lpm / スタートメニュー2.lpm（系统 UI，L0 资源串界定）；
    # 中间的 パーティ/島/海賊/軍ルート 属 ルートメニュー.lpm（上屏剧情分歧菜单）⇒ 保留
    lm.OPT_SKIP = {'00000003.lsb': ((0x1c00, 0x1e00), (0x4100, 0x4300))}
    arc = SplitArc()
    lm.load = lambda exe: arc
    # 引用目标必须真实存在于归档目录（正文字节里可巧含 `XXXXXXXX.lsb` 形态 ⇒ 伪命中过滤）
    _refs = lm.refs_of
    lm.refs_of = lambda b: [(o, t) for o, t in _refs(b) if t in arc.index]
    lm.run(str(SRC / 'RATW.exe'), None if a.verify else str(OUT))


if __name__ == '__main__':
    main()
