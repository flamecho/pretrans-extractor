# -*- coding: utf-8 -*-
"""二世の契り (PSP-JP, Otomate, 2011) 全文本提取

容器链: ISO9660 -> PSP_GAME/USRDIR/INSTALL.CPK (明文 CRI CPK) -> script/100..143 (STCM2L Jun 23 2010)
        USRDIR/UMD.CPK 只有 voice/ + movie/；INSDIR/INSTALL.DNS = PGD 安装副本(同内容)

记录: unit = [u32 size][payload]；payload = [ptr][0xff000000][0xff000000] + 记录 + [0][cmd][arg]
      记录 = [0][L/4][1][L][cp932]  (k=12)
cmd: 0xd2 = 框内续行(合并) / 0xd3 = 框末点击 / 0x1 = 框末点击(附名札框时的变体)
     0x1dd = 名札op(丢弃) / 0xe7(k=12) = 选择前正文(框末) / 0xe7,0xe6(k=24) = 选项

用法: python scripts/nisenochigiri_extract.py <输出txt> [script目录]
"""
import io
import os
import re
import struct
import sys

D = '_src_nise/install/script'
HERO = '真奈'      # #Name[1]（默认名，取 script/0 名表 0x1d7）
PET = 'シロ'       # #Name[2]（script/0 名表 0x1b9）

RE_KANA = re.compile(r'#Kana\[[^\]]*\]')
RE_COLOR = re.compile(r'#Color\[[^\]]*\]')
RE_SCALE = re.compile(r'#Scale\[[^\]]*\]')
RE_OTHER = re.compile(r'#(?!Name\[)[A-Za-z]+\[[^\]]*\]')
RE_PUA = re.compile(r'[\ue000-\uf8ff]')
RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')


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


def recs(pay):
    """顺序扫出 payload 内全部文本记录 -> [(k, text, cmd, arg)]"""
    n = len(pay)
    out = []
    k = 0
    while k < n - 15:
        f0, f1, f2, f3 = struct.unpack_from('<4I', pay, k)
        if f0 == 0 and f2 == 1 and 4 <= f3 <= 0x4000 and f3 % 4 == 0 \
                and f1 == f3 // 4 and k + 16 + f3 <= n:
            raw = pay[k + 16:k + 16 + f3].rstrip(b'\0')
            try:
                t = raw.decode('cp932')
            except UnicodeDecodeError:
                t = None
            if t is not None:
                cmd = arg = None
                m = k + 16 + f3
                if m + 12 <= n:
                    a, w1, w2 = struct.unpack_from('<3I', pay, m)
                    if a in (0, 1):
                        if w1 == 1 and m + 16 <= n:
                            # 变体：多一个参数字 [0][1][cmd][arg]
                            cmd, arg = w2, struct.unpack_from('<I', pay, m + 12)[0]
                        else:
                            cmd, arg = w1, w2
                out.append((k, t, cmd, arg))
                k += 16 + f3
                continue
        k += 4
    return out


def clean(t):
    t = t.replace('\\n', '')
    t = RE_KANA.sub('', t)
    t = RE_COLOR.sub('', t)
    t = RE_SCALE.sub('', t)
    t = RE_OTHER.sub('', t)
    t = RE_PUA.sub('', t)
    t = t.replace('#Name[1]', HERO).replace('#Name[2]', PET)
    t = t.replace('#Name[0]', '')
    return t


def load_names():
    """名札白名单：script/0 名表(0x1ae) + 全库 0x1dd 名札文本（清干净后）"""
    names = set()
    p = os.path.join(D, '0')
    b = open(p, 'rb').read()
    for u in units(b):
        for k, t, c, a in recs(u):
            if c == 0x1ae:
                names.add(clean(t).strip())
    import glob
    for p in glob.glob(os.path.join(D, '*')):
        bn = os.path.basename(p)
        if not bn.isdigit() or not (100 <= int(bn) <= 143):
            continue
        b = open(p, 'rb').read()
        for u in units(b):
            for k, t, c, a in recs(u):
                if c == 0x1dd:
                    names.add(clean(t).strip())
    names.add('？？？')
    return names


TEXT_CONT = {0xd2}
TEXT_END = {0xd3, 0x1, 0xe7}


RE_NAME_NO = re.compile(r'[。、」』！？…―─（）「『#\s0-9０-９]')
NAME_TAIL_NO = set('はがをにでとものへやかねよな')   # 叙述片段常以助词收尾


def norm(s):
    return s.replace('\u3000', '').replace(' ', '')


def is_name_like(s):
    s = s.strip()
    if not s or len(s) > 8:
        return False
    if RE_NAME_NO.search(s):
        return False
    if len(s) > 2 and s[-1] in NAME_TAIL_NO:
        return False
    return bool(RE_JP.search(s))


def extract_file(path, names, stat):
    b = open(path, 'rb').read()
    out = []
    flat = []
    for u in units(b):
        for k, t, c, a in recs(u):
            flat.append((k, t, c, a))
    cur = []
    opts = []
    prev_clean = None
    n = len(flat)
    for idx in range(n):
        k, t, c, a = flat[idx]
        nxt = flat[idx + 1][1][:1] if idx + 1 < n else ''
        if c in (0x1dd, 0x7a):
            stat['plate_op'] += 1
            continue
        if k == 24:
            if c in (0xe7, 0xe6) or (c == 0x1 and opts):
                s = clean(t).strip()
                if stat.get('skip'):
                    stat['skip'] -= 1
                    continue
                if s and not re.match(r'^[A-Za-z_0-9]+$', s):
                    if s in opts[-4:]:
                        stat['opt_dup'] += 1
                        continue
                    out.append(s)
                    prev_clean = s
                    opts.append(s)
                    stat['opt'] += 1
                else:
                    stat['opt_noise'].append(s)
            continue
        if k != 12:
            continue
        if c in TEXT_CONT:
            s = clean(t)
            if not s:
                continue
            if not cur and (s.strip() in names or
                            (is_name_like(s) and nxt in ('「', '『', '（'))):
                stat['plate_txt'] += 1
                if len(stat['plate_samples']) < 80:
                    stat['plate_samples'].append(s)
                continue
            cur.append(s)
            continue
        if c in TEXT_END:
            s = clean(t)
            if s:
                if not cur and (s.strip() in names or
                                (is_name_like(s) and nxt in ('「', '『', '（'))):
                    stat['plate_txt'] += 1
                    if len(stat['plate_samples']) < 80:
                        stat['plate_samples'].append(s)
                    continue
                cur.append(s)
            if not cur:
                continue
            txt = ''.join(cur)
            del cur[:]
            if txt.strip() == '序章をスキップしますか？':
                stat['skip'] = 2
                continue
            if txt.strip() in names:
                stat['plate_txt'] += 1
                if len(stat['plate_samples']) < 80:
                    stat['plate_samples'].append(txt)
                continue
            if txt == prev_clean or norm(txt) == norm(prev_clean or ''):
                stat['dup'] += 1
                continue
            out.append(txt)
            prev_clean = txt
            del opts[:]
            stat['frame'] += 1
            continue
        if c is not None or True:
            s = clean(t)
            if s and RE_JP.search(s) and len(s) >= 3:
                stat['odd_end'].append((os.path.basename(path), hex(c) if c is not None else None, t[:40]))
                if not cur and (s.strip() in names or
                                (is_name_like(s) and nxt in ('「', '『', '（'))):
                    stat['plate_txt'] += 1
                    continue
                cur.append(s)
            if not cur:
                continue
            txt = ''.join(cur)
            del cur[:]
            if txt.strip() in names:
                stat['plate_txt'] += 1
                continue
            if txt == prev_clean or norm(txt) == norm(prev_clean or ''):
                stat['dup'] += 1
                continue
            out.append(txt)
            prev_clean = txt
            del opts[:]
            stat['frame'] += 1
    if cur:
        txt = ''.join(cur)
        if txt.strip() not in names:
            out.append(txt)
            stat['frame'] += 1
    return out


COMMON = [
    'ここまで二世の契りを遊んでいただき、誠にありがとうございます。',
    '先程のエンディングを持ちまして、全てのグッドエンドを見ていただいた事になります。',
    'ただ、通ったルートによっては、見ていないエピソードやエンディングもあるかも知れません。',
    '中には、クリアした後に通ると追加されるエピソードもありますので、良かったら探してみて下さい。',
    '二世の契りのキャラクターやエピソード等で、気に入っていただけるものがありましたら、とても嬉しく思います。',
    'それでは失礼致します。',
]
DROP_LINES = set(COMMON) | {'処理開始', '処理開始\\n', '序章をスキップしますか？'}


def useful(s):
    if not s.strip():
        return False
    return bool(RE_JP.search(s))


def main():
    dst = sys.argv[1]
    files = sorted((f for f in os.listdir(D) if f.isdigit() and 100 <= int(f) <= 143), key=int)
    names = load_names()
    stat = {'frame': 0, 'opt': 0, 'plate_op': 0, 'plate_txt': 0, 'dup': 0,
            'plate_samples': [], 'odd': [], 'opt_noise': [], 'odd_end': [], 'skip': 0, 'opt_dup': 0,
            'common_block': 0}
    lines = []
    seen = {}
    for f in files:
        seg = [s for s in extract_file(os.path.join(D, f), names, stat)
               if s not in DROP_LINES and useful(s)]
        # 共通导入块（逐档重复的整段开头）只留一次：丢掉与本档前文完全相同的开头段
        while len(seg) >= 5 and seg[0] in seen:
            best = 0
            for pos in seen[seg[0]]:
                n2 = 0
                while n2 < len(seg) and pos + n2 < len(lines) and lines[pos + n2] == seg[n2]:
                    n2 += 1
                best = max(best, n2)
            if best < 5:
                break
            stat['common_block'] += best
            seg = seg[best:]
        for i, s in enumerate(seg):
            seen.setdefault(s, []).append(len(lines) + i)
        lines += seg
    # 全クリア後メッセージ（各档共通块，只留一次，置末尾）
    lines += COMMON
    print('files %d  frames %d  options %d  plate_op %d  plate_txt %d  dup %d'
          % (len(files), stat['frame'], stat['opt'], stat['plate_op'],
             stat['plate_txt'], stat['dup']))
    print('plate_txt samples:', stat['plate_samples'][:40])
    print('opt noise:', stat['opt_noise'][:20])
    print('common block dropped:', stat['common_block'])
    print('odd_end:', stat['odd_end'][:20], len(stat['odd_end']))
    with io.open(dst, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('wrote', dst, len(lines), 'lines')


if __name__ == '__main__':
    main()
