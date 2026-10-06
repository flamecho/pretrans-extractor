#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《ハイリゲンシュタットの歌》 (PS Vita / PCSG01070 / eXtend / Unity 5.6.1p4) 全文本提取

完整管线
--------
  1) 解 PKG (PSN 原始包, 含 NoNpDrm 结构):
       scripts/pkg2zip.exe -x "<pkg>" "<zRIF>"
       zRIF 需自备（见 references/third-party.md）
     产物: app/PCSG01070/{eboot.bin, archive.psarc, Media/, sce_*}
  2) 解密 PFS (NoNpDrm):
       <psvdec>/bin/win64/psvpfsparser.exe \
           -i app/PCSG01070 -o dec -z "<zRIF>" -f cma.henkaku.xyz
     成功标志: keystone: matched retail hmac
  3) 解 Unity PSARC:
       python scripts/psarc_extract.py dec/archive.psarc psarc_out
     产物: psarc_out/Media/resources.assets  (Unity 序列化文件, 内含全部 TextAsset)
  4) 本脚本:
       python scripts/heiligenstadt_extract.py psarc_out/Media/resources.assets <outdir>

依赖: UnityPy  (pip install UnityPy)

产物
----
  · ハイリゲンシュタットの歌_全文本.txt             剧本正文 (一行 = 一次点击)
  · ハイリゲンシュタットの歌_システムテキスト・資料.txt  系统/UI/资料文本
    ★ 后者**只收玩家在画面上实际能看到的文字** —— 键名 / 资源 ID / 脚本路径 /
      debug 脚本 / dbGallery 定义等内部数据一律剔除 (判据见 is_internal())。

数据格式 (逆向结论)
------------------
 * 游戏本体 = Unity 5.6.1p4 PSVita 构建; 全部剧本/文本都在 resources.assets 的
   TextAsset 里, 共 168 个:
     - "<X>_<Y>_0_main" (×2)  : (a) Lua 脚本 (b) 该场景的文本数据库 (同名, 二进制)
     - dbChapter / dbSection / dbScripterText / dbSelect / dbShop / dbShopText /
       dbGallery / dbSecret / dbHeaderFooter / strMenu / strSystem / face /
       lipsync / lipData / bgTargetOffset / charaTargetOffset / flag / t_staffroll
       / common / system / effect* / start
 * Lua 脚本按顺序调用:
     _talk( N )          -> 显示一个文本框; N = 文本库里 id==N 的记录
     ui_advSelectAdd( N )-> 显示一个选项;   N = 同上
     set_chapter_name( get_text( ID ) ) -> 章节名 (ID 十进制, 如 01000001 -> 1000001)
 * ★ 主人公名分岐: 全脚本有 **286 处**
     if isDefaultAdvCharaName() then  _talk(A)  else  _talk(B)  end
   A = 默认名「リート」版 (台詞里直接写 リート / 或写 #Name[0]), B = 自定义名版
   (把名字换成别的称呼或不带名字)。主角名既已统一按默认名还原, B 即重复文本
   -> 默认只保留 A 支线 (见 KEEP_NAME_BRANCH_ALTERNATIVE)。
 * 文本库 (dbin) 二进制格式:
     [records ...][strings ...][footer]
     记录 = { u32 id, u32 flag, u64 off1[, u64 off2 ...] }  (recsize = 8 + 8*字段数)
     对场景库 (recsize=32): off1=ver 音声ID / off2=话者 / off3=正文
     offset 相对 strings 区起点; footer 记录 count/recsize/textbase/nstr
 * footer magic: "BINL" (带偏移表) 或 "STRL" (纯字符串表)
"""
import os
import re
import sys
import struct

# ----------------------------------------------------------------------------
# 输出规范
# ----------------------------------------------------------------------------
HEROINE = 'リート'          # 主人公默认名 (strSystem: DEFAULT_ADV_NAME)
LINE_SEP_KEEP = False       # 框内 '\n' 全部并入一行 (一次点击 = 一行)
# 台詞が「主人公名の呼び方」で分岐する if 文:
#   if isDefaultAdvCharaName() then _talk(A) else _talk(B) end
# A = 默认名(リート)版, B = 自定义名版。主角名已固定还原为リート,
# 故 B 支线属同一台词的替换版本 -> 默认丢弃 (置 True 可两版都保留)。
KEEP_NAME_BRANCH_ALTERNATIVE = False

# 场景脚本的规范顺序 (共通 -> 各攻略对象 -> 特别篇 -> おまけ)
SCENE_ORDER = (
    # 共通ルート (序章 - 5章)
    ['0_0_0', '0_1_0', '0_2_0', '0_3_0', '0_4_0', '0_5_0'] +
    # ハルトルート
    ['1_6_0', '1_7_0', '1_8_0', '1_9_0', '1_10_0', '1_11_0'] +
    # アルシェルート
    ['2_6_0', '2_7_0', '2_8_0', '2_9_0', '2_10_0'] +
    # ディールート
    ['3_6_0', '3_7_0', '3_8_0', '3_9_0', '3_10_0'] +
    # クラヴィアルート
    ['4_6_0', '4_7_0', '4_8_0', '4_9_0', '4_10_0'] +
    # ヴィッセルート
    ['5_6_0', '5_7_0', '5_8_0', '5_9_0', '5_10_0', '5_11_0'] +
    # ハイリゲンシュタットの歌 (1-7)
    ['6_1_0', '6_2_0', '6_3_0', '6_4_0', '6_5_0', '6_6_0', '6_7_0'] +
    # 忘却の使徒ルート
    ['7_1_0', '7_2_0', '7_3_0', '7_4_0', '7_5_0'] +
    # おまけシナリオ (9 編)
    ['8_1_0', '8_2_0', '8_3_0', '8_4_0', '8_5_0', '8_6_0', '8_7_0', '8_8_0', '8_9_0']
)
# 開発用テスト脚本 (X_90_0 / X_91_0) —— 玩家不可视, 成品一律剔除 (此处仅作说明)
DEBUG_RE = re.compile(r'^\d+_9\d_0_main$')


# ----------------------------------------------------------------------------
# dbin (文本数据库) 解析
# ----------------------------------------------------------------------------
def _read_strings(b, textbase, end):
    """从 textbase 起读 0x00 分隔的 UTF-8 字符串, 返回 [(offset, str), ...]"""
    out = []
    p = textbase
    while p < end:
        e = b.find(b'\x00', p)
        if e < 0:
            break
        out.append((p - textbase, b[p:e].decode('utf-8', 'replace')))
        p = e + 1
    return out


class Dbin:
    """BINL / STRL 文本库"""

    def __init__(self, blob):
        self.blob = blob
        bi = blob.rfind(b'BINL')
        magic = b'BINL'
        if bi < 0:
            bi = blob.rfind(b'STRL')
            magic = b'STRL'
        self.magic = magic
        self.footer = None
        self.records = {}      # id -> [str, ...]
        self.ordered = []      # 按表中顺序的记录
        self.strings = []
        if bi < 0:
            return
        self.footer = bi
        h = struct.unpack_from('<12I', blob, bi + 4)
        self.count, self.recsize, self.tabsize, self.unk, self.textbase, self.nstr = h[4:10]
        if not (0 < self.textbase <= len(blob)):
            return
        self.strings = _read_strings(blob, self.textbase, bi)
        by_off = {o: s for o, s in self.strings}
        noff = (self.recsize - 8) // 8
        if noff <= 0 or self.recsize > self.textbase:
            return
        o = 0
        while o + self.recsize <= self.textbase:
            rid, flag = struct.unpack_from('<II', blob, o)
            vals = struct.unpack_from('<%dQ' % noff, blob, o + 8)
            texts = [by_off.get(v) for v in vals]
            if any(t is not None for t in texts):
                self.records[rid] = texts
                self.ordered.append((rid, flag, texts))
            o += self.recsize

    def text_of(self, rid, idx=0):
        r = self.records.get(rid)
        if r and idx < len(r):
            return r[idx]
        return None

    def all_texts(self):
        seen = set()
        out = []
        for _, _, texts in self.ordered:
            for t in texts:
                if t and t not in seen:
                    seen.add(t)
                    out.append(t)
        return out


# ----------------------------------------------------------------------------
# Lua 解析
# ----------------------------------------------------------------------------
def strip_lua_comments(s):
    """删除 -- 行注释与 --[[ ]] 块注释 (保留字符串字面量)"""
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == '-' and i + 1 < n and s[i + 1] == '-':
            j = i + 2
            m = re.match(r'\[(=*)\[', s[j:])
            if m:
                close = ']' + m.group(1) + ']'
                k = s.find(close, j + m.end())
                i = n if k < 0 else k + len(close)
            else:
                k = s.find('\n', i)
                i = n if k < 0 else k + 1
            continue
        if c in '"\'':
            q = c
            out.append(c)
            i += 1
            while i < n:
                if s[i] == '\\':
                    out.append(s[i])
                    i += 1
                    if i < n:
                        out.append(s[i])
                        i += 1
                    continue
                out.append(s[i])
                if s[i] == q:
                    i += 1
                    break
                i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


# 顺序扫描: _talk(N) / old1_talk(N) / ui_advSelectAdd(N) / _sys_talk("…")
EV = re.compile(
    r'\b(?P<fn>_talk|old1_talk|ui_advSelectAdd)\s*\(\s*(?P<num>\d+)\s*\)'
    r'|\b(?P<fn2>_sys_talk|ui_advSimpleMessage)\s*\(\s*"(?P<lit>(?:[^"\\]|\\.)*)"',
    re.S)

_TOK = re.compile(r'\b(if|for|while|function|then|do|end|else|elseif)\b')
_NAME_IF = re.compile(r'if\s+isDefaultAdvCharaName\s*\(\s*\)\s*then')


def mask_name_branch_else(code):
    """挖空 `if isDefaultAdvCharaName() then … else … end` 的 else 支线。

    该分支只是把同一句台词里的主人公名换成「不带名字的说法」(或别的称呼),
    主角名既然统一还原成默认名, 这条支线即为重复文本 → 屏蔽。
    保留换行, 以免影响其它行的定位。
    """
    spans = []
    for m in _NAME_IF.finditer(code):
        depth, i, els, endp = 1, m.end(), None, None
        while True:
            t = _TOK.search(code, i)
            if not t:
                break
            w = t.group(1)
            if w in ('if', 'for', 'while', 'function'):
                depth += 1
            elif w == 'end':
                depth -= 1
                if depth == 0:
                    endp = t.start()
                    break
            elif w in ('else', 'elseif') and depth == 1 and els is None:
                els = t.start()
            i = t.end()
        if endp is not None and els is not None and endp > els:
            spans.append((els, endp))
    if not spans:
        return code, 0
    buf = list(code)
    for s, e in spans:
        for k in range(s, e):
            if buf[k] != '\n':
                buf[k] = ' '
    return ''.join(buf), len(spans)


def lua_events(lua_src):
    """返回 [(kind, value)]; kind ∈ box / select / plain"""
    code = strip_lua_comments(lua_src)
    if not KEEP_NAME_BRANCH_ALTERNATIVE:
        code, _ = mask_name_branch_else(code)
    out = []
    for m in EV.finditer(code):
        if m.group('fn'):
            fn = m.group('fn')
            num = int(m.group('num'))
            kind = 'select' if fn == 'ui_advSelectAdd' else 'box'
            out.append((kind, ('id', num)))
        else:
            lit = m.group('lit')
            lit = lit.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            out.append(('box', ('lit', lit)))
    return out


# ----------------------------------------------------------------------------
# 文本规范化
# ----------------------------------------------------------------------------
def norm(t):
    """框内软换行合并 + 主人公名行内还原"""
    if t is None:
        return None
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    t = t.replace('#Name[0]', HEROINE).replace('#Name[1]', HEROINE)
    if not LINE_SEP_KEEP:
        t = t.replace('\n', '')
    return t


# 内部标识符 (玩家看不见者) 判据 -------------------------------------------------
_RE_IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(/[A-Za-z0-9_.]+)*$')
_RE_PATHY = re.compile(r'^[A-Za-z0-9_./]+$')


def is_internal(s):
    """True = 内部标识符 / 资源路径 / 键名 —— 玩家不可见, 不应出现在文本清单里。

    判据: 纯 ASCII, 且形如 `name_title` `SHOP_HARU_001` `main/08/8_1_0_main` `default`
    `KT00_01A`。含空格或大小写混排的自然语言 (如 `Press Any Button`) 不算内部。
    """
    if not s:
        return True
    if any(ord(c) >= 0x80 for c in s):
        return False
    if ' ' in s or '\t' in s:
        return False
    return bool(_RE_IDENT.match(s) or _RE_PATHY.match(s))


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def load_textassets(assets_path):
    try:
        import UnityPy
    except ImportError:
        sys.stderr.write(
            "需要 UnityPy: pip install UnityPy\n"
            "(或把 psarc_out/Media/resources.assets 所在目录加到 PYTHONPATH)\n")
        raise
    env = UnityPy.load(assets_path)
    tas = {}
    for obj in env.objects:
        if obj.type.name != 'TextAsset':
            continue
        d = obj.read()
        name = getattr(d, 'm_Name', None) or getattr(d, 'name', '')
        raw = d.m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8', 'surrogateescape')
        kind = 'lua' if raw[:1] == b'-' or raw[:2] == b'do' else 'bin'
        tas.setdefault(name, {})[kind] = raw
    return tas


def build_story(tas):
    """返回 (lines, stats, masked)"""
    lines = []
    stats = {}
    masked = 0
    for key in SCENE_ORDER:
        name = key + '_main'
        pair = tas.get(name)
        if not pair or 'bin' not in pair or 'lua' not in pair:
            stats[name] = 'MISSING'
            continue
        db = Dbin(pair['bin'])
        lua = pair['lua'].decode('utf-8', 'replace')
        if not KEEP_NAME_BRANCH_ALTERNATIVE:
            _, nm = mask_name_branch_else(strip_lua_comments(lua))
            masked += nm
        nbox = nsel = nempty = nmiss = 0
        for kind, val in lua_events(lua):
            if val[0] == 'lit':
                t = norm(val[1])
            else:
                # 场景库每条记录 = [音声ID, 話者, 本文] -> 取第 3 列
                t = norm(db.text_of(val[1], 2))
                if t is None:
                    nmiss += 1
                    continue
            if not t:
                nempty += 1
                continue
            lines.append(t)
            if kind == 'select':
                nsel += 1
            else:
                nbox += 1
        stats[name] = (len(db.records), nbox, nsel, nempty, nmiss)
    return lines, stats, masked


def build_extras(tas):
    """系统/UI/资料文本 —— 只收录玩家实际能在画面上看到的文字。

    被剔除的「玩家不可见」内容:
      · 键名/资源 ID/脚本路径等内部标识符 (name_title / SHOP_HARU_001 / main/08/8_1_0_main)
      · dbGallery 的鉴赏场景定义 (纯 script path + still id)
      · X_90_0 / X_91_0 开发用测试脚本 (游戏中不可达)
      · face 表里的 base id (只留画面上显示的称呼)
    """
    out = []

    def sec(title):
        out.append('')
        out.append('■ ' + title)

    def put(t):
        t = norm(t) if t else ''
        if t and not is_internal(t):
            out.append(t)

    # 1. 章タイトル (章节横幅)
    d = Dbin(tas.get('dbChapter', {}).get('bin', b''))
    if d.records:
        sec('章タイトル (dbChapter)')
        for rid, flag, texts in d.ordered:
            ts = [t for t in texts if t]
            if ts:
                put('　'.join(ts))

    # 2. 節タイトル + あらすじ (章节选择/详情画面)
    d = Dbin(tas.get('dbSection', {}).get('bin', b''))
    if d.records:
        sec('節タイトル・あらすじ (dbSection)')
        for rid, flag, texts in d.ordered:
            if len(texts) >= 2 and texts[0] and texts[1]:
                out.append('【%s】%s' % (texts[0], norm(texts[1])))

    # 3. シナリオ章名 / トロフィー通知
    d = Dbin(tas.get('dbScripterText', {}).get('bin', b''))
    if d.records:
        sec('シナリオ章名・実績通知 (dbScripterText)')
        for rid, flag, texts in d.ordered:
            put(texts[0] if texts else None)

    # 4. ショップの店員セリフ
    d = Dbin(tas.get('dbShopText', {}).get('bin', b''))
    if d.records:
        sec('ショップ (dbShopText)')
        for t in d.all_texts():
            put(t)

    # 5. シークレット（おまけシナリオのタイトル）
    d = Dbin(tas.get('dbSecret', {}).get('bin', b''))
    if d.records:
        sec('シークレット (dbSecret)')
        for t in d.all_texts():
            put(t)

    # 6. ヘッダ・フッタ（画面ボタンガイドのラベル）
    d = Dbin(tas.get('dbHeaderFooter', {}).get('bin', b''))
    if d.records:
        sec('ヘッダ・フッタ (dbHeaderFooter)')
        for t in d.all_texts():
            put(t)

    # 7. システム / メニュー文字列 (STRL) —— 只留显示值, 键名属内部
    for nm, label in (('strSystem', 'システム文字列 (strSystem)'),
                      ('strMenu', 'メニュー文字列 (strMenu)')):
        d = Dbin(tas.get(nm, {}).get('bin', b''))
        if d.strings:
            sec(label)
            for _, s in d.strings:
                put(s)

    # 8. ショップ商品の表示名
    d = Dbin(tas.get('dbShop', {}).get('bin', b''))
    if d.strings:
        sec('ショップ商品 (dbShop)')
        for _, s in d.strings:
            put(s)

    # 9. スタッフロール
    if 't_staffroll' in tas:
        sec('スタッフロール (t_staffroll)')
        raw = tas['t_staffroll']['bin'].decode('utf-8', 'replace')
        for ln in raw.split('\n'):
            if ln.strip():
                out.append(ln.rstrip())

    # 10. 話者名（画面上の名乗り）—— base id 属内部, 只留称呼
    if 'face' in tas:
        sec('話者名テーブル (face)')
        raw = tas['face']['bin'].decode('utf-8', 'replace')
        seen = set()
        for m in re.finditer(r'<base name="[^"]+"\s*/>|<base name="[^"]+">(.*?)</base>',
                             raw, re.S):
            for x in re.findall(r'<sync_text name="([^"]*)"', m.group(1) or ''):
                x = norm(x)
                if x and x not in seen:
                    seen.add(x)
                    out.append(x)

    return out


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(__doc__)
        sys.exit(2)
    assets = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)

    tas = load_textassets(assets)
    lines, stats, masked = build_story(tas)
    extras = build_extras(tas)

    story_path = os.path.join(outdir, 'ハイリゲンシュタットの歌_全文本.txt')
    extra_path = os.path.join(outdir, 'ハイリゲンシュタットの歌_システムテキスト・資料.txt')

    with open(story_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    with open(extra_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(extras).lstrip('\n') + '\n')

    print('== 场景统计 (场景: [记录数, 文本框, 选项, 空文本, 未命中]) ==')
    tot = [0, 0, 0, 0, 0]
    for k in SCENE_ORDER:
        s = stats.get(k + '_main', 'MISSING')
        if isinstance(s, str):
            print('  %-10s %s' % (k, s))
            continue
        for i in range(5):
            tot[i] += s[i] if i < len(s) else 0
        print('  %-10s %s' % (k, s))
    print('  TOTAL 记录=%d 文本框=%d 选项=%d 空=%d 未命中=%d' % tuple(tot))
    if KEEP_NAME_BRANCH_ALTERNATIVE:
        print('主角名分岐: 两版均保留')
    else:
        print('主角名分岐: 丢弃自定义名支线 %d 处 (if isDefaultAdvCharaName)' % masked)
    print('正文行数: %d  ->  %s' % (len(lines), story_path))
    print('资料行数: %d  ->  %s' % (len(extras), extra_path))


if __name__ == '__main__':
    main()
