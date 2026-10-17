#!/usr/bin/env python3
"""参千世界遊戯 ～Re Multi Universe Myself～ (PSV, PCSG01194, girls★dynamics / ACTGS「ROM2/SNR」)
main.snr 剧本文本提取。

链路：NoNpDrm zip → psvpfsparser -z <zRIF> → dec/data.rom(ROM2) → rom2_extract.py → main.snr

SNR 记录格式（本作变体，与 鳥籠のマリアージュ 同族但有两处不同）：
  头 = 87 <A:u16> <F:u8> <T:u8> <C:u16> <LEN:u16> <LEN 字节 body>
    - F 恒 0；**T ∈ {0x00,0x01}**（鳥籠只有 0x01；本作 47 条 T=0x00，不区分会漏）
    - A 严格递增且连续（1..22672）
  body = [名札] @r [@p<名>. ] [@v<语音名>. ] 正文
    - 名札 = 第一个 @r 之前的全部字节 ⇒ 丢弃（不加说话人前缀）
    - @r(40 72) = 框内换行 ⇒ 合并
    - @p(40 70)/@v(40 76) = 参数为「到 '.' 为止的名字」⇒ 丢弃（本作语音名含 SJIS 假名/汉字）
    - @y(40 79)/@|(40 7c) = 无参控制 ⇒ 丢弃
  ★ 单字节 kana/记号 = **引擎自定义码表**（非 cp932 半角假名！），权威来源 = eboot(ELF) 内
    代码→Unicode 表（@0xadc5a-0x10, 代码索引，0xA1↔index8）：
      0xA0=U+3000 0xA1=。 0xA2=「 0xA3=」 0xA4=、 0xA5=… 0xA6=を
      0xA7-0xB0 = ぁぃぅぇぉゃゅょっー ; 0xB1-0xDD = あ..ん ; **0xDE=！(U+FF01) 0xDF=？(U+FF1F)**
    2 字节（lead 0x81-0x9F/0xE0-0xFC）= cp932。
  选项（内联）: 01 80 xx xx 07 <選択肢\0> <u8 blocklen> <opt1>\0<opt2>\0…\0\0
"""
import re, struct, sys, os

# ---- 单字节码表（引擎自定义；来源 eboot.elf @0xadc5a-0x10） ----
SINGLE = {0xA0: '\u3000', 0xA1: '\u3002', 0xA2: '\u300C', 0xA3: '\u300D',
          0xA4: '\u3001', 0xA5: '\u2026', 0xA6: '\u3092'}
_HIRA = 'ぁぃぅぇぉゃゅょっーあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん'
for _k, _ch in enumerate(_HIRA):
    SINGLE[0xA7 + _k] = _ch
SINGLE[0xDE] = '！'
SINGLE[0xDF] = '？'

MAGIC_REC = 0x87
SEL = b'\x91\x49\x91\xf0\x8e\x88\x00'          # 「選択肢」


def parse_records(d):
    """→ [(off, A, body)]  (A 严格递增, 1..N 连续)"""
    recs = []; lastA = -1
    for m in re.finditer(b'\x87', d):
        o = m.start()
        if o + 9 > len(d):
            break
        A = struct.unpack_from('<H', d, o + 1)[0]
        F = d[o + 3]; T = d[o + 4]
        if F > 0x10 or T > 0x01:
            continue
        C, LEN = struct.unpack_from('<HH', d, o + 5)
        if LEN < 3 or o + 9 + LEN > len(d):
            continue
        body = d[o + 9:o + 9 + LEN]
        if body[-1] != 0 or b'\x00' in body[:-1]:
            continue
        if A <= lastA:
            continue
        recs.append((o, A, body)); lastA = A
    return recs


def decode_text(b):
    """body 的「正文」部分 → 显示字符串。@r 合并, @p/@v/@y/@| 丢弃。"""
    out = []; i = 0; n = len(b)
    while i < n:
        c = b[i]
        if c == 0x40 and i + 1 < n:
            d2 = b[i + 1]
            if d2 == 0x72:                      # @r 框内换行 → 合并
                i += 2; continue
            if d2 in (0x70, 0x76):              # @p / @v : 名字到 '.' 为止 → 丢
                j = b.find(b'.', i + 2)
                if 0 <= j < i + 40:
                    i = j + 1; continue
                i += 2; continue
            if d2 in (0x79, 0x7c):              # @y / @| : 无参 → 丢
                i += 2; continue
            i += 2; continue
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:      # 2 字节 cp932
            try:
                out.append(b[i:i + 2].decode('cp932'))
            except Exception:
                out.append('〔未解析〕')
            i += 2; continue
        if 0xa0 <= c <= 0xdf:                            # 单字节自定义码表
            out.append(SINGLE.get(c, '〔未解析〕'))
            i += 1; continue
        if c < 0x20:
            i += 1; continue
        out.append(chr(c)); i += 1
    return ''.join(out)


def decode_body(b):
    """→ 正文字符串（丢弃 @r 之前的名札）"""
    i = b.find(b'\x40\x72')
    if i < 0:
        return decode_text(b)
    return decode_text(b[i + 2:])


def parse_choices(d):
    out = []
    for m in re.finditer(re.escape(SEL), d):
        o = m.start(); p = o + len(SEL)
        if p >= len(d):
            continue
        blk = d[p + 1:p + 1 + d[p]]
        parts = [x for x in blk.split(b'\x00') if x]
        good = []
        for x in parts:
            if any(b2 < 0x20 for b2 in x):
                good = []; break
            good.append(x)
        if len(good) >= 2:
            out.append((o, good))
    return out


def main():
    src, out = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    items = []
    for (o, A, b) in parse_records(d):
        tx = decode_body(b)
        items.append((float(o), tx))
    nchoice = 0
    for (o, opts) in parse_choices(d):
        for k, x in enumerate(opts):
            tx = decode_text(x)
            items.append((o + (k + 1) * 0.001, tx))
            nchoice += 1
    items.sort(key=lambda t: t[0])
    lines = [t for _, t in items]
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('records=%d  options=%d  lines=%d' % (len(items) - nchoice, nchoice, len(lines)))


if __name__ == '__main__':
    main()
