"""YU-RIS YPF 归档提取（归档可内嵌在 exe 尾部，也可为独立 .ypf）。

ALL OUT (ver=462) 实测格式：

  header 16B : 'YPF\\0' | u16 ver | u16 pad | u32 count | u32 indexSize
  index      : 起点就在 header 处，共 indexSize 字节；数据区紧接其后。
    每条记录（长度 = nameLen + 23）：
      u8   mark            ← 不参与解析（多数记录恰等于名字字节数，但并非长度字段）
      u8   name[nameLen]   ← 逐字节 ^0xFF，cp932
      u8   type            ← 0=脚本(.ybn) 2=png 3=jpg 6=ogg
      u8   flag            ← 1 = zlib 压缩，0 = 原样
      u32  rawSize
      u32  compSize
      u32  offset          ← 相对 YPF 起点
      u8[8] unknown
    名字**没有**可靠的长度字段（那条 mark 在多数记录等于字节数、少数不等），
    因此解析用「候选签名 + cp932 名字校验」的贪心前向遍历，而不是步长硬走。
"""
import os
import struct
import sys
import zlib


def parse_index(d, ypf):
    ver, pad, cnt, isz = struct.unpack_from('<HHII', d, ypf + 4)
    raw = d[ypf:ypf + isz]
    pl = bytes(b ^ 0xFF for b in raw)          # 名字在此视图可读
    ds = len(d) - ypf

    cand = set()
    for q in range(0, len(pl) - 14):
        if raw[q] > 30 or raw[q + 1] > 1:      # type / flag
            continue
        r_, c_, o_ = struct.unpack_from('<III', raw, q + 2)
        if 0 < c_ <= r_ < 40_000_000 and o_ >= isz and o_ + c_ <= ds:
            cand.add(q)

    def name_of(b):
        if len(b) < 5 or b'\\' not in b or b'.' not in b:
            return None
        try:
            s = b.decode('cp932')
        except UnicodeDecodeError:
            return None
        return None if any(ord(c) < 0x20 for c in s) else s

    p, out = 0x24, []
    while len(out) < cnt:
        hit = None
        for q in range(p + 5, min(p + 130, len(pl) - 13)):
            if q in cand:
                s = name_of(pl[p + 1:q])
                if s:
                    hit = (q, s)
                    break
        if not hit:
            break
        q, s = hit
        typ, flg = raw[q], raw[q + 1]
        r_, c_, o_ = struct.unpack_from('<III', raw, q + 2)
        out.append((s, typ, flg, r_, c_, o_))
        p = q + 22
    return ver, cnt, out, isz


def extract(path, outdir):
    d = open(path, 'rb').read()
    ypf = d.rfind(b'YPF\0')
    if ypf < 0:
        raise SystemExit('未找到 YPF 魔数')
    ver, cnt, ents, isz = parse_index(d, ypf)
    print(f'YPF@{ypf:#x} ver={ver} count={cnt} 解析={len(ents)} indexSize={isz}')
    if len(ents) != cnt:
        print(f'!! 记录数不符：解析 {len(ents)} / 声明 {cnt}')
    ok = err = 0
    for (name, typ, flag, raw, comp, off) in ents:
        blob = d[ypf + off: ypf + off + comp]
        try:
            data = zlib.decompress(blob) if flag == 1 else blob
        except zlib.error as e:
            print('  ! 解压失败', name, e)
            err += 1
            continue
        if len(data) != raw:
            print('  ! 长度不符', name, len(data), raw)
            err += 1
        fp = os.path.join(outdir, name.replace('\\', os.sep))
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, 'wb') as f:
            f.write(data)
        ok += 1
    print(f'导出 {ok}，异常 {err}')
    return ents


if __name__ == '__main__':
    extract(sys.argv[1], sys.argv[2])
