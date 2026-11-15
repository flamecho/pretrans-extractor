# -*- coding: utf-8 -*-
"""[JP]Petit Fleur -丘を渡るクリスタルの風-  (Macromedia Director 10.1 / RIFX, zlib 分块)
文本提取器 v5 (最终, 长度前缀法)

容器: Ritz.exe 投影器 → 自解压 RAR5 → data/*.dcr(FGDM movie) / *.cct(FGDC cast)
文本在「文本 cast 成员」的 XMED 文本块里，二进制结构为:
  ... 0002 <len8hex> <flags8hex> 00  <id>,<seg1>\r<seg2>\r  <结构...>
  - 0002            : Director 文本块标记
  - len8hex         : 文本字段长度(含末尾少量结构字节)
  - flags8hex       : 标志位
  - 00              : 分隔字节
  - <id>            : 1~4 位十六进制（成员/行号）
  - <seg1>          : 说话人（印在文本框内）或空
  - <seg2>          : 正文；框内 \r 为换行→合并不拆
  - 字段以 0x00 / 0x03 / "000X"(X∈1-9/A-F) 等结构字节收尾

抽取判据（结构级，完全依赖长度前缀，杜绝二进制误抓）:
  1) 全文扫 zlib 流解压
  2) 定位 0002+16hex 锚点 → 读 len 字节 → 必以 <id>, 开头，否则跳过(二进制噪声)
  3) 剥领先 0x00 / <id>, ；内容首字节<0x20 → 字体/模板字段，跳过
  4) 内容遇 0x00 / 0x03 / "000X" 截断（结构字节）
  5) 解码 cp932；框内 \r/\n 合并
用法:
  python petitfleur_text.py <data_dir> [--out <combined.txt>]
  python petitfleur_text.py <file.dcr/.cct> [--print]
"""
import sys, os, re, zlib

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
IDB = re.compile(rb'^[0-9A-Fa-f]+,')
ANCH = re.compile(rb'0002([0-9A-Fa-f]{16})')
TEMPLATE = ('本文テキスト',)


def streams(data):
    out = []
    n = len(data); p = 0
    while p < n - 1:
        if data[p] == 0x78 and data[p+1] in (0x01, 0x9c, 0xda):
            try:
                do = zlib.decompressobj()
                o = do.decompress(data[p:])
                if len(o) > 50:
                    out.append(o)
                rem = do.unused_data
                if not rem:
                    break
                p = n - len(rem)
                continue
            except Exception:
                pass
        p += 1
    return out


def trim(content):
    cut = len(content)
    for i, b in enumerate(content):
        if b == 0x00 or b == 0x03:
            cut = i; break
        if b == 0x30 and i + 2 < len(content) and content[i+1] == 0x30 and content[i+2] == 0x30:
            nxt = content[i+3] if i+3 < len(content) else 0
            if (0x31 <= nxt <= 0x39) or (0x41 <= nxt <= 0x46):
                cut = i; break
    return content[:cut]


def texts_from(s):
    out = []
    for m in ANCH.finditer(s):
        length = int(m.group(1)[:8], 16)
        if not (2 <= length <= 6000):
            continue
        ts = m.start() + 21
        raw = s[ts:ts + length]
        while raw and raw[0] == 0x00:
            raw = raw[1:]
        if len(raw) < 2:
            continue
        if not IDB.match(raw):
            continue
        content = IDB.sub(b'', raw, count=1)
        if content[:1] < b'\x20':
            continue
        content = trim(content)
        t = content.decode('cp932', 'replace').replace('\ufffd', '').strip('\r\n').strip()
        if not t or not JP.search(t):
            continue
        t = t.replace('\r', '').replace('\n', '')
        if TEMPLATE[0] in t:
            continue
        out.append(t)
    return out


def sort_key(name):
    base = name.lower()
    digits = re.findall(r'\d+', base)
    if digits:
        return (0, [int(d) for d in digits], base)
    return (1, [], base)


def main():
    args = sys.argv[1:]
    src = args[0]
    outpath = args[args.index('--out') + 1] if '--out' in args else None
    if os.path.isdir(src):
        files = [f for f in sorted(os.listdir(src)) if f.lower().endswith(('.dcr', '.cct'))]
        ordered = sorted(files, key=sort_key)
        os.makedirs('out', exist_ok=True)
        combined = []; seen = set(); total = 0
        for f in ordered:
            d = open(os.path.join(src, f), 'rb').read()
            fseen = set()
            for st in streams(d):
                for t in texts_from(st):
                    fseen.add(t)
            open(os.path.join('out', f + '.txt'), 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(sorted(fseen)) + '\n')
            for t in sorted(fseen):
                if t not in seen:
                    seen.add(t); combined.append(t)
            total += len(fseen)
            print(f'{f}: {len(fseen)}')
        if outpath:
            open(outpath, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(combined) + '\n')
            print('COMBINED ->', outpath)
        print('TOTAL(per-file):', total, ' UNIQUE(combined):', len(combined))
    else:
        d = open(src, 'rb').read()
        ls = []
        for st in streams(d):
            for t in texts_from(st):
                if t not in ls:
                    ls.append(t)
        if '--print' in args:
            for l in ls:
                print(l)
        else:
            print(f'{os.path.basename(src)}: {len(ls)}')
            for l in ls[:40]:
                print('  ', l[:70])


if __name__ == '__main__':
    main()
