"""メサイア～パラノイア・パラドックス～（PC 2008 / GsWin「DataPack5」+ Scw5.x）文本提取器。

容器与脚本格式见 `scripts/gspak.py`（PAK 头 0x48 + LZSS 索引；SCW 头 0x3C + LZSS 体，
体＝instr/string/label 三张表 + 三段数据）。

文本单位（L1：记录自定界 ＋ 交叉验证）：
    SCW 的 **string 表**按脚本书写顺序排列，一条消息＝一条串：
      `#F【名前】#F\n本文`（台词；名字与正文在同一条串里，引擎没有独立名字字段）
      纯本文（地の文／游戏内说明）
    交叉验证（均为结构量，不看语感）：
      ① 4,425 条台词串中 4,264 条其后紧跟一条**语音 id 串**（与 VOICE.PAK 条目同名）；
      ② 4,425 条台词串里 4,424 条只有 1 个 `\n`（名字段分隔），仅 1 条含 2 个「」（源文如此）；
      ③ 地の文串 2,497 条中 2,426 条以句读收尾（其余 71 条＝章节标题卡／游戏内说明，逐条人工核对）；
      ④ 引擎类名 `CSsMessage` / `CSsMessageHistory`（回看一条一行）。
    ⇒ 一条串 = 一个 `CSsMessage` = 一次点击 = 一个文本框 = 一行。

取舍（全部按类型字段／结构量，不按内容相似度）：
    · 台词串（`#F【…】#F` 前缀）→ 收，名字印在正文框内 ⇒ 保留并接在同行（`【名前】「…」`）
    · 地の文／说明串（含日文且非标记前缀）→ 收
    · 章节标题卡：位于该脚本 string 表**第 0 条**且为纯 ASCII（`one night satisfaction` 等）→ 收
    · 稿件标记串（以 `■□◆◇※◎★` 或 `①〜⑳` 开头）→ 剔（作者批注，不上屏）
    · 语音 id / 立绘·背景·音效·BGM 名 / label / 脚本名 / 纯 ASCII 资源名 → 剔
    · 整个脚本不收：`Sys*`（系统 UI）、`_BG*`／`_Fog*`／`_Morning`／`_Night`（演出辅助）、
      `AAA`／`AHO`／`Test`（调试）

用法：
    python scripts/messiah_pp_extract.py <Scr.pak> <out.txt> [--graphic ...] [--voice ...] [--se ...] [--bgm ...]
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib.gspak import Pak, Scw

NAME_TAG = re.compile(r'^#F(【[^】]*】)#F\n?')
CTRL = re.compile(r'#[A-Za-z]')
RUBY = re.compile(r'#<[^>]*>')          # ルビ：唆#<そそのか>されて → 唆されて
MARK = re.compile(r'^[①-⑳㉑-㉟■□◆◇※◎★]')
# ★ 稿件批注的少数变体：本身不以标记符开头，但同为作者写给声优/自己的注记，
#   由「同一 string 表内、该注记串后紧跟一条台词、且再前后都是注记串」定位（结构量），
#   逐条人工核对后显式登记（不按内容猜测，只登记这几条实例）。
ANNOT = {
    '汎用苛立ち',                                  # 声优注记：通用「恼火」音效
    '子がBJだった場合（驚き、怒り、残念系？）（プレイヤーが圧倒的に有利な状態）',
}
ASCII_ONLY = re.compile(r'^[\x20-\x7e]*$')
JP = re.compile(r'[^\x00-\x7f]')

# 整个脚本不收（类型判据：脚本名本身即功能分类）
# CardGameMain / CardGameOld：全包无任何 string/label/原始字节引用（孤儿脚本），
#   两者 string 表完全一致且首条为「カードゲーム用テスト」⇒ 旧版测试副本，不上屏。
SKIP_SCRIPT = re.compile(r'^(Sys|_|AAA$|AHO$|Test$|CardGameMain$|CardGameOld$)')


def classify_scripts(pak):
    """返回 (参与脚本列表, 被剔脚本列表)。"""
    keep, drop = [], []
    for name, off, ln in pak.entries:
        (drop if SKIP_SCRIPT.match(name) else keep).append(name)
    return keep, drop


def script_strings(pak, name):
    return Scw(pak.read(name))


def main():
    src, dst = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]

    def opt(flag):
        return args[args.index(flag) + 1] if flag in args else None

    gp = opt('--graphic')
    vp = opt('--voice')
    sp = opt('--se')
    bp = opt('--bgm')
    gnames = {n.upper() for n, o, l in Pak(gp).entries} if gp else set()
    vnames = {n.upper() for n, o, l in Pak(vp).entries} if vp else set()
    snames = {n.upper() for n, o, l in Pak(sp).entries} if sp else set()
    bnames = {n.upper() for n, o, l in Pak(bp).entries} if bp else set()

    pak = Pak(src)
    scrnames = {n.upper() for n, o, l in pak.entries}
    keep, drop_scripts = classify_scripts(pak)

    lines = []
    stats = []
    total_drop = {'voice': 0, 'graphic': 0, 'se': 0, 'bgm': 0, 'label': 0,
                  'mark': 0, 'annot': 0, 'symbol': 0, 'empty': 0}
    total_keep = 0

    for fname in keep:
        try:
            scw = script_strings(pak, fname)
        except Exception as e:
            print('FAIL %s %s' % (fname, e))
            continue
        labels = {x.upper() for x in scw.labels}
        kept = 0
        drop = dict.fromkeys(total_drop, 0)
        for idx, raw in enumerate(scw.strings):
            t = raw.strip()
            if not t:
                drop['empty'] += 1
                continue
            u = t.upper()
            # —— 剔：语音 id 串（与 VOICE.PAK 条目同名）
            if u in vnames:
                drop['voice'] += 1
                continue
            # —— 剔：图像／音效／BGM 资源名
            if u in gnames:
                drop['graphic'] += 1
                continue
            if u in snames:
                drop['se'] += 1
                continue
            if u in bnames:
                drop['bgm'] += 1
                continue
            # —— 剔：label / 脚本名（控制跳转用）
            if u in labels or u in scrnames:
                drop['label'] += 1
                continue
            # —— 剔：稿件标记（作者批注，不上屏）
            if MARK.match(t):
                drop['mark'] += 1
                continue
            # —— 剔：无标记符的批注变体（已人工核对，登记实例）
            if t in ANNOT:
                drop['annot'] += 1
                continue
            if ASCII_ONLY.match(t):
                # 纯 ASCII：绝大多数是命令名／资源名（`FSA06a`／`MUS002`／`OBBG`）。
                # 唯一例外＝该脚本 string 表第 0 条的**章节标题卡**。
                if idx == 0 and u not in labels and u not in scrnames:
                    lines.append(t.replace('\n', ''))
                    kept += 1
                else:
                    drop['symbol'] += 1
                continue
            # —— 收：台词串（名字印在正文框内 ⇒ 保留并接同行）
            m = NAME_TAG.match(t)
            if m:
                body = RUBY.sub('', CTRL.sub('', t[m.end():]))
                lines.append(m.group(1) + body.replace('\n', ''))
            else:
                # —— 收：地の文／游戏内说明
                body = RUBY.sub('', CTRL.sub('', t))
                lines.append(body.replace('\n', ''))
            kept += 1
        for k in total_drop:
            total_drop[k] += drop[k]
        total_keep += kept
        stats.append((fname, kept, drop, len(scw.strings)))

    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(lines) + '\n')

    for n, k, d, tot in stats:
        print('%-18s 收 %-5d / 串 %-5d 剔 %s' % (n, k, tot, d))
    print('参与脚本 %d（剔脚本 %d 个: %s）' % (len(keep), len(drop_scripts), ' '.join(drop_scripts[:8])))
    print('收 %d 行；剔 %s' % (total_keep, total_drop))
    print('TOTAL lines=%d bytes=%d chars=%d'
          % (len(lines), os.path.getsize(dst), sum(len(x) for x in lines)))


if __name__ == '__main__':
    main()
