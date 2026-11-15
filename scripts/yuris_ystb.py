"""YU-RIS YSTB 脚本解析：解开 XOR 段并反汇编成 cmd + 参数。

V300 头（8×u32，32 字节）：
  'YSTB' | version | n_cmds | cmds_size(=n*4) | args_size | expr_size | lnos_size(=n*4) | pad
四段：cmds_data / args_data / expr_data / lnos_data，每段各自从段首起算，
用 4 字节密钥循环 XOR（本作 key = 0x96AC6FD3，字节序 little：D3 6F AC 96）。

Cmd : u8 code, u8 n_args, u16 n_para
Arg : u16 kw_id, u8 type(low2: 1=INT 2=FLT 3=STR 0=特殊/WORD), u8 assign,
      u32 expr_size, u32 expr_offset
"""
import struct

KEY = 0x96AC6FD3


def decrypt(buf, key=KEY, order='little'):
    kb = key.to_bytes(4, order)
    return bytes(b ^ kb[i % 4] for i, b in enumerate(buf))


class Script:
    def __init__(self, path, key=KEY):
        d = open(path, 'rb').read()
        magic, ver, n, csz, asz, esz, lsz, pad = struct.unpack_from('<8I', d, 0)
        assert magic == 0x42545359, 'not YSTB'
        self.ver, self.n = ver, n
        o = 32
        self.cmds = decrypt(d[o:o + csz], key); o += csz
        self.args = decrypt(d[o:o + asz], key); o += asz
        self.expr = decrypt(d[o:o + esz], key); o += esz
        self.lnos = decrypt(d[o:o + lsz], key)
        self.esz, self.asz = esz, asz
        self.parse()

    def parse(self):
        ap = 0
        self.items = []
        for i in range(self.n):
            code, na, npara = struct.unpack_from('<BBH', self.cmds, i * 4)
            args = []
            for _ in range(na):
                if ap + 12 > len(self.args):
                    break
                kw, ty, asg, esz, eoff = struct.unpack_from('<HBBII', self.args, ap)
                ap += 12
                args.append((kw, ty, asg, esz, eoff))
            lno = struct.unpack_from('<I', self.lnos, i * 4)[0] if i * 4 + 4 <= len(self.lnos) else -1
            self.items.append((code, npara, lno, args))
        self.args_used = ap

    def word(self, esz, eoff):
        return self.expr[eoff:eoff + esz]
