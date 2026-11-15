#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[PC-JP]すみれの蕾（PC / MADOKA GScript・GSCE 编译剧本）全文本提取 v2。

用法: python sumire_extract.py <すみれの蕾.sce> <out.txt>
源母本: <游戏 dump 目录>/还没做/[PC-JP]すみれの蕾.rar（Rar5 头加密，密码 otoame）
        → 解包得 すみれの蕾.sce（魔数 GSCE，14,360,066 B）。

v2 修正（2026-11-07）：
  ① 叙事区扩到 [prologue_start..epilogue_end)=[11529727..14359134]（补序章/尾声，
     原 v1 误用 VOICE 首末 [11530402..13907322] 当边界而砍掉两端）。
  ② 框模型：一个 S 段＝一个框（一次点击）；相邻 S 段绝不合并。
  ③ 0x08＝一框内多视觉行分隔符（不剥离）；仅 ≥2 有内容视觉行才出双版。
     171 个「全角空格缩排帧+正文」空白帧内联合并为单行（避免空行告警、不丢内容）。
  ④ 名字宏 NM=05 80 80 80 + d0 e6=姓 早坂／d0 e7=名 サツキ，均只输出名字、不带引号。
控制字节: 01 XX=2B命令(剥) / 10,11,12=1B内联(剥) / 8e XX=cp932 引导按有效性分流。
成品 53,284 行／双版 1 框／品检 check_text.py --dual --expect-dual --name サツキ PASS。
详见 解析报告/[PC-JP]すみれの蕾_解析报告.md ／ 日报 2026-11-07.md §[PC-JP]すみれの蕾。
"""
import re
import argparse

ap = argparse.ArgumentParser(description='[PC-JP]すみれの蕾 (MADOKA GSX / GSCE) extractor v2')
ap.add_argument('sce', help='解包得到的 すみれの蕾.sce 路径')
ap.add_argument('out', help='输出 txt 路径')
_args = ap.parse_args()
SCE = _args.sce
OUT = _args.out
data=open(SCE,"rb").read()
POOL=11509772; END=len(data)

VOICE=re.compile(rb'^[A-Z]{1,4}-[A-Z]{2,4}-\d{3}-\d{3}$')
JAP=re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff01-\uff60]')
CTRL1=bytes([0x10,0x11,0x12])   # 0x08 另作换行分隔符，不在此剥离
NM=b'\x05\x80\x80\x80'
# 系统/UI/调试串排除（子串匹配；均为非叙事文本）
SYS=["存在しないキャラクターID","ルール画像","存在しません","名前が入力されていません",
"名前に使用できない記号","プレイ情報","工事中","ループしています","専用ルートが解放されました",
"Congratulation","クイックセーブデータが存在しません","巻き戻し用データが存在しません",
"マップターン数が不正です","ＭＳ ゴシック","ＭＳ 明朝","達成率","ドラッグで移動","＊データなし",
"マップへ","データベースが開けませませんでした","クイック設定","通常の設定でゲームを開始します",
"IF_MU選択時","ｵﾜﾀ","シーン名","チャプター番号","なし\u3000"]
# 尾声结束：首个命中的系统警示/报错屏 → 之后为非叙事附录
ENDGAME=["このゲームには","女性同士の愛情表現","データベースが開けませんでした"]
DN="サツキ".encode("cp932")
SEI="早坂".encode("cp932")   # d0 e6=姓（游戏内字面量：登记表「早坂\0サツキ」×3）
OPEN="「".encode("cp932"); CLOSE="」".encode("cp932")

def handle_name(raw):
    out=bytearray(); i=0; n=len(raw)
    while i<n:
        if raw[i:i+4]==NM:
            nx=raw[i+4:i+6]
            if nx==b'\xd0\xe6': out+=SEI; i+=6; continue   # 姓（不带引号）
            elif nx==b'\xd0\xe7': out+=DN; i+=6; continue  # 名（不带引号）
            else: out+=DN; i+=4; continue
        out.append(raw[i]); i+=1
    return bytes(out)

LEAD_LO=set(range(0x81,0xA0)); LEAD_HI=set(range(0xE0,0xFD))
def is_lead(b): return b in LEAD_LO or b in LEAD_HI

def tok(raw):
    # 控制字节剥离：01 XX(2字节命令) / 10/11/12(样式) / 8e XX 按 cp932 有效性分流
    # 0x08 不在此处理（由调用方作换行分隔符）
    if NM in raw: raw=handle_name(raw)
    out=bytearray(); i=0; n=len(raw)
    while i<n:
        b=raw[i]
        if b in CTRL1: i+=1; continue
        if b==0x01: i+=2; continue
        if is_lead(b):
            if i+1<n:
                pair=raw[i:i+2]
                try:
                    ch=pair.decode("cp932")
                    if b==0x8e and '\uff66'<=ch<='\uff9f': i+=2; continue
                    out+=pair; i+=2; continue
                except: i+=2; continue
            else: i+=1; continue
        out.append(b); i+=1
    return bytes(out)

def dec(b):
    try: return b.decode("cp932")
    except: return None

def is_sys(t): return any(s in t for s in SYS)

def classify(raw):
    if not raw: return 'E'
    if VOICE.match(raw): return 'V'
    t=dec(tok(raw))
    if t is not None and JAP.search(t): return 'S'
    return 'M'

# ---- 区间：first_v / last_v ----
p=POOL; first_v=last_v=None
while p<END:
    z=data.index(b'\x00',p)
    if VOICE.match(data[p:z]):
        if first_v is None: first_v=p
        last_v=p
    p=z+1

# prologue_start：从 first_v 向前，遇首个系统 S 停止；取到序章首帧
prologue_start=None; pos=first_v
while pos>POOL:
    z=data.rfind(b'\x00',POOL,pos)
    raw=data[z+1:pos]
    if classify(raw)=='S':
        t=dec(tok(raw))
        if is_sys(t): break
        prologue_start=z+1
    pos=z

# epilogue_end：从 last_v 向后，遇首个 ENDGAME S 停止（之前为叙事尾声）
epilogue_end=END; pos=last_v
while pos<END:
    z=data.index(b'\x00',pos)
    raw=data[pos:z]
    if classify(raw)=='S':
        t=dec(tok(raw))
        if any(s in t for s in ENDGAME):
            epilogue_end=pos; break
    pos=z+1

# ---- 提取：每个 S 段 = 一个框；含 0x08 才拆段行+合并行（双版）----
# 08 多视觉行框里常见「首行仅全角空格缩排」→ 该视觉行剥后为空，不单列、不进合并行
# （避免空行告警；合并行只拼接有内容段，与 check_text 的 dual 重组校验自洽）
lines=[]; nS=0; nDual=0; nSys=0
p=prologue_start
while p<epilogue_end:
    z=data.index(b'\x00',p)
    raw=data[p:z]
    k=classify(raw)
    if k in ('E','V','M'):
        p=z+1; continue
    # k == 'S'
    t=dec(tok(raw))
    if t is None or not JAP.search(t):
        p=z+1; continue
    if is_sys(t):
        nSys+=1; p=z+1; continue
    nS+=1
    # 按 0x08 拆多行（一框内多视觉行）
    parts=[x for x in raw.split(b'\x08')]
    sub=[dec(tok(x)) for x in parts]
    sub=[s for s in sub if s]
    nonempty=[s for s in sub if s.strip()]   # 有内容的视觉行
    if len(nonempty)<=1:
        # 单内容帧（含「全角空格缩排帧+正文」这类首/尾帧为空白的 08 框）：
        # 空白帧内联合并为单行（保留缩进空格），不单列、不出双版，避免空行告警且不丢内容
        if nonempty:
            lines.append("".join(sub))
        # 全空框：跳过
    else:
        for s in nonempty: lines.append(s)            # 仅列有内容的视觉行
        lines.append("".join(nonempty)); nDual+=1     # 合并行＝有内容帧拼接（与 check_text 重组校验自洽）
    p=z+1

with open(OUT,"w",encoding="utf-8-sig",newline="\n") as f:
    for l in lines: f.write(l+"\n")

print("region [%d..%d]  first_v=%d last_v=%d"%(prologue_start,epilogue_end,first_v,last_v))
print("S-frames=%d  dual(08)=%d  sys-excluded=%d  TOTAL_lines=%d"%(nS,nDual,nSys,len(lines)))
print("=> "+OUT)
