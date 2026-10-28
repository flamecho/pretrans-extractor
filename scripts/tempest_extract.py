#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""even if TEMPEST 宵闇にかく語りき魔女（Switch / Nintendo Bezel Engine）剧本文本提取。

链路：NSP(PFS0) → NCA → 未压缩 romfs → Archive/static~NN_01.bin.nx.bea
      → SCNE 容器 → 单个 zstd 帧 → BIN_ 字符串池

★ 池格式（本作实测）：
  0x00 'BIN_'，0x0C u32 = 字符串数 N，0x18 u32 = 字符串区起点 base，
  0x1C 起 N×u32 偏移（相对 base）。闭合判据：0x1C + N*4 == base。
  池内顺序 = [ID/标签块（含 'sss' 首项）] + [日文正文块] + [英文正文块]，**两语言块等长**。

★ 切块（关键，区别于前作的「最后一个含日文项」法）：
  本作块尾有 `「…………」` 这类**不含假名/汉字**的正文行，用「最后一个含日文项」会吞掉块尾。
  故用：st = 首个含假名/汉字的项，块长 = (N - st) // 2（须整除），日文块 = pool[st:st+块长]。
  实测 26 个章节文件全部整除，且日文/英文逐条一一对应。

★ 成行：一个字符串 = 一个文本框 = 一次点击；框内 `\n` 是排版换行 ⇒ 合并。
★ 宏：`######`（402 处）= 主角名占位，官方默认名 **アナスタシア**
  （同文件内并列 '「アナスタシアお姉様！」' 与 '「######お姉様！」'、'（私の名は######・リンゼル。'，可互证）
  引擎转义 `\f`（清页）/ `\cN`（改色）/ `\ss`（演出）⇒ 剥除。

用法：
  python scripts/tempest_extract.py <含 Archive/ 的目录> --out <txt> [--json <dump>]
"""
import sys, os, re, json, glob, struct

import zstandard

NAME_MAP = {'######': 'アナスタシア'}
# 引擎转义：\f 清页、\cN 改色、\ss 演出/停顿
ESC = re.compile(r'\\[a-z]+\d*')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# 章节文件顺序：00..25 主线，91 = 人物事后谈
ORDER = ['%02d_01' % i for i in range(26)] + ['91_01']


def scne_payload(b):
    j = b.find(b'\x28\xb5\x2f\xfd')
    if j < 0:
        raise ValueError('no zstd frame')
    return zstandard.ZstdDecompressor().decompress(b[j:], max_output_size=256 << 20)


def parse_pool(d):
    assert d[:4] == b'BIN_', d[:4]
    n = struct.unpack_from('<I', d, 0x0C)[0]
    base = struct.unpack_from('<I', d, 0x18)[0]
    if 0x1C + n * 4 != base:
        raise ValueError('池不闭合 0x1C+%d*4 != %#x' % (n, base))
    offs = struct.unpack_from('<%dI' % n, d, 0x1C)
    out = []
    for o in offs:
        e = d.index(b'\x00', base + o)
        out.append(d[base + o:e].decode('utf-8', 'replace'))
    return out


LAT = re.compile(r'[A-Za-z]{3,}')          # 英文标志：连续 3 个以上拉丁字母
IDRE = re.compile(r'^\d{2,4}_\d{4}[a-z_]?$')  # 文本 ID/标签（如 1701_0312 / 01_0246）


def split_lang(pool):
    """返回 (日文块, 英文块, st, bd)。

    块界判据（两条互相印证，实测 27 个文件全部一致）：
      ① 英文块起点 bd = 首个「无假名汉字 + 含 3+ 拉丁字母 + 其后连续 5 条同样无日文」的项；
      ② 正文起点 st = 1 + bd 之前**最后一个文本 ID 项**。
    不用「N 对半分」：多数文件日英等长，但 01_01/19_01/20_01/25_01 差 1–2 条、
    17_01 的 ID 块里混着一条 `エラー`（旧「首个含日文项」法会被它带到 524，正文整块丢失）；
    10_01 的英文块里也混着两条 `エラー`（旧「最后一个含日文项」法会把英文块当正文收进来）。
    """
    bd = None
    for i in range(1, len(pool)):
        if JP.search(pool[i]) or not LAT.search(pool[i]):
            continue
        if all(not JP.search(pool[k]) for k in range(i, min(i + 5, len(pool)))):
            bd = i
            break
    if bd is None:
        bd = len(pool)
    lastid = max((i for i in range(bd) if IDRE.match(pool[i])), default=-1)
    st = lastid + 1
    return pool[st:bd], pool[bd:], st, bd


def clean(t):
    for k, v in NAME_MAP.items():
        t = t.replace(k, v)
    t = ESC.sub('', t)
    t = t.replace('\n', '')
    return t.strip('\u3000 \t\xa0')


def main():
    srcdir = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None

    files = {}
    for p in glob.glob(os.path.join(srcdir, '**', 'static~*.bin.nx.bea'), recursive=True):
        nm = os.path.basename(p).replace('static~', '').replace('.bin.nx.bea', '')
        files[nm] = p
    seq = [k for k in ORDER if k in files]
    print('[i] 池文件 %d 个，按章节序取 %d 个' % (len(files), len(seq)))

    lines, stat, skipped = [], [], []
    for k in seq:
        pool = parse_pool(scne_payload(open(files[k], 'rb').read()))
        jp, en, st, bd = split_lang(pool)
        n0 = len(lines)
        dedup = 0
        empty = 0
        sk0 = len(skipped)
        filled = 0
        for raw in jp:   # 英文块只用于定位块界，不参与成行（部分文件英文少 1–2 条）
            # 作者注释串（'//◆選択肢=====' / '//◆SE：…' / '//ＩＤ：10_46へ'）不上屏 ⇒ 丢弃
            if raw.lstrip().startswith('//'):
                skipped.append(clean(raw)[:40])
                continue
            # 91_01（人物事後談）每条 = 若干空行 + 「――姓名」 + 空行 + 正文：
            # 拆成「姓名行 / 正文行」两行，其余章节仍按「一框一行」合并框内 \n。
            if k == '91_01' and '\n\n' in raw:
                parts = [q for q in re.split(r'\n{2,}', raw) if q.strip()]
                if len(parts) >= 2:
                    lines.append(clean(parts[0]))
                    lines.append(clean(''.join(parts[1:])))
                    continue
            c = clean(raw)
            if not c:
                empty += 1
                continue
            # 源侧「实名版 / ###### 占位版」成对重复：替换后逐字相同 ⇒ 只留一条。
            # 占位版偶有漏写收尾引号（02_01：'「わー！　######さん！…ぅぅぅ！' 缺 」），
            # 故比较时先剥掉尾部引号，留收尾完整的那一条。
            if '######' in raw and lines and lines[-1].rstrip('」』') == c.rstrip('」』'):
                dedup += 1
                continue
            lines.append(c)
            if '######' in raw:
                filled += 1
        stat.append((k, len(pool), st, len(jp), len(en), len(lines) - n0, dedup, empty,
                     len(skipped) - sk0, filled))
        print('   %s N=%5d id=%4d jp=%4d en=%4d -> 收 %4d（并 %d / 空 %d / 注释 %d / 回填 %d）'
              % (k, len(pool), st, len(jp), len(en), len(lines) - n0, dedup, empty,
                 len(skipped) - sk0, filled))

    print('[i] 合计 %d 行（丢作者注释 %d 条）' % (len(lines), len(skipped)))
    for x in skipped:
        print('   - 注释: %s' % x)
    if js:
        json.dump({'stat': stat, 'lines': lines}, open(js, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[i] -> %s' % out)


if __name__ == '__main__':
    main()
