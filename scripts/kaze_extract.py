"""風色サーフ (PS2) 全文本抽出器。

容器链：ISO9660 → *.HD(4B LE size 表) + *.BIN(0x800 扇区)
  SCENE_ID.BIN  = 501 × Squirrel .cnut（本編会話）
  SYSTEM.BIN    = 58 × .cnut（SYSTEM/OVERRIDE、除外）
  SCENEDAT.BIN  = 3523 × TIM2（画像、除外）
解包：scripts/ps2_extract.py（同型引擎 はかれなはーと の解凍器）
VM：scripts/ps2_vm.decode_calls（RIQS/TRAP + 8B 命令 [arg1:u32][op][a0][a2][a3]）

エンジン命令（本作で確認）:
  msgon / dispname / text / ch / r / eol / p / afterpage / er / savepoint
  1 メッセージ枠 = msgon … text …(r text)… eol p afterpage
  ⇒ eol/p が同一クリック境界、r は枠内改行（合并）
  選択肢 = target '*SELx' + text(選択肢) + seladd → select
  主人公名 = exp 'f.name' + embex（文内挿入）
  名札 = name 関数（独立名前窓 MESWINDOW_NAME-WIN.TM2）⇒ 行を出さない
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps2_vm

PROTAGONIST = 'エリカ'          # vndb v4047 / c39901 エリカ・アレーニア（可改名）
FLUSH = ('eol', 'p', 'target', 'label', 'select',
         'msgon', 'afterpage', 'moveinit', 'moveadd', 'move')
SKIP_SCENES = {'characters', 'liketest', 'movetest', 'movetest2', 'setest', 'test', 'start'}


def scene_name(path):
    d = open(path, 'rb').read()
    m = re.search(rb'DataMake/SCENE/([\x20-\x7e]+)', d[:200])
    return m.group(1).decode('cp932', 'replace') if m else os.path.basename(path)


def extract_file(path):
    calls = ps2_vm.decode_calls(open(path, 'rb').read())
    lines, buf = [], []
    stats = {'text': 0, 'orphan': 0}

    def flush():
        if buf:
            line = ''.join(buf)
            # 黒地に「・」だけを敷く装飾枠（同一シーンの演出）は本文でない
            if line.replace('\u3000', '').replace('・', '').strip():
                lines.append(line)
            buf.clear()

    for tag, arg in calls:
        if tag == 'tagname':
            if arg in FLUSH:
                flush()
        elif tag == 'text':
            if not arg:
                continue
            if buf and arg.startswith('\u3000'):
                arg = arg[1:]              # 枠内折り返しの字下げ（全角スペース）
            buf.append(arg)
            stats['text'] += 1
        elif tag == 'exp':
            if arg == 'f.name':
                buf.append(PROTAGONIST)
        elif tag in FLUSH:
            flush()
    if buf:
        stats['orphan'] += 1
        flush()
    return lines, stats


def main():
    src, out = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(src, '*.cnut')))
    all_lines = []
    per = []
    for p in files:
        name = scene_name(p)
        if name[:-4] in SKIP_SCENES if name.endswith('.nut') else name in SKIP_SCENES:
            continue
        try:
            lines, st = extract_file(p)
        except Exception as e:
            print('SKIP(empty stub)', name, e)
            continue
        per.append((name, len(lines)))
        all_lines.extend(lines)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for t in all_lines:
            f.write(t + '\n')
    print('scenes:', len(per), 'lines:', len(all_lines))


if __name__ == '__main__':
    main()
