#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クリムゾン・ロワイヤル (QuinRose, 2009 / KiriKiri KAG3, DropWave OTag system)
全テキスト抽出器

入力: xp3 を展開したディレクトリ (appscenario.xp3 / appdata.xp3 / data.xp3 / respatch.xp3 ...)
出力: 全文本.txt / 資料・システムテキスト.txt

使い方:
  python crimson_royale_extract.py <xp3_dir> <out_dir>

メモ:
 - .ks は zlib 圧縮 + UTF-16LE (BOM付) の KAG3 スクリプト。
 - [message window="…"] … [/message] ブロック = プレイヤーの1クリック = 1行。
   ブロック内 [br] は同一画面内の改行 → 連結。window/name/face/voice 属性は
   （表示は画像 or ボイス）なのでテキストには出さない。
 - [firstname]/[familyname] = 主人公名（既定 シエラ / ロザン、PlayDataManager.tjs より）
 - [select word="…" file="…"] = 選択肢ボタン。word をその位置に1行で出す。
 - CSV 群は GBK エンコード（漢化ツールチェーンの名残）だが中身は日本語。
"""
import struct, zlib, os, sys, re, io, csv, glob, unicodedata

# ---------------------------------------------------------------- XP3 reader
class XP3:
    """KiriKiri XP3 (File/info/segm/adlr タグ式インデックス)."""

    def __init__(self, path):
        self.data = open(path, 'rb').read()
        self.files = {}
        self._parse()

    def _read_index(self):
        d = self.data
        if d[:3] != b'XP3':
            raise ValueError('not XP3: %s' % self.path)
        dir_off = struct.unpack_from('<Q', d, 0x0b)[0]
        for k in range(0, 48):
            if d[dir_off + k] == 0x78 and d[dir_off + k + 1] in (0x01, 0x5e, 0x9c, 0xda):
                try:
                    return zlib.decompress(d[dir_off + k:])
                except Exception:
                    continue
        raise RuntimeError('index zlib not found')

    def _parse(self):
        out = self._read_index()
        p = 0
        while p + 12 <= len(out):
            tag = out[p:p + 4]
            size = struct.unpack_from('<Q', out, p + 4)[0]
            if tag != b'File':
                break
            payload = out[p + 12:p + 12 + size]
            name, segs = self._parse_file(payload)
            if name is not None:
                self.files[name] = segs
            p += 12 + size

    @staticmethod
    def _parse_file(payload):
        q, name, segs = 0, None, []
        while q + 12 <= len(payload):
            tag = payload[q:q + 4]
            size = struct.unpack_from('<Q', payload, q + 4)[0]
            sp = payload[q + 12:q + 12 + size]
            if tag == b'info':
                nlen = struct.unpack_from('<H', sp, 20)[0]
                name = sp[22:22 + nlen * 2].decode('utf-16-le', 'replace')
            elif tag == b'segm':
                for i in range(0, len(sp), 28):
                    _, off, a, _b = struct.unpack_from('<IQQQ', sp, i)
                    segs.append((off, a))
            q += 12 + size
        return name, segs

    def read(self, name):
        buf = bytearray()
        for off, size in self.files[name]:
            buf += self.data[off:off + size]
        return bytes(buf)


# ---------------------------------------------------------------- text tools
TAG_RE = re.compile(r'\[[^\]]*\]')
MSG_RE = re.compile(r'\[message\b[^\]]*\](.*?)\[/message\]|\[select\b([^\]]*)\]', re.S)
WORD_RE = re.compile(r'word="([^"]*)"')


def decode_text(b):
    """zlib 解除 + UTF-16LE/CP932 判定."""
    if b[:1] == b'\x78':
        try:
            b = zlib.decompress(b)
        except Exception:
            pass
    for enc in ('utf-16-le', 'cp932', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('cp932', 'replace')


def decode_csv(b):
    for enc in ('gbk', 'cp932', 'utf-8'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('gbk', 'replace')


def clean_msg(body):
    # KAG コメント行 (行頭が ';') は表示されないので落とす
    body = '\n'.join(ln for ln in body.split('\n') if not ln.strip().startswith(';'))
    s = body
    s = s.replace('[firstname]', 'シエラ').replace('[familyname]', 'ロザン')
    # 前作テンプレート由来の生プレースホルダ（エンジンは置換しない）
    s = s.replace('【主人公の名前】', 'シエラ')
    s = TAG_RE.sub('', s)                      # 残りの演出タグを除去
    s = s.replace('\r', '').replace('\n', '').replace('\t', '')
    return s.strip()


def extract_script(text):
    """1ファイルから [message] 本文と [select] 選択肢を順に取り出す."""
    out = []
    for m in MSG_RE.finditer(text):
        if m.group(1) is None:                 # select
            w = WORD_RE.search(m.group(2) or '')
            if w:
                t = clean_msg(w.group(1))
                if t:
                    out.append(t)
        else:
            t = clean_msg(m.group(1))
            if t:
                out.append(t)
    return out


def norm(name):
    return unicodedata.normalize('NFKC', name.strip())


# ---------------------------------------------------------------- main
def main():
    xp3_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    app = XP3(os.path.join(xp3_dir, 'appscenario.xp3'))
    resp = XP3(os.path.join(xp3_dir, 'respatch.xp3'))
    appdata = XP3(os.path.join(xp3_dir, 'appdata.xp3'))

    # ファイル名 -> (XP3, 実名)  : appscenario 優先、無ければ respatch
    scripts = {}
    for nm in resp.files:
        if nm.lower().endswith('.ks'):
            scripts.setdefault(os.path.basename(nm), (resp, nm))
    for nm in app.files:
        if nm.lower().endswith('.ks'):
            scripts[os.path.basename(nm)] = (app, nm)   # appscenario が上書き

    by_norm = {norm(k): k for k in scripts}

    # --- シナリオ順 (scenarioindex.txt = ALL_SCENARIOPLAY の再生順) ---
    idx_txt = decode_text(app.read('scenarioindex.txt'))
    order = []
    for line in idx_txt.splitlines():
        line = norm(line)
        if not line:
            continue
        real = by_norm.get(line)
        if real and real not in order:
            order.append(real)

    # 索引に無いファイル (appscenario の残り → respatch の残り)
    app_only = [os.path.basename(n) for n in app.files
                if n.lower().endswith('.ks') and os.path.basename(n) not in order]
    res_only = [os.path.basename(n) for n in resp.files
                if n.lower().endswith('.ks') and os.path.basename(n) not in order]
    app_only.sort()
    res_only.sort()

    main_lines = []
    stats = []
    for group, names in (('本体', order), ('本体(未索引)', app_only), ('追加(respatch)', res_only)):
        cnt = 0
        for base in names:
            x, real = scripts[base]
            lines = extract_script(decode_text(x.read(real)))
            main_lines.extend(lines)
            cnt += len(lines)
        stats.append((group, len(names), cnt))

    # --- ショートシナリオ / 教程 (messagedata.csv) ---
    csv_dir = {}
    for nm in appdata.files:
        if nm.lower().endswith('.csv'):
            csv_dir[os.path.basename(nm)] = decode_csv(appdata.read(nm))

    def rows(name):
        if name not in csv_dir:
            return []
        return list(csv.reader(io.StringIO(csv_dir[name])))

    msg_rows = rows('messagedata.csv')
    shsc_rows = rows('shortscenariodata.csv')

    # 用途タイトル → メッセージ番号
    uses = {}
    for r in shsc_rows[1:]:
        if len(r) >= 2 and r[0].strip():
            uses.setdefault(r[1].strip(), []).append(r[0].strip())

    short_lines, short_blocks = [], []
    for r in msg_rows[1:]:
        if len(r) < 6 or not r[5].strip():
            continue
        no = r[0].strip()
        title = ' / '.join(uses.get(no, []))
        t = clean_msg(r[5])
        if t:
            short_lines.append(t)
            short_blocks.append((title, t))

    # --- 資料 (データテキスト) ---
    def col(rs, i):
        return [r[i].strip() for r in rs[1:] if len(r) > i and r[i].strip()]

    def pairs(rs, i, j):
        out = []
        for r in rs[1:]:
            if len(r) > j and r[i].strip() and r[j].strip():
                out.append((r[i].strip(), r[j].strip()))
        return out

    items = pairs(rows('itemdata.csv'), 1, 3)
    skills = pairs(rows('skilldata.csv'), 1, 3)
    quests = pairs(rows('questdata.csv'), 3, 4)
    monsters = col(rows('monsterdata.csv'), 1)
    fields = col(rows('fielddata.csv'), 1)

    # ------------------------------------------------------------- 書き出し
    all_txt = os.path.join(out_dir, 'クリムゾン・ロワイヤル_全文本.txt')
    with open(all_txt, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(main_lines) + '\n')

    ref_txt = os.path.join(out_dir, 'クリムゾン・ロワイヤル_資料・システムテキスト.txt')
    with open(ref_txt, 'w', encoding='utf-8-sig', newline='\n') as f:
        w = f.write
        w('=' * 60 + '\n')
        w('【ショートシナリオ・チュートリアル】(messagedata.csv)\n')
        w('=' * 60 + '\n')
        for title, t in short_blocks:
            w(t + '\n')
        w('\n')
        w('=' * 60 + '\n')
        w('【アイテム】\n')
        w('=' * 60 + '\n')
        for n, d in items:
            w('%s ── %s\n' % (n, d))
        w('\n')
        w('=' * 60 + '\n')
        w('【特技】\n')
        w('=' * 60 + '\n')
        for n, d in skills:
            w('%s ── %s\n' % (n, d))
        w('\n')
        w('=' * 60 + '\n')
        w('【クエスト】\n')
        w('=' * 60 + '\n')
        for n, d in quests:
            w('%s ── %s\n' % (n, d))
        w('\n')
        w('=' * 60 + '\n')
        w('【モンスター】\n')
        w('=' * 60 + '\n')
        for n in monsters:
            w(n + '\n')
        w('\n')
        w('=' * 60 + '\n')
        w('【フィールド】\n')
        w('=' * 60 + '\n')
        for n in fields:
            w(n + '\n')

    # ------------------------------------------------------------- レポート
    print('=== シナリオ集計 ===')
    for g, nf, nl in stats:
        print('  %-16s files=%3d  lines=%6d' % (g, nf, nl))
    print('  合計                lines=%6d' % len(main_lines))
    print('=== ショートシナリオ lines=%d ===' % len(short_lines))
    print('=== 資料 items=%d skills=%d quests=%d monsters=%d fields=%d ==='
          % (len(items), len(skills), len(quests), len(monsters), len(fields)))
    print('書き出し:', all_txt)
    print('書き出し:', ref_txt)


if __name__ == '__main__':
    main()
