"""メサイア（PC / GsWin「DataPack5」+ Scw5.x 脚本）文本提取器。

容器与脚本格式见 `scripts/gspak.py`（PAK 头 0x48 + LZSS 索引；SCW 头 0x3C + LZSS 体，
体＝instr/string/label 三张表 + 三段数据）。

文本单位（L1：记录自定界＋交叉验证）：
    SCW 的 **string 表**按脚本书写顺序排列，一条消息＝一条串：
      `#F【名前】#F\\n本文`（台词，`#F` 是字色/字体切换码）
      纯本文（地の文）
    交叉验证：每条台词串后面紧跟一条**语音 id 串**（13,553 对，与 VOICE.PAK 名字对应）；
    39,034 条消息串里 39,033 条只有 1 行、无一条含 2 个以上「」。
    ⇒ 一条串 = 一个 `CSsMessage`（引擎类名 `CSsMessage` / `CSsMessageHistory`）= 一次点击 = 一行。

不收（按类型排除，不做内容取舍）：
    · 语音 id 串（`AADD01_000000` 形态，或名字出现在 VOICE.PAK）
    · 图像名（出现在 GRAPHIC.PAK 的 `EV037` 等）
    · `====…` 整行分隔标记
    · SCW label 表里出现过的名字（`START` / `ROOT01` …）
    · 以 ①〜⑳ / ■◆◇ 开头的稿件小节标记（`③フルコンプ後のエクストラモード`、`■■煌　追加台詞`）

用法：
    python scripts/messiah_extract.py <SCR.PAK> <out.txt> [--graphic GRAPHIC.PAK] [--voice VOICE.PAK]
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _lib.gspak import Pak, Scw

NAME_TAG = re.compile(r'^#F(【[^】]*】)#F\n?')
CTRL = re.compile(r'#[A-Za-z]')
RUBY = re.compile(r'#<[^>]*>')      # ルビ：傀#<かい>儡 → 傀儡
VOICE_ID = re.compile(r'^[A-Z]{1,3}[A-Z0-9]*_\d{6}$')
EV_NAME = re.compile(r'^EV\d{3}(_[a-z0-9]+)?$')
EQ_RUN = re.compile(r'^=+$')
CMD_WORDS = {'RESET', 'START', 'EXIT', 'END', 'STOP'}
SECTION = re.compile(r'^[①-⑳㉑-㉟■□◆◇※]')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    gp = args[args.index('--graphic') + 1] if '--graphic' in args else None
    vp = args[args.index('--voice') + 1] if '--voice' in args else None
    gnames = set(n for n, o, l in Pak(gp).entries) if gp else set()
    vnames = set(n for n, o, l in Pak(vp).entries) if vp else set()

    pak = Pak(src)
    scr_names = set(n for n, o, l in pak.entries)
    lines = []
    stats = []
    for fname, off, ln in pak.entries:
        # 系统 UI（Sys*）／演出辅助（_BG*、_Fog*、_Morning…）／调试脚本（TEST、AHO、AAA）
        if fname.startswith(('Sys', 'SYS', '_')) or fname in ('TEST', 'AHO', 'AAA'):
            stats.append((fname, 0, {'file': 1}))
            continue
        try:
            scw = Scw(pak.read(fname))
        except Exception as e:
            print('FAIL %s %s' % (fname, e))
            continue
        labels = set(scw.labels)
        kept = 0
        drop = {'voice': 0, 'graphic': 0, 'eq': 0, 'label': 0, 'section': 0, 'symbol': 0}
        for idx, raw in enumerate(scw.strings):
            t = raw.strip()
            if not t:
                continue
            if VOICE_ID.match(t) or t in vnames:
                drop['voice'] += 1
                continue
            if t in gnames or EV_NAME.match(t):
                drop['graphic'] += 1
                continue
            if EQ_RUN.match(t):
                drop['eq'] += 1
                continue
            if t in labels:
                drop['label'] += 1
                continue
            if SECTION.match(t):
                drop['section'] += 1
                continue
            if all(ord(c) < 0x80 for c in t):
                # 纯 ASCII：本作里绝大多数是命令名/资源名（`SysReset`/`FSA04a`/`nse004a`）。
                # 唯一的例外是**每条脚本的第 0 条串**——ED／章节标题卡（`ENDLESS SNOW` 等，实测 9 处全在 idx=0）
                # 标题卡：idx==0 且不是「脚本名 / Sys 命令 / label / 纯命令词」
                if (idx == 0 and t not in scw.labels and t not in scr_names
                        and not t.startswith(('Sys', '_')) and t not in CMD_WORDS):
                    lines.append(t.replace('\n', ''))
                    kept += 1
                else:
                    drop['symbol'] += 1
                continue
            m = NAME_TAG.match(t)
            if m:
                body = t[m.end():]
                body = RUBY.sub('', CTRL.sub('', body))
                lines.append(m.group(1) + body.replace('\n', ''))
            else:
                lines.append(RUBY.sub('', CTRL.sub('', t)).replace('\n', ''))
            kept += 1
        stats.append((fname, kept, dict(drop)))
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(lines) + '\n')
    for n, k, d in stats:
        print('%-10s 收 %-5d 剔 %s' % (n, k, d))
    print('TOTAL lines=%d bytes=%d chars=%d'
          % (len(lines), os.path.getsize(dst), sum(len(x) for x in lines)))


if __name__ == '__main__':
    main()
