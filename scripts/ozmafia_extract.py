#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OZMAFIA!! -vivace-（Nintendo Switch, 01002BE0118AE000, HuneX「Ogre」系 Switch 变体）
====================================================================================
全文本提取器：一次点击 = 一个文本框 = 一行。

链路：
  RAR(密码 otoame) → XCI → hactool → NCA → RomFS → allscr.mrg → MZX0 → 脚本

allscr.mrg = 自包含 mrgd00 容器（count=750）：
  [0] 脚本名表（32B/条，747 名）  [1] scr_adr.mrg（地址表）  [2] 颜色小表
  [3..749] 747 个脚本本体（MZX0 压缩）
  descriptor(8B, u16×4)：off = 8+count*8 + so*0x800 + of；size = (su-1)//0x20*0x10000 + sz
  names[i] ↔ member[3+i]

指令（';' 分隔，`_CMD(args)`；各指令右闭括号数不等 → 按 ';' 切分后逐条 rstrip(')')）：
  _ZM<6hex>(正文)   一次点击 = 一个文本框（本作无 @n 续框体系，除下列 6 处）
  _MSAD(正文)       @n 续框（6 处；与前一 _ZM 的 @n 配对 ⇒ 合并成一行）
  _SELZ(_标签,idx,选项1,选项2,…)  选项（一行一条）
  _LVSV(章題)       章节标题（直接上屏；MAPSEL/分岐处也用于标签）
  _MTLK(1,名前)     说话人名札（规范：不输出）
  _LVSO(char_idx,线路标签)  存档/章选择菜单标签（系统元数据 ⇒ 不收）
正文控制码：`^` = 框内软换行（合并/删）；`@n` = 框内暂停（删）；`<基底語,読み>` = 注音（取基底语）。
主角宏：`＊Ａ` = 女主角（默认 フーカ，可改名）；`＊Ｂ` = ドリアン・グレイ（可改名）。

排除：系统・UI（0xx/1xx/2xx_*、MAIN_START/SUB_SCRIPT/SCENARIO_START/テンプレ/TEST_*）、
      *_BUNKI_*（分岐调度，0 正文）、MAPSEL_START*（地图选择菜单）、REP01..REP98/REPLAY_END（回想，0 正文）。
另：同目录 script_text.mrg = 「魔法使いの夜」他作遗留文本 ⇒ 整体排除（见报告）。

用法：python scripts/ozmafia_extract.py <romfs 目录> <输出.txt>
"""
import struct, io, re, os, sys, unicodedata

HERO_NAME = 'フーカ'          # ＊Ａ（eboot 名字输入初始值表 第 1 槽）
HERO_ALIAS = 'ドリアン'        # ＊Ｂ（同表 第 2 槽；★ 不是「ドリアン・グレイ」——
#   W_018A_ORG 里 24 处字面「ドリアン・グレイ」全在改名事件之前(@524–7047)、5 处 ＊Ｂ 全在其后(@7943–8434)，
#   即 ＊Ｂ＝玩家在 002_ドリアン名称設定 里输入的新名（默认「ドリアン」）；见报告 §3）

EXCLUDE_EXACT = {'MAIN_START', 'SUB_SCRIPT', 'TEST_SCRIPT', 'TEST_0424', 'SCENARIO_START',
                 'REPLAY_END'}
EXCLUDE_SUBSTR = ('BUNKI', '初回起動時設定', '主人公名称設定', 'ドリアン名称設定',
                  'フラグ判定用関数群', 'タイトルコール', 'テンプレ')
EXCLUDE_PREFIX = ('MAPSEL_START', 'REP')
# 系统・UI 提示（名字输入校验），非正文 ⇒ 丢弃（整行定值表）
EXCLUDE_LINE = {'ドロシー以外の名前を入力してください。'}

CMD_RE = re.compile(r'_([A-Za-z][A-Za-z0-9]*)\(')
ZM_RE = re.compile(r'^_ZM[0-9a-fA-F]{6}\(')
IF_RE = re.compile(r'^_IF__\(([^)]*)\)')
ZY_RE = re.compile(r'_ZY[0-9a-fA-F]*\(([^)]*)\)')
HANKAKU = re.compile(r'[\uff61-\uff9f]+')
RUBY = re.compile(r'<([^<>]*),[\u3040-\u309f\u30a0-\u30ffー]+>')
# 原文笔误：ruby 开括号 < 被写作 _ （全库仅 1 处）→ 整行定值表
FIX_EXACT = {'_睫毛,まつげを震わせ、ゆっくりと瞼,まぶたを開ける。':
             '睫毛を震わせ、ゆっくりと瞼,まぶたを開ける。'}


def mzx0_decompress(data, inlen, exlen, xorff=True):
    """HuneX MZX0（LZ77 变体）解压；xorff=True 时字面字节 XOR 0xFF。"""
    key = 0xFF
    out = bytearray()
    ring = [b'\xFF\xFF'] * 64 if xorff else [b'\x00\x00'] * 64
    rw = 0
    f = io.BytesIO(data)
    cl = 0
    last = b'\xFF\xFF' if xorff else b'\x00\x00'
    while len(out) < exlen:
        if f.tell() >= inlen:
            break
        if cl <= 0:
            cl = 0x1000
            last = b'\xFF\xFF' if xorff else b'\x00\x00'
        fl = f.read(1)[0]
        cl -= 1 if (fl & 3) == 2 else fl // 4 + 1
        if (fl & 3) == 0:
            out += last * ((fl // 4) + 1)
        elif (fl & 3) == 1:
            k = 2 * (f.read(1)[0] + 1)
            for _ in range(fl // 4 + 1):
                last = bytes(out[len(out) - k:len(out) - k + 2]); out += last
        elif (fl & 3) == 2:
            last = ring[fl // 4]; out += last
        else:
            for _ in range(fl // 4 + 1):
                b = f.read(2)
                if xorff:
                    b = bytes(x ^ key for x in b)
                last = bytes(b); ring[rw] = last; rw = (rw + 1) % 64; out += last
    del out[exlen:]
    return bytes(out)


def mrgd00_members(blob):
    assert blob[:6] == b'mrgd00', 'not mrgd00'
    cnt = struct.unpack('<H', blob[6:8])[0]
    base = 8 + cnt * 8
    out = []
    for i in range(cnt):
        so, of, su, sz = struct.unpack('<HHHH', blob[8 + i * 8:16 + i * 8])
        off = base + so * 0x800 + of
        size = (su - 1) // 0x20 * 0x10000 + sz if su else sz
        out.append(blob[off:off + size])
    return cnt, out


def load_scripts(allscr_path):
    blob = open(allscr_path, 'rb').read()
    cnt, members = mrgd00_members(blob)
    nam = members[0]
    names = [nam[i:i + 32][:30].rstrip(b'\x00').decode('cp932', 'replace')
             for i in range(0, len(nam) - 31, 32)]
    names = [n for n in names if n.strip()]
    out = []
    for i, nm in enumerate(names):
        b = members[3 + i]
        if b[:4] == b'MZX0':
            ex = struct.unpack('<L', b[4:8])[0]
            raw = mzx0_decompress(b[8:], len(b) - 8, ex)
        else:
            raw = b
        out.append((nm, raw.decode('cp932', 'replace')))
    return out


def norm_compat(t):
    if not any(0xFA00 <= ord(c) <= 0xFAFF or 0x2F800 <= ord(c) <= 0x2FA1F for c in t):
        return t
    return ''.join(unicodedata.normalize('NFKC', c)
                   if (0xFA00 <= ord(c) <= 0xFAFF or 0x2F800 <= ord(c) <= 0x2FA1F) else c
                   for c in t)


def fix_text(t):
    """正文清洗：注音取基底语、半角假名/标点归全角、宏替换、框内换行合并、@n 删。"""
    for k, v in FIX_EXACT.items():
        t = t.replace(k, v)
    t = RUBY.sub(r'\1', t)
    t = HANKAKU.sub(lambda m: unicodedata.normalize('NFKC', m.group(0)), t)  # 半角→全角
    t = t.replace('＊Ａ', HERO_NAME).replace('＊Ｂ', HERO_ALIAS)
    t = t.replace('^', '')     # 框内软换行 → 合并
    t = t.replace('@n', '')    # 框内暂停 → 删（与 _MSAD 合并）
    return norm_compat(t)


def guard_skip_set(stmts):
    """守卫块 `_IF__(VAR,op,val,LABEL) … _ZY<id>(LABEL)`：相邻、同变量、条件互斥
    （如 G241 eq 0 / eq 1 —— 同文本仅语音不同）⇒ 只留第一支，其余支的正文跳过。"""
    groups = []
    for i, st in enumerate(stmts):
        m = IF_RE.match(st)
        if not m:
            continue
        a = m.group(1).split(',')
        if len(a) < 4:
            continue
        var, op, val, lbl = a[0], a[1], a[2], a[3]
        for k in range(i + 1, min(i + 400, len(stmts))):
            z = ZY_RE.search(stmts[k])
            if z and z.group(1) == lbl:
                groups.append((i, k, var, op, val))
                break
    skip = set()
    g = 0
    while g < len(groups):
        run = [groups[g]]
        while (g + 1 < len(groups) and groups[g + 1][0] == groups[g][1] + 1
               and groups[g + 1][2] == groups[g][2]):
            g += 1
            run.append(groups[g])
        # 成对折叠（if-else 两支）：run = [eq0, eq1, eq0, eq1, …] ⇒ 每对只留第一支
        for k in range(0, len(run) - 1, 2):
            a, b = run[k], run[k + 1]
            if (a[3], a[4]) != (b[3], b[4]):        # 条件互斥才是备选
                skip.update(range(b[0] + 1, b[1]))
        g += 1
    return skip


def is_excluded(name):
    if name in EXCLUDE_EXACT:
        return True
    if any(s in name for s in EXCLUDE_SUBSTR):
        return True
    if any(name.startswith(p) for p in EXCLUDE_PREFIX):
        return True
    return False


def split_stmts(script):
    """按 ';' 切分为语句（各指令右闭括号数不等 ⇒ 逐条 rstrip(')') 取参数）。"""
    return script.split(';')


def stmt_events(st):
    """单条语句 → [('line'|'msad'|'opt'|'title', text)]。"""
    ev = []
    for m in CMD_RE.finditer(st):
        name = m.group(1)
        arg = st[m.end():].rstrip(')')
        if ZM_RE.match(st[m.start():]):
            t = fix_text(arg)
            if t.strip():
                ev.append(('line', t))
        elif name == 'MSAD':
            t = fix_text(arg)
            if t.strip():
                ev.append(('msad', t))
        elif name in ('SELZ', 'SELD'):
            parts = arg.split(',')
            if len(parts) >= 3:
                for o in parts[2:]:
                    o = fix_text(o)
                    if o.strip():
                        ev.append(('opt', o))
        elif name == 'LVSV':
            t = fix_text(arg)
            if t.strip():
                ev.append(('title', t))
    return ev


def guard_skip_set(stmts, evs):
    """守卫块 `_IF__(VAR,op,val,LABEL) … _ZY<id>(LABEL)`：
    同一变量的 if/else 备选支（G241 eq0/eq1 —— 同文本、仅语音/立绘不同）⇒ 只留第一支。
    仅当两支正文**完全相同**才折叠（有差异则两支都保留，宁多勿失）。"""
    groups = []
    for i, st in enumerate(stmts):
        m = IF_RE.match(st)
        if not m:
            continue
        a = m.group(1).split(',')
        if len(a) < 4:
            continue
        var, op, val, lbl = a[0], a[1], a[2], a[3]
        for k in range(i + 1, min(i + 400, len(stmts))):
            z = ZY_RE.search(stmts[k])
            if z and z.group(1) == lbl:
                groups.append((i, k, var, op, val))
                break

    def body(a, b):
        return [x for k in range(a + 1, b) for x in evs[k] if x[0] != 'msad']

    skip = set()
    g = 0
    while g < len(groups):
        run = [groups[g]]
        while (g + 1 < len(groups) and groups[g + 1][2] == run[-1][2]
               and not any(evs[k] for k in range(run[-1][1] + 1, groups[g + 1][0]))):
            g += 1
            run.append(groups[g])
        for k in range(0, len(run) - 1, 2):
            a, b = run[k], run[k + 1]
            if (a[3], a[4]) == (b[3], b[4]):
                continue
            ta, tb = body(*a[:2]), body(*b[:2])
            if tb and ta == tb:
                skip.update(range(b[0] + 1, b[1]))
        g += 1
    return skip


def extract_script(script):
    """→ [(kind, text)] kind ∈ {'line','opt','title'}，按出现顺序。"""
    stmts = split_stmts(script)
    evs = [stmt_events(st) for st in stmts]
    skip = guard_skip_set(stmts, evs)
    out = []
    for si, ev in enumerate(evs):
        if si in skip:
            continue
        for kind, t in ev:
            if kind == 'msad':
                if out and out[-1][0] == 'line':
                    out[-1] = ('line', out[-1][1] + t)
                else:
                    out.append(('line', t))
            else:
                out.append((kind, t))
    return out


def main():
    romfs, outpath = sys.argv[1], sys.argv[2]
    scripts = load_scripts(os.path.join(romfs, 'allscr.mrg'))
    lines = []
    nline = nopt = ntitle = 0
    for nm, body in scripts:
        if is_excluded(nm):
            continue
        for kind, t in extract_script(body):
            if t in EXCLUDE_LINE:
                continue
            lines.append(t)
            if kind == 'line':
                nline += 1
            elif kind == 'opt':
                nopt += 1
            else:
                ntitle += 1
    with open(outpath, 'w', encoding='utf-8-sig', newline='') as f:
        f.write('\n'.join(lines) + '\n')
    print('lines=%d (正文 %d / 选项 %d / 章題 %d)  scripts=%d' %
          (len(lines), nline, nopt, ntitle, len(scripts)))


if __name__ == '__main__':
    main()
