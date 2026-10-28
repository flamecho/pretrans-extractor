"""HuneX HLZS（LZSS）解码器：dict 0x1000 / maxlen 0x12，解 `script_dialog_xx.hdlg` 等 HLZS 载荷。"""
import struct
DICT=0x1000; MAXLEN=0x12
def decode_lzs(inbuf, outsize):
    dic=bytearray(DICT); out=bytearray(); flag8=1; ip=0; dp=0
    n=len(inbuf)
    while ip<n and len(out)<outsize:
        if flag8==1:
            flag8=inbuf[ip]|0x100; ip+=1
        f=flag8&1; flag8>>=1
        if f:
            c=inbuf[ip]; ip+=1
            out.append(c); dic[dp]=c; dp=(dp+1)&(DICT-1)
        else:
            low=inbuf[ip]; high=inbuf[ip+1]; ip+=2
            wp=((high&0xf0)<<4|low)+MAXLEN; ws=(high&0x0f)+3
            for i in range(ws):
                c=dic[(wp+i)&(DICT-1)]; out.append(c); dic[dp]=c; dp=(dp+1)&(DICT-1)
    return bytes(out)
def decompress(buf):
    magic,ver,enc,dec=struct.unpack_from('<4I',buf,0)
    assert magic==int.from_bytes(b'HLZS','little'), hex(magic)
    return decode_lzs(buf[0x20:0x20+enc], dec)
