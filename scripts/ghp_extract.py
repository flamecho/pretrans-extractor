#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Glass Heart Princess for Nintendo Switch —— 全文本提取器

作品: Otomate / Design Factory, NS 移植版（本体 ＋ FD「PLATINUM」同捆）
引擎: Idea Factory **STCM2L**（Switch / UTF-8）—— 与「猛獣たちとお姫様」「BLACK WOLVES SAGA」同族，
      但**记录框架与框边界自成一型**（勿套用前作判据）。

链路:
  XCZ(nsz) → nsz -D → XCI → 手切 secure 分区 NCA（hactool -t xci 会因 hfs0_header_hash 报 corrupt）
  → hactool -t nca --romfsdir → RomFS/STORY_01.CPK(本体)・STORY_02.CPK(FD) → CRI CPK → SCRIPT/*.DAT

脚本格式（本作实证）:
  * 文件头 `STCM2L <date>\0`；`CODE_START_\0` 之后为节点区。
  * 每个「消息节点」＝固定 44B 头 ＋ UTF-8 正文:
        [1][REF][1][size][self][0x40000000][0x40000000][0][L/4][1][L][utf8][pad]
      - `i` ＝ L 字段偏移 → 节点起点 s = i-40，节点长 size = 44+L，self = i-12（恒等于 s+28）
      - L = align4(byte_len + 1)
      - REF ＝ 指针（**逐文件不同**）→ 决定「正文 / 话者名」类别；本工具按 REF 分组后
        用「组内假名汉字含有率」分类:  ≥0.75 ＝ 正文, 0.10〜0.75 ＝ 话者名, 其余 ＝ 资源/杂项
  * 一次点击（＝一个文本框）＝ 一连串**地址连续**的节点；出现不连续（中间夹命令节点）或遇到
    「话者名节点」即开新框。**同框内多节点 ＝ 框内软换行 → 合并成一行**。
  * 话者名节点整条丢弃（§0：不加说话人前缀）。
  * 行内宏: `#Name[1]`＝姓 姫乃 / `#Name[2]`＝名 京子（源自 SCRIPT/init/0-init.DAT 默认名表），
    `#Color[n]`・`#Scale[n]`・`#Pos[a,b]` 等样式宏删除。

用法:
  python scripts/ghp_extract.py <SCRIPT目录>[,<SCRIPT目录>...] <out.txt>
"""
import os
import re
import sys
import glob
import struct
import collections

A4 = lambda n: (n + 3) & ~3
REF_TEXT_RATIO = 0.75          # 组内「含假名/汉字」比例 ≥ 此值 且 非「名札型」⇒ 正文
REF_NAME_RATIO = 0.10          # 0.10〜0.75 ⇒ 话者名（其余为资源/杂项）
MIN_GROUP = 3                  # 组内节点数 < 此值 ⇒ 直接当杂项
NAME_LIKE_RATIO = 0.70         # 「短・无句读」比例 ≥ 此值 ⇒ 名札组
NAME_MAXLEN = 16

# 选项（選択肢）节点的 REF —— 本作实证为三个固定值（跨文件稳定）
# 整文件排除：**回想/ギャラリー用のシーン選択スクリプト**
# （实证 890-893/898/990/992＝`どちらのバージョンを見ますか？`系列、FD 99＝`どのイベントを見ますか？`）
RE_GALLERY_FILE = re.compile(r'(?:シーン|バージョン|イベント)を見ますか')
# 选项（選択肢）节点的 REF —— 本作实证为三个固定值（跨文件稳定）
CHOICE_REFS = {0xF6C4, 0xF6F4, 0xF700}
BOX_GAP = 8                # 同框两行之间允许的字节间隙（对齐填充）


JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\uff10-\uff19\uff21-\uff3a\uff41-\uff5a]')
# 名札（话者名）判据: 短、无句读符号（允许 ？ —— 未知名「？？？」）
RE_NAMEPUNCT = re.compile(r'[\u3000-\u303f\u300c-\u300f\uff08\uff09()「」『』。、！!…—―・\s]')


def name_like(t):
    t = t.replace('？', '')
    return len(t) <= NAME_MAXLEN and not RE_NAMEPUNCT.search(t)

# 姓名（源自 init/0-init.DAT 索引 1/2）
NAME = {1: '姫乃', 2: '京子', 3: '京子'}

# 样式 / 位置宏（删除）。注意：`#Name[n]` 必须先替换，再跑这条通用式。
RE_STYLE = re.compile(r'#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]')
RE_NAME_INLINE = re.compile(r'#Name\[(\d)\]')

# 明确排除的「系统 / UI」节点（本作在脚本内，但属 UI 提示）
EXCLUDE_EXACT = {
    'プロローグ・チュートリアルをスキップしますか？',   # 系统提示
    'チュートリアルをスキップしますか？',
    'ＹＥＳ', 'ＮＯ',                                   # 上述提示的选项（UI）
}
# 整行形态的「系统标签」：独立成行的【…】（状態/トピック名・教程标题）、
# 以及パラメータ画面の時間割（`５：００・起床`）。
EXCLUDE_LINE = re.compile(r'^(?:[!！]?【[^】]{1,20}】|[０-９0-9]{1,2}：[０-９0-9]{2}・.*)$')


def scan_nodes(d):
    """返回 [(start, span, k, ref, text), ...]，按文件顺序。

    节点布局（本作实证，4 型）:
      k=1 头 44B : [1][REF][1][size][self][2.0][2.0][0][L/4][1][L][utf8]   ← 正文/话者名
      k=2 头 56B : [1][REF][2][size][p][2.0][2.0][p2][2.0][2.0][0][L/4][1][L][utf8] ← 选项等
      k=4 头 48B : [0][1][KIND][1][size][self][2.0][2.0][0][L/4][1][L][utf8] ← 正文（带容器前缀）
      k=3 头 32B : [0][1][1][4][KIND][0][L/4][1][L][utf8]                    ← 变体台词列表（可多行）
    自指针 self 恒指向 tail 的 `0` 字段。L = align4(byte_len + 1)。
    """
    n = len(d)
    out = []
    for k in (1, 2):
        hdr = 28 + 12 * k
        i = hdr
        while i < n - 8:
            L = struct.unpack_from('<I', d, i)[0]
            if 4 <= L <= 0x8000 and L % 4 == 0 and i + 4 + L <= n:
                s = i - hdr
                ok = (struct.unpack_from('<I', d, s)[0] == 1
                      and struct.unpack_from('<I', d, s + 8)[0] == k
                      and struct.unpack_from('<I', d, s + 16 + 12 * k)[0] == 0
                      and struct.unpack_from('<I', d, s + 16 + 12 * k + 4)[0] == L // 4
                      and struct.unpack_from('<I', d, s + 16 + 12 * k + 8)[0] == 1
                      and struct.unpack_from('<I', d, s + 16)[0] == i - 12)
                if ok:
                    for j in range(k):
                        if (struct.unpack_from('<I', d, s + 16 + 12 * j + 4)[0] != 0x40000000
                                or struct.unpack_from('<I', d, s + 16 + 12 * j + 8)[0] != 0x40000000):
                            ok = False
                    # k=2 的第 2 组指针恒指向「节点末尾」（强校验，滤掉偶然命中）
                    if (k == 2
                            and struct.unpack_from('<I', d, s + 28)[0] != s + 12 * k + 32 + L):
                        ok = False
                if ok:
                    raw = d[i + 4:i + 4 + L]
                    t = raw.rstrip(b'\x00')
                    try:
                        txt = t.decode('utf-8')
                    except UnicodeDecodeError:
                        txt = None
                    if (txt and all(ord(c) >= 0x20 for c in txt)
                            and A4(len(t) + 1) == L):
                        out.append((s, 32 + 12 * k + L, k,
                                    struct.unpack_from('<I', d, s + 4)[0], txt))
            i += 4
    # k=3（变体台词列表: [0][1][1][4][KIND][0][L/4][1][L]）
    i = 32
    while i < n - 8:
        L = struct.unpack_from('<I', d, i)[0]
        if 4 <= L <= 0x8000 and L % 4 == 0 and i + 4 + L <= n:
            ok = (struct.unpack_from('<I', d, i - 12)[0] == 0
                  and struct.unpack_from('<I', d, i - 8)[0] == L // 4
                  and struct.unpack_from('<I', d, i - 4)[0] == 1
                  and struct.unpack_from('<I', d, i - 32)[0] == 0
                  and struct.unpack_from('<I', d, i - 28)[0] == 1
                  and struct.unpack_from('<I', d, i - 24)[0] == 1
                  and struct.unpack_from('<I', d, i - 20)[0] == 4)
            if ok:
                raw = d[i + 4:i + 4 + L]
                t = raw.rstrip(b'\x00')
                try:
                    txt = t.decode('utf-8')
                except UnicodeDecodeError:
                    txt = None
                if (txt and len(txt) >= 2 and JP.search(txt)
                        and all(ord(c) >= 0x20 for c in txt)
                        and A4(len(t) + 1) == L):
                    out.append((i - 32, 36 + L, 3,
                                struct.unpack_from('<I', d, i - 16)[0], txt))
        i += 4
    out.sort()
    return out


def classify_global(all_nodes):
    """【跨文件全局分类】把 (k, REF) 组按「假名/汉字含有率」判为 TEXT/NAME/CHOICE/NOISE。

    REF 在本作**跨文件稳定**（个别文件整体 +0x30），故按全库聚合统计最稳：
    小文件里只有 1~2 条正文的 REF 组不会被误判为噪声。
    """
    grp = collections.defaultdict(list)
    for nodes in all_nodes:
        for nd in nodes:
            grp[nd[2], nd[3]].append(nd[4])
    kind = {}
    for key, texts in grp.items():
        k, ref = key
        if k == 2:
            kind[key] = 'CHOICE' if ref in CHOICE_REFS else 'NOISE'
            continue
        if k == 3:
            kind[key] = 'NOISE' if texts[0].startswith('s_') else 'TEXT'
            continue
        jp = sum(1 for t in texts if JP.search(t)) / len(texts)
        nl = sum(1 for t in texts if name_like(t)) / len(texts)
        if jp < REF_NAME_RATIO:
            kind[key] = 'NOISE'
        else:
            kind[key] = 'NAME' if (jp < REF_TEXT_RATIO or nl >= NAME_LIKE_RATIO) else 'TEXT'
    return kind


def _u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


RE_ASCII = re.compile(r'^[\x20-\x7e]+$')


def bare_records(d, p, starts=()):
    """从 p 起连续消费「裸记录」[0][L/4][1][L][utf8]。

    k=3 列表的续行用这种形态（无完整头）。两条硬约束：
    ① **碰到另一个已扫描节点的起点就停** —— 否则会把下一个 k=3 列表的表头
       `[0][1][1][4][KIND]` 当「4 字节列表项」（实证 KIND 恰为 ASCII 的 `Iv`/`Vv`/`1x`）
       而把下一框整段重读一遍 ⇒ **同一句输出两次**。
    ② 纯 ASCII 的 4 字节项 ⇒ 记 `('break',None)` 断框（A/B 变体分界）。
    返回 (items, next_end)，item ∈ ('text', str) | ('break', None)。
    """
    n = len(d)
    items = []
    while p + 16 <= n and p not in starts:
        if _u32(d, p) != 0 or _u32(d, p + 8) != 1:
            break
        L = _u32(d, p + 12)
        if not (4 <= L <= 0x8000 and L % 4 == 0 and _u32(d, p + 4) == L // 4
                and p + 16 + L <= n):
            break
        t = d[p + 16:p + 16 + L].rstrip(b'\x00')
        try:
            s = t.decode('utf-8')
        except UnicodeDecodeError:
            break
        if not (s and all(ord(c) >= 0x20 for c in s) and A4(len(t) + 1) == L):
            break
        items.append(('break', None) if RE_ASCII.match(s) else ('text', s))
        p += 16 + L
    return items, p


def build_boxes(d, nodes, kind):
    """把正文/话者名/选项节点按「地址连续 + 话者名断框」分组为文本框。"""
    msgs = [nd for nd in nodes if kind[(nd[2], nd[3])] in ('TEXT', 'NAME', 'CHOICE')]
    msgs.sort(key=lambda x: x[0])
    all_starts = {nd[0] for nd in nodes}          # 任何已扫描节点起点（防裸记录走越界）
    boxes = []
    cur = None
    prev_end = None
    for s, span, k, ref, txt in msgs:
        kd = kind[(k, ref)]
        new = ((kd in ('NAME', 'CHOICE') or k == 3) or (cur is None)
               or not (0 <= s - prev_end <= BOX_GAP))
        if new:
            if cur:
                boxes.append(cur)
            cur = {'name': None, 'lines': []}
        if kd == 'NAME':
            cur['name'] = txt
        else:
            cur['lines'].append(txt)
        tail, p = bare_records(d, s + span, all_starts)   # k=3 列表续行 / A|B 变体切分
        for kind2, tx in tail:
            if kind2 == 'break':
                if cur and cur['lines']:
                    boxes.append(cur)
                cur = {'name': None, 'lines': []}
            else:
                cur['lines'].append(tx)
        if kd == 'CHOICE':
            if cur and cur['lines']:
                boxes.append(cur)
            cur = None
        prev_end = p
    if cur:
        boxes.append(cur)
    return boxes


def transform(txt):
    txt = RE_NAME_INLINE.sub(lambda m: NAME.get(int(m.group(1)), m.group(0)), txt)
    txt = RE_STYLE.sub('', txt)
    return txt


def process_file(path, kind):
    d = open(path, 'rb').read()
    nodes = scan_nodes(d)
    boxes = build_boxes(d, nodes, kind)
    lines = []
    for b in boxes:
        if not b['lines']:
            continue
        s = transform(''.join(b['lines'])).strip()
        if not s or s in EXCLUDE_EXACT or EXCLUDE_LINE.match(s):
            continue
        # 纯资源名（无假名汉字也无标点）丢弃
        if not JP.search(s) and not re.search(r'[「」『』。、！？…—]', s):
            continue
        lines.append(s)
    return lines, nodes


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    srcs = sys.argv[1].split(',')
    out = sys.argv[2]
    files = []
    for src in srcs:
        files.extend(sorted(glob.glob(os.path.join(src, '*.DAT'))))
    # 第一遍：全库扫描 → 全局分类（REF 跨文件稳定）
    per_file = []
    for f in files:
        per_file.append((f, scan_nodes(open(f, 'rb').read())))
    kind = classify_global([ns for _, ns in per_file])
    # 第二遍：成行（跳过 回想/ギャラリー 的シーン選択脚本）
    all_lines = []
    skipped = []
    for f, nodes in per_file:
        if any(kind[(nd[2], nd[3])] == 'TEXT' and RE_GALLERY_FILE.search(nd[4])
               for nd in nodes):
            skipped.append(os.path.basename(f))
            continue
        lines, _ = process_file(f, kind)
        all_lines.extend(lines)
    if skipped:
        sys.stderr.write('[skip gallery/scene-select] %s\n' % ','.join(skipped))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for ln in all_lines:
            fh.write(ln + '\n')
    print('files=%d lines=%d -> %s' % (len(files), len(all_lines), out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
