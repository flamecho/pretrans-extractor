#!/usr/bin/env python3
"""フルハウスキス 2 (PS2, Capcom/TENKY, SLPM-662.88) —— 全文本提取（定稿）。

链路：
  ISO9660 → SCRIPT.HD / SCRIPT.BIN
  .HD = u32 LE 长度表（每条一文件），.BIN = 顺序拼接、每条按 0x800 扇区对齐
  子文件 = "CRPT" + 8 字节循环 XOR 加密的 xorshift 无关流（每文件独立 8 字节键）
  明文 = "SCPT" 头 + 指令流 + 字符串池（cp932, NUL 结尾）

本脚本可独立重跑：
  python scripts/fhk2_extract.py <iso> <outdir>
产物：
  <outdir>/[PS2-JP]フルハウスキス 2.txt    UTF-8 BOM / 纯 LF
  <outdir>/_reindex.tsv                   每行 ← 源脚本名（自查用）
"""

import os
import re
import struct
import sys

SEC = 2048
SECTOR = 0x800

TAG = re.compile(r'<[^<>]*>')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
BROKEN = re.compile(r'<?(?:START|STOP)_KCPK>|,wait,\d+>|wait\(\d+\);')
BADCH = re.compile(r'[\ue000-\uf8ff\ufffd\x00-\x09\x0b-\x1f]')
DOLLAR = re.compile(r'\$[0-9]')
# 主角名宏（默认名：vndb/capcom 系谱 —— 鈴原 むぎ；<HER_N> 在台词里作呼名，取「むぎ」）
HER = [('<HER_N>', 'むぎ'), ('<HER_NAMAE>', 'むぎ'),
       ('<HER_MYOZI>', '鈴原'), ('<END_HER>', '')]
# 开发样例 / 调试脚本整文件排除
SKIP = re.compile(r'^(tuto_|FK2_|SAMPLE_|WB00_|S0001\.bin)')
DROP_STR = {'起動無し'}          # 脚本路由表里的常量占位（不上屏）
PLATE_OP19 = b'\x0d\x30\x00\x00\x08\x00\x00\x00\x00'


# ---------- ISO9660 ----------
class ISO:
    def __init__(self, path):
        self.f = open(path, 'rb')
        vd = self.read_sector(16)
        if vd[1:6] != b'CD001':
            raise SystemExit('not ISO9660')
        self.root = self.parse_record(vd[156:156 + vd[156]])

    def read_sector(self, lba, count=1):
        self.f.seek(lba * SEC)
        return self.f.read(SEC * count)

    @staticmethod
    def parse_record(r):
        nlen = r[32]
        return {'lba': struct.unpack_from('<I', r, 2)[0],
                'size': struct.unpack_from('<I', r, 10)[0],
                'flags': r[25],
                'name': r[33:33 + nlen].decode('latin1').split(';')[0]}

    def entries(self, rec):
        data = self.read_sector(rec['lba'], (rec['size'] + SEC - 1) // SEC)[:rec['size']]
        i, out = 0, []
        while i < len(data):
            ln = data[i]
            if ln == 0:
                i = (i // SEC + 1) * SEC
                continue
            if i + ln > len(data):
                break
            out.append(self.parse_record(data[i:i + ln]))
            i += ln
        return [e for e in out if e['name'] not in (b'\x00', b'\x01')]

    def get(self, path):
        cur = self.root
        for part in path.strip('/').split('/'):
            hit = [e for e in self.entries(cur) if e['name'].lower() == part.lower()]
            if not hit:
                raise SystemExit('not found: ' + path)
            cur = hit[0]
        self.f.seek(cur['lba'] * SEC)
        return self.f.read(cur['size'])


# ---------- HD/BIN ----------
def split_hd_bin(hd, b):
    n = len(hd) // 4
    sizes = [struct.unpack_from('<I', hd, i * 4)[0] for i in range(n)]
    pos, out = 0, []
    for s in sizes:
        out.append(b[pos:pos + s])
        pos += s
        pos = (pos + SECTOR - 1) // SECTOR * SECTOR
    assert pos == len(b), (pos, len(b))
    return out


def decrypt(d):
    """CRPT → SCPT 明文。键由已知明文 "SCPT"+4 个 0x00 反解（每文件 8 字节）。"""
    pay = d[4:]
    A = bytes(pay[i] ^ b'SCPT'[i] for i in range(4))
    B = pay[4:8]
    K = A + B
    return bytes(c ^ K[i % 8] for i, c in enumerate(pay))


def ops_of(p):
    """指令流：5 字节/条；op 0x19 = 10 字节。"""
    code = p[0x20:0x20 + struct.unpack_from('<I', p, 12)[0]]
    j = 0
    while j + 5 <= len(code):
        op = code[j]
        n = 10 if op == 0x19 else 5
        if j + n > len(code):
            return
        yield op, code[j + 1:j + n]
        j += n


def norm(t):
    for k, v in HER:
        t = t.replace(k, v)
    t = BROKEN.sub('', t)
    t = t.replace('<<', '<').replace('＠>', '＠')
    t = TAG.sub('', t)
    t = t.replace('<', '').replace('>', '')
    t = DOLLAR.sub('', t)
    return t


def split_lines(t, first):
    out = []
    for k, l in enumerate(t.split('\n')):
        if not (k == 0 and first):
            l = l.lstrip('\u3000 ')
        l = l.rstrip('\u3000 ')
        if l:
            out.append(l)
    return out


def parse_script(p):
    """→ [(kind, text)]  kind ∈ {'line','option'}；一次点击 = 一条 'line'。"""
    buf, out, newblk, prev = [], [], False, None
    for op, a in ops_of(p):
        if op in (0x0a, 0x0b, 0x0c, 0x0d):   # 分支标签 / 跳转 ⇒ 新块，禁止跨块并框
            newblk, prev = True, None
            continue
        if op != 6:
            prev = (op, a)
            continue
        off = struct.unpack('<I', a)[0]
        was, prev = prev, (op, a)
        if off >= len(p):
            continue
        e = p.find(b'\x00', off)
        if e < 0:
            continue
        raw = p[off:e].decode('cp932', errors='replace')
        if BADCH.search(raw):                # 8 字节尾填充解出的杂讯
            continue
        plate = (was == (0x19, PLATE_OP19)) and not raw.endswith('\n')
        t = norm(raw)
        if not JP.search(t):
            continue
        if plate or t.strip() == '？？？':   # 名字窗（独立窗口）⇒ 丢行不接前缀
            continue
        if t.strip() in DROP_STR:
            continue
        click = t.rstrip('\n ').endswith('＠')   # ＠ = 一次点击（清框）
        body = t.replace('＠', '')
        if newblk and buf:
            out.append(('line', ''.join(buf)))
            buf = []
        newblk = False
        ls = split_lines(body, not buf)
        if not ls:
            continue
        if click:
            buf.extend(ls)
            out.append(('line', ''.join(buf)))
            buf = []
        elif '\n' in raw:                    # 同框软换行 ⇒ 并入
            buf.extend(ls)
        else:                                # 选项
            if buf:
                out.append(('line', ''.join(buf)))
                buf = []
            out.append(('option', ''.join(ls)))
    if buf:
        out.append(('line', ''.join(buf)))
    return out


def main():
    iso_path, outdir = sys.argv[1], sys.argv[2]
    iso = ISO(iso_path)
    files = split_hd_bin(iso.get('SCRIPT.HD'), iso.get('SCRIPT.BIN'))
    names = [l for l in files[0].decode('cp932').split('\r\n') if l]
    assert len(names) == len(files), (len(names), len(files))

    res, src = [], []
    for i in range(1, len(files)):
        if SKIP.match(names[i]):
            continue
        for kind, t in parse_script(decrypt(files[i])):
            if res and res[-1] == t and src[-1] == names[i]:
                continue                     # 同文件同串重绘变体（互斥分支）折叠
            res.append(t)
            src.append(names[i])

    os.makedirs(outdir, exist_ok=True)
    dst = os.path.join(outdir, '[PS2-JP]フルハウスキス 2.txt')
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        for t in res:
            f.write(t + '\n')
    with open(os.path.join(outdir, '_reindex.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for t, s in zip(res, src):
            f.write('%s\t%s\n' % (s, t))
    print('files', len(files) - 1, 'lines', len(res), '->', dst)


if __name__ == '__main__':
    main()
