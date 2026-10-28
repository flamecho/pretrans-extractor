#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""終遠のヴィルシュ -ErroRsalvation- (NS) STCM2L 文本提取。

链路: XCI → Program NCA（Standard crypto，key_area 槽 2）→ romfs/CONTENTS/STORY.cpk
      → SCRIPT/*.DAT（STCM2L「Feb 10 2014」SW 变体，UTF-8）

指令（L0）: [u32 func][u32 argc][u32 len][argc × 12B 槽][行内串区]，槽 = [u32 串记录偏移][0x40000000][0x40000000]
串记录: [u32 size][u32 0x10][u32 0][u32 L/4][u32 1][u32 L][UTF-8][NUL][pad]（24B 头）
       CODE_START_+0x10 起按 len 递推，走到 0x54614（100.DAT）＝文件尾标签表前，闭合。

语义（全库 117 文件统计，op 跨文件稳定）:
  0x11d14 (84,819) 正文片段（一次一块，多片段用 0x1f4 收框）
  0x1243c (22,774) 名札（独立名字窗）⇒ 丢
  0x1f4   (…)    等待点击 ⇒ 断框（一次点击 = 一行）
  0x1301c (144)  选项：槽0=选项文，槽2=sureN 跳转
  0x27b0  (450)  章题卡（第一幕　死神の呪い）⇒ 收（直接上屏）
  0x36a14/0x3674c/0x4720c/0x4738c 文本组（同文两版：#Color 版 / 纯文版）⇒ 取首版
  0x90ac/0x945c = switch（条件），0x999c/0x992c/0x3a394 = 结局 flag 串 ⇒ 不收

用法: python scripts/virche_extract.py <SCRIPT目录> <out.txt>
"""
import sys, os, glob, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERO = 'セレス'                     # セレス・プルースト（#NAME[1] 默认名）
BODY = {0x11d14}
TEXTGRP = {0x36a14, 0x3674c, 0x4720c, 0x4738c}
NAME = {0x1243c}
CHOICE = {0x1301c}
TITLE = {0x27b0}
CLICK = {0x1f4}

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def srec(d, off):
    """本作严格串记录（16B 头）：[u32 0][u32 L/4][u32 1][u32 L][UTF-8][NUL...]
    （sympathy_extract.readrec 的宽松回退会在这版格式上产生假阳性 ⇒ 这里自证四个字段）"""
    if off < 0 or off % 4 or off + 16 > len(d):
        return None
    a, l4, one, L = struct.unpack_from('<4I', d, off)
    if a != 0 or one != 1 or L != l4 * 4 or not (4 <= L <= 20000):
        return None
    body = d[off + 16:off + 16 + L]
    if len(body) < L:
        return None
    z = body.find(b'\x00')
    if z >= 0:
        body = body[:z]
    try:
        s = body.decode('utf-8')
    except UnicodeDecodeError:
        return None
    # 含控制符 ⇒ 不是显示串（如 `%\x04` 这类结构体误命中）
    if any(ord(c) < 0x20 for c in s):
        return None
    return s
RE_RUBY = re.compile(r'#Ruby\[([^,\]]*),[^\]]*\]')
RE_COLOR = re.compile(r'#Color\[\d+\]')
RE_NAME = re.compile(r'#NAME\[(\d+)\]')
RE_ANY = re.compile(r'#[A-Za-z][A-Za-z0-9_]*(\[[^\]]*\])?')


def clean(s):
    s = RE_RUBY.sub(lambda m: m.group(1), s)
    s = RE_NAME.sub(HERO, s)
    s = RE_COLOR.sub('', s)
    s = RE_ANY.sub('', s)
    return s.strip(' \u3000')      # 行首 U+3000＝悬挂缩进（框内软换行），去；行内全角空格保留


def walk(d):
    cs = d.find(b'CODE_START_')
    if cs < 0:
        return
    o, n = cs + 0x10, len(d)
    while o + 12 <= n:
        op, argc, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n or argc > 400 or 12 + argc * 12 > ln:
            return
        slots = [srec(d, struct.unpack_from('<I', d, o + 12 + i * 12)[0]) for i in range(argc)]
        yield o, op, slots
        o += ln


def is_text(s):
    """文本片段判据：含日文，或以「『（ 开头（纯拉丁短串如 `AKL`/`,zL` 是资源·音声 ID）。"""
    return bool(s) and bool(re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', s) or s[0] in '「『（')


def _min_period(t):
    """t（slot 串列表）在 clean 后呈周期重复时，返回最小周期 P（原串层面至少有一项不同才算变体），否则 0。

    本作 0x4738c 的槽里会并排放 **4 个变体 × 3 段**，变体之间只差 `#Color[8]…` 的高亮位置：

        ['私たち一般人が住む', '#Color[8]【#Ruby[庶民区,クーネ]】#Color[0]の治安を守る、', '#Color[8]自警団…#Color[0]を務めてくれている。',
         '私たち一般人が住む', '#Color[8]【#Ruby…】#Color[0]の治安を守る、', '自警団のリーダーを務めてくれている。', … 共 4 组]

    clean 后 4 组全等 ⇒ 旧逻辑（取「第一段连续正文」）把 12 段全拼起来，同一句重复 4 遍。
    判据：clean 后周期 P、整串 = P 的整数倍、且**原串层面存在差异**（纯 #Color 差异）⇒ 只取前 P 段。
    若原串完全一样（真·正文重复，如框内两次「はい。」）⇒ 不截断，照源保留。"""
    n = len(t)
    cl = [clean(x) for x in t]
    for P in range(1, n // 2 + 1):
        if n % P or n // P < 2:
            continue
        if all(cl[i] == cl[i % P] for i in range(n)) and any(t[i] != t[i % P] for i in range(n)):
            return P
    return 0


def grp_texts(slots):
    """文本组（0x36a14/0x3674c/0x4720c/0x4738c）：槽里排着「资源 ID → 明文版 → 空 → 资源 ID → #NAME 版」，
    取**第一段连续正文**（＝明文版，与交付口径「不改写」一致）；段内若是多版本并排（无分隔符），按周期取一个变体。"""
    runs, cur = [], []
    for s in slots:
        if is_text(s):
            cur.append(s)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if not runs:
        return []
    t = runs[0]
    P = _min_period(t)
    return t[:P] if P else t


def dict_entries(path):
    """用語辞典 dbDictionary.gbin：NUL 分隔的「見出し / 読み / 解説」三元组，读到非文本即止。
    ⇒ `【見出し】解説`（去读音；`#n` 为框内换行，删）"""
    d = open(path, 'rb').read()
    i = d.find('アドルフ'.encode('utf-8'))
    out = []
    if i < 0:
        return out
    parts = d[i:].split(b'\x00')
    txt = []
    for p in parts:
        if not p.strip():
            continue
        try:
            s = p.decode('utf-8')
        except UnicodeDecodeError:
            break
        txt.append(s)
    out = []
    k = 0
    while k + 2 < len(txt):
        tri = txt[k:k + 3]
        if all(JP.search(x) for x in tri):
            out.append('【%s】%s' % (tri[0], clean(tri[2]).replace('#n', '')))
            k += 3
        else:
            k += 1
    return out


def main():
    src, out = sys.argv[1], sys.argv[2]
    dpath = sys.argv[3] if len(sys.argv) > 3 else None
    lines, stats = [], {'files': 0, 'boxes': 0, 'frag': 0, 'opt': 0, 'title': 0, 'grp': 0}

    for fn in sorted(glob.glob(os.path.join(src, '*.DAT'))):
        d = open(fn, 'rb').read()
        stats['files'] += 1
        buf = []

        def flush():
            if not buf:
                return
            body = ''.join(x for x in buf if x)
            buf.clear()
            if body.strip():
                lines.append(body)
                stats['boxes'] += 1

        rows = list(walk(d))
        for idx, (o, op, slots) in enumerate(rows):
            look_menu = False
            if op in TITLE:
                for _o2, op2, s2 in rows[idx + 1:idx + 5]:
                    if op2 in (0x945c, 0x90ac) and any(
                            x in ('flowchart_play', 'scene_list_play', 'scene_play', 'flg_memory')
                            for x in s2 if x):
                        look_menu = True
                        break
            if op in BODY:
                if slots and slots[0]:
                    buf.append(clean(slots[0]))
                    stats['frag'] += 1
            elif op in TEXTGRP:
                t = grp_texts(slots)
                if t:
                    buf.extend(clean(x) for x in t)
                    stats['grp'] += 1
            elif op in CHOICE:
                flush()
                if slots and slots[0]:
                    lines.append(clean(slots[0]))
                    stats['opt'] += 1
            elif op in TITLE:
                # 0x27b0 有两用：① 章题卡（后接 bg/カット＋0x1f4）⇒ 收；
                # ② flowchart/scene-list 的节点标题（后接 flowchart_play / scene_list_play / scene_play / flg_memory）⇒ 菜单，不收
                if look_menu:
                    stats['title_menu'] = stats.get('title_menu', 0) + 1
                    continue
                flush()
                t = [x for x in slots if x and JP.search(x)]
                if t:
                    lines.append(clean(t[0]))
                    stats['title'] += 1
            elif op in CLICK:
                flush()
        flush()

    if dpath:
        de = dict_entries(dpath)
        lines.extend(de)
        stats['dict'] = len(de)

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as w:
        for ln in lines:
            w.write(ln + '\n')
    print(stats)
    print('lines', len(lines), 'chars', sum(len(x) for x in lines))


if __name__ == '__main__':
    main()
