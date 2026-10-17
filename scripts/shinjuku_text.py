# -*- coding: utf-8 -*-
"""
新宿羅生門 ―Rashomon of Shinjuku― (Switch / Idea Factory・ALTERGEAR, 開発:花梨エンターテイメント)
全文本提取器 —— 脚本为 SJIS 纯文本 @命令格式 (romfs/script/**/*.txt)，另有 fixeddata/Word.json 用語辞典。

链路：
  XCI --nstool--> NCA(Program) --part1--> RomFS --本脚本--> 正文 ＋ 选项 ＋ 用語辞典

成行规则（skill §0）：
  * @text("speaker","body")  -> 取 body（不加说话人前缀；本引擎 @text 即一个文本框，后随 @click()）
  * @select_text(n,"opt")    -> 选项，一行一条，保持出现顺序
  * 行内软换行 `\n` 合并
  * 注音 `|基底語|よみ|` -> 还原为基底语（上屏显示基底语）
  * 用語辞典 (Word.json)     -> `【見出し語】解説文`，一行一条、不带读音、条内换行合并，并入末尾

排除（判据＝是否正文上屏）：
  * 006/s11..s16 与 ExtraStory/s11..s19 —— 开发 QA 脚本（拡張子/3Dカメラ/カットイン/ステータス 確認用）
  * SubStory / ExtraStory 中的「テストシナリオ」占位脚本（逐文件检测，含测试标记则整体剔除）
  * battle/qdata.json（战斗问答）、fixeddata/*.json（系统数据）、system/bin/str_ja.bin（UI 串）、
    ui/80_manual（图片手册）—— 非正文/系统 UI

用法：
  python scripts/shinjuku_text.py [romfs脚本目录] [输出txt]
"""
import re
import sys
import os
import io
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROMFS = os.path.join(ROOT, '_work_shinjuku', 'romfs')
SRC = os.path.join(ROMFS, 'script')
OUT = os.path.join(ROOT, '提取结果', '新宿羅生門_全文本.txt')
if len(sys.argv) > 1:
    SRC = sys.argv[1]
    ROMFS = os.path.dirname(SRC)
if len(sys.argv) > 2:
    OUT = sys.argv[2]

MAIN = ['001', '002', '003', '004', '005', '006']
SUB = ['SubStory/%03d' % i for i in range(1, 7)]
ORDER = MAIN + SUB + ['ExtraStory']

# 显式排除（按名）：开发 QA 脚本
EXCLUDE_FILES = set(['006/s%d.txt' % n for n in range(11, 17)]) | \
                set(['ExtraStory/s%d.txt' % n for n in (11, 12, 14, 15, 16, 17, 19)])

# 「テストシナリオ」占位标记（仅用于 SubStory/ExtraStory；命中即整个文件剔除）
STUB_MARK = re.compile(
    r'テストシナリオ|テストを終わり|テストを終わ|エクストラト?(ストーリー|シナリオ)|'
    r'確認用シナリオ|テストを行います')

LIT = r'"((?:[^"\\]|\\.)*)"'
TOK_RE = re.compile(r'@(text|select_text)\s*\(\s*' + LIT + r'\s*,\s*' + LIT + r'\s*\)')
RUBY_RE = re.compile(r'\|([^|]*)\|([^|]*)\|')

# 战斗系统横幅（【決闘】/【同志戦】… 対 …）—— 属战斗模块 UI（ui/40_novel/05_battle_encount），非正文
BATTLE_BANNER = re.compile(r'^【(決闘|同志戦)】')

# 源笔误逐行定值复元表（仅此 3 行；源为全角「（」配半角「)」，改为全角「）」以配平）
REPAIRS = {
    '（聖舟さんと話そうかな……)': '（聖舟さんと話そうかな……）',
    '（高杉、なのか……？)': '（高杉、なのか……？）',
    '（蒼空。どうか、無事でいてくれ。)': '（蒼空。どうか、無事でいてくれ。）',
}


def unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            if n == 'n':
                pass
            elif n == '"':
                out.append('"')
            elif n == '\\':
                out.append('\\')
            else:
                out.append(n)
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def clean(body):
    s = RUBY_RE.sub(r'\1', unescape(body))
    return s.replace('\r', '').replace('\n', '').strip()


def collect_file(path):
    raw = open(path, 'rb').read().decode('cp932', 'replace')
    out = []
    for m in TOK_RE.finditer(raw):
        t = clean(m.group(3))
        if not t or BATTLE_BANNER.match(t):
            continue
        out.append(REPAIRS.get(t, t))
    return out


def main():
    lines = []
    log = []
    for d in ORDER:
        dp = os.path.join(SRC, d.replace('/', os.sep))
        if not os.path.isdir(dp):
            continue
        for root, dirs, files in os.walk(dp):
            for fn in sorted(files, key=lambda x: (len(x), x)):
                if not fn.endswith('.txt'):
                    continue
                rel = os.path.relpath(os.path.join(root, fn), SRC).replace(os.sep, '/')
                if rel in EXCLUDE_FILES:
                    log.append((rel, 'DEV', 0))
                    continue
                if d.split('/')[0] in ('SubStory', 'ExtraStory'):
                    probe = open(os.path.join(root, fn), 'rb').read().decode('cp932', 'replace')
                    if STUB_MARK.search(probe):
                        log.append((rel, 'STUB', 0))
                        continue
                got = collect_file(os.path.join(root, fn))
                if got:
                    lines.extend(got)
                log.append((rel, 'ok', len(got)))

    # 用語辞典（Word.json）并入末尾
    wp = os.path.join(ROMFS, 'fixeddata', 'Word.json')
    gloss_n = 0
    if os.path.exists(wp):
        w = json.loads(open(wp, 'rb').read().decode('utf-8-sig'))['Word']
        for e in w:
            desc = clean(e.get('Description', ''))
            if not desc:
                continue
            lines.append('【%s】%s' % (e.get('Word', ''), desc))
            gloss_n += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    print('output :', OUT)
    print('lines  :', len(lines), ' (glossary:', gloss_n, ')')
    print('--- per file ---')
    for rel, st, n in log:
        print(f'  {st:4s} {n:6d}  {rel}')


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()
