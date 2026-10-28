# -*- coding: utf-8 -*-
"""桜蘭高校ホスト部 (PS2-JP, SLPM-667.38 / Otomate·Idea Factory 2006) 剧本文本提取

容器链路
  ISO9660 -> UNION/SCRIPT.UNI                    [CRI UNI2]
    "UNI2" + u32(0x10000) + u32 nfiles(118) + u32 1 + u32 2
    FAT : 0x800 起 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
          绝对偏移 = 0x1000 + startCluster*0x800   (0x1000 起为数据区)
    子文件 : "STCM2 File Make By Minku 07.0" 起；"CODE_START_\\0" 后 24 字节 = 代码段
  代码段 = op 链 [u32 size][payload(size-4)]
    文本 op: payload = [u32 addr][ff000000][ff000000][0][L/4][1][L][cp932 text(L 含 4B 对齐填充)]
                       [0][cmd][flag]      (28 + L + 12 == len(payload))
    cmd(显示类)：
      0xd2       同一文本框内软换行（不点击）——实测 96% 段末落在词中，且名札亦用此码
      0xd3       框末（一次点击）
      0x34 0x35 0xdc 0xdd   框末变体（同样一次点击，语义差异不影响行界）
      0xe7 0xe6  选项：0xe7 为「问句末段 + 前 N-1 条选项」，0xe6 为最后一条选项
    非显示类（不收）：0x33/0x66/0x5/0x7a/0x96/0x98/0xa9/0x82/0x13/0x3d/0x6e… 资源名・
                     变量名・名札表・章题常量

成行
  一次点击 = 一行：0xd2 合并，其余显示码 flush。
  名札：短串（无句读/引号，<=10 字）且**下一记录以「（『 开头** ⇒ 独立名字窗，丢该行、不加前缀。
  资源名（纯 ASCII）与空占位丢弃。
"""
import struct
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys
import json
import collections

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.environ.get('OURAN_SRC', os.path.join(HOME, '_work_ouran', 'iso', 'UNION', 'SCRIPT.UNI'))
OUT = os.path.join(HOME, '提取结果', '[PS2-JP]桜蘭高校ホスト部.txt')

CONT = 0xd2                       # 框内软换行
END_CMDS = {0xd3, 0xd4, 0x34, 0x35, 0xdc, 0xdd}   # 框末（一次点击）
OPT_CMDS = {0xe6, 0xe7}

MACRO = re.compile(r'#?(?:Color|Scale|Pos|Speed|Kana|Font|Wait|Voice|Name)\[[^\]]*\]')
QUOTE_HEAD = '「（『'
NAME_BAN = '。、…！？「」『』（）'
# 资源标签：纯 ASCII 串，或 `ed_環` 这类「英文前缀＋日文」的结局/立绘标签
RE_RES = re.compile(r'^(?:[A-Za-z0-9_./\\:\[\]#&\-]+|[a-z]{1,4}_[^\x00-\x7f]+)$')

# 系统/管理画面标签（不渲染为剧情文本；'グラフキャラ' 等若不过滤会并入台词）
UI_LABEL = {
    'グラフキャラ', 'グラフ経過', 'ハルヒ指名率', '行動機嫌タイプ', '行動機嫌値',
    '経過日数', '行動グループ', 'タッチグループ', '警告フラグ', '行動選択結果',
    '接客回避', '表示位置', 'キャラtemp', '左キャラ', '右キャラ', '中央キャラ',
    '音楽室キャラ',
}

# 章題・エピローグ題＝上屏扉文（cmd 不一：0x3d/0x6e/0x13/0xf5/0x12a/0xa9 都有）
BANK_FILES = (7, 9, 10, 17)      # 接客メッセージバンク（データ子文件）
CHAP = re.compile(r'^(?:第[０-９0-9]+話|エピローグ|プロローグ)(?:[\u3000 ].*)?$')


def load():
    b = open(SRC, 'rb').read()
    n = struct.unpack_from('<I', b, 8)[0]
    files = [struct.unpack_from('<4I', b, 0x800 + i * 16) for i in range(n)]
    return b, files


def parse_file(b, base, size):
    """返回该子文件的显示文本记录 [(off, text, cmd)]（含非文本过滤前的原文）"""
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
        pay = b[p + 4:p + L]
        if len(pay) >= 40:
            # 定位串描述符 [0][L/4][1][L]；整条 op 只允许**一个**描述符（多描述符＝立绘/事件指令）
            descs = []
            for j in range(12, len(pay) - 15, 4):
                a, c, d, e = struct.unpack_from('<4I', pay, j)
                if a == 0 and d == 1 and c * 4 == e and 0 < e <= len(pay) - j - 16:
                    descs.append((j, e))
            if len(descs) == 1 and descs[0][0] + 16 + descs[0][1] + 12 == len(pay):
                j, e = descs[0]
                cmd, flag = struct.unpack_from('<2I', pay, len(pay) - 8)
                raw = pay[j + 16:j + 16 + e].rstrip(b'\x00')
                try:
                    t = raw.decode('cp932')
                except UnicodeDecodeError:
                    t = raw.decode('cp932', 'replace')
                if (cmd in END_CMDS or cmd == CONT or cmd in OPT_CMDS or cmd == 0x33
                        or CHAP.match(t)):
                    out.append((p, t, cmd, flag))
        p += L
    return out


def main():
    b, files = load()
    lines = []
    stats = collections.Counter()

    # ── pass 1：名札表（结构与词频双证）──────────────────────────────
    # 名札＝短串（<=10 字、无句读引号），且「跳过同名重复」后的下一段以「（『 开头。
    # 按出现次数统计命中率 ≥0.9 者入 NAMES；与上下文无关地整串丢弃（同一名字有时
    # 后接旁白而非引号，仅靠逐处判据会漏 26 行）。
    seen = collections.Counter()
    quoted = collections.Counter()
    per_file = []
    for idx in range(len(files)):
        fid, st, sz, szb = files[idx]
        recs = parse_file(b, 0x1000 + st * 0x800, szb)
        per_file.append(recs)
        for k, (off, text, cmd, flag) in enumerate(recs):
            t = MACRO.sub('', text)
            if cmd not in (CONT, 0xd4) or len(t) > 10 or any(ch in t for ch in NAME_BAN):
                continue
            if not t.strip() or RE_RES.match(t):
                continue
            seen[t] += 1
            j = k + 1
            while j < len(recs) and MACRO.sub('', recs[j][1]) == t:
                j += 1
            if j < len(recs) and MACRO.sub('', recs[j][1])[:1] in QUOTE_HEAD:
                quoted[t] += 1
    NAMES = {t for t, c in seen.items() if quoted[t] / c >= 0.9}
    NAMES.add('？？？')          # 未公开说话人（名字窗显示 ？？？）
    chap_seen = set()

    for idx, recs in enumerate(per_file):
        box = []            # 当前框的各段
        skip_opt = False

        def name_at(k):
            t = MACRO.sub('', recs[k][1])
            if t in NAMES:
                return True
            off, t, cmd, flag = recs[k]
            t = MACRO.sub('', t)
            if cmd not in (CONT, 0xd4) or len(t) > 10 or any(ch in t for ch in NAME_BAN):
                return False
            j = k + 1
            while j < len(recs) and MACRO.sub('', recs[j][1]) == t:
                j += 1
            return j < len(recs) and MACRO.sub('', recs[j][1])[:1] in QUOTE_HEAD

        for k, (off, text, cmd, flag) in enumerate(recs):
            t = MACRO.sub('', text)
            stats['rec'] += 1
            if not t.strip() or RE_RES.match(t) or t in UI_LABEL:
                stats['res'] += 1
                continue
            if cmd in OPT_CMDS:
                # 系统确认框（是否跳过序章）＝系统 UI，整块剔除
                if 'スキップしますか' in t or skip_opt:
                    skip_opt = True
                    stats['sysopt'] += 1
                    if k + 1 >= len(recs) or recs[k + 1][2] not in OPT_CMDS:
                        skip_opt = False
                    continue
                # 选项块首条：若当前框已有内容 ⇒ 作为该框末段（问句）合并；否则自成一框
                is_first = not (k > 0 and recs[k - 1][2] in OPT_CMDS)
                if is_first:
                    box.append(t)
                    lines.append(''.join(box))
                    box = []
                else:
                    lines.append(t)
                stats['opt'] += 1
                continue
            if not box and name_at(k):
                stats['name'] += 1
                continue
            if cmd == 0x33:
                # 0x33＝另有语义的显示码（同一串无 d2/d3 副本 ⇒ 确为屏上文字）。
                # 连续 ≥2 条（名札表/双人名）不显示；单条按正文处理。
                run = (k > 0 and recs[k - 1][2] == 0x33) or (k + 1 < len(recs) and recs[k + 1][2] == 0x33)
                if run:
                    stats['t33run'] += 1
                    continue
                box.append(t)
                lines.append(''.join(box))
                box = []
                stats['t33'] += 1
                continue
            if CHAP.match(t):
                # 章題・エピローグ題＝上屏扉文；同串多处出现（常量副本）只留首见
                if box:
                    lines.append(''.join(box))
                    box = []
                if t not in chap_seen:
                    chap_seen.add(t)
                    lines.append(t)
                    stats['chap'] += 1
                continue
            box.append(t)
            if cmd in END_CMDS:
                lines.append(''.join(box))
                box = []
                stats['line'] += 1
        if box:
            lines.append(''.join(box))
            stats['line'] += 1
    # ── 接客メッセージバンク（数据子文件 7/9/10/17）────────────────
    # 固定 0x100B 槽：文字列＋`#n#n`（显示换行宏）＋0x00＋0xFF 填充。
    # 无脚本位置可推（由接客系统按编号取用）⇒ 按子文件、记录序并入末尾。
    # 每条消息 = 记录内「最后一个 cp932 日文连续串」（前面是 立ち絵/表情 的 ASCII 名）。
    bank_seen = set()
    for idx in BANK_FILES:
        fid, st, sz, szb = files[idx]
        seg = b[0x1000 + st * 0x800:][:szb]
        for m in re.finditer(rb'(?:(?:[\x81-\x84\x88-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc])|#n|#N)+', seg):
            try:
                t = m.group().decode('cp932').replace('#n', '')
            except UnicodeDecodeError:
                continue
            if '\ufffd' in t or not re.search(r'[\u3040-\u9fff]', t):
                continue
            if t.strip() and t not in bank_seen and t not in NAMES:
                bank_seen.add(t)
                lines.append(t)
                stats['bank'] += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(stats, 'lines', len(lines))


if __name__ == '__main__':
    main()
