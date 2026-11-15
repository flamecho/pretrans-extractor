#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Laughter Land (WillPlus / RIO bytecode) text extractor.
Pipeline: will_arc(V1) unpack Rio.arc -> ROR2 deobfuscate each WSC object -> RIO disassemble -> cp932 text.
Output: one line per text box (text_n / text_c / text_extend), UTF-8 BOM, LF.
Reference: dogtopus/willplus-adv-tools (opcode.rb, wsc2scr.py, will_arc.py)."""
import struct, re, os, glob

# ---- RIO opcode table (default version) ported from dogtopus/opcode.rb ----
RIO = {
0x00:[None], 0x01:['Cs<', '_jmp', 'sub01'], 0x02:['S<','option','opt02'],
0x03:['CS<Cs<','_set','sub03'], 0x04:[None,'exit'], 0x05:['','apply_timer'],
0x06:['i<','jmp_offset'], 0x07:['Z*','goto'], 0x08:['C','text_size_modifier'],
0x09:['Z*','call'], 0x0a:[None,'return'], 0x0b:['C','set_timer'],
0x21:['Cs<', 'bgm'], 0x22:['Cs<','bgm_stop'], 0x23:['Cs<C2s<Z*','voice'],
0x25:['cC3s<c2xZ*','se'], 0x26:['c','se_stop'], 0x28:['C2s<'],
0x29:['cs<','se_fadeout'], 0x30:['Cs<','wait_30'], 0x41:['s<xZ*','text_n'],
0x42:['s<x2Z*Z*','text_c'], 0x43:['i<s<Z*','ui_load_anm'], 0x45:['Cs<','ui_show_anm'],
0x46:['s<4CZ*','bg'], 0x47:['C','bg_color'], 0x48:['Cs<4CCZ*','fg'],
0x49:['s<','layer1_cl'], 0x4a:['Cs<2i<s<','transition','sub4a'], 0x4b:['Cs<2i<s<','add_animation_key_frame'],
0x4c:['C','play_animation'], 0x4d:['C2s<','screen_effect'], 0x4e:['C3','weather'],
0x4f:['Cs<','ui_hide_anm'], 0x50:['Z*','ui_load_table'], 0x51:['S<2','ui_read_click'],
0x52:['C','se_wait'], 0x54:['Z*','set_trans_mask'], 0x55:[None], 0x61:['CZ*','video'],
0x62:[None,'clear_screen_effect'], 0x64:['Cs<2','fg_transform'], 0x68:['s<3','bg_vp'],
0x71:['Z*','side_image'], 0x72:[None,'hide_side_image'], 0x73:['s<4CZ*','obj'],
0x74:['C','obj_cl'], 0x78:['C7'], 0x79:[None], 0x82:['s<','sleep'], 0x83:[None,'open_load_menu'],
0x84:[None,'open_save_menu'], 0x85:['C','block_savegame_access'], 0x86:['C','unk_86_delay'],
0x88:['C2','initiate_battle'], 0x89:[None], 0x8b:[None,'open_prefereces_menu'],
0x8c:['s<','event_id'], 0x8e:[None,'highlight_visited_options'], 0xa7:[None], 0xa9:[None],
0xa0:['s<2c'], 0xae:[None], 0xb3:['C'], 0xb6:['s<Z*Z*','text_extend'], 0xb8:['s<','layer2_cl'],
0xb9:['C','tint'], 0xbd:['C'], 0xe0:['Z*','event_name'], 0xe2:[None,'quick_load'],
0xe4:['C'], 0xe6:['C'], 0xe7:['C2'], 0xff:[None,'eof'],
}

def read_params(fmt, buf, off):
    vals=[]; p=off; i=0; n=len(fmt)
    while i < n:
        lead=0
        while i<n and fmt[i].isdigit():
            lead=lead*10+int(fmt[i]); i+=1
        if i>=n: break
        c=fmt[i]
        if c=='Z':
            e=buf.find(b'\x00', p)
            if e<0: e=len(buf)
            vals.append(buf[p:e]); p=e+1; i+=2 if (i+1<n and fmt[i+1]=='*') else 1
            continue
        if c=='x':
            i+=1; trail=0
            while i<n and fmt[i].isdigit():
                trail=trail*10+int(fmt[i]); i+=1
            p+=(trail if trail else (lead if lead else 1)); continue
        letter=c; i+=1; mod=''
        if i<n and fmt[i]=='<':
            mod='<'; i+=1
        trail=0
        while i<n and fmt[i].isdigit():
            trail=trail*10+int(fmt[i]); i+=1
        cnt=trail if trail else (lead if lead else 1)
        for _ in range(cnt):
            if letter=='s': v=struct.unpack_from('<h', buf, p)[0]; p+=2
            elif letter=='S': v=struct.unpack_from('<H', buf, p)[0]; p+=2
            elif letter=='i': v=struct.unpack_from('<i', buf, p)[0]; p+=4
            elif letter=='C': v=buf[p]; p+=1
            elif letter=='c': v=struct.unpack_from('<b', buf, p)[0]; p+=1
            else: raise ValueError('bad fmt '+letter)
            vals.append(v)
    return vals, p

def sub01(buf, off):
    return read_params('Cs<', buf, off)
def opt02(buf, off):
    count=struct.unpack_from('<H', buf, off)[0]; p=off+2; out=[count]
    for _ in range(count):
        v,p=read_params('s<Z*CS<CZ*', buf, p); out.extend(v)
    return out, p
def sub03(buf, off):
    return read_params('CS<Cs<', buf, off)
def sub4a(buf, off):
    return read_params('Cs<2i<s<', buf, off)
POST={'sub01':sub01,'opt02':opt02,'sub03':sub03,'sub4a':sub4a}

CTRL=re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
BSL=re.compile(r'\\[A-Za-z]')   # backslash + letter control token (e.g. \n \c)
import unicodedata
# 半角假名(U+FF66-FF9F) 是前导字节 0x82/0x83 丢失后的残段，NFKC 还原为全角（确定性映射，非猜测）。
# 私用区 PUA(U+E000-F8FF) 为未映射字形槽，按铁律移除（记入报告）。
PUA=re.compile(r'[\uE000-\uF8FF]')
# WillPlus 振假名标记 {漢字:よみ} —— `：`是注音分隔符，渲染期注音，非正文 ⇒ 仅保留汉字本体
RUBY=re.compile(r'\{([^{}:：]*)[：:][^{}]*\}')

def clean(s):
    s=s.replace('\r',' ').replace('\n',' ')
    s=CTRL.sub(' ', s)
    s=BSL.sub(' ', s)
    s=re.sub(r'\s+',' ', s).strip()
    return s

def fix_chars(s):
    s=RUBY.sub(r'\1', s)             # 剥除振假名标记，保留汉字本体
    out=[]
    for c in s:
        o=ord(c)
        if 0xFF66<=o<=0xFF9F:        # 半角仮名 → 全角（NFKC 确定性还原）
            out.append(unicodedata.normalize('NFKC', c))
        else:
            out.append(c)
    s=''.join(out)
    s=PUA.sub('', s)                  # 移除未映射字形槽
    return s

def disassemble(scr):
    off=0; n=len(scr)
    while off < n:
        op=scr[off]
        if op not in RIO:
            z=scr.find(b'\x00', off)
            if z<0: z=n
            yield (off,'INVALID',list(scr[off:z])); off=z+1; continue
        fmt=RIO[op]; base=off+1
        if fmt[0] is None:
            yield (off, fmt[1] if len(fmt)>1 else op, []); off=base; continue
        if len(fmt)>2 and fmt[2] in POST:
            params,base=POST[fmt[2]](scr, base)
            yield (off, fmt[1] if len(fmt)>1 else op, params); off=base; continue
        params,base=read_params(fmt[0], scr, base)
        name=fmt[1] if len(fmt)>1 else op
        if not (fmt[0].endswith('Z*') or op==0x02):
            if base<n and scr[base]==0: base+=1
        yield (off,name,params); off=base

def extract_boxes(scr):
    boxes=[]; prev=None
    for off,name,params in disassemble(scr):
        if name=='text_n':
            t=fix_chars(clean(params[1].decode('cp932','replace'))); boxes.append(('', t)); prev=len(boxes)-1
        elif name=='text_c':
            # params[1]=名字窗（独立名字窗 ⇒ 剔除）；params[2]=台词正文
            t=fix_chars(clean(params[2].decode('cp932','replace')))
            if t:
                boxes.append(('', t)); prev=len(boxes)-1
        elif name=='text_extend':
            t=fix_chars(clean(params[-1].decode('cp932','replace')))
            if boxes: boxes[prev]=('', boxes[prev][1]+t)
            else: boxes.append(('', t))
    return boxes

def parse_will_arc(data):
    ntypes=struct.unpack_from('<I', data, 0)[0]
    p=4; types=[]
    for _ in range(ntypes):
        nm=data[p:p+4].split(b'\0')[0].decode('ascii','replace')
        sz=struct.unpack_from('<I',data,p+4)[0]; ofs=struct.unpack_from('<I',data,p+8)[0]
        types.append((nm,sz,ofs)); p+=12
    objs=[]
    for i in range(types[0][1]):
        b=types[0][2]+i*17
        nm=data[b:b+9].split(b'\0')[0].decode('ascii','replace')
        sz=struct.unpack_from('<I',data,b+9)[0]; ofs=struct.unpack_from('<I',data,b+13)[0]
        objs.append((nm,ofs,sz))
    return objs

def name_key(nm):
    parts=nm.split('_')
    try:
        return (int(parts[0]), int(parts[1]) if len(parts)>1 else 0)
    except: return (9999,0)

if __name__=='__main__':
    import sys
    rio=glob.glob('_work_ll/iso/Rio.arc')
    if not rio: rio=glob.glob('**/Rio.arc', recursive=True)
    data=open(rio[0],'rb').read()
    objs=parse_will_arc(data)
    kana=re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
    out=[]
    for nm,ofs,sz in sorted(objs, key=lambda o: name_key(o[0])):
        if sz<50: continue
        raw=data[ofs:ofs+sz]
        deb=bytes(((b>>2)|(b<<6))&0xff for b in raw)  # ROR2 deobfuscate
        try:
            boxes=extract_boxes(deb)
        except Exception:
            continue
        for _,t in boxes:
            if kana.search(t):
                out.append(t)
    out=[l for l in out if l.strip()]
    # de-dup exact adjacent duplicates only (keep intentional repeats elsewhere)
    txt='\n'.join(out)
    path='提取结果/[JP]Laughter Land.txt'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'w',encoding='utf-8',newline='\n') as f:
        f.write('\ufeff'+txt+'\n')
    print("WROTE",path,"lines",len(out))
