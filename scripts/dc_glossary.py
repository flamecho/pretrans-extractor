# -*- coding: utf-8 -*-
"""デス・コネクション ポータブル —— 用語辞典（fid 22 見出し語表 ＋ fid 23 解説チャンク）

fid 22（サムネイル説明＋用語見出し語表）:
  見出し語表 @0xa2000+0x1000、slot 0x68B：+0x0C から cp932 見出し語 NUL 終端、
  slot 内に `note_NN`（＝解説グループ id）。表はファイル宣言サイズを越えて次クラスタ境界まで続く。
fid 23（解説＋おまけボイス）:
  解説チャンク @0xa4800+0x800、slot 0x32B：`[u16 group][u16 1][u16 first]` ＋ 本文（～NUL, 0xFF 埋め）。
  同一 group の連続チャンクを連結＝1 項目の解説（表示は 21B 折返し）。
  チャンク列は `u16@+2 != 1` に当たった所で終了（以降はおまけボイス台詞）。
"""
import struct, re, os, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HOME, '_work_dc/PSP_GAME/USRDIR/UNION/SCRIPT.UNI')
OUT = os.path.join(HOME, '_work_dc/glossary.txt')
F22, S22 = 0xa2000, 9264
F23, S23 = 0xa4800, 45584
NEXT22 = F23                      # fid22 的数据（含簇尾）到 fid23 起点


def terms():
    p = open(SRC, 'rb').read()[F22:NEXT22]
    a = 0x1000
    out = []
    while a + 0x68 <= len(p):
        seg = p[a:a + 0x68]
        m = re.search(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc])+', seg[0x0c:0x40])
        nm = re.match(rb'note_(\d+)', seg[0x5e:0x68])
        if not m or not nm:
            a += 0x68
            continue
        try:
            t = m.group().decode('cp932')
        except Exception:
            a += 0x68
            continue
        nid = int(nm.group(1))
        out.append((nid, t))
        a += 0x68
    # fid 23 头部 4 个追加词条（0x68 槽，note_59..62）
    q = open(SRC, 'rb').read()[F23:F23 + 0x1a4]
    a = 0
    while a + 0x68 <= len(q):
        seg = q[a:a + 0x68]
        nm = re.search(rb'note_(\d+)', seg)
        mm = None
        for m2 in re.finditer(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc])+', seg[:0x50]):
            if m2.start() < 0x04:
                continue
            try:
                t2 = m2.group().decode('cp932')
            except Exception:
                continue
            if re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', t2):
                mm = m2
                break
        if mm and nm:
            out.append((int(nm.group(1)), mm.group().decode('cp932')))
        a += 0x68
    return out


def explain():
    p = open(SRC, 'rb').read()[F23:F23 + S23]
    groups = []           # [(id, text)]
    # first chunk: 14B 头
    tid = struct.unpack_from('<H', p, 0x808)[0]
    cur = [p[0x80e:0x834].split(b'\x00')[0].decode('cp932', 'replace')]
    a = 0x83a
    while a + 0x32 <= len(p):
        g, one, first = struct.unpack_from('<HHH', p, a)
        if one != 1:
            break
        raw = p[a + 6:a + 0x32].split(b'\x00')[0]
        try:
            s = raw.decode('cp932')
        except Exception:
            break
        if not s or '#n' in s:
            break
        if g != tid:
            groups.append((tid, ''.join(cur)))
            tid, cur = g, [s]
        else:
            cur.append(s)
        a += 0x32
    groups.append((tid, ''.join(cur)))
    return groups


def main():
    T = dict(terms())
    G = dict(explain())
    print('terms', len(T), 'groups', len(G), file=sys.stderr)
    hit = 0
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        for nid in sorted(G):
            t = T.get(nid)
            if not t:
                print('  [no term] id', nid, G[nid][:30], file=sys.stderr)
                continue
            hit += 1
            f.write('【%s】%s\n' % (t, G[nid]))
    print('written', hit, '->', OUT, file=sys.stderr)


if __name__ == '__main__':
    main()
