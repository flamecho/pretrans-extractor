#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""恋花デイズ (PSP / Otomate, STCM2L in CRI CPK) 文本提取

容器链路: ISO9660 -> USRDIR/UNION.CPK (1432 个 STCM2L) -> 记录流

记录格式（本作）
  op = [12B 槽 × s][文本记录 × m][12B 收尾]
      槽          = [u32 v][0xff000000][0xff000000]
      文本记录    = [0][L/4][1][L][cp932 文本 + NUL + 4 字节对齐填充]
      收尾 A      = [0][cmd][flag]          （普通指令）
      收尾 B      = [1][跳转地址][flag]      （正文/选项 + 跳转，记为 cmd=0x100）

  逐文件公共库：每个文件 op[0:3717] 的 (cmd,text) 序列与 3000.bin 完全一致
  （内容＝道具取得提示 / 场景选择菜单 / PUA 占位），整块只保留一次并排除。

  正文指令（实测）
    0xd4            名札框开始（紧随的 0xd2 单记录 = 名札，丢弃）
    0xd2            正文续行
    0xd3 / 0x35 /
    0x1(s=1) /      正文 + 框末（一次点击）
    0xffffff14
    0x5  s=3        选项（一行一条）
    0x100 s>=2      选项（每项带跳转地址）
  排除：0xe7 / 0xe6（调试菜单・结局选择）、0x1 s=2 / 0x5 s=2（花知识问答）、
        0xbb / 0x1c8（邮件・话题模板）、0x1db（称呼设置表）

宏：#cname[N]＝第 N 位角色对主角的称呼　#friend[N]＝主角对第 N 位角色的称呼
    #Name[1]＝姓　#Name[2]＝名　#Name[1]#Name[2]＝全名　#n＝同框软换行
"""
import os
import re
import struct
import sys

HERO_SUR = '美咲'
HERO_GIV = '花'
HERO = HERO_SUR + HERO_GIV

# 称呼默认形：取 0x1db 表首项（游戏内可改；静态数据无"当前选择"记录）
FRIEND = {
    1: '蘭木くん',    # 蘭木司
    2: '日向くん',    # 日向陽太
    3: '百合澤先輩',  # 百合澤英士
    4: '早乙女先輩',  # 早乙女椿
    5: '高丘くん',    # 高丘菊之介
    6: '菫舘くん',    # 菫舘律人
    7: '鈴宮千尋',
    8: '鈴宮千彰',
}

JP = re.compile(r'[ぁ-んァ-ヴー一-龠]')
PUA = re.compile(r'[\uf8f0-\uf8f3]')
DEBUG = re.compile(r'デバッ?グ|^ラベル')
SYS = re.compile(r'パラメーターがプラスされます|なんて返そうかな|^[○×]$')
SKIP_PROMPT = {'プロローグをスキップしますか？'}
COMMON_OPS = 3717
SRC = '_work_koibana/cpk'
END_CMDS = {0xD3, 0x35, 0x1, 0xFFFFFF14}


def parse_op(p):
    """-> (nslots, [text...], (cmd, flag) or None)"""
    s = 0
    while (s + 1) * 12 <= len(p):
        _v, w1, w2 = struct.unpack_from('<III', p, 12 * s)
        if w1 == 0xff000000 and w2 == 0xff000000:
            s += 1
        else:
            break
    rest = p[12 * s:]
    texts, j = [], 0
    while j + 16 <= len(rest):
        a, b, c, L = struct.unpack_from('<IIII', rest, j)
        if a == 0 and b == L // 4 and c == 1 and 4 <= L <= 20000 and j + 16 + L <= len(rest):
            texts.append(rest[j + 16:j + 16 + L].split(b'\0')[0].decode('cp932', 'replace'))
            j += 16 + L
        else:
            break
    if len(rest) - j != 12:
        return s, texts, None
    w0, w1, w2 = struct.unpack_from('<III', rest, j)
    if w0 == 1:
        return s, texts, (0x100, w1)
    if w0 != 0:
        return s, texts, None
    return s, texts, (w1, w2)


def ops_of(d):
    i = d.find(b'CODE_START')
    if i < 0:
        return []
    end = struct.unpack_from('<I', d, 0x20)[0]
    off = i + 24
    out = []
    while off + 4 <= min(end, len(d)):
        sz = struct.unpack_from('<I', d, off)[0]
        if sz < 4 or off + sz > len(d):
            break
        out.append(d[off + 4:off + sz])
        off += sz
    return out


def fix(t):
    t = t.replace('#Name[1]#Name[2]', HERO)
    t = t.replace('#Name[1]', HERO_SUR).replace('#Name[2]', HERO_GIV)
    t = t.replace('#Name[0]', HERO)
    t = re.sub(r'#cname\[(\d)\]', HERO, t)
    t = re.sub(r'#friend\[(\d)\]', lambda m: FRIEND.get(int(m.group(1)), m.group(0)), t)
    t = re.sub(r'#(?:Color|Scale|Pos|Ruby|Kana|Font|Speed|Wait|SE|Flag|Var|Center|Voice)\[[^\]]*\]', '', t)
    t = t.replace('#n', '')
    t = re.sub(r'@\d+', '', t)
    t = PUA.sub('', t)
    return t.strip('\u3000').strip()


def plate_set(files):
    """全库 0xd4 名札集合（闭集）"""
    names = {'#Name[1]#Name[2]'}
    for fn in files:
        d = open(fn, 'rb').read()
        if not d.startswith(b'STCM2'):
            continue
        ops = ops_of(d)
        for i, p in enumerate(ops[COMMON_OPS:], COMMON_OPS):
            s, r, t = parse_op(p)
            if t and t[0] == 0xD4 and i + 1 < len(ops):
                s2, r2, t2 = parse_op(ops[i + 1])
                if t2 and t2[0] == 0xD2 and len(r2) == 1:
                    names.add(r2[0])
    return names


def extract(d, plates):
    """-> [(kind, text)]  kind: 'L' 正文 / 'O' 选项"""
    ops = ops_of(d)[COMMON_OPS:]
    parsed = [parse_op(p) for p in ops]
    out, cur, opts, want = [], [], [], False
    drop_opts = [False]

    def flush():
        if cur:
            t = fix(''.join(cur))
            if t and JP.search(t) and not DEBUG.search(t) and not SYS.search(t):
                if t in SKIP_PROMPT:
                    drop_opts[0] = True
                else:
                    out.append(('L', t))
            del cur[:]

    def flush_opts():
        if opts:
            if not drop_opts[0]:
                out.extend(opts)
            del opts[:]
            drop_opts[0] = False

    for idx, (s, recs, term) in enumerate(parsed):
        if term is None:
            continue
        cmd = term[0]
        if cmd == 0xD4:
            flush()
            want = True
            continue
        if want and cmd == 0xD2 and len(recs) == 1:
            want = False
            continue
        want = False
        # 名札（闭集）出现在正文流中 ⇒ 丢弃
        if len(recs) == 1 and s <= 1 and recs[0] in plates:
            flush()
            continue
        if cmd == 0x100:                       # 文本 + 跳转
            if s >= 2 and len(recs) == 1:      # 选项（每项带跳转地址）
                t = fix(recs[0])
                if t and not t.isascii() and not DEBUG.search(t):
                    flush()
                    opts.append(('O', t))
            elif len(recs) == 1:
                cur.append(recs[0])
                flush()
                flush_opts()
            else:
                flush()
                flush_opts()
            continue
        if cmd == 0x5 and s == 3 and len(recs) == 1:
            t = fix(recs[0])
            if t and not t.isascii() and not DEBUG.search(t):
                flush()
                opts.append(('O', t))
            continue
        if len(recs) != 1 or s > 1:
            continue
        t = recs[0]
        if cmd == 0xD2:
            cur.append(t)
        elif cmd in END_CMDS:
            cur.append(t)
            flush()
            flush_opts()
    flush()
    flush_opts()
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    dst = sys.argv[2] if len(sys.argv) > 2 else '_work_koibana/out/koibana.txt'
    files = sorted((os.path.join(src, n) for n in os.listdir(src) if n.endswith('.bin')),
                   key=lambda p: int(os.path.basename(p).split('.')[0]))
    plates = plate_set(files)
    lines, nf = [], 0
    for fn in files:
        d = open(fn, 'rb').read()
        if not d.startswith(b'STCM2'):
            continue
        got = extract(d, plates)
        if got:
            nf += 1
            lines.extend(t for _, t in got)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('plates', len(plates), 'files', nf, 'lines', len(lines), '->', dst)


if __name__ == '__main__':
    main()
