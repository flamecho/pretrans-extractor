#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Musketeer (PSP/5pb) .evb text decoder  -- solved 2026-10-13.

Char table (game code -> character):
  hiragana : code in [0x8181,0x81D3]  ->  SJIS = code + 0x011E   (あ=0x8182)
  katakana : sequence "ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾ
             タダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマ ミ"
             code = 0x81E1 + index, wrapping 0x8200 -> 0x8100  (i.e. i>=31 -> 0x8100+(i-31))
             tail (verified): ム=813A メ=813B モ=813C ャ=813D ヤ=813E ュ=813F ユ=8140
                              ョ=815C ラ=815E リ=815F ル=817B レ=817C ロ=817D ワ=817F
                              ン=81D7 ヴ=81D8 ー=825F
  kanji    : code = 0x8201 + (JISrow-0x30)*96 + (JIScol-0x21)   (JIS X0208, row stride 96;
             level1 rows 0x30-0x4F, level2 rows 0x50-0x74; cols 0..93, 2 pad cells/row)
  digits   : 0x8130='0' .. 0x8139='9'
  symbols  : 0x8121=！ 0x8124=… 0x8128=（ 0x8129=） 0x812C=、 0x812E=。 0x8160=？
             0x8127=々 0x8180=・ 0x8200=〜 0x8E13=―(dash)
             NOTE 0x8128/0x8129 are the ONLY bracket pair in the corpus and are
             used for the protagonist's inner monologue -> full-width （）. (user-confirmed)
Control / effect codes (not text): 0x8DD7/0x8DD8 (name/term wrapper), 0x9C00-0x9FFF
             (inline decoration), 0xFE** opcodes.
"""
C0 = 0x8201
R = 96

_KATA_SEQ = list(
    "ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅ"
    "テデトドナニヌネノハバパヒビピフブプヘベペホボポマミ"
)
KATA = {}
for _i, _ch in enumerate(_KATA_SEQ):
    _c = 0x81E1 + _i
    if _c > 0x81FF:
        _c = 0x8100 + (_i - 31)
    KATA[_c] = _ch
KATA.update({
    0x813A: 'ム', 0x813B: 'メ', 0x813C: 'モ', 0x813D: 'ャ', 0x813E: 'ヤ',
    0x813F: 'ュ', 0x815B: 'ユ', 0x815C: 'ョ', 0x815D: 'ヨ', 0x815E: 'ラ', 0x815F: 'リ',
    0x817B: 'ル', 0x817C: 'レ', 0x817D: 'ロ', 0x817F: 'ワ', 0x81D7: 'ン',
    0x81D8: 'ヴ', 0x81D9: 'ヶ', 0x81DA: 'ヶ', 0x825F: 'ー',
    0x8130: '0', 0x8131: '1', 0x8132: '2', 0x8133: '3', 0x8134: '4',
    0x8135: '5', 0x8136: '6', 0x8137: '7', 0x8138: '8', 0x8139: '9',
})

# Latin block: A-Z @ 0x8141..0x815A, a-z @ 0x8161..0x817A
LATIN = {}
for _i in range(26):
    LATIN[0x8141 + _i] = chr(ord('A') + _i)
    LATIN[0x8161 + _i] = chr(ord('a') + _i)

# individual kanji cells where euc_jp lookup fails but the game defines them
KANJI_FIX = {
    0x8E13: '―', 0x8DDD: '嗅', 0x8DE1: '媚', 0x8DE3: '諍', 0x8DE7: '璧', 0x8DE9: '疼',
    0x8DEA: '眷', 0x8DEF: '贅',
}

PUNCT = {
    0x8121: '！', 0x8124: '…', 0x8127: '々', 0x8128: '（', 0x8129: '）',
    0x812C: '、', 0x812E: '。', 0x8160: '？', 0x8180: '・', 0x8200: '〜',
}

# codes that are control/effect markers -> dropped
STRIP = {0x8DD7, 0x8DD8}


def kanji(code):
    p = code - C0
    if p < 0:
        return None
    ri, ci = divmod(p, R)
    if ci >= 94:
        return None
    jr = 0x30 + ri if ri < 32 else 0x50 + (ri - 32)
    if not (0x21 <= jr <= 0x7E):
        return None
    try:
        ch = bytes([jr | 0x80, (0x21 + ci) | 0x80]).decode('euc_jp')
        return ch if len(ch) == 1 else None
    except Exception:
        return None


def hira(code):
    if 0x8181 <= code <= 0x81D3:
        sj = code + 0x011E
        try:
            return bytes([sj >> 8, sj & 0xFF]).decode('cp932')
        except Exception:
            return None
    return None


def is_effect(code):
    if 0x9C00 <= code <= 0x9FFF or code in STRIP:
        return True
    # kanji-table pad slots (2 per row, cols 94/95) -> not characters
    if code >= 0x8201 and (code - 0x8201) % R >= 94:
        return True
    return False


def decode_char(code):
    return (KATA.get(code) or LATIN.get(code) or hira(code)
            or KANJI_FIX.get(code) or kanji(code) or PUNCT.get(code))


def decode_stream(bs):
    """decode one message-box byte run -> list of visual lines (0x0A splits)."""
    lines = [[]]
    i, n = 0, len(bs)
    while i < n:
        b = bs[i]
        if b == 0x0A:
            lines.append([])
            i += 1
            continue
        if 0x81 <= b <= 0x9F and i + 1 < n:
            code = (b << 8) | bs[i + 1]
            i += 2
            ch = decode_char(code)
            if ch is not None:
                lines[-1].append(ch)
            elif not is_effect(code):
                lines[-1].append('〔未解析〕')
            continue
        i += 1
    return [''.join(l) for l in lines if l]
