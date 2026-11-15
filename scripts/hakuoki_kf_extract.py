#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]薄桜鬼 真改 風華伝 文本提取（STCM2L / Switch / UTF-8）。

容器：romfs/CONTENTS/STORY_01.cpk ＋ STORY_02.cpk（CRI CPK，本作＝風ノ章／華ノ章两卷）
      → SCRIPT/*.DAT（01:144 本、02:84 本；900.DAT 两卷同容，只取一次）＋ SCRIPT/init/*.DAT（系统表）

记录框架（与薄桜鬼SSL 同族但字段位置不同）：
    [u32 size][u32 ptr→记录内串块][0x40000000][0x40000000][id][id+1][counter][0x10]
              [u32 0][u32 L/4][u32 1][u32 L][UTF-8 文本][pad][尾参数…]
    ★ 32 字节记录（[size=0x20][id][id+1][counter][0x10][0][0][0]）＝一次点击 ⇒ 框边界
    ★ 文本/名札/资源/标签都走同一种「带串记录」，靠 tag 分不出来 —— 见下

名札判据（薄桜鬼 随想録 同族口径，S6-lines-names）：名札是独立名字窗的记录，
    形如「土方 歳三」「雪村 #Name[1]」= 短、无假名、无句读、含分隔空格或 #Name 宏 ⇒ 丢；
    仅此形态的框（`色変化判定`/`好感度沖田`/`羅刹次` 之类系统旗标）整框丢。

用法：
    python scripts/hakuoki_kf_extract.py <SCRIPT 目录…> --out <txt>
"""
import os
import re
import struct
import sys

CLICK_SIZE = 0x20

# 记录 op：`[size][ptr][4e9][4e9] ×N` 之后那一字 ＝ opcode（N 由 4e9 对儿数出来）。
# 本族各作 op 值不同，默认不启用；用 `--drop-op` / `--opt-op` 显式开。
# 万葉ノ抄实测：0x115 台词、0x112 語り、0x13E 双版台词、0xFE 选项组、
# 0x35/0x36/0x37 旗标与 `switch`、0xEE 素材名（`bg52`）、0xFD 菜单标签（`懐古録01`／`事件想起２沖田`／`雨下語りCG`）。
DROP_OPS = set()
OPT_OPS = set()
TITLE_OPS = set()     # 标题/标签记录：名札形态的剔，其余（扉题、手纸题）单独成行
PLATE_OPS = set()     # 名札窗记录：名札剔、扉题（全角空格形态）独行、其余（群体名札／用語／旗标）全剔
BOX_OPS = set()       # 该 op 的记录＝断框（改ページ）；空文本记录也断框
PAGE_LINES = 0        # >0：连续 N 条文本记录自动分页（引擎文本窗行数）；0＝不分页


def rec_op(d, o, sz, u):
    """记录 opcode ＝ 指针表之后那一字。指针项＝12 字节 `[ptr][4e9][4e9]`。"""
    n = 0
    while n < 20:
        p = o + 4 + 12 * n
        if p + 12 > o + sz or p + 12 > len(d):
            break
        if u(p + 4) != 0x40000000 or u(p + 8) != 0x40000000:
            break
        n += 1
    p = o + 4 + 12 * n
    return u(p) if p + 4 <= len(d) else None

KANA = re.compile(r"[\u3040-\u30ff]")
HIRA = re.compile(r"[\u3040-\u309f]")
PUNCT = re.compile(r"[「」。、！？…―〜\-—]")
NAME_PUNCT = re.compile(r"[「」。、]")
# 名札形态：`姓 名`（中间 1 个半角/全角空格），两段都不含标点 —— 本引擎名札窗的固定写法。
# 例：`沖田 ミツ`／`雪村 #Name[1]`／`土方 歳三`。★ 不能只靠「无假名」判：`ミツ` 是片假名，
# 一被排除就会漏进正文，再与后面的 `「…」` 粘成 `沖田 ミツ「先生方…」`（黎明録 L18524 实际踩到）。
PLATE_SEG = (r"[^\s「」『』【】〈〉《》（）()\[\]〔〕〔〕。、，．！？…‥―—～〜・：；"
             r"!?.,:;#＃]")
PLATE = re.compile("^" + PLATE_SEG + "{1,8}[ \u3000]" + PLATE_SEG + "{1,8}$")


CHAPTER = re.compile(r"^(序章|終章|第[一二三四五六七八九十]+章)$")


def is_name_like(s):
    """名札／未知说话人：短、无「」。、，且不是纯标点（`？？？` 算名字）。
    `姓 名` 形态（可含片假名）也算 —— 见 `PLATE`；但全平假名的两段串不算（避免把台词当名札），
    章题形态（`第一章　其ノ一`）也不算（它要走 collect 的 CHAPTER 分支单独成行）。

    ★ 分隔符判据（2026-10-30 月影ノ抄）：本引擎名札窗**恒用半角空格**（`土方 歳三`／`沖田 ミツ`），
    而扉题／章题**恒用全角空格**（`補完物語　伏見`／`共通物語　其の一`／`土方編　個別物語　其の二`）。
    旧写法把两者都当 `PLATE`，于是 `補完物語　伏見` 被当名札丢掉（本作 22 处扉题全失）。
    现：含全角空格而不含半角空格 ⇒ **不是名札**（走单独成行）。
    """
    if "\u3000" in s and " " not in s:
        return False
    if PLATE.match(s) and not re.fullmatch(r"[\u3040-\u309f \u3000]+", s) \
            and "章" not in s and "其ノ" not in s:
        return True
    if CHAPTER.fullmatch(s):              # `序章`／`終章`：章题卡，不是名札
        return False
    return (len(s) <= 14 and not KANA.search(s) and not NAME_PUNCT.search(s)
            and bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9０-９？?]", s)))


def is_title(s):
    """扉题／章题（`補完物語　伏見`／`共通物語　其の一`／`序章`）——上屏标题卡，不是说话人。

    判据只有两条形态量（不是内容词表）：
    ① **全角空格**分隔的多段串：本引擎名札窗恒用半角空格（`土方 歳三`／`沖田 ミツ`），
       标题恒用全角空格 —— 这是同一窗口里两类记录的固定排版差异；
    ② 章题卡固定词形 `序章`／`終章`／`第N章`（`CHAPTER`）。
    ★ 必须排除以全角空格**开头**的串 —— 那是台词续行的字下げ（`　どうしたの、こんな所で」`），
      不是标题；同理排除含 `「」` 的串（标题卡无引号）。
    """
    if s.startswith("\u3000"):
        return False
    if "\u3000" in s and " " not in s and "「" not in s and "」" not in s:
        return True
    return bool(CHAPTER.fullmatch(s))
NAME_MAP = {"#Name[1]": "雪村", "#Name[2]": "千鶴"}

# 系统 UI（非正文）：序章跳过确认框；它的选项随整框一起剔除
SYSTEM_TEXT = {"序章をスキップしますか？"}

# 系统旗标／变量名（不是台词）：形如 end土方／normal土方2／gameover沖田01／好感度土方／色変化判定／羅刹度／伊庭ルート１
FLAG = re.compile(r"(^end|^normal|^bad|^gameover)|好感度|判定|ルート|隊士録|行軍録|羅刹那?(度)?$")

# 系统通知（开放提示 toast），不是台词
NOTICE = re.compile(r"開放されました|開放$")
MACRO = re.compile(r"#[A-Za-z][A-Za-z0-9_]*(?:\[[^\]]*\])?")
INLINE_NAME = re.compile(r"^([^\s「」（）]{1,12})[\u3000 ]*(「.*」)$")
PUNCT_ONLY = re.compile(r"^[…―〜\-—！？!?\s]+$")


ASCII_ID = re.compile(r"^[#A-Za-z0-9_\[\]\-\.\/]+$")


def ok_string(s):
    """串内容校验：无控制符；含日文，或整体是 ASCII 标识符（#Name[1]／ev12020…／aya_WorB_01）。"""
    if not s or len(s) > 2000:
        return False
    if any(ord(c) < 0x20 for c in s):
        return False
    if KANA.search(s) or re.search(r"[\u4e00-\u9fff]", s):
        return True
    if re.search(r"[「」『』（）…―、。！？]", s):     # 宏版台词（`「#Name[1]……。」`）无假名无汉字
        return True
    return bool(ASCII_ID.match(s))


def norm_ver(s):
    """版本比对用归一化：名字宏**与默认名**都→占位、去引号、去空白。
    本作每次含主角名的台词都存两份：固定名版（千鶴）＋ `#Name[1]` 宏版。"""
    for v in NAME_MAP.values():
        if v:
            s = s.replace(v, "\u0001")
    s = re.sub(r"#[A-Za-z]+\[\d+\]", "\u0001", s)
    s = re.sub(r"[「」『』（）()、。！？…―\.\,\!\?\u3000 ]", "", s)
    return s


def group_msgs(blocks):
    """按**消息 id** 把记录内的串分组成「消息」，一条消息＝一版。

    结构判据（字节字段，不用相似度／不用字数）：
        每条消息的第一个串前有标志 `[u32 4][u32 msgid]`：
            +0x080 [4][0xEDCA][0][0C][1][30]「#Name[1]ちゃんは、食ったのか？」
            +0x0FC [4][0xEDCB][0][0C][1][30]「おまえさんは、食ったのか？」
        同一消息的续行只有 `[0][L/4][1][L][文本]`，没有 4/msgid：
            +0x0C4 …text…  +0x0C8 [0][13][1][34]「　敵はどうなった？…」
    一条记录里出现 2 个 msgid ＝ 同一句存了两版（`#Name` 有名版／无名版），各出一行；
    同一 msgid 下的多段 ＝ 同一框内的换行，合并成一行。
    两版逐字全等（归一化后）⇒ 只出一版，避免重复行。
    """
    groups = []
    for mid, s in blocks:
        if mid is not None or not groups:
            groups.append([])
        groups[-1].append(s)
    if len(groups) > 1:
        sig = [tuple(norm_ver(x) for x in g) for g in groups]
        if all(s == sig[0] for s in sig):
            return groups[:1]
    return groups


def read_dat(path):
    """返回 boxes：box = [(文本, 是否选项), …]，box 内顺序＝记录顺序。

    ★ 一次点击（size==0x20）断框；框内每条记录可能带 1〜2 个串。
    ★ 选项＝记录里带 `sureN` 标签的那条（全库 1,247 条）⇒ 选项组内每条单独一行，
      不能与提示语拼在一起（否则「名を名乗る名乗らない」会粘成一行）。
    """
    d = open(path, "rb").read()
    if not d.startswith(b"STCM2L"):
        return []
    i = d.find(b"CODE_START_")
    if i < 0:
        return []
    u = lambda o: struct.unpack_from("<I", d, o)[0]
    o = i + 24
    boxes, cur, run = [], [], 0
    rid = 0
    SURE = re.compile(r"sure\d+$")
    while o + 8 <= len(d):
        sz = u(o)
        if sz <= 0 or sz % 4 or o + sz > len(d):
            break
        if sz == CLICK_SIZE:
            if cur:
                boxes.append(cur)
                cur = []
            run = 0
            rid += 1
            o += sz
            continue
        op = rec_op(d, o, sz, u)
        if op in BOX_OPS and cur:      # 改ページ命令 ⇒ 断框
            boxes.append(cur)
            cur = []
            run = 0
            rid += 1
            o += sz
            continue
        if op in DROP_OPS:
            o += sz            # 素材名／旗标／菜单标签记录：整条丢
            rid += 1
            continue
        rec = []
        k = 4
        while k < sz - 8:
            got = None
            # 形态 A：[0][L/4][1][L][文本]
            if u(o + k) == 0 and u(o + k + 4) and u(o + k + 8) == 1:
                L = u(o + k + 12)
                if 0 < L <= 2000 and L % 4 == 0 and u(o + k + 4) == L // 4 \
                        and o + k + 16 + L <= len(d):
                    got = (o + k + 16, L, 16 + L)
            # 形态 B：[L/4][1][L][文本]（前导 0 省略；宏版台词常用这种）
            if got is None and k >= 4:
                L = u(o + k + 8)
                if 0 < L <= 2000 and L % 4 == 0 and u(o + k + 4) == 1 \
                        and u(o + k - 4) == L // 4 and o + k + 12 + L <= len(d):
                    got = (o + k + 12, L, 12 + L)
            if got is not None:
                toff, L, step = got
                # 长度字段会偏：① 多算 1 字节（万葉ノ抄 505.DAT，尾部 0x09）⇒ 削尾部控制字节；
                # ② 少算 1–2 字节（銀星ノ抄 302.DAT @0x61440，末字「」」被截断成非法 UTF-8）
                #    ⇒ 解不出就往后补字节，直到 UTF-8 完整（最多补 2 字节，遇 NUL/ASCII 停）。
                s = None
                for extra in range(0, 3):
                    end = toff + L + extra
                    raw = d[toff:end].split(b"\0")[0]
                    raw = raw.rstrip(bytes(range(0x20)))
                    try:
                        s = raw.decode("utf-8")
                        break
                    except UnicodeDecodeError:
                        s = None
                        nxt = d[end] if end < len(d) else 0
                        if nxt == 0 or nxt < 0x80:
                            break
                if s and ok_string(s):
                    # 消息 id：本串块前 8 字节是 `[4][msgid]` ⇒ 新消息起点
                    bs = o + k
                    mid = u(bs - 4) if bs - 8 >= o and u(bs - 8) == 4 else None
                    rec.append((mid, s))
                    k += step
                    continue
            k += 4
        if BOX_OPS and not rec:            # 空文本记录（L=4，只有 NUL 串）＝改ページ
            if cur:
                boxes.append(cur)
                cur = []
            run = 0
            rid += 1
            o += sz
            continue
        if rec:
            rec = [(m, x) for m, x in rec if not (x.isascii() and x != "switch")]
            lead = []
            if op in PLATE_OPS:                 # 名札窗：名札剔、扉题独行、其余（群体名札／用語／旗标）全剔
                for _, x in rec:
                    if is_title(x) or is_name_like(x):
                        lead.append(x)
                rec = []
            elif op in TITLE_OPS:               # 标题记录：名札剔，其余单独成行
                for _, x in rec:
                    if is_name_like(x):
                        lead.append(x)
                    else:
                        cur.append((x, True, rid, -1, False))
                rec = []
            while rec and is_name_like(rec[0][1]):
                lead.append(rec.pop(0)[1])          # 名札／资源名：单独打标，供上层切块
            vers = group_msgs(rec) if rec else []
            is_opt = op in OPT_OPS or any(SURE.fullmatch(x) for _, x in rec)
            for x in lead:
                cur.append((x, False, rid, -1, True))
            for vi, ver in enumerate(vers):
                for x in ver:
                    cur.append((x, is_opt, rid, vi, False))
            if PAGE_LINES and vers and not is_opt:
                run += sum(1 for ver in vers for _ in ver)
                if run >= PAGE_LINES:       # 文本窗写满 ⇒ 引擎自动翻页
                    boxes.append(cur)
                    cur = []
                    run = 0
        rid += 1
        o += sz
    if cur:
        boxes.append(cur)
    return boxes


def is_name_tag(s):
    """独立名字窗的名札：短、无假名、无句读、带分隔空格或 #Name 宏。"""
    if len(s) > 14 or KANA.search(s) or PUNCT.search(s):
        return False
    return (" " in s) or ("\u3000" in s) or ("#Name" in s)


def is_system_flag(s):
    """系统旗标／资源名／二进制串：含控制符、纯 ASCII、或命中旗标词。"""
    if any(ord(c) < 0x20 for c in s):
        return True
    if s.isascii() and s != "switch":
        return True
    if re.match(r"^[A-Za-z]", s) and s != "switch":
        return True          # 变量名/资源名：ev12020池田屋風間あり／op風ノ章／end土方 …
    if re.search(r"イベント|シーン|ページ|ＣＥＲＯ", s):
        return True          # 脚本内部标签：藤堂イベント１／シーン4-4-8／ＣＥＲＯ用スクリプト
    if len(s) <= 12 and re.search(r"[０-９]+$", s) and "「" not in s:
        return True          # 以全角数字收尾的变量名
    # 旗标名判据（2026-10-30）：只当**整串就是旗标名**时才丢。
    # 旧写法 `FLAG.search(s)` 是子串匹配，会把真台词一起杀掉 ——
    # 天雲ノ抄 101.DAT @0x8A6B8「実は、先日話に出た行軍録に…」因含「行軍録」整行消失。
    if FLAG.search(s) and len(s) <= 12 and not re.search(r"[「」。、！？…]", s):
        return True
    return False


CHAPTER = re.compile(r"^(序章|終章|[一二三四五六七八九十]+章(其ノ[一二三四五六七八九十]+)?)$")


def join(parts):
    """框内多行合并：续行行首的 `　` 是排版缩进，去掉。"""
    out = []
    for s in parts:
        s = clean(s)
        if not s.strip("\u3000 "):
            continue
        if out and s.startswith("\u3000"):
            # 句末署名（`　――雪村千鶴」`）前的全角空格是原文间隔，保留
            if not s.lstrip("\u3000").startswith("――"):
                s = s.lstrip("\u3000")
        out.append(s)
    return "".join(out)


def strip_inline_name(line):
    """行首「名＋（空格）＋「台词」」＝内联名札（名字与台词同一串）⇒ 去名保引号。
    前缀若只是标点（`……「…」`）则不动。"""
    m = INLINE_NAME.match(line)
    if not m or PUNCT_ONLY.match(m.group(1)):
        return line
    return m.group(2)


def clean(s):
    s = s.replace("#n", "")      # 软换行（框内换行，合并）
    for k, v in NAME_MAP.items():
        s = s.replace(k, v)
    return MACRO.sub("", s)


def load_names(path):
    """从 SYSTEM.cpk/DATABASE/strGame.gstr 取角色名表，生成「姓 名」变体（表内是无空格的 土方歳三）。"""
    import re as _re
    d = open(path, "rb").read()
    out = set()
    for m in _re.finditer(rb"(?:[\xe3-\xe9][\x80-\xbf]{2}){1,}", d):
        w = m.group().decode("utf-8", "replace")
        if not w or "\u3000" in w:
            continue
        out.add(w)
        for k in (2, 3):
            if len(w) > k:
                out.add(w[:k] + " " + w[k:])
                out.add(w[:k] + "\u3000" + w[k:])
    return out


def collect(srcs, name_path=None):
    import hashlib
    all_boxes = []
    seen_md5 = set()
    for src in srcs:
        for f in sorted((x for x in os.listdir(src) if x.upper().endswith(".DAT")),
                        key=lambda x: (len(x), x)):
            if f.upper() == "99.DAT":
                continue      # 系统/设定脚本：序章跳过确认 ＋ 暴力表现等级（CERO）表
            p = os.path.join(src, f)
            h = hashlib.md5(open(p, "rb").read()).hexdigest()
            if h in seen_md5:      # 900.DAT 两卷同容
                continue
            seen_md5.add(h)
            for box in read_dat(p):
                if any(NOTICE.search(x) for x, *_ in box):
                    continue
                box = [(x, opt, rid, vi, nm) for x, opt, rid, vi, nm in box
                       if not is_system_flag(x)]
                if box:
                    all_boxes.append(box)

    first, mid = {}, {}
    for box in all_boxes:
        i = 0
        for x, opt, rid, vi, nm in box:
            if nm:
                continue
            d = first if i == 0 else mid
            d[x] = d.get(x, 0) + 1
            i += 1
    # 名札＝短、无句读，且绝大多数出现在框首
    names = {x for x in first
             if is_name_like(x) and mid.get(x, 0) <= max(1, first[x] // 10)}
    names |= {x for x in list(first) + list(mid)
              if len(x) <= 8 and not KANA.search(x) and not NAME_PUNCT.search(x)
              and "\u3000" not in x and not CHAPTER.fullmatch(x)   # 全角空格／`序章`＝扉题，不是名札
              and not re.fullmatch(r"[…―〜\-—！？!?\s]+", x)}
    if name_path:
        names |= load_names(name_path)

    lines = []
    for box in all_boxes:
        # ① 按名札记录切块（名札＝说话人设置 ⇒ 每种称呼一块）
        blocks = []
        for item in box:
            if item[4]:
                blocks.append([item])       # 名札记录 ⇒ 新块（＝换称呼的版本）
            else:
                if not blocks:
                    blocks.append([])
                blocks[-1].append(item)

        # ② 块 × 版本序号（vi）＝一行；两版都留
        buf, key = [], None

        def flush():
            if buf:
                ln = join(buf)
                if ln:
                    lines.append(strip_inline_name(ln))
                del buf[:]

        for bi, b in enumerate(blocks):
            for x, opt, rid, vi, nm in b:
                if nm:
                    if is_title(x):          # 扉题／章题：自成一行（不并入台词）
                        flush()
                        key = None
                        t = clean(x).strip()
                        if t:
                            lines.append(t)
                    continue
                if x in names or x == "switch":
                    continue
                k = (bi, vi)
                if k != key:
                    flush()
                    key = k
                if opt:
                    flush()
                    o = clean(x).strip("\u3000 ")
                    if o:
                        lines.append(o)
                    continue
                if CHAPTER.match(x.strip()):
                    flush()
                    lines.append(x.strip())
                    continue
                buf.append(x)
        flush()
    return lines


def load_dict(path):
    """用語辞典（SYSTEM.cpk/DATABASE/dbDictionary.gbin）：
    NUL 分隔的串池，前缀 0x3730，尾部到 `GBNL` 之前；条目＝[見出し語][よみ(可省)][解説]。
    ★ 見出し語本身是假名时**没有读音串**（`あぐり`/隊士・佐々木愛次郎と恋仲の町娘。）。
    ★ 少数条目解説为空（`島原\0しまばら\0下総\0…`）⇒ 该条无上屏文字，跳过。
    """
    d = open(path, "rb").read()
    gn = d.find(b"GBNL")
    body = d[:gn] if gn > 0 else d
    m = re.search(rb"(?:[\xe3-\xe9][\x80-\xbf]{2})+", body)
    if not m:
        return []
    seq = []
    i = m.start()
    while i < len(body):
        j = body.find(b"\0", i)
        if j < 0:
            break
        s = body[i:j]
        if s:
            seq.append(s.decode("utf-8", "replace"))
        i = j + 1

    KANA_ONLY = re.compile(r"^[\u3040-\u30ff\u30fc\u30fb\uff08\uff09 ]+$")
    # ★ 串数能被 3 整除、且每组第 2 串都是假名 ⇒ 固定「見出し語／よみ／解説」三切（風華伝 270＋295 条）
    if len(seq) % 3 == 0 and all(
            KANA_ONLY.match(seq[i + 1]) and not seq[i + 1].endswith("。")
            for i in range(0, len(seq), 3)):
        res = []
        for i in range(0, len(seq), 3):
            head = seq[i].replace("#n", "").strip()
            desc = seq[i + 2].replace("#n", "").strip()
            if not desc or len(head) > 20 or "。" in head:
                continue                    # 見出し語字段不该含句号（含＝错位）
            res.append("【%s】%s" % (head, desc))
        return res
    out = []
    k = 0
    while k < len(seq):
        head = seq[k]
        k += 1
        if k < len(seq) and KANA_ONLY.match(seq[k]) and not seq[k].endswith("。"):
            k += 1                      # 读音，丢弃（交付不带读音）
        if k >= len(seq):
            break
        desc = seq[k]
        # 解説为空：下一条的見出し語被当成了解説（短、不以「。」结尾、后面跟读音）
        if not desc.endswith("。") and not KANA_ONLY.match(desc) \
                and k + 1 < len(seq) and KANA_ONLY.match(seq[k + 1]):
            continue
        k += 1
        desc = desc.replace("#n", "").strip()
        head = head.replace("#n", "").strip()
        if not desc or len(head) > 20 or "。" in head:
            continue
        out.append("【%s】%s" % (head, desc))
    return out


def main(argv):
    args = [a for a in argv[1:]]
    out = None
    name_path = None
    if "--names" in args:
        j = args.index("--names")
        name_path = args[j + 1]
        args = args[:j] + args[j + 2:]
    for key, macro in (("--name1", "#Name[1]"), ("--name2", "#Name[2]")):
        if key in args:
            j = args.index(key)
            NAME_MAP[macro] = args[j + 1]
            args = args[:j] + args[j + 2:]
    dict_paths = []
    while "--dict" in args:
        j = args.index("--dict")
        dict_paths.append(args[j + 1])
        args = args[:j] + args[j + 2:]
    drop_ops, opt_ops = set(), set()
    name_ops = set()
    page_lines = 0
    if "--page-lines" in args:
        j = args.index("--page-lines")
        page_lines = int(args[j + 1], 0)
        args = args[:j] + args[j + 2:]
    plate_ops = set()
    box_ops = set()
    for key, tgt in (("--drop-op", drop_ops), ("--opt-op", opt_ops),
                     ("--title-op", name_ops), ("--box-op", box_ops),
                     ("--plate-op", plate_ops)):
        while key in args:
            j = args.index(key)
            tgt.update(int(x, 0) for x in args[j + 1].split(",") if x.strip())
            args = args[:j] + args[j + 2:]
    if "--out" in args:
        j = args.index("--out")
        out = args[j + 1]
        args = args[:j] + args[j + 2:]
    srcs = args
    global DROP_OPS, OPT_OPS, TITLE_OPS, PLATE_OPS, BOX_OPS, PAGE_LINES
    DROP_OPS = drop_ops
    OPT_OPS = opt_ops
    TITLE_OPS = name_ops
    PLATE_OPS = plate_ops
    BOX_OPS = box_ops
    PAGE_LINES = page_lines
    lines = collect(srcs, name_path)
    seen_dict = set()
    for dp in dict_paths:                 # 两卷各一份辞典，重复条目只留一次
        for ln in load_dict(dp):
            if ln not in seen_dict:
                seen_dict.add(ln)
                lines.append(ln)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="\n") as fh:
        for ln in lines:
            fh.write(ln + "\n")
    print("目录 %d / 行 %d / 字节 %d" % (len(srcs), len(lines), os.path.getsize(out)))


if __name__ == "__main__":
    main(sys.argv)
