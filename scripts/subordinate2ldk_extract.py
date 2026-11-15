# -*- coding: utf-8 -*-
"""上司と秘密の2LDK（Switch / Bezel Engine「SCNE + scb_」）剧本正文提取。

链路：romfs/Archive/script.nx.bea（SCNE）
      ├ ASST0 条目表（0x30 B/条，534 条）：+20 压缩大小 +24 解压大小 +32 帧偏移 +40 名字指针
      └ 每帧 = zstd → 'scb_' 脚本（282 ja + 252 en）

scb_ 头（0x08 起 8 个 u32）：code_off/code_len, t1_off/t1_len, t2_off/t2_len, str_off/str_len
自证：t2_off + 4 + 4*N == str_off（534/534 成立）
字符串池 = NUL 结尾 UTF-8；偏移表按池序；正文 id 在 code 中单调递增（534/534）

记录识别（L1：记录自定界 + 交叉验证）：
  [0x000b][0x0002][name_id][0x0000]   名札（保留，接在同行台词前 → 【名】台词）
  [0x000c][0x0002][text_id][0x0000]   正文（= 一页 = 一次点击）
  [0x0011][arg]                       等待点击（普通）
  [0x0021][arg]                       等待点击（带角色/语音）
  [0x0013][argc][每 6 字一组：选项文 id, 标签 id, 0, 0, 0]  选项块
  [0x0012][0x0002][id][0]             工作用临时串（全为非日文标签，不进成品）

交叉验证（本作实测）：
  1) 0x0b 记录 138,950 ＝ 0x0c 记录 138,949 + 1，且 0x0b 恒紧邻其后的 0x0c
  2) 正文 id 在全部 534 帧内单调递增 ⇒ 池序 = 脚本序
  3) 非空串 100% 被 0x0b/0x0c/0x13 引用；仅 0x12 引用的 4,153 条全为非日文标签（日文 0 条）
  4) 两次点击（0x11/0x21）之间恒定只有 1 条 0x0c ⇒ 一次点击一页 ⇒ 单版
  5) 0x0c 与 0x0c 之间无点击码的相邻对 0 处 ⇒ 无跨页合并需求

用法：python extract.py <script.nx.bea> <out.txt> [dump.json]
"""
import sys, struct, re, json, zstandard

PLACE = {'#NAME[1]': '立花', '#NAME[2]': 'なつみ'}
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def zframes(b):
    out, i = [], 0
    while True:
        j = b.find(b'\x28\xb5\x2f\xfd', i)
        if j < 0:
            break
        o = zstandard.ZstdDecompressor().decompressobj()
        d = o.decompress(b[j:])
        used = len(b) - j - len(o.unused_data)
        out.append((j, used, d))
        i = j + used
    return out


def parse_scb(d):
    co, cs, t1o, t1s, t2o, t2s, so, ss = struct.unpack_from('<8I', d, 8)
    pool = d[so:so + ss]
    n = struct.unpack_from('<I', d, t2o)[0]
    offs = struct.unpack_from('<%dI' % n, d, t2o + 4)
    strs = []
    for o in offs:
        e = pool.find(b'\x00', o)
        if e < 0:
            e = len(pool)
        strs.append(pool[o:e].decode('utf-8', 'replace'))
    W = struct.unpack_from('<%dH' % (cs // 2), d, co)
    return strs, W, (t2o + 4 + 4 * n == so)


def clean(t):
    for k, v in PLACE.items():
        t = t.replace(k, v)
    t = re.sub(r'#NAME\[(\d)\]', '', t)
    return t.replace('\r', '').replace('\n', '').strip()


def main():
    bea, out_txt = sys.argv[1], sys.argv[2]
    dump = sys.argv[3] if len(sys.argv) > 3 else None
    b = open(bea, 'rb').read()
    scb = [(off, d) for off, used, d in zframes(b) if d[:4] == b'scb_']

    ents, p = [], 0
    while True:
        k = b.find(b'ASST0', p)
        if k < 0:
            break
        ents.append((struct.unpack_from('<I', b, k + 32)[0],
                     struct.unpack_from('<I', b, k + 40)[0]))
        p = k + 4
    off2 = {}
    for foff, noff in ents:
        ln = struct.unpack_from('<H', b, noff)[0]
        m = re.match(rb'script/(ja|en)/([0-9A-Za-z_]+)\.scb$', b[noff + 2:noff + 2 + ln])
        if m:
            off2[foff] = (m.group(1).decode(), m.group(2).decode())

    frames, inv_ok, mism = [], 0, 0
    for off, d in scb:
        strs, W, inv = parse_scb(d)
        inv_ok += inv
        lang, sid = off2.get(off, ('?', '?'))
        n, cnt = len(W), len(strs)
        jp = tot = 0
        for q in range(n - 3):
            if W[q] == 0x0C and W[q + 1] == 2 and W[q + 3] == 0 and W[q + 2] < cnt:
                t = strs[W[q + 2]]
                if t:
                    tot += 1
                    jp += bool(JP.search(t))
        guess = 'ja' if tot and jp / tot > 0.3 else 'en'
        mism += (guess != lang)
        frames.append({'off': off, 'lang': lang, 'sid': sid, 'strs': strs, 'W': W})

    print('[i] scb 帧=%d  池不变量=%d/%d  名字映射=%d  语言复核不一致=%d' % (
        len(scb), inv_ok, len(scb), len(off2), mism))

    order = sorted([f for f in frames if f['lang'] == 'ja'], key=lambda f: f['sid'])
    lines = []
    stat = {'frames': len(order), 'pages': 0, 'plates': 0, 'choices': 0,
            'empty_text': 0, 'multi_per_click': 0, 'adjacent_no_click': 0}
    for f in order:
        strs, W = f['strs'], f['W']
        n, cnt = len(W), len(strs)
        ev = []
        q = 0
        while q + 3 < n:
            if W[q] == 0x0B and W[q + 1] == 2 and W[q + 3] == 0 and W[q + 2] < cnt:
                ev.append(('N', q, W[q + 2]))
                q += 4
                continue
            if W[q] == 0x0C and W[q + 1] == 2 and W[q + 3] == 0 and W[q + 2] < cnt:
                ev.append(('T', q, W[q + 2]))
                q += 4
                continue
            if W[q] == 0x13:
                ev.append(('O', q, W[q + 1]))
                q += 2 + W[q + 1]
                continue
            if W[q] in (0x11, 0x21):
                ev.append(('C', q, 0))
                q += 2
                continue
            q += 1

        tpos = [e[1] for e in ev if e[0] == 'T']
        for a, bb in zip(tpos, tpos[1:]):
            if not any(e[0] == 'C' and a < e[1] < bb for e in ev):
                stat['adjacent_no_click'] += 1

        page, plate = [], None
        for kind, pos, val in ev:
            if kind == 'N':
                t = clean(strs[val])
                plate = t or None
                if plate:
                    stat['plates'] += 1
            elif kind == 'T':
                t = strs[val]
                if t:
                    page.append((plate, t))
                    stat['pages'] += 1
                else:
                    stat['empty_text'] += 1
                plate = None
            elif kind == 'O':
                args = W[pos + 2:pos + 2 + val]
                k = 0
                while k + 1 < len(args):
                    a = args[k]
                    if a >= cnt or args[k + 1] != 0:
                        break
                    t = strs[a]
                    if t:
                        lines.append(clean(t))
                        stat['choices'] += 1
                    k += 6
            elif kind == 'C':
                if len(page) > 1:
                    stat['multi_per_click'] += 1
                for nm, t in page:
                    body = clean(t)
                    lines.append(nm + body if nm else body)
                page = []
                plate = None
        for nm, t in page:
            body = clean(t)
            lines.append(nm + body if nm else body)

    print('[i] 统计:', stat)
    lines = [x for x in lines if x]
    if dump:
        json.dump({'stat': stat, 'lines': lines}, open(dump, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    with open(out_txt, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('[i] -> %s  %d 行' % (out_txt, len(lines)))


if __name__ == '__main__':
    main()
