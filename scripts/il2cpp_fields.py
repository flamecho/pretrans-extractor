#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纯 Python 读 IL2CPP global-metadata.dat 的类型定义/字段表（不反编译、零依赖）。

用途：拿到 `AdvScriptElement` 等类的 **字段声明顺序**，用于推断自定义 MessagePack formatter
的序列化顺序（绝大多数 formatter 按字段声明顺序写）。

用法:
  python scripts/il2cpp_fields.py <global-metadata.dat> <类名> [类名...]
  python scripts/il2cpp_fields.py <global-metadata.dat> --list AdvScript      # 模糊列类名
"""
import struct
import sys

# header: sanity, version, 然后是一串 (offset,size) 对
# 索引（v24~v31 通用）：0 stringLiteral, 1 stringLiteralData, 2 string, 3 events,
# 4 properties, 5 methods, 6 parameterDefaultValues, 7 fieldDefaultValues,
# 8 fieldAndParameterDefaultValueData, 9 fieldMarshaledSizes, 10 parameters,
# 11 fields, 12 genericParameters, 13 genericParameterConstraints, 14 genericContainers,
# 15 nestedTypes, 16 interfaces, 17 vtableMethods, 18 interfaceOffsets,
# 19 typeDefinitions, 20 images, 21 assemblies, 22 fieldRefs, 23 referencedAssemblies
IDX_STRING = 2
IDX_FIELDS = 11
IDX_TYPEDEFS = 19


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def read_pairs(d):
    pairs = []
    o = 8
    while o + 8 <= 0x100:
        off, size = struct.unpack_from('<II', d, o)
        pairs.append((off, size))
        o += 8
    return pairs


def cstr(d, base, idx):
    e = d.index(b'\0', base + idx)
    return d[base + idx:e].decode('utf-8', 'replace')


def main():
    path = sys.argv[1]
    args = sys.argv[2:]
    d = open(path, 'rb').read()
    sanity, version = struct.unpack_from('<Ii', d, 0)
    pairs = read_pairs(d)
    s_off, s_size = pairs[IDX_STRING]
    f_off, f_size = pairs[IDX_FIELDS]
    t_off, t_size = pairs[IDX_TYPEDEFS]
    print('[i] version=%d strings=%#x+%#x fields=%#x+%#x typedefs=%#x+%#x'
          % (version, s_off, s_size, f_off, f_size, t_off, t_size))

    # 标定 typedef 条目大小（v29 起 0x5C）
    entry = 0
    for cand in (0x5C, 0x60, 0x58, 0x64, 0x50):
        if t_size % cand == 0:
            entry = cand
            break
    if not entry:
        print('[!] 定不到 typedef 条目大小'); return 1
    n = t_size // entry
    print('[i] typedef 条目 %#x，共 %d 个类' % (entry, n))

    fentry = 0
    for cand in (12, 16):
        if f_size % cand == 0:
            fentry = cand
            break
    print('[i] field 条目 %d，共 %d 个字段' % (fentry, f_size // fentry))

    if args and args[0] == '--list':
        pat = args[1].lower() if len(args) > 1 else ''
        for i in range(n):
            b = t_off + i * entry
            nm = cstr(d, s_off, u32(d, b))
            ns = cstr(d, s_off, u32(d, b + 4))
            if pat in nm.lower():
                fc = struct.unpack_from('<H', d, b + 0x3C)[0]
                print('   %-40s ns=%-20s fields=%d' % (nm, ns, fc))
        return 0

    for want in args[:4]:
        found = False
        for i in range(n):
            b = t_off + i * entry
            nm = cstr(d, s_off, u32(d, b))
            if nm != want:
                continue
            ns = cstr(d, s_off, u32(d, b + 4))
            fields_start = struct.unpack_from('<i', d, b + 0x24)[0]
            field_count = struct.unpack_from('<H', d, b + 0x3C)[0]
            print('\n== %s (ns=%s) fields=%d start=%d' % (nm, ns, field_count, fields_start))
            for k in range(field_count):
                fb = f_off + (fields_start + k) * fentry
                fn = cstr(d, s_off, u32(d, fb))
                print('   %2d  %s' % (k, fn))
            found = True
        if not found:
            print('\n== %s 没找到（用 --list 模糊查）' % want)
    return 0


if __name__ == '__main__':
    sys.exit(main())
