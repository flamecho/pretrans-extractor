#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""終遠のヴィルシュ -EpiClycoris- —— STCM2L(Switch/2018型) → 全文本。

链路：NSP → Program NCA(titlekey) → RomFS CONTENTS/STORY.cpk → SCRIPT/*.DAT（STCM2L）

记录（L1，头签名极强）：
  p-28 u32 size | p-24 u32 = p+4 | p-20 f32 2.0 | p-16 f32 2.0 |
  p-12 u32 kind(0xf5=本文 / 0x125=名前) | p-8 u32 0x11d |
  p     u32 0x10 | p+4 0 | p+8 L/4 | p+12 1 | p+16 L | p+20..p+20+L UTF-8
  文本记录之后 e=p+20+L：e+4 处 u32 = 0x1f4 ⇒ 等待点击（框结束）；0x14010 ⇒ 同框续行
"""
import struct, sys, glob, os, re, collections

SRC = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != 'survey' else '_w_W1_epic/story/SCRIPT'
OUT = '提取结果/[NS-JP]終遠のヴィルシュ -EpiClycoris-.txt'
KANA = re.compile(r'[\u3041-\u3096\u30a1-\u30fa\u4e00-\u9fff]')


def scan(d):
    """返回 [(kind, p, text, flag)]"""
    out = []
    L = len(d)
    p = 0x200
    while p < L - 0x40:
        if (struct.unpack_from('<I', d, p)[0] == 0x10
                and struct.unpack_from('<I', d, p + 4)[0] == 0
                and struct.unpack_from('<I', d, p + 12)[0] == 1
                and struct.unpack_from('<I', d, p - 8)[0] == 0x11d
                and struct.unpack_from('<I', d, p - 20)[0] == 0x40000000
                and struct.unpack_from('<I', d, p - 16)[0] == 0x40000000
                and struct.unpack_from('<I', d, p - 24)[0] == p + 4):
            n = struct.unpack_from('<I', d, p + 8)[0] * 4
            if n == struct.unpack_from('<I', d, p + 16)[0] and 4 <= n < 40000 and p + 20 + n + 8 <= L:
                try:
                    s = d[p + 20:p + 20 + n].rstrip(b'\x00').decode('utf-8')
                except UnicodeDecodeError:
                    s = None
                if s:
                    e = p + 20 + n
                    flag = struct.unpack_from('<I', d, e + 4)[0]
                    out.append((struct.unpack_from('<I', d, p - 12)[0], p, s, flag))
                    p = e + 8
                    continue
        p += 4
    return out


def survey():
    kinds = collections.Counter()
    flagged = collections.Counter()
    for f in sorted(glob.glob(SRC + '/*.DAT')):
        d = open(f, 'rb').read()
        for kind, p, s, flag in scan(d):
            kinds[kind] += 1
            flagged[(kind, flag)] += 1
    print('kind 分布', [(hex(k), v) for k, v in kinds.most_common(10)])
    print('kind×flag', [((hex(k), hex(f)), v) for (k, f), v in flagged.most_common(10)])


def clean(s):
    s = re.sub(r'#Ruby\[([^,\]]+)(?:,[^\]]*)?\]', lambda m: m.group(1), s)
    s = s.replace('#NAME[1]', NAME)
    s = s.replace('\u3000', '\u3000')
    return s.strip().strip('\u3000').strip()


NAME = 'セレス'
RUBY = re.compile(r'#Ruby\[([^,\]]+)(?:,[^\]]*)?\]')


# 名札类 kind（2026-10-27 实测本作有 8 种，互相不通用）：
#   0x120 'アドルフ' / 0x121 '？？？'·'国民Ａ' / 0x123 'イヴ' / 0x124 '笏木環' /
#   0x125 '？？？'·'近所の女' / 0x12b 'サロメ' / 0x12d '教会の管理者'·'#NAME[1]'
#   0x126 两用：'イヴ・シアン'（名札）/ 'sureNN'（标签）
# ★ 这些 kind 都还与其它用途混用（0x12d 也有 '05u_nml_a' 语音资源名、'end06_02'、'another'、'P'），
#   所以必须再过一道**串形态**过滤，不能只靠 kind。
NAMEK = {0x120, 0x121, 0x123, 0x124, 0x125, 0x126, 0x12b, 0x12d}
NOT_NAME_KIND = {0x122}                  # 'ＣＥＲＯ用' 分级审查标记（全角，形态过滤挡不住，单独排除）
RE_LABEL = re.compile(r'^(?:sure\d+|IF_\w*)$')
RE_ASCII = re.compile(r'^[0-9A-Za-z_]+$')

# 尾标记「同框续行」白名单（其余一律断框）：本作 kind=0xF5 的 flag 实测只有这 2 个值算续行。
# 断框值实测：0x1F4（等点击，40,584）／0x0A118（清屏，63）／0x1A9E4（5）／0x2C7（2）／
#             0x15A0C（1）／0x3B630（2）／0x6（2）—— 后几个小值后面也都跟名札或另一段正文。
CONT = {0x14010, 0x14030}


def is_name(kind, s):
    """名札判据：kind 在 NAMEK 内，且串既不是跳转标签/纯 ASCII（语音资源名 `05u_nml_a`）也不是单字符控制码。"""
    if kind in NOT_NAME_KIND or kind not in NAMEK or not s or len(s) <= 1:
        return False
    if RE_LABEL.match(s) or RE_ASCII.match(s):
        return False
    return not any(ord(c) < 0x20 for c in s)


def extract_file(path, out):
    """一框 = 一次点击。断框三判据（2026-10-27 补前两条）：
      ① `0x1f4`（等待点击）与 `0x0a118`（消息结束＝清屏，本作 63 处，其中 7 处后直接接正文——
         「（心声）」段末就是这个标记，旧版不认它，于是「（心声）＋旁白」并成一行）；
      ② **名札出现**（＝新消息开头）——旧版只 `continue` 不断框，导致 39 处「旁白＋（心声）」
         「旁白＋台词」被并成一行（实例 `1205.DAT` 405-410：旁白 2 段 → 名札 #NAME[1] → 心声 3 段）；
      ③ **台词接台词**（已累积内容以 `」` 收尾、下一条以 `「` 开头）——同一角色连说两句时中间没有名札，
         旧版靠交付后的后处理拆，现内置。
    """
    d = open(path, 'rb').read()
    box = []
    nbox = 0

    def flush():
        nonlocal nbox
        if box:
            out.append(''.join(box))
            box.clear()
            nbox += 1

    for kind, p, s, flag in scan(d):
        if is_name(kind, s):                    # ② 名札 ⇒ 断框（名字本身不收：有独立名字窗）
            flush()
            continue
        if kind in NAMEK:                       # 名札 kind 但被形态过滤（标签/语音名/控制码）⇒ 剔除
            continue
        if kind != 0xf5:
            continue
        t = clean(RUBY.sub(lambda m: m.group(1), s))
        if t:
            body = ''.join(box).rstrip()
            if box and t.startswith('「') and body.endswith('」'):   # ③ 台词接台词
                flush()
            box.append(t.lstrip('\u3000'))
        if flag not in CONT:                    # ① 非「同框续行」标记 ⇒ 一条消息结束（断框）
            flush()
    flush()
    return nbox


def main():
    files = sorted(glob.glob(SRC + '/*.DAT'))
    allout = []
    for f in files:
        n = extract_file(f, allout)
        print('%-12s %5d' % (os.path.basename(f), n))
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(allout) + '\n')
    print('总行 %d' % len(allout))
    print('->', OUT)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'survey':
        survey()
    else:
        main()
