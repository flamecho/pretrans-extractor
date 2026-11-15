"""YU-RIS / ERIS 剧本正文提取：[JP]ALL OUT

判据（L0 代码级）：
  显示单元 = cmd code 91（expr arg#0 = 裸 SJIS 原文，无操作码前缀）
  其后紧跟 cmd code 64（等待点击）——覆盖率 1496/1496
  选项 = cmd code 29 调用 "ES.SEL.SET"，字符串参数依次为各选项（''
        为占位空位，跳过）
  cmd code 30 的 arg#2 是整段登记副本，全部与 91 重复 ⇒ 排除，避免重复行
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuris_ystb import Script

# 用法：python yuris_allout_extract.py <ysbin 目录> [输出 txt]
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VNTRANS_HOME, '_work_allout/unp/ysbin')
# 阅读顺序：111 = 共通线（结尾 \GO(mako)/\GO(rin) 分岔）
#           108 = 真琴线（mako）  109 = 凛线（rin）
FILES = ['yst00111', 'yst00108', 'yst00109']
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, '提取结果/[JP]ALL OUT.txt')


def strs_of(s, args):
    """取一个 arg 的 expr 里所有 4D 压栈字符串。"""
    out = []
    for kw, ty, asg, esz, eoff in args:
        if ty != 3:
            continue
        b = s.expr[eoff:eoff + esz]
        i = 0
        while i < len(b) - 3:
            if b[i] == 0x4D:
                ln = struct.unpack_from('<H', b, i + 1)[0]
                if 2 < ln < 400 and i + 3 + ln <= len(b):
                    try:
                        out.append(b[i + 3:i + 3 + ln].decode('cp932'))
                    except UnicodeDecodeError:
                        i += 1
                        continue
                    i += 3 + ln
                    continue
            i += 1
    return out


lines = []
stat = []
for fn in FILES:
    s = Script(rf'{SRC}\{fn}.ybn')
    nline = nopt = 0
    for (code, npara, lno, args) in s.items:
        if code == 91:
            if not args:
                continue
            kw, ty, asg, esz, eoff = args[0]
            if ty != 0 or esz == 0:
                continue
            try:
                t = s.expr[eoff:eoff + esz].decode('cp932')
            except UnicodeDecodeError:
                stat.append((fn, lno, 'DECODE_FAIL'))
                continue
            t = t.strip()
            if not t:
                continue
            lines.append(t)
            nline += 1
        elif code == 29:
            ss = strs_of(s, args)
            if not ss or ss[0] != '"ES.SEL.SET"':
                continue
            opts = [x[1:-1] for x in ss[1:] if len(x) > 2]
            for o in opts:
                lines.append(o)
                nopt += 1
    stat.append((fn, 'lines', nline, 'opts', nopt))

with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
    f.write('\n'.join(lines) + '\n')

print('files', FILES)
for x in stat:
    print(' ', x)
print('total lines', len(lines))
print('wrote', OUT)
