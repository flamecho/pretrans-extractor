# -*- coding: utf-8 -*-
"""遥かなる時空の中で6 DX (Switch) 全文本提取器 v2
- CDAR 容器 (DATA_ORG=遥か6本篇, DATA_PK=幻燈ロンド)
- VM: [op][u32] 定长5B + [04][u16 len][cp932] 变长文本
- 校验式 walk + 失步重同步 (header 区含不规则长度指令)
- 消息边界: gap 含 1e 2224058b → 新消息
- 文本记录后无 close(1e 4c8707f9) → 独立标题行
- 插入变量块: 1e 0a1e02cf 引导
"""
import struct, zlib, re, os, collections

class CDAR:
    def __init__(self, path):
        with open(path, 'rb') as f: self.d = f.read()
        data = self.d
        assert data[:4] == b'CDAR', 'not CDAR: ' + path
        self.unk1, self.count, self.unk2 = struct.unpack_from('<III', data, 4)
        after = 16 + self.count * 4
        for base in (after, (after + 0xF) & ~0xF):
            if base + 12*self.count > len(data): continue
            ok=True; prev=-1; ents=[]
            for i in range(self.count):
                o, ds, s = struct.unpack_from('<III', data, base+12*i)
                if o<prev or o>len(data) or s>len(data) or o+s>len(data): ok=False; break
                prev=o; ents.append((o,ds,s))
            if ok: self.entries=ents; self.base=base; break
        else:
            raise ValueError('bad entry table')
    def raw(self,i):
        o,ds,s=self.entries[i]; return self.d[o:o+s]
    def data(self,i):
        blob=self.raw(i)
        if len(blob)>=2 and blob[0]==0x78:
            try: return zlib.decompress(blob)
            except Exception:
                try: return zlib.decompressobj().decompress(blob)
                except Exception: pass
        return blob

# ---- 文本记录校验 ----
def jp_ratio(t):
    if not t: return 0.0
    jp = sum(1 for ch in t if ('\u3040'<=ch<='\u30ff') or ('\u4e00'<=ch<='\u9fff') or ('\u3000'<=ch<='\u303f') or ('\uff01'<=ch<='\uff60') or ch in '─―…‥')
    return jp / len(t)

def valid_text_record(d, p):
    """d[p]==0x04 时, 验证是否为一个合法文本记录. 返回 (ok, ln, textbytes)"""
    L = len(d)
    if p+3 > L: return False, 0, None
    ln = struct.unpack_from('<H', d, p+1)[0]
    if ln < 1 or ln > 3000: return False, 0, None
    end = p + 3 + ln
    if end > L: return False, 0, None
    if d[end-1] != 0: return False, 0, None
    body = d[p+3:end-1]
    if b'\x00' in body: return False, 0, None
    # 内容必须基本可解码
    try:
        s = body.decode('cp932')
    except Exception:
        return False, 0, None
    # 控制字节比例 (除 \n 外不应有其它 <0x20)
    ctrl = sum(1 for b in body if b < 0x20 and b != 0x0a)
    if ctrl > 0: return False, 0, None
    return True, ln, body

KNOWN_OPS = {0x02, 0x1e, 0x04, 0x17}

SYNC_PATS = [
    bytes.fromhex('1ef907874c'),   # close
    bytes.fromhex('1ecf021e0a'),   # insert start
    bytes.fromhex('1e8b052422'),   # message chain
]

def instr_len_at(d, p):
    """估算位置 p 处一条指令的长度; 不合法返回 None."""
    L = len(d)
    if p >= L: return None
    b = d[p]
    if b == 0x04:
        ok, ln, _ = valid_text_record(d, p)
        return (3 + ln) if ok else None
    if b in (0x02, 0x1e):
        return 5 if p + 5 <= L else None
    return None   # 未知op

def frame_chain_ok(d, p, depth=2):
    n = instr_len_at(d, p)
    if n is None: return False
    if depth <= 1: return True
    return frame_chain_ok(d, p + n, depth - 1)

def walk_safe(d, start=0):
    """校验式遍历; op17 等非常规指令采用多长度试探; 失步时后向重同步."""
    ins = []
    i = start
    L = len(d)
    while i < L:
        b = d[i]
        if b == 0x04:
            ok, ln, body = valid_text_record(d, i)
            if ok:
                ins.append((i, 0x04, ln, body))
                i += 3 + ln
                continue
        # 常规 5B 指令
        if i + 5 > L: break
        if b in (0x02, 0x1e):
            val = struct.unpack_from('<I', d, i+1)[0]
            ins.append((i, b, val, None))
            i += 5
            continue
        # 非常规 op (17 等): 多长度试探
        chosen = None
        if b == 0x17:
            for ln_try in (3, 4, 5, 6, 7, 8):
                if frame_chain_ok(d, i + ln_try, 2):
                    chosen = ln_try
                    break
        if chosen is None and frame_chain_ok(d, i + 5, 2):
            chosen = 5
        if chosen is not None:
            val = struct.unpack_from('<I', d, i+1)[0]
            ins.append((i, b, val, None))
            i += chosen
            continue
        # 失步: 重同步
        best = None
        for pat in SYNC_PATS:
            k = d.find(pat, i+1)
            if k >= 0 and (best is None or k < best):
                best = k
        k2 = d.find(b'\x04', i+1)
        while k2 >= 0:
            ok2, ln2, _ = valid_text_record(d, k2)
            if ok2:
                if best is None or k2 < best:
                    best = k2
                break
            k2 = d.find(b'\x04', k2+1)
        if best is None:
            break
        # 恢复区间内的文本记录
        pp = i
        while pp < best - 3:
            if d[pp] == 4:
                ok3, ln3, body3 = valid_text_record(d, pp)
                if ok3:
                    ins.append((pp, 0x04, ln3, body3))
                    pp += 3 + ln3
                    continue
            pp += 1
        i = best
    return ins

# ---- 插入变量 ----
VAR_TEXT = {
    0x329007e7: '梓', 0x01ea0153: '梓', 0x01cb013a: '高塚',
    0x2350067d: '高塚梓', 0x1d950587: '高塚梓', 0x0b49032e: '高塚梓',
}
VAR_PLACEHOLDER = '〓'
INS_CONSTS = {0x15500462, 0x1af9056c, 0x00000002, 0x0d6503f2, 0x13d404bc}
CLOSE = 0x4c8707f9
INS_OP  = 0x0a1e02cf

RE_NOISE_LIST = [
    re.compile(r'^イベント・'),
    re.compile(r'^回想録[0-9０-９]+$'),
    re.compile(r'^配信イベント[0-9０-９]*$'),
    re.compile(r'^札[0-9０-９]+$'),
    re.compile(r'^(ダミー|仮|予備|テスト)$'),
    re.compile(r'フラグ$'),
    re.compile(r'^ゴシップ取材'),
    re.compile(r'^[0-9A-Za-z_\-]+$'),
    re.compile(r'^[！？…、。\s]+$'),
]
def is_noise(t):
    for r in RE_NOISE_LIST:
        if r.search(t): return True
    return False

def clean_message(s):
    s = s.replace('\u3000\n', '\n')
    s = s.replace('\n\u3000', '\n').replace('\n', '')
    return s

def process_entry(d):
    ins = walk_safe(d)
    n = len(ins)
    msgs = []
    unresolved = []
    cur = []
    last_elem = -1   # 上一个"元素"(文本或插入)的指令下标
    def gap_has_boundary(k):
        for gi in range(last_elem+1, k):
            o2, op2, v2, t2 = ins[gi]
            if op2 == 0x1e and v2 == 0x2224058b:
                return True
        return False
    def flush():
        if cur:
            msgs.append(''.join(cur))
            cur.clear()
    k = 0
    while k < n:
        off, op, val, txt = ins[k]
        if txt is not None:
            t = txt.decode('cp932', errors='replace')
            has_close = (k+1 < n and ins[k+1][1] == 0x1e and ins[k+1][2] == CLOSE)
            if last_elem >= 0 and gap_has_boundary(k):
                flush()
            cur.append(t)
            last_elem = k
            if not has_close:
                # 标题/独立行: 单独成行
                flush()
            k += 1
            continue
        if op == 0x1e and val == INS_OP:
            if last_elem >= 0 and gap_has_boundary(k):
                flush()
            j = k + 1
            pieces = []
            while j < n and ins[j][3] is None and j < k + 12:
                o2, op2, v2, t2 = ins[j]
                if op2 == 0x1e and v2 == 0x329007e7:
                    pieces.append(('1e', v2))
                elif op2 == 0x02 and v2 not in INS_CONSTS:
                    pieces.append(('02', v2))
                j += 1
            s = ''
            for kind, v in pieces:
                if v in VAR_TEXT: s += VAR_TEXT[v]
                else:
                    s += VAR_PLACEHOLDER
                    unresolved.append((kind, v))
            cur.append(s)
            last_elem = j - 1 if j > k else k
            k = j
            continue
        k += 1
    flush()
    return msgs, unresolved

def main():
    """用法: haruka6_extract.py <DATA_xxx.BIN> <out.txt> [<DATA_yyy.BIN> <out2.txt> ...]
    遥かなる時空の中で6 DX (Switch) / Ruby Party CDAR 脚本提取。
    DATA_ORG.BIN = 遥か6 本篇; DATA_PK.BIN = 幻燈ロンド (1.0.1)。"""
    import sys
    if len(sys.argv) < 3 or len(sys.argv) % 2 == 0:
        print(__doc__)
        sys.exit(1)
    all_unresolved = {}
    for a in range(1, len(sys.argv), 2):
        path, outpath = sys.argv[a], sys.argv[a+1]
        c = CDAR(path)
        lines = []
        n_entries = 0
        for i in range(c.count):
            try: d = c.data(i)
            except Exception:
                continue
            if len(d) < 4: continue
            head = d[:4]
            if head in (b'GT1G', b'KTSS', b'CDAR') or head[:2] == b'PK':
                continue
            msgs, unresolved = process_entry(d)
            if not msgs: continue
            kept = []
            for m in msgs:
                m2 = clean_message(m)
                if not m2: continue
                if jp_ratio(m2) < 0.35 and not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', m2):
                    continue
                if is_noise(m2): continue
                kept.append(m2)
            if not kept: continue
            n_entries += 1
            lines.extend(kept)
            for kind, v in unresolved:
                all_unresolved.setdefault((os.path.basename(path), kind, v), 0)
                all_unresolved[(os.path.basename(path), kind, v)] += 1
        with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print(f'[{os.path.basename(path)}] entries={n_entries} lines={len(lines)} -> {outpath}')
    if all_unresolved:
        print()
        print('== 未解析插入值 ==')
        for (tag, kind, v), n in sorted(all_unresolved.items()):
            print(f'  {tag} {kind} 0x{v:08x} x{n}')

if __name__ == '__main__':
    main()
