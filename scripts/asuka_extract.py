#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP]あすか！～僕ら星灯高校野球団～ 全文本提取器 (Madoka GScript / CRPT)"""
import sys, re, numpy as np

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
    pun=np.zeros(256,np.int32)
    for s in S1: pun+=H[_r81,(_sds^s)]
    hira=np.zeros(256,np.int32)
    for t in range(0xA0,0xF2): hira+=H[_r82,(_sds^t)]
    kanji=BH[_lead^_sds[:,None]].sum(axis=1)
    topfrac=BH[_sds[:,None]^np.arange(256)].max(axis=1)/1024.0
    sc=8*pun+2*hira+0.5*kanji-np.where(topfrac>0.30,800,0)
    k=int(sc.argmax()); return k,int(sc[k])

# 人名宏 → 名称（外部依据 vndb：空谷あすか；游戏内宏以姓/名分别插入，d190=姓“空谷”、d191=名“あすか”）
MACRO_SUR=b'\x05\x80\x80\x80\xd1\x90'   # 空谷
MACRO_GIV=b'\x05\x80\x80\x80\xd1\x91'   # あすか
SUB_SUR='空谷'.encode('cp932'); SUB_GIV='あすか'.encode('cp932')

def clean(s):
    s=s.replace(MACRO_SUR,SUB_SUR).replace(MACRO_GIV,SUB_GIV)
    try: t=s.decode('cp932')
    except: return None
    t=re.sub(r'\x10(.*?)\x11.*?\x12',r'\1',t)   # 注音 ruby → 本文
    t=t.replace('\x08','')                        # 框内换行合并
    t=re.sub(r'[\x00-\x1f]','',t)                # 残留控制码
    return t

def decrypt_full(path):
    data=open(path,'rb').read(); assert data[:4]==b'CRPT'
    pay=data[0x20:]; NB=len(pay)//0x400
    blocks=np.frombuffer(pay[:NB*0x400],dtype=np.uint8).reshape(NB,0x400)
    out=bytearray()
    for bi in range(NB):
        base=np.frombuffer(decrypt_block(bytes(blocks[bi])),dtype=np.uint8)
        k,sc=score_block(base); out+=bytes(c^k for c in base)
    return bytes(out)

EXCLUDE_SUBSTR=[
 "CV[:：]",            # キャスト表
 "ルート設定が異常",     # 调试断言
 "SEF_",               # 调试脚本API
 "廃止され",           # 调试（已废弃API）
 "工事中",             # 调试（未实装）
 "行き止まり",          # 调试（未实装）
 "プレイ情報",          # 存档系统
 "セーブデータ",        # 存档系统
 "破損",               # 错误
 "初期状態",           # 存档系统
 "終了します。よろしいですか",  # 退出确认
 "をプレイしていただき",  # 致谢
 "このソフトの実行には", # 配置
 "画面サイズ",          # 配置
 "色数",               # 配置
 "ＭＳ ゴシック","ＭＳゴシック", # 字体
 "ウィンドウ",          # 配置
 "クイック設定",        # 配置
 "ハードウェア",        # 配置
 "※一部のグラフィック",  # 配置注记
 "今すぐ有効にしますか",  # 配置
 "支障をきたす",        # 配置
 "打ち込んでください",    # 命名UI
 "お手数をおかけ",       # 系统
 "名前が入力されていません", # 命名UI
 "名前に使用できない記号", # 命名UI
 "名前を入力",          # 命名UI
 "タイトル名を編集",     # 存档UI
 "スキップしますか",     # 系统提示
 "スキップできます",     # 系统提示
 "Microsoft Office",     # IME 系统提示
 "お客様のPC",          # IME 系统提示
 "SetCharCount",        # 引擎调试
 "SetMaxCharCount",     # 引擎调试
 "存在しないキャラクターID", # 引擎调试
 "キャラ表示位置の指定が",  # 引擎调试
 "が存在しません",        # 引擎调试（文件/字符不存在）
 "ルール画像",            # 引擎调试（规则背景图）
 "test_",               # 调试测试串
]
EXCLUDE_EXACT={"空谷","あすか","あすか！"}   # 姓名登记表默认值（非剧情文本）
EXC=[re.compile(p) for p in EXCLUDE_SUBSTR]

def is_system(t):
    if t in EXCLUDE_EXACT: return True
    return any(p.search(t) for p in EXC)

def bag(path):
    data=open(path,'rb').read(); assert data[:4]==b'CRPT'
    pay=data[0x20:]; NB=len(pay)//0x400
    blocks=np.frombuffer(pay[:NB*0x400],dtype=np.uint8).reshape(NB,0x400)
    keep=np.zeros(NB,dtype=bool); dec=[None]*NB
    for bi in range(NB):
        base=np.frombuffer(decrypt_block(bytes(blocks[bi])),dtype=np.uint8)
        k,sc=score_block(base)
        dec[bi]=(k,sc,bytes(c^k for c in base))
        if sc>=150: keep[bi]=True
    for bi in range(NB):
        if keep[bi]:
            for j in (bi-1,bi+1):
                if 0<=j<NB: keep[j]=True
    stream=bytearray()
    for bi in range(NB):
        if keep[bi]: stream+=dec[bi][2]
    lines=[]
    for s in bytes(stream).split(b'\x00'):
        if len(s)<2: continue
        t=clean(s)
        if t is None: continue
        jp=sum(1 for ch in t if 0x3040<=ord(ch)<=0x9fff or ch in '、。「」『』…―・')
        if jp<1 or jp<len(t)*0.3: continue
        if is_system(t): continue
        lines.append(t)
    return lines

if __name__=='__main__':
    SCE=sys.argv[1]; OUT=sys.argv[2]
    lines=bag(SCE)
    with open(OUT,'w',encoding='utf-8-sig',newline='\n') as f:
        f.write('\n'.join(lines)+'\n')
    print("lines:",len(lines))
    has_k=sum(1 for l in lines if '「' in l or '」' in l)
    print("with 「」:",has_k," without:",len(lines)-has_k)
