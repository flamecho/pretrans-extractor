#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アーメン・ノワール ポータブル (PSP, Idea Factory / Design Factory 2012, ULJM06064)
剧本文本提取 —— 自包含。

【容器链路】
  ISO9660 -> PSP_GAME/USRDIR/UNION.CPK (CRI CPK v7, @UTF)
    -> 4304 条目；条目名 = 纯数字 ID
       STCM2L 脚本 = ID 3xxx（共 157 个）；ART2=图；6001=嵌套 CPK(音频 HCA)；1050=PNG 捆包
    -> 每条目多为 CRILAYLA 压缩（cpk.py 内置解压）

【STCM2L 结构（本作变体）】
  0x00  32B generator "STCM2L Oct  7 2010 17:55:27"
  0x20  u32 exports_offset（= 代码段终点；实测精确，其后 2.8KB 为 memory_init 导出表）
  0x50  "GLOBAL_DATA\0" ... "CODE_START_\0"  -> 代码起点 = CODE_START_ 偏移 + 24
  代码段 = opcode 链  [u32 size][payload(size-4)]
    payload = [若干 12B 「槽」][文本记录…][12B 收尾三元组 [0][cmd][flag]]
    槽 = [u32 值][0xff000000][0xff000000]；值为「该记录头在文件中的绝对地址」时 = 引用该记录
    文本记录 = [0][L/4][1][L][cp932 text][NUL pad]，L = align4(bytelen+1)
  收尾 cmd（= 语义）：
      0xd4 flag1 = 正文框（最多 3 槽，槽内多段**拼接** = 一个文本框）
      0xdf flag4 = 名札/单槽框（内容为角色名 → 丢弃；为 　　　缩进叙述 → 收）
      0xe7 flag2 = 选项（每条一个 op，连续若干条后跟一条 'select' op）
      0x34 flag2 = 'select' 选项组终止标记
      其余 cmd = 立绘/背景/音效/变量/wipe 等资源与系统指令（其记录多为资源名）
  一次点击 = 一个「正文框/单槽框/选项」op（同名札 op 不成行）。

【文件取舍】
  收：3101-3110 / 3201-3256 / 3300-3301 / 3501-3506 / 3601-3607（共 62 个，含实台词）
  弃：3000-3007（系统）、3100、3200、3400-3484（仅公共前导块，无台词）
  每个脚本开头都有一段**逐字节相同的公共前导块**（色変化判定 / 1sho-7sho / 1day-3day / wipe_* …）
  ⇒ 由内容规则（资源名表）整体滤除。

【人名】
  主角宏 `#Name[1]` -> **ナスカ**（vndb v4633 Protagonist，ナスカ）。
  独立名札行丢弃，不加前缀。

用法:
  python scripts/amennoir_extract.py <UNION.CPK 或 union_x 目录> <输出txt>
"""
import os
import sys
import io
import re
import struct
import glob

A4 = lambda n: (n + 3) & ~3
CMD_TEXT = 0xd4
CMD_NAME = 0xdf
CMD_OPT = 0xe7
CMD_SEL = 0x34

HERO = {1: 'ナスカ'}

# 原文侧缺陷：整行定值表（仅 2 处，脚本内该行确实缺收尾「」；勿用正则泛修）
FIX = {
    '「ハンター登録時１７歳、最終年齢１９歳契約ＣＡ【アンドロマリウス】':
        '「ハンター登録時１７歳、最終年齢１９歳契約ＣＡ【アンドロマリウス】」',
    '「それだけど、ナイヴスは多分賞金首じゃなくなると思う':
        '「それだけど、ナイヴスは多分賞金首じゃなくなると思う」',
    '「……どうにもなんねえのか、それ。そのネタ自体がブラフって可能性は？」」':
        '「……どうにもなんねえのか、それ。そのネタ自体がブラフって可能性は？」',
}

# ---- 资源/系统符号（引擎符号名，勿当正文） ----
SYM_EXACT = {
    '色変化判定', '処理開始', '処理開始\\n', '処理開始\n', 'select', 'switch', 'end',
    'savepoint', 'load', 'screen', 'dummy', 'suma', 'wipe', 'wipe_a', 'wipe_b',
    'makuai', 'title_start', 'game_start', 'common', 'continue',
}
SYM_PREFIX = (
    'bg', 'oboe', 'btl', 'battle', 'thread_cnt', 'file_cnt', 'flg_memory',
    'scene_play', 'konte', 'casm_', 'mevius', 'ash_a', 'nfs', 'nf-', 'fb-', 'fm-',
    'fs-', 'rb-', 'rm-', 'rs-', 'ab-', 'am-', 'as-', 'scr-', 'chr-', 'ev',
    'swd_', 'crm_', 'eru_', 'niv_', 'rai_', 'zec_', 'kow_', 'nor_',
)
SYM_RE = re.compile(r'^(?:[1-9]?(?:sho|day)|[0-9]+(?:sho|day))\d*$')
RE_ASCII = re.compile(r'^[\x20-\x7e]+$')
RE_PUA = re.compile(r'[\ue000-\uf8ff]')
RE_KANAKAN = re.compile(r'[ぁ-んァ-ヶ一-龯]')
RE_TEXTMARK = re.compile(r'[「『（(【]。]')
# 装饰性「无名札」占位（话者不明时的名称框内容，如 【――――】）
RE_DECOR_ONLY = re.compile(r'^[【】\[\]〔〕―—‐−─‐‐＝=＊*×・…\s\u3000]+$')

# 名札：短、无句读、无括号、无缩进
RE_NAME_OK = re.compile(r'^[ぁ-んァ-ヶー一-龯Ａ-Ｚａ-ｚ０-９？！]+$')
BAD_IN_NAME = '。、！？…「」『』（）()【】,.!?　 \u3000―—‐−─～〜'


def is_symbol(s):
    if not s:
        return True
    if RE_ASCII.match(s):
        return True
    if RE_PUA.search(s):
        return True
    if s in SYM_EXACT:
        return True
    low = s.lower()
    if any(low.startswith(p) for p in SYM_PREFIX):
        return True
    if SYM_RE.match(s):
        return True
    return False


def is_name(s):
    """名札判定：≤10 字、无句读/括号/缩进、结尾非助词。"""
    t = s.strip()
    if not t or len(t) > 10:
        return False
    if any(c in t for c in BAD_IN_NAME):
        return False
    if not RE_NAME_OK.match(t):
        return False
    if t[-1] in 'がをはにへとでもやのねよ':
        return False
    return True


def recs_of(pay, keep_empty=False):
    """payload 内の全部の文本记录を順に返す（槽の数も数えるので空記録も拾う）。"""
    out = []
    k, n = 0, len(pay)
    while k + 16 <= n:
        f0, f1, f2, f3 = struct.unpack_from('<4I', pay, k)
        if (f0 == 0 and f2 == 1 and 4 <= f3 <= 0x4000
                and f3 % 4 == 0 and f1 == f3 // 4 and k + 16 + f3 <= n):
            raw = pay[k + 16:k + 16 + f3].rstrip(b'\x00')
            if raw or keep_empty:
                try:
                    out.append(raw.decode('cp932'))
                except Exception:
                    pass
            k += 16 + f3
            continue
        k += 4
    return out


def parse_ops(b):
    """STCM2L -> [(op_off, cmd, flag, recs_all, recs_nonempty)]，到 exports_offset 为止。"""
    if b[:6] != b'STCM2L':
        return None
    ci = b.find(b'CODE_START_')
    if ci < 0:
        return None
    exp = struct.unpack_from('<I', b, 0x20)[0]
    end = min(exp, len(b)) if 0 < exp <= len(b) else len(b)
    i, ops = ci + 24, []
    while i + 4 <= end:
        bs = struct.unpack_from('<I', b, i)[0]
        if bs < 4 or i + bs > len(b):
            break
        pay = b[i + 4:i + bs]
        cmd = flag = None
        if len(pay) >= 12:
            t0, t1, t2 = struct.unpack_from('<3I', pay, len(pay) - 12)
            if t0 == 0 and t1 < 0x4000 and t2 < 16:
                cmd, flag = t1, t2
        allr = recs_of(pay, keep_empty=True)
        ops.append((i, cmd, flag, allr, [r for r in allr if r]))
        i += bs
    return ops


def clean(s):
    """样式标签去除 + 主角宏展开。"""
    s = re.sub(r'#Name\[(\d+)\]', lambda m: HERO.get(int(m.group(1)), m.group(0)), s)
    s = re.sub(r'#(?!Name\[)[A-Za-z_]+\[[^\]]*\]', '', s)
    return s


def extract_file(b):
    ops = parse_ops(b)
    if ops is None:
        return []
    n = len(ops)

    # 选项：每条 'select' 记录之前，紧邻的一串「恰好 1 槽」op 即为选项组
    kind = [''] * n
    for i, (off, cmd, flag, allr, rs) in enumerate(ops):
        if rs and rs[0] == 'select' and len(allr) == 1:
            kind[i] = 'sel'
            j = i - 1
            while j >= 0 and len(ops[j][3]) == 1 and ops[j][4]:
                if ops[j][1] == CMD_NAME or is_name(ops[j][4][0]):
                    break                       # 名札遇止（勿把说话人名当选项）
                kind[j] = 'opt'
                j -= 1

    lines = []
    for i, (off, cmd, flag, allr, rs) in enumerate(ops):
        if kind[i] == 'sel':
            continue
        if kind[i] == 'opt':
            t = clean(rs[0]).strip()
            if t and not is_symbol(t):
                lines.append(t)
            continue
        keep = [r for r in rs if not is_symbol(r)]
        if not keep:
            continue
        if len(keep) == 1 and RE_DECOR_ONLY.match(keep[0]):
            continue                        # 【――――】等装饰性无名札
        if len(allr) == 1:
            # 单槽框 = 名札 / 单槽叙述
            t = clean(keep[0]).strip()
            if is_name(t):
                continue                    # 角色名 -> 丢
            if not RE_KANAKAN.search(t):
                continue                    # 无假名/汉字 = 装饰性名札占位
        # 正文框：先剥样式标签，再按槽拼接（槽首尾缩进空白为显示用）
        txt = ''.join(clean(r).strip() for r in keep)
        if not RE_TEXTMARK.search(txt) and is_name(txt):
            continue
        t = txt.strip()
        if t:
            lines.append(FIX.get(t, t))
    return lines


def load_scripts(src):
    out = []
    if os.path.isdir(src):
        for f in sorted(os.listdir(src), key=lambda x: (len(x), x)):
            p = os.path.join(src, f)
            with open(p, 'rb') as fh:
                if fh.read(6) == b'STCM2L':
                    out.append((f, open(p, 'rb').read()))
    else:
        d = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, d)
        from cpk import CPK
        cpk = CPK(src)
        for e in sorted(cpk.entries, key=lambda e: e['offset']):
            b = cpk.raw(e)
            if b[:6] == b'STCM2L':
                out.append((e['name'], b))
    return out


# 有实台词的文件（其余为系统 / 公共前导块专用）
KEEP_IDS = set()
for lo, hi in ((3101, 3110), (3201, 3256), (3300, 3301), (3501, 3506), (3601, 3607)):
    KEEP_IDS |= set(range(lo, hi + 1))


def main():
    src, outpath = sys.argv[1], sys.argv[2]
    all_scripts = load_scripts(src)
    per, nfiles = [], 0
    for name, b in all_scripts:
        key = os.path.splitext(os.path.basename(name))[0]
        if key.isdigit() and int(key) not in KEEP_IDS:
            continue
        ls = extract_file(b)
        if ls:
            per.append((key, ls))
            nfiles += 1
    lines = []
    for key, ls in per:
        lines.extend(ls)
    with io.open(outpath, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('scripts=%d files_used=%d lines=%d -> %s' % (len(all_scripts), nfiles, len(lines), outpath))


if __name__ == '__main__':
    main()
