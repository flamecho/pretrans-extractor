# -*- coding: utf-8 -*-
"""銀の冠碧の涙 —— 按 silverblue.tpm 真实代码重写的 CX 解密器（无任何补丁表）

全部取值均来自 .decc 解密后的真实指令（见 decc_full.txt / decc_disasm.txt）：

  0x1e001e80  Decode  : 按 hash 取 key，整段 XOR，再在 start/end 两处定点补 XOR；
                        文件跨过 boundary=0x1eb+(hash&0x1a1) 时后半段换 hash2=hash^(hash>>16)
  0x1e001fb0  DecodeRange : 主体
  0x1e001090  GetKey  : (hash&0x7f) 选 128 槽之一，buf 里放 JIT 出来的 128 字节 x86 桩，
                        桩(arg=hash>>7) 与 桩(arg=~arg) 得到 3 个密钥字节 + start/end
  0x1e0011d0  VM 初始化 (seed = 槽号, 输出上限 0x80)
  0x1e001220  LCG     : state = state*0x41C64E6D + 0x3039; ret = ((s>>16)^(s<<16)^new) & 0xFFFFFFFF
  0x1e0014d0/1520/15a0/1650/18a0  x86 代码生成器（真实 op 表见下方 OP1650 / OP18A0）
  0x1e0054a0  控制块 1024 × dword（4096 B，映像内静态常量，首个 dword 起就是许可声明字符串）
"""
import os
import struct

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(ROOT, 'tpm_mem.bin')

CTRL_VA = 0x1e0054a0          # GetKey 桩里 mov esi, 0x1e0054a0 的立即数
IMG_BASE = 0x1e000000
M32 = 0xffffffff


def load_ctrl_block():
    d = open(IMG, 'rb').read()
    off = CTRL_VA - IMG_BASE
    assert len(d) >= off + 4096, 'image too small'
    return d[off:off + 4096]


CTRL = struct.unpack('<1024I', load_ctrl_block())


# ---------------------------------------------------------------------------
# 0x1e0011d0 / 0x1e0014d0 : 代码生成 VM
# ---------------------------------------------------------------------------
class VM:
    def __init__(self, seed, size=0x80):
        self.buf = bytearray()
        self.cap = size
        self.seed = seed & M32

    # 0x1e001220
    def rand(self):
        x = self.seed
        self.seed = (x * 0x41C64E6D + 0x3039) & M32
        return ((x >> 16) ^ ((x << 16) & M32) ^ self.seed) & M32

    def emit(self, *bs):
        if len(self.buf) + len(bs) > self.cap:
            raise Overflow()          # 0x1250 返回 0 时调用者立刻逐层返回
        self.buf.extend(bs)

    def emit32(self, v):                       # 0x1e001480
        self.emit(v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >> 24) & 0xff)

    # ---- 0x1e0015a0 : 叶子表达式（写 eax） ----
    def gen_leaf(self):
        c = self.rand() % 3
        if c == 0:                             # 0x1633
            self.emit(0x8b, 0xc7)              # mov eax, edi
        elif c == 1:                           # 0x161a
            self.emit(0xb8)
            self.emit32(self.rand())           # mov eax, imm32
        else:                                  # 0x15c0
            self.emit(0xbe)
            self.emit32(CTRL_VA)               # mov esi, 0x1e0054a0
            self.emit(0x8b, 0x86)
            self.emit32((self.rand() & 0x3ff) << 2)   # mov eax, [esi + (rand&0x3ff)*4]

    # ---- 0x1e0018a0 : 语句（写 eax），带 ebx 暂存 ----
    def gen_stmt(self, n):
        if n - 1 == 0:
            return self.gen_leaf()
        self.emit(0x53)                        # push ebx
        for _ in range(2):
            if self.rand() & 1:
                self.gen_stmt(n - 1)
            else:
                self.gen_expr(n - 1)
            if _ == 0:
                self.emit(0x89, 0xc3)          # mov ebx, eax
        c = self.rand() % 6
        if c == 0:                             # 0x19af
            self.emit(0x51)                    # push ecx
            self.emit(0x89, 0xd9)              # mov ecx, ebx
            self.emit(0x83, 0xe1, 0x0f)        # and ecx, 0xf
            self.emit(0xd3, 0xe0)              # shl eax, cl
            self.emit(0x59)                    # pop ecx
        elif c == 1:                           # 0x199a
            self.emit(0x0f, 0xaf, 0xc3)        # imul eax, ebx
        elif c == 2:                           # 0x1a02
            self.emit(0x51)
            self.emit(0x89, 0xd9)
            self.emit(0x83, 0xe1, 0x0f)
            self.emit(0xd3, 0xe8)              # shr eax, cl
            self.emit(0x59)
        elif c == 3:                           # 0x1977
            self.emit(0x29, 0xd8)              # sub eax, ebx
        elif c == 4:                           # 0x195a
            self.emit(0x01, 0xd8)              # add eax, ebx
        else:                                  # 0x1980 -> 0x195a
            self.emit(0xf7, 0xd8)              # neg eax
            self.emit(0x01, 0xd8)              # add eax, ebx
        self.emit(0x5b)                        # pop ebx

    # ---- 0x1e001650 : 表达式（写 eax） ----
    def gen_expr(self, n):
        if n - 1 == 0:
            return self.gen_leaf()
        if self.rand() & 1:
            self.gen_stmt(n - 1)
        else:
            self.gen_expr(n - 1)
        c = self.rand() % 8
        if c == 0:                             # 0x17f8  查控制块
            self.emit(0xbe)
            self.emit32(CTRL_VA)
            self.emit(0x25)
            self.emit32(0x3ff)                 # and eax, 0x3ff
            self.emit(0x8b, 0x04, 0x86)        # mov eax, [esi + eax*4]
        elif c == 1:                           # 0x16bf
            self.emit(0xf7, 0xd8)              # neg eax
        elif c == 2:                           # 0x16dd
            self.emit(0x40)                    # inc eax
        elif c == 3:                           # 0x16a1
            self.emit(0xf7, 0xd0)              # not eax
        elif c == 4:                           # 0x17b6  加减立即数
            self.emit(0x05 if (self.rand() & 1) else 0x2d)
            self.emit32(self.rand())
        elif c == 5:                           # 0x16f5
            self.emit(0x48)                    # dec eax
        elif c == 6:                           # 0x16f9 位掺混
            self.emit(0x53)                    # push ebx
            self.emit(0x89, 0xc3)              # mov ebx, eax
            self.emit(0x81, 0xe3)
            self.emit32(0xAAAAAAAA)            # and ebx, 0xAAAAAAAA
            self.emit(0x25)
            self.emit32(0x55555555)            # and eax, 0x55555555
            self.emit(0xd1, 0xeb)              # shr ebx, 1
            self.emit(0xd1, 0xe0)              # shl eax, 1
            self.emit(0x09, 0xd8)              # or eax, ebx
            self.emit(0x5b)                    # pop ebx
        else:                                  # c == 7: 0x17a4
            self.emit(0x35)                    # xor eax, imm32
            self.emit32(self.rand())

    # ---- 0x1e001520 : 生成整个桩 ----
    def gen_stub(self, n):
        self.emit(0x57, 0x56, 0x53, 0x51, 0x52)      # push edi/esi/ebx/ecx/edx
        self.emit(0x8b, 0x7c, 0x24, 0x18)            # mov edi, [esp+0x18]
        self.gen_stmt(n)
        self.emit(0x5a, 0x59, 0x5b, 0x5e, 0x5f)      # pop edx/ecx/ebx/esi/edi
        self.emit(0xc3)                              # ret

    # ---- 0x1e0014d0 : 深度 5..1 重试 ----
    def build(self):
        for n in (5, 4, 3, 2, 1):
            self.buf = bytearray()
            try:
                self.gen_stub(n)
            except Overflow:
                continue
            return bytes(self.buf)
        return None


class Overflow(Exception):
    pass


_STUB_CACHE = {}


def get_stub(idx):
    if idx not in _STUB_CACHE:
        _STUB_CACHE[idx] = VM(idx).build()
    return _STUB_CACHE[idx]


# ---------------------------------------------------------------------------
# 极简 x86 解释器：只跑上面生成器可能产生的指令
# ---------------------------------------------------------------------------
def run_stub(code, arg):
    r = {'eax': 0, 'ebx': 0, 'ecx': 0, 'edx': 0, 'esi': 0, 'edi': 0}
    stack = [0] * 64
    sp = 0

    def push(v):
        nonlocal sp
        stack[sp] = v & M32
        sp += 1

    def pop():
        nonlocal sp
        sp -= 1
        return stack[sp]

    push(arg)                     # 调用者的返回地址位（占位）
    push(0)                       # ret addr
    pc = 0
    limit = 4096
    while off_ok(pc, code) and limit:
        limit -= 1
        op = code[pc]
        if 0x50 <= op <= 0x57:
            push(r[('eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi')[op - 0x50]])
            pc += 1
        elif 0x58 <= op <= 0x5f:
            r[('eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi')[op - 0x58]] = pop()
            pc += 1
        elif 0xb8 <= op <= 0xbf:
            r[('eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi')[op - 0xb8]] = \
                struct.unpack_from('<I', code, pc + 1)[0]
            pc += 5
        elif op == 0x8b:
            m = code[pc + 1]
            if m == 0xc7:
                r['eax'] = r['edi']; pc += 2
            elif m == 0x86:
                disp = struct.unpack_from('<i', code, pc + 2)[0]
                r['eax'] = mem_read(r['esi'], disp); pc += 6
            elif m == 0x04 and code[pc + 2] == 0x86:      # mov eax,[esi+eax*4]
                r['eax'] = mem_read(r['esi'], r['eax'] * 4); pc += 3
            elif m == 0x7c and code[pc + 2] == 0x24:
                d = code[pc + 3]
                r['edi'] = stack[sp - 1 - d // 4]
                pc += 4
            else:
                raise NotImplementedError('8b %02x' % m)
        elif op == 0x89:
            m = code[pc + 1]
            if m == 0xc3:
                r['ebx'] = r['eax']
            elif m == 0xd9:
                r['ecx'] = r['ebx']
            else:
                raise NotImplementedError('89 %02x' % m)
            pc += 2
        elif op == 0x01 and code[pc + 1] == 0xd8:
            r['eax'] = (r['eax'] + r['ebx']) & M32; pc += 2
        elif op == 0x29 and code[pc + 1] == 0xd8:
            r['eax'] = (r['eax'] - r['ebx']) & M32; pc += 2
        elif op == 0x09 and code[pc + 1] == 0xd8:
            r['eax'] = r['eax'] | r['ebx']; pc += 2
        elif op == 0x25:
            r['eax'] = r['eax'] & struct.unpack_from('<I', code, pc + 1)[0]; pc += 5
        elif op == 0x0d:
            r['eax'] = r['eax'] | struct.unpack_from('<I', code, pc + 1)[0]; pc += 5
        elif op == 0x05:
            r['eax'] = (r['eax'] + struct.unpack_from('<I', code, pc + 1)[0]) & M32; pc += 5
        elif op == 0x2d:
            r['eax'] = (r['eax'] - struct.unpack_from('<I', code, pc + 1)[0]) & M32; pc += 5
        elif op == 0x35:
            r['eax'] = r['eax'] ^ struct.unpack_from('<I', code, pc + 1)[0]; pc += 5
        elif op == 0x83 and code[pc + 1] == 0xe1:
            r['ecx'] = r['ecx'] & code[pc + 2]; pc += 3
        elif op == 0x81 and code[pc + 1] == 0xe3:
            r['ebx'] = r['ebx'] & struct.unpack_from('<I', code, pc + 2)[0]; pc += 6
        elif op == 0xf7 and code[pc + 1] == 0xd0:
            r['eax'] = (~r['eax']) & M32; pc += 2
        elif op == 0xf7 and code[pc + 1] == 0xd8:
            r['eax'] = (-r['eax']) & M32; pc += 2
        elif op == 0x40:
            r['eax'] = (r['eax'] + 1) & M32; pc += 1
        elif op == 0x48:
            r['eax'] = (r['eax'] - 1) & M32; pc += 1
        elif op == 0xd3 and code[pc + 1] == 0xe0:
            r['eax'] = (r['eax'] << (r['ecx'] & 0x1f)) & M32; pc += 2
        elif op == 0xd3 and code[pc + 1] == 0xe8:
            r['eax'] = (r['eax'] >> (r['ecx'] & 0x1f)) & M32; pc += 2
        elif op == 0xd1 and code[pc + 1] == 0xeb:
            r['ebx'] = r['ebx'] >> 1; pc += 2
        elif op == 0xd1 and code[pc + 1] == 0xe0:
            r['eax'] = (r['eax'] << 1) & M32; pc += 2
        elif op == 0x0f and code[pc + 1] == 0xaf and code[pc + 2] == 0xc3:
            r['eax'] = (r['eax'] * r['ebx']) & M32; pc += 3
        elif op == 0xc3:
            break
        else:
            raise NotImplementedError('op %02x @%d' % (op, pc))
    return r['eax']


def off_ok(pc, code):
    return 0 <= pc < len(code)


def mem_read(base, disp):
    # 只可能读 0x1e0054a0 控制块
    idx = (base - CTRL_VA + disp) // 4
    return CTRL[idx]


# ---------------------------------------------------------------------------
# 0x1e001090 : GetKey
# ---------------------------------------------------------------------------
def get_key(h):
    idx = h & 0x7f
    arg = (h >> 7) & M32
    stub = get_stub(idx)
    if stub is None:
        raise RuntimeError('stub gen failed idx=%d' % idx)
    a = run_stub(stub, arg)
    b = run_stub(stub, (~arg) & M32)
    start = (b >> 16) & 0xffff
    end = b & 0xffff
    if start == end:
        end = (end + 1) & 0xffff
    k0 = a & 0xff
    if k0 == 0:
        k0 = 1
    return dict(start=start, end=end, k0=k0, k1=(a >> 8) & 0xff, k2=(a >> 16) & 0xff)


# ---------------------------------------------------------------------------
# 0x1e001e80 / 0x1e001fb0 : Decode
# ---------------------------------------------------------------------------
def decode_range(data, pos, count, h):
    k = get_key(h)
    for i in range(count):
        data[pos + i] ^= k['k0']
    if pos <= k['start'] < pos + count:
        data[k['start']] ^= k['k1']
    if pos <= k['end'] < pos + count:
        data[k['end']] ^= k['k2']
    return k


def decode(data, h):
    """整段解密（引擎在 pos=0 处一次读完整文件）；返回 (k_first, k_second)"""
    n = len(data)
    bnd = 0x1eb + (h & 0x1a1)
    h2 = h ^ (h >> 16)
    if bnd < n and bnd > 0:
        k1 = decode_range(data, 0, bnd, h)
        k2 = decode_range(data, bnd, n - bnd, h2)
        return bnd, k1, k2
    if bnd <= 0:
        return 0, decode_range(data, 0, n, h2), None
    return bnd, decode_range(data, 0, n, h), None
