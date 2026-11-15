# -*- coding: utf-8 -*-
"""BUSTAFELLOWS（NS-JP, Unity 2018.4 IL2CPP, global-metadata v24）文本提取。

文本源（三处，均已逐字节核验）：
  A. StreamingAssets/sk_ep0_text_2.bytes   自研 UTXT 容器，23,966 条记录
  B. data.unity3d MonoBehaviour pid 436    PhoneMessageContentsDatabase（mailText_/dm_ 正文，72 条）
  C. data.unity3d MonoBehaviour pid 429    ContentsDatabase（メモラビリア 解説，66 条）

UTXT 容器：
  0x00  "UTXT" | u32 ver=1 | u32 常量 | u32 table_end
  0x10..table_end-4   varint 表：[0]=记录数 n，[1..n]=每条字节长（7bit 高位组，首字节 msb=续）
  table_end-4        "TEND"
  table_end..EOF     n 条记录首尾相接（Σ长度 == 文件长 − table_end 已闭合）
字符码流：0x00=框内换行；0x01..0x7F→表下标 b-1；0x81..→(b1-0x81)*128+(b2-1)+128
字符表   = global-metadata.dat 字面量（3704 字 = ASCII 0x20–0x7E + SJIS 全集序）

成行判据（L1）：一条记录 = 表长界定的一段 = 一个文本框 = 一次点击；0x00 为框内排版换行
  → 81.7% 的 0x00 之后紧跟全角空格（续行缩进）、78.8% 之前是句读；每条记录内 「 与 」 各至多 1 个
  → 无点击码、无跨记录断句 ⇒ 单版。
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

ROOT = os.path.join(VNTRANS_HOME, '还没做/[NS-JP]BUSTAFELLOWS/romfs/Data')
SA = os.path.join(ROOT, 'StreamingAssets')
TEXT = os.path.join(SA, 'sk_ep0_text_2.bytes')
META = os.path.join(ROOT, r'Managed\Metadata\global-metadata.dat')
UNITY = os.path.join(ROOT, 'data.unity3d')
DEST = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]BUSTAFELLOWS.txt')
WORK = os.path.join(VNTRANS_HOME, '_work_bustafellows')

HERO = 'テウタ'

# ---------------- 字符表 ----------------
def load_table():
    md = open(META, 'rb').read()
    sl_off, sl_cnt, sld_off, _ = struct.unpack_from('<IIII', md, 8)
    for i in range(sl_cnt // 8):
        ln, idx = struct.unpack_from('<Ii', md, sl_off + 8 * i)
        if ln == 10794:
            return md[sld_off + idx:sld_off + idx + ln].decode('utf-8')
    raise SystemExit('charset literal not found')

T = load_table()

# ---------------- UTXT ----------------
def utxt_records(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'UTXT', d[:4]
    table_end = struct.unpack_from('<I', d, 0x0C)[0]
    assert d[table_end - 4:table_end] == b'TEND'
    tbl = d[0x10:table_end - 4]
    vals, v = [], 0
    for x in tbl:
        v = (v << 7) | (x & 0x7f)
        if not x & 0x80:
            vals.append(v); v = 0
    cnt = vals[0]
    lens = vals[1:1 + cnt]
    assert sum(lens) == len(d) - table_end, (sum(lens), len(d) - table_end)
    o, out = table_end, []
    for L in lens:
        out.append(d[o:o + L]); o += L
    return out, len(d), table_end

def decode(buf):
    out, i, n, oob = [], 0, len(buf), 0
    while i < n:
        b = buf[i]
        if b == 0:
            out.append('\n'); i += 1
        elif b < 0x80:
            out.append(T[b - 1]); i += 1
        else:
            if i + 1 >= n:
                oob += 1; i += 1; out.append('〔未解析〕'); continue
            k = (b - 0x81) * 128 + (buf[i + 1] - 1) + 128
            i += 2
            if 0 <= k < len(T):
                out.append(T[k])
            else:
                oob += 1; out.append('〔未解析〕')
    return ''.join(out), oob

# ---------------- MonoBehaviour 字面量 ----------------
def raw_strings(raw, maxlen=20000):
    """u32 长度前缀 + 严格 UTF-8 字符串序列（无 \x00、无替换符）。"""
    out, n, i = [], len(raw), 0
    while i + 4 <= n:
        ln = struct.unpack_from('<I', raw, i)[0]
        if 1 <= ln <= maxlen and i + 4 + ln <= n:
            b = raw[i + 4:i + 4 + ln]
            if b'\x00' not in b:
                try:
                    s = b.decode('utf-8')
                    if '\ufffd' not in s:
                        out.append(s); i += 4 + ln; continue
                except Exception:
                    pass
        i += 1
    return out

def mb_raw(path_id):
    import UnityPy
    env = UnityPy.load(UNITY)
    for obj in env.objects:
        if obj.path_id == path_id and obj.type.name == 'MonoBehaviour':
            return obj.get_raw_data()
    raise SystemExit('MonoBehaviour %d not found' % path_id)

PHONE_KEY = re.compile(r'^(?:mailText|dm)_\d{4}_\d{2}_\d{2}$')

def phone_map():
    ss = raw_strings(mb_raw(436))
    m, i = {}, 0
    while i < len(ss):
        if PHONE_KEY.match(ss[i]) and i + 1 < len(ss):
            m[ss[i]] = ss[i + 1]; i += 2
        else:
            i += 1
    return m

# ContentsDatabase 结构（逐条实测）：ID(ASCII) → 标题 → カテゴリ → 解説
CATEG = re.compile(r'^(?:CHAPTER \d|PROLOGUE|LIMBO Side:[AB]|SHU Side:[AB]|HELVETICA Side:[AB]|'
                  r'MOZU Side:[AB]|SCARECROW Side:[AB]|FULL CIRCLE|AULD LANG SYNE|JOKER|'
                  r'Patent Troll|One and Only|Wrong Number|Fleeting Joy|Chain Smoker|'
                  r'Meatloaf|Meat Sauce|Ceviche|Chop Suey|Hamburg Steak)$')
KANA = re.compile(r'[\u3041-\u309f]')
PLACEHOLDER = re.compile(r'^(?:あいうえお)+$')

def memorabilia():
    """返回 [(カテゴリ, 标题, 解説)]，结构 = 标题 / カテゴリ / 解説。"""
    ss = raw_strings(mb_raw(429))
    out = []
    for i in range(1, len(ss) - 1):
        if not CATEG.match(ss[i]):
            continue
        desc = ss[i + 1]
        if len(desc) < 60 or not KANA.search(desc) or PLACEHOLDER.match(desc):
            continue
        title = ss[i - 1].strip()
        if PLACEHOLDER.match(title) or len(title) > 60:
            title = None
        out.append((ss[i], title, desc))
    return out

# ---------------- 过滤 ----------------
RES_ID = re.compile(r'^(?:bg|ch|cg|ev|se|bgm|cut|ui|emo|body|face|mask|scene|mv|snd|voice|'
                    r'phone-screen|mail-screen|rec-screen|trophy|image|emoji|sk_ep0)[_-]', re.I)
SCREEN = re.compile(r'^(?:phone-screen\d*|mail-screen\d*|rec-screen\d*)$')

def norm(s):
    return s.replace('\r\n', '\n').replace('\r', '')

def flatten(s):
    return re.sub(r'\n\u3000?', '', s)

def main():
    os.makedirs(WORK, exist_ok=True)
    recs, fsize, tbl_end = utxt_records(TEXT)
    texts, oob = [], 0
    for r in recs:
        s, o = decode(r)
        oob += o
        texts.append(s)
    print('UTXT %d B / table_end %d / records %d / OOB %d' % (fsize, tbl_end, len(texts), oob))

    pmap = {k: flatten(norm(v)) for k, v in phone_map().items()}
    mem = memorabilia()
    print('phone db %d / memorabilia %d' % (len(pmap), len(mem)))

    # 说话人/界面名：结构判定＝「紧接界面 ID 之后」或「紧邻短信 ID 之前」的纯拉丁记录
    stripped = [flatten(t).strip() for t in texts]
    latin = re.compile(r'^[A-Za-z][A-Za-z0-9 \'\.]*$')
    name_set = set()
    for i, s in enumerate(stripped):
        if not latin.match(s):
            continue
        prev = stripped[i - 1] if i else ''
        nxt = stripped[i + 1] if i + 1 < len(stripped) else ''
        if SCREEN.match(prev) or PHONE_KEY.match(nxt):
            name_set.add(s)
    print('speaker/ui names (%d): %s' % (len(name_set), sorted(name_set)))

    # 资源名：\d{2,3}_ 前缀 + 资源清单里的 basename
    res_names = set()
    for fn in os.listdir(SA):
        if not (fn.startswith('sk_ep0_') and fn.endswith('.txt')):
            continue
        for line in open(os.path.join(SA, fn), encoding='utf-8', errors='replace').read().split('\n'):
            line = line.strip()
            if not line:
                continue
            res_names.add(line)
            res_names.add(re.sub(r'^[a-z]{2,4}[_-]', '', line, flags=re.I))
            res_names.add(re.sub(r'^\d{2,3}_', '', line))

    # 来电名牌：全大写拉丁，且夹在两条引号台词中间（上一记录以 」 收尾、下一记录以 「 开头）
    caps = re.compile(r"^[A-Z][A-Z0-9' ]{0,24}$")
    for i, s in enumerate(stripped):
        if not caps.match(s) or i == 0 or i + 1 >= len(stripped):
            continue
        if stripped[i - 1].endswith(('」', '』')) and stripped[i + 1].startswith(('「', '『')):
            name_set.add(s)


    drop = collections.Counter()
    samples = collections.defaultdict(list)
    lines = []
    prev_raw = None

    for i, t in enumerate(texts):
        raw_s = flatten(t).strip()
        if not raw_s:
            drop['blank'] += 1
            continue
        # 1) 短信/私信 ID → 正文来自 PhoneMessageContentsDatabase
        if PHONE_KEY.match(raw_s):
            body = pmap.get(raw_s)
            if body:
                if lines and lines[-1] == body:
                    drop['phone_id_inline_dup'] += 1
                else:
                    lines.append(body)
                    drop['phone_id_resolved'] += 1
            else:
                drop['phone_id_no_content'] += 1
                samples['phone_id_no_content'].append(raw_s)
            continue
        # 2) 资源 ID（trophy_/cg_/scene_/mv_ 等）
        if RES_ID.match(raw_s):
            drop['res_id'] += 1
            samples['res_id'].append(raw_s)
            continue
        # 3) 手机/邮件界面 ID
        if SCREEN.match(raw_s):
            drop['screen_id'] += 1
            samples['screen_id'].append(raw_s)
            continue
        # 4) 资源名（含 \d{2,3}_ 前缀与资源清单 basename）
        if raw_s in res_names or re.fullmatch(r'\d{2,3}_[^ ]*', raw_s):
            drop['res_name'] += 1
            samples['res_name'].append(raw_s)
            continue
        # 5) 发信人名/界面名（结构判据：紧接界面 ID 之后，或紧邻短信 ID 之前）
        if raw_s in name_set:
            drop['sender_ui'] += 1
            samples['sender_ui'].append(raw_s)
            continue
        # 6) 正文（不改写：源数据的两处半角收尾符 ] / ) 属原文缺陷，保留并登记 allow）
        s = raw_s.replace('（名前）', HERO)
        # 互斥双写折叠：相邻两条源记录，归一后相同但源字节不同
        # （默认名「テウタ」版 ／ 自定义名「（名前）」版，玩家只会看到其一）
        if lines and s == lines[-1] and raw_s != prev_raw:
            drop['name_variant_dup'] += 1
            prev_raw = raw_s
            continue
        lines.append(s)
        prev_raw = raw_s

    extra = ['■エクストラ（メモラビリア／コレクション解説）']
    for cat, title, desc in mem:
        b = flatten(norm(desc)).strip()
        extra.append('【%s】%s' % (title, b) if title else b)

    out = '\ufeff' + '\n'.join(lines + extra) + '\n'
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    open(DEST, 'w', encoding='utf-8', newline='\n').write(out)

    print('kept %d + extras %d = %d lines' % (len(lines), len(extra), len(lines) + len(extra)))
    print('dropped', dict(drop))
    for k in ('phone_id_no_content', 'res_id', 'screen_id', 'sender_ui', 'res_name'):
        u = sorted(set(samples[k]))
        print('-- %s uniq %d --' % (k, len(u)))
        print('   ', u[:25])
    print('bytes', len(out.encode('utf-8')))
    print('wrote', DEST)

if __name__ == '__main__':
    main()
