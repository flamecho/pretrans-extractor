# -*- coding: utf-8 -*-
"""[PSV-JP] MARGINAL#4 ROAD TO GALAXY  (PCSG01008, Otomate x Rejet / Idea Factory)

剧本文本提取（正文 + 章题）。

容器链路
  NoNpDrm pkg -> pkg2zip -x -> app/PCSG01008/data/{GAME,STORY,SYSTEM,SOUND,MOVIE}.cpk
  -> psvpfsparser -k <work.bin[0x50:0x60]> -f cma.henkaku.xyz -> dec/data/*.cpk (明文 CPK)
  -> STORY.cpk 内 SCRIPT/*.DAT (140) + SCRIPT/init/*.DAT (6) = 正文
     SYSTEM.cpk 内 DATABASE/dbEntryScript.gbin = 剧本入口表（判定哪些 DAT 真的被播放）

脚本格式 = STCM2L（PSV 新变体 F：**UTF-8** 字符串、opcode 恒定无逐文件 Δ、文本记录内联）
  0x00 'STCM2L <date>\0..'
  0x50 'GLOBAL_DATA\0' ... 'CODE_START_\0' -> 指令流起点 = 'CODE_START_' + 12
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length]
         + nparams*[p0,p1,p2] + data（length = 整条指令字节数，含内联记录）
  字符串记录（内联在指令尾部）= [0][L/4][1][L][utf-8 text][pad]

  本作 opcode（实测，全 146 文件稳定；与 IDOL OF SUPERNOVA 的 CP932 变体 E 不同编码）：
    0xE714  push 正文（np=1，UTF-8）
    0xEF20  push 说话人名札（np=1，'桐原 アトム' / '#Name[1] #Name[2]'）—— 丢
    0x62F80 / 0x63318  互斥双写正文（np=8 = [id][t1][t2][t3][id2][t1'][t2'][t3']）
            —— 组2 用 #Name 宏、组1 直写人名 ⇒ **取组1**
    **0xFB68  選択肢（np=3）**：p0 = 选项文本（字符串记录，**常驻「指令外」的数据区**，故不能用
            内联范围判定，须直接按绝对偏移取记录）、p1 = 数据指针、p2 = 跳转标签（'sure2/3/4'）
            ⇒ 一行一条、按出现顺序；同一组 = 连续 3 条 0xFB68
    0x2250  章题（np=2，'Prologue'/'MARGINAL#4 1話'）—— 收（直接上屏扉文）
    0x5778/0x5168/0x4D98/0x4F80/0x56E8/0x5988  变量/标签名（含薄桜鬼遗留槽）—— 丢
    0x54990/0x548AC/0x636B0  背景变更 + 地名（'事務所・社長室'）—— 默认丢（--with-loc 收）
    0xF850  系统通知（'#Color[3]おまけ画像#Color[0]が開放されました'）—— 丢
    0x1F4  换框 / 等待点击（np=0）—— **唯一的「一次点击」分隔符**
    builtin 0x0/0x3/0x6/0x11/0x12/0x2xx… = VM 内部 —— 丢

  宏：#Name[1] -> 片岡（姓）  #Name[2] -> ユエ（名）
      [默认名取自 SCRIPT/init/0_init.DAT 的 名前入力初期値表 @0x37f68 / 0x37fcc]

输出：一次点击 = 一行（连续正文记录合并；0x1F4 断行）；UTF-8-BOM / LF。
"""
import os
import re
import sys
import struct
import glob

HERO_SURNAME = '片岡'   # #Name[1]
HERO_GIVEN = 'ユエ'     # #Name[2]

TEXT_OP = 0xE714
NAME_OP = 0xEF20
WAIT_OP = 0x1F4
TITLE_OP = 0x2250
OPT_OP = 0xFB68                        # 選択肢（p0=选项文本, p2=跳转标签）
DUP_OPS = (0x62F80, 0x63318)          # 互斥双写正文
LOC_OPS = (0x54990, 0x548AC, 0x636B0)  # 背景 + 地名
# 断框（一次点击）
#   0x1F4 = 换框/等待点击（主判据）
#   0xEF20 = 说话人名札（新说话人 ⇒ 新框）
#   变量/标签访问 op（'switch'/'羅刹度'…）——少数短句「框尾无 0x1F4」的情形靠它断开
#     （如 304.DAT『え、何？』后紧跟 0x4F80 'switch'；同 RE:VICE[D] 变体 B 的「变量 op 断框」判据）
BOUNDARY_OPS = (WAIT_OP, NAME_OP, 0x4F80, 0x5168, 0x4D98, 0x5778, 0x56E8, 0x5988)

RE_NAME = re.compile(r'#Name\[(\d+)\]')
RE_COLOR = re.compile(r'#Color\[\d+\]')


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
    """第 k 个参数指向的内联字符串记录 [0][L/4][1][L][utf-8]；c==1 且 b==L//4 为签名。"""
    if k >= np:
        return None
    q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
    if not (p <= q < p + ln) or q + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, q)
    if c != 1 or b != L // 4 or not (0 < L <= 0x4000) or q + 16 + L > len(d):
        return None
    try:
        return d[q + 16:q + 16 + L].split(b'\x00')[0].decode('utf-8')
    except Exception:
        return None


def rec_at(d, q):
    """直接按绝对偏移取字符串记录（不做「指令内」范围判定）——0xFB68 的选项文本常驻指令外的数据区。"""
    if q < 0 or q % 4 or q + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, q)
    if c != 1 or b != L // 4 or not (0 < L <= 0x4000) or q + 16 + L > len(d):
        return None
    try:
        return d[q + 16:q + 16 + L].split(b'\x00')[0].decode('utf-8')
    except Exception:
        return None


def is_jp(s):
    return bool(s) and any('\u3040' <= ch <= '\u30ff' or '\u4e00' <= ch <= '\u9fff' for ch in s)


def clean(s):
    s = RE_COLOR.sub('', s)
    s = RE_NAME.sub(lambda m: HERO_SURNAME if int(m.group(1)) == 1
                    else (HERO_GIVEN if int(m.group(1)) == 2 else m.group(0)), s)
    return s.replace('\n', '')


# ---------------------------------------------------------------- 提取
def extract_file(d, with_loc=False):
    lines = []
    cur = []

    def flush():
        if cur:
            t = ''.join(cur).strip(' \u3000\t')
            if t:
                lines.append(t)
            del cur[:]

    for (p, ic, op, np, ln) in parse(d):
        if op == TEXT_OP:
            s = param_str(d, p, np, ln, 0)
            if s is None:
                continue
            cur.append(clean(s))
        elif op in DUP_OPS:
            for k in (1, 2, 3):                 # 组1（直写人名版）
                s = param_str(d, p, np, ln, k)
                if s:
                    cur.append(clean(s))
        elif op == TITLE_OP:
            flush()
            s = param_str(d, p, np, ln, 0)
            if s:
                lines.append(clean(s))
        elif op == OPT_OP:
            flush()
            for k in range(np):
                q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
                s = rec_at(d, q)
                if is_jp(s):            # 取第一个（= p0）日文选项文本
                    lines.append(clean(s))
                    break
        elif op in BOUNDARY_OPS:
            flush()
        elif with_loc and op in LOC_OPS:
            flush()
            for k in range(np):
                s = param_str(d, p, np, ln, k)
                if s and any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in s):
                    lines.append(clean(s))
    flush()
    return lines


def load_entry_order(sys_cpk_dir):
    """从 SYSTEM.cpk 的 DATABASE/dbEntryScript.gbin 取剧本顺序。"""
    p = os.path.join(sys_cpk_dir, 'DATABASE', 'dbEntryScript.gbin')
    d = open(p, 'rb').read()
    order = []
    for m in re.finditer(rb'/SCRIPT/([A-Za-z0-9_./]+\.DAT)', d):
        order.append(m.group(1).decode())
    return order


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    xroot = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, '..', '_work_marginal4_road', 'x')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        here, '..', '提取结果', '[PSV-JP]MARGINAL#4 ROAD TO GALAXY_全文本.txt')
    with_loc = '--with-loc' in sys.argv

    sdir = os.path.join(xroot, 'x_story', 'SCRIPT')
    sysdir = os.path.join(xroot, 'x_sys')

    # 入口表顺序（去掉 init/*）
    order = load_entry_order(sysdir)
    files = []
    for rel in order:
        if rel.startswith('init/'):
            continue
        f = os.path.join(sdir, rel.replace('/', os.sep))
        if os.path.isfile(f):
            files.append(f)
    if not files:   # 兜底：直接扫 SCRIPT 根
        files = sorted(glob.glob(os.path.join(sdir, '*.DAT')))
        files = [f for f in files if os.path.basename(f) != '100.DAT']

    all_lines = []
    per = []
    for f in files:
        ls = extract_file(open(f, 'rb').read(), with_loc)
        per.append((os.path.basename(f), len(ls)))
        all_lines.extend(ls)

    print('files=%d  lines=%d  (with_loc=%s)' % (len(files), len(all_lines), with_loc))
    print('per-file:', ' '.join('%s:%d' % (b, n) for b, n in per))
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(all_lines) + '\n')
    print('->', out)


if __name__ == '__main__':
    main()
