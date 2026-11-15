# -*- coding: utf-8 -*-
"""
星の王女 (PC-JP, 2003) — Madoka GScript 旧式 .sce (CRPT 加密) 全文本提取 v1
解密：seed=0x2c, kc=0, 0x400 块，从文件偏移 0x10 起连续排列
对白结构：[名]\0[语音ID mNNN-N-NNN]\0[正文(含内联控制码)]\0 …  [指令token]
  两语音ID之间(含日文)的所有 token 合并 = 一框 = 一行
控制码（实证）：
  05 80 80 80 + 2B 名宏(a7 96 / a7 95 两变体) -> 立花未来（vndb v1930 主角 Tachibana Mirai，Role=Nameable；两变体均指向同一主角，统一回填默认名，无空格）
  01 XX            -> 2B 命令（剥）
  a7 96 / a7 95    -> 2B 命令（剥）
  0x02/03/04/06/07/09/ff/80 等单字节 -> 控制（剥）
  0x0a/0x0d        -> 换行（保留，框内视觉行合并用）
  合法 cp932 2B(81-9f,e0-fc 引导)+半角假名(a1-df) 保留
"""
import re, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SCE = os.path.join(VNTRANS_HOME, '_work_hoshinoujo/sce.bin')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]星の王女.txt')

def load_decrypted(path):
    d = open(path, 'rb').read()
    ORDER = [(0x43 + 0x17*i) & 0x3FF for i in range(0x400)]
    def dec(chunk):
        out = bytearray(0x400); prev = chunk[0x2c]; out[0] = prev
        for i in range(0x3FF):
            j = ORDER[i]; b = chunk[j] if j < len(chunk) else 0
            prev = b ^ prev; out[i+1] = prev
        return bytes(out)
    N = (len(d) - 0x10) // 0x400
    return b''.join(dec(d[0x10 + k*0x400 : 0x10 + k*0x400 + 0x400]) for k in range(N))

VOICE = re.compile(rb'^[A-Za-z]?\d{3}-\d-\d{3}$')
JAP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff01-\uff60]')
# 指令 token（背景/音乐/立绘等）：前缀 2–3 个小写字母 + _/数字，后接日文名也算指令
# 例 bg_エレベーター / mu_04 / st_015b / se03 / bg04a —— 非上屏文本，须剔除
DIRECTIVE = re.compile(rb'^[a-z]{2,3}[_0-9]')
NM = b'\x05\x80\x80\x80'
CMD2 = (b'\xa7\x96', b'\xa7\x95')   # 2B 命令

def clean_text(raw):
    """剥离内联控制码，保留正文。返回 (text, had_name)。
    注意：out 用 str 累积，正文 chunk 以 cp932 解码、名宏占位直接以 str 插入，
    避免 cp932 字节与占位符的 UTF-8 字节混在同一 bytearray 里被误解码。"""
    parts = []          # str 片段
    buf = bytearray()   # 累积待解码的 cp932 字节
    i = 0; n = len(raw); had_name = False
    def flush():
        if buf:
            parts.append(buf.decode('cp932', errors='replace'))
            buf.clear()
    while i < n:
        b = raw[i]
        if raw[i:i+4] == NM:
            # 名宏：剥 4B + 2B 名ID -> 主角默认名（vndb v1930 主角 Tachibana Mirai / 立花未来，Role=Nameable）
            # a7 96（×827，多直呼）与 a7 95（×70，多带 さん/君 敬称）均指向同一可改名主角，统一回填默认名（无空格）。
            flush()
            parts.append('立花未来')
            had_name = True
            i += 6; continue
        if raw[i:i+2] in CMD2:
            i += 2; continue
        if b == 0x01:
            i += 2; continue
        if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc:
            if i+1 < n and 0x40 <= raw[i+1] <= 0xfc:
                buf += raw[i:i+2]; i += 2; continue
            i += 1; continue
        if 0xa1 <= b <= 0xdf:   # 半角假名（正文）
            buf.append(b); i += 1; continue
        if 0x20 <= b <= 0x7e:   # ASCII 可显
            buf.append(b); i += 1; continue
        if b in (0x0a, 0x0d):   # 换行
            buf.append(b); i += 1; continue
        # 其余控制字节：剥
        i += 1
    flush()
    return ''.join(parts), had_name

def is_jp_token(tok):
    try:
        s = tok.decode('cp932')
    except:
        return False
    return bool(JAP.search(s))

def extract(data):
    # 切 \0 终止 token
    toks = []
    start = 0; i = 0; L = len(data)
    while i < L:
        if data[i] == 0:
            if i > start:
                toks.append(data[start:i])
            while i < L and data[i] == 0: i += 1
            start = i
        else:
            i += 1
    if start < L: toks.append(data[start:L])

    lines = []
    i = 0; n = len(toks)
    while i < n:
        if VOICE.match(toks[i]):
            j = i + 1
            while j < n and not VOICE.match(toks[j]):
                t = toks[j]
                if DIRECTIVE.match(t):     # 指令 token（bg_*/mu_*/st_*/se* 等，含日文后缀也算）
                    j += 1; continue
                if is_jp_token(t):         # 只纳入含日文的文本 token，排纯ASCII指令
                    text, _ = clean_text(t)
                    text = text.strip()
                    if text and JAP.search(text):
                        lines.append(text)
                j += 1
            i = j
        else:
            i += 1
    return lines

data = load_decrypted(SCE)
lines = extract(data)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:   # UTF-8 BOM
    for ln in lines:
        f.write(ln + '\n')
print("lines:", len(lines))
print("sample:")
for ln in lines[:15]:
    print(" ", ln)
