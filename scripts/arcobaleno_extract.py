# -*- coding: utf-8 -*-
"""アルコバレーノ! ポータブル (PSP, ULJM05609) 剧本文本提取

容器链路
  ISO9660 -> PSP_GAME/USRDIR/UNION/SCRIPT.UNI            [CRI UNI2]
    UNI2 头 : "UNI2" + u32(0x10000) + u32 file_count(239) + u32 1 + u32 0x10(=3)
    FAT     : 0x800 起, 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
              绝对偏移 = startCluster * 0x800
    子文件  : [0x1800 前缀区/数据表][STCM2 脚本 @ +0x1800]
    STCM2 头: +0x00 generator 32B ("STCM2 File Make By Minku 07.0")
              +0x20 exports_offset(u32) ; +0x50 "GLOBAL_DATA\0" ...
              "CODE_START_\0" 12B -> 代码段 = 该串偏移 + 24
  代码段 = opcode 链 [u32 size][payload(size-4)]
    文本记录 payload = [12B「槽」*k][ [u32 0][u32 L/4][u32 1][u32 L][cp932 text] ]*n [12B [0][cmd][flag]]
      ★ 判型用「槽数 slots」(前导 [u32 v][0xff000000][0xff000000] 三元组个数):
        slots==4                 -> 正文框 (同框多串 => 合并为「一次点击=一行」)
        slots==2 & cmd in {e6,e7}-> 选项
        slots==1 & cmd==0xdf     -> 名札 (丢弃, 不加前缀)
      cmd==0xd3/0xd8 的 slots==4 记录是旗标/名表 => 丢弃

  前缀区数据表 (无 STCM2 的文件 fid 10..24):
    头 [u32 count][u32 8] + 条目 [u16 seq?][u16 idx]<cp932 string>\0 (0xFF 填充)
    ★ 按用户口径: 只并入「剧情性文本」= 语音/评论台词 + 邮件正文 (fid 15,19..24);
      食谱步骤(fid16-18)/读盘提示(fid12-14)/内部旗标(fid10,11) 判系统/UI, 不收。

主角名: #Name[1] -> 茅野(姓)  #Name[2] -> 夕菜(名)   (默认名表 SCRIPT.UNI @0xb600/0xb640)
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_src_arcobaleno/PSP_GAME/USRDIR/UNION/SCRIPT.UNI')
OUT = os.path.join(VNTRANS_HOME, '提取结果/アルコバレーノ! ポータブル_全文本.txt')
FAT, PREFIX = 0x800, 0x1800

NAME_MAGIC = (b'STCM2L', b'STCM2 ')
SYM_CMD = {0xd3, 0xd8}            # 旗标/名表载体 (slots==4 时也须丢)
OPT_CMDS = {0xe6, 0xe7}
EXCLUDE_FIDS = {90}               # 系统菜单 (プロローグをスキップしますか？)
TABLE_INCLUDE = {15, 19, 20, 21, 22, 23, 24}   # 语音/评论台词 + 邮件正文 (剧情性)
# 10,11=旗标 12,13,14=读盘提示 16,17,18=食谱 => 不收

RENAME = {'#Name[1]': '茅野', '#Name[2]': '夕菜'}
STYLE = re.compile(r'#(?:Color|Scale|Pos|Kana)\[[^\]]*\]')
JAP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e]+$')

# 旗标/系统/进度标签: 零散混进 slots==4 正文框的漏网项
DROP = [
    re.compile(r'^[^\s]{1,16}(?:フラグ|メール)$'),
    re.compile(r'^[^\s]{1,16}Ｆ[０-９0-9]*$'),
    re.compile(r'^[^\s]{1,16}[ＦＦ]$'),
    re.compile(r'^[０-９0-9]+週目$'),
    re.compile(r'^[^\s]{1,12}正解$'),
    re.compile(r'^[―—─－-]{2,}$'),          # 装饰用分隔线 (邮件画面的横线) —— 无文本内容
    re.compile(r'^(?:プロローグ|エピローグ|処理開始|テスト相談キャラ|ダミーフラグ|'
               r'不合格カウンタ|戻り値|テンション|主人公レベル|主人公タイプ|その他|'
               r'レシピ|テスト結果|水|夕菜|茅野)$'),
]


def dropped(t):
    return any(r.match(t) for r in DROP)


def usable(s):
    """保留显示用串: 纯 ASCII 者视为资源/符号名丢弃; 标点/宏串(如「……#Name[2]。)须保留"""
    return bool(s) and not ASCII_ONLY.match(s)


def load_fat(d):
    n = struct.unpack_from('<I', d, 8)[0]
    ents = []
    for i in range(n):
        fid, sc, scl, sb = struct.unpack_from('<IIII', d, FAT + 16 * i)
        if sb:
            ents.append((fid, sc * 0x800, sb))
    return ents


def analyze(pay):
    """-> (cmd, flag, slots, [str,...]) 或 None"""
    m = len(pay)
    if m < 28 or pay[m - 12:m - 8] != b'\x00\x00\x00\x00':
        return None
    cmd, flag = struct.unpack_from('<II', pay, m - 8)
    slots = 0
    while slots * 12 + 12 <= m - 12:
        v, a, b = struct.unpack_from('<III', pay, slots * 12)
        if a == 0xff000000 and b == 0xff000000:
            slots += 1
        else:
            break
    res, i = [], slots * 12
    while i + 16 <= m - 12:
        if pay[i:i + 4] == b'\x00\x00\x00\x00':
            nn, one, L = struct.unpack_from('<III', pay, i + 4)
            if one == 1 and 4 <= L <= 0x2000 and L % 4 == 0 and nn == L // 4 and i + 16 + L <= m - 12:
                raw = pay[i + 16:i + 16 + L].rstrip(b'\x00')
                s = None
                if raw and not any(b >= 0xfd for b in raw):     # cp932 合法字节仅 0x00-0xFC
                    try:
                        s = raw.decode('cp932')
                    except Exception:
                        s = None
                    if s and ('\ufffd' in s or any(ord(c) < 0x20 for c in s)):
                        s = None
                if s:
                    res.append(s)
                i += 16 + L
                continue
        i += 4
    return cmd, flag, slots, res


def iter_ops(d, fs, fe):
    c = d.find(b'CODE_START_\0', fs + PREFIX, fe)
    if c < 0:
        return
    i = c + 24
    while i + 4 <= fe:
        bs = struct.unpack_from('<I', d, i)[0]
        if bs == 0 or bs % 4 or i + bs > fe:
            break
        yield d[i + 4:i + bs]
        i += bs


def clean(s):
    s = STYLE.sub('', s)
    for k, v in RENAME.items():
        s = s.replace(k, v)
    return s.replace('#n', '').strip()


def table_strings(d, fs, end):
    """前缀区数据表: [u32 count][u32 8] 后逐条 [u16 seq?][u16 idx]<cp932>\\0 (0xFF 填充)"""
    out = []
    i = fs
    while i < end:
        j = d.find(b'\x00', i, end)
        if j < 0:
            break
        # 跳过 0xFF 填充, 再跳过至多 2 个 <0x1000 的 u16 头(seq/idx)
        k = j + 1
        while k < end and d[k] == 0xff:
            k += 1
        for _ in range(2):
            if k + 2 <= end and struct.unpack_from('<H', d, k)[0] < 0x1000:
                k += 2
            else:
                break
        e = d.find(b'\x00', k, end)
        if e < 0:
            break
        raw = d[k:e]
        if raw and not any(b >= 0xfd for b in raw):      # cp932 合法字节仅 0x00-0xFC
            try:
                s = raw.decode('cp932')
            except Exception:
                s = None
            if s and not any(0xE000 <= ord(c) <= 0xF8FF or 0xFF61 <= ord(c) <= 0xFF9F
                             for c in s) and '\ufffd' not in s \
                    and not any(ord(c) < 0x20 for c in s) and usable(s):
                out.append(clean(s))
        i = e + 1
    return out


def prefix_records(d, fs, pend):
    """前缀区 [fs, fs+0x1800) 另含记录 (子文件头部 0x1800 前的「另一份脚本段」,
    与代码段分开 ⇒ 只走代码段会漏; 见 engines/idea-factory-stcm2l-psp-cpk.md)。
    形如 [12B 槽 ×k][ [0][L/4][1][L][cp932] ]*n —— 无收尾 [0][cmd][flag],
    故以「槽块 + 其后连续串组」为一个记录, 组内合并为一行。"""
    i, recs = fs, []
    while i + 12 <= pend:
        j, k = i, 0
        while j + 12 <= pend:
            v, a, b = struct.unpack_from('<III', d, j)
            if a == 0xff000000 and b == 0xff000000:
                k += 1
                j += 12
            else:
                break
        if k == 0:
            i += 4
            continue
        strs, p = [], j
        while p + 16 <= pend:
            if d[p:p + 4] == b'\x00\x00\x00\x00':
                nn, one, L = struct.unpack_from('<III', d, p + 4)
                if one == 1 and 4 <= L <= 0x2000 and L % 4 == 0 and nn == L // 4 and p + 16 + L <= pend:
                    raw = d[p + 16:p + 16 + L].rstrip(b'\x00')
                    if raw and not any(x >= 0xfd for x in raw):
                        try:
                            strs.append(raw.decode('cp932'))
                        except Exception:
                            pass
                    p += 16 + L
                    continue
            break
        recs.append((k, strs))
        i = p if p > j else j + 12
    return recs


def main():
    d = open(SRC, 'rb').read()
    ents = load_fat(d)
    starts = sorted(e[1] for e in ents) + [len(d)]

    def fend(fs):
        return next(s for s in starts if s > fs) + PREFIX

    # pass 1: 名札集 (slots==1 & cmd==0xdf) + 代码段正文全集 (用于剔前缀区副本行)
    names, codeset = set(), set()
    for fid, fs, sb in ents:
        if d[fs + PREFIX:fs + PREFIX + 6] not in NAME_MAGIC:
            continue
        if fid not in EXCLUDE_FIDS:
            for pay in iter_ops(d, fs, fend(fs)):
                r = analyze(pay)
                if not r:
                    continue
                cmd, flag, slots, res = r
                ks = [s for s in res if usable(s)]
                if not ks:
                    continue
                if (slots == 2 and cmd in OPT_CMDS) or (slots == 4 and cmd not in SYM_CMD):
                    t = clean(''.join(ks))
                    if t and not dropped(t) and not ASCII_ONLY.match(t):
                        codeset.add(t)
        for pay in iter_ops(d, fs, fend(fs)):
            r = analyze(pay)
            if r and r[0] == 0xdf and r[2] == 1:
                t = clean(''.join(r[3]))
                if t and len(t) <= 12:
                    names.add(t)

    # pass 2: 前缀区 (记录在前) + 代码段 (正文 / 选项)
    lines, st = [], collections.Counter()
    for fid, fs, sb in sorted(ents, key=lambda e: e[0]):
        if fid in EXCLUDE_FIDS or d[fs + PREFIX:fs + PREFIX + 6] not in NAME_MAGIC:
            continue
        # 前缀区 = 与代码段并存的一份记录层 (74% 与代码段逐字相同 => 显示稿副本部分剔除,
        #          只留代码段没有的行; 纯汉字短串=姓名表 => 丢)
        for k, strs in prefix_records(d, fs, fs + PREFIX):
            ks = [s for s in strs if usable(s)]
            if not ks:
                continue
            t = clean(''.join(ks))
            if not t or t in names or t in codeset or dropped(t) or ASCII_ONLY.match(t):
                continue
            if re.match(r'^[\u4e00-\u9fff]{2,6}$', t):
                continue
            if k == 1 and len(ks) == 1 and len(t) <= 12 and not re.search(r'[。！？」』]$', t):
                names.add(t)
                st['skip'] += 1
                continue
            lines.append(t)
            st['prefix'] += 1
        for pay in iter_ops(d, fs, fend(fs)):
            r = analyze(pay)
            if not r:
                continue
            cmd, flag, slots, res = r
            ks = [s for s in res if usable(s)]
            if not ks:
                continue
            if slots == 2 and cmd in OPT_CMDS:
                t = clean(''.join(ks))
                if t and t not in names and not dropped(t) and not ASCII_ONLY.match(t):
                    lines.append(t)
                    st['opt'] += 1
                continue
            if slots != 4 or cmd in SYM_CMD:
                continue
            t = clean(''.join(ks))
            if not t or t in names or dropped(t) or ASCII_ONLY.match(t):
                st['skip'] += 1
                continue
            lines.append(t)
            st['text'] += 1

    # pass 3: 剧情性数据表 (语音/评论台词 + 邮件正文)
    # 邮件结构: 「＞<件名>」＝1 件; 「宛先：/送信者：/件名：」＝该件的字段行; 其后到下一个字段/件名
    #   之间的串是**同一封的软换行正文** ⇒ 合并为一行 (§0「行内换行合并」)。
    #   ⚠ 不可把「整封」并成一行 (会得到 200~3000 宽巨行, 用户 2026-10-18 否掉)。
    MAIL_FIELD = re.compile(r'^(?:宛先|送信者|件名|差出人)：')
    cur, in_mail = None, False
    for fid, fs, sb in sorted(ents, key=lambda e: e[0]):
        if fid not in TABLE_INCLUDE:
            continue
        end = fs + ((sb + 0x7ff) // 0x800) * 0x800      # 簇对齐: 数据文件无 STCM2, 整块都是表
        for t in table_strings(d, fs, end):
            if not (t and t not in names and not dropped(t) and not ASCII_ONLY.match(t)):
                continue
            if t.startswith('＞') or MAIL_FIELD.match(t):
                if cur:
                    lines.append(cur)
                    st['table'] += 1
                lines.append(t)
                st['table'] += 1
                cur, in_mail = None, True
            elif in_mail:
                cur = (cur or '') + t
                st['mail_join'] += 1
            else:
                lines.append(t)
                st['table'] += 1
    if cur:
        lines.append(cur)
        st['table'] += 1

    out = [l.strip() for l in lines]
    out = [l for l in out if l]
    # 行首收束标点 = 前文被切 (00b⑯) -> 并回上一行; 邮件头「送信者：」并回主题行
    LEAD = '、。，）」』）'
    mg = []
    for l in out:
        if mg and l[:1] in LEAD:
            mg[-1] += l
            st['merge_lead'] += 1
            continue
        mg.append(l)
    out = mg
    # 相邻完全重复行去重 (§0 不改写原文; 仅去相邻逐字相同)
    ded = []
    for l in out:
        if ded and ded[-1] == l:
            st['dup'] += 1
            continue
        ded.append(l)

    print('stats: %s  lines=%d' % (dict(st), len(ded)), file=sys.stderr)
    print('名札 %d 種' % len(names), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(ded) + '\n')
    print('->', OUT, file=sys.stderr)


if __name__ == '__main__':
    main()
