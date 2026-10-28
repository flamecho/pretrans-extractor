#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""キミカレ ～キミとカレはじめました～ (PSP, 2012 / STCM2L) 文本提取

容器链路: CHD v5 -> ISO9660 -> PSP_GAME/INSDIR/INSTALL.DNS (PGD, drm_type=1)
          -> pgdecrypt -> CRI CPK -> script/<id> (221 个, 全 STCM2L, CRILAYLA)

STCM2L 记录（本作变体）
  0x00 32B 生成串 "STCM2L Jul 21 2011 14:25:23"
  0x20 u32 导出表偏移（= 代码段终点）
  0x54 "GLOBAL_DATA" / 0x30x "CODE_START_" -> 代码起点 = CODE_START_ 偏移 + 24
  代码段 = opcode 链 [u32 size][payload]
    payload = 12B 槽 × k  [u32 val][0xff000000][0xff000000]
            + 文本记录 × m [0][L/4][1][L][cp932 text + NUL pad]
            + 12B 收尾 [0][cmd][flag]
  cmd: 0xd2 正文片段（续行）｜0xd3 正文片段+框末｜0xd4 说话人框开始
       0x29e / 0x1dd / 0x9a / 0x7c / 0x6e / 0x6f / 0x1 等 = 正文片段+框末（同 0xd3 语义）
       0xe7(s=1) 提示行；0xe7/0xe6/0xea(s=2) 选项；0x34/0xd3('select') 选项组锚点
       0x5 = 标签定义（第一話/第二話/…/select/sure* 皆为跳转标签，非上屏文本）
"""
import os
import re
import struct
import sys

HERO = '名前'
JP = re.compile(r'[ぁ-んァ-ヴー一-龠]')
TAGS = re.compile(r'#(?:Name|Color|Scale|Pos|Ruby|Kana|Font|Speed|Wait|SE|Flag|Var)\[[^\]]*\]')

LABEL_CMDS = {0x5, 0x35, 0x34}            # 标签定义/分支锚点
KANA = re.compile(r'[ぁ-んァ-ヴ]')
OPT_CMDS = {0xe7, 0xe6, 0xea}            # 2 槽 = 选项
SKIP_IDS = {199}                          # 进度确认 ROM（调试菜单/背景列表），整文件排除


def ops_of(d):
    i = d.find(b'CODE_START')
    if i < 0:
        return []
    end = struct.unpack_from('<I', d, 0x20)[0]
    off = i + 24
    out = []
    while off + 4 <= end and off + 4 <= len(d):
        sz = struct.unpack_from('<I', d, off)[0]
        if sz < 4 or off + sz > len(d):
            break
        out.append(d[off + 4:off + sz])
        off += sz
    return out


def split(p):
    """-> (nslots, recs, (cmd,flag) or None)"""
    s = 0
    while len(p) - 12 * (s + 1) >= 12:
        w = struct.unpack_from('<III', p, 12 * s)
        if w[1] == 0xff000000 and w[2] == 0xff000000:
            s += 1
        else:
            break
    rest = p[12 * s:]
    if len(rest) < 12:
        return s, [], None
    if struct.unpack_from('<I', rest, len(rest) - 12)[0] != 0:
        return s, [], None
    cmd, flag = struct.unpack_from('<II', rest, len(rest) - 8)
    mid = rest[:-12]
    recs, j = [], 0
    while j + 16 <= len(mid):
        a, b, c, L = struct.unpack_from('<IIII', mid, j)
        if a == 0 and b == L // 4 and c == 1 and 4 <= L <= 20000 and j + 16 + L <= len(mid):
            recs.append(mid[j + 16:j + 16 + L].split(b'\0')[0].decode('cp932', 'replace'))
            j += 16 + L
        else:
            break
    return s, recs, ((cmd, flag) if j == len(mid) else None)


def clean(t, hero):
    t = t.replace('#Name[1]', hero).replace('#Name[0]', hero)
    t = TAGS.sub('', t)
    return t.replace('\uf8f2', '').replace('\uf8f3', '').strip('\u3000').strip()


def extract(d, hero=HERO):
    sp = [split(p) for p in ops_of(d)]
    lines, opts = [], []
    cur = []
    want_name = False

    def flush():
        if cur:
            t = ''.join(cur).strip()
            if t:
                lines.append(t)
            del cur[:]

    def flush_opts():
        if opts:
            lines.extend(opts)
            del opts[:]

    for i, (s, recs, t) in enumerate(sp):
        if t is None:
            want_name = False
            continue
        cmd = t[0]
        one = (len(recs) == 1 and JP.search(recs[0]) is not None)

        if cmd == 0xd4:
            flush()
            flush_opts()
            want_name = True
            continue

        if want_name and cmd == 0xd2 and len(recs) == 1:
            want_name = False                      # 名札：丢弃
            continue
        want_name = False

        # 选项（2 槽）
        if cmd in OPT_CMDS and s == 2 and len(recs) == 1:
            flush()
            x = clean(recs[0], hero)
            if x:
                opts.append(x)
            continue

        # 选项组锚点
        if cmd in (0x34, 0xd3) and recs and recs[0] == 'select':
            flush()
            flush_opts()
            continue

        if len(recs) != 1 or s > 1 or cmd in LABEL_CMDS:
            continue

        x = clean(recs[0], hero)
        if not x:
            continue
        # 纯 ASCII 记录 = 资源名/标签（screen / bg9901 / 03a_2a），不是正文
        if x.isascii():
            continue
        # 0x33 = 进度 ROM 调试打印（'処理開始' / 'thread_cnt2'）；仅极少数真正文带假名
        if cmd == 0x33 and not KANA.search(x):
            continue
        if cmd == 0xd2:
            cur.append(x)
        else:
            cur.append(x)
            flush()
            flush_opts()
    flush()
    flush_opts()
    return lines


def main():
    src, dst = sys.argv[1], sys.argv[2]
    hero = sys.argv[3] if len(sys.argv) > 3 else HERO
    files = sorted(os.listdir(src), key=lambda n: int(n.split('.')[0]))
    out, nf = [], 0
    for n in files:
        if not n.endswith('.bin'):
            continue
        if int(n.split('.')[0]) in SKIP_IDS:
            continue
        d = open(os.path.join(src, n), 'rb').read()
        if not d.startswith(b'STCM2'):
            continue
        ls = extract(d, hero)
        if ls:
            nf += 1
            out.extend(ls)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('files', nf, 'lines', len(out), '->', dst)


if __name__ == '__main__':
    main()
