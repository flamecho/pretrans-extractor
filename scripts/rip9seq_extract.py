#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]9 R.I.P. sequel —— STCM2L(UTF-8) 文本提取。

【2026-10-28 实证结构】（本体《9 R.I.P.》的同族引擎，但**指令编号完全不同**）
容器：XCZ→XCI→Program NCA(keygen20/slot2)→RomFS→CONTENTS/STORY.cpk（CRI CPK/CRILAYLA）→ SCRIPT/*.DAT
脚本头：`STCM2L Apr 12 2018 18:22:39`（与 9 R.I.P. / 十鬼の絆 同一份运行时）
  · 指令头 16B：`[op][kind][seq][0x10]`，紧跟操作数
  · 字符串对象：`[0][cnt][1][cnt*4][UTF-8 文本 + NUL 补足]`
  · **两种操作数形态**：
      A) 内联：指令头 + 字符串对象
      B) 引用：指令头 + `[0][1][1][4]` + 引用块 + 字符串对象（指令头与字符串之间隔着引用块）
  · 断框（L0）：记录结束后 16B 内出现 `0x1F4`（wait＝点击）⇒ 一次点击一框；
    没有 `0x1F4` 的是框内换行 ⇒ 合并。
分派（本作实测）：
  · 主消息窗正文 = op 0x145（75,031 条）＋ 一族的引用形态 op（0x181/0x184/0x185/0x187/0x188/0x189/0x18a/0x18b …）
    ⇒ **不按 op 白名单**，改按「内容形态」判：以 「（『【 开头，或含句读且够长。
  · 名札窗 / 资源名 / 旗标：`戸田 和真` `逸色　絢芽` `紅華_天12` `bg_02a` `好感度_紅華` `色変化判定` —— 无句读、短，按形态剔除。
  · 章题卡：op 0x17c（`紅華　天編　其ノ拾` / `響　終幕　深`）、0x17d（`序章`）⇒ 单列成行。
默认名：`SCRIPT/init/0_init.DAT` 里唯一有意义的日文串常量（`珠沙`）＝ `default_name_set` 的参数。
用法: python scripts/rip9seq_extract.py [--out 提取结果/x.txt] [--dump]
"""
import argparse
import collections
import os
import re
import struct

SRC = '_w_rq2/story/SCRIPT'
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
RE_COLOR = re.compile(r'#(?:Color|Scale|Speed|Fade|PosX|PosY|Wait)\[[^\]]*\]')
RE_RUBY = re.compile(r'#Ruby\[([^,\]]*),([^\]]*)\]')
RE_NAMEVAR = re.compile(r'#Name\[\d+\]')
WAIT = b'\xf4\x01\x00\x00'
WAIT_ARG0 = b'\xf4\x01\x00\x00\x00\x00\x00\x00'   # wait 指令：op 0x1F4 + 零参数
SWITCH = b'switch\x00'   # 分支指令串（见 walk ⑥bis）
HEROINE = '珠沙'          # 读取自 init/0_init.DAT（下方 verify_default_name 复核）
OP_CHAP = {0x17c, 0x17d}
# 名字窗指令族（实测名字形占比 0.6~0.98）：`悪魔` `聖ヤ` `逸色 珠沙` `天堂 紅華`
# ⚠ 只收「名字形占比 ≥0.85 且几乎不出台词」的：0x181/0x18b 虽是名字窗，但同一 op 也排正文片段
#   （`珠沙さんをここまで` 这类 9 字纯假名会被误当名字窗），那两条用「带 tag / 姓＋空格＋名」判据覆盖。
OP_NAME = {0x17e, 0x17f, 0x180, 0x182, 0x183}
# UI/旗标（永不显示为正文）：`色変化判定` `共通ルート` `マップ追加出現` `おまけ９解放` `閲覧設定` …
OP_UI = {0x35, 0x36, 0x37, 0x132, 0x15e, 0x16d, 0x19d}
RE_MAP_PROMPT = re.compile(r'^どこに行こうかな[？?]?$')
RE_CHAP = re.compile(r'(天編|神編|終幕|^序章$)')
# 名札/资源/旗标形态：无句读、无引号、短
RE_RESID = re.compile(r'^(?:bg|fg|b-|enbg|sure|select|switch|ED|ed)[-_A-Za-z0-9]*')


def clean(s):
    s = RE_RUBY.sub(lambda m: m.group(1), s)
    s = RE_NAMEVAR.sub(HEROINE, s)
    s = RE_COLOR.sub('', s)
    return s.strip().lstrip('　')


def bare(s):
    s = RE_RUBY.sub(lambda m: m.group(1), s)
    s = RE_COLOR.sub('', s)
    return s.strip()


def is_text_shape(t):
    """引用形态（op≠0x145）里「是不是正文」的判据。

    op 0x145 是主消息窗，**不加形态过滤**（框内换行片段如 `元の空間に戻ってから` 没有句读，滤掉就丢正文）。
    引用形态的 op 一族（0x181/0x184/0x185/0x187/0x188/0x189/0x18a/0x18b …）混着名札与资源名，只能按形态分：
      · 以 「（『【 开头 ⇒ 台词
      · 含 。！？… 且 ≥8 字、且不是资源名/带 #Name#Color 的名字窗 ⇒ 正文片段
    """
    b = bare(t)
    if not b:
        return False
    if RE_RESID.match(b) or '_' in b:
        return False                      # `bg_02a` `紅華_天12` `好感度_紅華`
    if b[0] in '「（『【':
        return True
    if is_name_window(t):
        return False                      # 名字窗（`逸色 #Name[1]` 这类短标签）
    return len(b) >= 8 and bool(re.search(r'[。！？…]', b))


NAME_ONLY = re.compile(r'^[\u3040-\u30ff\u4e00-\u9fff\u30fc\s　]{1,12}$')


def is_name_window(t):
    """名字窗：带 #Color/#Name 且**很短**（`逸色 #Name[1]` `逸色 #Name[1]？` `#Color[0]天堂 #Color[13]紅#Color[0]華`）。

    ⚠ 不能只看「含 #Name」：台词里也会内联 `#Name[1]を心配しているのか？」`，那是正文。
    """
    if '#Name' not in t and '#Color' not in t:
        return False
    b = clean(t)          # 先把 #Name[1] 代入默认名，否则 `逸色 #Name[1]` 会比 `逸色 珠沙` 长、判不出名字窗
    if len(b) > 10 or re.search(r'[、。…」』]', b):
        return False
    # 名字窗都带空格（`逸色 絢芽` `天堂 紅華`）或极短（`紅華`）；
    # 而带颜色的**台词片段**（`#Color[2]一生感謝してね？`，8 字、无空格）不是名字窗
    return (' ' in b or '\u3000' in b) or len(b) <= 6


RE_NAMESHAPE = re.compile(r'^[\u3040-\u30ff\u4e00-\u9fff\u3005\u30fc\u3000 ]{1,10}$')
# 框内名字行（台本演出）：`朱里` / `スサク` / `空蘭` —— 独立一条、同框、紧接 `「台词」`。
# ⚠ 必须**不含平假名**：`まるでそれは`+`「さあ…」`、`いつもなら`+`『…』` 是正文接台词（实测 3 处）。
RE_INLINE_NAME = re.compile(r'^[\u30a0-\u30ff\u4e00-\u9fff\u3005\u30fc]{1,6}$')
RE_BARE_NAME = re.compile(r'^[\u4e00-\u9fff\u3005]{1,6}[ \u3000][\u4e00-\u9fff\u3005]{1,6}$')


def is_bare_name(t):
    """没有样式标签的名字窗：`逸色 珠沙` `天堂 紅華` `月神 優衣`（姓＋空格＋名，全汉字）。

    ⚠ 框内换行的片段不会有「汉字＋空格＋汉字」这种形态（`　あのネックレスがないと` 带假名，
      `私の人生、その全てを` 带标点）⇒ 用它把「排在框中间的名札」挑出来。
    """
    b = clean(t)
    return bool(RE_BARE_NAME.fullmatch(b))


def is_inline_name(d, recs, k):
    """框内名字行：与下一条**同 op、同框（无点击）**，且下一条以 `「`/`『` 起，本条形如短人名。

    实测只有 S＝ＣＲＯＷＮ 三人（`朱里`×10 `スサク`×10 `空蘭`×8 `魅ナミ`×1，803.DAT 0x93a69 一带）。
    同段的**台本版**写作 `朱里：みんな、こんばんは！`（名字＋冒号＋台词在同一个串）⇒ 那是正文，不能动；
    对话版才把名字拆成独立记录 ⇒ 名字属名札，剔除后只留台词。
    """
    b = bare(recs[k][3])
    if not RE_INLINE_NAME.fullmatch(b) or k + 1 >= len(recs):
        return False
    off, end, op, _ = recs[k]
    nx = recs[k + 1]
    if nx[2] != op or WAIT in d[end:end + 16] or WAIT_ARG0 in d[end:nx[0]]:
        return False
    return bare(nx[3]).startswith(('「', '『'))


def is_place_tag(d, recs, k):
    """地点/词条标签：`【ユニュオン】` `【きさらぎエリア】` —— 屏幕上单独显示的地名，不是正文。

    判据＝形如 `【…】` 短词条 + 与下一条**同框（无点击/无分支）** + **下一条以 `（` 开头**（心声紧接标签）。
    实测 2 处：451.DAT @0xa72d0（op 0x19b）、553.DAT @0xb17c1（op 0x193）。
    ⚠ 只按形态会误杀正文里的强调括号：`【わかりました】` `【ＴＨＥ　幽霊】` `【存在力】`
      `【ソイツの夢に入るのが先だな】`（同框候选 16 处，其余 14 处下一条都不是 `（`）。
    """
    if not RE_SUBTITLE.fullmatch(bare(recs[k][3])) or k + 1 >= len(recs):
        return False
    end = recs[k][1]
    nx = recs[k + 1]
    if WAIT in d[end:end + 16] or WAIT_ARG0 in d[end:nx[0]] or SWITCH in d[end:nx[0]]:
        return False
    return bare(nx[3]).startswith('（')


def is_name_like(t):
    """名札：纯日文短串（`戸田 和真`），或带 #Color/#Name 且不是台词（`逸色 #Name[1]`）。"""
    b = bare(t)
    if not b:
        return True
    if NAME_ONLY.fullmatch(b):
        return True
    if ('#Name' in t or '#Color' in t) and b[:1] not in '「（『':
        return bool(NAME_ONLY.fullmatch(b)) or len(b) <= 12
    return False


RE_FLAGID = re.compile(r'[A-Za-z0-9_\-]+通過')
# 名字窗「肩書き」行：`俺` / `【ウラ七不思議】` 同 op 连续两条（名前＋肩書き），
# 或紧贴名字窗指令（0x182 `天堂 紅華`）。内部无句读，与正文里的 `【……僕たちは、幸せ者】` 区分。
RE_SUBTITLE = re.compile(r'^【[^【】。、…！？]{1,14}】$')
RE_LATIN_ONLY = re.compile(r'^[A-Za-z0-9_\-\.\s]+$')


def is_id(t):
    """分支旗标 / 资源名（`ten-minami11-8通過` `ED紅華_神` `sure4` `bg_02a` `好感度_紅華`）。

    ⚠ 框内续行的判断也要先过这一关：旗标就排在选项后面（`switch` 的键），
      当年就是它被当成续行粘进了正文（`…重なるten-minami11-8通過（…`）。
    """
    b = bare(t)
    if not b:
        return False
    if '_' in b or RE_FLAGID.fullmatch(b):
        return True
    if RE_RESID.match(b):
        return True
    return bool(RE_LATIN_ONLY.fullmatch(b)) and bool(re.search(r'[A-Za-z]', b))


def is_subtitle(d, recs, k):
    """名字窗第二行「肩書き」（`【ウラ七不思議】`），不是正文。

    实测两处：200.DAT @0xb6200 `0x196 俺` + `0x196 【ウラ七不思議】`（名前＋肩書き）；
             159.DAT @0x94090 `0x185 【ウラ七不思議】` + `0x182 天堂 紅華`。
    L0 判据：**与前后记录之间都没有 0x1F4（点击）**⇒ 和名字窗同框，是窗内的第二行。
    ⚠ 不能只看形态：独立 `【…】` 全源 64 处，其余都是正文（`【はい】` `【星絆　５才】`），
      那些与相邻记录之间都有点击。
    """
    if not RE_SUBTITLE.fullmatch(bare(recs[k][3])) or k == 0:
        return False
    off, end = recs[k][0], recs[k][1]
    if WAIT in d[recs[k - 1][1]:off]:
        return False
    if not (k + 1 < len(recs) and WAIT not in d[end:recs[k + 1][0]]):
        return False
    # 必须与名字窗成对：邻条是名字窗指令（0x182 `天堂 紅華`），或同 op 的短名字（`俺`）
    p, op = recs[k - 1], recs[k][2]
    if (k + 1 < len(recs) and recs[k + 1][2] in OP_NAME) or p[2] in OP_NAME:
        return True
    return p[2] == op and len(clean(p[3])) <= 6 and bool(RE_NAMESHAPE.fullmatch(clean(p[3]) or ''))


def load(d):
    """返回 [(off, end, op, text)]：指令头(可选) + 字符串对象。"""
    n = len(d)
    out = []
    i = 0
    while i + 16 <= n:
        z, c, one, bl = struct.unpack_from('<IIII', d, i)
        if z == 0 and one == 1 and 1 <= c <= 0x800 and bl == c * 4 and i + 16 + bl <= n:
            try:
                t = d[i + 16:i + 16 + bl].decode('utf-8').rstrip('\x00')
            except UnicodeDecodeError:
                t = None
            # 只有标点的记录（`「` `」` `！？` 单独成串）也是正文的一部分，不能因为是标点就丢
            if t and (JP.search(t) or re.search(r'[「」『』、。！？…―]', t)) and not any(ord(ch) < 0x20 for ch in t):
                out.append((i, i + 16 + bl, prefix_op(d, i), t))
            i += 16 + bl
            continue
        i += 4
    return out


def prefix_op(d, i):
    """指令头：紧邻前 16B；否则（引用形态）往回找最近的合法指令头。"""
    if i >= 16:
        a, b, c, e = struct.unpack_from('<IIII', d, i - 16)
        if e == 0x10 and 0x20 <= a <= 0x800:
            return a
    for back in range(20, 0x140, 4):
        j = i - back
        if j < 0:
            break
        a, b, c, e = struct.unpack_from('<IIII', d, j)
        if e == 0x10 and 0x20 <= a <= 0x800 and 0x14 <= c < 0x200000:
            return a
    return None


def verify_default_name(path):
    """init/0_init.DAT 里唯一有意义的日文串常量 = 默认名（其余是 `色変化判定` 之类旗标）。"""
    d = open(path, 'rb').read()
    cand = []
    for off, end, op, t in load(d):
        b = bare(t)
        if b != '色変化判定' and re.fullmatch(r'[\u3040-\u30ff\u4e00-\u9fff\u30fc]{2,8}', b or ''):
            cand.append(b)
    return cand


def files_of(root):
    out = []
    for f in sorted(os.listdir(root)):
        p = os.path.join(root, f)
        if f.upper().endswith('.DAT') and f[0].isdigit():
            out.append(p)
    out.sort(key=lambda p: int(os.path.basename(p).split('.')[0]))
    return out


def walk(files, dump=False):
    lines = []
    stats = collections.Counter()
    for p in files:
        d = open(p, 'rb').read()
        recs = load(d)
        cur = []

        def flush():
            nonlocal cur
            if cur:
                lines.append(''.join(cur))
            cur = []

        for k, (off, end, op, t) in enumerate(recs):
            # ⓪ 分支指令（L0）：`switch` 串对象夹在两段之间 ⇒ 程序在此重新起框，必须断。
            #    ⚠ 它是纯 ASCII，被 load 的「只要日文/标点」过滤掉、看不见，
            #      于是 `（独白）` 与 `それに、…` 粘成一行（457.DAT @0x98008）。
            if k and cur and SWITCH in d[recs[k - 1][1]:off]:
                flush()
                stats['switch_break'] += 1
            # ①-0 名字窗的肩書き行（`【ウラ七不思議】`）：UI，不是正文
            if is_subtitle(d, recs, k):
                stats['subtitle'] += 1
                continue
            # ①-0c 地点/词条标签（`【ユニュオン】` + `（心声）`）：屏幕地名，不是正文
            if is_place_tag(d, recs, k):
                if cur:
                    flush()
                stats['place_tag'] += 1
                continue
            # ①-0b 框内名字行（`朱里` + `「台词」`）：名札，剔除后台词单独成行
            if is_inline_name(d, recs, k):
                if cur:
                    flush()
                stats['inline_name'] += 1
                continue
            # ① UI / 地图菜单 / 旗标：不是正文（`どこに行こうかな？` `九十九神社` `色変化判定` `おまけ９解放`）
            if op in OP_UI or (op != 0x145 and RE_MAP_PROMPT.match(bare(t))):
                stats['ui'] += 1
                continue
            # ② 选项：单列（后面紧跟 `xxx通過` 的 switch 键）
            if op == 0x133:
                flush()
                lines.append(clean(t))
                stats['opt'] += 1
                continue
            # ③ 章题卡：单列
            if op in OP_CHAP and RE_CHAP.search(bare(t)):
                flush()
                lines.append(bare(t))
                stats['chap'] += 1
                continue
            prev_op = recs[k - 1][2] if k else None
            next_op = recs[k + 1][2] if k + 1 < len(recs) else None
            # ④ ★★ 名札判据之三：**op 与前后都不相同**（孤立的指令）且形态是短日文
            #    `（心声）`0x145 → `悪魔`0x180 → `「台词」`0x145 ⇒ 0x180 孤立，是名字窗；
            #    而框内换行片段与相邻段同 op（`水鏡星絆と逸色珠沙の` 前后都是 0x17f）⇒ 是正文
            lone_name = (op != prev_op and op != next_op
                         and bool(RE_NAMESHAPE.fullmatch(clean(t) or '')))
            # ⑤ 是不是正文
            if op == 0x145:
                is_text = True
            elif lone_name or is_id(t) or is_name_window(t) or is_bare_name(t):
                is_text = is_text_shape(t)
            elif cur:
                is_text = True                      # 同指令且在框内 ⇒ 框内换行片段
            else:
                is_text = is_text_shape(t)
            if not is_text:
                stats['drop'] += 1
                if cur and (lone_name or is_name_window(t) or is_bare_name(t)):
                    flush()                         # 换了说话人
                    stats['name_break'] += 1
                continue
            c = clean(t)
            # ⑥bis 完整的括号独白另起一框：`…感情をぶつけたり……` + `（危害を加えるようなものではありません）`
            #      两条同框（无点击/无分支），字节上无从区分；但括号**自身闭合**＝L1 记录自定界，
            #      且本框括号已配平 ⇒ 是「叙述 + 独立心声」两段。全源仅 2 处正文命中（807.DAT / 152.DAT）。
            #      ⚠ 排除地名/词条标签 `【ユニュオン】（…）` 与台本名字 `空蘭：（…）`（前段以】/：收尾）。
            if (cur and c.startswith('（') and c.endswith('）')
                    and c.count('（') == c.count('）')
                    and ''.join(cur).count('（') == ''.join(cur).count('）')
                    and not ''.join(cur).rstrip().endswith(('】', '：'))):
                flush()
                stats['paren_split'] += 1
            # ⑥ 台词接台词（本框引号已闭合）⇒ 断框
            if (cur and cur[-1].rstrip().endswith(('」', '』')) and c[:1] in ('「', '『')
                    and ''.join(cur).count('「') == ''.join(cur).count('」')):
                flush()
                stats['quote_split'] += 1
            # ⑦ if/else 双版：编译器把整段重排一次（段首重复 ⇒ 以第二版为准；尾部重复 ⇒ 丢弃）
            if cur and c == cur[0]:
                cur = [c]
                stats['dual'] += 1
            elif cur and c in cur[1:]:
                stats['dual_tail'] += 1
            else:
                cur.append(c)
            stats['rec'] += 1
            # ⑦ 点击断框：`0x1F4` 不一定紧贴记录尾 —— 双版重排的第二版后面，wait 前还夹着引用块
            #    （`[0][1][1][4]` + `[0][0][1][1]` + `[4][串ID]`，40B），wait 落在 gap 的 +44
            #    （250.DAT 0xdb8f8）。⚠ 必须匹配 `f4010000 00000000`（op + 零参数）：
            #    下一条**指令头**里的 `[0x17b][0x1f4][0x10]` 也含 `f4010000`，那是序号不是 wait
            #    （254.DAT `「自分のものを取り返すのに`｜`　取引なんて必要ない」` 会因此被误拆）。
            nxt_off = recs[k + 1][0] if k + 1 < len(recs) else end + 16
            if WAIT in d[end:end + 16] or WAIT_ARG0 in d[end:nxt_off]:
                flush()
                stats['click'] += 1
        flush()
    out = []
    for x in lines:
        x = x.strip()
        if not x:
            continue
        if out and out[-1] == x:
            stats['dup'] += 1
            continue
        out.append(x)
    # if/else 双版在「框内换行」时会变成相邻的 2~3 行整块重复 ⇒ 块级去重（只去相邻的整块同文）
    for k in (3, 2):
        res = []
        i = 0
        while i < len(out):
            if i + 2 * k <= len(out) and out[i:i + k] == out[i + k:i + 2 * k]:
                res.extend(out[i:i + k])
                stats['dup_block'] += 1
                i += 2 * k
                continue
            res.append(out[i])
            i += 1
        out = res
    return out, stats


KANA = re.compile(r'[\u3040-\u30ff\s・ー]{2,60}')


def dict_lines(path='_w_rq2/sys/DATABASE/dbDictionary.gbin'):
    """用語辞典：`dbDictionary.gbin` = [見出し, 読み, 解説] × N（`#n` 是折行）⇒ `【見出し】解説`。"""
    d = open(path, 'rb').read()
    start = d.find('相合傘の恋まじない'.encode('utf-8'))     # 串表起始（前面是二进制头）
    if start < 0:
        start = 0
    out = []
    i = start
    while i < len(d):
        j = d.find(b'\x00', i)
        if j < 0:
            break
        if d[i:j]:
            try:
                out.append(d[i:j].decode('utf-8'))
            except UnicodeDecodeError:
                break
        i = j + 1
    res = []
    seen = set()
    for k in range(1, len(out) - 1):
        head, yomi, body = out[k - 1], out[k], out[k + 1]
        # 見出し：短く、句点なし（解説の途中が拾われないように）；読み：仮名＋空白のみ；解説：相応の長さ
        if not KANA.fullmatch(yomi) or KANA.fullmatch(head):
            continue
        if not (2 <= len(head) <= 24) or '。' in head or len(yomi) > 40:
            continue
        if len(body) < 8:
            continue
        line = '【%s】%s' % (head, body.replace('#n', ''))
        if line in seen:
            continue
        seen.add(line)
        res.append(line)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--dump', action='store_true')
    a = ap.parse_args()
    files = files_of(SRC)
    print('[i] files', len(files))
    print('[i] init 默认名候选', verify_default_name(os.path.join(SRC, 'init', '0_init.DAT')))
    lines, stats = walk(files, a.dump)
    print('[i] stats', dict(stats))
    dic = dict_lines()
    if dic:
        lines = lines + dic
        print('[i] 用語辞典', len(dic), '条（已并入末尾）')
    print('[i] lines', len(lines), 'chars', sum(len(x) for x in lines))
    for x in sorted(lines, key=len)[-3:]:
        print('[max] %d %s' % (len(x), x[:70]))
    if a.out:
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[ok]', a.out)


if __name__ == '__main__':
    main()
