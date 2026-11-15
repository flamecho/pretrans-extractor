# -*- coding: utf-8 -*-
"""核验高-ja 的 0-box 文件：ja 在 iscript 内 vs 外，外显文本样本，页界标签计数。"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xp3 import XP3
from recall_extract import read_ks

XP3_PATH = os.path.join(VNTRANS_HOME, "_work_recall/src/[JP]Recall/data.xp3")
xp3 = XP3(XP3_PATH)
ks = sorted(n for n in xp3.files if n.lower().endswith('.ks'))

SUSPECTS = ['scenario2/終了会話.ks','scenario2/戦闘味方ターン.ks','scenario2/戦闘敗北会話.ks',
            'scenario2/戦闘敵ターン.ks','scenario2/戦闘.ks','scenario2/終了会話調査.ks',
            'scenario/初期値変数代入.ks','scenario/rclick_tjs21.ks','scenario/戦術指示2.ks']

for name in SUSPECTS:
    t = read_ks(xp3, name)
    # 拆分 iscript 块
    parts = re.split(r'(\[iscript|@iscript|\[endscript)', t, flags=re.I)
    in_sc = False; ja_in = 0; ja_out = 0; out_txt = []
    for i, p in enumerate(parts):
        if re.match(r'\[iscript|@iscript', p, re.I):
            in_sc = True; continue
        if re.match(r'\[endscript', p, re.I):
            in_sc = False; continue
        ja = len(re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]', p))
        if in_sc: ja_in += ja
        else:
            ja_out += ja
            if len(out_txt) < 1 and ja > 0:
                # 抽取非 tag 的可见文本片段
                clean = re.sub(r'\[[^\]]*\]', '', p)
                clean = re.sub(r'[\u3000\s]+', ' ', clean).strip()
                if clean: out_txt.append(clean[:300])
    breaks = {b: t.count('['+b+']') for b in ['p','e','er','ct','cm','pe','ple','clear','r','l','waitclick']}
    print(f"### {name}")
    print(f"    ja_in_script={ja_in}  ja_out_script={ja_out}")
    print(f"    breaks={breaks}")
    for s in out_txt[:2]:
        print(f"    OUT_TXT> {s}")
    print()
