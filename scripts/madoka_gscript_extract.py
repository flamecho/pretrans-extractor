# -*- coding: utf-8 -*-
"""Madoka GScript (CRPT) scenario text extractor — engine: 美蕾/MP2.
Decryption (un-scatter + prefix-XOR + LCG table + per-block key recovery) is
ENGINE-LEVEL and reused from the reference tool. Game-specific items below are
empirically derived for THIS work (夢をもう一度＋幸福の風) — NOT copied from other games.
Usage: python madoka_gscript_extract.py <game.sce> <out.txt>
"""
import sys, re
import numpy as np

# ---- engine-level (reused, NOT game-specific) ----
MUL=0x41C64E6D; ADD=0x3039; SEED=0x915354A9; MASK=0xFFFFFFFF
def lcg_table():
    t=[]; s=SEED
    for _ in range(256):
        t.append(s); s=(s*MUL+ADD)&MASK
    return b''.join(int(x).to_bytes(4,'little') for x in t)
TB=lcg_table()
ORDER=[(0x43+0x17*(i-1))&0x3ff for i in range(1,1024)]
def decrypt_block(raw):
    w=bytearray(1024); pref=0
    for i,idx in enumerate(ORDER,1):
        pref^=raw[idx]; w[i]=pref^TB[i]
    w[0]=TB[0]; return w
S1=[0x41,0x42,0x75,0x76,0x40,0x63,0x5e,0x9f,0x48,0x49]
_sds=np.arange(256,dtype=np.int32); _r81=(0x81^_sds); _r82=(0x82^_sds)
_lead=np.array([v for v in range(0x88,0xA0)]+[v for v in range(0xE0,0xEB)],dtype=np.int32)
def score_block(blk):
    pair=(blk[:-1].astype(np.int32)<<8)|blk[1:].astype(np.int32)
    H=np.bincount(pair,minlength=65536).reshape(256,256)
    BH=np.bincount(blk,minlength=256).astype(np.float64)
    pun=sum((H[_r81,(_sds^s)] for s in S1),np.zeros(256,np.int32))
    hira=sum((H[_r82,(_sds^t)] for t in range(0xA0,0xF2)),np.zeros(256,np.int32))
    kanji=BH[_lead^_sds[:,None]].sum(axis=1)
    tf=BH[_sds[:,None]^np.arange(256)].max(axis=1)/1024.0
    sc=8*pun+2*hira+0.5*kanji-np.where(tf>0.30,800,0)
    return int(sc.argmax())

# ---- game-specific (THIS work, empirically derived) ----
# Name-insert macros: \x05\x80\x80\x80 + 2-byte id. Two slots found:
#   c1ee (1411x) = dominant protagonist name; c1ed (284x) = secondary (often with 君 / combined).
# Real names are runtime variables; not present as plaintext in .sce/.exe.
# Preserved as flagged tokens; resolve via external check (vndb/official) — do NOT guess.
NAME_MAP = {
    b'\x05\x80\x80\x80\xc1\xee': b'@@N1@@',
    b'\x05\x80\x80\x80\xc1\xed': b'@@N2@@',
}
# Resolved 2026-11-09 (evidence-based, NOT guessed):
#   The two slots are the NAMEABLE protagonist's GIVEN NAME (N1/c1ee) and SURNAME (N2/c1ed).
#   In-game confirmation dialogue proves the mapping (user-corrected: ① is the given name only):
#     L29679 "君は、〈主人公②〉……〈主人公①〉さん、だね"  (= your surname is ②, given name ①-san)
#     L30188 "……失礼ですが、〈主人公②〉、〈主人公①〉さんかな"
#   Canonical default: surname 佐々木, given name 瞳 (Hitomi Sasaki), a "Nameable Protagonist" (VNDB/official).
#   (佐々木/瞳 appear 0× as plaintext in the script — name exists ONLY through these slots.)
#   2026-11-09 user correction: ① = 瞳 (given name only), NOT 佐々木瞳.
NAME_SHOW = {'@@N1@@':'瞳', '@@N2@@':'佐々木'}

FURIGANA = re.compile(rb'\x10(.*?)\x11.*?\x12', re.S)
CMD_HEAD = re.compile(r'^[A-Za-z][A-Za-z0-9_]*\s*[!:！]')
# Engine debug/error strings (shown only on missing-scene/chapter faults) — NOT rendered dialogue.
DEBUG_SUB = ('データベースが開けませんでした','のシナリオはまだ存在しない','ループしています',
             'とばして次にいく','シーン名 ','チャプター番号 ')

# ---- halfwidth-katakana -> hiragana (deterministic phonetic restoration) ----
# Proven empirically: in this game ち/き/う appear 0x fullwidth but 55k/14k/21k as halfwidth,
# so the scenario stores these syllables as halfwidth-katakana bytes that represent hiragana.
# Each halfwidth katakana maps to exactly one hiragana (same phonetic inventory); not a guess.
_HWK = {
 '\uff61':'。','\uff62':'「','\uff63':'」','\uff64':'、','\uff65':'・','\uff66':'を',
 '\uff67':'ゃ','\uff68':'ぃ','\uff69':'ゅ','\uff6a':'ぇ','\uff6b':'ょ','\uff6c':'ゃ',
 '\uff6d':'ゅ','\uff6e':'ょ','\uff6f':'っ','\uff70':'ー',
 '\uff71':'あ','\uff72':'い','\uff73':'う','\uff74':'え','\uff75':'お',
 '\uff76':'か','\uff77':'き','\uff78':'く','\uff79':'け','\uff7a':'こ',
 '\uff7b':'さ','\uff7c':'し','\uff7d':'す','\uff7e':'せ','\uff7f':'そ',
 '\uff80':'た','\uff81':'ち','\uff82':'つ','\uff83':'て','\uff84':'と',
 '\uff85':'な','\uff86':'に','\uff87':'ぬ','\uff88':'ね','\uff89':'の',
 '\uff8a':'は','\uff8b':'ひ','\uff8c':'ふ','\uff8d':'へ','\uff8e':'ほ',
 '\uff8f':'ま','\uff90':'み','\uff91':'む','\uff92':'め','\uff93':'も',
 '\uff94':'や','\uff95':'ゆ','\uff96':'よ','\uff97':'ら','\uff98':'り',
 '\uff99':'る','\uff9a':'れ','\uff9b':'ろ','\uff9c':'わ','\uff9d':'ん',
}
_VOICE = {'か':'が','き':'ぎ','く':'ぐ','け':'げ','こ':'ご','さ':'ざ','し':'じ','す':'ず',
          'せ':'ぜ','そ':'ぞ','た':'だ','ち':'ぢ','つ':'づ','て':'で','と':'ど','う':'ゔ',
          'は':'ば','ひ':'び','ふ':'ぶ','へ':'べ','ほ':'ぼ','や':'ゃ','ゆ':'ゅ','よ':'ょ'}
_HVOICE = {'は':'ぱ','ひ':'ぴ','ふ':'ぷ','へ':'ぺ','ほ':'ぽ'}
def hwk_to_hira(t):
    out=[]
    for ch in t:
        if ch=='\uff9e':  # dakuten
            if out and out[-1] in _VOICE: out[-1]=_VOICE[out[-1]]
        elif ch=='\uff9f':  # handakuten
            if out and out[-1] in _HVOICE: out[-1]=_HVOICE[out[-1]]
        elif ch in _HWK:
            out.append(_HWK[ch])
        else:
            out.append(ch)
    return ''.join(out)

def clean_bytes(s):
    s = FURIGANA.sub(rb'\1', s)                 # furigana -> base
    for k,v in NAME_MAP.items(): s = s.replace(k, v)
    s = s.replace(b'\x08', b'')                 # in-box newline -> merge
    s = re.sub(rb'[\x00-\x1f]', b'', s)        # drop control < 0x20
    return s

def is_dialogue(raw):
    """L0/L1 gate. A segment is real dialogue if it contains kana (hiragana/katakana)
    OR a plausible kanji sentence (>=3 kanji + punctuation). Noise heuristics (dominance/
    run) are intentionally NOT applied to kana-bearing lines: this game stores hiragana as
    halfwidth-katakana and legitimately repeats kana (ふふふ, ククク, 死ね死ね) and trails lines
    with ellipsis (私達は……), so the old dominance/run rules were dropping real sentences.
    Mis-keyed garbage is excluded by:
      (a) never-present chars in real dialogue (enclosed 0x3200-32FF, CJK Ext-A 0x3400-4DBF);
      (b) a stray-kana-drowned-in-kanji guard (kj>=4 and kj>hk*3);
      (c) for kanji-only lines, a single-kanji-dominance guard (>0.5 of kanji = garbage repeat).
    """
    try: t = raw.decode('cp932')
    except: return None
    if '�' in t: return None
    if CMD_HEAD.match(t): return None
    if any(d in t for d in DEBUG_SUB): return None
    # strip PUA (mis-decoded control remnants)
    t = ''.join(c for c in t if not (0xE000<=ord(c)<=0xF8FF))
    L = len(t)
    if L==0: return None
    # (a) garbage insurance: enclosed / CJK Ext-A never appear in real dialogue
    if any(0x3200<=ord(ch)<=0x32FF or 0x3400<=ord(ch)<=0x4DBF for ch in t):
        return None
    from collections import Counter
    hk = sum(1 for ch in t if 0x3040<=ord(ch)<=0x30ff)   # hiragana + katakana
    kj = sum(1 for ch in t if 0x4e00<=ord(ch)<=0x9fff)   # kanji
    punct = sum(1 for ch in t if ch in '。、！？（）「」『』…―ー：・！')
    hwk = sum(1 for ch in t if 0xFF61<=ord(ch)<=0xFF9F)   # halfwidth katakana
    if hk>=1:
        # (b) isolated kana drowned in many kanji => mis-keyed garbage
        if kj>=4 and kj>hk*3: return None
        return hwk_to_hira(t)        # normalize only accepted text
    if kj>=3 and punct>=1:
        # (c) reject kanji-repeat garbage (one kanji dominates the kanji count)
        cc = Counter(ch for ch in t if 0x4e00<=ord(ch)<=0x9fff)
        if cc and cc.most_common(1)[0][1] / kj > 0.5: return None
        return hwk_to_hira(t)
    if hwk>=2 and kj==0:
        return hwk_to_hira(t)
    return None

def extract(path, out):
    data=open(path,'rb').read()
    assert data[:4]==b'CRPT', data[:4]
    pay=data[0x20:]
    NB=len(pay)//0x400
    blocks=np.frombuffer(pay[:NB*0x400],dtype=np.uint8).reshape(NB,0x400)
    # Decode EVERY block with its best-key; text vs binary is decided by is_dialogue(),
    # NOT by score band (score only picks the XOR key; real text exists in every band).
    keep=np.ones(NB,dtype=bool); dec=[None]*NB
    for bi in range(NB):
        base=decrypt_block(bytes(blocks[bi]))
        k=score_block(np.frombuffer(base,dtype=np.uint8))
        dec[bi]=(k,bytes(c^k for c in base))
    lines=[]; ctrl=set(); n_name=0
    for bi in range(NB):
        if not keep[bi]: continue
        stream=dec[bi][1]
        for seg in stream.split(b'\x00'):
            if len(seg)<2: continue
            cl=clean_bytes(seg)
            if not cl: continue
            t=is_dialogue(cl)
            if t is None: continue
            n_name += t.count('@@N1@@') + t.count('@@N2@@')
            t=t.replace('@@N1@@',NAME_SHOW['@@N1@@']).replace('@@N2@@',NAME_SHOW['@@N2@@'])
            for ch in t:
                if ord(ch)<0x20: ctrl.add(hex(ord(ch)))
            lines.append(t)
    with open(out,'w',encoding='utf-8-sig',newline='\n') as f:
        f.write('\n'.join(lines)+'\n')
    print('blocks',NB,'lines',len(lines),'name-tokens',n_name,'leftover-ctrl',ctrl)

if __name__=='__main__':
    extract(sys.argv[1], sys.argv[2])
