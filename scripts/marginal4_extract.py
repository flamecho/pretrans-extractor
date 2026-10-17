# -*- coding: utf-8 -*-
"""[PSV-JP] MARGINAL#4 IDOL OF SUPERNOVA  (PCSG00448, Otomate x Rejet / Idea Factory)

剧本文本提取（正文 + 选项）。

容器链路
  NoNpDrm pkg -> pkg2zip -x -> app/PCSG00448/data/{GAME,SYSTEM,SOUND,MOVIE}.cpk
  -> psvpfsparser -k <work.bin[0x50:0x60]> -f cma.henkaku.xyz -> dec/data/*.cpk (明文 CPK)
  -> GAME.cpk 内 script/1-scenario/**/*.DAT (213) = 正文
                 database/data/dbXlsSelect.gbin = 本編選択肢

脚本格式 = STCM2L（PSV 变体；与本仓库 RE:VICE[D] 同族，但文本记录内联）
  0x00 'STCM2L <date>\0..'  0x20 export_addr
  0x50 'GLOBAL_DATA\0' ... 'CODE_START_\0'  -> 指令流起点 = 'CODE_START_' + 12
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length]
         + nparams*[p0,p1,p2] + data（length = 整条指令字节数，含内联记录）
  字符串记录（内联在指令尾部）= [0][L/4][1][L][cp932 text][pad]

  本作 opcode（实测，全 213 文件稳定）：
    0x4ba  push 文本片段（空串 = 换框符）
    0x4bb  换框 / 等待点击（np=0, len=16）—— 唯一的「一次点击」分隔符
    0x4bc  说话人/表情 ID（4 字节整数，非文本）
    0x599  p0='select', p1=<选项组KEY>  -> 本編選択肢；KEY = dbXlsSelect.gbin 的组键
    0x7e4  p0=<路线KEY>, p1='select'    -> IP 選択肢（2 选项）；KEY = dbXlsIPSelect.gbin 的组键
    0x7e9  p0=<skitterKEY>, p1='select' -> スキッター選択肢（3 候选帖文）；KEY = dbXlsSkitterSelect.gbin
           （スキッター的帖正文是图片 system/09_skitter/*.tid，无字可提，不收）

  断框判据 = 0x4bb（实测：相邻两条 0x4ba 之间若只有其它 op 而无 0x4bb ⇒ 同框合并；
             「无任何 op 相邻」35683 例、「0x4bb 分隔」约 3 万例）

  宏：#Name[1] -> 片岡（姓）  #Name[2] -> ユエ（名）  [默认名取自 script/0-init/0-init.DAT]

dbXlsSelect.gbin（本編選択肢表）
  0x40 起、每行 0x20 字节、8 个小端 u32（col0=组键偏移, col1=选项文本偏移, 其余 0）
  字符串池 base = 0x28e0，偏移相对 base，NUL 结尾，cp932

输出：一次点击=一行（连续 0x4ba 合并；0x4bb 断行）；选项紧跟其触发点；UTF-8-BOM / LF。
"""
import os
import re
import sys
import glob
import struct

HERO_SURNAME = '片岡'   # #Name[1]
HERO_GIVEN = 'ユエ'     # #Name[2]
FIRST_IP_KEY = 'ATOM01_1'   # dbXlsIPSelect 首组键（落在表头里）

RE_NAME = re.compile(r'#Name\[(\d+)\]')
RE_COLOR = re.compile(r'#Color\[\d+\]')
RE_KEY = re.compile(r'^[A-Z][A-Za-z_]*\d+_\d+$')

TEXT_OP = 0x4BA
WAIT_OP = 0x4BB
NAME_OP = 0x4BC
SELECT_OP = 0x599       # 本編選択肢 (dbXlsSelect.gbin)
SELECT_IP_OP = 0x7E4    # IP/個別選択肢 (dbXlsIPSelect.gbin)
SELECT_SK_OP = 0x7E9    # スキッター選択肢 (dbXlsSkitterSelect.gbin)


# ---------------------------------------------------------------- STCM2L
def parse(d):
    """返回 [(offset, is_call, opcode, nparams, length)]"""
    out = []
    cs = d.find(b'CODE_START_')
    if cs < 0:
        return out
    export_addr = struct.unpack_from('<I', d, 0x20)[0]
    p = cs + 12
    end = min(len(d), export_addr)
    while p + 16 <= end:
        ic, op, np, ln = struct.unpack_from('<4I', d, p)
        if ln < 16 or ln % 4 or p + ln > len(d) or np > 0x100:
            break
        out.append((p, ic, op, np, ln))
        p += ln
    return out


def param_str(d, p, np, ln, k):
    """第 k 个参数指向的内联字符串记录 [0][L/4][1][L][text]；b==L//4 且 c==1 为签名。"""
    if k >= np:
        return None
    q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
    if not (p <= q < p + ln) or q + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, q)
    if c != 1 or b != L // 4 or not (0 < L <= 0x4000) or q + 16 + L > len(d):
        return None
    try:
        return d[q + 16:q + 16 + L].split(b'\x00')[0].decode('cp932')
    except Exception:
        return None


def text_at(d, p, np, ln, k=0):
    return param_str(d, p, np, ln, k)


def clean(s):
    s = RE_COLOR.sub('', s)
    s = RE_NAME.sub(lambda m: HERO_SURNAME if int(m.group(1)) == 1
                    else (HERO_GIVEN if int(m.group(1)) == 2 else m.group(0)), s)
    return s


# ---------------------------------------------------------------- gbin 選択肢表
def load_select_gbin(path, base, row0=0x40, stride=0x20, endian='<'):
    """(key -> [option text, ...])，按出现顺序。"""
    d = open(path, 'rb').read()

    def s_at(v):
        if v == 0:
            return None
        q = base + v
        if q < 0 or q >= len(d):
            return None
        e = d.find(b'\x00', q)
        if e < 0:
            return None
        try:
            return d[q:e].decode('cp932')
        except Exception:
            return None

    groups = []
    seen = {}
    p = row0
    while p + stride <= base and p + 8 * 4 <= len(d):
        row = struct.unpack_from(endian + '8I', d, p)
        k = s_at(row[0])
        t = s_at(row[1])
        if k is None and t is None:
            p += stride
            continue
        if k is None or t is None:
            p += stride
            continue
        if k not in seen:
            seen[k] = len(groups)
            groups.append((k, []))
        groups[seen[k]][1].append(t)
        p += stride
    return groups


# ---------------------------------------------------------------- 提取
def extract_file(d, opts, ip_opts=None, sk_opts=None):
    """返回 [str, ...]：正文行 + 选项行（在触发点插入）。"""
    lines = []
    cur = []

    def flush():
        if cur:
            t = ''.join(cur).strip(' \u3000\t')
            if t:
                lines.append(t)
            del cur[:]

    def emit(key, table):
        if key and table and key in table:
            for t in table[key]:
                lines.append(clean(t))

    for (p, ic, op, np, ln) in parse(d):
        if op == TEXT_OP:
            s = text_at(d, p, np, ln, 0)
            if s is None:
                continue
            if s.strip(' \u3000\t') == '':
                flush()                       # 空文本记录 = 换框符
            else:
                cur.append(clean(s))
        elif op == WAIT_OP:
            flush()                           # 一次点击
        elif op == SELECT_OP:
            flush()
            key = None
            for k in range(np):
                s = text_at(d, p, np, ln, k)
                if s and s != 'select':
                    key = s
            emit(key, opts)
        elif op == SELECT_IP_OP:
            flush()
            key = None
            for k in range(np):
                s = text_at(d, p, np, ln, k)
                if s and s != 'select':
                    key = s
            emit(key, ip_opts)
        elif op == SELECT_SK_OP:
            flush()
            key = None
            for k in range(np):
                s = text_at(d, p, np, ln, k)
                if s and s != 'select':
                    key = s
            emit(key, sk_opts)
    flush()
    return lines


def load_ip_select(path, base=0x8F0):
    """dbXlsIPSelect.gbin（0x7e4 用）：小端/大端混在 ⇒ 实测为大端 u32 ×(表头+0x20 行)。
    结构 = [n][组键偏移][文本偏移][…][哨兵 199/200]。实测：每个组键恰好 2 条文本。
    判据 = 偏移必须「NUL 起点」（前 1 字节为 0）且可 cp932 解码；组键形如 ATOM02_2。
    第一组（偏移 0）的键在表头里 ⇒ 由脚本 0x7e4 顺序补回（本作首键 = ATOM01_1）。"""
    d = open(path, 'rb').read()

    def s_at(v):
        if v == 0:
            return None
        q = base + v
        if q <= 0 or q >= len(d) or d[q - 1] != 0:
            return None
        e = d.find(b'\x00', q)
        try:
            return d[q:e].decode('cp932')
        except Exception:
            return None

    out = []
    for i in range(0, base, 4):
        t = s_at(struct.unpack_from('>I', d, i)[0])
        if t is None:
            continue
        if RE_KEY.match(t):
            out.append([t, []])
        elif out:
            out[-1][1].append(t)
        else:
            out.append([None, [t]])
    return out


def load_skitter_select(path, base=0x1B10):
    """dbXlsSkitterSelect.gbin（0x7e9 用）：0x00 起每行 0x10 字节、4 个大端 u32
    = [组键偏移][文本偏移 或 "set"][帖子图键偏移][flag]。每 4 行为一组，组键相同。
    选项 = 组内 col1（跳过 'set' 标记行）。"""
    d = open(path, 'rb').read()

    def s_at(v):
        q = base + v
        if q < 0 or q >= len(d):
            return None
        e = d.find(b'\x00', q)
        try:
            return d[q:e].decode('cp932')
        except Exception:
            return None

    groups = []
    idx = {}
    for r in range(432):
        row = struct.unpack_from('>4I', d, r * 0x10)
        key = s_at(row[0])
        txt = s_at(row[1])
        if key is None or txt is None or r * 0x10 >= base:
            continue
        if key not in idx:
            idx[key] = len(groups)
            groups.append((key, []))
        if txt != 'set':
            groups[idx[key]][1].append(txt)
    return groups


def dedup(lines, minlen=5):
    """删除「与前面完全相同的整段」（互斥分支造成的场景重复）。

    证据：101_ATOM01 中 idx207-270 与 idx307-370 有 62 行完全相同（仅前 2 行 lead-in 不同）
    ⇒ 编译器把同一段场景分别发射到两条互斥分支下。重复段≥5 行的在本作全部是此类分支产物
    （重复块长度分布：6×1、18×1、20×1、24×1 …… 78×1，无 5 行以下的重复段）。
    只删「完全相同」的后续副本，保留每一行的首次出现；不删除任何只出现一次的行。
    """
    n = len(lines)
    delete = set()
    i = 0
    while i < n:
        best, bj = 0, None
        for j in range(i):
            k = 0
            while i + k < n and j + k < i and lines[i + k] == lines[j + k]:
                k += 1
            if k >= minlen and k > best:
                best, bj = k, j
        if best >= minlen:
            delete.update(range(i, i + best))
            i += best
        else:
            i += 1
    return [l for idx, l in enumerate(lines) if idx not in delete]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    xroot = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..', '_work_marginal4', 'x')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        here, '..', '提取结果', '[PSV-JP]MARGINAL#4 IDOL OF SUPERNOVA_全文本.txt')
    keep_dup = '--keep-dup' in sys.argv

    dbdir = os.path.join(xroot, 'database', 'data')
    sel = load_select_gbin(os.path.join(dbdir, 'dbXlsSelect.gbin'), 0x28E0)
    opts = dict(sel)

    ip_list = load_ip_select(os.path.join(dbdir, 'dbXlsIPSelect.gbin'))
    ip_opts = {}
    for k, v in ip_list:
        if k:
            ip_opts.setdefault(k, []).extend(v)
    if ip_list and ip_list[0][0] is None:
        # 首组键在表头里 ⇒ 由脚本 0x7e4 的首键补回（本作 = ATOM01_1）
        ip_opts[FIRST_IP_KEY] = ip_list[0][1]

    sk_opts = dict(load_skitter_select(os.path.join(dbdir, 'dbXlsSkitterSelect.gbin')))

    files = sorted(glob.glob(os.path.join(xroot, 'script', '1-scenario', '**', '*.DAT'),
                             recursive=True))
    all_lines = []
    raw_total = 0
    for f in files:
        ls = extract_file(open(f, 'rb').read(), opts, ip_opts, sk_opts)
        raw_total += len(ls)
        all_lines.extend(ls if keep_dup else dedup(ls))

    print('files=%d  sel=%d  ip=%d  skitter=%d  raw=%d  final=%d  (dups removed=%d)'
          % (len(files), len(sel), len(ip_opts), len(sk_opts),
             raw_total, len(all_lines), raw_total - len(all_lines)))
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(all_lines) + '\n')
    print('->', out)


if __name__ == '__main__':
    main()
