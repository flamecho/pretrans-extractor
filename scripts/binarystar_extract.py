# -*- coding: utf-8 -*-
"""[PSV-JP] BinaryStar (PCSG00389, Otomate × Design Factory, 2014) 剧本文本提取

容器链路
  NoNpDrm pkg -> pkg2zip -x -> app/PCSG00389/{data/*.cpk, sce_pfs}
  -> psvpfsparser -z <zRIF> -f cma.henkaku.xyz   （header signature is valid / keystone matched retail hmac）
  -> dec/data/GAME.cpk -> script/**/*.DAT ×128
  同捆更新包 v1.01 -> patch/PCSG00389/data/PATCH.cpk -> script/**/*.DAT ×128（40 个被改，全量覆盖）

脚本格式 = STCM2L（PSV 变体，CP932，指令 [ic][op][np][len] + np×[p0,p1,p2] + data）
  文本记录内联：p0 = 指令起点+16+12*np，记录 = [0][L/4][1][L][cp932][pad]

opcode（全 128 文件稳定，无逐文件 Δ）
  0x4BA  np=1  正文片段                     -> 收（连续合并成一行）
  0x4BB  np=0  换框／等待点击（唯一断框 op）  -> 断行（一次点击 = 一行）
  0x4BC  np=1  名札（話者名，含 #Name[1]・#Name[2]）-> 丢弃，视为断行
  0x4BE  np=1  文本速度/等待（不携带正文）
  0x4C0  np=2  章题（扉文，直接上屏）         -> 收，独占一行
  0x4CF  np=2  选项（p0=文本, p1=序号）       -> 收，独占一行
  0xC654 / 0xC664  np=8  事件 CG 台词：三行同框 + 双写变体
          参数 = [id][t1][t2][t3][id2][t1'][t2'][t3']，取组 1（t1+t2+t3 合并 = 一次点击）
  0x41A/0x41C/0x41D/0x423/0x424  np=2  按名访问变量（switch/好感度/end…）-> 不収

宏：#Name[1]=ソラノ(姓) #Name[2]=フウ(名)（默认名取自 00-init/0.DAT 名入力初期値表）
    #Color[n] 富文本色标 -> 成行前剥除

排除：00-init/*（系统初始化 + 名字表 0x596）、9-check/*（调试菜单）、05-chikai/{580,590}.DAT（ODE 调试）
用語辞典：database/data/dbXlsDictItem.gbin（見出し語）+ dbXlsDictExpl.gbin（解説），按 id 配对，并入末尾

输出：一行 = 一次点击；同框软换行合并；UTF-8 BOM / LF。
"""
import os
import re
import sys
import glob
import struct
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERO_SURNAME = 'ソラノ'
HERO_GIVEN = 'フウ'

TEXT_OP = 0x4BA
WAIT_OP = 0x4BB
NAME_OP = 0x4BC
TITLE_OP = 0x4C0
OPT_OP = 0x4CF
CG_OPS = (0xC654, 0xC664)

RE_COLOR = re.compile(r'#Color\[\d+\]')
RE_NAME = re.compile(r'#Name\[(\d)\]')
RE_CTRL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')

FILE_ORDER = [  # 输出顺序（剧本推进顺序）
    ('01-kyoutu', ('100', '101')),
    ('02-yun', None), ('03-reira', None), ('04-mikuto', None),
    ('05-chikai', None), ('06-izuki', None),
    ('07-ode', None),
]
# 11-scene（68 件）= 「シーンを選択してください。／狂愛ルート／純愛ルート」的シーン選択（回想）
# 菜单，全 68 件合计只有 4 条文本、且是选择项 ⇒ 属系统/回想载体，整体不收。
SKIP = {'00-init', '9-check', '11-scene'}


def A4(n):
    return (n + 3) & ~3


def parse(d):
    out = []
    cs = d.find(b'CODE_START_')
    if cs < 0:
        return out
    export_addr = struct.unpack_from('<I', d, 0x20)[0]
    p = cs + 12
    end = min(len(d), export_addr if export_addr else len(d))
    while p + 16 <= end:
        ic, op, np_, ln = struct.unpack_from('<4I', d, p)
        if ln < 16 or ln % 4 or p + ln > len(d) or np_ > 0x100:
            break
        out.append((p, ic, op, np_, ln))
        p += ln
    return out


def rec(d, addr):
    """文本记录 [0][L/4][1][L][cp932]"""
    if addr < 0 or addr + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, addr)
    if c != 1 or b != L // 4 or not (0 < L <= 0x8000) or addr + 16 + L > len(d):
        return None
    try:
        return d[addr + 16:addr + 16 + L].split(b'\x00')[0].decode('cp932')
    except Exception:
        return None


def param(d, p, np_, ln, k):
    if k >= np_:
        return None
    q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
    if not (p <= q < p + ln):
        return None
    return rec(d, q)


def clean(s):
    s = RE_COLOR.sub('', s)
    s = RE_NAME.sub(lambda m: HERO_SURNAME if m.group(1) == '1'
                    else (HERO_GIVEN if m.group(1) == '2' else ''), s)
    s = RE_CTRL.sub('', s)
    return s.strip('\u3000 ').rstrip() if s.strip() else s


def join_parts(parts):
    """同框多段合并：续段行首全角空格（排版缩进）去掉。"""
    out = ''
    for i, s in enumerate(parts):
        s = s.lstrip('\u3000 ') if i else s.lstrip('\u3000 ')
        out += s
    return out.strip()


def extract_file(path):
    d = open(path, 'rb').read()
    lines = []
    buf = []
    for (p, ic, op, np_, ln) in parse(d):
        if op == TEXT_OP and ic == 0:
            s = param(d, p, np_, ln, 0)
            if s is not None:
                buf.append(clean(s))
        elif op in CG_OPS:
            seg = [param(d, p, np_, ln, k) for k in (1, 2, 3)]
            seg = [clean(x) for x in seg if x]
            if seg:
                buf.append(join_parts(seg))
        elif op == WAIT_OP:
            if buf:
                t = join_parts(buf)
                if t:
                    lines.append(t)
            buf = []
        elif op == NAME_OP:
            if buf:
                t = join_parts(buf)
                if t:
                    lines.append(t)
            buf = []
        elif op == TITLE_OP:
            if buf:
                t = join_parts(buf)
                if t:
                    lines.append(t)
            buf = []
            s = param(d, p, np_, ln, 0)
            if s:
                lines.append(clean(s))
        elif op == 0x41C:   # switch/变量访问：框末分隔（全库 178 处两段正文之间只有它）
            if buf:
                t = join_parts(buf)
                if t:
                    lines.append(t)
            buf = []
        elif op == OPT_OP or (ic == 1 and op == 0xD328):
            if buf:
                t = join_parts(buf)
                if t:
                    lines.append(t)
            buf = []
            s = param(d, p, np_, ln, 0)
            if s:
                lines.append(clean(s))
    if buf:
        t = join_parts(buf)
        if t:
            lines.append(t)
    return lines


def _gbnb(d):
    """表尾 GBNB 元数据 -> (rows, rowsize, colsize, tableoff, ncols2, dataoff)"""
    i = d.rfind(b'GBNB')
    if i < 0:
        return None
    v = struct.unpack_from('>11I', d, i + 4)
    return dict(rows=v[5], rowsize=v[6], ncols=v[7], taboff=v[8],
                rows2=v[9], dataoff=v[10])


def load_dict(gbin_dir):
    it = open(os.path.join(gbin_dir, 'dbXlsDictItem.gbin'), 'rb').read()
    ex = open(os.path.join(gbin_dir, 'dbXlsDictExpl.gbin'), 'rb').read()
    words = {}
    for r in range(_gbnb(it)['rows']):
        row = struct.unpack_from('>6I', it, r * 24)
        iid, off = row[0], row[3]
        q = 0xBF0 + off
        if q >= len(it):
            continue
        e = it.find(b'\x00', q)
        words[iid] = it[q:e].decode('cp932', 'replace')
    texts = {}
    for i in range(_gbnb(ex)['rows']):
        idx, off = struct.unpack_from('>II', ex, i * 8)
        q = 0x400 + off
        if q >= len(ex):
            continue
        e = ex.find(b'\x00', q)
        texts[idx] = ex[q:e].decode('cp932', 'replace')
    out = []
    for iid in sorted(words):
        if iid in texts:
            body = texts[iid].replace('#n', '')
            out.append('【%s】%s' % (words[iid], body))
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '_work_bstar/patch_script/script'
    out_path = sys.argv[2] if len(sys.argv) > 2 else '提取结果/[PSV-JP]BinaryStar.txt'
    gbin = sys.argv[3] if len(sys.argv) > 3 else '_work_bstar/database/database/data'

    all_lines = []
    stat = []
    for sub, only in FILE_ORDER:
        d0 = os.path.join(root, sub)
        if not os.path.isdir(d0):
            continue
        for f in sorted(glob.glob(os.path.join(d0, '*.DAT')), key=lambda x: int(os.path.basename(x)[:-4])):
            base = os.path.basename(f)[:-4]
            if only and base not in only:
                continue
            if sub == '05-chikai' and base in ('580', '590'):
                continue  # ODE 调试脚本
            lines = extract_file(f)
            stat.append((sub, base, len(lines)))
            all_lines.extend(lines)

    dict_lines = load_dict(gbin)
    if dict_lines:
        all_lines.extend(dict_lines)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(all_lines) + '\n')

    print('files:', len(stat), 'lines:', len(all_lines), 'dict:', len(dict_lines))
    for s in stat:
        print('  %-10s %-5s %d' % s)


if __name__ == '__main__':
    main()
