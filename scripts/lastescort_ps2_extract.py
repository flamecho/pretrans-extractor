# -*- coding: utf-8 -*-
"""ラスト・エスコート 〜深夜の黒蝶物語〜 (PS2 / SLPS_255.91 / D3P・Vingt-et-un) 全文本提取

链路：ISO9660 → DATA/ADV.FPK → *.VML（831 个）→ 「メッセージ枠」= 一次点击

FPK:
  +0x00 u32 count | +0x04 u32 0 | +0x08 u64 total | +0x10 u32 0x20 | +0x14 u32 dataStart
  0x20 起 count × 32B：name[16] + u32 size + u32 offset（4KB 对齐）

VML（自定义字节码）:
  +0x00 u32 hdr(=0x10) | +0x04 u32 ? | +0x08 u32 offTable 数 | +0x0c u32 size
  指令 = u16 id + 00 FF；文本载体内字节 | 0x80 = EUC-JP
    0x66 メッセージ枠 開始       0x67 フラグ(1=通常 / 0=字幕)
    0x64 ボイス有 / 0x65 ボイス無 0x68 u8 len + 文本（1 行 = 1 显示行, ≤18 字）
    0x69 枠内改行                0x6A 主人公「姓」/ 0x6B 主人公「名」
    0x6C 強調スパン(start 02 / end 00, 挿入なし)
    0x6F / 0x6D メッセージ枠 終了（= 一次点击）
    0x1F6 選択肢：u16 idx + u8 len + 文本（idx 非表示順，記録順で出す）；0x1F7 = 組の終端
  ★ 校验：0x66 数 == 0x6F 数（15,114 / 15,102）；枠内文本 ≤54 字 = 18 字 × 3 行

用法：python scripts/lastescort_ps2_extract.py <ADV.FPK> <out.txt>
"""
import struct, sys, re

SURNAME = '作上'
GIVEN = '明里'

# 系统/操作提示（非剧本正文）：シャンパンコール中のボタン案内 ×21
SKIP = {'シャンパンコール中！□ボタンのスキップに注意して下さい。'}


def read_fpk(path):
    d = open(path, 'rb').read()
    cnt, = struct.unpack('<I', d[:4])
    ent = []
    for i in range(cnt):
        o = 0x20 + i * 32
        nm = d[o:o + 16].rstrip(b'\0').decode('latin1')
        sz, off = struct.unpack('<II', d[o + 16:o + 24])
        ent.append((nm, off, sz))
    return d, ent


def euc(buf):
    return bytes(b | 0x80 for b in buf).decode('euc_jp', 'replace')


def find_ops(b):
    out, i = [], 0
    while True:
        j = b.find(b'\x00\xff', i)
        if j < 0 or j < 2:
            break
        out.append((j - 2, b[j - 2] | (b[j - 1] << 8)))
        i = j + 2
    return out


def boxes(b, flushed=None):
    """→ [文本(合并后)]，一个 66..(6F|6D) 枠 = 一条（= 一次点击）
    ★ 0x6F 与 0x6D 都是枠終了（6D 少見：E0000 开场那种「无 6F」的段用它收尾）"""
    res, cur, pend = [], None, []
    pos = find_ops(b)
    for i, (p, op) in enumerate(pos):
        nxt = pos[i + 1][0] if i + 1 < len(pos) else len(b)
        arg = b[p + 4:nxt]
        if op == 0x66:
            if pend:
                res.extend(x for x in pend if x.strip(' \u3000'))
                pend = []
            if cur:
                t = ''.join(cur).strip(' \u3000')
                if t:
                    res.append(t)
                if flushed is not None:
                    flushed.append(t)
            cur = []
        elif op == 0x68:
            if cur is None:
                cur = []
            L = arg[0] if arg else 0
            cur.append(euc(arg[1:1 + L]))
        elif op == 0x6A:
            if cur is None:
                cur = []
            cur.append(SURNAME)
        elif op == 0x6B:
            if cur is None:
                cur = []
            cur.append(GIVEN)
        elif op in (0x6F, 0x6D):
            if cur is not None:
                t = ''.join(cur).strip(' \u3000')
                if t:
                    res.append(t)
                cur = None
        elif op == 0x1F6:
            L = arg[2] if len(arg) > 2 else 0
            pend.append(euc(arg[3:3 + L]))
        elif op == 0x1F7:
            res.extend(x for x in pend if x.strip(' \u3000'))
            pend = []
    if cur:
        t = ''.join(cur).strip(' \u3000')
        if t:
            res.append(t)
    if pend:
        res.extend(x for x in pend if x.strip(' \u3000'))
    return res


def order_key(nm):
    """顺序：E####（本编事件，序章 E0000 起，编号序）→ NN_S9xxx（各章会话）→ S####（個別場面）
    → EVE##（イベント短編）→ ED##（各角色 3 结局）
    ★ ROM 内无跨文件顺序表（推进靠 flag/存档驱动），此处按族+编号序，报告里注明。"""
    m = re.match(r'^E(\d{4})([A-Z]?)\.VML$', nm)
    if m:
        return (0, int(m.group(1)), m.group(2))
    m = re.match(r'^(\d\d)_S(\d{4})\.VML$', nm)
    if m:
        return (1, int(m.group(1)), m.group(2))
    m = re.match(r'^S(\d{4})\.VML$', nm)
    if m:
        return (2, int(m.group(1)), '')
    m = re.match(r'^EVE(\d\d)\.VML$', nm)
    if m:
        return (3, int(m.group(1)), '')
    m = re.match(r'^ED(\d\d)\.VML$', nm)
    if m:
        return (4, int(m.group(1)), '')
    return (9, 0, nm)


def main():
    fpk, out = sys.argv[1], sys.argv[2]
    d, ent = read_fpk(fpk)
    vmls = sorted([(nm, off, sz) for nm, off, sz in ent if nm.endswith('.VML')],
                  key=lambda x: order_key(x[0]))
    lines, stat = [], {}
    for nm, off, sz in vmls:
        bs = [x for x in boxes(d[off:off + sz]) if x not in SKIP]
        stat[nm] = len(bs)
        lines.extend(bs)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('files', len(vmls), 'lines', len(lines), 'chars', sum(len(x) for x in lines))
    print('sample:', lines[:3])
    over = [x for x in lines if len(x) > 54]
    print('over54', len(over), over[:3])


if __name__ == '__main__':
    main()
