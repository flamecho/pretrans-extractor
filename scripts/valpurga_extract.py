#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
valpurga_extract.py —— [PSV-JP]ヴァルプルガの詩 (PCSG00768) 全文本提取

引擎：3Daisy 自研（SCRVITA / .tbl+.pak / .psb）
- pkg 解密：pkg2zip -x + psvpfsparser -i -o -z（PFS 层）→ dec/PCSG00768/
- 脚本容器：psvscr.tbl(索引) + psvscr00.pak(数据)
  * .pak = 0x800 头 + 脚本序列；每个脚本头 16B:
      u32 LE magic 0x00011804 | u32 checksum | u32 BE stream_off | u32 BE ?
    命令流起点 = 脚本头偏移 + stream_off
    脚本头用 magic 04 18 01 00 定位（0x800 对齐）
- 命令流 = token 序列:
      token = b'\x00' <u8 len> <len 字节 payload>   （扩展/带参）
            | <单字节 opcode>
    payload[0]=0x01 → u32 BE 整数参数；payload[0]=0x02 → 字符串:
      `02 <u16 BE len> <len 字节 cp932> \x00`
  * 关键 opcode: 0xf0=设置/更换文本框(并进入等待)、0xb0=续接当前文本框、
                 0x01=标题(扉文)、0x09=调用函数、0x30=BGM、0x0e=切场景、0x44=播放影片
- 成行：文本框 = 一次点击 = 一行
  * `«str»0xf0`  (非空)         → 以 str 开启新文本框
  * `«str»0xb0 0xf0`            → 续接到当前文本框（框内换行/分段）
  * `«""»0xf0`                  → 结算并输出当前文本框
  * `«str»0x01`                 → 标题行（扉文）
  * 字符串以 「 开头（无说话人名）  → 选项，单独成行
- 说话人：正文形如 `名前 「…」`／`名前 『…』`／`名前 （…）`／`mob名　そのN 「…」`
  （名札与正文同一串，空格分隔：半角 0x20 或全角 U+3000）→ 去「名札+空格」，仅保留括号内容
- 行内 `\n`（ASCII 反斜杠 n，SJIS 5C 6E）→ 框内换行，合并
用法: python scripts/valpurga_extract.py <dec/PCSG00768 目录> <out.txt>
"""
import sys, os, struct, re

MAGIC = b'\x04\x18\x01\x00'
ESC = {b'\\n': '', b'\\N': '', b'\\c': '', b'\\f': ''}  # 框内换行/颜色/翻页 → 全部合并剔除
ESCRE = re.compile(r'\\[A-Za-z]')          # 其余 \X 控制序列
# 主人公名插入宏：`f0 <int slot> f0` + `00 01 04`（type 0x04）
# slot 7 = 名（詩生），slot 6 = 姓（泉）；默认名见 eboot 名字输入表（姓=泉 / 名=詩生）
NAME_SLOT = {6: '泉', 7: '詩生'}
HERO = '詩生'

def scripts(d):
    pos = []
    i = 0
    while True:
        j = d.find(MAGIC, i)
        if j < 0:
            break
        pos.append(j)
        i = j + 1
    return pos

def tokens(d, a, b):
    q = a
    out = []
    while q < b:
        x = d[q]
        if x == 0:
            L = d[q + 1]
            out.append(('E', L, d[q + 2:q + 2 + L]))
            q += 2 + L
        else:
            out.append(('S', x, None))
            q += 1
    return out

def decode_str(payload):
    # payload = 02 <u16 BE len> <len bytes> 00
    if len(payload) < 4 or payload[0] != 2:
        return None
    n = (payload[1] << 8) | payload[2]
    raw = payload[3:3 + n]
    try:
        return raw.decode('cp932')
    except Exception:
        return None

def clean(s):
    for k, v in ESC.items():
        s = s.replace(k.decode('ascii'), v)
    s = ESCRE.sub('', s)
    s = s.strip()
    # 说话人名札前缀（规范：不加说话人前缀）
    # 原始字节已确认：名札与正文同处一个 cp932 串，形如
    #   `名前 「…」` / `名前 『…』` / `名前 （…）` / `mob名　そのN 「…」`
    # （半角 0x20 或全角 U+3000 作分隔；mob 名内部可能自带全角空格）
    # 判据：行首片段不含起引号/括号，且其后紧跟起始括号 → 判为名札并剥离
    m = re.match(r'^([^「『（]{1,26}?)[ \u3000](?=[「『（])', s)
    if m:
        s = s[m.end():]
    return s

def main():
    src, out = sys.argv[1], sys.argv[2]
    dat = os.path.join(src, 'psvscr00.pak')
    d = open(dat, 'rb').read()
    pos = scripts(d)
    lines = []
    nopt = 0
    ntitle = 0
    for k, mp in enumerate(pos):
        so = struct.unpack('>I', d[mp + 8:mp + 12])[0]
        start = mp + so
        end = pos[k + 1] if k + 1 < len(pos) else len(d)
        T = tokens(d, start, end)
        buf = ''
        last_slot = None
        def emit(x):
            x = clean(x)
            if x:
                lines.append(x)
        for idx, t in enumerate(T):
            # 记录 slot 选择（`f0 <int> f0`）
            if t[0] == 'E' and t[2] and t[2][0] == 1 and len(t[2]) == 5:
                last_slot = int.from_bytes(t[2][1:5], 'big')
                continue
            # 主人公名插入宏：`00 01 04`
            if t[0] == 'E' and t[2] == b'\x04':
                nxt = T[idx + 1] if idx + 1 < len(T) else ('END', 0, None)
                if nxt[0] == 'S' and nxt[1] == 0xb0:
                    buf += NAME_SLOT.get(last_slot, HERO)   # 行内插入名字
                elif nxt[0] == 'S' and nxt[1] == 0xf0:
                    emit(buf); buf = ''                     # 设置名札并开启新文本框
                continue
            if t[0] != 'E' or not t[2] or t[2][0] != 2:
                continue
            S = decode_str(t[2])
            if S is None:
                continue
            nxt = T[idx + 1] if idx + 1 < len(T) else ('END', 0, None)
            op = nxt[1] if nxt[0] == 'S' else None
            # 仅收「显示用」文本：含非 ASCII 字符（资源/函数名为纯 ASCII）；空串=清框，须保留语义
            text = bool(re.search(r'[^\x00-\x7f]', S))
            if op == 0xb0:
                if text:
                    buf += S
            elif op == 0xf0:
                if S == '':
                    emit(buf); buf = ''
                elif not text:
                    pass
                elif S[0] in '「 ':
                    # 以「或空格开头 = 完整新文本框（选项 / 无说话人台词）
                    if S[0] == '「':
                        nopt += 1
                    emit(buf); buf = S
                else:
                    buf += S
            elif op == 0x01:
                if text:
                    emit(buf); buf = ''
                    emit(S); ntitle += 1
        emit(buf)
    # 不做「相邻重复行」去重：本作相邻同文行经源偏移核对全部来自不同脚本位置
    # （例：`金の犬 「……」` 与 `銀の犬 「……」` 为两个说话人的两次点击），
    # 去重会误删真实文本，违反「一次点击 = 一行」。
    res = lines
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(res) + '\n')
    print('scripts=%d  lines=%d  options=%d  titles=%d  -> %s' %
          (len(pos), len(res), nopt, ntitle, out))

if __name__ == '__main__':
    main()
