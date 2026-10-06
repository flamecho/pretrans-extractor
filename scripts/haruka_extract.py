"""Extractor for Koei / Ruby Party "Harukanaru Toki no Naka de" (遥かなる時空の中で) scripts.

Two container/encoding variants are handled:

A) PSV "Ultimate" ports (e.g. 遥か3 Ultimate, PCSG00992)
   script file: `<app>/EV/EVENTSCE.DAT`  -- plain Shift-JIS text records.

B) PSP 遥か4 / PSV 遥か Ultimate style
   遥か4 (PSP): script is a CDAR entry inside `PSP_GAME/USRDIR/DATA.BIN`
   (entry #2512).  Kana are stored as single-byte JIS X0201 katakana
   (0xA1-0xDF) which the game renders with a custom font page as HIRAGANA,
   while kanji/full-width kana use ordinary 2-byte Shift-JIS.
   NOTE: 遥か4 uses different opcodes/operands from 遥か3 (all `5b`/`5d`
   operands are u16, speaker/insert base 0x0248, 12x9 address matrix).
   Use `scripts/haruka4_extract.py` for it -- this module is 遥か3 only.

Shared bytecode subset (reverse-engineered):
    0x20 <len:u8> <text bytes>    -> append text to the current line
    0x25 <u16 LE>                 -> insert runtime variable (name / item / place);
                                     resolved via the game's string table
                                     (DATA.BIN entry 6003: 2000 records, each
                                     [name\0\0 kana-reading\0\0] = 4 null-split
                                     segments; id N -> segments [4N] / [4N+2]);
                                     unresolved -> emitted as PLACEHOLDER
    0x5d 00 00                    -> line break inside the same message
    0x5d XX 00  (XX != 0)         -> end of message -> flush one output line
    other bytes                   -> skipped
"""
import os
import re
import sys
import unicodedata

PLACEHOLDER = '〓'

# Dynamic name inserts (verified against game-displayed text):
#   5d 17 00            -> protagonist name (春日望美)
#   5b 16 00            -> 有川将臣 addressed form (将臣くん)
#   5d 17 00 5b 16 00   -> the pair inserts 将臣くん (user-verified game display)
NAME_PROTAGONIST = '望美'
NAME_MASARU = '将臣くん'

RE_BAD_ASCII = re.compile(r'[A-Za-z0-9\\\[\]{}~^|`_#<>&*@$%+=/]')
RE_JP = re.compile(r'[\u3041-\u309f\u4e00-\u9fff\u30a0-\u30ff]')
# JP punctuation that can legitimately form a whole text record (e.g. a lone 「、」)
RE_JP_PUNCT = re.compile(r'^[\u3000-\u303f\u30fb\u30fc\uff01-\uff65]+$')


def half_to_hira(b):
    """Single-byte JIS X0201 katakana byte -> the hiragana glyph it stands for."""
    ch = bytes([b]).decode('cp932')
    fw = unicodedata.normalize('NFKC', ch)
    if len(fw) == 1 and 0x30A1 <= ord(fw) <= 0x30F6:
        return chr(ord(fw) - 0x60)
    return fw


def decode_text(data):
    """Shift-JIS aware decode; 0xA1-0xDF lead bytes become hiragana."""
    out = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef:
            if i + 1 < n:
                try:
                    out.append(data[i:i + 2].decode('cp932'))
                except Exception:
                    pass
                i += 2
            else:
                i += 1
            continue
        if 0xa1 <= b <= 0xdf:
            out.append(half_to_hira(b))
            i += 1
            continue
        if 0x20 <= b < 0x7f:
            out.append(chr(b))
            i += 1
            continue
        i += 1
    s = ''.join(out)
    # game-font remaps: combined punctuation glyphs stored at rarely-used
    # SJIS symbol codes (user-verified in game: ＄ displays ！？, ￠ displays ！！)
    s = s.replace('＄', '！？')
    s = s.replace('￠', '！！')
    s = s.replace('￡', '？！')
    return s


def _valid(t):
    if not t:
        return None
    if '\ufffd' in t:
        return None
    if RE_BAD_ASCII.search(t):
        return None
    if RE_JP.search(t) is None and RE_JP_PUNCT.search(t) is None:
        return None
    return t


def load_varmap(table_path):
    """Parse the game's string table (DATA.BIN entry 6003).

    Layout: records of [name\0\0 kana-reading\0\0], i.e. 4 null-split
    segments per record.  Variable id N -> name = segment[4N].
    Returns {id: name_text}.
    """
    data = open(table_path, 'rb').read()
    parts = data.split(b'\x00')
    varmap = {}
    for pid in range(len(parts) // 4):
        name = parts[4 * pid]
        if name:
            varmap[pid] = decode_text(name)
    return varmap


def load_addrnames(table_path):
    """Parse the address-form matrix (DATA.BIN entry 4004).

    Layout (2026-09-29 reverse-engineering): a 24-column matrix
    M[person][target] of 16-byte null-padded SJIS records.
      M[0]   = protagonist row   (私 / 将臣くん / 九郎さん / ヒノエくん / ...)
      M[r][c]= how person r addresses person c; the SELF reference sits on
               the diagonal (M[r][r] = 私/俺/オレ/僕/...).
      col0   = how person r addresses the PROTAGONIST, e.g.
               M[1][0]='（望美）' (将臣), M[5][0]='（春日）先輩' (譲, school).
      （...） = runtime name-variable markers -> parentheses stripped.
    Script opcode `5b XX 00` inserts M[current_speaker][XX - 0x15], where the
    speaker row comes from the message header tag `5d 0d 00 5b A 00`.
    Returns the flat row-major list (row stride 24, index 0 == 私).
    """
    data = open(table_path, 'rb').read()
    s0 = data.find('ヒノエくん'.encode('cp932'))
    if s0 < 0:
        return []
    phase = s0 % 16
    # row0 col0 ('私') sits 3 records before ヒノエくん
    start = s0 - 3 * 16
    chk = data[start:start + 16].split(b'\x00')[0]
    if chk.decode('cp932', errors='replace') != '私':
        # fall back: walk backwards while records look like SJIS strings
        start = s0
        while start - 16 >= phase:
            blk = data[start - 16:start]
            t = blk.split(b'\x00')[0]
            if 0 < len(t) < 14 and (t[0] & 0x80):
                start -= 16
            else:
                break
    recs = []
    for off in range(start, len(data), 16):
        t = data[off:off + 16].split(b'\x00')[0]
        if len(t) < 1 or not (t[0] & 0x80):
            break
        nm = decode_text(t)
        # strip runtime name-variable markers: （望美）->望美, （春日）先輩->春日先輩
        if '（' in nm and '）' in nm:
            nm = nm.replace('（', '').replace('）', '')
        recs.append(nm)
    return recs


def _text_record(blob, i, n):
    """If a valid `0x20 <len> <text>` record starts at i, return (text, end_index)."""
    if blob[i] != 0x20 or i + 2 > n:
        return None
    L = blob[i + 1]
    if not (2 <= L <= 600) or i + 2 + L > n:
        return None
    t = _valid(decode_text(blob[i + 2:i + 2 + L]))
    if t is None:
        return None
    return t, i + 2 + L


def _emit_name(cur, name):
    """Append a dynamic name insert; collapse direct repeats (望美望美 -> 望美)."""
    if not cur or cur[-1] != name:
        cur.append(name)


def parse_messages(blob, varmap=None, addrnames=None):
    """Walk the event bytecode; return one string per message, in stream order.

    `0x20 [name]` immediately followed by `0x47 XX 00` is an inline speaker name
    and is dropped (output carries no speaker prefix).
    `0x25 <u16 id>` resolves through `varmap` when available.
    """
    n = len(blob)
    out = []
    cur = []
    i = 0
    dropped_names = 0
    names_in_line = 0
    speaker = 0  # address-matrix row of the current speaker (0 = protagonist)
    stride = 24  # address matrix row stride
    if addrnames is None:
        addrnames = []

    def _addr(col):
        """Address form: how the current speaker names person `col`."""
        idx = stride * speaker + col
        return addrnames[idx] if 0 <= idx < len(addrnames) else None

    while i < n:
        c = blob[i]
        if c == 0x20 and i + 2 <= n:
            rec = _text_record(blob, i, n)
            if rec is not None:
                t, j = rec
                if j + 3 <= n and blob[j] == 0x47:
                    dropped_names += 1
                    i = j + 3
                    continue
                cur.append(t)
                i = j
                continue
        if c == 0x25 and i + 3 <= n:
            nxt = _text_record(blob, i + 3, n)
            if cur or nxt is not None:
                if varmap:
                    vid = blob[i + 1] | (blob[i + 2] << 8)
                    cur.append(varmap.get(vid, PLACEHOLDER))
                else:
                    cur.append(PLACEHOLDER)
            i += 3
            continue
        if c == 0x5d and i + 3 <= n and blob[i + 1] == 0x0d and blob[i + 2] == 0x00:
            # 5d 0d 00 5b A 00 5d 0e 00 5b B 00 47 .. : message header tag;
            # A - 0x15 = address-matrix ROW of this message's speaker
            # (game-verified: tag 5b16 + insert 5b15 -> M[1][0]='（望美）',
            #  tag 5b1a + insert 5b15 -> M[5][0]='（春日）先輩').
            if i + 6 <= n and blob[i + 3] == 0x5b:
                sp = blob[i + 4] - 0x15
                if 0 <= sp < 200:
                    speaker = sp
                i += 6
                if i + 3 <= n and blob[i] == 0x5d and blob[i + 1] == 0x0e:
                    i += 3
                    if i + 3 <= n and blob[i] == 0x5b:
                        i += 3
                continue
            i += 3
            continue
        if c == 0x5d and i + 3 <= n and blob[i + 1] == 0x17 and blob[i + 2] == 0x00:
            # 5d 17 00: NOT a message end -- dynamic name insert.
            #  + 5b XX 00 -> M[speaker][XX-0x15] address-form insert
            #    (5d17 5b16 as protagonist -> 将臣くん, game-verified);
            #    the 5d17 itself is a silent prefix here.
            if i + 6 <= n and blob[i + 3] == 0x5b and blob[i + 5] == 0x00:
                nm = _addr(blob[i + 4] - 0x15)
                if nm:
                    _emit_name(cur, nm)
                    names_in_line += 1
                i += 6
            else:
                _emit_name(cur, NAME_PROTAGONIST)
                names_in_line += 1
                i += 3
            continue
        if c == 0x5b and i + 3 <= n and blob[i + 2] == 0x00:
            # 5b XX 00: address-form insert -- ONLY valid immediately after a
            # 5d 17 00 prefix (all game-verified dialogue inserts are paired;
            # bare 5b XX 00 bytes in junk/secondary regions are misaligned
            # resyncs and must NOT emit).  Skips:
            #  - followed by 47 YY 00 -> speaker tag (dropped, no prefix)
            #  - part of a dense 5b-run         -> registration template (skip)
            if i + 6 <= n and blob[i + 3] == 0x47:
                i += 3
                continue
            if i + 6 <= n and blob[i + 3] == 0x5b:
                i += 3
                continue
            i += 3
            continue
        if c == 0x5d and i + 3 <= n and blob[i + 2] == 0x00:
            if blob[i + 1] != 0x00:
                s = ''.join(cur).strip()
                # literal （望美） in text records = protagonist-name marker
                s = s.replace('（望美）', NAME_PROTAGONIST)
                # junk guard: registration-template blocks emit long runs of
                # bare name inserts / unresolved placeholders -- not dialogue.
                # A line that is ONLY a name (or only a placeholder) is a
                # speaker/address tag -> dropped per the no-prefix standard.
                if (s and s != PLACEHOLDER and s not in addrnames
                        and names_in_line < 3 and PLACEHOLDER not in s):
                    out.append(s)
                cur = []
                names_in_line = 0
            i += 3
            continue
        i += 1
    if cur:
        s = ''.join(cur).strip()
        s = s.replace('（望美）', NAME_PROTAGONIST)
        if (s and s != PLACEHOLDER and s not in addrnames
                and names_in_line < 3 and PLACEHOLDER not in s):
            out.append(s)
    return out


def write_lines(lines, out_path):
    with open(out_path, 'w', encoding='utf-8-sig') as f:
        for ln in lines:
            f.write(ln + '\n')


def from_event_sce(path, out_path, varmap=None, addrnames=None):
    lines = parse_messages(open(path, 'rb').read(), varmap, addrnames)
    write_lines(lines, out_path)
    return lines


def from_cdar_entry(cdar_path, index, out_path, varmap=None, addrnames=None):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cdar import CDAR
    blob = CDAR(cdar_path).data(index)
    lines = parse_messages(blob, varmap, addrnames)
    write_lines(lines, out_path)
    return lines


if __name__ == '__main__':
    if sys.argv[1] == '--cdar':
        ls = from_cdar_entry(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    else:
        ls = from_event_sce(sys.argv[1], sys.argv[2])
    print('lines=%d -> %s' % (len(ls), sys.argv[-1]))
