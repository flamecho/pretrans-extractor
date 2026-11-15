"""Record the installed Ungai executable's text handlers and read-only checks.

The runtime check reads only the executable's .text section. It never writes
process memory, advances the game, or touches save data.
"""
from pathlib import Path
import argparse
import collections
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json

import capstone
import pefile

RANGES = [
    ('message submission / 04 wait / 05 window effect / 06 choices', 0xf35a7, 0xf3b4a),
    ('new-page clear, CRLF consumption and first-line name processing', 0x10916b, 0x1097d5),
    ('row-capacity clipping and scrolling', 0x109880, 0x109990),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('--evidence', required=True, type=Path)
    ap.add_argument('--pid', type=int)
    ap.add_argument('--base', type=lambda x: int(x, 0))
    args = ap.parse_args()
    root = args.source.resolve()
    args.evidence.mkdir(parents=True, exist_ok=True)
    exe = root / 'souten_sp.exe'
    pe = pefile.PE(str(exe))
    static = pe.get_memory_mapped_image()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    proof = [f'Executable: {exe}',
             f'Executable SHA256: {hashlib.sha256(exe.read_bytes()).hexdigest()}',
             'Instruction addresses below are RVA; static image base = 0x400000.']
    record = {'exe': str(exe), 'exe_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
              'capstone_version': capstone.__version__, 'pefile_version': pefile.__version__}
    if args.pid:
        if args.base is None:
            ap.error('--pid requires --base')
        k = C.WinDLL('kernel32', use_last_error=True)
        k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        k.OpenProcess.restype = W.HANDLE
        k.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p,
                                       C.c_size_t, C.POINTER(C.c_size_t)]
        k.ReadProcessMemory.restype = W.BOOL
        k.CloseHandle.argtypes = [W.HANDLE]
        h = k.OpenProcess(0x10 | 0x400, False, args.pid)
        if not h:
            raise C.WinError(C.get_last_error())
        try:
            section = next(s for s in pe.sections if s.Name.rstrip(b'\0') == b'.text')
            start, size = section.VirtualAddress, section.Misc_VirtualSize
            buf = C.create_string_buffer(size)
            got = C.c_size_t()
            if not k.ReadProcessMemory(h, C.c_void_p(args.base + start), buf,
                                       size, C.byref(got)) or got.value != size:
                raise C.WinError(C.get_last_error())
            actual = buf.raw
            relocated = pe.get_memory_mapped_image(ImageBase=args.base)[start:start + size]
            differences = [start + i for i, (a, b) in enumerate(zip(actual, relocated)) if a != b]
            handlers_match = all(actual[a-start:b-start] == relocated[a-start:b-start]
                                 for _, a, b in RANGES)
            record['runtime'] = {'pid': args.pid, 'base': hex(args.base),
                                 'text_bytes_read': size, 'different_bytes': len(differences),
                                 'difference_rvas': [hex(x) for x in differences[:32]],
                                 'handlers_match_relocated_file': handlers_match,
                                 'runtime_text_sha256': hashlib.sha256(actual).hexdigest()}
            proof.append('Read-only runtime comparison: ' + json.dumps(record['runtime']))
            if not handlers_match:
                raise ValueError('The live text handlers differ from the installed executable')
        finally:
            k.CloseHandle(h)
    for heading, a, b in RANGES:
        proof.extend(['', heading])
        instructions = list(md.disasm(static[a:b], a))
        if not instructions or instructions[-1].address + instructions[-1].size != b:
            raise ValueError(f'Instruction region did not close: {heading}')
        proof.extend(f'{i.address:08x}: {i.mnemonic:8} {i.op_str}' for i in instructions)
    (args.evidence / 'engine-proof.txt').write_text('\n'.join(proof) + '\n',
                                                  encoding='utf-8', newline='\n')
    (args.evidence / 'engine-proof.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    inventory = [{'path': str(p.relative_to(root.parent.parent)), 'bytes': p.stat().st_size}
                 for p in sorted(root.parent.parent.rglob('*')) if p.is_file()]
    (args.evidence / 'inventory.json').write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'proof': record, 'inventory_files': len(inventory),
                      'extensions': dict(collections.Counter(Path(p['path']).suffix for p in inventory))},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
