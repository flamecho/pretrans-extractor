# -*- coding: utf-8 -*-
"""蜜×蜜ドロップス LOVE×LOVE HONEY LIFE (PS2-JP, SLPM-663.81 / Otomate·Design Factory 2006)

容器链路
  ISO9660 -> UNION/SCRIPT.UNI                    [CRI UNI2]
    "UNI2" + u32(0x10000) + u32 nfiles(59) + u32 1 + u32 2
    FAT : 0x800 起 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
          绝对偏移 = 0x1000 + startCluster*0x800   (0x1000 起为数据区)
    子文件 : "STCM2 File Make By Minku 07.0" 起；"CODE_START_\0" 后 24 字节 = 代码段
  代码段 = op 链 [u32 size][payload(size-4)]
    文本 op: payload = [u32 addr][ff000000][ff000000][0][L/4][1][L][cp932 text(L 含 4B 对齐填充)]
                       [0][cmd][flag]      (28 + L + 12 == len(payload))

  cmd(显示类，实测计数)：
    0x118       同一文本框内按框宽折行（不点击，21 字/行；长度 ±2 占 98.4%）—— 18,539 条
    0x119       框末（一次点击）             —— 17,922 条
    0x16a 0x16b 0x16c 0x108 0x1b8 0x17e 0x7 0x171 0x105  框末变体（同一次点击，后接控制不同）
    0x11b 0x11c 选项：0x11b 为「问句末段 + 前 N-1 条」，0x11c 为最后一条
  非显示类（不收）：0x14a/0x14b/0x12c/0x15f/0x136/0xe1/0x11a/0x14e（シーン名・イベント名，
    与 bg47_a/satuki 等资源名共用一个通道 ⇒ 是参数槽而非渲染）；0x1e6（好感度トースト）；
    0x18b/0x18c（移动地点播报）；0x0/0x6/0x11d/0x11e（switch/select 系统串）

成行
  一次点击 = 一行：0x118 合并（实测为按框宽折行，非语义断行 ⇒ 单版），其余显示码 flush。
  名札：0x118 短串（无句读引号，<=10 字）且下一记录以「（『 开头 ⇒ 独立名字窗，丢该行、不加前缀。
  行内宏：#Name[1] -> 姓 / #Name[2] -> 名（默认名表 file0 しらつめ＋くるみ；vndb 白詰 くるみ）。
"""
import struct
import os
import re
import collections

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get('MITSU_SRC', os.path.join(HOME, '_work_mitsu', 'x', 'UNION', 'SCRIPT.UNI'))
OUT = os.path.join(HOME, '提取结果', '[PS2-JP]蜜×蜜 ドロップス LOVE×LOVE HONEY LIFE.txt')

CONT = 0x118
# 框末（一次点击）：0x119 主用；其余为后接控制不同的变体
END_CMDS = {0x119, 0x16a, 0x16b, 0x16c, 0x108, 0x1b8, 0x17e, 0x7, 0x171, 0x105}
OPT_CMDS = {0x11b, 0x11c}

# 剧情子文件：101-125（各路线本篇）＋ 502（キャラ当てクイズ＝脚本イベント）
STORY_FIDS = set(range(101, 126)) | {502}

SURNAME, GIVEN = '白詰', 'くるみ'
MACRO_NAME1 = re.compile(r'#Name\[1\]')
MACRO_NAME2 = re.compile(r'#Name\[2\]')
MACRO = re.compile(r'#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]')

QUOTE_HEAD = '「（『'
NAME_BAN = '。、…！？「」『』（）'
RE_RES = re.compile(r'^[A-Za-z0-9_./\\:\[\]#&\-\s]+$')
# シーン名/イベント名（与 0x14a/0x14b 参数槽同名的字符串会混进显示通道）：
# 无引号无句读、<=20 字、以编号或「編」收尾 —— 如 `勉強嫌い４` `アプローチ／千駿編４`
RE_LABEL = re.compile(r'^[^「」『』。、…]{1,19}[０-９0-9編]$')
PUA = re.compile(r'[\ue000-\uf8ff]')
# `明日は…／茅架` 型：日程/担当キャラのラベル（短く、引号なし、全角斜線入り）
RE_SLASH_LABEL = re.compile(r'^[^「」『』]{1,12}／[^「」『』]{1,12}$')


def load():
    b = open(SRC, 'rb').read()
    n = struct.unpack_from('<I', b, 8)[0]
    files = [struct.unpack_from('<4I', b, 0x800 + i * 16) for i in range(n)]
    return b, files


def ops_of(b, base, size):
    end = base + size
    i = b.find(b'CODE_START_', base)
    if i < 0 or i > end:
        return []
    p = i + 24
    out = []
    while p + 4 <= end:
        L = struct.unpack_from('<I', b, p)[0]
        if L < 4 or p + L > end:
            break
        out.append(b[p+4:p+L])
        p += L
    return out


def text_of(pay):
    """单描述符文本 op -> (cmd, flag, text)；否则 None"""
    if len(pay) < 40:
        return None
    descs = []
    for j in range(12, len(pay) - 15, 4):
        a, c, d, e = struct.unpack_from('<4I', pay, j)
        if a == 0 and d == 1 and c * 4 == e and 0 < e <= len(pay) - j - 16:
            descs.append((j, e))
    if len(descs) != 1:
        return None
    j, e = descs[0]
    if j + 16 + e + 12 != len(pay):
        return None
    cmd, flag = struct.unpack_from('<2I', pay, len(pay) - 8)
    raw = pay[j+16:j+16+e].rstrip(b'\x00')
    try:
        t = raw.decode('cp932')
    except UnicodeDecodeError:
        return None
    return cmd, flag, t


def is_jp(t):
    return re.search(r'[ぁ-んァ-ヶ一-龯]', t) is not None


def main():
    b, files = load()
    per_file = []
    for fid, st, sz, szb in files:
        if fid in STORY_FIDS:
            base = 0x1000 + st * 0x800
            recs = []
            for pay in ops_of(b, base, szb):
                r = text_of(pay)
                if r and r[0] in END_CMDS | {CONT} | OPT_CMDS:
                    recs.append(r)
            per_file.append((fid, recs))

    # ── pass 1：名札（结构 + 词频双证）─────────────────────────────
    seen = collections.Counter()
    quoted = collections.Counter()
    for fid, recs in per_file:
        for k, (cmd, flag, text) in enumerate(recs):
            t = MACRO.sub('', text)
            if cmd != CONT or len(t) > 10 or any(ch in t for ch in NAME_BAN):
                continue
            if not t.strip() or RE_RES.match(t):
                continue
            seen[t] += 1
            j = k + 1
            while j < len(recs) and MACRO.sub('', recs[j][2]) == t:
                j += 1
            if j < len(recs) and MACRO.sub('', recs[j][2])[:1] in QUOTE_HEAD:
                quoted[t] += 1
    NAMES = {t for t, c in seen.items() if quoted[t] / c >= 0.9}
    NAMES.add('？？？')

    stats = collections.Counter()
    lines = []
    used_names = collections.Counter()

    def name_at(recs, k):
        t = MACRO.sub('', recs[k][2]).strip()
        if t == '' and '#Name' in recs[k][2]:
            return True                     # 纯 #Name 宏 ＝ 名札窗（主角名）
        if t in NAMES:
            return True
        if len(t) > 10 or any(ch in t for ch in NAME_BAN):
            return False
        j = k + 1
        while j < len(recs) and MACRO.sub('', recs[j][2]) == t:
            j += 1
        return j < len(recs) and MACRO.sub('', recs[j][2])[:1] in QUOTE_HEAD

    for fid, recs in per_file:
        box = []
        for k, (cmd, flag, text) in enumerate(recs):
            t = MACRO_NAME1.sub(SURNAME, text)
            t = MACRO_NAME2.sub(GIVEN, t)
            t = MACRO.sub('', t).strip('\x00')
            if PUA.search(t):
                stats['pua'] += 1
                continue
            if not t.strip() or RE_RES.match(t):
                stats['res'] += 1
                continue
            if cmd in OPT_CMDS:
                if cmd == 0x11b and not (k > 0 and recs[k - 1][0] in OPT_CMDS):
                    box.append(t)
                    lines.append(''.join(box))
                    box = []
                else:
                    if box:
                        lines.append(''.join(box))
                        box = []
                    lines.append(t)
                stats['opt'] += 1
                continue
            if not box and name_at(recs, k):
                used_names[t] += 1
                stats['name'] += 1
                continue
            if not box and (RE_LABEL.match(t) or RE_SLASH_LABEL.match(t)):
                stats['label'] += 1
                continue
            box.append(t)
            if cmd in END_CMDS:
                lines.append(''.join(box))
                box = []
                stats['line'] += 1
        if box:
            lines.append(''.join(box))
            stats['line'] += 1

    # 行内宏
    out = []
    for l in lines:
        l = MACRO.sub('', l)
        if l.strip():
            out.append(l)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print(stats, 'lines', len(out))
    print('NAMES', len(NAMES), sorted(NAMES)[:60])


if __name__ == '__main__':
    main()
