#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""psvskip_patch.py — 让 psvpfsparser 在单文件解密失败时继续（跳过），不整进程退出。

用法:
  python scripts/psvskip_patch.py analyze <psvpfsparser.exe>
  python scripts/psvskip_patch.py patch   <src.exe> <dst.exe>

原理: 在 decrypt_files() 里定位 `call decrypt_file` 之后对返回值的条件跳转
      （"Failed to decrypt: " 字符串的 xref 往回找），把该条件跳转 NOP 掉，
      使失败时也落入成功分支 → 打印 Decrypted: 并继续下一个文件。
      失败文件的输出是垃圾/空，但会继续处理后续文件（用于只取小体积脚本）。
"""
import sys, struct

def load_pe(path):
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3c)[0]
    assert d[pe:pe+4] == b'PE\0\0', 'not PE'
    nsec = struct.unpack_from('<H', d, pe+6)[0]
    optsz = struct.unpack_from('<H', d, pe+20)[0]
    magic = struct.unpack_from('<H', d, pe+24)[0]
    imagebase = struct.unpack_from('<Q', d, pe+24+24)[0] if magic == 0x20b else struct.unpack_from('<I', d, pe+24+28)[0]
    sec = pe + 24 + optsz
    secs = []
    for i in range(nsec):
        o = sec + i*40
        name = d[o:o+8].rstrip(b'\0').decode('latin1')
        vsz, va, rsz, rptr = struct.unpack_from('<IIII', d, o+8)
        secs.append(dict(name=name, va=va, vsz=vsz, rptr=rptr, rsz=rsz))
    return d, imagebase, secs

def va2off(secs, imagebase, va):
    r = va - imagebase
    for s in secs:
        if s['va'] <= r < s['va'] + max(s['vsz'], s['rsz']):
            return s['rptr'] + (r - s['va'])
    return None

def main():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    cmd = sys.argv[1]
    path = sys.argv[2]
    d, ib, secs = load_pe(path)
    print('imagebase=%#x sections=%s' % (ib, [(s['name'], hex(s['va']), hex(s['rsz'])) for s in secs]))

    # 找字符串
    targets = {}
    for key in (b'Failed to decrypt: ', b'Crypto Engine failed'):
        i = d.find(key)
        print('str', key, 'fileoff=%#x' % i if i >= 0 else 'NOT FOUND')
        if i < 0: continue
        for s in secs:
            if s['rptr'] <= i < s['rptr'] + s['rsz']:
                targets[key] = ib + s['va'] + (i - s['rptr'])
    if b'Failed to decrypt: ' not in targets:
        print('abort: string not found'); return

    strva = targets[b'Failed to decrypt: ']
    text = [s for s in secs if s['name'] == '.text'][0]
    code = d[text['rptr']:text['rptr']+text['rsz']]
    base = ib + text['va']
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    insns = list(md.disasm(code, base))
    print('insns', len(insns))

    hits = []
    for idx, ins in enumerate(insns):
        if ins.mnemonic == 'lea' and 'rip' in ins.op_str:
            # lea rax, [rip + 0x...]
            try:
                disp = int(ins.op_str.split('rip + ')[1].rstrip(']'), 16)
            except Exception:
                continue
            if ins.address + ins.size + disp == strva:
                hits.append(idx)
    print('xref idx', hits)
    for idx in hits:
        print('--- context around xref idx', idx, hex(insns[idx].address))
        for j in range(max(0, idx-12), min(len(insns), idx+3)):
            mark = '>>' if j == idx else '  '
            print(mark, hex(insns[j].address), insns[j].mnemonic, insns[j].op_str, '|', insns[j].bytes.hex())
        # 往回找条件跳转
        for j in range(idx, max(0, idx-40), -1):
            m = insns[j].mnemonic
            if m.startswith('j') and m != 'jmp':
                print('    CANDIDATE', hex(insns[j].address), m, insns[j].op_str, '|', insns[j].bytes.hex())
                break

    if cmd == 'patch':
        dst = sys.argv[3]
        out = bytearray(d)
        n = 0
        for idx in hits:
            for j in range(idx, max(0, idx-40), -1):
                m = insns[j].mnemonic
                if m.startswith('j') and m != 'jmp':
                    off = va2off(secs, ib, insns[j].address)
                    out[off:off+len(insns[j].bytes)] = b'\x90'*len(insns[j].bytes)
                    print('patched', hex(insns[j].address), m, insns[j].op_str)
                    n += 1
                    break
        open(dst, 'wb').write(out)
        print('wrote', dst, 'patches', n)

main()
