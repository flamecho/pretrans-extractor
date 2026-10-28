# -*- coding: utf-8 -*-
"""恋愛番長2 MidnightLesson!!! (PSP-JP / Rejet×Otomate 2011) 剧本文本提取

容器链路
  ISO9660 -> PSP_GAME/USRDIR/INSTALL.CPK            [CRI CPK v3 (@UTF)]
    CPK 内 script/<id> = 裸 STCM2L 脚本（234 个，无 UNI2 外层）
  STCM2L 文件: "STCM2L Nov 22 2011 14:13:51" + ... + "CODE_START_\0" + 24 -> op 链
    op = [u32 size][payload(size-4)]
    文本记录 payload 尾部锚定 = [u32 0][u32 cmd][u32 flag]
      记录体 = [u32 addr][u32 style]*n [u32 0][u32 L/4][u32 1][u32 L][cp932 text]
      => k + 16 + L == len(payload) - 12

本作 cmd 语义（实证，与同族各作不同）
  k==12 cmd==0xd3  flag=0 -> 正文框末（一次点击） 25,210 条，89% 以句末标点收尾
  k==12 cmd==0x228 flag=1 -> 同框软换行续行 24,612 条，75% 句中截断
  k==12 cmd==0x2d2(282)/0x9a(13)/0x7a(2)/0x226(1)/0x2ad(1) -> 框末变体
  k==12 其余（0x0/0x5/0x33/0x34/0x35/0x67/0x66/0x6f/0xa0 ...） -> 符号/资源名，剔
  cmd∈{0xe6,0xe7} 且 k>=24 -> 选项（0xe7=308 / 0xe6=289，显示顺序 e7 先 e6 后）
    ⚠ script/1001 = シーン選択メニュー（プロローグ／〇〇番長ＥＤ１…）⇒ 菜单表，整文件不收

字体替换槽（不信 cp932；本作与 1 作同字体改画）
  0x8154(ゝ)->？  0x8155(ゞ)->！  0x8490(ю)->１０
主角宏： #Name[1]=姓(40) / #Name[2]=名(709)
"""
import struct, os, re, sys, json, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.environ.get('KB2_SRC', os.path.join(HOME, '_work_koibann2', 'cpk', 'script'))
OUT = os.environ.get('KB2_OUT', os.path.join(HOME, '提取结果', '[PSP-JP]恋愛番長2 MidnightLesson!!!_全文本.txt'))

TXT_END = {0xd3, 0x2d2, 0x9a, 0x7a, 0x226, 0x2ad}   # 框末（一次点击）
TXT_CONT = {0x228}                                 # 同框软换行续行
OPT_CMDS = {0xe6, 0xe7}
# 0      : 人物名表（op 0x1ae，15 名＋その他）＝菜单表，不收
# 999    : ＣＧ／表情ギャラリー（通常・喜び・困惑… 716 条）＝调试/UI，不收
# 1001   : シーン選択メニュー（プロローグ／〇〇番長ＥＤ１…）＝菜单表，不收
# 1xxx   : 1xx〜6xx 的**重排版副本**（内容逐字相同、断行不同）⇒ 去重不收
SKIP_FILES = {'0', '999', '1001',
              '1100', '1101', '1102', '1103', '1104',
              '1311', '1511', '1525', '1624'}
NAME = {'#Name[1]': '主人公', '#Name[2]': '主人公'}
# 字体替换槽：0x8154(ゝ)->？ 0x8155(ゞ)->！  （上下文确证，与 1 作同款改画）
# 其余 15 个西里尔槽＝数字绘制槽（0x8443..0x8484），值须 UF_ 字形光栅才能定，本次不动 ⇒ 〔未解析〕
SLOT = {'\u309d': '？', '\u309e': '！'}
SLOT_UNRESOLVED = {'\u0413', '\u0414', '\u0417', '\u041f', '\u0420', '\u0421',
                   '\u0422', '\u0423', '\u0426', '\u0427', '\u042e',
                   '\u0431', '\u0432', '\u043d', '\u0442', '\u044e'}
UNRES = '〔未解析〕'
# 槽位映射表（人工填值后重跑即可生效）：scripts/koibann2_slotmap.json
#   {"8448": {"char":"З","value":null,...}}  ->  value 填 "１００" 之类即替换
SLOTMAP = os.path.join(HOME, 'tools', 'koibann2_slotmap.json')
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e]+$')
MACRO = re.compile(r'#Name\[[12]\]')


def file_ops(p):
    d = open(p, 'rb').read()
    c = d.find(b'CODE_START_\0')
    if c < 0:
        return []
    i, out = c + 24, []
    while i + 4 <= len(d):
        bs = struct.unpack_from('<I', d, i)[0]
        if bs == 0 or bs % 4 or i + bs > len(d):
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


def load_slotmap():
    """读 scripts/koibann2_slotmap.json 里已人工填好的 value（未填=仍输出〔未解析〕）。"""
    m = {}
    try:
        j = json.load(open(SLOTMAP, encoding='utf-8'))
        for code, v in j.items():
            val = (v or {}).get('value')
            if val:
                m[bytes.fromhex(code).decode('cp932')] = str(val)
    except Exception as e:
        print('[slotmap]', e, file=sys.stderr)
    return m


SLOT_FILL = load_slotmap()


def clean(s):
    s = MACRO.sub(lambda m: NAME[m.group(0)], s)
    s = s.replace('主人公　主人公', '主人公')
    for k, v in SLOT.items():
        s = s.replace(k, v)
    for k in SLOT_UNRESOLVED:
        if k in SLOT_FILL:
            s = s.replace(k, SLOT_FILL[k])
        else:
            s = s.replace(k, UNRES)
    return s


def main():
    files = sorted((f for f in os.listdir(SRC) if f not in SKIP_FILES), key=lambda x: int(x))
    lines, st = [], collections.Counter()
    buf = []
    seq = []                                    # 用于统计续行邻接
    for f in files:
        for pay in file_ops(os.path.join(SRC, f)):
            r = rec_of(pay)
            if not r:
                seq.append(None)
                continue
            k, s, cmd, fl = r
            if k == 12 and JP.search(s):
                seq.append(('t', cmd))
                if cmd in TXT_CONT:
                    buf.append(clean(s))
                    st['cont'] += 1
                else:
                    buf.append(clean(s))
                    lines.append(''.join(buf)); buf = []
                    st['line'] += 1
            elif cmd in OPT_CMDS and k >= 24 and JP.search(s):
                seq.append(('o', cmd))
                if buf:
                    lines.append(''.join(buf)); buf = []
                    st['flush_before_opt'] += 1
                lines.append(clean(s))
                st['opt'] += 1
            else:
                seq.append(('x', cmd))
                st['other'] += 1
    if buf:
        lines.append(''.join(buf))
        st['flush_tail'] += 1

    # 续行邻接统计：cont 记录前后是否同为正文
    for i, it in enumerate(seq):
        if it and it[0] == 't' and it[1] in TXT_CONT:
            nb = [seq[j] for j in (i - 1, i + 1) if 0 <= j < len(seq) and seq[j] and seq[j][0] == 't']
            st['cont_adj1' if len(nb) == 1 else ('cont_adj0' if not nb else 'cont_adj2')] += 1

    out = [l.strip() for l in lines]
    out = [l for l in out if l]
    ded = []
    for l in out:                               # 仅去相邻完全重复（互斥分支同段取一）
        if ded and ded[-1] == l:
            st['dup_adj'] += 1
            continue
        ded.append(l)
    st['final'] = len(ded)

    print('files:', len(files), 'stats:', dict(st), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(ded) + '\n')
    print('->', OUT, file=sys.stderr)


if __name__ == '__main__':
    main()
