"""Extractor for 遥かなる時空の中で4 (PSP, Koei / Ruby Party).

Container & tables (all inside `PSP_GAME/USRDIR/DATA.BIN`, a CDAR archive):
  * entry 2512  -> the whole event script (4.1 MB of bytecode)
  * entry 4418  -> two string tables:
      - word/variable table : base 900,  stride 54  -> [name 20B][reading 20B][14B]
        `0x25 <u16 id>` in the script inserts words[id].name
        (verified: 4=那岐 22=一ノ姫 435=龍神 770=中つ国 1026=顕)
      - address matrix      : base 108244, 16-byte cells, 12 columns
        M[row][col] = how the person of `row` calls the person of `col`
        row0 = protagonist (葦原千尋), rows 1..8 = 風早 / アシュヴィン / サザキ /
        那岐 / 布都彦 / 柊 / 遠夜 / 塔矢;  diagonal = self reference (私/俺/オレ/僕)

Script bytecode (reverse-engineered 2026-09-30, game-verified):
    0x20 <u8 len> <bytes>   append text (see decode_text)
    0x25 <u16 id>           insert word-table entry `id`
    0x5d 00 00              line break inside the same message (joined)
    0x5d 08 00 5b <u16>     message header: speaker row = u16 - 0x0248
    0x5d 0a/0b/09 00 5b ..  rest of the message header (ignored)
    0x5d 07 00              ruby separator -> drop name + reading
    0x5d 14 00 5b <u16>     insert how the speaker addresses (u16 - 0x0248)
    0x5d 01/02/03/04/05/06 00   end of message -> emit one line
    0x47 <u16>              message/speaker tag; `0x20 <name> 0x47 ..` is an
                            inline speaker label -> dropped (no name prefix)
    other bytes             skipped

Text encoding: kanji / voiced kana are ordinary 2-byte Shift-JIS; plain
hiragana are stored as single-byte JIS X0201 katakana (0xA1-0xDF) and drawn
with a hiragana font page.  Byte 0xA0 is the game's own glyph for "…".
"""
import os
import re
import sys
import unicodedata

PLACEHOLDER = '\u3013'
PROTAGONIST = '千尋'

# JIS X0201 half-width katakana
HW = ('。「」、・ヲァィゥェォャュョッーアイウエオカキクケコサシスセソタチツテト'
      'ナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン゛゜')
HW2KANA = {0xA1 + i: ch for i, ch in enumerate(HW)}

RE_BAD_ASCII = re.compile(r'[A-Za-z0-9\\\[\]{}~^|`_#<>&*@$%+=/]')
RE_ASCII = re.compile(r'[A-Za-z0-9]')
# dev/debug leftovers: 0xDE/0xDF (voicing marks never used in normal text) and
# full-width alphanumerics ("効スチル０４ａ゛ＳＴＡ゜", "フキダシ位置を３２０ ２２４...",
# "スチル０６２＆効果", CG viewer labels, option tags, ...).  Normal dialogue
# never carries full-width digits/letters.
RE_DEV = re.compile(r'[\u309b\u309c]')
RE_FWALNUM = re.compile(r'[０-９Ａ-Ｚａ-ｚ]')
# developer / debug-menu strings (CG viewer, bubble placement, monologue test...)
# NOTE: keep テスト/天秤 OUT of the plain-keyword list -- they occur in real
# dialogue (school exams, the "心の天秤" mechanic).  They are matched with
# dedicated line-shaped patterns in RE_DEBUGLINE instead.
RE_DEBUGWORD = re.compile(r'モノローグ|デバッグ|スチル|フキダシ|ＣＢＵ|シネスコ'
                          r'|登場します|揺れます|セピア|記憶干渉|顔表示'
                          r'|ワープ退場|人物消去')
# debug-block line shapes (menu labels like "テスト１", "天秤表示", "選択肢２…")
RE_DEBUGLINE = re.compile(
    r'テスト[０-９]*です。?$'
    r'|^テスト[０-９]$'
    r'|テスト終了|テストを終了|関連のテスト'
    r'|^天秤$|天秤(?:表示|消去|失敗|オン|オフ|コマンド)'
    r'|消去$'
    r'|^選択肢$|選択肢[０-９]')
# bare expression labels ("通常", "笑顔", "驚き"...) = sprite/voice tags
RE_EXPR_ONLY = re.compile(r'^(?:通常|笑顔|怒り|驚き|照れ|困り|真剣|本気|優しい|不快'
                          r'|悲しい|泣き|真面目|デフォルト)[０-９]*$')
# "<name><expression>" sprite tags ("サザキ笑顔", "サザキ顔通常", ...)
_NAMES = '那岐|千尋|風早|アシュヴィン|サザキ|布都彦|柊|遠夜|塔矢|里仲|翡翠|岩長|翁|土蜘蛛|芦屋|多史|忍人'
RE_EXPR_TAG = re.compile(r'^(?:%s)(?:顔)?(?:通常|笑顔|怒り|驚き|照れ|困り|真剣|本気|優しい|不快|悲しい|泣き|真面目)$' % _NAMES)
# trailing full-width digit = script label ("天秤２", "ひざまずいて忠誠を誓う１")
RE_TRAILDIGIT = re.compile(r'[０-９]$')
# "２択だよ"-style debug choice counters
RE_TAKU = re.compile(r'[０-９]択')
# scene / sprite-pick labels: "Ｃ桃の木" (bg), "Ｗ風早" (character), variable
# debug output ("現在の変数Ａの値は", bare "０です", "２が出ました")
RE_CWLABEL = re.compile(r'^[ＣＷ]')
RE_VARDUMP = re.compile(r'^現在の変数|^[０-９]です$|^[０-９]が出ました$'
                        r'|^別のファイルから飛んできました'
                        r'|^オープニング[Ａ-Ｚ]$|^神の声を聞く主人公[Ａ-Ｚ]$')
# "シーン２アシュヴィンは…" -- scene-pick label glued to real dialogue
RE_SCENEPRFX = re.compile(r'^シーン[０-９]+')
RE_JP = re.compile('[\u3041-\u309f\u4e00-\u9fff\u30a0-\u30ff]')
# punctuation-only records are legitimate (a lone "…" for example)
RE_JP_PUNCT = re.compile('^[\u3000-\u303f\u30fb\u30fc\uff01-\uff65\u2010-\u203b]+$')
# game-font remaps: rarely used SJIS symbol codes carry combined punctuation
FONT_REMAP = {'\uff04': '\uff01\uff1f',      # ＄ -> ！？
              '\uffe0': '\uff01\uff01',      # ￠ -> ！！
              '\uffe1': '\uff1f\uff01'}      # ￡ -> ？！

WORD_BASE, WORD_STRIDE, WORD_NAME = 900, 54, 20
MATRIX_BASE, MATRIX_CELL, MATRIX_COLS, MATRIX_ROWS = 108244, 16, 12, 9
CHAR_BASE = 0x0248          # address-matrix index = operand - CHAR_BASE


def decode_text(data):
    """Shift-JIS aware decode; 0xA1-0xDF -> hiragana, 0xA0 -> '…'."""
    out = []
    i, n = 0, len(data)
    while i < n:
        b = data[i]
        if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef:
            if i + 1 < n:
                try:
                    out.append(data[i:i + 2].decode('cp932'))
                except Exception:
                    out.append('\ufffd')
                i += 2
            else:
                i += 1
        elif b == 0xa0:
            out.append('\u2026')      # game glyph: "…"
            i += 1
        elif 0xa1 <= b <= 0xdf:
            k = HW2KANA.get(b)
            if k and 0x30A1 <= ord(k) <= 0x30F6:
                out.append(chr(ord(k) - 0x60))
            elif k:
                out.append(k)
            i += 1
        elif 0x20 <= b < 0x7f:
            out.append(chr(b))
            i += 1
        else:
            i += 1
    return ''.join(out)


def clean(t):
    t = ''.join(FONT_REMAP.get(c, c) for c in t)
    # （千尋）= runtime protagonist-name marker
    return t.replace('\uff08' + PROTAGONIST + '\uff09', PROTAGONIST)


def _valid(t):
    if not t or '\ufffd' in t:
        return None
    if RE_BAD_ASCII.search(t):
        return None
    if RE_JP.search(t) is None and RE_JP_PUNCT.search(t) is None:
        return None
    return t


class Tables:
    def __init__(self, blob):
        self.blob = blob
        self.words = {}
        for i in range((len(blob) - WORD_BASE) // WORD_STRIDE):
            o = WORD_BASE + WORD_STRIDE * i
            name = clean(decode_text(blob[o:o + WORD_NAME].split(b'\x00')[0]))
            if name:
                self.words[i] = name
        self.matrix = []
        for r in range(MATRIX_ROWS):
            row = []
            for c in range(MATRIX_COLS):
                o = MATRIX_BASE + (r * MATRIX_COLS + c) * MATRIX_CELL
                cell = blob[o:o + MATRIX_CELL].split(b'\x00')[0]
                row.append(clean(decode_text(cell)))
            self.matrix.append(row)

    def addr(self, speaker, col):
        """How `speaker` (row) calls `col`.  Falls back to the word table."""
        if 0 <= speaker < len(self.matrix) and 0 <= col < MATRIX_COLS:
            nm = self.matrix[speaker][col]
            if nm:
                return nm
        return self.words.get(col, PLACEHOLDER)


def parse_messages(blob, tables, with_offsets=False):
    n = len(blob)
    # byte range of the in-game debug menu block (see flush() for details)
    DEBUG_LO = 1523000
    DEBUG_HI = 1628400
    out, cur = [], []
    offs = []
    msg_start = 0
    i = 0
    speaker = 0
    names_in_line = 0

    def flush(end_off):
        s = ''.join(cur).strip()
        # narration / inner monologue is wrapped in the 0xDE/0xDF glyph pair
        # (rendered as quotation marks): keep the text, drop the markers.
        if len(s) >= 2 and s[0] == '\u309b' and s[-1] == '\u309c':
            s = s[1:-1].strip()
        s = RE_SCENEPRFX.sub('', s).strip()
        # drop leftovers of system/battle blocks (they carry raw ASCII fields)
        # drop lines that are nothing but a character name -> speaker label
        # DEBUG BLOCK: the script carries a whole in-game debug menu (effect /
        # sprite / CG viewers, flag & bond manipulation, Momotaro font test...)
        # spanning offsets ~1523779 ("エフェクト") to ~1621856 ("どうする？");
        # real dialogue resumes at 1628541.  Bare name lines inside it are CG /
        # scene labels ("白麒麟", "桜の花びら", "同門の絆"...).  Bare name
        # messages OUTSIDE it are real dialogue (a character calling a name,
        # e.g. 「風早」 after the teacher's greeting in the opening).
        if (s and s != PLACEHOLDER and not RE_ASCII.search(s)
                and not (DEBUG_LO <= msg_start < DEBUG_HI)
                and not RE_DEBUGWORD.search(s)
                and not RE_DEBUGLINE.search(s)
                and not RE_EXPR_ONLY.match(s)
                and not RE_EXPR_TAG.match(s)
                and not RE_TRAILDIGIT.search(s)
                and not RE_TAKU.search(s)
                and not RE_CWLABEL.match(s)
                and not RE_VARDUMP.search(s)
                and len(RE_FWALNUM.findall(s)) < 2
                and names_in_line < 3):
            out.append(s)
            offs.append((msg_start, end_off))
        cur.clear()

    while i < n:
        c = blob[i]
        # ---- text -------------------------------------------------------
        if c == 0x20 and i + 2 <= n:
            L = blob[i + 1]
            if 1 <= L <= 600 and i + 2 + L <= n:
                t = _valid(decode_text(blob[i + 2:i + 2 + L]))
                if t is not None:
                    j = i + 2 + L
                    if j + 3 <= n and blob[j] == 0x47 and blob[j + 2] == 0x00:
                        i = j + 3          # inline speaker label -> dropped
                        continue
                    if not cur:
                        msg_start = i
                    cur.append(t)
                    i = j
                    continue
        # ---- word-table insert -----------------------------------------
        if c == 0x25 and i + 3 <= n:
            vid = blob[i + 1] | (blob[i + 2] << 8)
            if vid in tables.words:
                cur.append(tables.words[vid])
                i += 3
                continue
        # ---- 5d family --------------------------------------------------
        if c == 0x5d and i + 3 <= n and blob[i + 2] == 0x00:
            xx = blob[i + 1]
            if xx == 0x00:
                i += 3                      # line break inside the message
                continue
            if xx == 0x07:                  # ruby: "<name> 5d07 <reading>"
                cur.clear()
                i += 3
                if (i + 2 <= n and blob[i] == 0x20 and 2 <= blob[i + 1] <= 600
                        and i + 2 + blob[i + 1] <= n):
                    i += 2 + blob[i + 1]
                continue
            if xx == 0x08:                  # speaker row
                if cur:
                    flush(i)
                    names_in_line = 0
                if i + 6 <= n and blob[i + 3] == 0x5b:
                    speaker = (blob[i + 4] | (blob[i + 5] << 8)) - CHAR_BASE
                    i += 6
                else:
                    i += 3
                continue
            if xx == 0x14:                  # address-form insert
                if i + 6 <= n and blob[i + 3] == 0x5b:
                    col = (blob[i + 4] | (blob[i + 5] << 8)) - CHAR_BASE
                    nm = tables.addr(speaker, col)
                    if nm and (not cur or cur[-1] != nm):
                        cur.append(nm)
                        names_in_line += 1
                    i += 6
                else:
                    i += 3
                continue
            if xx in (0x09, 0x0a, 0x0b, 0x0f, 0x10, 0x13, 0x16):
                i += 3                      # header tail / message-start
                if i + 3 <= n and blob[i] == 0x5b:
                    i += 3
                continue
            if xx == 0x06:
                # 5d 06 00 <0x20 len name> : inline speaker-name block.
                # Not a message end -- the name belongs to the message header and
                # is dropped (output carries no speaker prefix).  Verified: all 839
                # occurrences of 5d 06 00 in the script are followed by 0x20.
                if cur:
                    flush(i)
                    names_in_line = 0
                i += 3
                if i + 2 <= n and blob[i] == 0x20:
                    L = blob[i + 1]
                    if 1 <= L <= 600 and i + 2 + L <= n:
                        i += 2 + L          # skip the name record
                continue
            if xx in (0x01, 0x02, 0x03, 0x04, 0x05):
                flush(i)                    # end of message
                names_in_line = 0
                i += 3
                continue
            i += 3                          # 0x1c/0x1d/0x1e/0x1f ... ignored
            continue
        if c == 0x5b and i + 3 <= n:
            i += 3                          # generic 5b <u16>
            continue
        i += 1
    flush(i)
    if with_offsets:
        return out, offs
    return out


def main():
    cdar_path = sys.argv[1]
    out_path = sys.argv[2]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cdar import CDAR
    arc = CDAR(cdar_path)
    tables = Tables(arc.data(4418))
    lines = parse_messages(arc.data(2512), tables)
    with open(out_path, 'w', encoding='utf-8-sig') as f:
        for ln in lines:
            f.write(ln + '\n')
    print('words=%d lines=%d -> %s' % (len(tables.words), len(lines), out_path))


if __name__ == '__main__':
    main()
