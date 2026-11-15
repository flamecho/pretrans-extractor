# -*- coding: utf-8 -*-
"""[NS-JP]Code：Realize ～彩虹の花束～ for Nintendo Switch —— STCM2L 文本提取

## 容器链
  romfs（用户模拟器 dump：%APPDATA%/eden/dump/0100B6900A668000/romfs）
  → CONTENTS/STORY_01.cpk（CRI CPK，`scripts/cpk.py`）→ SCRIPT/*.DAT ×155（+ init 子目录）
  另：GAME_01/02.cpk（1.6 GB / 3.5 GB）、SYSTEM.cpk、SOUND/MOVIE —— 剧本只在 STORY

## 记录框架（L0，本作自证）
  文件头 `STCM2L <build>\\0`(32B) + u32@0x20 = **codeEnd** + u32@0x2c = 文件尾-64
  记录 = `[u32 is_call][u32 opcode][u32 nparams][u32 length]` + nparams×12B `[p0][2.0f][2.0f]`
  **length 含 16B 头**；步进到 codeEnd-12 逐字节闭合（155/155 文件）
  串对象 = `[0][L/4][1][L][utf8]`，参数 p0 是**绝对偏移**指向它

## 三种构建串（同一 romfs 混装，opcode 各不同 —— 分别定表）
  | build | 文件数 | 正文 op | 名字 op |
  |---|---|---|---|
  | Dec 14 2016 13:08:37（彩虹の花束） | 36 | 0x10150 / 0x10160 / 0x10170 / 0x3808c | 0x10788 |
  | Feb 10 2014 16:23:58（本篇）      | 96 | 0xe510 | 0xea58 |
  | May 18 2015 17:17:25（？）        | 23 | 0xe540 | 0xea88 |

## 成行（L0）
  **`op=0x1f4` = 等玩家点击**；两次 0x1f4 之间的全部正文段按序拼成一屏 ⇒ 一行。
  自证：一屏内文本段数分布 {1:531, 2:422, 3:323, 0:293, 4:13, 6:11}（104.DAT）
  ⇒ 主体 1〜3 段、上界集中在 3，与 Utage 三行框一致。
  选项 = `n==3 且 p1=文本、p2=='h'、p3 匹配 sure\\d+`（Dec 版 28 条）；组内连续，组末接 0x1f4。
"""
import difflib
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cr_dict

ROOTS = [os.path.join(VNTRANS_HOME, '_w_cr/story/SCRIPT'),    # STORY_01.cpk：本篇（155 个 .DAT）
         os.path.join(VNTRANS_HOME, '_w_cr/story2/SCRIPT')]    # STORY_02.cpk：彩虹の花束 FD（56 个 .DAT）
DICT_DIR = os.path.join(VNTRANS_HOME, '_w_cr/dict')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]Code：Realize ～彩虹の花束～ for Nintendo Switch.txt')

TEXT_OPS = {
    # Dec 2016（本篇主力）：正文 op 随章节不同 —— 每章用一个 0x1015x〜0x1019x 的「本文窗口」op，
    #   箱内多片段的变体式记录走 0x3806c/7c/8c/ac 与 0x3104c（同一句并排 2〜4 版，见 pick_params）
    ('STCM2L Dec 14 2016 13:08:37', 'story'): {0x10150, 0x10160, 0x10170, 0x10190,
                                               0x3806C, 0x3807C, 0x3808C, 0x380AC, 0x3104C},
    ('STCM2L Dec 14 2016 13:08:37', 'story2'): {0x11E3C, 0x3B278, 0x50260, 0x50480, 0x33CC8, 0x45440},
    ('STCM2L Feb 10 2014 16:23:58', 'story'): {0xE510, 0x3104C},
    ('STCM2L Feb 10 2014 16:23:58', 'story2'): {0xFECC},
    ('STCM2L May 18 2015 17:17:25', 'story'): {0xE540},
    ('STCM2L May 18 2015 17:17:25', 'story2'): {0xFEFC},
}
# 名字窗 op = 同名文件的正文 op + 每构建串固定的偏移（Dec=0x628 / Feb=0x548 / May=0x548）；
# 各章正文 op 不同，名字 op 随之不同（0x10778/0x10788/0x10798/0x107b8 …）⇒ 只登记在案的默认值，实用的判据见 NAME_DELTA
NAME_OPS = {
    ('STCM2L Dec 14 2016 13:08:37', 'story'): {0x10788},
    ('STCM2L Dec 14 2016 13:08:37', 'story2'): {0x12648},
    ('STCM2L Feb 10 2014 16:23:58', 'story'): {0xEA58},
    ('STCM2L Feb 10 2014 16:23:58', 'story2'): {0x105C8},
    ('STCM2L May 18 2015 17:17:25', 'story'): {0xEA88},
    ('STCM2L May 18 2015 17:17:25', 'story2'): {0x105F8},
}
# 已核为「标签/旗标/枚举」而不收的 op（内容已逐条抽样确认：`ルパン_共通` `ヴァンend` `ドラちゃん１`
#   `ＦＤエンドコンプ` `無印エンドコンプ` `ヴァン第13話` `ルパンoma` `フィーニス`(名札) 等）
LABEL_OPS = {0x38C74, 0x38C84, 0x38CA4, 0x4D6D0, 0x5164C, 0x6AA0, 0x6A70, 0x6A30, 0x6A00,
             0x319A4, 0x31BC4, 0x33B0C, 0x6560, 0x34014, 0x319D4, 0x3BBC8,
             0x7600, 0x7610, 0x7F34, 0x7F04, 0x7EC4, 0x7E94, 0x7EFC, 0x7DC0,
             0x8D24, 0x8C94, 0x8CDC, 0x3C128}
# 名字窗 op = 本文件正文 op + 每构建串固定偏移（Dec=0x628 / Feb=0x548 / May=0x548）
# 偏移按 **(构建串, 目录)** 定：本篇与 FD 的 opcode 基数不同（Dec 本篇 0x628 / FD 0x80C；
# Feb・May 本篇 0x548 / FD 0x6FC）。自证：0x10788-0x10160 = 0x12648-0x11E3C? = 0x628/0x80C 各自恒定
NAME_DELTA = {('STCM2L Dec 14 2016 13:08:37', 'story'): 0x628,
              ('STCM2L Dec 14 2016 13:08:37', 'story2'): 0x80C,
              ('STCM2L Feb 10 2014 16:23:58', 'story'): 0x548,
              ('STCM2L Feb 10 2014 16:23:58', 'story2'): 0x6FC,
              ('STCM2L May 18 2015 17:17:25', 'story'): 0x548,
              ('STCM2L May 18 2015 17:17:25', 'story2'): 0x6FC}
WAIT_OP = 0x1F4
# 开发用脚本测试：920/921 的正文是 `★スクリプトテスト★` / `キャラ角度 テスト` / `フラッシュ 速度` 之类
# ⇒ 按**文件**整份剔除（不是按内容过滤）
SKIP_FILES = {'920.DAT', '921.DAT'}   # ★スクリプトテスト★ / キャラ角度 テスト / フラッシュ 速度 = 开发测试串
# 菜单台本不靠文件名判定：**整份脚本的行全是选项行**（见 main）⇒ 是ルート/シーン選択・開発ジャンプ台本，整份剔除
SURE = re.compile(r'sure\d+')
# 有些构建的选项记录把 `sureN` 放在**中间**参数（本作 Feb 10 2014 的 `0x11c1c`：param2=sureN、
# param3=`\x08`），末位判据会漏 ⇒ 登记 op 后改为「任一参数 = sureN」。
SURE_ANY_OPS = set()
# 有些构建的选项是**独立组件记录**（op 自身唯一标识选项，前面不接 switch/点击）
# ⇒ 登记该 op 后不再看「组起始」门控。
OPT_ALWAYS_OPS = set()
# 若设为 set：按 **(文件, 显示文本, sureN)** 去重选项——同文本 + 同跳转标号 = 同一个选择节点，
# 引擎可能为「初始显示 / 已选状态」各发一条记录（本作 382 条 → 212 条）。
OPT_SEEN = None
# 逐文件覆盖：`{basename: (正文op集合, 名字窗op集合)}` —— 有的作品每个脚本的 opcode 基数都不同，
# 无法用 (构建串, 目录) 定一张表（ピオフィオーレ -ricordo- 即如此）。由驱动预先探测后填入。
FILE_OPS = {}
# 若为 True：**任何非正文记录都收框**（只把「相邻的正文记录」并成同框）。
# 适用于没有 0x1f4/名字窗这类明确边界、而是「每个其它指令都代表换行/等待」的构建。
FLUSH_OTHERS = False
# 若为 True：`0x6` 只当作「收框」，**不划 if/else 两支**。有的作品把 0x6 当「文本块结束」用，
# 一文件上百次，按分支处理会把整段正文塌成一行（ピオフィオーレ -ricordo-）。
GOTO_PLAIN = False
# 真文本的字符范围：日文假名/汉字 + 全角标点 + `…`(U+2026) + `―`(U+2015)
# （纯符号台词如「…………」「――。」也是正文，不能因为没假名就丢）
JP = re.compile(r'[\u3000-\u30ff\u4e00-\u9fff\uff01-\uff60\u2026\u2015]')
TAG = re.compile(r'</?(?:ruby|color|size|speed)[^>]*>')
CMD_MACRO = re.compile(r'#[A-Za-z]+\[[^\]]*\]')   # #Color[8] / #Speed[..] 等行内指令
NAME_MACRO = re.compile(r'#Name\[(\d+)\]')
HERO = 'カルディア'          # 官方默认名（#Name[1] = 主角名，可改名）


def clean(t):
    t = NAME_MACRO.sub(HERO, t)
    t = CMD_MACRO.sub('', t)
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    t = re.sub(r'\\n', '', t)
    t = TAG.sub('', t)
    t = t.replace('\u3000', ' ').strip()
    return t


def str_at(d, p):
    n = len(d)
    if not (0 < p < n - 16) or struct.unpack_from('<I', d, p)[0] != 0:
        return None
    if struct.unpack_from('<I', d, p + 8)[0] != 1:
        return None
    L = struct.unpack_from('<I', d, p + 12)[0]
    if not (4 <= L <= 8000) or L % 4 or p + 16 + L > n:
        return None
    try:
        s = d[p + 16:p + 16 + L].rstrip(b'\x00').decode('utf-8')
    except UnicodeDecodeError:
        return None
    return s or None


def code_start(d, code_end):
    """CODE 起点：0x40..0x2000 内第一个能一路步进到 codeEnd（±16）的位置。
    上限不能写 0x400 —— 有的构建头部表格更长（ピオフィオーレ -ricordo- 的起点在 0x60c）。"""
    u = lambda o: struct.unpack_from('<I', d, o)[0]

    def ok(i):
        if i + 16 > code_end:
            return False
        pre, op, n, ln = u(i), u(i + 4), u(i + 8), u(i + 12)
        return pre in (0, 1) and 16 <= ln <= 20000 and ln % 4 == 0 and i + ln <= code_end and n <= 64

    for s in range(0x40, 0x2000, 4):
        if not ok(s):
            continue
        j, c = s, 0
        while ok(j) and c < 300000:
            j += u(j + 12)
            c += 1
        if code_end - j <= 16:
            return s
    return None


def norm(s):
    """归一化：去空白 + 去引号。本作同一句常有「带主角名 / 不带主角名」两版
    （`「いいから来い！フラン、カルディア！！」` vs `「いいから来い！」`），
    去引号后互为子串 ⇒ 可被判为同句变体。"""
    return re.sub(r'[\s\u3000「」『』' + HERO + ']', '', s)


def same(a, b):
    """两条文本记录是否「同一句的变体」（结构判据，不看语感）：
    归一化后相等 / 互为子串 / 前 15 字相同（措辞略有出入）。"""
    n, m = norm(a), norm(b)
    # 归一化后极短的片段（如只剩一个「。」）参与子串判断会**平凡命中**
    # （`「カルディア。` 去名后剩 `。`，而 `。` 必然出现在任意长句里）⇒ 短串只认全等
    if min(len(n), len(m)) < 6:
        return n == m
    if not n or not m:
        # 归一化后为空（整句只有主角名/引号）⇒ 退回「只去引号与空白」再比
        n = re.sub(r'[\s\u3000「」『』]', '', a)
        m = re.sub(r'[\s\u3000「」『』]', '', b)
        return bool(n) and n == m
    if n == m or n in m or m in n:
        return True
    return len(n) > 15 and len(m) > 15 and n[:15] == m[:15]


def dedup(recs, min_ratio=0.0):
    """框内逐条去重：命中 same() ⇒ 只留较长者。
    `min_ratio`：要求较短者长度 ≥ 较长者 × 该比例才允许合并 —— 防止**框内续写片段**
    （如 `　言ってくれた」` 恰好是前一片段的子串）被当成变体吞掉。"""
    keep = []
    for s in recs:
        for k, t in enumerate(keep):
            if min_ratio:
                a, b = len(norm(s)), len(norm(t))
                if min(a, b) < max(a, b) * min_ratio:
                    continue
            if same(s, t):
                if len(s) > len(t):
                    keep[k] = s
                break
        else:
            keep.append(s)
    return keep


def sim(a, b):
    """两段文本的相似度（归一化后 SequenceMatcher）；用于识别「同一句的 A/B 版」——
    差异仅在 `#Color` / 括号一处时 ratio ≥ 0.9，真正的不同句远低于此。"""
    n, m = norm(a), norm(b)
    if not n or not m:
        return 0.0
    return difflib.SequenceMatcher(None, n, m).ratio()


def near_same(a, b):
    """「几乎逐字相同」：相似度 ≥0.9 **且改动量很小**（≤2 字 或 ≤8% 长度）。
    只放宽到这一档、不再放宽到「任意 0.9」——因为同一串**整体平移**一位时相似度也 ~0.9，
    但改动量是成块的（数十字），必须排除（实测会把 A 套尾片 + B 套全句拼成一行）。"""
    na, nb = norm(a), norm(b)
    if min(len(na), len(nb)) < 6:
        return na == nb
    sm = difflib.SequenceMatcher(None, na, nb)
    if sm.ratio() < 0.9:
        return False
    changed = sum(max(i2 - i1, j2 - j1)
                  for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal')
    return changed <= max(2, int(0.08 * max(len(na), len(nb))))


def paired_ok(g0, g, f0, f1):
    """两套是否「同一句的变体」：same()（去空白/引号/主角名后相等、互为子串、前 15 字相同）
    或 near_same()（几乎逐字相同）。首片段参数保留用于将来更严的排版对照。"""
    return same(g0, g) or near_same(g0, g)


def slots_ok(slots, groups):
    """变体槽判据的兜底：每套都含空槽，且**首个非空片段在各套中的位置相同**（对照排版），
    且各套拼接后相似度 ≥0.45 ⇒ 认为是同一句的 A/B 版。
    「位置相同」这一条是关键：它把「一套的上半句 / 另一套的下半句」这类**互补片段**排除掉。"""
    if not all(any(not x for x in sl) for sl in slots):
        return False
    offs = []
    for sl in slots:
        idx = next((i for i, x in enumerate(sl) if x), None)
        if idx is None:
            return False
        offs.append(idx)
    if len(set(offs)) != 1:
        return False
    return all(sim(groups[0], g) >= 0.45 for g in groups[1:])


def pick_params(ps, texts):
    """一个记录的 n 个参数（`texts[k]` = 第 k 个参数解析出的正文，非正文 / 空串为 ''）：
    · 通常 n 个参数是**同一文本框的连续片段**（软换行处切开）⇒ 按序拼接；
    · 也可能**按参数位等分**成 m 套互斥变体（同一句的 A/B/C 版：带 / 不带 `#Color`、带 / 不带主角名）。
      判据是**参数级周期**：`(n-off) % p == 0`（off=0/1：有的记录第 0 个参数是句柄，不参与分套），
      且满足以下**任一结构条件**即认为各套是「同一句的变体」⇒ 只取最长的一套：
        ① 各套拼接后互为 same（去空白/引号/主角名后相等或互为子串）或相似度 ≥ 0.9；
        ② 各套的**首片段完全相同**（同一句开头、只是后半改写）；
        ③ **每一套都含空槽**（变体槽用空串占位；纯续写框不会每套都带空槽）。
      用参数级周期才不会被段内的空串 / 非正文参数打乱分组
      （例：`0x380ac n=8` = 4+4 两套，第 2 套的第 2 片为空串；`0x50260 n=7` = 1 句柄 + 3+3 两套）。"""
    n = len(ps)
    # 循环顺序：**周期 p 在外、句柄偏移 off 在内**。必须取「最小周期」——
    # 否则长度非整倍时（如 2 句柄 + 4×3）会出现 p=7 的**错位分组**：两组恰好是同一串整体平移，
    # 相似度也会 ≥0.9，于是把 1 套 + 下一套首片拼成了错误的一行（`ある組織の総帥を…」`+`「私の名は…`）
    for p in range(1, n // 2 + 1):
        for off in range(0, 4):      # 头部句柄参数个数因记录而异（0〜2）
            n2 = n - off
            if n2 < 2 or n2 % p:
                continue
            m = n2 // p
            if m < 2:
                continue
            # ① tiling 之外的前导参数必须全是空槽/非正文 —— 否则说明 off 选错了相位
            #   （109.DAT 反例：off=2 时把 `「おーーーい！` 留在 tiling 外，切出「フラン！…くれ！」这种缺开引号的残句）
            if any(texts[:off]):
                continue
            groups, firsts, slots = [], [], []
            for gi in range(m):
                sl = texts[off + gi * p: off + (gi + 1) * p]
                g = ''.join(sl)
                if not g:
                    groups = None
                    break
                groups.append(g)
                firsts.append(sl[0])
                slots.append(sl)
            if not groups:
                continue
            if all(paired_ok(groups[0], g, firsts[0], fi) for g, fi in zip(groups[1:], firsts[1:])) \
                    or (all(firsts) and len(set(firsts)) == 1) \
                    or slots_ok(slots, groups):
                return max(groups, key=len)
    return ''.join(t for t in texts if t)


QUOTED = re.compile(r'「[^「]*')


def collapse_pieces(t):
    """同一行里若**同一句重复排在相邻位置**（变体记录分套没吃干净时的兜底）：
    把行切成「引号块 / 非引号片段」序列后保序保留，只有**相邻两个引号块**互为 same /
    相似度 ≥0.6 时才丢掉较短的一块。引号前的叙述、块间的非引号字符一律原样保留。"""
    if t.count('「') < 2:
        return t
    segs, pos = [], 0
    for m in QUOTED.finditer(t):
        if m.start() > pos:
            segs.append((False, t[pos:m.start()]))
        segs.append((True, m.group(0)))
        pos = m.end()
    if pos < len(t):
        segs.append((False, t[pos:]))
    out = []
    for isq, sv in segs:
        if isq and out and out[-1][0] and (same(sv, out[-1][1]) or
                                           (min(len(norm(sv)), len(norm(out[-1][1]))) >= 12
                                            and sim(sv, out[-1][1]) >= 0.7)):
            if len(sv) > len(out[-1][1]):
                out[-1] = (True, sv)
            continue
        out.append((isq, sv))
    return ''.join(x for _, x in out)


def click_rows(boxes):
    """一次点击（到 `0x1f4` 为止）内的若干**文本框** → 成行：
    · 任一框带 `alt` 标记（`goto(0x6)` 划出的 if/else 两支）⇒ 只留最长的一支；
    · 否则每个框各成一行（同一句的 A/B 记录已由 `dedup` 在框内合并）。"""
    boxes = [(t, a) for t, a in boxes if t]
    if not boxes:
        return []
    if any(a for _, a in boxes):
        return [max((t for t, _ in boxes), key=len)]
    return dedup([t for t, _ in boxes])


def parse_file(path, tag):
    d = open(path, 'rb').read()
    u = lambda o: struct.unpack_from('<I', d, o)[0]
    build = d[:32].split(b'\x00')[0].decode('utf-8', 'replace')
    code_end = u(0x20)
    st = code_start(d, code_end)
    if st is None:
        return build, None, 0
    global OPT_N
    key = os.path.basename(path)
    if key in FILE_OPS:
        texts, names = FILE_OPS[key]          # 逐文件表（op 基数随脚本变化时用）
    else:
        texts = TEXT_OPS.get((build, tag), set())
        delta = NAME_DELTA.get((build, tag), 0)
        names = {t + delta for t in texts}   # 名字窗：换说话人 ⇒ 必换文本框
    rows = []
    boxes = []                   # 本次点击内的文本框：[(文本, 是否互斥分支)]
    cur = []                     # 当前文本框的片段
    alt_next = False             # 下一个框是 if/else 的另一支
    nopt = 0                     # 本文件产出的**选项**行数（用于判定菜单台本）
    in_choice = False            # 当前是否处于「switch → sureN 组」内
    prev_text = False            # 上一条记录是否「正文 / 0x1f4」（选项组起始的另一判据）

    def flush():
        """收当前文本框。"""
        nonlocal cur, alt_next
        if cur:
            t = ''.join(dedup(cur, 0.5))
            if t:
                boxes.append((t, alt_next))
            cur = []
            alt_next = False

    def close_click():
        """收一次点击。"""
        nonlocal boxes
        flush()
        rows.extend(collapse_pieces(x) for x in click_rows(boxes))
        boxes = []

    def opt_hit(op, n, i):
        """这条记录是不是选项：末参数 = `sureN`（常规），或该 op 登记为「sureN 可在任意位」。"""
        if n < 3:
            return False
        if SURE.fullmatch(str_at(d, u(i + 16 + 12 * (n - 1))) or ''):
            return True
        if op in SURE_ANY_OPS:
            return any(SURE.fullmatch(str_at(d, u(i + 16 + 12 * k)) or '') for k in range(n))
        return False

    i = st
    while i + 16 <= code_end:
        pre, op, n, ln = u(i), u(i + 4), u(i + 8), u(i + 12)
        if pre not in (0, 1) or ln < 16 or i + ln > code_end:
            break
        if op in LABEL_OPS:            # 标签 / 旗标 / 枚举：不是正文，也不是选项
            in_choice = False
        elif op in texts:
            in_choice = False
            # L0：一个记录 = 一个文本框；n 个参数按**参数位**分套后拼接（见 pick_params）
            tp = []
            for k in range(n):
                sv = str_at(d, u(i + 16 + 12 * k))
                tp.append(clean(sv) if (sv and JP.search(sv)) else '')
            if any(tp):
                cur.append(pick_params(tp, tp))
        elif op == 0x6:                # goto：划出 if/else 两支（两支相邻排放，只留一支）
            in_choice = False
            flush()
            if GOTO_PLAIN:
                pass                      # 本构建的 0x6 = 文本块结束，不是互斥分支
            else:
                if boxes:
                    boxes[-1] = (boxes[-1][0], True)
                alt_next = True
        elif op in names:              # 名字窗：说话人变了 ⇒ 必换文本框（本作有「无 0x1f4 直接换人」写法）
            in_choice = False
            flush()
        elif op == 0x3 and n == 4:
            # `[0][\x04][序号][0]`：同框内的**表情/姿势步进**（不是点击）⇒ 不断框
            in_choice = False
        elif op == 0x1F4:              # 等玩家点击 ⇒ 一次点击结束
            in_choice = False
            close_click()
        elif opt_hit(op, n, i):
            # 选项记录（L0）：末参数 = `sureN`；其前**最后一个**日文参数 = 显示文本
            # 组起始判据：紧跟 `switch` 记录，或紧跟一次点击（0x1f4）之后 —— 都是引擎把控制权
            #   交给 choice 组件的位置；组内连续 sure 记录续行，遇正文 / 0x1f4 收组。
            if in_choice or prev_text or op in OPT_ALWAYS_OPS:
                t, lab = '', ''
                for k in range(n):
                    sv = str_at(d, u(i + 16 + 12 * k))
                    if not sv:
                        continue
                    if SURE.fullmatch(sv):
                        lab = sv
                        continue
                    if JP.search(sv):
                        t = clean(sv)
                if t:
                    key = (path, t, lab)
                    if OPT_SEEN is not None and key in OPT_SEEN:
                        in_choice = True      # 同一选项的第二份发行：不计行，但保持组状态
                    else:
                        if OPT_SEEN is not None:
                            OPT_SEEN.add(key)
                        close_click()
                        rows.append(t)
                        OPT_N += 1
                        nopt += 1
                        in_choice = True
        elif n == 2 and str_at(d, u(i + 16)) == 'switch':
            # `switch` = 控制权转移（分支 / 换框）。文本上等同「框到此结束」：本作大量
            # 「台詞框 → switch → 地の文框」结构（如 `「…うめえ！」` + `と、トーストを…`）
            in_choice = True
            flush()
        else:
            in_choice = False
            if FLUSH_OTHERS:
                flush()                # 未知/演出/等待类记录一律把当前框截断
        prev_text = (op in texts) or op == 0x1F4
        i += ln
    close_click()
    return build, rows, nopt


OPT_N = 0


def main():
    rows, stat, menu = [], {}, []
    for root in ROOTS:
        files = sorted(f for f in os.listdir(root) if f.endswith('.DAT') and f not in SKIP_FILES)
        tag = os.path.basename(os.path.dirname(root))
        for f in files:
            build, r, nopt = parse_file(os.path.join(root, f), tag)
            if r is None:
                print('[!] 起点未定位', tag, f, file=sys.stderr)
                continue
            if r and nopt == len(r):
                # 整份脚本的行**全部**是选项行 ⇒ ルート／シーン選択・開発ジャンプ台本（无剧情正文）
                menu.append('%s/%s' % (tag, f))
                continue
            key = build + ' | ' + tag
            stat.setdefault(key, [0, 0])
            stat[key][0] += 1
            stat[key][1] += len(r)
            rows.extend(r)
    n_body = len(rows)
    # 用語辞典（SYSTEM.cpk → DATABASE/dbDictionary_0{1,2}.gbin）并入末尾
    dict_rows = []
    for fn in ('dbDictionary_01.gbin', 'dbDictionary_02.gbin'):
        p = os.path.join(DICT_DIR, fn)
        if os.path.exists(p):
            dict_rows.extend(cr_dict.parse(p)[0])
    rows.extend(dict_rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(rows) + '\n')
    for b, (c, n) in stat.items():
        print('  %-34s files=%-4d lines=%d' % (b, c, n))
    print('其中选项 %d 条；整份剔除的菜单台本 %d 个：%s' % (OPT_N, len(menu), ' '.join(menu)))
    print('正文 %d 行 + 用語辞典 %d 条 = %d 行 -> %s' % (n_body, len(dict_rows), len(rows), OUT))


if __name__ == '__main__':
    main()
