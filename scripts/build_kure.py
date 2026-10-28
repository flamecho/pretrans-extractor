# -*- coding: utf-8 -*-
"""クレプシドラ 成品构建：scenario(ARC2) -> LZSS -> 正文成行

规则
  · 一行＝一次点击（本引擎每条消息行独立等待点击；无「不清框等待」指令 ⇒ 单版）
  · 名札内嵌在正文行首（`名前「…」` / `名前（…）`）⇒ 按行首名表剥除，不加说话人前缀
  · 富文本/指令标签成行前剥净；<RUBY TEXT="本字" RUBY="よみ"> 只留本字
  · <SELECT TEXT="…"> ＝ 选项，取 TEXT
  · `;` 开头＝作者注释/死代码，整行丢弃
  · 排除：系统・UI・回想/相册列表・调试・存档/表情/画像名单・小游戏二进制・staff roll
"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clep_lzss as lz

SRC = os.path.join(VNTRANS_HOME, '_work_kure/[PC-JP]クレプシドラ～光と影の十字架～（硬盘版）/scenario')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]クレプシドラ～光と影の十字架～（硬盘版）.txt')

# 行首名表（本作全部说话人前缀，人工核对过；`;` 开头的注释行不进此表）
NAMES = [
    'イヴ', 'イヴリン', 'デヴィン', 'カテキスタ', 'アルジェン', 'チェンバレン',
    '水先圭二', '水先', 'ディス', 'バロ', 'クルス', '霧下香', '霧島香', '少女',
    'アダム', 'ユディト', '小泉友美', '長瀬拓己', 'ヴァンギオ', 'グレム',
    '大河内部長', '浦辺課長', '駅員', '駅の少女', 'てんたま', 'でびたま',
    '中年男', '謎の浮遊物体', 'やさしそうな声', 'こわそうな声', '男の人の声',
    '穏やかな声', '声', 'アル様と呼ばれた人', 'クルスと呼ばれた少年',
    'チェンバレンと呼ばれたおじさま', 'ゾンビＡ', 'ゾンビＢ？',
]
NAMES.sort(key=len, reverse=True)

INCLUDE = [
    r'^審判表情リスト\.adv$',          # シーン01 十字架の丘 プロローグ
    r'^A-本編\d+\.adv$',
    r'^logo2\.adv$',                   # 実体は アダム・タイムテーブル 青の回廊
    r'^uninit\.adv$',                  # 実体は シーン16 審判の鐘前
    r'^T-.*\.adv$',
    r'^T\d{4}-.*\.adv$',
    r'^T(?:AL|BA|CA|CH|CR|DE|DI|KA|KK|MI|MS|MU|RO)-.*\.adv$',
    r'^X-KEY.*\.adv$',
    r'^Z-END2?-.*\.adv$',
]
EXCLUDE_NAME = [r'旧ED']    # 明示「こっちは使わない」的死代码

RUBY = re.compile(r'<RUBY\s+TEXT="([^"]*)"[^>]*>')
SELECT = re.compile(r'<SELECT\s+TEXT="([^"]*)"[^>]*>')
TAG = re.compile(r'<[^>"]*(?:"[^"]*"[^>"]*)*>')
NAME_HEAD = re.compile(r'^(' + '|'.join(map(re.escape, NAMES)) + r')\s*(?=[「（])')


def wanted(name):
    if any(re.search(p, name) for p in EXCLUDE_NAME):
        return False
    return any(re.search(p, name) for p in INCLUDE)


def cut_comment(s):
    """`;` 在本引擎＝注释/演出注记（引擎不显示）⇒ 引号外遇到 `;` 即切"""
    depth = 0
    for i, ch in enumerate(s):
        if ch == '「':
            depth += 1
        elif ch == '」':
            depth = max(0, depth - 1)
        elif ch == ';' and depth == 0:
            return s[:i]
    return s


def clean_line(raw_line):
    """返回成行文本；空串＝丢弃"""
    s = raw_line.strip()
    if not s:
        return ''
    if s.lstrip().startswith(';'):
        return ''
    keep = None
    m = SELECT.search(s)
    if m:
        keep = m.group(1)
    s = RUBY.sub(r'\1', s)
    s = TAG.sub('', s)
    s = cut_comment(s).strip()
    if keep is not None and not s:
        s = keep
    if not s or s.lstrip().startswith(';'):
        return ''
    s = NAME_HEAD.sub('', s, count=1).strip()
    return s


def build():
    recs = lz.parse_arc2(open(SRC, 'rb').read())
    inv = bytes(b ^ 0xFF for b in open(SRC, 'rb').read())
    lines, order = [], []
    for i, (name, off, us) in enumerate(recs):
        if not wanted(name):
            continue
        end = recs[i+1][1] if i+1 < len(recs) else os.path.getsize(SRC)
        text = lz.lzss_decompress(inv[off:end]).decode('cp932')
        n0 = len(lines)
        for raw_line in re.split(r'\r\n|\n', text):
            t = clean_line(raw_line)
            if t:
                lines.append(t)
        order.append((name, len(lines) - n0))
    return lines, order


if __name__ == '__main__':
    lines, order = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('文件 %d 个，成行 %d' % (len(order), len(lines)))
    for n, c in order:
        print('  %-44s %5d' % (n, c))
