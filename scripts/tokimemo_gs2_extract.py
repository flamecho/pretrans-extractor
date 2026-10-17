#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ときめきメモリアル Girl's Side 2nd Season (NS-JP, Unity) 全文本提取器。

引擎要点（reverse-engineered 2026-10-15）：
1. 剧本 = RomFS `Data/StreamingAssets/scenario/<a-z>/<name>.assetbundle`（Unity AssetBundle，
   内含 1 个 TextAsset `*.bytes`）。
2. `.bytes` 结构 = [28B 头][代码区 4B/指令][字符串池]：
   - 头 = 7 个 u32 LE：<16><poolOff><poolOff><poolOff><1><773><772>；
     poolOff = 字符串池相对文件偏移（= 表首）。
   - 代码区 = 从 0x1C 到 poolOff，每条指令 4B = <u8 A><u8 B><u16 BE 参数>。
   - 指令 `05 03 <u16>` = 引用字符串池（参数 = 池内偏移）。
   - 消息块 = `0316 … 0317`；块内 `0503` 序列：
       * `0316 0503 0400 0503 0317`（后面跟 `0402 0104`）= **选项块**（0503 全是选项）
       * `0316 0503 0400 0503 0317`（其他）= **名札+正文**（第 1 个=说话人名，第 2 个=正文）
       * 其余骨架（0503=语音 ID / 资源 ID）无正文
3. 字符串池：每条以原始 `0x00` 分隔；每条用一个**随池内起始偏移变化的 XOR 键**
   `K(off) = 0x3C ^ ((off & 0xC0) | (off & 0x03))` 解码；
   解码结果中的 `0x00` 字节表示「原文该字节 == K」（被编码器规避）⇒ 还原为 K。
4. 文本 = UTF-8；`\n`（反斜杠+n）为框内换行；`@@` 为排版断行；`▼` 为「继续」提示符。
5. `｛X＊＊｝` = 角色名变量（X = 姓氏）；`｛主人公…｝` = 主角名（默认「主人公」）。
   历史遗留：`∋`≡`？`、`∈`≡`！`（同一句两种写法实证，见解析报告）。

用法:
  python scripts/tokimemo_gs2_extract.py <romfs_dir> [-o OUT.txt]
         [--no-skinship] [--no-net] [--keep-markers]
"""
import argparse, glob, json, os, re, struct, sys

# ---------- 文本清洗 ----------
VAR_MAP = {'日付': '〔日付〕', '待ち合わせ場所': '〔待ち合わせ場所〕', '流行アクセサリ名': '〔流行アクセサリ名〕'}
JPRE = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u2000-\u206f\u2190-\u21ff\u2460-\u24ff\u25a0-\u25ff]')
BRACE = re.compile(r'｛([^｝]*)｝')
DOTRUN = re.compile(r'．{2,}')
# ★ 主角名（交付口径 2026-10-15：用户指定「用 vndb 上的主角名」）
#   `｛主人公｝`(氏名)/`｛主人公姓名｝`/`｛主人公苗字｝`(姓)/`｛主人公名前｝`(名) 皆玩家自定名槽位；
#   相邻「苗字+名前」（可含 1 个分隔符）合并为一个名字，避免「「X」X」。
PROTAG_NAME = 'デイジー'
_SEP = r'(?:[、\u3000 ]|\\n|[\r\n])*'
PAIR = re.compile(r'｛主人公苗字｝' + _SEP + r'｛主人公名前｝'
                  r'|｛主人公名前｝' + _SEP + r'｛主人公苗字｝')


def clean_text(s, keep_markers=False):
    s = s.replace('∋', '？').replace('∈', '！')          # 历史遗留变体（实证见解析报告）
    s = s.replace('\uff65', '・')
    s = s.replace('(', '（').replace(')', '）')       # 半角括号 -> 全角（源数据偶见混用）
    s = DOTRUN.sub(lambda m: '…' * max(1, len(m.group()) // 3), s)   # 「．．．」= 省略号记号
    s = PAIR.sub(PROTAG_NAME, s)                                   # 姓+名 相邻 ⇒ 合并为一个主角名

    def rep(m):
        v = m.group(1)
        if v.startswith('強調'):
            v = v[2:]                     # 样式标记「強調」（仅はばたきネット内容出现）
        if v.endswith('＊＊'):            # ｛佐伯＊＊｝ = 角色名（称呼形式）
            return v[:-2]
        if v.startswith('主人公'):        # 主角名（vndb 口径，同时覆盖 姓名/苗字/名前）
            return PROTAG_NAME
        return '〔' + v + '〕'            # 运行时变量（日付/待ち合わせ場所/流行＊名/学年…）
    s = BRACE.sub(rep, s)
    if s.strip() == '主人公':                     # 裸字面（非宏）＝「显示主角名」的块
        return PROTAG_NAME
    if not keep_markers:
        s = s.replace('▼', '')
    s = s.replace('\\n', '').replace('@@', '')   # 框内换行 / 排版断行 -> 合并
    s = s.replace('\r', '').replace('\n', '')    # JSON 里解析出的真实换行同样合并
    if s and set(s.replace('\u3000', '').replace(' ', '')) <= {'・'}:
        return ''                          # 纯装饰行（・＋全角空格，画面「幕」）
    s = s.strip()
    if '）' in s and '（' not in s and not s.startswith('）'):
        s = '（' + s                              # 源数据缺开括号（唯一一处：j03_m5_010）
    return s


def is_content(s):
    """至少含 1 个日文字符（排除纯 ASCII 资源 ID/说话人标签）。"""
    s = s.strip()
    return bool(s) and ('\ufffd' not in s) and bool(JPRE.search(s))


# ---------- 块分类（★2026-10-15 修订：与 GS3 统一口径）----------
# 旧版「块后 `0402` 再跟 `0104` ⇒ 选项块」在本系作品并不完整：
#   ① 名札+正文块也可能带 `0104`（会把名札当选项，泄漏成品行）；
#   ② 2 选项块可能不带 `0104`（会丢选项）。
# 故改按「`0503` 个数 + `ops[0]` 是否名札」分类（细则见报告与 skill `00c3`）。
DIAL_MARK = set('「」（）()。！？…―～♪∋∈▼、!?')
OPTION_ONLY = {'大学を受験する', '就職試験を受ける'}
KANA_END = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]$')
DUMMY_SPEAKER = {'ダミー', 'デバッグ', 'テスト', 'セリフ', 'サンプル'}
IDRE = re.compile(r'^[A-Za-z0-9_]+$')
DECO = re.compile(r'^[\u3000\u30fb]+$')
SENT = re.compile(r'[。！？…、\n]')


def _strip_style(s):
    """剥名札样式前缀（？＊！∈∋♪…）。"""
    while s and s[0] in '？＊！∈∋♪…':
        s = s[1:]
    return s


def is_name_plate(s):
    t = _strip_style(s)
    if not t or len(t) > 9:
        return False
    if t in OPTION_ONLY:
        return False
    if SENT.search(t) or t.startswith('（') or t.startswith('｛'):
        return False
    return True


def is_option_pair(ops):
    """两项皆「无对话标记的短语」⇒ 选项对（避免把选项误当名札+正文）。"""
    if not (is_name_plate(ops[0]) and is_name_plate(ops[1])):
        return False
    return not any(c in DIAL_MARK for c in ops[1])


def is_display_text(s):
    """可上屏文本（排除资源 ID / 数字标签 / 装饰行）。"""
    t = s.replace('\\n', '').replace('\n', '').strip()
    if not t or IDRE.match(t) or t.isdigit() or DECO.match(t):
        return False
    return bool(JPRE.search(t))


# ---------- .bytes 解析 ----------


# ---------- 说话人白名单（★2026-10-15：修 0104 名札泄漏）----------
# 「ops[0] 在 2-op 块中与 ≥2 个**不同** ops[1] 共现」⇒ 判为真名札（人物/角色名）。
# 反例（会被排除）：选项短语 `話を聞いてもらう`／`そうかも`／`鐘を鳴らす` —— 各自只对应 1 个 ops[1]。
CODE_OFF = 0x1c
PLATE_SET = set()


def _iter_blocks(raw):
    """yield (ops, n2)：ops = 块内 0503 引用串，n2 = 0317 之后第二条指令。"""
    if len(raw) < 0x40:
        return
    try:
        pool_off = struct.unpack('<7I', raw[:28])[1] if CODE_OFF == 0x1C else struct.unpack('<I', raw[4:8])[0]
    except Exception:
        return
    if not (CODE_OFF <= pool_off < len(raw)):
        return
    pool = raw[pool_off:]
    smap = {}
    pos = 0
    while pos < len(pool):
        e = pool.find(b'\x00', pos)
        if e < 0:
            e = len(pool)
        K = key_of(pos)
        smap[pos] = bytes(b ^ K for b in pool[pos:e]).replace(b'\x00', bytes([K])).decode('utf-8', 'replace')
        pos = e + 1
    code = raw[CODE_OFF:pool_off]
    ins = [(code[k], code[k + 1], (code[k + 2] << 8) | code[k + 3]) for k in range(0, len(code) - 3, 4)]
    i = 0
    while i < len(ins):
        if (ins[i][0], ins[i][1]) == (3, 0x16):
            j = i
            ops = []
            while j < len(ins) and (ins[j][0], ins[j][1]) != (3, 0x17):
                if (ins[j][0], ins[j][1]) == (5, 3):
                    ops.append(smap.get(ins[j][2], ''))
                j += 1
            n2 = ins[j + 2] if j + 2 < len(ins) else (0, 0, 0)
            yield ops, n2
            i = j
        else:
            i += 1


def _read_textasset(path):
    import UnityPy
    try:
        env = UnityPy.load(path)
    except Exception:
        return None
    for o in env.objects:
        if o.type.name == 'TextAsset':
            d = o.read()
            raw = d.m_Script
            if isinstance(raw, str):
                raw = raw.encode('utf-8', 'surrogateescape')
            return raw
    return None


def precompute_plate_set(romfs):
    """说话人白名单（游戏自带表，非启发式）：
    `string_table` 的 `AdvNameCh*`（ADV 名札表）＋ `ExtraProfileCh_*` / `AddressBookAddress_*`
    拆出的**姓与名** ＋ 固定 `主人公`。用于区分「名札+正文」与「2 选项」
    （选项短语如 `話を聞いてもらう`／`嬉しいです`／`はい、大丈夫です` 均不在表内）。
    """
    p = os.path.join(romfs, 'Data', 'StreamingAssets', 'lang', 'ja', 'initialize.assetbundle')
    names = {'主人公'}
    if not os.path.exists(p):
        return names
    import UnityPy
    try:
        env = UnityPy.load(p)
    except Exception:
        return names
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        if getattr(d, 'm_Name', '') != 'string_table':
            continue
        s = d.m_Script
        if isinstance(s, str):
            s = s.encode('utf-8', 'surrogateescape')
        try:
            st = json.loads(s.decode('utf-8', 'replace'), strict=False)
        except Exception:
            return names
        for k, v in st.items():
            if not isinstance(v, str) or not v.strip():
                continue
            if k.startswith('ExtraProfileCh_') or k.startswith('AddressBookAddress_'):
                for part in re.split(r'[\u3000 ]+', v.strip()):
                    if part and not any(c in part for c in '｛｝＠'):
                        names.add(part)
            elif k.startswith('AdvName'):
                names.add(v.strip())
        break
    return names


def key_of(off):
    return 0x3C ^ ((off & 0xC0) | (off & 0x03))


def parse_bytes(raw):
    if len(raw) < 0x40:
        return []
    try:
        pool_off = struct.unpack('<7I', raw[:28])[1]
    except Exception:
        return []
    if not (0x1C <= pool_off < len(raw)):
        return []
    pool = raw[pool_off:]
    smap = {}
    pos = 0
    while pos < len(pool):
        e = pool.find(b'\x00', pos)
        if e < 0:
            e = len(pool)
        K = key_of(pos)
        smap[pos] = bytes(b ^ K for b in pool[pos:e]).replace(b'\x00', bytes([K])).decode('utf-8', 'replace')
        pos = e + 1
    code = raw[0x1C:pool_off]
    instrs = [(code[k], code[k + 1], (code[k + 2] << 8) | code[k + 3]) for k in range(0, len(code) - 3, 4)]
    out = []
    i = 0
    while i < len(instrs):
        op, sub, arg = instrs[i]
        if (op, sub) == (3, 0x16):
            j = i
            ops = []
            while j < len(instrs):
                o2, s2, a2 = instrs[j]
                if (o2, s2) == (3, 0x17):
                    break
                if (o2, s2) == (5, 3):
                    ops.append(smap.get(a2, ''))
                j += 1
            if ops and _strip_style(ops[0]) in DUMMY_SPEAKER:   # 占位说话人（台词实为脚本注释）
                i = j
                continue
            if len(ops) == 1:                     # 无说话人的旁白/结局叙述
                if is_display_text(ops[0]):
                    out.append(('text', ops[0]))
            elif len(ops) >= 3:                   # 选项块（3 项以上）
                for s in ops:
                    if is_content(s):
                        out.append(('choice', s))
            elif len(ops) == 2:
                n2 = instrs[j + 2] if j + 2 < len(instrs) else (0, 0, 0)
                p0 = _strip_style(ops[0])
                at_choice = (n2[0], n2[1]) == (1, 4)
                # 名札判据：① 在游戏自带名表；② 名札形且**不以假名收尾**（台词/选项多以「です/ます/う/か」收尾，
                # 角色名多以汉字收尾）；③ 非 0104 块沿用旧口径（ops[0] 名札形）。
                nameish = is_name_plate(ops[0]) and not KANA_END.search(p0.rstrip('▼＊'))
                if (p0 in PLATE_SET or nameish
                        or (not at_choice and not is_option_pair(ops) and is_name_plate(ops[0]))):
                    if is_content(ops[1]):
                        out.append(('text', ops[1]))
                else:
                    for s in ops:
                        if is_content(s):
                            out.append(('choice', s))
            i = j
        else:
            i += 1
    return out


# ---------- 各来源抽取 ----------
def iter_scenario(romfs):
    root = os.path.join(romfs, 'Data', 'StreamingAssets', 'scenario')
    for p in sorted(glob.glob(os.path.join(root, '*', '*.assetbundle'))):
        yield p


def extract_scenario(romfs):
    global PLATE_SET
    PLATE_SET = precompute_plate_set(romfs)
    import UnityPy
    lines = []
    for p in iter_scenario(romfs):
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        raw = None
        for o in env.objects:
            if o.type.name == 'TextAsset':
                d = o.read()
                raw = d.m_Script
                if isinstance(raw, str):
                    raw = raw.encode('utf-8', 'surrogateescape')
                break
        if raw is None:
            continue
        for kind, s in parse_bytes(raw):
            t = clean_text(s)
            if t:
                lines.append(t)
    return lines


def extract_skinship(romfs):
    import UnityPy
    p = os.path.join(romfs, 'Data', 'StreamingAssets', 'lang', 'ja', 'initialize.assetbundle')
    out = []
    if not os.path.exists(p):
        return out
    env = UnityPy.load(p)
    names = []
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        n = getattr(d, 'm_Name', '')
        if n.startswith('skinship_dialogue_'):
            names.append((n, d.m_Script))
    names.sort(key=lambda x: x[0])
    for n, s in names:
        if isinstance(s, str):
            s = s.encode('utf-8', 'surrogateescape')
        try:
            j = json.loads(s.decode('utf-8'))
        except Exception:
            continue
        for tb in j.get('Tables', []):
            for rec in tb.get('Records', []):
                for par in rec.get('Params', []):
                    for dt in par.get('DlgText', []):
                        t = clean_text(dt)
                        if t:
                            out.append(t)
    return out


HABATA_KEYS = ('Title', 'Commentary', 'Arg0', 'Arg1', 'ContentsName', 'Caption', 'Text')


def _walk_habata(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in HABATA_KEYS and isinstance(v, str):
                t = clean_text(v)
                if t and is_content(t):
                    out.append(t)
            else:
                _walk_habata(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_habata(v, out)


def extract_net(romfs):
    import UnityPy
    p = os.path.join(romfs, 'Data', 'StreamingAssets', 'lang', 'ja', 'initialize.assetbundle')
    out = []
    if not os.path.exists(p):
        return out
    env = UnityPy.load(p)
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        n = getattr(d, 'm_Name', '')
        if not n.startswith('habatakinet_'):
            continue
        s = d.m_Script
        if isinstance(s, str):
            s = s.encode('utf-8', 'surrogateescape')
        try:
            j = json.loads(s.decode('utf-8'))
        except Exception:
            continue
        _walk_habata(j, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('romfs')
    ap.add_argument('-o', '--out', default='out.txt')
    ap.add_argument('--no-skinship', action='store_true')
    ap.add_argument('--no-net', action='store_true')
    ap.add_argument('--keep-markers', action='store_true')
    args = ap.parse_args()

    lines = extract_scenario(args.romfs)
    parts = []
    parts += lines
    sk = net = []
    if not args.no_skinship:
        sk = extract_skinship(args.romfs)
        parts += sk
    if not args.no_net:
        net = extract_net(args.romfs)
        parts += net
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(parts) + '\n')
    print(f'scenario={len(lines)} skinship={len(sk) if not args.no_skinship else 0} '
          f'net={len(net) if not args.no_net else 0} total={len(parts)}')


if __name__ == '__main__':
    main()
