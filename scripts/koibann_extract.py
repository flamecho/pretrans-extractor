# -*- coding: utf-8 -*-
"""恋愛番長 命短し、恋せよ乙女！ Love is Power (PSP-JP / Rejet×Otomate 2010) 剧本文本提取

容器链路
  ISO9660 -> PSP_GAME/USRDIR/UNION/SCRIPT.UNI      [CRI UNI2]
    UNI2 头 : "UNI2" + u32(0x10000) + u32 file_count(160) + u32 1 + u32 3
    FAT     : 0x800 起 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
              绝对偏移 = startCluster * 0x800
    子文件  : [0x1800 前缀区][STCM2L @ +0x1800]（生成器串 "STCM2L Sep 17 2010 14:08"）
  代码段 = "CODE_START_\0" 串 + 24 起，op 链 [u32 size][payload(size-4)]（小端）
    文本记录 payload 尾部锚定 = [u32 0][u32 cmd][u32 flag]
      记录体 = [u32 addr][u32 style]*n [u32 0][u32 L/4][u32 1][u32 L][cp932 text][尾部 12B]
      => k + 16 + L == len(payload) - 12

本作 cmd 语义（与同族 dcgs/minus8 不同，靠实证）
  k==12 cmd==0xd3 flag=0  -> 正文框末（一次点击），24,622 条，80% 以句末标点收尾
  k==12 cmd==0x1e2 flag=1 -> 同框软换行续行，16,675 条，82% 句中截断（无句末标点）
  k==12 cmd∈{0x0,0x1,0x33,0x96,0xea,0xeb} -> 符号/系统串（sure2 / 処理開始 / screen / select）
  k==12 其余 cmd（0x26/0x6f/0xd6/0x7c/0x9a/0x6e/0x13/0x34） -> 少量正文变体，按框末处理
  k==24 cmd∈{0xe6,0xe7} -> 选项（一行一条；文件内顺序即显示顺序 e7 先 / e6 后）
  k==24 cmd==0x1 且日文 -> 章名表（第一話..最終話/エピローグ，160 文件各一份＝菜单表，不收）

名札：本作脚本内**无**说话人名札文本记录（人物名由 chara 表按 id 绘制）⇒ 无需剥离。
主角宏：#Name[1]=姓 / #Name[2]=名（实证 "#Name[1]　#Name[2]！"）。本作可改名且**无内置默认名**
        （EBOOT 内仅有「この名前を使用しますか？」与五十音键盘表，无默认值）⇒ 统一替换为「主人公」。
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.environ.get('KOB_SRC', os.path.join(HOME, '_work_koibann', '_iso/PSP_GAME/USRDIR/UNION/script.uni'))
OUT = os.environ.get('KOB_OUT', os.path.join(HOME, '提取结果', '[PSP-JP]恋愛番長 命短し、恋せよ乙女！ Love is Power_全文本.txt'))

FAT, PREFIX = 0x800, 0x1800
TXT_END = {0xd3}                       # 框末（一次点击）
TXT_CONT = {0x1e2}                     # 同框续行
NON_DLG = {0x0, 0x1, 0x33, 0x96, 0xea, 0xeb}   # 符号/系统串
OPT_CMDS = {0xe6, 0xe7}
NAME = {'#Name[1]': '主人公', '#Name[2]': '主人公'}
# 字体替换槽（不信 cp932）——本作字体把 4 个槽位改画：
#   0x8154(ゝ) 渲染为「？」：1,342 处；1,033 处在行末、154 处后接全角空格（「？　」），
#                           「はゝなんだお前らゝ」「ええゝ　なんでゝ」⇒ 句尾问号
#   0x8155(ゞ) 渲染为「！」：353 处，常叠用「ゞゞ」、「はっはっはゞゞ」
#   0x8490(ю) 渲染为「10」：10月／10分延長／10ヶ月／10年前／10回に1回／10の68乗／「10！」→「９！」倒计时
#   0x8446(Ё) 渲染为「11」：唯一处「もう11月で結構寒いのに」，同档次下文「来月はクリスマス」
SLOT = {'\u309d': '？', '\u309e': '！', '\u044e': '１０', '\u0401': '１１'}
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e]+$')
MACRO = re.compile(r'#Name\[[12]\]')


def load_files(d):
    n = struct.unpack_from('<I', d, 8)[0]
    ents = []
    for i in range(n):
        fid, sc, scl, sb = struct.unpack_from('<IIII', d, FAT + 16 * i)
        if sb:
            ents.append((fid, sc * 0x800, sb))
    ents.sort()
    starts = sorted(e[1] for e in ents) + [len(d)]

    def fend(fs):                       # 末条可能跨入下一文件前缀区
        return next(s for s in starts if s > fs) + PREFIX
    return [(fid, fs, fend(fs)) for fid, fs, sb in ents]


def file_ops(d, fs, fe):
    if d[fs + PREFIX:fs + PREFIX + 6] not in (b'STCM2L', b'STCM2 '):
        return []
    c = d.find(b'CODE_START_\0', fs + PREFIX, fe)
    if c < 0:
        return []
    i, out = c + 24, []
    while i + 4 <= fe:
        bs = struct.unpack_from('<I', d, i)[0]
        if bs == 0 or bs % 4 or i + bs > fe:
            break
        out.append(d[i + 4:i + bs])
        i += bs
    return out


def rec_of(pay):
    """尾部锚定：返回 (k, text, cmd, flag) 或 None"""
    n = len(pay)
    if n < 28 or pay[n - 12:n - 8] != b'\x00\x00\x00\x00':
        return None
    cmd, flag = struct.unpack_from('<II', pay, n - 8)
    for k in range(12, min(n - 16, 208), 4):
        if pay[k:k + 4] != b'\x00\x00\x00\x00':
            continue
        nn, one, L = struct.unpack_from('<III', pay, k + 4)
        if one != 1 or L < 4 or L > 0x2000 or L % 4 or nn != L // 4:
            continue
        if k + 16 + L != n - 12:
            continue
        raw = pay[k + 16:n - 12].rstrip(b'\x00')
        if not raw:
            return None
        if any(b >= 0xfd for b in raw):      # cp932 合法字节 0x00-0xFC；>=0xFD 为样式哨兵
            return None
        try:
            s = raw.decode('cp932')
        except Exception:
            return None
        if not s or '\ufffd' in s or any(ord(c) < 0x20 for c in s):
            return None
        return (k, s, cmd, flag)
    return None


def clean(s):
    s = MACRO.sub(lambda m: NAME[m.group(0)], s)
    s = s.replace('主人公　主人公', '主人公')
    for k, v in SLOT.items():
        s = s.replace(k, v)
    return s


def main():
    d = open(SRC, 'rb').read()
    files = load_files(d)
    lines, st = [], collections.Counter()
    buf = []
    for fid, fs, fe in files:
        for pay in file_ops(d, fs, fe):
            r = rec_of(pay)
            if not r:
                continue
            k, s, cmd, fl = r
            if k == 12:
                if cmd in NON_DLG:
                    if buf:
                        lines.append(''.join(buf)); buf = []
                        st['flush_orphan'] += 1
                    st['sym'] += 1
                    continue
                if ASCII_ONLY.match(s.strip()):
                    if buf:
                        lines.append(''.join(buf)); buf = []
                    st['ascii'] += 1
                    continue
                buf.append(clean(s))
                if cmd not in TXT_CONT:
                    lines.append(''.join(buf)); buf = []
                    st['line'] += 1
                else:
                    st['cont'] += 1
            else:
                if buf:            # 续行被非正文打断 -> 先落地
                    lines.append(''.join(buf)); buf = []
                    st['flush_interrupt'] += 1
                if cmd in OPT_CMDS and JP.search(s):
                    lines.append(clean(s))
                    st['opt'] += 1
    if buf:
        lines.append(''.join(buf))

    out = [l.strip() for l in lines]
    out = [l for l in out if l]
    ded = []
    for l in out:                        # 仅去相邻完全重复（互斥分支同段取一）
        if ded and ded[-1] == l:
            st['dup_adj'] += 1
            continue
        ded.append(l)
    st['final'] = len(ded)

    print('stats:', dict(st), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(ded) + '\n')
    print('->', OUT, file=sys.stderr)


if __name__ == '__main__':
    main()
