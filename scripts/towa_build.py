# -*- coding: utf-8 -*-
"""悠久ノ桜（Towa no Sakura / PS2-JP）全文本生成

链路：ISO9660 → DATA/SYSTEM.VDP 的 SCRIPT 条目 → 500 个 *.LSB → 正文

LSB 结构（VSC 引擎）
  0x00 u32 fileSize / 0x04 u32 cmdCount / 0x0C u32 cmdTableOff(0x58)
  0x10 u32 bodyOff（命令表结束处，正文区起点）/ 0x18 场景名 cp932（不渲染）
  命令表：cmdCount × 8B [u16 op][u16 sub][u32 arg]
    op 0x1016 = 显示正文，arg 相对 (body+8) 指向记录的「名字域」
    op 0x1012 = 选项（cc 填充块）；op 0x1014 = 选项（无 cc 标记块）
  记录：[u32 样式][u32 语音 ID][名字域][正文\0]；名字域 = `26 00`（主角名宏）
        / `00`（无名）/ NUL 结尾名札串（偶有「！！」这类演出名）

正文内控制码：0x5C 同框软换行（合并）｜0x5C 0x5C 换页（清框，另起一行）
             0x26 主角名｜0x25 主角姓｜0x23 演出码（丢弃）
"""
import struct, sys, os, glob, re, hashlib, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import towa_extract as T

NAME, SUR = '鳴美', '時沢'      # 時沢 鳴美（vndb c47591 / v9912）；全库字面出现 0 次 ⇒ 只经宏插入
PAGE = '\x01'


def natkey(p):
    b = os.path.basename(p)
    return (0 if b.startswith('EV') else 1, [int(x) for x in re.findall(r'\d+', b)], b)


OPT_OK = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')


def opt_str(s):
    """选项串判定：含假名/汉字；排除半角片假名、PUA、ASCII 残渣（结构字节误读）"""
    return (len(s) >= 2 and bool(OPT_OK.search(s)) and T.valid(s)
            and not re.search('[\uff61-\uff9f]', s)
            and not re.search('[A-Za-z0-9]', s))


def read_block(d, st):
    """从 st 起读选项串（连续 NUL 结尾 cp932 串）"""
    out = []
    p = st
    while p < len(d):
        s, q = T.read_cstr(d, p, 200)
        if s is None or not opt_str(s):
            break
        out.append(s)
        p = q
    return out


def file_lines(path):
    d = open(path, 'rb').read()
    if len(d) < 0x30:
        return []
    body = struct.unpack('<I', d[0x10:0x14])[0]
    cnt = struct.unpack('<I', d[4:8])[0]
    base = body + 8
    recs = []
    for i in range(cnt):
        off = 0x58 + 8 * i
        if off + 8 > len(d):
            break
        op, sub, arg = struct.unpack_from('<HHI', d, off)
        if arg >= 0x100000:
            continue
        if op == 0x1016:
            r = T.parse_text(d, base + arg)
            if r:
                recs.append(('T', r[1]))
        elif op in (0x1012, 0x1014):
            # 选项块：arg 指向块前一拍，向后找第一串
            p = base + arg
            for k in range(0, 32):
                s, _q = T.read_cstr(d, p + k, 200)
                if s is not None and opt_str(s):
                    for t in read_block(d, p + k):
                        recs.append(('O', t))
                    break
    out = []
    for kind, tx in recs:
        tx = T.clean(tx, NAME, SUR)
        if not tx:
            continue
        for seg in tx.split(PAGE):
            if seg:
                out.append(seg)
    return out


def main(root, out, stat_path=None):
    files = sorted(glob.glob(os.path.join(root, '*.LSB')), key=natkey)
    lines, seen, dup, stat = [], {}, [], {}
    for f in files:
        got = file_lines(f)
        if not got:
            continue
        key = hashlib.md5('\n'.join(got).encode()).hexdigest()
        if key in seen:
            dup.append((os.path.basename(f), seen[key]))
            continue
        seen[key] = os.path.basename(f)
        lines.extend(got)
        stat[os.path.basename(f)] = len(got)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(lines) + '\n')
    print(f'文件 {len(stat)} / 折叠 {len(dup)} / 行 {len(lines)}')
    if stat_path:
        json.dump({'files': stat, 'collapsed': dup, 'lines': len(lines)},
                  open(stat_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
