# -*- coding: utf-8 -*-
"""
[JP]STAMP OUT（Monoceros 自研引擎，与 Spell Down 同族：STMD/STSL/GLNK）
提取器（参照 Spell Down 方法，已逐字节验证 STAMP OUT 实际结构）

源：
  [JP]STAMP OUT.exe (RAR5 SFX, 密码 otoame) -> STAMP OUT.img (CloneCD MODE1/2352)
  -> stampout.iso (2352->2048 抽取) -> setupdata/data/
     SO_MSG.dat (STMD, 12,054 条消息, 逐字节 XOR 0xFF -> cp932)
     SO_SNR.dat (STSL, 12,054 个 00 80 <u32> 消息引用 + 106 个 28 00 01 选项)
     stampout.glk/.mlk/.slk (GLNK, 图像/音频, 排除)
     SO_OP.dat / ENDING01/02.dat (MPEG 影片, 排除)

断框判据（L0）：参照同族 Spell Down 的方法 + STSL 实测
  - STSL 中 `00 80 <u32 idx>` 引用 msg[idx]；全 12,054 引用取值 0..12,053 各一次、
    文件顺序严格递增 -> 一引用 = 一次 SetText = 一框 = 一次点击（同族 Spell Down 验证）。
  - 选项 `28 00 01 <u16 len> <cp932>` 106 条，全部落在相邻两引用之间 -> 逐组归到其前一条消息。
  - `\n` 9,368 处 = 框内排版换行（合并）；`\k` 12,054 处 = 零宽结束标记（删）；
    `\a<名>;` 3,222 处 = 正文内名札（保留并接同行）；`\v<语音>.ogg;` 3,221 处 = 语音（删）。
  - 全部反斜杠均属上述 4 类转义或 cp932 尾字节 0x5c，无游离转义。
"""
import struct, os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

BASE = os.path.join(VNTRANS_HOME, '_work_stampout/iso_data/setupdata/data')
OUT  = os.path.join(VNTRANS_HOME, '_work_stampout/_out.txt')

def u32(b, o): return struct.unpack_from('<I', b, o)[0]
def u16(b, o): return struct.unpack_from('<H', b, o)[0]

def load_msgs():
    m = open(os.path.join(BASE, 'SO_MSG.dat'), 'rb').read()
    assert m[:4] == b'STMD'
    cnt = u32(m, 6)
    pool = u32(m, 10)
    idx0 = 14
    data_start = idx0 + cnt * 4
    assert data_start + pool == len(m), (data_start + pool, len(m))
    recs = []
    for i in range(cnt):
        off = data_start + u32(m, idx0 + i*4)
        rl = u32(m, off)
        body = m[off+4: off+4+rl]
        dec = bytes(b ^ 0xFF for b in body)          # 逐字节 XOR 0xFF -> cp932
        recs.append(dec)
    return recs

def process(raw):
    """解析单条记录（cp932 字节流，已 XOR 0xFF）。返回 (name, text)。
    用 cp932 感知扫描，避免把 cp932 尾字节 0x5c 误当转义。"""
    out = bytearray()
    name = None
    i, n = 0, len(raw)
    while i < n:
        b = raw[i]
        # cp932 双字节（前导字节）
        if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc:
            out += raw[i:i+2]; i += 2; continue
        if b == 0x5c:                       # 反斜杠
            nx = raw[i+1] if i+1 < n else 0
            if nx == 0x61:                   # \a<名>; -> 名札（正文框内）
                j = i+2
                while j < n and raw[j] != 0x3b: j += 1
                name = raw[i+2:j]
                i = j+1; continue
            if nx == 0x76:                   # \v<语音>.ogg; -> 删
                j = i+2
                while j < n and raw[j] != 0x3b: j += 1
                i = j+1; continue
            if nx == 0x6e:                   # \n -> 框内换行（合并）
                i += 2; continue
            if nx == 0x6b:                   # \k -> 零宽结束标记（删）
                i += 2; continue
            out.append(0x5c); i += 1; continue   # 极少见：游离反斜杠，保留
        out.append(b); i += 1
    text = out.decode('cp932', errors='replace')
    if name is not None:
        nm = name.decode('cp932', errors='replace').replace('　', '')  # 去引擎名框全角空格填充
        text = nm + text
    return text.strip()

def load_scenario(recs):
    s = open(os.path.join(BASE, 'SO_SNR.dat'), 'rb').read()
    cnt = len(recs)
    # 线性扫描：消息引用 00 80 <u32> 与选项 28 00 01 <u16 len> <cp932>
    seq = []                                  # (kind, payload) kind: 'm' msg-idx / 'o' option-text
    i, n = 0, len(s)
    ref_count = 0
    opt_count = 0
    while i < n:
        if s[i:i+2] == b'\x00\x80':
            v = u32(s, i+2)
            if v < cnt:
                seq.append(('m', v)); ref_count += 1
            i += 6; continue
        if s[i:i+3] == b'\x28\x00\x01':
            ln = u16(s, i+3)
            txt = s[i+5: i+5+ln]
            seq.append(('o', txt.decode('cp932', errors='replace')))
            opt_count += 1
            i += 5 + ln; continue
        i += 1
    return seq, ref_count, opt_count

def main():
    recs = load_msgs()
    seq, rc, oc = load_scenario(recs)
    lines = []
    empty = 0
    for kind, payload in seq:
        if kind == 'm':
            t = process(recs[payload])
            if t == '':
                empty += 1; continue
            lines.append(t)
        else:
            lines.append(payload.strip())
    # 写 UTF-8 BOM / 纯 LF（newline='\n' 防止 Windows 把 \n 翻成 \r\n）
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\ufeff')
        f.write('\n'.join(lines))
        f.write('\n')
    print('messages total', len(recs), 'refs', rc, 'options', oc, 'empties skipped', empty)
    print('output lines', len(lines), 'bytes', os.path.getsize(OUT))
    # 抽样
    for idx in (0, 1, 17, 200):
        print('--- msg', idx, '---')
        # 找该 idx 在 seq 中的首个出现行
        li = None
        c = 0
        for k, p in seq:
            if k == 'm':
                if p == idx: li = c; break
                c += 1
        if li is not None and li < len(lines):
            print(repr(lines[li][:80]))

if __name__ == '__main__':
    main()
