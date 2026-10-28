# -*- coding: utf-8 -*-
"""ときめきレストラン☆☆☆ Project TRISTARS (PSV / PCSG01171, KONAMI) 全文本提取 v2

链路
  RAR(app/PCSG01171) → psvpfsparser -z <zRIF> → DATA.BIN
  DATA.BIN = CDAR v4: "CDAR" + u32 ver(4) + u32 count + count×u32 + count×12B {off, ds, stored}
            载荷 zlib(78 …)；子条目可为嵌套 CDAR（递归 + md5 去重）

VM（遥か5/ネオアン同族）
  指令 = <u8 op><u32 arg> 定长；文本 = 04 <u16 len> <cp932> 00
  框边界：间隔里出现 BOUND(1e8b052422) / C7(1ec7094774) / M91(1e910bbda0) ⇒ 断开
         间隔不以 CLOSE(1ef907874c) 开头 ⇒ 也断开（续写）

取捨（§0）
  收：剧情叶（含「イベント・」标签的叶）的全部正文 ＋ 豆辞典（【用語】【人名】【組織】【機能】【施設】）
  不收：系统/UI（メモリーカード・セーブ・設定・ヘルプ・操作説明・絆通知）、
        句集（挨拶/相槌バンク＝叶 235/310/992-1073/992-1343）、年表資料（168）、
        デバッグ（「次は〜モーションです」）、同社他作残骸（992/657 怨霊・帝都）
"""
import sys, struct, zlib, hashlib, re

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
C7 = b'\x1e\xc7\x09\x47\x74'
M91 = b'\x1e\x91\x0b\xbd\xa0'

# 句集・資料・他作残骸・デバッグ（叶单位排除）
DROP_LEAF = {'168', '235', '310', '992/657', '992/1073', '992/1343', '992/480', '992/1304'}


def load_leaves(datapath, maxdepth=4):
    d = open(datapath, 'rb').read()
    cnt = struct.unpack_from('<I', d, 8)[0]
    b2 = 16 + cnt * 4
    ents = [struct.unpack_from('<III', d, b2 + 12 * i) for i in range(cnt)]
    leaves, seen = [], set()

    def maybe_z(u):
        if len(u) > 1 and u[0] == 0x78:
            try:
                return zlib.decompress(u)
            except Exception:
                return u
        return u

    def parse_cdar(u):
        if len(u) < 16 or u[:4] != b'CDAR':
            return None
        c = struct.unpack_from('<I', u, 8)[0]
        bb = 16 + c * 4
        if c == 0 or bb + 12 * c > len(u):
            return None
        return [struct.unpack_from('<III', u, bb + 12 * k) for k in range(c)]

    def walk(u, path, depth):
        u = maybe_z(u)
        e = parse_cdar(u)
        if e is not None and depth < maxdepth:
            for k, (o, ds, s) in enumerate(e):
                if s > 0 and o + s <= len(u):
                    walk(u[o:o + s], path + '/' + str(k), depth + 1)
            return
        h = hashlib.md5(u).hexdigest()
        if h in seen:
            return
        seen.add(h)
        leaves.append((path, u))

    for i, (o, ds, s) in enumerate(ents):
        walk(d[o:o + s], str(i), 0)
    return leaves


def valid_record(b, i):
    n = len(b)
    if i + 3 > n or b[i] != 4:
        return None
    ln = struct.unpack_from('<H', b, i + 1)[0]
    if ln < 2 or ln > 4000:
        return None
    e = i + 3 + ln
    if e > n or b[e - 1] != 0:
        return None
    body = b[i + 3:e - 1]
    if b'\x00' in body:
        return None
    if any(x < 0x20 and x != 0x0a for x in body):
        return None
    try:
        return (i, e, body.decode('cp932'))
    except Exception:
        return None


def find_records(b):
    out, i, n = [], 0, len(b)
    while i < n - 3:
        if b[i] == 4:
            r = valid_record(b, i)
            if r:
                out.append(r)
                i = r[1]
                continue
        i += 1
    return out


def clean(s):
    s = re.sub(r'[\u3000]*\n[\u3000]*', '', s)
    return s.replace('\n', '')


def process(b):
    recs = find_records(b)
    if not recs:
        return []
    msgs, cur = [], []

    def flush():
        if cur:
            msgs.append(''.join(cur))

    for i, (s, e, t) in enumerate(recs):
        gap = b[(recs[i - 1][1] if i > 0 else 0):s]
        sep = (BOUND in gap) or (C7 in gap) or (M91 in gap)
        if i > 0 and not gap.startswith(CLOSE):
            sep = True
        if sep and cur:
            flush()
            cur = []
        cur.append(t)
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        if not b[e:nxt].startswith(CLOSE):
            flush()
            cur = []
    flush()
    return msgs


KANA = re.compile(r'[ぁ-んァ-ヴ]')
SENT = re.compile(r'[。、！？…」』）]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e]+$')
# 系统/UI・通知（正文叶内混入的菜单锁定文・错误提示）
UI_LINE = re.compile(
    r'(を観た状態でPLAYを続けていないと再生できません|設定エラー|'
    r'「Memory」を重ねた結果|項目が解放されました|（デバッグ）|'
    r'^音声引用テスト|^モブ表示|^BUテスト|^立ち位置テスト)')

# 豆辞典：收录分类（【機能】=ヘルプ/操作説明、【再生中操作】=操作ガイド ⇒ 排除）
GLOSS_KEEP = ('用語', '人名', '組織', '施設', '基本')


def is_label(t):
    return t.startswith('イベント・') or t.startswith('イベント_') or t.startswith('システム')


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else '_work_tokires/dec/DATA.BIN'
    out = sys.argv[2] if len(sys.argv) > 2 else '_work_tokires/tokires.txt'
    leaves = load_leaves(src)
    body, gloss, stats = [], [], []
    for p, u in leaves:
        if p in DROP_LEAF:
            continue
        recs = find_records(u)
        if not recs:
            continue
        txts = [t for _, _, t in recs]
        is_story = any(t.startswith('イベント・') for t in txts)
        is_gloss = txts[0].startswith('【') and '】' in txts[0]
        if not (is_story or is_gloss):
            continue
        _n = [0]
        for t in process(u):
            t = clean(t).strip('\u3000')
            if not t or is_label(t):
                continue
            if ASCII_ONLY.match(t) or not KANA.search(t):
                continue
            if '_' in t and not SENT.search(t):
                continue
            if UI_LINE.search(t):
                continue
            if is_gloss:
                continue
            body.append(t)
            _n[0] += 1

        # 豆辞典：1 叶 = 【分類】見出し語 ＋ 解説文（记录直读，不做框合并）
        stats.append((p, _n[0]))
        if is_gloss:
            recs_t = [clean(t).strip('\u3000') for _, _, t in recs]
            head, buf = None, []
            for t in recs_t:
                if t.startswith('【') and '】' in t:
                    if head:
                        gloss.append((head, ''.join(buf)))
                    head, buf = t, []
                else:
                    buf.append(t)
            if head:
                gloss.append((head, ''.join(buf)))

    gl2, seen = [], set()
    for head, bodyt in gloss:
        cat = head[1:head.index('】')]
        name = head[head.index('】') + 1:]
        if cat not in GLOSS_KEEP or not name or not bodyt:
            continue
        line = f'【{name}】{bodyt}'
        if line in seen:
            continue
        seen.add(line)
        gl2.append(line)

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for t in body:
            f.write(t + '\n')
        for t in gl2:
            f.write(t + '\n')
    with open(out + '.leaves.tsv', 'w', encoding='utf-8', newline='\n') as g:
        for p, n in stats:
            g.write(f'{p}\t{n}\n')
    used = [s for s in stats if s[1] > 0]
    print('leaves', len(leaves), 'body', len(body), 'gloss', len(gl2),
          'leaves_with_text', len(used), '->', out)


if __name__ == '__main__':
    main()
