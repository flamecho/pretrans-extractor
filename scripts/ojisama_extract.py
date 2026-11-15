#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]２人の王子（AbelCain / 「シナリオくん」エンジン）文本提取

链路:
  RAR5 SFX (本 .exe) -> data/sce/*.st1（剧本，cp932，XOR 0x65）
    -> ＃セリフ / ＃文字 文本元素，＃選択 选项
解密:
  原文 = (cipher 去掉「文本模式膨胀」的 0x0D) XOR 0x65
  ★ 密文里的 0x0D 0x0A 是写入时 0x0A -> 0x0D 0x0A 的膨胀（0x0A 来自明文 0x6F 的
    「バ」「出」等尾字节），必须先 replace(b'\r\n', b'\n') 再 XOR，否则会出现
    「オードoーラップ」「救い宿oされた」这类多出来的 'o'。
成行:
  ＃セリフ[<params>] / ＃文字[<params>] = 一次文本显示；参数含「追加」= 并入同一文本框
  （其余参数是颜色：ピンク/シアン/黄色/明るい紫/黄緑…）
  => 一个「无追加」命令 + 其后连续的「追加」命令 = 一个文本框 = 一次点击 = 一行；
     框内换行是该框的排版折行，直接合并。
  【名前】独占一行 = 独立名字窗 => 剥离。
  ＃選択 后以 ◇ 开头的行 = 选项，一行一条。
用法: python ojisama_extract.py <sce 目录> <out.txt>
"""
import sys, os, re, glob

KEY = 0x65

ORDER = ['opening.st1', '02battle1.st1', '03battle1.st1', '04battle1.st1',
         '2day.st1', 'battle1.st1', '3day.st1', '4day.st1', '5day.st1', '6day.st1',
         '02love.st1', '02loveending.st1', '03love.st1', '03loveending.st1',
         '04love.st1', '04loveending.st1',
         'lastbattle1.st1', 'lastbattle2.st1',
         'bad.st1', 'ending1.st1', 'ending2.st1', 'ending3.st1']

CMD = re.compile(r'^＃(\S+)(?:\t(.*))?$')
NAME = re.compile(r'^【[^】]*】$')


def load(path):
    d = open(path, 'rb').read()
    d = d.replace(b'\x0d\x0a', b'\x0a')          # 撤销文本模式的 0x0A → 0x0D 0x0A
    return bytes(b ^ KEY for b in d).decode('cp932', 'replace').replace('\r\n', '\n')


def parse(text):
    """返回 [(kind, payload)]
    kind='box'    -> payload = [seg, ...]（一个文本框内的各段；段 = 一条 ＃セリフ 含其后夹的 ＃文字）
    kind='choice' -> payload = 选项文本
    """
    out = []
    lines = text.split('\n')
    i = 0
    box = []            # 当前文本框：段列表，每段是 list[str]（行）
    seg = None          # 当前段

    def end_seg():
        nonlocal seg
        if seg is not None:
            box.append(seg)
        seg = None

    def end_box():
        nonlocal box, seg
        end_seg()
        segs = []
        for s in box:
            body = ''.join(x for x in s if x)
            if body:
                segs.append(body)
        if segs:
            out.append(('box', segs))
        box = []

    while i < len(lines):
        ln = lines[i]
        m = CMD.match(ln)
        if m:
            name, params = m.group(1), (m.group(2) or '')
            is_add = '追加' in params
            if name in ('セリフ', '文字'):
                if name == 'セリフ':
                    if is_add:
                        # 追加 = 同一文本框的下一段（不另起框、不另计点击）
                        end_seg()
                    else:
                        end_box()
                    seg = []
                else:
                    # ＃文字 = 同框内的行内特效（赤大/色替え），一律并入当前段，绝不新开段：
                    # 4day.st1「…オマエのココロは、」+＃文字(赤大)通常の３倍 +＃文字追加「は丸聞こえだ。」
                    if seg is None:
                        seg = box.pop() if box else []
                i += 1
                continue
            if name == '選択':
                end_box()
                i += 1
                # 选项行：以 ◇ 开头，直到空行或下一个命令
                while i < len(lines):
                    s = lines[i].strip()
                    if s == '' :
                        if any(l.strip().startswith('◇') for l in lines[i:i+30]):
                            i += 1
                            continue
                        break
                    if s.startswith('＃') or s.startswith('//'):
                        break
                    if s.startswith('◇'):
                        out.append(('choice', s[1:].strip()))
                    i += 1
                continue
            # 其它命令：结束当前框
            end_box()
            i += 1
            continue
        if ln.startswith('//'):
            i += 1
            continue
        if seg is not None:
            s = ln.strip()
            if s and not NAME.match(s):
                seg.append(s)
        i += 1
    end_box()
    return out


def render(items, mode='both'):
    """mode: 'both' = 双版对照（段行在前、合并行在后）；'merged' = 只合上；'split' = 只拆开"""
    rows = []
    multi = 0
    for kind, payload in items:
        if kind == 'choice':
            rows.append(payload)
            continue
        segs = [s for s in payload if s]
        if not segs:
            continue
        if len(segs) == 1:
            rows.append(segs[0])            # 单段页不重复
            continue
        multi += 1
        if mode == 'split':
            rows.extend(segs)
        elif mode == 'merged':
            rows.append(''.join(segs))
        else:
            rows.extend(segs)               # 段行 A, B, C …
            rows.append(''.join(segs))      # 合并行 ABC
    return rows, multi


def main():
    src = sys.argv[1]
    outpath = sys.argv[2]
    mode = 'both'
    if len(sys.argv) > 3 and sys.argv[3] in ('both', 'merged', 'split'):
        mode = sys.argv[3]
    result, stats, nmulti = [], {}, 0
    names = [f for f in ORDER if os.path.exists(os.path.join(src, f))]
    extra = sorted(f for f in os.listdir(src) if f.endswith('.st1') and f not in names
                   and f != '変数宣言.st1' and f != 'cgmode.st1')
    for f in names + extra:
        items = parse(load(os.path.join(src, f)))
        rows, multi = render(items, mode)
        nmulti += multi
        stats[f] = rows
        result.extend(rows)
    d = os.path.dirname(os.path.abspath(outpath))
    os.makedirs(d, exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(result) + '\n')
    total = len(result)
    print('files=%d rows=%d multi_seg_boxes=%d mode=%s' % (len(stats), total, nmulti, mode))
    for f in names + extra:
        if f in stats:
            print('  %5d  %s' % (len(stats[f]), f))


if __name__ == '__main__':
    main()
