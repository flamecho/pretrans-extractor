#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
オルフレール ～幸福の花束～ (PSV / PCSG00919, dramatic create「Orfre」/ DCVM)
文本提取器 —— 以 STBL（脚本发射序）为准 ⇒ 「一次点击 = 一行」

关键格式（详见 references/engines/orfre-dcvm.md）
  rom/script.rom : 1024B 页 -> 块头 12B[type] -> DCVM
  DCVM 段: DCVM > STOR > PTBL > PSTR > [VTBL] > FTBL > CODE > STR > STBL
  STR  = NUL 分隔字符串池（**分类排序存放**，池序 != 显示序）
  STBL = u32[size] + u32[count] + count×u32[offset]
         offset 以 **STR 段 tag 起点** 为基准
         字符串起点 = data[STR_off + 16 + offset]   (等价 strd[offset+8], strd=data[STR_off+8:])
         **STBL 顺序 == 脚本（显示）序**（562 块 122212/122212 映射成功）

显示文本判定（其余一律丢弃）：
  行首为 半角空格 / 全角空格 / 「 / （ / ― / 『   → 正文（旁白・对白・心声・扉文・信件）
  "\n" 连接串                              → 选项组（逐条成行）
  紧接 '選択肢' 后的同名串                   → 选项副本，丢弃
  丢弃：名字札（アデル 等）、资源路径（game/image/...）、语音（ad/ad1092）、
        BGM/SE、API 符号名、系统字符串（タイトルに戻りますか？ 等）、回想:XXX
"""
import os, sys, glob, re, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orfleur_extract as OE  # hankaku_to_hiragana / strip_tags / secs

# 行首允许字符：半角空格 / 全角空格 / 引号 / 括弧 / 破折号 / 双角引用
EMIT_HEADS = (' ', '\u3000', '「', '（', '―', '『')
JUNK_EXACT = ('*', '-t', '選択肢')


# ---------------------------------------------------------------- 读取/解包
def load_chunks(dec_dir):
    """rom/script.rom -> list[bytes|None]，索引＝块号"""
    return OE.parse_rom(os.path.join(dec_dir, 'rom', 'script.rom'))


def secs(b):
    """解析 DCVM 段表 -> {tag: (off, size)}，off 指向 tag 本身"""
    out = {}
    i = 0x10
    while i < len(b) - 8:
        tag = b[i:i + 4].decode('latin1').strip()
        sz = int.from_bytes(b[i + 4:i + 8], 'little')
        if sz < 8 or sz > len(b):
            break
        out[tag] = (i, sz)
        i += sz
    return out


def stbl_order(data):
    """返回 [pool_index,...]（按 STBL 顺序）。失败返回 None"""
    S = secs(data)
    if 'STR' not in S or 'STBL' not in S:
        return None
    so, ss = S['STR']
    strd = data[so + 8:so + ss]
    parts = strd.split(b'\0')
    starts = []
    acc = 0
    for p in parts:
        starts.append(acc)
        acc += len(p) + 1
    sidx = {}
    for i, s in enumerate(starts):
        sidx[s] = i
    to, ts = S['STBL']
    stb = data[to + 8:to + ts]
    cnt = int.from_bytes(stb[0:4], 'little')
    offs = [int.from_bytes(stb[4 + 4 * i:8 + 4 * i], 'little') for i in range(cnt)]
    return [sidx.get(o + 8) for o in offs], parts


def norm(b):
    """字节 -> 归一化文本（去标签 / 还原括号 / 半角假名→平假名）"""
    try:
        t = OE.strip_tags(b.decode('cp932'))
    except Exception:
        return None
    return OE.hankaku_to_hiragana(t)


# ---------------------------------------------------------------- 文本抽取
def extract_scene(data, pc_chapters=None, stats=None):
    """按 STBL 顺序抽取一「场景」的显示文本行"""
    r = stbl_order(data)
    if not r:
        return []
    seq, parts = r
    out = []
    pending_opts = []
    has_dash_title = False
    bare_title = None
    for k in seq:
        if k is None or not (0 <= k < len(parts)):
            continue
        t = norm(parts[k])
        if t is None:
            continue
        ts = t.strip()
        if not ts:
            continue

        # ---- 选项组（"\n" 连接）
        if '\n' in t and '/' not in ts:
            opts = [x.strip() for x in t.split('\n')]
            opts = [x for x in opts if x]
            if opts and all(re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', x) for x in opts):
                for x in opts:
                    out.append(x)
                pending_opts = list(opts)
                continue

        if ts in JUNK_EXACT:
            continue
        if pending_opts and ts == pending_opts[0]:
            pending_opts.pop(0)
            continue
        if pending_opts and ts not in pending_opts:
            pending_opts = []

        # ---- 行首判定
        if t[0] == '―' and ts.endswith('―') and len(ts) > 2:
            has_dash_title = True
        if pc_chapters and ts in pc_chapters:
            bare_title = ts
            continue                      # 裸章题＝元数据，不上屏
        if t[0] in EMIT_HEADS:
            line = t.lstrip(' \u3000').replace('\n', '')
            if re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', line):
                out.append(line)
            continue
        # 其余（名字札 / 资源 / 符号 / 系统串）丢弃
    if stats is not None:
        stats['has_dash_title'] = has_dash_title
        stats['bare_title'] = bare_title
    return out


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dec_dir')
    ap.add_argument('out', help='输出 全文本.txt')
    ap.add_argument('--chunk-txt', default=None, help='每场景 txt 输出目录')
    ap.add_argument('--script-list', default=None, help='chunk8 剧本名清单 json')
    args = ap.parse_args()

    chunks = load_chunks(args.dec_dir)
    print('chunks:', len(chunks))

    # 档案顺序：桩块 21..287 各含 1 条剧本名 ⇒ 即游戏流程序
    sp = re.compile(r'game/script/scenario/([A-Za-z0-9_\-]+)\.s')
    names = []
    for i in range(21, 288):
        c = chunks[i]
        full = c.decode('cp932', 'replace')
        m = sp.findall(full)
        names.append(m[0] if m else '?')
    print('scene count:', len(names))

    # PC 章题集（用于识别裸章题＝元数据）
    pc_chapters = set()
    pj = os.path.join(os.path.dirname(args.out), '..', '..', '_work_orfleur', 'pc_order.json')
    for cand in ('_work_orfleur/pc_order.json', '../../_work_orfleur/pc_order.json'):
        if os.path.exists(cand):
            pc = json.load(open(cand, encoding='utf-8'))
            pc_chapters = set(v['chapter'] for v in pc.values() if v.get('chapter'))
            break
    print('pc chapters:', len(pc_chapters))

    total = 0
    nscene = 0
    index = []
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    if args.chunk_txt:
        os.makedirs(args.chunk_txt, exist_ok=True)

    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as fp:
        for k, nm in enumerate(names):
            data = chunks[295 + k] if 295 + k < len(chunks) else None
            if not data or data[:4] != b'DCVM':
                continue
            st = {}
            lines = extract_scene(data, pc_chapters, st)
            if not lines:
                index.append((k, nm, st.get('bare_title') or '', 0))
                continue
            nscene += 1
            if args.chunk_txt:
                with open(os.path.join(args.chunk_txt, '%03d_%s.txt' % (k, nm)), 'w',
                          encoding='utf-8-sig', newline='\n') as cf:
                    for s in lines:
                        cf.write(s + '\n')
            for s in lines:
                fp.write(s + '\n')
            index.append((k, nm, st.get('bare_title') or '', len(lines)))
            total += len(lines)

    # 场景索引（导航用；不含系统/UI 文本）
    idx_path = args.out.replace('_全文本.txt', '_场景索引.txt')
    with open(idx_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('序号\t脚本名\t章题\t行数\n')
        for k, nm, ch, n in index:
            f.write('%d\t%s\t%s\t%d\n' % (k, nm, ch, n))
    print('scenes with text:', nscene, 'total lines:', total)
    print('->', args.out)
    print('->', idx_path)
    empty = [nm for k, nm, ch, n in index if n == 0]
    print('empty scenes:', len(empty), empty[:12])


if __name__ == '__main__':
    main()
