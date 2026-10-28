# -*- coding: utf-8 -*-
"""クローバー図書館の住人たちⅡ (PC-JP / System-NNN「NNNLib」) 全文本提取

链路：ISO(UDF2.00) → Inno Setup 5.5.0 分卷(setup-1/2.bin) → app/spt/*.spt
.spt = 整文件逐字节 XOR 0xFF；解密后 0x00 u32=0x20、0x30 = "SPTHEADER0"
头 0x10..0x30 = 4×(u32 count + u32 base)：
  组1 (count1,base1) = 消息池（正文/名札）
  组2 (count2,base2) = 選択肢・演出池（%質問行 / 選択肢 / 分岐ラベル / 資源名）
  组3 (count3,base3) = 小表（文字列不使用）、组4 = 2 项常量
  表首值 = base+count（逻辑地址），全文件唯一且表严格递增 ⇒ 据此定位地址表
  池起点 = 表起点 + count*4；记录 = [串][NUL][垃圾填充至 4 字节网格]

成行：一条消息记录 = 一次点击（框内 \r\n 为软换行 → 合并）
  `<名札>\r\n<正文>`：本作有独立名字窗（init2/messageWindow.fxf: nameWindowFlag 1 +
  filenameNameWindow*/namePrintY 370，正文区 printY 437）⇒ 名札行丢弃，不加前缀
  正文内联：`#名`=主人公名(千紘) / `#［N読み］`=注音(剔)

用法：
  python scripts/cloverlib2_extract.py            # 统计
  python scripts/cloverlib2_extract.py --dump     # 导出选项群供人工核对
  python scripts/cloverlib2_extract.py --build    # 生成成品
"""
import struct, os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_src_cloverlib2/app/app/spt')
WORK = os.path.join(VNTRANS_HOME, '_work_cloverlib2')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]クローバー図書館の住人たちII.txt')

# project.xtx 加载序（引擎脚本配置）→ 输出顺序
# 不收：sys(系统菜单) / tosho2_backscript(omake 背景演出，仅标签与资源名) / omake2(空)
ORDER = ['kyoutuu_2_1', 'kyoutuu_2_2', 'map',
         'route_1', 'route_2', 'route_3', 'route_6', 'route_4', 'route_5',
         'quiz']

PROTAG = '千紘'      # game.fxf defaultNameMei
SEI = '相川'         # game.fxf defaultNameSei

RUBY = re.compile(r'#［[^］]*］')      # #［２むげ］= 注音（前置字数+读法）
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# 池2 的分歧ラベル（非上屏）：节点标题 / 边注 / 资源名
LABEL_RE = re.compile(r'^[★☆■□◆◇①②③④⑤⑥⑦⑧⑨⑩]'
                      r'|^[０-９]+階'
                      r'|^シーン'
                      r'|ルート'
                      r'|^共通'
                      r'|ＴＲＵＥ|ＢＡＤ'
                      r'|^[\x20-\x7e]+$')
LABELS = {
    'オープニング', 'エンディング', 'スタッフロール', '音楽停止', '個別ルート分岐',
    '地下', '開かずの間', '場所移動メイン', 'シナリオ', '序章', 'クイズ説明',
    'マップ表示キャラフラグ・朝', 'マップ表示キャラフラグ・朝サブ',
    'マップ表示キャラフラグ・夜', 'マップ表示キャラフラグ・夜サブ',
}
MAX_OPT = 5          # 選択肢窗口 4 行 + 滚动（selectmessage.fxf: useScrollFlag 1）


def load(slug):
    return bytes(b ^ 0xFF for b in open(os.path.join(SRC, slug + '.spt'), 'rb').read())


def find_table(d, c, b):
    """表首值 = base+count；候选须 4 字节对齐、整表严格递增。"""
    pat = struct.pack('<I', b + c)
    i = d.find(pat)
    while i >= 0:
        if i % 4 == 0 and i + 4 * c <= len(d):
            vals = [struct.unpack_from('<I', d, i + 4 * k)[0] for k in range(c)]
            if all(vals[k] < vals[k + 1] for k in range(c - 1)):
                return i
        i = d.find(pat, i + 1)
    raise RuntimeError('addr table not found c=%d base=%d' % (c, b))


def pools(d):
    c1, b1, c2, b2 = struct.unpack_from('<4I', d, 0x10)
    out = []
    for c, b in ((c1, b1), (c2, b2)):
        if c == 0:
            out.append([])
            continue
        p = find_table(d, c, b) + 4 * c
        o, rec = p, []
        while o < len(d) and len(rec) < c:
            j = o
            while j < len(d) and d[j] != 0:
                j += 1
            if j >= len(d):
                break
            rec.append(d[o:j].decode('cp932', 'replace'))
            o = ((j + 1 + 3) // 4) * 4
        assert len(rec) == c, (c, len(rec))
        out.append(rec)
    return out


def plates():
    s = []
    for l in open(os.path.join(SRC, 'namecol.xtx'), 'rb').read().decode('cp932').splitlines():
        v = l.split(' ')[0].strip()
        if v and v not in ('#名', PROTAG):
            s.append(v)
    s += ['#名', '？？？']
    return sorted(set(s), key=len, reverse=True)


def clean(body):
    body = RUBY.sub('', body)
    body = body.replace('#姓', SEI).replace('#名', PROTAG)   # 名字宏（可改名主角）
    body = body.replace('\r\n\u3000', '').replace('\r\n', '')
    return body.strip()


def to_line(raw, PL):
    if '\r\n' in raw:
        seg0, rest = raw.split('\r\n', 1)
        if RUBY.sub('', seg0).strip() in PL:
            return clean(rest)
    return clean(raw)


def msg_lines(p1, PL):
    out = []
    for raw in p1:
        s = to_line(raw, PL)
        if not s:
            continue
        if not JP.search(s) and s[0] not in '「『（':
            continue
        out.append(s)
    return out


def choice_groups(p2):
    gs, i, n = [], 0, len(p2)
    while i < n:
        if p2[i].startswith('%'):
            j = i
            while j < n and p2[j].startswith('%'):
                j += 1
            q = ''.join(re.sub(r'^%#?', '', p2[k]).strip() for k in range(i, j))
            k, opts = j, []
            while k < n and len(opts) < MAX_OPT:
                t = p2[k]
                if t.startswith('%') or LABEL_RE.search(t) or t in LABELS:
                    break
                opts.append(t)
                k += 1
            gs.append((q, opts))
            i = k
        else:
            i += 1
    return gs


def main():
    PL = plates()
    dump = '--dump' in sys.argv
    build = '--build' in sys.argv
    out_lines, stat = [], []
    for slug in ORDER:
        p1, p2 = pools(load(slug))
        lines = msg_lines(p1, PL)
        gs = choice_groups(p2)
        out_lines += lines
        for q, opts in gs:
            if q:
                out_lines.append(q)
            out_lines += opts
        stat.append((slug, len(p1), len(lines), len(gs), sum(len(o) for _, o in gs)))
        if dump:
            os.makedirs(WORK, exist_ok=True)
            with open(os.path.join(WORK, 'choice_dump.txt'), 'a', encoding='utf-8') as f:
                f.write('===== %s\n' % slug)
                for q, o in gs:
                    f.write('Q: %s\n' % q)
                    for x in o:
                        f.write('   O: %s\n' % x)
    for s in stat:
        print('%-14s msg=%4d line=%4d groups=%3d opts=%4d' % s)
    print('TOTAL lines', len(out_lines))
    if build:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(out_lines) + '\n')
        print('->', OUT)


if __name__ == '__main__':
    main()
