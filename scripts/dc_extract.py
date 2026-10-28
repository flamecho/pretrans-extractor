# -*- coding: utf-8 -*-
"""デス・コネクション ポータブル（PSP ULJM05823 / Otomate 2011）
UNI2 -> STCM2L -> .evb 相当のスクリプト -> テキスト

容器：PSP_GAME/USRDIR/UNION/SCRIPT.UNI = CRI UNI2
  头：UNI2 + 0x10000 + count(698) + 1 + 7
  FAT@0x800：16B/条 [FileID][startCluster][sizeClusters][sizeBytes]
  绝对偏移 = 0x800 + startCluster*0x800；子文件前缀区 = 0x3000（STCM2L 在 +0x3000）
  STCM2L 生成串：Oct 13 2009 13:07:22（多数）、Jan 27 2006 / Jan 23 2007 / Minku 07.0（少量）

记录：payload = [u32 addr][u32 style]*n [u32 0][u32 L/4][u32 1][u32 L][cp932 text][u32 0][u32 cmd][u32 flag]
  端锚定：末 12B = [0][cmd][flag]；k + 16 + L == len-12
  k==12 cmd==0xd2 flag=1 = 同框软换行（续行）
  k==12 cmd==0xd3 flag=0 = 框末（一次点击）
  其余 k==12 且含日文 = 特殊文本框（各自成行）
  选项：k!=12 cmd 0xe6(末项)/0xe7(非末项)，组末跟 cmd 0x34 'select'
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HOME, '_work_dc/PSP_GAME/USRDIR/UNION/SCRIPT.UNI')
OUT = os.path.join(HOME, '提取结果/[PSP-JP]デス・コネクション ポータブル.txt')
FAT, BASE, PREFIX = 0x800, 0x800, 0x3000
PROTAG = 'アメリア'

JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
MACRO = re.compile(r'#(?:Name\[\d+\]|Color\[\d+\]|Scale\[[^\]]*\])')

NAMES = set("""
ヨシュア メディシス レオナルド ヴィシャス グロリア ジャン ニコール ルチアーノ
ニコラス グィード ダレンツィオ セルビア カストロ クラウディア 神父 キーラ
フィリッポ レナード ランベルト レミィ
店員 男 マスター 女性 グィードの部下 部下 声 シスター マフィアＡ 子供 マフィアＢ
祖母 派手な女性 派手な女 街の人 部下Ａ 同僚の刑事 レナードの部下 グィードの部下Ａ
警官 医者 男性 店長 グィードの部下Ｂ 執事 子供達 マダム 金髪の男 怪しい男 銀行員
若い女 赤髪の男 大人しい子 女の人 中世の女 部下Ｂ 威勢のいい女 男の子 女の子
中世の男 グィード部下Ａ 男Ｂ 新しい母親 クラスメイト 不動産 グィード部下Ｂ 一同
男Ａ コック 鑑賞に来た女性 案内係 男性Ａ 男性Ｂ マフィアＣ 女性の声 マフィア部下Ｃ
ウェイトレス グロリアの父 クラウディアの部下
""".split())

INLINE_PLATE = re.compile(r'^([\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3005ー]{1,10})(「|『)(.*)(」|』)$')
CHAPTER = re.compile(r'^(序章|プロローグ|最終章|第[一二三四五六七八九十０-９0-9]+章|[０-９0-9]+章)(\u3000.*)?$')
NAV_OPT = {'他の人へ', '最初に戻る'}


def load(path=SRC):
    d = open(path, 'rb').read()
    n = struct.unpack_from('<I', d, 8)[0]
    ents = []
    for i in range(n):
        fid, sc, scl, sb = struct.unpack_from('<IIII', d, FAT + 16 * i)
        if sb:
            ents.append((fid, BASE + sc * 0x800, sb))
    starts = sorted(e[1] for e in ents) + [len(d)]

    def fend(fs):
        return next(s for s in starts if s > fs) + PREFIX

    yes = set(os.environ.get('DC_FIDS', '').split(',')) - {''}
    files = [(fid, fs, fend(fs)) for fid, fs, sb in ents]
    if yes:
        files = [f for f in files if str(f[0]) in yes]
    return d, files


def file_ops(d, fs, fe):
    if d[fs + PREFIX:fs + PREFIX + 6] not in (b'STCM2L', b'STCM2 '):
        return []
    c = d.find(b'CODE_START_\0', fs + PREFIX, fe)
    if c < 0:
        return []
    i, out = c + 24, []
    while i + 4 <= fe:
        bs = struct.unpack_from('<I', d, i)[0]
        if bs == 0 or bs % 4 or i + bs > fe:
            break
        out.append(d[i + 4:i + bs])
        i += bs
    return out


def rec_of(pay):
    n = len(pay)
    if n < 28:
        return None
    if pay[n - 12:n - 8] != b'\x00\x00\x00\x00' and pay[n - 12:n - 8] != b'\x01\x00\x00\x00':
        return None
    cmd, flag = struct.unpack_from('<II', pay, n - 8)
    for k in range(12, min(n - 16, 208), 4):
        if pay[k:k + 4] != b'\x00\x00\x00\x00':
            continue
        nn, one, L = struct.unpack_from('<III', pay, k + 4)
        if one != 1 or L < 4 or L > 0x2000 or L % 4 or nn != L // 4:
            continue
        if k + 16 + L != n - 12:
            continue
        raw = pay[k + 16:n - 12].rstrip(b'\x00')
        while raw and raw[-1] < 0x20:
            raw = raw[:-1]
        if not raw or any(b >= 0xfd for b in raw) or any(b < 0x20 for b in raw):
            return None
        try:
            s = raw.decode('cp932')
        except Exception:
            return None
        if not s or '\ufffd' in s or any(ord(c) < 0x20 for c in s):
            return None
        return (k, s, cmd, flag)
    return None


def clean(s):
    s = s.replace('#Name[1]', PROTAG)
    s = MACRO.sub('', s)
    return s.strip()


def main():
    d, files = load()
    lines, opts = [], []
    st = collections.Counter()
    for fid, fs, fe in files:
        buf = []
        fopts = set()
        for pay in file_ops(d, fs, fe):
            r = rec_of(pay)
            if not r:
                continue
            k, s, cmd, flag = r
            t = s.strip()
            if not JP.search(t):
                continue
            if k != 12:
                if cmd in (0xe6, 0xe7):
                    if buf:
                        lines.append(''.join(buf)); buf = []
                    t2 = clean(s)
                    if t2 and t2 not in NAV_OPT and t2 not in fopts:
                        fopts.add(t2)
                        lines.append(t2); st['opt'] += 1
                elif CHAPTER.match(t):
                    if buf:
                        lines.append(''.join(buf)); buf = []
                    lines.append(t); st['title'] += 1
                continue
            if t in ('処理開始', '処理開始\\n', 'select', 'コンタクトハート開始'):
                st['sym'] += 1
                continue
            if t in NAMES:                     # 名札（独立名窓）→ 整行丢弃；名字出现＝换框
                if buf:
                    lines.append(''.join(buf)); buf = []
                st['name'] += 1
                continue
            mo = INLINE_PLATE.match(s)
            if mo and mo.group(1) in NAMES:
                s = s[len(mo.group(1)):]
                st['inline'] += 1
            t2 = clean(s)
            if not t2:
                continue
            buf.append(t2)
            if cmd != 0xd2:
                lines.append(''.join(buf)); buf = []
                st['frame'] += 1
        if buf:
            lines.append(''.join(buf))

    out = [l.strip() for l in lines if l.strip()]
    # 相邻完全重复行去重
    ded = []
    for l in out:
        if ded and ded[-1] == l:
            st['dup'] += 1
            continue
        ded.append(l)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # 用語辞典（fid22 見出し語表 ＋ fid23 解説チャンク）を末尾に併合
    gl = os.path.join(HOME, '_work_dc/glossary.txt')
    if os.path.exists(gl):
        gloss = [l.rstrip('\n') for l in open(gl, encoding='utf-8') if l.strip()]
    else:
        gloss = []
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(ded + gloss) + '\n')
    print('stats', dict(st), 'lines', len(ded), 'opts', len(opts))
    print('->', OUT)


if __name__ == '__main__':
    main()
