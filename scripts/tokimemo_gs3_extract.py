#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ときめきメモリアル Girl's Side 3rd Story for Nintendo Switch (NS-JP, Unity) 全文本提取器。

引擎：KONAMI 自研 Unity `.bytes` 字节码（同 GS1/GS2；reverse-engineered 2026-10-15 本作复核）。
与 GS1/GS2 的**实质差异**（详见解析报告 §3）：
  1. **头 = 4×u32 LE（16 B）**；代码区自 **0x10** 起（GS1/GS2 为 7×u32＝0x1C 起）。
  2. `.bytes` 头魔数不再固定（GS1/GS2 的 `(…,1,773,772)` 不适用）⇒ 仅校验
     `poolOff = u32@4`、`0x10 <= poolOff < len`。
  3. **块分类改判**（GS1/GS2 的「块后 `0402` + `0104`＝选项」在 GS3 只覆盖一部分）：
     - `ops == 0` → 丢（语音/资源骨架）
     - `ops == 1` → **正文**（无说话人的旁白/结局叙述）—— 判据：非资源 ID、非装饰、含日文
     - `ops >= 3` → **选项块**（全部收）
     - `ops == 2` → `post2 == (1,4)` ⇒ 选项块；否则 `ops[0]` 为名札 ⇒ 名札+正文（只收 ops[1]），
       否则 ⇒ 选项块（两项全收）
  4. 名札带**样式前缀** `？`（如 `？琉夏`）⇒ 判名札前先剥前缀（名札本身不入正文）。
  5. 附加文本源：根 `initialize.assetbundle` 的 `ss_rct_*` / `nss_rct_*` / `wnss_rct_*` / `sstuto_rct`
     之 `StrData` ＝ スキンシップ（触摸）台词；行内换行标记为 `**LF**`（GS1/GS2 为 `\n`）。
  6. `lang/ja/initialize.assetbundle` 的 `habatakinet_*` ＝ はばたきネット 读文（同 GS1/GS2）。

字符串池：同 GS1/GS2 —— 每条以原始 0x00 分隔，键 `K(off) = 0x3C ^ ((off & 0xC0) | (off & 0x03))`，
解码结果中的 0x00 还原为 K。

用法:
  python scripts/tokimemo_gs3_extract.py <romfs_dir> [-o OUT.txt]
         [--no-skinship] [--no-net] [--keep-markers]
"""
import argparse
import glob
import json
import os
import re
import struct

# ---------- 文本清洗 ----------
VAR_MAP = {}
BRACE = re.compile(r'｛([^｝]*)｝')
DOTRUN = re.compile(r'．{2,}')
TAG = re.compile(r'\*\*[A-Za-z0-9_]+\*\*')     # 富文本标记（**LF** 等）
# ★ 主角名（交付口径，2026-10-15 用户指定「用 vndb 上的主角名」）：
#   vndb `v2956` 主角 = 「バンビ」(Bambi)，描述「the protagonist, nicknamed "Bambi" by her friend Karen」
#   （别名 Protagonist／主人公）。剧本里的 `｛主人公｝`(氏名) / `｛主人公苗字｝`(姓) / `｛主人公名前｝`(名)
#   皆为玩家自定名的槽位，游戏内**无默认姓名**（EntryProfile 预制体只有示例占位「ああああ　ああああ」，
#   唯一默认值＝`string_table.ExtraProfilePlayerName="主人公"`，IL2CPP 元数据的变量名仅 `主人公姓名/苗字/名前`）。
#   故三槽统一填主角名；**相邻的「苗字＋名前」（可含 1 个分隔符）合并为一个名字**，避免「バンビバンビ」。
PROTAG_NAME = 'バンビ'
_SEP = r'(?:[、\u3000 \u3000]|\\n|[\r\n])*'
PAIR = re.compile(r'｛主人公苗字｝' + _SEP + r'｛主人公名前｝'
                  r'|｛主人公名前｝' + _SEP + r'｛主人公苗字｝')
JPRE = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff00-\uffef'
                  r'\u2000-\u206f\u2190-\u21ff\u2460-\u24ff\u25a0-\u25ff]')
IDRE = re.compile(r'^[A-Za-z0-9_]+$')
DECO = re.compile(r'^[\u3000\u30fb]+$')
SENT = re.compile(r'[。！？…、\n]')


def clean_text(s, keep_markers=False):
    s = s.replace('∋', '？').replace('∈', '！')      # 历史遗留变体（GS2 实证；GS3 亦有）
    s = s.replace('\uff65', '・')
    s = s.replace('(', '（').replace(')', '）')       # 半角括号 -> 全角（源数据偶见混用）
    s = TAG.sub('', s)                                # **LF** ＝ 框内换行 -> 合并
    s = DOTRUN.sub(lambda m: '…' * max(1, len(m.group()) // 3), s)
    s = PAIR.sub(PROTAG_NAME, s)                      # 姓+名 相邻 ⇒ 合并为一个主角名

    def rep(m):
        v = m.group(1)
        if v.startswith('強調'):
            v = v[2:]
        if v.endswith('＊＊'):
            return v[:-2]                             # ｛設楽＊＊｝ = 角色名（称呼形式）
        if v.endswith('＊') and not v.startswith('主人公') and len(v) > 1:
            return v[:-1]
        if v.startswith('主人公'):                     # 主人公／主人公姓名／主人公苗字／主人公名前
            return PROTAG_NAME
        return '〔' + v + '〕'                        # 运行期变量
    s = BRACE.sub(rep, s)
    if s.strip() == '主人公':                          # 裸字面（非宏）＝「显示主角名」的块
        return PROTAG_NAME
    if not keep_markers:
        s = s.replace('▼', '')
    s = s.replace('\\n', '').replace('@@', '')
    s = s.replace('\r', '').replace('\n', '')
    if s and set(s.replace('\u3000', '').replace(' ', '')) <= {'・'}:
        return ''                          # 纯装饰行（・＋全角空格，画面「幕」）
    return s.strip()


def is_content(s):
    """至少含 1 个日文字符（排除纯 ASCII 资源 ID / 说话人标签）。"""
    s = s.strip()
    return bool(s) and ('\ufffd' not in s) and bool(JPRE.search(s))


# ---------- .bytes 解析 ----------


# ---------- 说话人白名单（★2026-10-15：修 0104 名札泄漏）----------
# 「ops[0] 在 2-op 块中与 ≥2 个**不同** ops[1] 共现」⇒ 判为真名札（人物/角色名）。
# 反例（会被排除）：选项短语 `話を聞いてもらう`／`そうかも`／`鐘を鳴らす` —— 各自只对应 1 个 ops[1]。
CODE_OFF = 0x10
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


def _strip_style(s):
    """剥名札样式前缀（？＊！∈∋♪…）。"""
    while s and s[0] in '？＊！∈∋♪…':
        s = s[1:]
    return s


# 对话标记：出现即说明是台词（而非选项短语）。
DIAL_MARK = set('「」（）()。！？…―～♪∋∈▼、!?')
# 2 op 均为「无对话标记短语」时若 ops[0] 落在这个表里，则是「选项对」而非名札
# （全量扫描本作 2-op 块得出；「大学を受験する／やめて、就職試験を受ける」一项含
#  「、」故不满足上句判据，须单列）。
OPTION_ONLY = {'大学を受験する', '就職試験を受ける'}
# 占位说话人（其「台词」实为脚本注释/工程串）⇒ 整块丢弃。
KANA_END = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]$')
DUMMY_SPEAKER = {'ダミー', 'デバッグ', 'テスト', 'セリフ', 'サンプル'}


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
    """2 op 都是「无对话标记的短语」⇒ 选项对（如「鐘を鳴らす／鐘を鳴らさない」）。

    名札＋正文的 ops[1] 一定带「」（）等标记或以 ∋∈♪ 收尾；仅此二者皆无标记时才判选项。
    """
    if not (is_name_plate(ops[0]) and is_name_plate(ops[1])):
        return False
    return not any(c in DIAL_MARK for c in ops[1])


def is_display_text(s):
    """可上屏文本（排除资源 ID / 数字标签 / 装饰行）。"""
    t = s.replace('\\n', '').replace('\n', '').strip()
    if not t or IDRE.match(t) or t.isdigit() or DECO.match(t):
        return False
    return bool(JPRE.search(t))


def parse_bytes(raw):
    if len(raw) < 0x40:
        return []
    pool_off = struct.unpack('<I', raw[4:8])[0]
    if not (0x10 <= pool_off < len(raw)):
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
    code = raw[0x10:pool_off]
    instrs = [(code[k], code[k + 1], (code[k + 2] << 8) | code[k + 3])
              for k in range(0, len(code) - 3, 4)]
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
            n2 = instrs[j + 2] if j + 2 < len(instrs) else (0, 0, 0)
            if ops and _strip_style(ops[0]) in DUMMY_SPEAKER:
                i = j
                continue
            if len(ops) == 1:
                if is_display_text(ops[0]):
                    out.append(('text', ops[0]))
            elif len(ops) >= 3:
                for s in ops:
                    if is_content(s):
                        out.append(('choice', s))
            elif len(ops) == 2:
                # ★ 本作不能用「块后 0104」判 2 选项：实测 25 个 名札+正文 块（全部 ops[0]==主人公，
                #   n2==(1,4)）会被误判成选项 ⇒ 名札判定优先于 0104。
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
# 调试专用脚本（SCENARIO 相对路径，无扩展名）：v00_00_000/001 = 命令テスト菜单，
# 内容全为「〜テスト／他のテストを行う／存在しないキャラ／目：普通」等内部项 ⇒ 整体排除。
SKIP_SCENARIO = {'v/v00_00_000', 'v/v00_00_001'}
# 调试/占位串（散落在正式剧本里的错误回退、実績占位标签、脚本名注释行）⇒ 逐行剔除。
JUNK_LINE = re.compile(r'バイト実績イベント'
                       r'|デバッグキャラIDに不正な値が入っています'
                       r'|^アルバイト実績イベント(成功|失敗)$'
                       r'|[A-Za-z]{1,2}\d{2}_\d{2}_\d{3}')        # 「Q31_01_000修学旅行…」式脚本注释


def iter_scenario(romfs):
    root = os.path.join(romfs, 'Data', 'StreamingAssets', 'scenario')
    for p in sorted(glob.glob(os.path.join(root, '*', '*.assetbundle'))):
        key = os.path.relpath(p, root).replace('\\', '/')
        if key[:-len('.assetbundle')] in SKIP_SCENARIO:
            continue
        yield p


def extract_scenario(romfs, keep_markers=False):
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
        for _kind, s in parse_bytes(raw):
            t = clean_text(s, keep_markers)
            if t and not JUNK_LINE.search(t):
                lines.append(t)
    return lines


SKINSHIP_TABLES = ('ss_rct_', 'nss_rct_', 'wnss_rct_', 'sstuto_rct')
LABEL_BLACKLIST = {'共通反応', 'ダミー', 'デバッグ', 'テスト', 'セリフ', 'シート名'}


def _walk_key(obj, key, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, str):
                out.append(v)
            else:
                _walk_key(v, key, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_key(v, key, out)


def _textassets(romfs, rel):
    import UnityPy
    p = os.path.join(romfs, 'Data', 'StreamingAssets', rel)
    out = []
    if not os.path.exists(p):
        return out
    for o in UnityPy.load(p).objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        s = d.m_Script
        if isinstance(s, str):
            s = s.encode('utf-8', 'surrogateescape')
        out.append((getattr(d, 'm_Name', ''), s))
    return out


def extract_skinship(romfs, keep_markers=False):
    """スキンシップ台词：根 initialize.assetbundle 的 ss/nss/wnss/sstuto_rct 之 StrData。"""
    out = []
    for name, s in sorted(_textassets(romfs, 'initialize.assetbundle')):
        if not name.startswith(SKINSHIP_TABLES):
            continue
        try:
            j = json.loads(s.decode('utf-8'))
        except Exception:
            continue
        vals = []
        _walk_key(j, 'StrData', vals)
        for v in vals:
            if not v.strip() or v.strip() in LABEL_BLACKLIST:
                continue
            t = clean_text(v, keep_markers)
            if t:
                out.append(t)
    return out


HABATA_KEYS = ('Title', 'Commentary', 'Arg0', 'Arg1', 'ContentsName', 'Caption', 'Text')


def _walk_habata(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in HABATA_KEYS and isinstance(v, str):
                if v.strip():
                    out.append(v)
            else:
                _walk_habata(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_habata(v, out)


def extract_net(romfs, keep_markers=False):
    out = []
    for name, s in sorted(_textassets(romfs, os.path.join('lang', 'ja', 'initialize.assetbundle'))):
        if not name.startswith('habatakinet_'):
            continue
        try:
            j = json.loads(s.decode('utf-8'))
        except Exception:
            continue
        raw = []
        _walk_habata(j, raw)
        for v in raw:
            t = clean_text(v, keep_markers)
            if t and is_content(t):
                out.append(t)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('romfs')
    ap.add_argument('-o', '--out', default='out.txt')
    ap.add_argument('--no-skinship', action='store_true')
    ap.add_argument('--no-net', action='store_true')
    ap.add_argument('--keep-markers', action='store_true')
    args = ap.parse_args()

    lines = extract_scenario(args.romfs, args.keep_markers)
    parts = list(lines)
    sk = net = []
    if not args.no_skinship:
        sk = extract_skinship(args.romfs, args.keep_markers)
        parts += sk
    if not args.no_net:
        net = extract_net(args.romfs, args.keep_markers)
        parts += net
    with open(args.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(parts) + '\n')
    print(f'scenario={len(lines)} skinship={len(sk)} net={len(net)} total={len(parts)}')


if __name__ == '__main__':
    main()
