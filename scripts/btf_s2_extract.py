# -*- coding: utf-8 -*-
"""BUSTAFELLOWS シーズン2（NS-JP）全文本提取 —— 自研 UTXT 容器

容器 sk_ep0_text_2.bytes:
  0x00 "UTXT" | 0x04 u32 ver=1 | 0x08 u32 0x2A30CC(常量)
  0x0C u32 table_len(=0x8ED8)  → 表区 0x10..0x8ED4 + 尾部 "TEND"
  表 = varint(记录数) + 记录数×varint(记录字节长)   # 7bit 大端，首字节 msb=续
  body 0x8ED8..EOF = 记录首尾相接的字符索引流

字符表 = global-metadata.dat 第 94 号字符串字面量（3732 字：ASCII+SJIS 全集序）
码流:  0x00            → 框内换行
       0x01..0x7F      → 表索引 b-1
       0x81..0x9D + b2 → 表索引 (b1-0x81)*128 + (b2-1) + 128
"""
import struct, sys, os, re, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

META = os.path.join(VNTRANS_HOME, '_w_bf/romfs/Data/Managed/Metadata/global-metadata.dat')
SRC  = os.path.join(VNTRANS_HOME, '_w_bf/romfs/Data/StreamingAssets/sk_ep0_text_2.bytes')
LISTS = ['sk_ep0_body_2.txt','sk_ep0_effect_2.txt','sk_ep0_label_2.txt','sk_ep0_label_range_2.txt',
         'sk_ep0_loopsound_2.txt','sk_ep0_movie_2.txt','sk_ep0_music_2.txt','sk_ep0_name_2.txt',
         'sk_ep0_picture_2.txt','sk_ep0_sound_2.txt','sk_ep0_valuestorage_2.txt']
HERE = os.path.dirname(os.path.abspath(SRC))

def load_table():
    d = open(META,'rb').read()
    ln, idx = struct.unpack_from('<Ii', d, 0x100 + 8*94)
    return d[0x19e48+idx : 0x19e48+idx+ln].decode('utf-8')

T = load_table()

def decode(buf):
    out=[]; i=0; n=len(buf)
    while i < n:
        b=buf[i]
        if b == 0: out.append('\n'); i+=1
        elif b < 0x80: out.append(T[b-1]); i+=1
        else:
            k=(b-0x81)*128 + (buf[i+1]-1) + 128; i+=2
            out.append(T[k] if 0<=k<len(T) else '\u3013')
    return ''.join(out)

def records(path):
    d=open(path,'rb').read()
    assert d[:4]==b'UTXT', d[:4]
    tbl_end=struct.unpack_from('<I',d,0x0C)[0]
    assert d[tbl_end-4:tbl_end]==b'TEND'
    tbl=d[0x10:tbl_end-4]
    vals=[]; v=0
    for x in tbl:
        v=(v<<7)|(x&0x7f)
        if not x & 0x80: vals.append(v); v=0
    cnt=vals[0]; lens=vals[1:1+cnt]
    assert sum(lens)==len(d)-tbl_end, (sum(lens), len(d)-tbl_end)
    o=tbl_end; out=[]
    for L in lens:
        out.append(d[o:o+L]); o+=L
    return out, d

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
ID_PAT = re.compile(r'^(bg|ch|cg|ev|se|bgm|cut|ui|emo|body|face|mask|scene|mail-screen|phone-screen|phone|trophy|image|mv|snd|voice)[_-]', re.I)
ID2_PAT = re.compile(r'^\d{2}_\d{2}[A-Z]')
EMOJI_PAT = re.compile(r'^\(emoji_\d+\)$')
NUM_PAT = re.compile(r'^[0-9:.\-]+$')
SENDER = re.compile(r'^[A-Z][A-Z ]{1,}$')

HIRA = re.compile(r'[\u3041-\u309f]')

def extras():
    """エクストラ（コレクション／用語解説）= IL2CPP リテラル。文字表リテラル等は除外。"""
    d = open(META,'rb').read()
    rows = []
    for i in range(105800//8):
        ln, idx = struct.unpack_from('<Ii', d, 0x100 + 8*i)
        if ln < 150: continue
        b = d[0x19e48+idx : 0x19e48+idx+ln]
        try: s = b.decode('utf-8')
        except Exception: continue
        if not HIRA.search(s): continue
        if any('\u0080' <= c <= '\u03ff' for c in s): continue
        if re.search(r'[\u0400-\u04ff\u2e80-\u2fff]', s): continue
        rows.append((idx, s))
    rows.sort()
    out = ['■エクストラ（コレクション／用語解説・IL2CPP リテラル）']
    for _, s in rows:
        out.append(re.sub(r'\n\u3000?', '', s).strip())
    return out

def main():
    recs, raw = records(SRC)
    texts = [decode(r) for r in recs]
    res = set()
    for f in LISTS:
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            for l in open(p, encoding='utf-8', errors='replace').read().split('\n'):
                if l.strip(): res.add(l.strip())
    dropped = collections.Counter()
    typo = []
    keep = []
    for i,t in enumerate(texts):
        s = t.strip()
        if not s: dropped['blank'] += 1; continue
        if '#n' in t: dropped['markup#n'] += 1; continue
        if EMOJI_PAT.match(s): dropped['emoji_id'] += 1; continue
        if ID_PAT.match(s) or ID2_PAT.match(s): dropped['res_id'] += 1; continue
        if s in res: dropped['res_list'] += 1; continue
        if NUM_PAT.match(s): dropped['numeric'] += 1; continue
        if not JP.search(s) and re.fullmatch(r'[\x20-\x7e]+', s):
            # 纯 ASCII：只留「上屏标题/新闻」（多词，或后随「－…－」字幕）
            if SENDER.match(s) and len(s.split()) == 1: dropped['sender'] += 1; continue
            if re.fullmatch(r'-(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)-', s):
                pass   # 日期标题（与「月曜日」成对，上屏）
            elif len(s.split())<2 and not (i+1<len(texts) and re.fullmatch(r'－.*－', texts[i+1].strip())):
                dropped['ascii_single'] += 1; continue
        # 框内换行合并：删换行 + 紧随全角空格
        s = re.sub(r'\n\u3000?', '', s)
        s = s.replace('（名前）', 'テウタ')
        s = re.sub(r'\(emoji_\d+\)', '', s)
        s = s.strip()
        if not s: dropped['blank2'] += 1; continue
        # 原文誤字の統一：行頭「で始まる行の末尾が ] / 』 になっている 4 例のみ 」へ
        if s.startswith('「') and s.count('「') == 1 and s.count('」') == 0 and s[-1] in ']』':
            s = s[:-1] + '」'
            typo.append(s)
        keep.append(s)
    ex = extras()
    out = '\ufeff' + '\n'.join(keep + ex) + '\n'
    dest = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]BUSTAFELLOWS シーズン2.txt')
    os.makedirs(os.path.dirname(dest), exists_ok=True) if False else None
    open(dest,'w',encoding='utf-8',newline='\n').write(out)
    print('records', len(recs), 'kept', len(keep), 'extras', len(ex))
    print('dropped', dict(dropped))
    print('typo-fixed', len(typo))
    for t in typo: print('   ', t[:40])
    print('wrote', dest, len(out.encode('utf-8')), 'bytes')

if __name__ == '__main__':
    main()
