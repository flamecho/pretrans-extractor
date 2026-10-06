# -*- coding: utf-8 -*-
"""STCM2L 剧本文本提取器 —— 猛獣たちとお姫様 for Nintendo Switch

【格式实证结论（2026-09-30）】
容器链路：
  XCI (hactool + 你自己的 prod.keys) -> secure/*.nca -> RomFS -> STORY_01/02.CPK -> SCRIPT/*.DAT
脚本格式：STCM2L（Idea Factory 系字节码，Switch 版）
  * 头部 'STCM2L' + 日期串；文件内是「对象/指令字段」的序列化流
  * 每个字符串字段 = [u32 L][UTF-8 bytes][NUL][pad]
      L = align4(utf8len + 1)，恒为 4 的倍数
  * 记录之间夹着 VM 字段（非字符串），需按 4 字节步进扫描
  * 剧情文本顺序 = 文件内出现顺序（已实证无 PE 乱序）
  * 说话人标注：
      `#Name[N]` -> 主角（1:ユーリア / 2:ユーリ）
      短人名串（塔の見張り１ / ルドヴィク / ミアーシュ ...） -> NPC 说话人
  * 消息边界：
      立绘切换串 `mob*_a` / `b-*_a` / `hub_a` / `b-*_b` ...
      紧随其后的数字（`100`/`101`/...）是该立绘的编号
  * 选项：`switch` ... [人名或选项文本, `d`, `sureN`] ... `switch`
  * 心声/旁白：多以 `（` 包裹，前置 `#Name[1]` + `c` 标记

【输出规范（用户既定）】
  1 次点击 = 1 行（同一消息框内的分行片段合并为一行）
  保留原文日文，不翻译
  不输出说话人名前缀
  `#Name[1]` -> ユーリア / `#Name[2]` -> ユーリ
  选项与正文一起按序输出
"""
import struct
import re
import os
import glob
import sys
import io
import difflib

A4 = lambda n: (n + 3) & ~3

# 消息开始标记：STCM2L 的「新消息/文本框」描述符
# `[...][0x00014058][count][0x60]` —— 每个标记开启一次「点击消息」
# 实证：800.DAT（序章）只有 2 个 `<` 分页符，但 52 个 0x14058 标记，
#       标记位置与「一次点击 = 一句」完全吻合。
MSG_DESC = 0x00014058
_MSG_DESC_B = MSG_DESC.to_bytes(4, 'little')

RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_TEXTY = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff'
                      r'\u3000-\u303f\uff01-\uff60\u2010-\u2030\u2026\u2015]')
RE_PLACEHOLDER = re.compile(r'^#Name\[(\d+)\]$')
RE_INLINE_NAME = re.compile(r'#Name\[(\d+)\]')
# 人名允许含全角数字（塔の見張り１ / 見張り２）与未知说话人标记（？？？）
RE_NAME_OK = re.compile(r'^[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uff10-\uff19\uff1f\uff01]+$')

# 立绘/背景资源串（消息边界）—— 见资源出现即视为场景切换 = 新消息
RE_TACHIE = re.compile(
    r'^(?:'
    r'mob\d*_[a-z]|b-[a-z0-9]+_[a-z]|hub_[a-z]|fr[a-z]*_[a-z]'
    r'|[a-z]{3}\d{2}[a-z]?$'                 # bg07a / rys01 / hen_d 类场景·立绘代号
    r'|[a-z]{3}_[a-z]$'
    r')$'
)
# 纯数字（立绘编号）
RE_NUMONLY = re.compile(r'^\d{1,4}$')
# 消息开始标记（`c` 字段，恒跟在 `#Name[N]` 之后）
MSG_MARKERS = {'c'}

# 游戏教学文本区（ＦＭＭＳ 玩法说明，非剧情）—— 起止标记
RE_TUTORIAL = re.compile(r'^tutorial\d*$')
RE_TUTORIAL_END = re.compile(r'^ＦＭＭＳの遊び方は以上となります。$')

HEROINE = {1: 'ユーリア', 2: 'ユーリ'}

# 明确的资源/系统标签 → 丢弃内容，但**仍作为消息边界**（flush）
# 注意：这些串本身带 delta>=4，是脚本里真实的消息分隔符；
#       若只丢弃不 flush，紧随其后的正文会粘到上一条消息（实证：tutorial01）。
RE_BOUNDARY_RES = re.compile(
    r'^(?:'
    r'switch$|sure\d+$|tutorial\d*$|d$|e$|x$'
    r'|bg\d+[a-z]?$|frame\d*$'
    r')$'
)

# 明确的资源/系统标签（纯噪声，直接丢弃，不作边界）
# ⚠️ 注意：用 `^(...)$` 精确匹配的项不能做「前缀」匹配 ——
#    曾把 `ＦＭＭＳ` 写成前缀，误杀了 30 条玩家可见文本
#    （`ＦＭＭＳの目的は、` / `ＦＭＭＳを開始する` / FMSS 选人菜单 等）。
RE_RES = re.compile(
    r'^(?:'
    r'位置＿|flg_|love_end|LOVE_|MPup|SPup'
    r'|en\d+$|[a-zA-Z_]{1,24}\d*$'
    r')'
    # 角色立绘/结局 flag 表（数据表区，非剧情）
    r'|.{1,12}oma$'
    r'|.{1,12}end\d*$'
    r'|.{1,12}chapter\d+$'
    # 结局 ID 标签（结局一览内部 flag）：`リシャルトAFTER04` / `リシャルトed` / `ノーマルed`
    r'|.{1,12}AFTER\d+$'
    r'|.{1,12}ed$'
    # FMSS 选人菜单的内部 ID（`ＦＭＭＳリシャルト１` 这类），
    # 但**不**匹配以 `ＦＭＭＳ` 开头的正文（如 `ＦＭＭＳの目的は、`）。
    r'|ＦＭＭＳ[\u3040-\u30ff\u4e00-\u9fff]{1,8}[１-９\d]$'
    # 剧本 flag / 分支管理标签（非剧情、非玩家可见）
    r'|選択肢[０-９\d]+$'
    r'|ストーリー分岐[０-９\d]+$'
    r'|ルート解放[０-９\d]+$'
    r'|お仕事[０-９\d]+解決$'
    r'|.{1,12}ルート確定$'
    r'|.{1,12}ルート$'          # 717.DAT 的 `タルメルート`（与 713.DAT 的 `タルメ` 同槽位）
    r'|竜化.+$'                 # 事件标签 `竜化リシャルト` / `竜化タルメ`（同槽位还有 ev7080）
)
RES_EXACT = {
    '特殊ウィンドウ', 'フレーム', '色変化判定', 'チャプタージャンプ',
    'ノーマルエンド', 'モフモフ判定', 'おみや', '名声度', '全曲解放',
    'ＦＭＭＳ',
    'c', 'P', '(', '<', '-r', '2', '-l', ' ', 'Z', '-c',
    'XV', '-', '@',
}


def scan_strings(path):
    """扫描 STCM2L 文件，返回 [(offset, L, text, node, msgstart)]（文件顺序）。

    node = 台词节点 ID，从记录头 `[1][4][node][0][idx][1]`（紧邻字符串前 24 字节）读取。
      * node 非 None -> 这是一条**新消息/台词节点的行首**（如 200004 / 210003）
      * node is None -> 续行 / 立绘串 / 说话人
    msgstart = 该片段是否为「消息描述符 `[...][0x00014058][count][0x60]` 之后的第一个文本片段」
      * True -> 这是一条**新消息（一次点击）的开头**
    两条判据互补：主剧本靠 node，序章/绘本（800.DAT）只有 msgstart。
    """
    d = open(path, 'rb').read()
    n = len(d)
    # 1) 先定位所有消息描述符偏移
    marks = [m.start() for m in re.finditer(re.escape(_MSG_DESC_B), d)]
    # 2) 选项：`sureNN` 标记后回溯，紧邻的字符串即选项文本。
    #    标记模板（`[1][1][4][<tag:u32>][0][2][1][8] "sureNN\0"`）：
    #      tag 是随上下文变化的 ID（如 0x3c0 / 0x64 / 0x320），必须通配。
    #    其前是选项文本记录 `[1][L=A4(tlen+1)][text][null 填充]`。
    SURE_TMPL = re.compile(
        rb'(?:\x01\x00\x00\x00){2}\x04\x00\x00\x00....'
        rb'\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00'
        rb'\x08\x00\x00\x00sure\d+\x00')
    choice_offs = set()
    for m in SURE_TMPL.finditer(d):
        sp = m.start()
        # 选项文本记录与普通串同构：`[1][L=A4(tlen+1)][text][null 填充]`。
        # 从 `sureNN` 模板往前回溯，找到满足该形状且到模板之间全为 0 的记录。
        for back in range(8, 8 + 0x200 + 16):
            p = sp - back                          # `[1]` 头位置
            if p < 0:
                break
            hdr1, L = struct.unpack_from('<2I', d, p)
            if hdr1 != 1 or not (4 <= L <= 0x200) or L % 4:
                continue
            if p + 8 + L > sp:
                continue
            raw = d[p + 8:p + 8 + L]
            t = raw.rstrip(b'\x00')
            if not t or A4(len(t) + 1) != L:
                continue
            gap = d[p + 8 + L:sp]
            if any(b != 0 for b in gap):
                continue
            try:
                t.decode('utf-8')
            except Exception:
                continue
            choice_offs.add(p + 4)                 # `L` 字段位置 = 主扫描的 i
            break
    mk = 0
    out = []
    prev_a1 = None
    i = 0
    while i < n - 8:
        L = struct.unpack_from('<I', d, i)[0]
        if 4 <= L <= 0x4000 and L % 4 == 0 and i + 4 + L <= n:
            raw = d[i + 4:i + 4 + L]
            t = raw.rstrip(b'\x00')
            if t:
                try:
                    s = t.decode('utf-8')
                except Exception:
                    s = None
                if s and all(ord(c) >= 0x20 for c in s) and A4(len(t) + 1) == L:
                    node = None
                    if i >= 24:
                        a, b, c, z, idx, one = struct.unpack_from('<6I', d, i - 24)
                        if a == 1 and b == 4 and z == 0 and one == 1:
                            node = c
                    # 头部 `[0x40000000][a1][a2=a1+1][len][16][0][idx][1]` 的 a1
                    # 是「片段序号」，同一消息内 delta=2，新消息 delta>=4
                    a1 = None
                    if i >= 32:
                        h = struct.unpack_from('<8I', d, i - 32)
                        if h[0] == 0x40000000 and h[2] == h[1] + 1:
                            a1 = h[1]
                    delta = (a1 - prev_a1) if (a1 is not None
                                               and prev_a1 is not None) else None
                    if a1 is not None:
                        prev_a1 = a1
                    # 该片段前是否存在尚未「消费」的消息描述符
                    msgstart = False
                    if mk < len(marks) and marks[mk] < i:
                        msgstart = True
                        mk += 1
                    is_choice = i in choice_offs
                    out.append((i, L, s, node, msgstart, delta, is_choice))
        i += 4
    return out


def is_noise(s):
    if s in RES_EXACT:
        return True
    if RE_NUMONLY.match(s):
        return True
    if RE_RES.match(s):
        return True
    return False


def looks_like_name(s):
    return bool(s) and len(s) <= 10 and RE_NAME_OK.match(s)


def is_dialog(s):
    return any(ch in s for ch in '「」『』')


def _is_skippable(s):
    """前瞻时跳过的「非正文」串（资源标记 / flag / 占位符）。"""
    return (is_noise(s) or RE_BOUNDARY_RES.match(s) or RE_TACHIE.match(s)
            or s in MSG_MARKERS or RE_PLACEHOLDER.fullmatch(s) is not None)


def collect_labels(files, lookahead=4):
    """第一遍：判定「哪些短名型串是说话人标签」。

    【判据（2026-10-03 实证）】说话人标签后面（允许隔着 `d`/`x`/`ev*` 等资源标记）
    必定紧跟一条 `「…」` 台词；而**短旁白/台词碎片**后面接的是自己的续句，
    永远不跟 `「`。
      正例：`ヘンリク`   -> `「いや、涙ぐむほど感激してくれたとは`   （标签）
            `ピスキスの人たち` -> `d` -> `「かんぱ～い！」`        （标签）
      反例：`そう言うとヘンリクは` -> `不思議そうに眉根を寄せた。`      （正文）
            `どうしてそんな目に？` -> `城の兵士たちは…`              （正文）
    凡出现「后跟 `「`」的短串，判为说话人标签（整部作品统一丢弃）。
    """
    labels = set()
    for f in files:
        sc = scan_strings(f)
        for k, t in enumerate(sc):
            s = t[2]
            if t[6] or is_noise(s) or not looks_like_name(s) or is_dialog(s):
                continue
            if not RE_TEXTY.search(s):
                continue
            for j in range(k + 1, min(len(sc), k + 1 + lookahead)):
                nx = sc[j][2]
                if _is_skippable(nx):
                    continue
                if nx[:1] in ('「', '『'):
                    labels.add(s)
                break
    return labels


# ---------------------------------------------------------------------------
# 称呼变体对（A/B 互斥节点）—— 只保留 A 版（名字直写），丢弃 B 版
# ---------------------------------------------------------------------------
# 【实证 2026-10-03】脚本对同一句存两版，node 编号相邻（N / N+1，个别 B 版 node=0）：
#   A 版 = 名字直写（ユーリア／ユーリ）           ← 保留
#   B 版 = 占位符 `#Name[N]` 或 称号・代名詞        ← 丢弃
#          变体族：王女殿下 / 姫 / 姫さま / 王女 / お前 / 彼女 / あの人 / そっち
# 全游戏 ≥571 处（73 个文件）。B 版占位符替换后常与 A 版逐字相同 → 输出里出现重复行。
# 用户决定：连称呼变体也去，只留直写名版。
RE_APPELL = re.compile(
    r'(?:王女殿下|姫さま|ユーリア|王女|ユーリ|#Name\[1\]|#Name\[2\]'
    r'|お前|彼女|あの人|そっち)(?:さま|様|さん|ちゃん|殿下)?')
VARIANT_SIM = 0.6


def _norm_appell(s):
    """把「对女主角的称呼」统一成占位符，用于变体对比较。"""
    return re.sub(r'[\s\u3000]', '', RE_APPELL.sub('\x01', s))


def find_variant_b(recs, labels, sim_thresh=VARIANT_SIM):
    """返回「称呼变体 B 版」的文本记录 offset 集合（这些记录将被丢弃）。

    判据：相邻两条消息 · 起始 node 满足 `n2 == n1 + 1` 或 `n2 == 0`
          · 归一化（称呼→占位符）后相似度 >= 阈值
    只在 node 编号相邻时才判定，正常连续台词不会满足该形状。
    """
    msgs = []          # [node, text, [offsets]]
    cur = None
    for o, L, s, node, msgstart, delta, ch in recs:
        is_label = (s in MSG_MARKERS
                    or RE_BOUNDARY_RES.match(s) or RE_TACHIE.match(s)
                    or RE_TUTORIAL.match(s) or ch
                    or (looks_like_name(s) and s in labels and not is_dialog(s)))
        if is_label:
            if cur:
                msgs.append(cur)
                cur = None
            continue
        if is_noise(s) or 'sss' in s or RE_PLACEHOLDER.fullmatch(s):
            continue
        if not RE_TEXTY.search(s):
            continue
        is_new = (node is not None) or msgstart or (delta is not None and delta >= 4)
        if is_new or cur is None:
            if cur:
                msgs.append(cur)
            cur = [node, s, [o]]
        else:
            cur[1] += s
            cur[2].append(o)
    if cur:
        msgs.append(cur)

    drop = set()
    for a, b in zip(msgs, msgs[1:]):
        n1, n2 = a[0], b[0]
        if n1 in (None, 0) or n2 is None:
            continue
        if not (n2 == n1 + 1 or n2 == 0):
            continue
        if len(a[1]) < 4 or len(b[1]) < 4:
            continue
        r = difflib.SequenceMatcher(None, _norm_appell(a[1]),
                                    _norm_appell(b[1])).ratio()
        if r >= sim_thresh:
            drop.update(b[2])
    return drop


def tokenize(path, labels=None):
    """返回按文件顺序的 token 列表：
       ('open',)              立绘切换 / 分页 / 消息描述符（新消息）
       ('name', s)            说话人名（NPC）
       ('text', s, is_new)    剧情文本（is_new=True 表示新消息开头）

    注：`tutorialNN` 教学区（ＦＭＭＳ 玩法说明）也是**玩家可见文本**，保留，
    但 tutorial 标记本身作为消息边界 flush（其后的说明文字是新消息开头）。

    `labels` = `collect_labels()` 得到的两遍法说话人标签集合。
    短名型串**只有在集合里**才当说话人丢弃；否则按正文输出
    （避免把 `どうしてそんな目に？` / `そう言うとヘンリクは` 这类短旁白吃掉）。
    未传 `labels` 时退化为单文件自统计。

    称呼变体：A 版（名字直写）与 B 版（占位符/称号）互斥共存，
    这里按用户决定**只保留 A 版**，B 版记录整体跳过（见 `find_variant_b`）。
    """
    if labels is None:
        labels = collect_labels([path])
    recs = scan_strings(path)
    variant_b = find_variant_b(recs, labels)
    toks = []
    in_tutorial = False
    for o, L, s, node, msgstart, delta, is_choice in recs:
        if o in variant_b:          # 称呼变体 B 版 → 丢弃
            continue
        # ---- 教学区起始标记：新消息边界，内容不输出 ----
        if RE_TUTORIAL.match(s):
            in_tutorial = True
            toks.append(('open', None, None))
            continue
        # ---- 选项文本：本身独立成一行，其后的 `sureNN` 标记再 flush 一次 ----
        #   （`sureNN` 已由 RE_BOUNDARY_RES 处理为 open）
        if is_choice:
            if RE_TEXTY.search(s) and not is_noise(s):
                toks.append(('text', s, True))
                toks.append(('open', None, None))
            continue
        # ---- 教学区内文字：保留，边界仍按 delta 规律判断 ----
        if in_tutorial:
            if RE_TUTORIAL_END.search(s):
                in_tutorial = False
            if (RE_TEXTY.search(s) and not is_noise(s)
                    and not (looks_like_name(s) and s in labels)):
                is_new = (node is not None) or msgstart or (delta is not None and delta >= 4)
                toks.append(('text', s, is_new))
            continue
        # 资源/系统串：内容丢弃，但作为消息边界 flush
        if RE_BOUNDARY_RES.match(s):
            toks.append(('open', None, None))
            continue
        if RE_TACHIE.match(s):
            toks.append(('open', None, None))
            continue
        # 数据表区人名列表（`リシャルトsssルドヴィクsss...`）
        if 'sss' in s:
            continue
        if RE_PLACEHOLDER.fullmatch(s):
            continue
        if s in MSG_MARKERS:
            toks.append(('open', None, None))
            continue
        if not RE_TEXTY.search(s):
            continue
        if is_noise(s):
            continue
        if looks_like_name(s) and not is_dialog(s):
            if s in labels:                     # 真说话人标签 -> 丢弃（不输出到行首）
                toks.append(('name', s, None))
                continue
            # 不在标签集合 -> 是**短旁白/台词碎片**，按正文处理（补 issue #3）
        # 新消息开头（任一）：
        #   * 台词节点 ID（主剧本对白）
        #   * 消息描述符 0x14058 后的首个文本片段（序章）
        #   * 片段序号 delta >= 4（旁白段 —— 唯一可用的边界信号）
        is_new = (node is not None) or msgstart or (delta is not None and delta >= 4)
        toks.append(('text', s, is_new))
    return toks


def _brackets_closed(s):
    """该行是否已构成完整对白（「」成对且已闭合）。"""
    depth = 0
    for ch in s:
        if ch == '「':
            depth += 1
        elif ch == '」':
            depth -= 1
            if depth <= 0:
                return True
    return False


RE_SUBTITLE = re.compile(r'^『[^『』]{1,40}』$')


def _is_standalone_title(s, buf=''):
    """`『…』` 完全包裹且较短 = 章节副标题，应独立成行。

    例外：若缓冲区已有未闭合的 `「`，说明这是台词内的**引用**（`「…『…』…」`），
    不可切分。
    """
    if not RE_SUBTITLE.match(s):
        return False
    # 缓冲区里有未闭合的「 -> 是台词内引用
    depth = 0
    for ch in buf:
        if ch == '「':
            depth += 1
        elif ch == '」':
            depth = max(0, depth - 1)
    return depth == 0


def _sub_placeholder(s):
    """把文本内联的 `#Name[N]` 换成主角名（1:ユーリア / 2:ユーリ）。"""
    def _r(m):
        return HEROINE.get(int(m.group(1)), m.group(0))
    return RE_INLINE_NAME.sub(_r, s)


def build_lines(toks):
    """把 token 折叠成「一次点击 = 一行」。

    消息边界判据（任一即切）：
      1. `open`（立绘切换 / 分页 `<` / `c` 标记）
      2. `text` 的 `is_new` 为 True —— 新的台词节点或消息描述符（新消息行首）
      3. 缓冲区已构成完整对白（「」已闭合）
      4. `name`（说话人切换）—— 见下

    【实证（2026-09-30）】两种「新消息」信号，互补使用：
      * **台词节点 ID**（STORY_01/02 主剧本）：行首片段头部 `[1][4][node][0][idx][1]`，
        node 如 200004 / 210003；分支互斥版本各有独立 node。
      * **消息描述符 0x00014058**（序章/绘本 800.DAT）：`[...][0x14058][count][0x60]`，
        每出现一次 = 一次点击。800.DAT 里只有 2 个 `<` 分页符但 52 个该标记。
    """
    lines = []
    buf = []

    def flush():
        if buf:
            lines.append(''.join(buf))
            buf.clear()

    for kind, s, is_new in toks:
        if kind == 'open':
            flush()
            continue
        if kind == 'name':
            # 说话人名一律是「下一条消息」的开头标记：
            # 无论缓冲区是否闭合都先切行，然后丢弃人名本身
            # （规则：说话人名不输出到行首）。
            # 例外：缓冲区有未闭合的「，说明该串其实是台词碎片而非人名。
            if buf:
                if ''.join(buf).count('「') > ''.join(buf).count('」'):
                    buf.append(s)
                    continue
                flush()
            continue
        # kind == 'text'
        if buf:
            if is_new:
                flush()
            elif _brackets_closed(''.join(buf)):
                flush()
            elif _is_standalone_title(s, ''.join(buf)):
                flush()
        # 章节副标题 `『…』`：缓冲区为空且非台词内引用 -> 独立成行
        if not buf and _is_standalone_title(s):
            lines.append(s)
            continue
        buf.append(s)
    flush()
    return [_sub_placeholder(x) for x in lines]


def process_files(files):
    """两遍法主流程：先全量统计说话人标签，再逐文件提取。"""
    labels = collect_labels(files)
    lines = []
    for f in files:
        lines.extend(build_lines(tokenize(f, labels)))
    return lines


def process_file(path):
    return process_files([path])


def main():
    """用法：stcm2l_extract.py <SCRIPT dir|file> [<dir|file> ...] <out.txt>

    支持多源输入：说话人标签集合从**全部输入文件**统一统计
    （如 `魔術師` 在 STORY_02 里只出现在人名数据表，单跑会误判为正文）。
    """
    if len(sys.argv) < 3:
        print('usage: stcm2l_extract.py <SCRIPT dir|file> [<dir|file> ...] <out.txt>')
        return
    srcs = sys.argv[1:-1]
    out = sys.argv[-1]
    files = []
    for src in srcs:
        if os.path.isfile(src):
            files.append(src)
        else:
            files.extend(sorted(glob.glob(os.path.join(src, '*.DAT'))))
    all_lines = process_files(files)
    with io.open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for ln in all_lines:
            ln = ln.strip()
            if ln:
                fh.write(ln + '\n')
    print('files=%d lines=%d -> %s' % (len(files), len(all_lines), out))


if __name__ == '__main__':
    main()
