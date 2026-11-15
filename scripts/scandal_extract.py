#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""偽りの君とスキャンダル（Switch / Nintendo Bezel Engine）剧本文本提取。

链路：
  romfs/Archive/script.nx.bea  (SCNE 容器, zstd 负载)
    └ 头部 0x28 起 = ASST 表（每项 0x30 字节），共 2259 个 .sc 脚本（ja 1151 + en 1108）
         └ 每项 [0x14]=压缩长度 [0x18]=解压长度 [0x20]=压缩数据偏移 [0x28]=路径串偏移
              解 zstd → `scb_` 字节码容器

scb_ 容器（<10I 头）：
  0x00 'scb_'   0x08=代码段起点(0x28)  0x0C=代码段长度
  0x10=段2偏移   0x18=段3偏移          0x20=字符串池起点  0x24=字符串池长度

字节码：`u16 opcode, u16 word_count`，指令总长 = 4 * word_count，
  其后 (word_count-1) 个 u32 参数。实测全部 2259 个脚本均可完整解析到代码段末尾。

每个脚本内的 opcode 编号存在两套方言（同目录内按文件各自固定）：
  方言 A: name=11  text=12  wait=17  choice=19
  方言 B: name=12  text=13  wait=18  choice=20
  判定：统计「(name_op, text_op, wait_op) = (u32 字串引用, u32 字串引用, 无参)」
        三元组出现次数取最高票。

成行（L0）：
  **一个 text 指令 = 一个文本框 = 一次点击 = 一行**。
  实测 284,258 个 text 指令中，wait 前的 text 数恒为 1（无「一框多段」），
  同一 text 串内 0 个换行符（引擎本就不含软换行码）⇒ 单版，无合并行。
  选项 = choice 指令（24 个参数 = 8 槽 × (文本, 跳转标签, 落点) 三元组），按流序插入。

名札：name 指令是**独立名字框**（与正文分离的字段）⇒ 丢弃。
宏：#NAME[1] = 姓（立花）、#NAME[2] = 名（なつみ），取自 static~localize.bin 默认名。

用法：
  python scripts/scandal_extract.py <romfs 目录> --out <txt> [--json <dump>]
"""
import sys, os, struct, re, json, collections

import zstandard

ASST_MAGIC = b'ASST0'
JP = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')

# 默认名（static~localize.bin.nx.bea 的 487/488 条：姓 立花 / 名 なつみ）
# 另有引擎侧槽宏 [0]/[99]（不带 # 前缀，独立槽）：
#   证据 A：ja「[99][0]、銀(しろがね)室配属」↔ en「[0] [99]」⇒ 前者姓、后者名（语序互换）
#   证据 B：ja 用 [0] 处，en 同串位改写成 #NAME[2]（4 例逐字对齐，如 310108011 idx40）
#   证据 C：ja「[99]、昨日頼んでいた資料は…」被同僚以姓相称
NAME_MAP = {'#NAME[1]': '立花', '#NAME[2]': 'なつみ',
            '[99]': '立花', '[0]': 'なつみ'}

DIALECTS = {
    (11, 12, 17): dict(name=11, text=12, wait=17, choice=19),
    (12, 13, 18): dict(name=12, text=13, wait=18, choice=20),
}


def load_asst(path):
    """返回 (容器字节, [(压缩长度, 解压长度, 数据偏移, 脚本路径)])"""
    b = open(path, 'rb').read()
    if b[:4] != b'SCNE':
        raise ValueError('not SCNE')
    a0 = b.find(ASST_MAGIC)
    if a0 < 0:
        raise ValueError('no ASST table')
    ents = []
    o = a0
    while b[o:o+5] == ASST_MAGIC:
        clen = struct.unpack_from('<I', b, o + 0x14)[0]
        dlen = struct.unpack_from('<I', b, o + 0x18)[0]
        doff = struct.unpack_from('<Q', b, o + 0x20)[0]
        poff = struct.unpack_from('<Q', b, o + 0x28)[0]
        ln = b[poff]
        name = b[poff + 1:poff + 1 + ln].decode('utf-8', 'replace')
        ents.append((clen, dlen, doff, name))
        o += 0x30
    return b, ents


def parse_scb(raw):
    """scb_ → (指令列表 [(偏移, op, 参数元组)], 字符串表, 是否完整解析)"""
    if raw[:4] != b'scb_':
        raise ValueError('not scb_')
    codelen = struct.unpack_from('<I', raw, 0x0C)[0]
    code = raw[0x28:0x28 + codelen]
    s0 = struct.unpack_from('<I', raw, 0x20)[0]
    slen = struct.unpack_from('<I', raw, 0x24)[0]
    strs, q = [], s0
    while q < s0 + slen:
        e = raw.find(b'\x00', q)
        if e < 0:
            break
        strs.append(raw[q:e].decode('utf-8', 'replace'))
        q = e + 1
    ins, q = [], 0
    while q + 4 <= len(code):
        op, n = struct.unpack_from('<HH', code, q)
        if n == 0:
            ins.append((q, op, ()))
            q += 4
            continue
        if q + 4 * n > len(code):
            return ins, strs, False
        vals = struct.unpack_from('<%dI' % (n - 1), code, q + 4) if n > 1 else ()
        ins.append((q, op, vals))
        q += 4 * n
    return ins, strs, q == len(code)


def detect_dialect(ins):
    """用 (name_op, text_op, wait_op) 三元组投票，两组都试。"""
    trip = collections.Counter()
    for k in range(len(ins) - 2):
        a, b, c = ins[k], ins[k + 1], ins[k + 2]
        if len(a[2]) == 1 and len(b[2]) == 1 and a[1] != b[1] and c[1] != b[1]:
            trip[(a[1], b[1], c[1])] += 1
    if not trip:
        return None
    key = max(trip.items(), key=lambda x: x[1])[0]
    return key if key in DIALECTS else None


def clean(s, choice=False):
    for k, v in NAME_MAP.items():
        s = s.replace(k, v)
    if choice:
        # 选项标签首字符 '.' 是引擎的选择标记（源内 3 处），非正文
        s = s.lstrip('.．\u3000 ')
    return s.strip('\u3000 \t')


def extract(romfs):
    sp = os.path.join(romfs, 'Archive', 'script.nx.bea')
    b, ents = load_asst(sp)
    print('[i] script.nx.bea: %d 个脚本条目' % len(ents))
    lines, stat = [], collections.Counter()
    per_file = []
    for idx, (clen, dlen, doff, name) in enumerate(ents):
        if '/en/' in name:
            stat['skip_en'] += 1
            continue
        raw = zstandard.ZstdDecompressor().decompress(
            b[doff:doff + clen], max_output_size=dlen)
        ins, strs, ok = parse_scb(raw)
        if not ok:
            stat['parse_fail'] += 1
            print('   ! 解析未闭合: %s' % name)
            continue
        d = detect_dialect(ins)
        if d is None:
            stat['dialect_fail'] += 1
            print('   ! 方言未识别: %s' % name)
            continue
        m = DIALECTS[d]
        n0 = len(lines)
        ntext = nchoice = nempty = nnamed = 0
        cur_name = ''
        for k, (off, op, vals) in enumerate(ins):
            if op == m['name']:
                # 名札：印在正文文本框内的名字行（无独立名字窗）⇒ 保留，接到同行正文前
                if vals and vals[0] < len(strs):
                    cur_name = clean(strs[vals[0]])
                continue
            if op == m['text']:
                if not vals or vals[0] >= len(strs):
                    continue
                s = clean(strs[vals[0]])
                nm, cur_name = cur_name, ''
                if not s:
                    nempty += 1
                    continue
                if nm:
                    s = nm + s
                    nnamed += 1
                lines.append(s)
                ntext += 1
            elif op == m['choice'] and len(vals) >= 9:
                for j in range(len(vals) // 3):
                    lab = vals[3 * j]
                    if lab >= len(strs):
                        continue
                    s = clean(strs[lab], choice=True)
                    if s:
                        lines.append(s)
                        nchoice += 1
        per_file.append((name, len(lines) - n0, ntext, nchoice, nempty, d))
        stat['files'] += 1
        stat['text'] += ntext
        stat['choice'] += nchoice
        stat['empty_text'] += nempty
        stat['named'] += nnamed
    print('[i] 已处理 ja 脚本 %d 个；text=%d choice=%d 空文本=%d 带名札=%d' % (
        stat['files'], stat['text'], stat['choice'], stat['empty_text'], stat['named']))
    print('[i] 跳过 en 脚本 %d 个；解析失败 %d，方言未识别 %d' % (
        stat['skip_en'], stat['parse_fail'], stat['dialect_fail']))
    return lines, per_file, stat


def main():
    romfs = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    lines, per_file, stat = extract(romfs)
    print('[i] 合计 %d 行' % len(lines))
    if js:
        json.dump({'stat': dict(stat), 'lines': lines, 'per_file': per_file},
                  open(js, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[i] -> %s' % js)
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[i] -> %s' % out)


if __name__ == '__main__':
    main()
