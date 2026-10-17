#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ガーネット・クレイドル ポータブル ～鍵の姫巫女～ (PSP, 2011 / STCM2L "Minku 07.0")
剧本文本提取 —— 自包含。

【容器链路】
  ISO9660 -> PSP_GAME/USRDIR/CPK/DATA0.CPK (CRI CPK, @UTF, 521 条目, 全部 STCM2L,
             条目名缺失 => 纯数字 ID; 每条 CRILAYLA 压缩)
  DATA1/2/3.CPK = 音频/图像/视频（无正文）

【STCM2L 结构（本作变体，与 アーメン・ノワール 同族但 code 不同）】
  0x00  32B generator "STCM2 File Make By Minku 07.0"
  0x20  u32 exports_offset（= 代码段终点）
  0x50  "GLOBAL_DATA\0" / "CODE_START_\0" -> 代码起点 = CODE_START_ 偏移 + 24
  代码段 = opcode 链 [u32 size][payload(size-4)]
    payload = [12B 槽 × k][文本记录 × m][12B 收尾三元组 [0][cmd][flag]]
    槽 = [u32 值][0xff000000][0xff000000]；值为「该记录头在文件中的绝对地址」；
         值高字节 0xff（0xff0000NN）= 立即数。
    文本记录 = [0][L/4][1][L][cp932 text][NUL pad]，L = align4(bytelen+1)
  cmd（收尾三元组中段）：
      0xd4 = 说话人框开始（带脸/表情参数；其后的 0xd2 文本 = 名札）
      0xd2 = 正文片段（续行）
      0xd3 = 正文片段 + 框末
      0xe7 = 框末变体（1 槽）/ 选项（2 槽）
      0xec = 选项（2 槽）
      0xe6 = 选项组终止
      0x33 + 记录 'select' = 选项组锚点
      其余 cmd = 立绘/背景/音效/变量/wipe 等资源指令（记录多为资源名）
  ★ 名札判据：0xd4 之后**紧跟**的那一个 0xd2 文本 op（全库 19,461 对，1:1 配对）
     名札丢弃、不加前缀；正文＝后续 0xd2/0xd3/0xe7 片段**直接拼接**（软换行，合并成一行）
  ★ 选项判据：**2 槽** + 1 记录 + cmd∈{0xe7,0xec}（全库 71 条 / 33 组），后跟 0xe6 + 'select'

用法:
  python scripts/garnet_extract.py <DATA0.CPK 或已解包目录> <输出txt>
"""
import os
import sys
import re
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK, crilayla_decompress

CMD_BOX = 0xd4      # 说话人框开始
CMD_TXT = 0xd2      # 正文片段 / 名札
CMD_TXTEND = 0xd3   # 正文片段 + 框末
CMD_OPT_A = 0xe7    # 框末变体 / 选项
CMD_OPT_B = 0xec    # 选项
CMD_OPT_END = 0xe6  # 选项组终止
CMD_SEL = 0x33      # 记录 'select'

TAGS = re.compile(r'#(?:Name|Color|Scale|Pos|Ruby|Kana|Font|Speed|Wait|SE|Flag|Var)\[[^\]]*\]')
# 名札位置可能出现的「无名字符」占位（0xFF/0xFE 字节经 cp932 解成 PUA）
PUA = {chr(0xF8F0 + i) for i in range(16)}

# 制作备忘（直接在框内上屏的注记；本作仅 3 处，整行定值剔除）
MEMO = {'きすしーん。', 'キスシーン。'}
# 调试脚本（SE 试听 + 名字试显），整文件排除
SKIP_IDS = {101}

# 判定「日文记录」用的字符集（假名/常用汉字区段抽样）
JPCHARS = set('ぁあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめも'
              'やゆよらりるれろわをんがぎぐげござじずぜぞだでどばびぶべぼゃゅょっ'
              'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモ'
              'ヤユヨラリルレロワヲンー')


def parse_ops(d):
    """代码段 opcode 链 -> list of dict"""
    i = d.find(b'CODE_START')
    if i < 0:
        return []
    cs = i + 24
    end = struct.unpack_from('<I', d, 0x20)[0]
    off = cs
    ops = []
    while off + 4 <= end:
        sz = struct.unpack_from('<I', d, off)[0]
        if sz < 4 or off + sz > len(d):
            break
        p = d[off + 4:off + sz]
        slots = 0
        while len(p) - 12 * (slots + 1) >= 12:
            s = p[12 * slots:12 * slots + 12]
            if (struct.unpack_from('<I', s, 4)[0] == 0xff000000
                    and struct.unpack_from('<I', s, 8)[0] == 0xff000000):
                slots += 1
            else:
                break
        rest = p[12 * slots:]
        if len(rest) < 12:
            tr = rest + bytes(12 - len(rest))
        else:
            tr = rest[-12:]
        cmd, flag = struct.unpack_from('<II', tr, 4)
        mid = rest[:len(rest) - 12]
        recs = []
        j = 0
        while j + 16 <= len(mid):
            a, b, c, L = struct.unpack_from('<IIII', mid, j)
            if a == 0 and b == L // 4 and c == 1 and 4 <= L <= 16384 and j + 16 + L <= len(mid):
                raw = mid[j + 16:j + 16 + L]
                recs.append(raw.split(b'\0')[0].decode('cp932', 'replace'))
                j += 16 + L
            else:
                break
        ops.append(dict(off=off, sz=sz, slots=slots, cmd=cmd, flag=flag, recs=recs))
        off += sz
    return ops


def clean(t, hero):
    # #Name 宏必须先替换再剥标签（否则标签正则会把宏整段吃掉）
    t = t.replace('#Name[1]', hero).replace('#Name[0]', hero)
    t = TAGS.sub('', t)
    # 未解码占位（0xFF/0xFE 伪文本）
    t = ''.join('' if ch in PUA else ch for ch in t)
    return t.strip('\u3000').strip()


def _is_title_card(ops, i):
    """扉文/章节标题卡：非文本 op 里的日文记录，且其后 1〜3 个 op 是「大槽数 + IMG/BG」的标题卡图片。"""
    o = ops[i]
    if o['cmd'] in (CMD_TXT, CMD_TXTEND, CMD_OPT_A, CMD_OPT_B) or not o['recs']:
        return None
    r = o['recs'][0]
    if len(r) < 2 or not any(ch in JPCHARS for ch in r):
        return None
    for x in ops[i + 1:i + 4]:
        if x['slots'] >= 5 and x['recs'] and x['recs'][0][:3] in ('IMG', 'BG'):
            return r
    return None


def extract_text(d, hero='美紅'):
    """-> list of str（一次点击 = 一行，选项一行一条按序）"""
    ops = parse_ops(d)
    out = []
    cur = []
    opts = []
    box = False          # 刚发生 0xd4，下一个 0xd2 文本是名札

    def flush():
        if cur:
            line = ''.join(cur).strip()
            if line and line not in MEMO:
                out.append(line)
            del cur[:]

    for idx, o in enumerate(ops):
        cmd, slots, recs = o['cmd'], o['slots'], o['recs']
        title = _is_title_card(ops, idx)
        if title:
            flush()
            out.append(clean(title, hero))
            box = False
            continue
        if cmd == CMD_BOX:
            flush()
            opts = []
            box = True
            continue
        # 选项（2 槽）
        if cmd in (CMD_OPT_A, CMD_OPT_B) and slots == 2 and len(recs) == 1:
            flush()
            t = clean(recs[0], hero)
            if t:
                opts.append(t)
            box = False
            continue
        if cmd == CMD_OPT_END:
            if opts:
                out.extend(opts)
                opts = []
            box = False
            continue
        if cmd == CMD_SEL and recs and recs[0] == 'select':
            if opts:
                out.extend(opts)
                opts = []
            box = False
            continue
        # 文本片段（1 槽 1 记录）
        if cmd in (CMD_TXT, CMD_TXTEND, CMD_OPT_A) and slots == 1 and len(recs) == 1:
            if box and cmd == CMD_TXT:
                box = False          # 名札：丢弃
                continue
            box = False
            t = clean(recs[0], hero)
            if t:
                cur.append(t)
            if cmd in (CMD_TXTEND, CMD_OPT_A):
                flush()
            continue
        box = False
    flush()
    if opts:
        out.extend(opts)
    return out


def iter_files(src):
    """-> list of (name, bytes)"""
    if os.path.isdir(src):
        for n in sorted(os.listdir(src)):
            p = os.path.join(src, n)
            if not os.path.isfile(p):
                continue
            raw = open(p, 'rb').read()
            if raw[:8] == b'CRILAYLA':
                try:
                    raw = crilayla_decompress(raw)
                except Exception:
                    continue
            yield n, raw
        return
    cpk = CPK(src)
    for e in cpk.entries:
        raw = cpk.raw(e)
        yield (e.get('name') or '%04d' % (e.get('id') or 0)), raw


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else 'out.txt'
    hero = os.environ.get('GARNET_HERO', '美紅')
    lines = []
    nfile = 0
    for name, data in iter_files(src):
        if not data.startswith(b'STCM2'):
            continue
        try:
            fid = int(name)
        except ValueError:
            fid = -1
        if fid in SKIP_IDS:
            continue
        ls = extract_text(data, hero)
        if not ls:
            continue
        nfile += 1
        lines.extend(ls)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('files:', nfile, 'lines:', len(lines), '->', dst)


if __name__ == '__main__':
    main()
