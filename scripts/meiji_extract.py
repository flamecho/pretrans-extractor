"""明治活劇 ハイカラ流星組 (NS-JP) テキスト抽出.

【正文】Data/SCD/CHAP####.lzs を LZSS 解凍したもの:
    [0x00] u32x4 ヘッダ, [0x10] 名前(0xFF pad), [u32@0x04]=b から
    コマンド列 <u16 tag><u16 size(自身含む)><payload>
    tag 0x10/0x11 = メッセージノード:
        payload = <u32 話者ID> + <u16 len><utf8> x3 = [ボイスID][名札][本文]
【選択肢】CORE (Data/CORE.lzs 解凍, 161MB) の 0x99e7000 付近:
    レコード <u32 len><u32 スロットID><utf8 len バイト> が連続。
本文中の制御: '%'=姓(芳川), '&'=名(けい), '\\'=框内改行(合并),
             '$'/'#'=用語マーカー, '+'=姓名区切り。
"""
import struct, glob, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meiji_lzs

SURNAME = '芳川'
GIVEN = 'けい'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, '_work_meiji')
SCD_DIR = os.path.join(WORK, 'scd')
CORE = os.path.join(WORK, 'CORE')
OUT = os.path.join(ROOT, '提取结果', '[NS-JP]明治活劇 ハイカラ流星組_全文本.txt')

# 原作の誤り（閉じ括弧欠落）— 整行定値表で修正（正则で泛修しない）
LINE_FIX = {
    '（京呉服の「に乃屋」ね……楓花ちゃんから話を\u3000聞いていないから、'
    'たぶんお祖母様からは何も\u3000聞けなかったんだろうな……':
    '（京呉服の「に乃屋」ね……楓花ちゃんから話を\u3000聞いていないから、'
    'たぶんお祖母様からは何も\u3000聞けなかったんだろうな……）',
}

CORE_OPT_START = 0x99e7000
CORE_OPT_END = 0x99eb000


def cmds(o):
    b = struct.unpack('<I', o[4:8])[0]
    p = b
    out = []
    while p + 4 <= len(o):
        tag, size = struct.unpack('<HH', o[p:p + 4])
        if size < 4 or p + size > len(o):
            break
        out.append((p, tag, size))
        p += size
    return out


def read_strs(o, p, end):
    r = []
    while p + 2 <= end:
        L = struct.unpack('<H', o[p:p + 2])[0]
        if L < 1 or p + 2 + L > end:
            break
        try:
            t = o[p + 2:p + 2 + L].decode('utf-8')
        except UnicodeDecodeError:
            break
        if '\ufffd' in t:
            break
        r.append(t.rstrip('\x00'))
        p += 2 + L
    return r


def clean(t):
    t = t.replace('%', SURNAME).replace('&', GIVEN)
    t = t.replace('\\', '')      # 框内改行 -> 合并
    t = t.replace('$', '').replace('#', '')   # 用語マーカー
    t = t.replace('+', '')       # 姓名区切り
    return t.strip('\x00')


def extract_scd(path):
    o = open(path, 'rb').read()
    lines = []
    for p, tag, size in cmds(o):
        if tag not in (0x10, 0x11):
            continue
        ss = read_strs(o, p + 14, p + size)
        if len(ss) < 3:
            continue
        t = clean(ss[2])
        t = LINE_FIX.get(t, t)
        if t:
            lines.append(t)
    return lines


def extract_core_options():
    o = open(CORE, 'rb').read()
    end = min(CORE_OPT_END, len(o))
    out = []
    i = CORE_OPT_START
    while i < end - 8:
        L, slot = struct.unpack('<II', o[i:i + 8])
        if 2 <= L <= 400 and i + 8 + L <= end:
            b = o[i + 8:i + 8 + L]
            try:
                t = b.decode('utf-8')
            except UnicodeDecodeError:
                t = None
            if (t and not any(ord(c) < 0x20 for c in t)
                    and any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in t)):
                out.append(clean(t))
                i += 8 + L
                continue
        i += 1
    return out


def main():
    files = sorted(glob.glob(os.path.join(SCD_DIR, 'CHAP*')),
                   key=lambda f: int(os.path.basename(f)[4:] or 0))
    lines = []
    for f in files:
        lines.extend(extract_scd(f))
    opts = extract_core_options()
    lines.extend(opts)
    with open(OUT, 'wb') as fp:
        fp.write(b'\xef\xbb\xbf')
        fp.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('scd files', len(files), 'body', len(lines) - len(opts),
          'options', len(opts), 'total', len(lines))


if __name__ == '__main__':
    main()
