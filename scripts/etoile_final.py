# -*- coding: utf-8 -*-
"""SCPT 目录 -> 最终全文本（一行 = 一次点击）

规则：
  - 控制码 ▼(0x81A5) ∋(0x81B9) ⊆(0x81BA) ∈(0x81B8) 视作 message box 分隔 -> 拆行
  - 行内 \\n 合并（同一框内换行）
  - 行首 [主人公] 删除（不加说话人前缀）
  - 行内 [主人公] 替换为主角名 エンジュ
  - 丢弃非日文行、空行
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from etoile_text import LABEL  # noqa: E402

HEROINE = 'エンジュ'
# ▼∋⊆∈ = 0x81A5/B9/BA/B8 message box 分隔；#t1/#t2 = 脚本层的分页控制码
CTRL = re.compile(r'[\u25bc\u220b\u2286\u2208]|#t\d')
COLOR = re.compile(r'#c\d+')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def boxes(blob):
    """返回 [message_box_text, ...]"""
    out = []
    for m in LABEL.finditer(blob):
        st = m.end()
        en = blob.find(b'\x00', st)
        if en < 0:
            continue
        raw = blob[st:en]
        if not raw or b'\x00' in raw:
            continue
        try:
            s = raw.decode('cp932')
        except UnicodeDecodeError:
            continue
        for part in CTRL.split(s):
            t = ''.join(x.strip() for x in part.split('\n'))
            t = t.strip()
            # 纯名字行：#c9クラヴィス#c0 —— 带色名字，按口径不收说话人前缀
            if t.startswith('#c') and t.endswith('#c0') and len(COLOR.sub('', t)) <= 12:
                continue
            t = COLOR.sub('', t)
            t = re.sub(r'^\[主人公\]', '', t)
            t = t.replace('[主人公]', HEROINE)
            t = t.strip()
            if not t:
                continue
            # 纯标点块（『』「」。、等）并入上一行，避免断引号
            if not JP.search(t) and out and all(ch in '。、，．』」）！？…' for ch in t):
                out[-1] += t
                continue
            if not JP.search(t):
                continue
            t = re.sub(r'^[。、，．]+', '', t)   # 名字占位符删掉后残留的行首标点
            t = t.strip()
            if not t or 'システムメッセージ' in t or 'ﾎﾞﾘｭｰﾑ' in t or '本編用アイテム' in t:
                continue
            # 孤立的开引号（原文被变量切断）直接去掉，避免残符号
            while t.count('『') > t.count('』'):
                t = t[::-1].replace('『', '', 1)[::-1].strip()
            while t.count('「') > t.count('」'):
                t = t[::-1].replace('「', '', 1)[::-1].strip()
            if t:
                out.append(t)
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VNTRANS_HOME, '_work_etoile/scpt2')
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, '_work_etoile/final.txt')
    total = 0
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fp:
        for f in sorted(os.listdir(src)):
            if not f.endswith('.scpt'):
                continue
            for line in boxes(open(os.path.join(src, f), 'rb').read()):
                fp.write(line + '\n')
                total += 1
    print('lines=%d -> %s' % (total, dst))


if __name__ == '__main__':
    main()
