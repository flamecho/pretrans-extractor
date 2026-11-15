#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]9 R.I.P. —— STCM2L(UTF-8) 文本提取。

【2026-10-28 实证结构】
容器：NSZ→NSP→NCA(keygen16)→RomFS→CONTENTS/STORY.cpk（CRI CPK, CRILAYLA）→ SCRIPT/*.DAT
脚本：`STCM2L Apr 12 2018 18:22:39`（与《十鬼の絆》同一份运行时），但**编码 UTF-8**、tag 与断框都不同。
  记录 = [u32 0][u32 cnt][u32 1][u32 cnt*4][UTF-8 文本，尾 NUL 补足 cnt*4]
  记录前 16 字节 = [a][tag][seq][0x10]；**正文 tag = 0x163**
  其它 tag：0x138 = 「視点変更_紅華」标签、0x01 = 「説明文01」、0x10E = 「色変化判定」、0x162 = 测试
断框（L0）：
  · 记录结束后的 16 字节内出现 **`0x1F4`（wait＝点击）** ⇒ 该框到此为止；
  · 名札记录（含 `#Name[1]`，形如 `#Color[23]逸#Color[0]色 #Name[1]`）⇒ 独立名字窗，**剔除并断框**；
  · 其余为**框内换行**（续行）⇒ 合并。
用法: python scripts/rip9_extract.py [--out 提取结果/x.txt] [--dump]
"""
import argparse
import collections
import os
import re
import struct

SRC = '_w_rip/story/SCRIPT'
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
JPONLY = re.compile(r'^[\u3040-\u30ff\u4e00-\u9fff\u30fc]+$')
PUNCT = re.compile(r'[「」『』、。！？…―\s]')
RE_ASCII = re.compile(r'^[0-9A-Za-z_\-\.]+$')
RE_COLOR = re.compile(r'#(?:Color|Name|Speed|Scale|Fade)\[[^\]]*\]')
RE_RUBY = re.compile(r'#Ruby\[([^,\]]*),([^\]]*)\]')
TAG_BODY = 0x163
WAIT = b'\xf4\x01\x00\x00'


def load(path):
    d = open(path, 'rb').read()
    n = len(d)
    out = []
    i = 0
    while i + 20 <= n:
        z, c, one, bl = struct.unpack_from('<IIII', d, i)
        if z == 0 and one == 1 and 1 <= c <= 0x400 and bl == c * 4 and i + 16 + bl + 16 <= n:
            if struct.unpack_from('<I', d, i - 12)[0] == TAG_BODY:
                try:
                    s = d[i + 16:i + 16 + bl].decode('utf-8').rstrip('\x00')
                except UnicodeDecodeError:
                    s = None
                if s:
                    out.append((i, c, s))
                    i += 16 + bl
                    continue
        i += 4
    return d, out


HEROINE = '珠沙'   # 官方设定：女主角默认名「珠沙」，姓固定「逸色」（絢芽 是母亲）


def clean(s):
    s = RE_RUBY.sub(lambda m: m.group(1), s)
    s = s.replace('#Name[1]', HEROINE)
    s = RE_COLOR.sub('', s)
    return s.strip().lstrip('　')


def bare(s):
    """剥掉全部样式标签后的纯文本（用于判名札/资源名）。"""
    s = RE_RUBY.sub(lambda m: m.group(1), s)
    s = RE_COLOR.sub('', s)
    return s.strip()


def is_junk(s):
    """控制符 / 无日文的短串 / 无标签可剥的纯 ASCII 资源名（`switch` `small_tate` `bg_02a` `g[` `<`）。

    ⚠ 不能按「首字符是 ASCII」判：`#Color[3]――――ねえ　知ってる？` 是**特效正文**；
    正确做法是**先剥标签再比**——剥完与原串相同才可能是资源名。
    """
    if any(ord(ch) < 0x20 for ch in s):
        return True
    b = bare(s)
    if not b:
        return True
    if '_' in b:
        return True                      # `bg_落書き１` `響_正解` `1-2-10通過紅華_正解`
    if len(b) <= 12 and re.search(r'[A-Za-z]', b):
        return True                      # `kureha6-2通過`
    if re.match(r'^[0-9\-]+[-0-9]', b):
        return True                      # `1-2-10通過`
    if b == s.strip():
        if RE_ASCII.match(b):
            return True
        if not JP.search(b) and not re.search(r'[「」『』、。！？…―・～]', b):
            return True
    return False


RE_NAMECH = re.compile(r'^[\u3040-\u30ff\u4e00-\u9fff\u30fc\uff21-\uff3a\uff41-\uff5a\uff10-\uff19\s？?！!]+$')


def is_name_candidate(s):
    t = bare(s)
    return bool(t) and len(t) <= 8 and bool(RE_NAMECH.match(t))


def build_names(files):
    """名札白名单：剥标签后 ≤6 字纯日文，且**下一记录以「或（开头**（＝台词/心声）。"""
    names = set()
    for p in files:
        d, recs = load(p)
        for k, (off, c, s) in enumerate(recs):
            if not is_name_candidate(s):
                continue
            if k + 1 < len(recs) and recs[k + 1][2][:1] in '「（':
                names.add(bare(s))
    return names


SLOT_TEXT = 0x13a                                   # メッセージウィンドウ正文
SLOT_OPT = 0xda                                     # 選択肢
SLOT_CHAT = {0x173, 0x17e, 0x181, 0x188}            # スマホのメッセージ（正文，无「」）
SLOT_NAME = set(range(0x164, 0x173)) | {0x17d, 0x180, 0x187}   # 名札窓族（名字/表情资源）
RE_CHAP = re.compile(r'其ノ|編|終幕|^序章$')
# 章题卡只在这两个槽：实测 71 条里 67 条 0x164、2 条 0x165（后继都是同名资源 `学校の怪談01`）；
# 另有 1 条 0x17d 的 `序章` 是「章題＋場面番号＋話者」存档元数据三元组，不是画面上的卡 ⇒ 不算。
SLOT_CHAP = {0x164, 0x165}
# 变量/旗标/分支指令槽（`switch` 分支、`マップ回数`、`桃嘉ルート`、`共通ルート`、`話題選択`、`精神度` …）。
# ★ 这些槽必须**先于 junk 形态过滤**处理并断框：`switch` 长得像资源名（纯 ASCII），
#   若被 junk 吃掉就不断框，会把「心声框」和紧跟的叙述粘成一行
#   （实测 101.DAT 0xa4750：`（…クローゼットの奥にしまうしかないな）` + `そんな風に考えなら歩いていると…`）。
SLOT_UI = {0x35, 0x36, 0x37, 0x127, 0x161}


def slot(d, off):
    """记录前 16 字节首 u32 = 槽/指令号（0x13a=正文窗，0x164..=名札窗，0xda=选项，0x35/36/37=变量旗标）。"""
    return struct.unpack_from('<I', d, off - 16)[0]


def walk(files, dump=False, names=frozenset()):
    lines = []
    stats = collections.Counter()
    for p in files:
        d, recs = load(p)
        cur = None
        cur_kind = None

        def flush():
            nonlocal cur, cur_kind
            if cur:
                lines.append(''.join(cur))
            cur = None
            cur_kind = None

        for off, c, s in recs:
            end = off + 16 + c * 4
            has_wait = WAIT in d[end:end + 16]
            sl = slot(d, off)
            if sl in SLOT_UI:
                # 分支/旗标指令：交互边界，**断框**（必须在 junk 形态过滤之前判，见 SLOT_UI 注释）
                flush()
                stats['ui'] += 1
                continue
            if is_junk(s):
                # 资源名/控制记录：不是正文。**不断框**——断框只认 0x1F4（L0）、槽变化（L1）与名札（L1），
                # 资源切换不是一次点击，断在这里会把一句话劈成两行（实测 17 处引号不配平）。
                stats['junk'] += 1
                continue
            if sl in SLOT_NAME:
                # 名札窗：章题卡（`序章` `学校の怪談編　其ノ壱` `紅華　終幕 天`）⇒ 直接上屏，单列
                # 其余（人名 / 内部资源标签 `学校の怪談01`）⇒ 剔除
                if sl in SLOT_CHAP and RE_CHAP.search(bare(s)):
                    flush()
                    lines.append(bare(s))
                    stats['chap'] += 1
                else:
                    flush()
                    stats['name'] += 1
                continue
            if sl == SLOT_OPT:
                flush()
                lines.append(clean(s))
                stats['opt'] += 1
                continue
            if sl not in SLOT_CHAT and sl != SLOT_TEXT:
                # 变量/旗标/UI 菜单标签（`共通ルート` `話題選択` `精神度` `マップ回数`）：**断框**
                flush()
                stats['ui'] += 1
                continue
            if bare(s) in names:
                flush()
                stats['name'] += 1
                continue
            kind = 'chat' if sl in SLOT_CHAT else 'text'
            # ★ 台词接台词（上一段以」收，本段以「起）＝换了说话人 ⇒ 新框
            if cur and cur[-1].rstrip().endswith(('」', '』')) and s.lstrip('　').startswith(('「', '『')):
                flush()
                stats['quote_split'] += 1
            if cur is None:
                cur = [clean(s)]
                cur_kind = kind
            elif cur_kind != kind:
                flush()
                cur = [clean(s)]
                cur_kind = kind
            else:
                cur.append(clean(s))
            stats['rec'] += 1
            if has_wait:
                flush()
                stats['click'] += 1
        flush()
    out = []
    for x in lines:
        x = x.strip()
        if not x:
            continue
        # 相邻完全相同的行＝if/else 互斥分支各排一份（本作 12 处，含 `気分転換しよう`/`どこに行こうかな？`
        # 这类双版选项），只留一版。`無理無理無理…` 那种同框连排在同一行内，不受影响。
        if out and out[-1] == x:
            stats['dup'] += 1
            continue
        out.append(x)
    return out, stats


def dict_lines(path='_w_rip/sys/DATABASE/dbDictionary.gbin'):
    """用語辞典：dbDictionary.gbin = [見出し, 読み, 解説] × N ⇒ `【見出し】解説`（#n 折行合并）。"""
    t = open(path, 'rb').read().decode('utf-8', 'replace')
    runs = [m.group() for m in re.finditer(r'[\u3040-\u30ff\u4e00-\u9fff][^\x00-\x1f]{1,200}', t)]
    out = []
    i = 0
    while i + 2 < len(runs):
        head, read, body = runs[i], runs[i + 1], runs[i + 2]
        if re.fullmatch(r'[\u3040-\u30ff\s・ー]+', read):      # 第 2 项应是读音（假名）
            out.append('【%s】%s' % (head, body.replace('#n', '')))
            i += 3
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--dump', action='store_true')
    a = ap.parse_args()
    files = []
    for root, _, fs in os.walk(SRC):
        for f in fs:
            if f.upper().endswith('.DAT'):
                files.append(os.path.join(root, f))
    files.sort()
    print('[i] files', len(files))
    names = build_names(files)
    print('[i] 名札白名单', len(names), sorted(names)[:10])
    lines, stats = walk(files, a.dump, names)
    print('[i] stats', dict(stats))
    dic = dict_lines()
    if dic:
        lines = lines + dic
        print('[i] 用語辞典', len(dic), '条（已并入末尾）')
    print('[i] lines', len(lines), 'chars', sum(len(x) for x in lines))
    for x in sorted(lines, key=len)[-3:]:
        print('[max] %d %s' % (len(x), x[:80]))
    if a.out:
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[ok]', a.out)


if __name__ == '__main__':
    main()
