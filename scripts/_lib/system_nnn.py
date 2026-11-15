"""Read System-NNN SPT using its header tables and length-prefixed commands.

Logical addresses and command sizes are measured in 32-bit words. No byte
scanning, encoding scores, or resynchronization are used to locate text.
"""
from dataclasses import dataclass
from pathlib import Path
import struct

XOR = bytes.maketrans(bytes(range(256)), bytes(255-i for i in range(256)))

@dataclass(frozen=True)
class String:
    index: int
    offset: int
    end: int
    text: str

@dataclass(frozen=True)
class Command:
    offset: int
    words: tuple

@dataclass
class Script:
    path: Path
    data: bytes
    header: tuple
    messages: list
    strings: list
    commands: list

def read_script(path):
    path=Path(path)
    data=path.read_bytes().translate(XOR)
    header=struct.unpack_from('<12I',data)
    if header[:3] != (32,0x66660001,0x55550001) or data[0x30:0x3a] != b'SPTHEADER0':
        raise ValueError(f'{path}: unsupported SPT header')
    def pool(count,base):
        addresses=struct.unpack_from('<'+str(count)+'I',data,base*4) if count else ()
        rows=[]
        for i,addr in enumerate(addresses):
            offset=addr*4
            end=data.index(0,offset)
            if offset < (base+count)*4 or end>=len(data):
                raise ValueError(f'{path}: bad string address {addr:x}')
            if i+1<count and ((end+4)//4)*4 != addresses[i+1]*4:
                raise ValueError(f'{path}: noncontiguous string slots at {offset:x}')
            rows.append(String(i,offset,end,data[offset:end].decode('cp932','strict')))
        return rows
    messages=pool(header[4],header[5]); strings=pool(header[6],header[7])
    commands=[]; offset=header[0]*4; stop=header[9]*4-16
    label_header=struct.unpack_from('<4I',data,stop)
    if label_header != (header[8]+4,0x66660001,0x55550002,0x44440003):
        raise ValueError(f'{path}: unsupported label-table header')
    while offset<stop:
        count=struct.unpack_from('<I',data,offset)[0]
        if count<2 or offset+count*4>stop:
            raise ValueError(f'{path}: invalid command at {offset:x}, size={count}')
        words=struct.unpack_from('<'+str(count)+'I',data,offset)
        commands.append(Command(offset,words)); offset+=count*4
    if offset!=stop: raise ValueError(f'{path}: command region did not close')
    return Script(path,data,header,messages,strings,commands)
