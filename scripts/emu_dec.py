# -*- coding: utf-8 -*-
"""用 unicorn 模拟执行 SLPM 里的解压函数（0x142c80 = type1, 0x142a20 = type2）

ELF 已打过补丁：$sp 基址的 sq/lq 改写成 sd/ld（栈存取成对，标量代码语义不变）。
"""
import struct
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from unicorn import *
from unicorn.mips_const import *

ELF = os.path.join(VNTRANS_HOME, '_src_etoile/SLPM_an.bin')
IMG_BASE, IMG_OFF, IMG_SIZE = 0x100000, 0x80, 0xdc580
SRC, DST, STK = 0x300000, 0x400000, 0x700000
RET = 0x7FFF00

class Decomp:
    def __init__(self):
        self.img = open(ELF, 'rb').read()
        self.mu = None

    def _setup(self, src, cap):
        mu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 + UC_MODE_LITTLE_ENDIAN)
        mu.mem_map(IMG_BASE, 0x100000)          # 代码+数据
        mu.mem_write(IMG_BASE, self.img[IMG_OFF:IMG_OFF + IMG_SIZE])
        mu.mem_map(0x200000, 0x200000)          # src 区
        mu.mem_map(0x400000, 0x300000)          # dst 区
        mu.mem_map(0x700000, 0x100000)          # 栈
        mu.mem_write(SRC, src)
        mu.reg_write(UC_MIPS_REG_SP, STK + 0xF000)
        mu.reg_write(UC_MIPS_REG_GP, 0x1e40f0)
        mu.reg_write(UC_MIPS_REG_RA, RET)
        mu.mem_write(RET, b'\x00' * 8)
        return mu

    def run(self, func, src, out_cap):
        mu = self._setup(src, out_cap)
        mu.reg_write(UC_MIPS_REG_A0, SRC)
        mu.reg_write(UC_MIPS_REG_A1, len(src))
        mu.reg_write(UC_MIPS_REG_A2, DST)
        mu.reg_write(UC_MIPS_REG_A3, out_cap)
        calls = []

        def on_code(uc, address, size, _):
            if address == RET:
                uc.emu_stop()
            elif address == 0:
                uc.emu_stop()
        mu.hook_add(UC_HOOK_CODE, on_code)
        try:
            mu.emu_start(func, RET, count=200_000_000)
        except UcError as e:
            return None, 'ucerr:%s @pc=%08x' % (e, mu.reg_read(UC_MIPS_REG_PC))
        out = bytes(mu.mem_read(DST, out_cap))
        return out, 'ok'

def dec1(src, out_cap):
    return Decomp().run(0x142c80, src, out_cap)

def dec2(src, out_cap):
    return Decomp().run(0x142a20, src, out_cap)
