#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KiriKiri/KAG3 シナリオ(.ks) テキスト抽出。

方針（skill の L0/L1 ルールに準拠）:
- クリック境界 = コードレベル判拠: `[cm]` / `[ct]` タグ、および `plc` マクロ
  (マクロ定義: `[l]\[label]\[ct]` ⇒ `[ct]`=クリア+待ち ⇒ 境界)。
- 1クリック=1テキストボックス=1行。ボックス内改行(`[l]`/ソース改行/`\`継続)は
  すべて同一行へマージ(分割しない)。
- タグは除去。ただし `[font ...]…[resetfont]` の内側テキスト、
  `[ruby text=…]漢字` のベース文字は保持。
- 話者: `[名前]NAME[名後]` は同ボックス内に名前をインライン表示⇒
  名前+台詞を同行へ結合。
- 選択肢: `[選択肢始め]…[選択肢 target=…] TEXT[選択済み]…[選択肢終わり]`
  ⇒ 各選択肢を1行ずつ(順序通り)出力。
- システムUI・コメント(`;`)・ラベル(`*`)・`@`コマンド行は除外。
"""
import struct, zlib, os, re, sys, io

# ---------- 最小 XP3 リーダ (scripts/xp3.py と同仕様) ----------
class XP3:
    def __init__(self, path):
        self.data = open(path, 'rb').read()
        self.files = {}
        self._parse()

    def _find_index(self):
        d = self.data
        cands = []
        v = struct.unpack_from('<Q', d, 0x20)[0]
        if 0 < v < len(d):
            cands.append(v)
        start = max(0, len(d) - 2_000_000)
        i = start
        while i < len(d) - 2:
            if d[i] == 0x78 and d[i+1] in (0x01, 0x5e, 0x9c, 0xda):
                cands.append(i)
            i += 1
        for c in cands:
            for k in range(0, 64):
                p = c + k
                if p >= len(d):
                    break
                if d[p] == 0x78 and d[p+1] in (0x01, 0x5e, 0x9c, 0xda):
                    try:
                        out = zlib.decompressobj().decompress(d[p:])
                        if out[:4] == b'File':
                            return out
                    except Exception:
                        pass
        raise RuntimeError('index not found')

    def _parse(self):
        out = self._find_index()
        p = 0
        while p + 12 <= len(out):
            tag = out[p:p+4]
            size = struct.unpack_from('<Q', out, p+4)[0]
            if tag != b'File':
                break
            payload = out[p+12:p+12+size]
            name, segs = self._parse_file(payload)
            if name is not None:
                self.files[name] = segs
            p += 12 + size

    @staticmethod
    def _parse_file(payload):
        q, name, segs = 0, None, []
        while q + 12 <= len(payload):
            tag = payload[q:q+4]
            size = struct.unpack_from('<Q', payload, q+4)[0]
            sp = payload[q+12:q+12+size]
            if tag == b'info':
                nlen = struct.unpack_from('<H', sp, 20)[0]
                name = sp[22:22+nlen*2].decode('utf-16-le', 'replace')
            elif tag == b'segm':
                for i in range(0, len(sp)-27, 28):
                    _, off, a, b = struct.unpack_from('<IQQQ', sp, i)
                    segs.append((off, b, a))
            q += 12 + size
        return name, segs

    def read(self, name):
        buf = bytearray()
        for off, comp, orig in self.files[name]:
            raw = self.data[off:off+comp]
            if comp == 0:
                continue
            if comp == orig:
                buf += raw
            else:
                try:
                    buf += zlib.decompress(raw)
                except Exception:
                    buf += raw
        return bytes(buf)

# ---------- 抽出 ----------
# 境界タグ
BOUNDARY = {'[cm]', '[ct]', '[plc]'}
# ボックス内で改行のみ(マージ対象)
INLINE_NL = {'[l]'}
# 単純除去タグ(属性/制御)。中身テキストは保持しない
DROP_TAGS = {
    '[resetfont]', '[er]', '[s]', '[nowait]', '[endnowait]', '[r]',
    '[select]', '[noselect]', '[ct]', '[cm]', '[plc]', '[l]',
    '[選択肢始め]', '[選択肢終わり]', '[選択済み]', '[名前]', '[名後]',
    '[名前大]', '[名後大]',
}
NAME_OPEN = '[名前]'
NAME_CLOSE = '[名後]'
CHOICE_OPEN = '[選択肢始め]'
CHOICE_CLOSE = '[選択肢終わり]'
CHOICE_OPT = '[選択肢'

def tokenize(logical_line):
    """[...] タグと @コマンドとテキストに分割。"""
    toks = []
    i = 0
    n = len(logical_line)
    while i < n:
        c = logical_line[i]
        if c == '[':
            j = logical_line.find(']', i)
            if j == -1:
                toks.append(('text', logical_line[i:]))
                break
            toks.append(('tag', logical_line[i:j+1]))
            i = j + 1
        elif c == '@':
            # @コマンド: コマンド名＋引数(=システム属性)をまとめて除去。
            # 次の '[' または行末までを @文として丸ごと落とす(引数リーク防止)。
            k = logical_line.find('[', i + 1)
            if k == -1:
                k = n
            toks.append(('at', logical_line[i:k]))
            i = k
        else:
            j = i
            while j < n and logical_line[j] not in '[@':
                j += 1
            toks.append(('text', logical_line[i:j]))
            i = j
    return toks

def clean_text(s):
    s = s.replace('\r', '').replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def extract_ks(text):
    """1 .ks のテキストを行リストで返す。"""
    out = []
    # 物理行 -> 継続 `\` で結合
    # ただしコメント(`;`)・ラベル(`*`)・@コマンド行は結合に参加させず除去
    # (コメント行が `\` で終わると次の台詞行とくっつき、丸ごと除去されて台詞が消えるのを防ぐ)
    raw_lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    logi = []
    buf = ''
    for ln in raw_lines:
        s = ln.strip()
        is_skip = s.startswith(';') or s.startswith('*') or s.startswith('@')
        if is_skip:
            if buf:
                logi.append(buf)
                buf = ''
            continue
        if ln.endswith('\\'):
            buf += ln[:-1]
        else:
            buf += ln
            logi.append(buf)
            buf = ''
    if buf:
        logi.append(buf)

    cur_box = []          # 現在のボックスのテキストチャンク
    cur_name = None       # 現在の話者
    in_choice = False
    choices = []          # 集めた選択肢
    cur_choice = None     # 構築中の選択肢

    def finalize_box():
        nonlocal cur_name
        txt = clean_text(''.join(cur_box))
        cur_box.clear()
        if txt:
            line = (cur_name + txt) if cur_name else txt
            out.append(line)
        cur_name = None

    for ll in logi:
        s = ll.strip()
        if not s:
            continue
        # コメント / ラベル / @コマンド行 は除外
        if s.startswith(';'):
            continue
        if s.startswith('*'):
            continue
        if s.startswith('@'):
            # @cm / @ct は境界(この作品では未使用だが念のため)
            low = s.lstrip('@').split()[0] if s.lstrip('@') else ''
            if low in ('cm', 'ct'):
                finalize_box()
            continue

        toks = tokenize(ll)
        for kind, val in toks:
            if kind == 'at':
                continue
            if kind == 'tag':
                # 境界判定
                if val in BOUNDARY:
                    finalize_box()
                    continue
                if val == CHOICE_OPEN:
                    in_choice = True
                    choices = []
                    cur_choice = None
                    continue
                if val == CHOICE_CLOSE:
                    in_choice = False
                    for ch in choices:
                        if ch:
                            out.append(ch)
                    choices = []
                    cur_choice = None
                    continue
                if val.startswith(CHOICE_OPT):
                    cur_choice = []   # 新しい選択肢構築開始
                    continue
                if val == '[選択済み]':
                    if cur_choice is not None:
                        choices.append(clean_text(''.join(cur_choice)))
                        cur_choice = None
                    continue
                if val == NAME_OPEN:
                    cur_name = ''   # 名前取得モード(次テキスト)
                    continue
                if val == NAME_CLOSE:
                    cur_name = clean_text(cur_name) if cur_name else ''
                    continue
                # ruby タグ: 中身(ベース文字)は次トークンで来るので除去のみ
                if val.startswith('[ruby'):
                    continue
                if val == '[/ruby]':
                    continue
                # font 等のスタイルタグ: 除去のみ(内側テキストは保持)
                # その他のタグも除去
                continue
            else:  # text
                if not val:
                    continue
                # ASCII [] は KAG タグ専用。台詞には出ないので除去(著者のタイポ等)
                val = val.replace('[', '').replace(']', '').replace('\\', '')
                if not val:
                    continue
                # インラインコメント(`;…`)・ラベル(`*…`)は除去
                if val.startswith(';') or val.startswith('*'):
                    continue
                if in_choice:
                    if cur_choice is not None:
                        cur_choice.append(val)
                    # 選択肢外のテキストは無視
                    continue
                if cur_name is not None and cur_name == '':
                    # 名前取得中
                    cur_name = val
                    continue
                cur_box.append(val)
    # 末尾ボックス
    finalize_box()
    return out

STORY_FILES = [
    'scenario/オープニング.ks',
    'scenario/共通ルート.ks',
    'scenario/ウイトリルート.ks',
    'scenario/クリアルート.ks',
    'scenario/ノイズルート.ks',
    'scenario/紅雀ルート.ks',
    'scenario/エンディングリスト.ks',
    'scenario/おまけ.ks',
]

# システム属性がリークした行を弾くための安全網(これらは台詞に絶対出ない)
LEAK_MARKERS = ('storage=', 'layer=', 'page=', 'visible=', 'vertical=',
               'backvisible=', 'left=', 'top=', 'opacity=', 'frame=',
               'cond=', 'target=', 'buf=', 'sysbtn', 'exp=', 'edgecolor=',
               'face=', 'size=', 'color=', 'method=', 'time=', 'repage=')

def main():
    xp3path = sys.argv[1]
    outpath = sys.argv[2]
    xp = XP3(xp3path)
    all_lines = []
    for f in STORY_FILES:
        if f not in xp.files:
            print('WARN missing', f)
            continue
        raw = xp.read(f)
        try:
            t = raw.decode('cp932')
        except UnicodeDecodeError:
            t = raw.decode('utf-8', 'replace')
        ls = extract_ks(t)
        for ln in ls:
            # 安全網: システム属性文字列を含む(台詞にあり得ない)行は除外
            if any(m in ln for m in LEAK_MARKERS):
                continue
            all_lines.append(ln)
        print('  %-22s -> %d lines' % (f.split('/')[-1], len(ls)))
    # 空行除去・重複連続は残す(意味がある可能性)
    body = '\n'.join(all_lines)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write(body + '\n')
    print('TOTAL %d lines -> %s' % (len(all_lines), outpath))

if __name__ == '__main__':
    main()
