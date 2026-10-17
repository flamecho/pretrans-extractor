#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学園K -Wonderful School Days- V Edition  (PSV, PCSG00654, Otomate / Idea Factory)

容器链
------
  NoNpDrm zip
    -> psvpfsparser -i <PCSG00654> -o dec -z <zRIF> -f cma.henkaku.xyz   (PFS 解密)
    -> Data/DATA.PAK   串联 1719 个「单文件 zip」, 每块 512 字节对齐
    -> Data/CORE.DAT   同样是一个 zip (内 CORE.DAT_)
    -> 内层 `DAT ` 归档:  [u32 count] + count × (name[0x20] + u32 size + u32 offset) + 数据区
    -> *.SCD 剧本 / *.gxt 贴图 / *.LIP 口型 / *.BIN 表

SCD 字符串记录 (UTF-8):  <u16 len> <len bytes>
  旁白   :  fe ff 00 XX 02 00 2d 31 02 00 25 26  <u16 len> <text>
  会話   :  0f 00 00 00  <u16 len> char_id("ddd_ddd_ddd")  <u16 len> name  <u16 len> text
  選択肢 :  61 00 14 00  <u32 scene_id> <u32 idx> <u32> <u32> <u32>   -> CHOICE.BIN 的 (scene_id, idx) 块
  * 名札(char_id 之后紧跟的短串) 丢弃; `$...$` = 用語辞典词条标记; `\\` = 框内软换行;
    `%` = 主角姓, `&` = 主角名, `%&` = 主角全名 (玩家可改名)。

CHOICE.BIN: [u32 n_blocks] + n_blocks ×
            [u32 size][u32 scene_id][u32 idx][u32 n_opts][s32 -1][pad]
            [n_opts × (u32 len + utf8, 4 字节对齐)]
DICT.BIN  : [u32 n] + n × [u32 size][u32 idx][u32 ?][u32 title_len][title]
            [u32 n_lines][n_lines × (u32 len + utf8, 4 字节对齐)]

用法
----
  python scripts/gakuenk_extract.py \
      --pak _dec_gakuenk/Data/DATA.PAK --core _dec_gakuenk/Data/CORE.DAT \
      --out "提取结果/[PSV-JP]学園K -Wonderful School Days- V Edition_全文本.txt" \
      --family 木野花 --given 沙耶
"""
import struct, zlib, sys, os, re, argparse

JP = re.compile('[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff01-\uff60\uff9e\uff9f]')
IDRE = re.compile(r'^[0-9]{3}_[0-9]{3}_[0-9]{3}$')


# ------------------------------------------------------------------ 容器

def _iter_single_zips(d):
    """DATA.PAK = 串联的单文件 zip；CORE.DAT = 单个 zip。通用顺序扫描。"""
    i, n = 0, len(d)
    while True:
        i = d.find(b'PK\x03\x04', i)
        if i < 0:
            return
        (ver, flag, method, mt, md, crc, csz, usz, nl, el) = struct.unpack('<HHHHHIIIHH', d[i+4:i+30])
        nm = d[i+30:i+30+nl]
        if (0 < nl < 64 and method == 8 and csz > 0 and all(32 <= c < 127 for c in nm)
                and d[i+30+nl+el+csz:i+30+nl+el+csz+4] == b'PK\x01\x02'):
            try:
                yield nm.decode('latin1'), zlib.decompress(d[i+30+nl+el:i+30+nl+el+csz], -15)
            except Exception:
                pass
        i += 4


def dat_entries(blob):
    """内层 `DAT ` 归档 -> [(name, bytes)]"""
    if blob[:4] != b'DAT ':
        return []
    cnt = struct.unpack('<I', blob[4:8])[0]
    out = []
    for k in range(cnt):
        o = 8 + k * 0x28
        if o + 0x28 > len(blob):
            break
        nm = blob[o:o+0x20].split(b'\0')[0].decode('latin1')
        sz, off = struct.unpack('<II', blob[o+0x20:o+0x28])
        if off + sz <= len(blob):
            out.append((nm, blob[off:off+sz]))
    return out


def game_files(pak_path, core_path):
    scds = []
    for _, blob in _iter_single_zips(open(pak_path, 'rb').read()):
        for iname, sub in dat_entries(blob):
            if iname.endswith('.SCD'):
                scds.append((iname, sub))
    scds.sort(key=lambda t: t[0])
    core = {}
    for _, blob in _iter_single_zips(open(core_path, 'rb').read()):
        for nm, sub in dat_entries(blob):
            core.setdefault(nm, sub)
    return scds, core


# ------------------------------------------------------------------ 表

def parse_choices(blob):
    """CHOICE.BIN -> {(scene_id, idx): [option, ...]}"""
    out = {}
    n = struct.unpack('<I', blob[:4])[0]
    pos = 4
    for _ in range(n):
        if pos + 20 > len(blob):
            break
        size, sid, idx, nopt, _m1 = struct.unpack('<IIIIi', blob[pos:pos+20])
        p, end, opts = pos + 20, min(pos + max(size, 20), len(blob)), []
        while p + 4 <= end and len(opts) < nopt:
            L = struct.unpack('<I', blob[p:p+4])[0]
            if not (0 < L <= 4000) or p + 4 + L > end:
                p += 4
                continue
            try:
                opts.append(blob[p+4:p+4+L].decode('utf-8').rstrip('\0'))
            except UnicodeDecodeError:
                p += 4
                continue
            p += 4 + L
            while p % 4:
                p += 1
        out[(sid, idx)] = opts
        if size < 20:
            break
        pos += size
    return out


def parse_dict(blob):
    """DICT.BIN -> [(title, body)]，正文按行槽拼接"""
    n = struct.unpack('<I', blob[:4])[0]
    pos, out = 4, []
    for _ in range(n):
        if pos + 16 > len(blob):
            break
        size, idx, _z, tl = struct.unpack('<IIII', blob[pos:pos+16])
        p = pos + 16
        title = blob[p:p+tl].rstrip(b'\0').decode('utf-8', 'replace')
        p += tl
        nl = struct.unpack('<I', blob[p:p+4])[0]
        p += 4
        parts = []
        for _l in range(nl):
            L = struct.unpack('<I', blob[p:p+4])[0]
            p += 4
            parts.append(blob[p:p+L].rstrip(b'\0').decode('utf-8', 'replace'))
            p += L
        out.append((title, ''.join(parts)))
        if size < 16:
            break
        pos += size
    return out


# ------------------------------------------------------------------ SCD

def scan_strings(b, minlen=2, maxlen=6000):
    """<u16 len><utf8> 记录 -> [(start, text)]，顺序、不重叠"""
    res, i, n = [], 0, len(b)
    while i + 4 < n:
        L = b[i] | (b[i+1] << 8)
        if minlen <= L <= maxlen and i + 2 + L <= n:
            try:
                s = b[i+2:i+2+L].decode('utf-8')
            except UnicodeDecodeError:
                i += 1
                continue
            s = s.rstrip('\0')
            if s and not any(ord(c) < 0x20 and c not in '\n\t' for c in s):
                res.append((i, s))
                i += 2 + L
                while i < n and b[i] == 0:
                    i += 1
                continue
        i += 1
    return res


def scan_choices(b):
    """61 00 14 00 <u32 scene_id> <u32 idx> -> [(offset, scene_id, idx)]"""
    res, i, n = [], 0, len(b)
    while i + 24 <= n:
        if b[i] == 0x61 and b[i+1] == 0x00 and b[i+2] == 0x14 and b[i+3] == 0x00:
            sid, idx = struct.unpack('<II', b[i+4:i+12])
            res.append((i, sid, idx))
            i += 24
            continue
        i += 1
    return res


def scd_items(blob, choices):
    """按偏移合并正文 / 选项 / 名札 -> [(kind, text)]，kind ∈ text|opt|name"""
    ev = [('text', o, s) for o, s in scan_strings(blob)]
    for o, sid, idx in scan_choices(blob):
        if (sid, idx) in choices:
            ev.append(('opt', o, list(choices[(sid, idx)])))
    ev.sort(key=lambda t: t[1])
    items, prev_id = [], False
    for kind, _o, payload in ev:
        if kind == 'opt':
            items.append(('opt', payload))
            prev_id = False
            continue
        if IDRE.match(payload):
            prev_id = True
            continue
        if not JP.search(payload):
            prev_id = False
            continue
        if prev_id and len(payload) <= 12:      # 名札 -> 丢
            prev_id = False
            continue
        items.append(('text', payload))
        prev_id = False
    return items


# ------------------------------------------------------------------ 清洗

def clean(s, fam, giv):
    s = s.replace('%&', fam + giv)     # 主角全名
    s = s.replace('%', fam)            # 姓
    s = s.replace('&', giv)            # 名
    s = s.replace('$', '')             # 用語辞典词条标记
    s = s.replace('\\', '')            # 框内软换行 -> 合并
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pak', default='_dec_gakuenk/Data/DATA.PAK')
    ap.add_argument('--core', default='_dec_gakuenk/Data/CORE.DAT')
    ap.add_argument('--out', default='提取结果/[PSV-JP]学園K_全文本.txt')
    ap.add_argument('--family', default='木野花')
    ap.add_argument('--given', default='沙耶')
    ap.add_argument('--no-dict', action='store_true')
    args = ap.parse_args()

    scds, core = game_files(args.pak, args.core)
    choices = parse_choices(core['CHOICE.BIN']) if 'CHOICE.BIN' in core else {}
    print(f'SCD={len(scds)}  選択肢ブロック={len(choices)}', file=sys.stderr)

    per_file, matched, n_opt = {}, set(), 0
    for iname, blob in scds:
        ls = []
        for kind, txt in scd_items(blob, choices):
            if kind == 'opt':
                for o in txt:
                    ls.append(clean(o, args.family, args.given))
                    n_opt += 1
            else:
                ls.append(clean(txt, args.family, args.given))
        per_file[iname] = ls
        for _o, sid, idx in scan_choices(blob):
            matched.add((sid, idx))

    unmatched = [k for k in choices if k not in matched]
    placed = []
    for sid, idx in unmatched:
        fname = str(sid).zfill(7) + '.SCD'
        if fname in per_file:
            for o in choices[(sid, idx)]:
                per_file[fname].append(clean(o, args.family, args.given))
                n_opt += 1
            placed.append((sid, idx))

    lines = []
    for iname, _blob in scds:
        lines.extend(per_file[iname])
    lines = [l for l in lines if l != '']        # 规范：不留空行
    n_text = len(lines) - n_opt

    if not args.no_dict and 'DICT.BIN' in core:
        for title, body in parse_dict(core['DICT.BIN']):
            lines.append(f'【{clean(title, args.family, args.given)}】{clean(body, args.family, args.given)}')

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'正文行={n_text}  选项行={n_opt}  合计={len(lines)}', file=sys.stderr)
    print(f'选项块 内联命中 {len(matched)}/{len(choices)}; 置场景末 {len(placed)}; '
          f'仍未定位 {[k for k in unmatched if k not in placed]}', file=sys.stderr)
    print('wrote', args.out, file=sys.stderr)


if __name__ == '__main__':
    main()
