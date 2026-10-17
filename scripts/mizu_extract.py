#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""水の旋律 (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本
用法: python scripts/mizu_extract.py <GAMEDATA.DAT> <out.txt> [--stat]
结构: THFS 头 0x18 + 条目 64B (name32 + pad8 + off u32 + size u32 + z u32 + size u32 + hash8)
脚本: 0x20 头 + 指令流; 文本串 = cp932 + NUL; 页尾控制 %K%P(普通) / %K%p(选项前)
"""
import struct, re, sys, os, collections

TXT_CTRL = re.compile(r'%[A-Za-z](?:[A-Za-z]|[0-9]{0,3})')
JPCHAR = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
HIRA = re.compile(r'[\u3041-\u309f]')
HALFKANA = re.compile(r'[\uff66-\uff9f]')
ASCII2 = re.compile(r'[A-Za-z0-9]{2,}')
# 正文起始字符：名札/引号/括号/汉字/假名
OKSTART = re.compile(r'^[\u3005\u3007\u3041-\u309f\u30a0-\u30ff\u4e00-\u9fff【「『（〈《〔\[＊☆♪―－〜'
                     r'\uff10-\uff19\uff21-\uff3a\uff41-\uff5a]')
NAME = re.compile(r'^【[^】]{1,20}】')
# 系统 / UI / 遗留脚本：不收
EXCLUDE = ('SHORTCUT', 'DATA', 'MAIN', 'DMENU', 'DBG', 'INIT', 'JIS2UCS', 'SYS')


def thfs_entries(path):
    d = open(path, 'rb').read()
    magic, total, count, _ = struct.unpack_from('<4sIII', d, 0)
    assert magic == b'THFS', magic
    ents = []
    for i in range(count):
        o = 0x18 + i * 64
        nm = d[o:o+32].split(b'\0')[0].decode('cp932', 'replace')
        off, sz, _z, sz3 = struct.unpack_from('<IIII', d, o + 40)
        ents.append((nm, off, sz))
    return d, ents


def dec_ok(seg):
    """cp932 完整性检查（不含 NUL / 控制字节 / 半角假名之外的可疑字节）"""
    i, n = 0, len(seg)
    while i < n:
        c = seg[i]
        if c < 0x20 or c == 0x7f:
            return False
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            if i + 1 >= n:
                return False
            s = seg[i+1]
            if not (0x40 <= s <= 0x7e or 0x80 <= s <= 0xfc):
                return False
            i += 2
        elif c < 0x80 or 0xa1 <= c <= 0xdf:
            i += 1
        else:
            return False
    return True


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def clean(t):
    t = TXT_CTRL.sub('', t)          # %K %P %N %W %O060 %FS ...
    t = t.replace('\r', '').replace('\n', '')
    t = NAME.sub('', t)              # 名札剥除（不加说话人前缀）
    return t.strip(' \u3000')


def core_of(s):
    """剥掉开头的连续控制码（%S020%LC%FS...），返回正文部分"""
    m = re.match(r'^(?:%[A-Za-z](?:[A-Za-z]|[0-9]{0,3}))+', s)
    return s[m.end():] if m else s


def is_ctrl_only(s):
    return re.fullmatch(r'(?:%[A-Za-z](?:[A-Za-z]|[0-9]{0,3}))+', s) is not None


def is_text_seg(s, opt=False, loose=False):
    """正文段判定（s 已剥前导控制码）
    loose=True：自带页尾(%P/%p)或特效尾(%O)⇒ 本身就是「上屏」信号，放宽
    opt=True  ：选项区，允许短句 / 无平假名的地名"""
    if not s or not JPCHAR.search(s):
        return False
    if HALFKANA.search(s):          # 半角假名＝化け信号（本作正文不用半角假名）
        return False
    if s[0].isascii():              # ASCII 起始＝命令残余
        return False
    if ASCII2.search(s) and not HIRA.search(s):   # 混入成串 ASCII＝化け
        return False
    if opt or loose:
        return True
    if HIRA.search(s):              # 含平假名＝正文强信号
        return True
    # 无平假名：须含日文标点（…… 开头的台词）
    return len(s) >= 2 and bool(re.search(r'[…‥「」『』、。！？・]', s))


def extract_file(b):
    """返回 [(kind, text)]，kind: body / option / effect"""
    out = []
    pending = []          # 本页待合并的文本段
    opt_mode = False      # 上一控制段是否为 %p（选项前）

    def flush(kind):
        nonlocal pending
        if pending:
            txt = ''.join(clean(x) for x in pending)
            pending = []
            if txt:
                out.append((kind, txt))

    segs = []
    st = 0
    for i, c in enumerate(b):
        if c == 0:
            segs.append(b[st:i])
            st = i + 1
    for seg in segs:
        if not seg:
            continue
        try:
            s = seg.decode('cp932')
        except UnicodeDecodeError:
            s = None
        if s is None or not dec_ok(seg):
            flush('option' if opt_mode else 'body')
            opt_mode = False
            continue
        core = core_of(s)
        if not core:                       # 纯控制段
            if ('%P' in s or '%p' in s) and pending:
                flush('option' if opt_mode else 'body')
            if '%p' in s:
                opt_mode = True
            elif '%P' in s:
                opt_mode = False
            continue
        has_p = core.rstrip().endswith(('%P', '%p'))
        eff = re.sub(r'%O\d*$', '', core)
        is_eff = (eff != core) and bool(eff)
        if has_p:
            flush('option' if opt_mode else 'body')
            if is_text_seg(eff if is_eff else core, loose=True):
                txt = clean(s)
                if txt:
                    out.append(('body', txt))
            opt_mode = core.rstrip().endswith('%p')
        elif is_eff:
            flush('option' if opt_mode else 'body')
            # 特效串须够长且含成串日文（排除「1%O」这类索引表记录）
            if len(eff) >= 4 and re.search(r'[\u3041-\u30ff\u4e00-\u9fff]{2,}', eff) \
                    and is_text_seg(eff, loose=True):
                txt = clean(s)
                if txt:
                    out.append(('effect', txt))
            opt_mode = False
        elif opt_mode:
            if is_text_seg(core, opt=True):
                txt = clean(s)
                if txt:
                    out.append(('option', txt))
        elif is_text_seg(core):
            pending.append(s)
        else:
            flush('option' if opt_mode else 'body')
            opt_mode = False
    flush('option' if opt_mode else 'body')
    return out


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    d, ents = thfs_entries(src)
    files = [(n, o, s) for n, o, s in ents
             if n.upper().endswith('.BIN') and not any(n.upper().startswith(e) for e in EXCLUDE)]
    files.sort(key=lambda x: natkey(x[0]))
    lines = []
    stat = collections.Counter()
    for nm, off, sz in files:
        items = extract_file(d[off:off+sz])
        for kind, t in items:
            stat[kind] += 1
            lines.append(t)
    print('文件 %d / 条目 %d / %s' % (len(files), len(lines), dict(stat)))
    if dst:
        with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('写出 %s' % dst)


if __name__ == '__main__':
    main()
