# -*- coding: utf-8 -*-
"""官能昔話 ポータブル (PSP, ULJM06015, vndb v9071) 全文本提取

【容器链】
  CHD v5(zstd) --scripts/chd_to_iso.js--> ISO9660
    -> PSP_GAME/USRDIR/INSTALL.CPK (CRI CPK) --scripts/cpk.py--> script/*  = STCM2L (Jul 21 2011)
       USRDIR/UMD.CPK 只有 movie/；voice 在 INSTALL2.CPK
    -> script/0-5            = 共通システム（符号表：章名/話名/処理開始）⇒ 无正文，排除
    -> script/1201..1902     = 恋愛番長（同社他作）遗留符号表 ⇒ 排除
    -> script/1xx..9xx       = 本编 9 段：プロローグ / 七つの昔話 / エピローグ

【STCM2L 记录（本作布局）】
  unit = [u32 size][payload]；payload = [ptr][-1][-1] + 记录 [+ [0][cmd][arg]]
  记录 = [0][L/4][1][L][cp932]，正文记录落 payload 偏移 12
  cmd: 0xd2 = 框内续行（同一次点击，合并）  0xd3 = 框末（点击）
       0x34/0x35 = 框末（大字/演出版，本作共 23 条）
       0x7a = 名札（arg=名表索引；丢弃并断框）
       0xe7/0xe6 = 选项（连串 e7 … 末尾 e6）
       0x33 = 処理開始（调试串）/ 0x5・0x2bc = 章名・話名表 / 0x0・0x34(k=24) = 符号表 ⇒ 排除
  偏移 24 的记录 = 符号表/选项（payload[12] 为 0xffffffXX）

【主角】姫子（script/0 名表 cmd 0x2d1 初期値）⇒ #Name[1] → 姫子

用法: python kannou_extract.py <输出txt>
"""
import struct, os, re, sys, io

D = '_work_kannou/install/script'
HERO = '姫子'
DROP_TEXT = {'処理開始', '処理開始\\n', '処理開始\r\n'}
TEXT_CMDS = {0xd2, 0xd3, 0x34, 0x35}
END_CMDS = {0xd3, 0x34, 0x35}
OPT_CMDS = {0xe7, 0xe6}
RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_NAME_NO = re.compile(r'[。、」』！？…―─（）「『#\s0-9０-９]')
HONOR = ('さん', 'ちゃん', 'さま', '様', '君', 'くん')


def units(b):
    ci = b.find(b'CODE_START_')
    if ci < 0:
        return []
    exp = struct.unpack_from('<I', b, 0x20)[0]
    i = ci + 24
    out = []
    while i + 4 <= exp:
        bs = struct.unpack_from('<I', b, i)[0]
        if bs < 4 or i + bs > len(b):
            break
        out.append(b[i + 4:i + bs])
        i += bs
    return out


def parse(pay):
    """-> (k, text, cmd, arg)；找不到记录返回 None"""
    n = len(pay)
    for k in range(0, n - 15, 4):
        f0, f1, f2, f3 = struct.unpack_from('<4I', pay, k)
        if f0 or f2 != 1 or f3 < 4 or f3 > 0x4000 or f3 % 4 or f1 != f3 // 4:
            continue
        if k + 16 + f3 > n:
            continue
        raw = pay[k + 16:k + 16 + f3].rstrip(b'\0')
        try:
            t = raw.decode('cp932')
        except Exception:
            continue
        tail = pay[k + 16 + f3:]
        c = a = None
        if len(tail) >= 12:
            a, c, _ = struct.unpack_from('<3I', tail, 0)
            if a not in (0, 1):
                c = None
        return k, t, c, a
    return None


def clean(t):
    t = t.replace('\\n', '')
    t = re.sub(r'#(?!Name\[)[A-Za-z]+\[[^\]]*\]', '', t)
    t = re.sub(r'[\ue000-\uf8ff]', '', t)          # 私用区字形槽
    return t.replace('#Name[1]', HERO)


def useful(t):
    """片段是否有内容：去掉半角假名/符号后仍非空"""
    if re.match(r'^[\x20-\x7e]*$', t):
        return False                     # 纯 ASCII ⇒ 资源名/符号表
    return bool(re.sub(r'[\uff61-\uff9f\u3000\s]', '', t))


def extract_file(path, stat):
    b = open(path, 'rb').read()
    if b[:6] != b'STCM2L':
        return []
    out, cur = [], []

    def flush():
        if not cur:
            return
        parts = cur[:]
        if len(parts) >= 2 and len(parts[0]) <= 8 \
                and not RE_NAME_NO.search(parts[0]) \
                and parts[1][:1] in ('「', '『', '（'):
            stat['drop_name'] += 1
            if len(stat['drop_samples']) < 60:
                stat['drop_samples'].append(parts[0])
            parts = parts[1:]
        stat['frag_drop'] += len(cur) - len(parts)
        txt = ''.join(parts)
        if txt:
            out.append(txt)
            stat['frame'] += 1
        del cur[:]

    for u in units(b):
        r = parse(u)
        if not r:
            continue
        k, t, c, a = r
        if c in OPT_CMDS and k == 24:
            flush()
            out.append(clean(t))
            stat['opt'] += 1
            continue
        if k != 12:
            continue
        if c == 0x7a:
            flush()
            stat['plate'] += 1
            continue
        if t in DROP_TEXT:
            stat['debug'] += 1
            continue
        if not useful(t):
            continue
        if c is not None and c not in TEXT_CMDS:
            # 未知 cmd：名札形（短・无句读）⇒ 名札丢弃；否则按正文处理并断框
            if len(t) <= 8 and not RE_NAME_NO.search(t) and RE_JP.search(t):
                flush()
                stat['plate'] += 1
                stat['odd'].append((path, hex(c), t + ' [NAME]'))
                continue
            stat['odd'].append((path, hex(c), t))
            t2 = clean(t)
            if RE_JP.search(t2):
                cur.append(t2)
                flush()
            continue
        t2 = clean(t)
        if not useful(t2):
            continue
        cur.append(t2)
        stat['frag_used'] += 1
        stat['frag_cmd'][c] += 1
        if c in END_CMDS:
            flush()
    flush()
    return out


ORDER = lambda f: int(f)


def main():
    files = [f for f in os.listdir(D) if f.isdigit() and 100 <= int(f) < 1000]
    files.sort(key=ORDER)
    stat = {'opt': 0, 'plate': 0, 'frame': 0, 'drop_name': 0,
            'drop_samples': [], 'debug': 0, 'odd': [], 'frag_drop': 0,
            'frag_used': 0,
            'frag_cmd': __import__('collections').Counter()}
    lines = []
    for f in files:
        lines += extract_file(os.path.join(D, f), stat)
    print('frames %d  options %d  plates %d  dropped_name %d  debug %d  odd %d'
          % (stat['frame'], stat['opt'], stat['plate'], stat['drop_name'],
             stat['debug'], len(stat['odd'])))
    print('frag used %d / dropped-as-name %d / by cmd %s'
          % (stat['frag_used'], stat['frag_drop'],
             {hex(k) if k is not None else None: v for k, v in stat['frag_cmd'].items()}))
    print('dropped-name kinds:', sorted(set(stat['drop_samples'])))
    for x in stat['odd']:
        print('  ODD', x[1], repr(x[2][:50]))
    dst = sys.argv[1]
    with io.open(dst, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('wrote', dst, len(lines), 'lines')


if __name__ == '__main__':
    main()
