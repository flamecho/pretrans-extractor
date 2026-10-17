# -*- coding: utf-8 -*-
"""ウィル・オ・ウィスプ ポータブル (PSP, ULJM05447, Design Factory & Otomate / Idea Factory) 剧本文本提取

容器链路
  ISO9660 -> PSP_GAME/USRDIR/UNION/SCRIPT.UNI            [CRI UNI2]
    UNI2 头 : "UNI2" + u32(0x10000) + u32 file_count(334) + u32 1 + u32 4
    FAT     : 0x800 起, 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
              绝对偏移 = startCluster * 0x800
    子文件  : [0x2000 前缀区/符号表][STCM2 脚本 @ +0x2000]   ← ★本作 PREFIX=0x2000（非同族前作的 0x1800）
              ★328/334 个子文件带 "STCM2 File Make By Minku 07.0"（余 6 个纯数据）
    STCM2 头: generator 32B ; "CODE_START_\0" 12B -> 代码段 = 该串偏移 + 24
  代码段 = opcode 链 [u32 size][payload]
    payload = [u32 self_addr][ [u32 v][0xff000000][0xff000000] ]*k   (k 个「槽」，12B/个)
              [ [u32 0][u32 L/4][u32 1][u32 L][cp932 text] ]*n
              [u32 0][u32 opcode][u32 flag]
    ★ 短形 op（无字符串）：size==16，payload = [u32 0][u32 opcode][u32 flag]

  ★★ 本作 opcode 语义（**与 DCGS/アルコバレーノ 的「槽数判型」完全不同** ⇒ 逐作实测）：
    slots(槽数) <= 1 且 cmd ∈ TEXT_CMDS  -> 上屏文本（一行）
       cmd==0xd2(210)  ⇒ **追加**（同一文本框继续）
       其它 TEXT_CMDS  ⇒ 追加后**文本框结束（＝一次点击）**
    ★★ cmd==0xd4(212) = **名札セット**：紧随其后的那条文本记录 = 说话人名 ⇒ 丢弃（不加前缀）
          （该 op 有 slots=0/1/2/4/5/6/8 多种形态 ⇒ **只看 opcode，不看槽数**）
       cmd∈{0xe6,0xe7}(230/231) slots==2 -> 选项（一行一条）
       cmd∈{0xe6,0xe7} slots<=1          -> 选择支前引导文（并入当前文本框后结束该框）
    slots>=2 的其它记录 = 资源名/旗标/符号表（bg52・flg_memory・ep_chara_d・ウィル…）⇒ 不收
       ★例外：slots==2 & cmd==0xf5(245) 的**非 ASCII** 串 = 章题/日付卡（`第１章　１日目`）⇒ 收
    cmd==0x33(51) 的 `処理開始` = 制作/系统注记 ⇒ 按值丢弃

主角名: #Name[1] -> ハンナ（默认名／符号表 SCRIPT.UNI @0x8220；vndb v1919 c4728 Hanna，Nameable）
  ★本作主角名插入宏**只有 `#Name[1]`**（无 #Name[2]，非「姓/名」双槽）
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_work_willo/PSP_GAME/USRDIR/UNION/SCRIPT.UNI')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PSP-JP]ウィル・オ・ウィスプ ポータブル_全文本.txt')
FAT, PREFIX = 0x800, 0x2000
NAME_MAGIC = (b'STCM2L', b'STCM2 ')

CMD_NAME = 0xd4                              # 名札セット
CMD_APPEND = 0xd2                            # 正文・追加（同框继续）
TEXT_CMDS = {0xd2, 0xd3, 0x34, 0x01, 0x33, 0xdd, 0x3f, 0xa9, 0x9a, 0xab, 0x35, 0x13}
OPT_CMDS = {0xe6, 0xe7}
CHAP_CMD, CHAP_SLOTS = 0xf5, 2               # 章题/日付卡

RENAME = {'#Name[1]': 'ハンナ'}
STYLE = re.compile(r'#(?:Color|Scale|Pos|Kana)\[[^\]]*\]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e]+$')
PUA = re.compile(r'[\ue000-\uf8ff\uff61-\uff9f\ufffd]')
DROP = [re.compile(r'^処理開始')]             # 制作/系统注记
# ★ 整行定值表（不改写原文；仅补原脚本脱落的一个收尾引号。§00b⑧「属笔误用整行定值表修」）
_L = ('「君が私のものだという証は、いくつあっても足りはしない。その肌に残す刻印も、指輪も、'
      'すべてそのためのものなのだから……')
FIX = {_L: _L + '」'}


def dropped(t):
    return any(r.match(t) for r in DROP)


def load_fat(d):
    n = struct.unpack_from('<I', d, 8)[0]
    ents = []
    for i in range(n):
        fid, sc, scl, sb = struct.unpack_from('<IIII', d, FAT + 16 * i)
        if sb:
            ents.append((fid, sc * 0x800, sb))
    return ents


def parse_op(pay):
    """-> (cmd, flag, slots, [str,...]) ；无法解析返回 None"""
    m = len(pay)
    if m < 12:
        return None
    if m == 12:                                   # 短形: [0][opcode][flag]
        if pay[:4] != b'\x00\x00\x00\x00':
            return None
        return struct.unpack_from('<I', pay, 4)[0], struct.unpack_from('<I', pay, 8)[0], 0, []
    if pay[m - 12:m - 8] != b'\x00\x00\x00\x00':
        return None
    cmd, flag = struct.unpack_from('<II', pay, m - 8)
    slots = 0
    while slots * 12 + 12 <= m - 12:
        v, a, b = struct.unpack_from('<III', pay, slots * 12)
        if a == 0xff000000 and b == 0xff000000:
            slots += 1
        else:
            break
    res, i = [], slots * 12
    while i + 16 <= m - 12:
        if pay[i:i + 4] == b'\x00\x00\x00\x00':
            nn, one, L = struct.unpack_from('<III', pay, i + 4)
            if one == 1 and 4 <= L <= 0x2000 and L % 4 == 0 and nn == L // 4 and i + 16 + L <= m - 12:
                raw = pay[i + 16:i + 16 + L].rstrip(b'\x00')
                s = None
                if raw and not any(b >= 0xfd for b in raw):     # cp932 合法字节仅 0x00-0xFC
                    try:
                        s = raw.decode('cp932')
                    except Exception:
                        s = None
                    if s and ('\ufffd' in s or any(ord(c) < 0x20 for c in s) or PUA.search(s)):
                        s = None
                if s:
                    res.append(s)
                i += 16 + L
                continue
        i += 4
    return cmd, flag, slots, res


def iter_ops(d, fs, fe):
    c = d.find(b'CODE_START_\0', fs + PREFIX, fe)
    if c < 0:
        return
    i = c + 24
    while i + 4 <= fe:
        bs = struct.unpack_from('<I', d, i)[0]
        if bs == 0 or bs % 4 or i + bs > fe:
            break
        yield d[i + 4:i + bs]
        i += bs


def clean(s):
    s = STYLE.sub('', s)
    for k, v in RENAME.items():
        s = s.replace(k, v)
    return s.replace('#n', '').strip()


def keep(s):
    """显示用串：空 / 纯 ASCII 资源名（非 `#` 宏）/ 制作注记 ⇒ 丢"""
    return bool(s) and (not ASCII_ONLY.match(s) or s.startswith('#')) and not dropped(s)


def cont(r):
    """该 op 能否让当前文本框继续（= 属于同一文本框的后续文本）"""
    return r is not None and r[2] <= 1 and (r[0] in TEXT_CMDS or r[0] in OPT_CMDS)


def walk(d, ents, fend, lines, st, names, nset, collect_only=False):
    """collect_only=True：只收集 0xd4 标记的名札（第 1 趟）；
       False：正式成行，并用已收集的名札集做兜底（第 2 趟）。"""
    for fid, fs, sb in sorted(ents, key=lambda e: e[0]):
        if d[fs + PREFIX:fs + PREFIX + 6] not in NAME_MAGIC:
            continue
        ops = [parse_op(pay) for pay in iter_ops(d, fs, fend(fs))]
        box, nameset = [], False
        for j, r in enumerate(ops):
            if not r:
                continue
            cmd, flag, slots, res = r
            nxt = ops[j + 1] if j + 1 < len(ops) else None

            if cmd == CMD_NAME:                              # 名札セット
                nameset = True
                continue

            if slots <= 1 and cmd in TEXT_CMDS:              # 上屏文本
                s = clean(''.join(res))
                # 说话人名 ⇒ 丢弃。判据 ①「前一 op 是 0xd4」为主；
                # ★②兜底：全库有 1 处（fid135）名札**漏了 0xd4 标记** ⇒ 用「已由 0xd4 精确
                #   建立的名札集」在「文本框首位」做确定性匹配（非猜测；第 1 趟集合为空 ⇒ 不生效）。
                if nameset or (not collect_only and not box and s and s in nset):
                    nameset = False
                    if s:
                        names[s] += 1
                    st['name'] += 1
                    continue
                if collect_only:
                    continue
                if keep(s):
                    box.append(s)
                # 框结束判据：本记录非「追加」(0xd2) ⇒ 结束；本记录是 0xd2 但下一记录不是
                # 可续接文本（文本/选项引导文）⇒ 也结束（防控制 op 处误并）
                if cmd != CMD_APPEND or not cont(nxt):
                    t = clean(''.join(box))
                    box = []
                    if keep(t):
                        lines.append(t)
                        st['text'] += 1
                continue

            if cmd in OPT_CMDS:
                if slots <= 1:                               # 選択肢前の導入文
                    t = clean(''.join(res))
                    if keep(t):
                        box.append(t)
                    t = clean(''.join(box))
                    box = []
                    if keep(t):
                        lines.append(t)
                        st['text'] += 1
                    continue
                if slots == 2:                               # 选项
                    t = clean(''.join(res))
                    if keep(t):
                        lines.append(t)
                        st['opt'] += 1
                    continue

            if slots == CHAP_SLOTS and cmd == CHAP_CMD:      # 章题/日付卡
                t = clean(''.join(res))
                if keep(t):
                    tt = clean(''.join(box))
                    box = []
                    if keep(tt):
                        lines.append(tt)
                        st['text'] += 1
                    lines.append(t)
                    st['chap'] += 1
                continue
            # 其它 op：不影响文本框
        t = clean(''.join(box))
        if keep(t):
            lines.append(t)
            st['text'] += 1


def main():
    d = open(SRC, 'rb').read()
    ents = load_fat(d)
    starts = sorted(e[1] for e in ents) + [len(d)]

    def fend(fs):
        return next(s for s in starts if s > fs) + PREFIX

    # 第 1 趟：只由 0xd4 精确建立名札集（不产出）
    p1 = collections.Counter()
    walk(d, ents, fend, [], collections.Counter(), p1, set(), collect_only=True)
    nset = set(p1)
    # 第 2 趟：正式成行（名札集作兜底）
    lines, st, names = [], collections.Counter(), collections.Counter()
    walk(d, ents, fend, lines, st, names, nset, collect_only=False)

    out = [l.strip() for l in lines]
    out = [FIX.get(l, l) for l in out]
    out = [l for l in out if l]
    print('stats: %s' % dict(st), file=sys.stderr)
    print('名札 %d 種' % len(names), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    rp = os.path.join(os.path.dirname(OUT), '解析报告')
    os.makedirs(rp, exist_ok=True)
    with open(os.path.join(rp, '_willowisp_names.txt'), 'w', encoding='utf-8') as f:
        for k, v in names.most_common():
            f.write(f'{v}\t{k}\n')
    print('->', OUT, '| lines', len(out), file=sys.stderr)


if __name__ == '__main__':
    main()
