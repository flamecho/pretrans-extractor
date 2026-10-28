# -*- coding: utf-8 -*-
"""マツリカの炯-kEi- 天命華燭伝 (NS-JP) 全文本提取

链路: XCI(0xF000 root HFS0) -> secure HFS0 @0x17033 -> NCA0 @0x1F033 (Program, Standard crypto)
      -> RomFS -> common/script.memfs (RSON 索引) + common/script.membody (RZ + zlib)
      -> KUV 脚本 (magic C0DEABC1, "KUV ") -> 字符串池 + 字节码 -> 一行=一次点击

脚本格式（本作逆向结论, 2026-10-23）
  0x00 magic 'C0DEABC1'(LE) / 0x04 'KUV ' / 0x08 0x64 / 0x0C 字符串描述表偏移
  0x40 字符串池基址 (hdr[16]) / 0x44 字节码偏移 (hdr[17])
  字符串描述表: {u32 off, u32 bytelen} 相对池基址, 字符串为 UTF-16LE + 0000
  字节码: 0x0E <BE u32 字符串索引> = push; 0x2B <u8 参数个数> = 调用(命令名=最后 push 的串)
          (0x2B 后紧跟 0x2C 为同一条 invoke 的固定字节, 见实测)
  文本: GuideMess(text) / NameMess(name,text) 各占一次点击; KW = 等待点击; WinClear = 清框
  选项: SltAdd(id, 内部名, 显示文本); SltRun = 显示选项
  富文本: #C(TR,0x......)/#C(TR,prev) 颜色, #R(よみ,語) 注音, #KW 内联等待
"""
import os, sys, struct, zlib, re, json

# ---------------- memfs 索引 ----------------
TAG = 0x2002C800


def parse_memfs(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'RSON', d[:8]
    ents = []
    i = 0x10
    while i + 12 <= len(d):
        tag = struct.unpack('<I', d[i:i + 4])[0]
        if tag != TAG:
            i += 4
            continue
        off, size = struct.unpack('<II', d[i + 4:i + 12])
        ents.append((off, size))
        i += 12
    return ents


def read_entry(body, off, size):
    raw = body[off:off + size]
    assert raw[:2] == b'RZ', raw[:8]
    o = zlib.decompressobj()
    out = o.decompress(raw[6:])
    return out


# ---------------- 脚本解析 ----------------
def parse_script(d):
    assert d[:4] == b'\xc1\xab\xde\xc0' and d[4:8] == b'KUV ', d[:8]
    hdr = [struct.unpack('<I', d[i:i + 4])[0] for i in range(0, 0x48, 4)]
    desc_off, pool_off, code_off = hdr[3], hdr[16], hdr[17]
    desc_n = (hdr[11] - desc_off) // 8
    pool = []
    for i in range(desc_n):
        o, l = struct.unpack('<II', d[desc_off + i * 8:desc_off + i * 8 + 8])
        pool.append(d[pool_off + o:pool_off + o + l].decode('utf-16-le'))
    code = d[code_off:]
    ops, st, i = [], [], 0
    while i < len(code):
        b = code[i]
        if b == 0x0E:
            st.append(struct.unpack('>I', code[i + 1:i + 5])[0])
            i += 5
        elif b == 0x2B:
            na = code[i + 2]
            c = st.pop() if st else None
            args = st[-na:] if na else []
            if na:
                del st[-na:]
            ops.append((pool[c] if isinstance(c, int) and c < len(pool) else c, args))
            i += 3
        else:
            i += 1
    return pool, ops


# ---------------- 富文本 / 宏 ----------------
RE_C = re.compile(r'#C\([^)]*\)')
RE_R = re.compile(r'#R\([^)]*\)')
RE_KW = re.compile(r'#KW')
RE_OTHER = re.compile(r'#[A-Za-z]+(?:\([^)]*\))?')


def clean(s, macros=None):
    s = RE_C.sub('', s)
    s = RE_R.sub('', s)
    s = RE_KW.sub('', s)
    if macros:
        for k, v in macros.items():
            s = s.replace(k, v)
    s = s.replace('\n', '')
    return s


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '_work_matsurika/romfs/common'
    outdir = sys.argv[2] if len(sys.argv) > 2 else '_work_matsurika/out'
    os.makedirs(outdir, exist_ok=True)
    memfs = os.path.join(root, 'script.memfs')
    body = open(os.path.join(root, 'script.membody'), 'rb').read()
    ents = parse_memfs(memfs)
    print('memfs entries:', len(ents))
    lines, stats, titles = [], {}, []
    for n, (off, size) in enumerate(ents):
        raw = read_entry(body, off, size)
        try:
            pool, ops = parse_script(raw)
        except AssertionError:
            stats['bad'] = stats.get('bad', 0) + 1
            continue
        name = pool[0] if pool and pool[0] else ''
        titles.append(name)
        for cmd, args in ops:
            stats[cmd] = stats.get(cmd, 0) + 1
            if cmd == 'GuideMess' and args:
                t = clean(pool[args[0]])
                if t.strip():
                    lines.append(t)
            elif cmd == 'NameMess' and len(args) >= 2:
                t = clean(pool[args[1]])
                if t.strip():
                    lines.append(t)
            elif cmd == 'SltAdd' and len(args) >= 3:
                t = clean(pool[args[2]])
                if t.strip():
                    lines.append(t)
    print('scripts', len(titles), 'lines', len(lines))
    print('cmds', sorted(stats.items(), key=lambda x: -x[1])[:20])
    open(os.path.join(outdir, 'names.txt'), 'w', encoding='utf-8').write('\n'.join(titles))
    with open(os.path.join(outdir, 'text_raw.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
