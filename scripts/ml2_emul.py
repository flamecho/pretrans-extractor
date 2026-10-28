#!/usr/bin/env python3
"""ml2_emul.py -- 直接执行 SLPM_662.47 内的解压例程（unicorn, MIPS64/R5900 子集）.

用途：给 flags=1 (LZSS 变体) 解压提供"原机真值"，并用于校验 Python 实现。
签名（由调度器 0x141dd4 / 0x141e40 反汇编确认）:
    int decode(const u8* src, u32 csize, u8* dst, u32 usize)   -> 输出字节数 / -1

注意：R5900 的 MMI 指令（SQ/LQ, opcode 0x1E/0x1F）unicorn 不支持，
装载镜像时统一 NOP 掉（只影响寄存器保存/恢复，不影响解码逻辑）。
"""
import sys

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS64, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn.mips_const import *

ELF = '_work_ml2/x/SLPM_662.47'
CODE_BASE = 0x100000
CODE_FILE_OFF = 0x80
CODE_SIZE = 0x140000
STACK = 0x7F0000
SRC = 0x9000000
DST = 0x9800000
SENTINEL = 0xDEA000
SRC_CAP = 0x400000
DST_CAP = 0xC00000

REGS = ('V0', 'V1', 'A0', 'A1', 'A2', 'A3', 'T0', 'T1', 'T2', 'T3', 'T4', 'T5',
        'T6', 'T7', 'S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'T8', 'T9', 'GP')


def _load_image():
    d = open(ELF, 'rb').read()
    img = bytearray(d[CODE_FILE_OFF:CODE_FILE_OFF + CODE_SIZE])
    for i in range(0, len(img) - 3, 4):
        if (img[i + 3] >> 2) in (0x1E, 0x1F):      # SQ / LQ
            img[i:i + 4] = b'\x00\x00\x00\x00'
    return bytes(img)


class Decoder(object):
    def __init__(self):
        self.mu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 + UC_MODE_LITTLE_ENDIAN)
        self.mu.mem_map(CODE_BASE, CODE_SIZE)
        self.mu.mem_write(CODE_BASE, _load_image())
        self.mu.mem_map(STACK, 0x20000)
        self.mu.mem_write(STACK, b'\x00' * 0x20000)
        self.mu.mem_map(SRC, SRC_CAP)
        self.mu.mem_map(DST, DST_CAP)
        self.mu.mem_map(SENTINEL, 0x1000)
        self.mu.hook_add(UC_HOOK_CODE, self._hook)

    def _hook(self, mu, addr, size, ud):
        if addr == SENTINEL:
            mu.emu_stop()

    def call(self, entry, data, usize, max_insn=40000000):
        mu = self.mu
        if len(data) > SRC_CAP or usize > DST_CAP:
            raise ValueError('buffer too small')
        for name in REGS:
            mu.reg_write(getattr(__import__('unicorn.mips_const', fromlist=['x']), 'UC_MIPS_REG_' + name), 0)
        mu.mem_write(SRC, data)
        mu.reg_write(UC_MIPS_REG_A0, SRC)
        mu.reg_write(UC_MIPS_REG_A1, len(data))
        mu.reg_write(UC_MIPS_REG_A2, DST)
        mu.reg_write(UC_MIPS_REG_A3, usize)
        mu.reg_write(UC_MIPS_REG_SP, STACK + 0x10000)
        mu.reg_write(UC_MIPS_REG_RA, SENTINEL)
        mu.emu_start(entry, SENTINEL, count=max_insn)
        v0 = mu.reg_read(UC_MIPS_REG_V0)
        if v0 & 0x80000000:
            raise ValueError('decoder returned -1')
        if v0 != usize:
            raise ValueError('decoder size %d != usize %d' % (v0, usize))
        return bytes(mu.mem_read(DST, usize))


DEC_LZSS = 0x136070
DEC_T2 = 0x135E30

if __name__ == '__main__':
    ent = int(sys.argv[1], 16)
    data = open(sys.argv[2], 'rb').read()
    out = Decoder().call(ent, data, int(sys.argv[4], 0))
    open(sys.argv[3], 'wb').write(out)
    print('ok %d' % len(out))
