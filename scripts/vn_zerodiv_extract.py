# -*- coding: utf-8 -*-
"""
裏語 薄桜鬼 / ～暁の調べ～ (PSP ULJM06281 / ULJM06373) 剧本提取器 —— 定稿版
================================================================================
引擎: Design Factory + Zerodiv Inc. 自研

【编码模型 —— 全部由 out1/event/tutorial.dat 实证, 该文件是同一引擎的教程脚本,
  header = count(u32) + count×u32 偏移表, 数据区 78% 为明文, 可作 ground truth】

  ✗ 废除 R2「0x82 + [0x40..0x91] = 字库重绘槽 → 假名 0x82(b+0x60)」
      铁证: tutorial.dat 中 `82 71 82 51` 解出 「Ｒ２」(全角 R、2), `83 8d 81 5b 83 68
      93 e0 82 c5 ... 82 71 82 51 83 7b 83 5e 83 93` = 「ロード内で…Ｒ２ボタン」。
      该区间实为标准 cp932 的 全角数字 ０-９(824F-8258) 与 全角字母 Ａ-Ｚ(8260-8279)。
      统计: 0x82 后紧跟字节落在 40..91 的仅占 6.16%, 且全部是 １２３Ｔ 这类全角字符。

  ✗ 废除 R3「[op][B] 插入假名 (B∈A0..DF)」
      铁证: tutorial.dat 中孤立出现的 0xA0..0xDF 字节仅 235 次, 且分布**完全平坦**
      (の=7 ぇ=6 ぃ=5 か=4 …)。若真是单字节假名, の 必远多于 ぇ。→ 是随机指令字节。

  ✓ 唯一编码 = 纯 Shift-JIS (cp932)
      tutorial.dat 中 0x82 后的字节分布完全是标准假名:
      の 423 / す 351 / ま 286 / を 284 / る 267 / に 265 / が 218 / い 206 / は 200 …

【文本与指令】
  event.enc 内 = 「文本串(纯 cp932)」与「变长指令字节」交替出现。例 (entry 173):
    81 75 8d 95 82 b8 82 ad 82 df 82 cc 88 df 91 95 82 cc 96 ad 82 c8 92 6a 81 41
    82 a9 81 63 81 63 81 76        「黒ずくめの衣装の妙な男、か……」
    31 4c 05 6c 0d 01 75 05 00 00 7c 08 6c 01 2a 0c 01 00 0e   ← 17 字节指令
    8d 95 93 53 89 ae 82 cc 82 b2 8e e5 90 6c 82 aa …            黒鉄屋のご主人が…
  指令字节数不固定 (1~30+), 且含变量, 无法在不反汇编 EBOOT 的情况下完全解析
  (EBOOT.BIN = `~PSP` 加密 PRX, BOOT.BIN 全零占位, 字符表不可读)。

【判别器: 白名单】
  实测: >=8 字的 clean run 共 33035 字符 / 仅 1672 个不同字 (top2000 覆盖 100%) — 真实
  日文 Zipf 分布; 而 ==2 字的串有 45964 字符 / 4359 个不同字, 多出的 2946 字
  (煖 酋 驍 謔 娼 躓 錯 綜 ≠ 把 惠 恝 ポ 憔 …) 在长串中从未出现 — 指令字节的巧合。
  → 白名单 = 独立干净文件(tutorial/TextData/table.enc/book.dat/…)字符
             ∪ event.enc 长串(>=10字)中**出现>=3次**的字符
     (低频者视为噪声, 剔除 —— 这一步是关键, 否则 `梶`(0x8A81) 这类
      长串中出现 0 次的伪字会污染整库)

【切分】
  B1) 指令间隔含 `00 00` (字符串终止符, 由 hex dump 实证) → 强制新行
  B2) 间隔 >= maxgap → 新行
  B3) 当前行以句末标点结尾且长度 >= 4 → 新行

输出: UTF-8 BOM / LF / 一次点击一行 / 保留日文原文 / 不加说话人前缀
================================================================================
"""
import sys, os, io, struct, collections

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LEAD = lambda c: (0x81 <= c <= 0x9F) or (0xE0 <= c <= 0xFC)

CLEAN_FILES = ('event/tutorial.dat', 'text/TextData.bin', 'text/TextDataEx.bin',
               'table.enc', 'book.dat', 'defNpc.dat', 'defParty.dat',
               'termItem.dat', 'termCategory.dat', 'staffList.dat',
               'npc_album.dat', 'RTMParts.dat')
TERM = '。！？…」』!?'


def dec2(d, i):
    """严格 cp932 双字节解码"""
    if i + 1 >= len(d):
        return None
    a, b = d[i], d[i + 1]
    # N1) 0x82 是本引擎的平假名 lead, 被前一指令字节吞掉会产生 `eX82` 型伪汉字。
    #     实测: 0xE0..0xFB + 0x82 共 25 个字 (烽416 痰80 竄232 蛯108 謔261 轤285
    #     閧283 驍475 黷595 …) 在 ==10 字长串中**出现 0 次**, 而在指令区高频。
    #     真文本字的"长串占比"约 12-13% (の 739/5514, か 294/2359) -> 这 25 字必为噪声。
    if a >= 0xE0 and b == 0x82:
        return None
    if not LEAD(a) or not ((0x40 <= b <= 0x7E) or (0x80 <= b <= 0xFC)):
        return None
    try:
        c = bytes([a, b]).decode('cp932')
        return c if c else None
    except Exception:
        return None


def clean_runs(d, minlen):
    out = []; n = len(d); i = 0
    while i < n - 1:
        if dec2(d, i):
            j = i; s = []
            while j < n - 1:
                c = dec2(d, j)
                if not c: break
                s.append(c); j += 2
            if len(s) >= minlen: out.append((i, j, ''.join(s)))
            i = j if j > i else i + 1
        else:
            i += 1
    return out


def entries(base):
    d = open(os.path.join(base, 'event.enc'), 'rb').read()
    cnt = struct.unpack('<I', d[0:4])[0]
    out = []
    for i in range(cnt):
        o = 0x10 + i * 12
        a, b, c = struct.unpack('<III', d[o:o + 12])
        size = a & 0x7fffffff
        if size >= 24:
            out.append(d[c:c + size])
    return out


def build_wl(base, ents, longmin=10, longfreq=3, verbose=True):
    wl = collections.Counter()
    for fn in CLEAN_FILES:
        p = os.path.join(base, fn)
        if not os.path.exists(p): continue
        for st, en, t in clean_runs(open(p, 'rb').read(), 2):
            wl.update(t)
    c = collections.Counter()
    for e in ents:
        for st, en, t in clean_runs(e, longmin):
            c.update(t)
    for ch, n in c.items():
        if n >= longfreq: wl[ch] += n
    if verbose:
        print('  白名单 %d 字 (独立文件 ∪ event.enc 长串>=%d字出现>=%d次)' % (len(wl), longmin, longfreq))
    return wl


def runs_of(d, wl):
    out = []; n = len(d); i = 0
    while i < n - 1:
        c = dec2(d, i)
        if c and c in wl:
            j = i; s = []
            while j < n - 1:
                c2 = dec2(d, j)
                if not c2 or c2 not in wl: break
                s.append(c2); j += 2
            if s: out.append((i, j, ''.join(s)))
            i = j if j > i else i + 1
        else:
            i += 1
    return out


def split_lines(d, runs, maxgap=8):
    lines = []; cur = ''; prev = None
    for st, en, t in runs:
        brk = False
        if prev is not None:
            if b'\x00\x00' in d[prev:st]: brk = True          # B1
            if st - prev >= maxgap: brk = True                 # B2
            if cur and cur[-1] in TERM and len(cur) >= 4: brk = True   # B3
        if brk and cur:
            lines.append(cur); cur = ''
        cur += t; prev = en
    if cur: lines.append(cur)
    return lines


def extract(base, maxgap=8, longmin=10, longfreq=3, verbose=True):
    ents = entries(base)
    wl = build_wl(base, ents, longmin, longfreq, verbose)
    lines = []
    for e in ents:
        for t in split_lines(e, runs_of(e, wl), maxgap):
            t = t.strip()
            if len(t) < 2: continue
            if not any(0x3040 <= ord(x) <= 0x30FF or 0x4E00 <= ord(x) <= 0x9FFF for x in t):
                continue
            lines.append(t)
    return lines


def main(base, outpath, maxgap=8):
    lines = extract(base, maxgap)
    with io.open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('%s -> %d 行 / %d 字' % (outpath, len(lines), sum(len(x) for x in lines)))
    return lines


if __name__ == '__main__':
    base = sys.argv[1]; outp = sys.argv[2]
    mg = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    L = main(base, outp, mg)
    print('--- 抽样 ---')
    import random; random.seed(2)
    for i in random.sample(range(len(L)), 25): print('   |', L[i])
