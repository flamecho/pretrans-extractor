import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
# Rosarium ～繋がれた少年～ (RealLive / OPTiM 2005) 全文本提取
# L0 断框: WINDOW.000.R_COMMAND_MOD=0 ⇒ pause(0:3:17)=NewPageOnAllAfterLongop=点击后清屏
#   spause(0:3:205)=点击不清屏(同框多击) / msgHide(151)/msgClear(152)/page(210)=框界
#   br(201)/par(3)=框内换行(合并) / ruby 120/1+基底+120/0(gloss丢弃)
# 名札: NAME_MOD=1 独立名字窗 ⇒ 剔行首【名】
# 变量: ％Ａ=GetLocalName(0)=名字输入(nwSingleLocal 1:4:1312) ⇒ 填ルカ
#   (证据: 输入后紧邻字面名札【ルカ】+ SEEN0601「ルカです」+ vndb v3528 主角ルカ)
#   ＊Ａ=全局名槽(全游戏未赋值, 1处, 上下文=主角) ⇒ 填ルカ
#   选项内 ###PRINT($0C[..])=strM 提示文本(菜单 hint 系统, OFF 时为空) ⇒ 剥除
import re, sys
from pathlib import Path
from rl_decomp import decompress, read_toc, scenario
from rl_parse import parse_scenario

SKIP_SCENES = {1, 51, 52, 53, 300, 9999}  # 系统/菜单/无正文(报告单列)
NAME_SUB = {'％Ａ': 'ルカ', '＊Ａ': 'ルカ'}
PRINT_RE = re.compile(r'###PRINT\([^)]*\)')
TAG_RE = re.compile(r'^【[^】]*】')

def unquote(b):
    # rlvm TextoutElement::GetText: '"' 是字节码文本定界符(保护 ! 等字面量), 不上屏
    return b.replace(b'"', b'')

def clean_text(t):
    t = unquote(t).decode('cp932')
    for k, v in NAME_SUB.items():
        t = t.replace(k, v)
    return t

def clean_line(t):
    t = TAG_RE.sub('', t)
    return t.rstrip()

def clean_opt(t):
    t = unquote(t).decode('cp932')
    t = PRINT_RE.sub('', t)
    for k, v in NAME_SUB.items():
        t = t.replace(k, v)
    return t.strip()

def extract_scene(sn, code, out, stats):
    seg = []
    frame = []

    def end_seg():
        nonlocal seg
        s = ''.join(seg)
        seg = []
        if s:
            frame.append(s)

    def flush():
        nonlocal frame
        end_seg()
        lines = [clean_line(s) for s in frame]
        lines = [s for s in lines if s]
        frame = []
        if not lines:
            return
        stats['frames'] += 1
        stats['segments'] += len(lines)
        if len(lines) > 1:
            stats['dual_frames'] += 1
            out.extend(lines)
            merged = ''.join(lines)
            out.append(merged)
            stats['merged'] += 1
            stats['dual_log'].append((sn, lines))
        else:
            out.append(lines[0])

    for kind, val in parse_scenario(code):
        if kind == 'text':
            t = clean_text(val)
            if t.startswith('ＳｅｅｎＥｎｄ'):
                continue
            seg.append(t)
            stats['text_chars'] += len(t)
        elif kind == 'func':
            mt, mo, op, ov, extra = val
            if (mt, mo) == (0, 3):
                if op in (201, 3):  # br / par: 框内换行合并
                    stats['soft_breaks'] += 1
                elif op == 205:  # spause: 同框下一次点击
                    end_seg()
                    stats['spause'] += 1
                elif op in (17, 151, 152, 210):  # pause/msgHide/msgClear/page
                    flush()
                elif op == 120:
                    stats['ruby'] += 1  # gloss 参数丢弃, 基底已在 text 中
        elif kind == 'select':
            flush()
            for o in val[4]['opts']:
                s = clean_opt(o)
                if s:
                    out.append(s)
                    stats['options'] += 1
    flush()

def main():
    seen = sys.argv[1] if len(sys.argv) > 1 else 'game/Seen.txt'
    d = open(seen, 'rb').read()
    out = []
    stats = dict(frames=0, segments=0, dual_frames=0, merged=0, options=0,
                 text_chars=0, soft_breaks=0, spause=0, ruby=0, dual_log=[])
    for sn, (off, ln) in sorted(read_toc(d).items()):
        if sn in SKIP_SCENES:
            continue
        _, _, co, dl, cl, s = scenario(d, off, ln)
        code = decompress(s[co:co + cl], dl)
        assert len(code) == dl
        extract_scene(sn, code, out, stats)
    path = Path(os.environ.get('VNTRANS_HOME', os.getcwd())) / '提取结果/[JP]Rosarium～繋がれた少年～.txt'
    with open(path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('lines', len(out))
    for k, v in stats.items():
        if k != 'dual_log':
            print(k, v)
    for sn, lines in stats['dual_log']:
        print('DUAL', sn, lines)

if __name__ == '__main__':
    main()
