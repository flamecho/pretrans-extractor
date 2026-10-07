# -*- coding: utf-8 -*-
"""
《薔薇に隠されしヴェリテ》 (PS Vita / PCSG00708 / Unity 5.3.5p5) 全文本提取

管线
----
 1) RAR -> app/PCSG00708  (NoNpDrm 加密 dump)
 2) psvpfsparser -z <zRIF> -f cma.henkaku.xyz   (PFS 解密)  -> dec/
 3) psarc_extract.py  archive.psarc -> psarc_out/Media/{level0,resources.assets,...}
 4) list_ta.py  resources.assets -> textassets/ (784 个 TKG TextAsset)
 5) 本脚本

文本来源 (逆向结论)
------------------
 A. TKG 脚本 (TextAsset, 676 EV + 100 QT + MAP_*):
      记录 = int16 cmd + int16 size(整条长度, 含 4B 头) + 参数(自 +4 起)
      MSG_PARAM(0x10)/MSG_PARAM_RWD(0x11):
        i32 x6 (msgid, charid, dispType, stop, ?, voiceFlag) + 3 个 [u16 len][UTF-8]
        串 1 = ボイスID / 串 2 = 話者名(m_szName) / 串 3 = 正文(m_szText)
        正文替换: '%'->名, '&'->姓, '$'/'@'/'#'(着色标记)删除, 0x5C(backslash)=框内换行
      CHOICE_JUMP(0x61): [u16 len]choiceKey + i16 n + i32 x n  -> 选项文本查 So選択肢
 B. scene@2d AssetBundle 里的 ScriptableObject:
      So選択肢 / So辞書 / SoBook / SoItem / SoQuest / SoEvtDesc / SoChart
      BhvMchHost (地图 NPC 会話) / ScnMiniMap
输出规范: UTF-8-BOM, 纯 LF, 一次点击 = 一行, 框内换行合并, 保留日文, 不加说话人前缀
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys
import struct
import collections

BASE = os.path.join(VNTRANS_HOME, '_work_verite')
TA_DIR = os.path.join(BASE, 'textassets')
BUNDLE = os.path.join(BASE, 'dec/PCSG00708/Media/StreamingAssets/scene@2d')
OUT_DIR = os.path.join(VNTRANS_HOME, '提取结果')

NAME = ['リーゼ', 'フォルスター']   # GMDEF.NAME = { "リーゼ", "フォルスター" }

# 字体替换槽: FNT00SP 图集把 U+333B 的格子画成了一个粉色花蕾/心形的装饰符号。
# 它只出现在レオナール(flamboyant 髪結師)的台词里, 作语气符号用。
# 原始码位 U+333B 保留在 TA 里; 成品中按最常见的台词装饰符 ♥ 呈现 (详见解析报告)。
GLYPH_SUBST = {'\u333b': '♥'}

# 未在游戏中引用的开发用残留 (Assembly-CSharp 里 grep 引用数 = 0)
EXCLUDE = {'EVXXX_XXX', 'DRESS_TST_01'}

CMD_MSG = (16, 17)
CMD_CHOICE = 97

# ---------------------------------------------------------------- TKG parser
def i16(b, o):
    return struct.unpack_from('<h', b, o)[0]


def i32(b, o):
    return struct.unpack_from('<i', b, o)[0]


class Tkg:
    """精确复刻 Assembly-CSharp:TkgData"""

    def __init__(self, b):
        self.b = b
        self.cmd = 0
        self.prm = 0

    def command(self):
        return i16(self.b, self.cmd) if self.cmd < len(self.b) else 0xA2

    def size(self):
        return i16(self.b, self.cmd + 2) if self.cmd + 2 < len(self.b) else 0

    def end(self):
        return self.cmd >= len(self.b)

    def s16(self):
        v = i16(self.b, self.cmd + self.prm + 4); self.prm += 2; return v

    def s32(self):
        v = i32(self.b, self.cmd + self.prm + 4); self.prm += 4; return v

    def utf8(self):
        ln = i16(self.b, self.cmd + self.prm + 4); self.prm += 2
        st = self.cmd + self.prm + 4
        s = self.b[st:st + ln].decode('utf-8', 'replace')
        self.prm += ln
        return s

    def align(self, ea=2):
        self.prm += (self.cmd + self.prm) % ea

    def nxt(self):
        self.cmd += self.size()
        self.prm = 0


def parse_tkg(data):
    """-> [('msg', name, text) | ('choice', key)]"""
    t = Tkg(data)
    out = []
    guard = 0
    while not t.end():
        guard += 1
        if guard > 500000:
            break
        c = t.command()
        sz = t.size()
        if sz <= 0:
            break
        try:
            if c in CMD_MSG:
                _ = [t.s32() for _ in range(6)]
                _voice = t.utf8(); t.align()
                nm = t.utf8(); t.align()
                tx = t.utf8(); t.align()
                out.append(('msg', nm, tx))
            elif c == CMD_CHOICE:
                key = t.utf8(); t.align()
                n = t.s16()
                out.append(('choice', key))
        except Exception:
            pass
        t.nxt()
    return out


# ---------------------------------------------------------------- normalize
def norm_text(s):
    """玩家实际看到的文字: %/& 换名, 去着色标记, 框内换行合并且去掉行首缩进"""
    s = s.replace('%', NAME[0]).replace('&', NAME[1])
    s = re.sub(r'[$@#]', '', s)
    s = s.replace('\\', '')          # 0x5C = 框内软换行 -> 合并
    s = s.replace('\n', '').replace('\r', '')
    for k, v in GLYPH_SUBST.items():
        s = s.replace(k, v)
    s = s.strip(' \u3000')
    return s


def norm_name(s):
    s = s.replace('%', NAME[0]).replace('&', NAME[1])
    s = re.sub(r'[$@#]', '', s)
    return s.replace('\\', '').replace('\n', '').strip(' \u3000')


# ---------------------------------------------------------------- unify
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---------- 1. scene@2d: ScriptableObjects + BhvMchHost ----------
    import UnityPy
    env = UnityPy.load(BUNDLE)
    choice_map = {}          # id -> [(txt), ...]
    npc_lines = []           # BhvMchHost
    so_dict = []             # So辞書  (id, idx, title)
    so_book = []
    so_item = []
    so_quest = []
    so_evt = []
    so_chart = []
    minimap = []
    extra_pending = collections.defaultdict(list)

    for o in env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        try:
            d = o.read()
        except Exception:
            continue
        nm_obj = getattr(d, 'm_Name', '') or ''
        fields = set(a for a in dir(d) if not a.startswith('_'))
        tbl = getattr(d, 'tbl', None) or []
        e0 = tbl[0] if len(tbl) else None
        has = lambda o, a: hasattr(o, a)

        if e0 is not None and has(e0, 'a') and has(e0, 'id'):          # So選択肢.Q
            for q in tbl:
                key = getattr(q, 'id', '')
                opts = [getattr(a, 'txt', '') for a in getattr(q, 'a', [])]
                if key:
                    choice_map[key] = [x for x in opts if x]
        elif e0 is not None and has(e0, 'bg1st'):                      # SoEvtDesc
            for e in tbl:
                so_evt.append((getattr(e, 'id', ''), getattr(e, 'title', '')))
        elif e0 is not None and has(e0, 'title') and has(e0, 'idx'):   # So辞書
            for e in tbl:
                so_dict.append((getattr(e, 'id', ''), getattr(e, 'idx', 0), getattr(e, 'title', '')))
        elif e0 is not None and has(e0, 'price買'):                    # SoItem
            for e in tbl:
                so_item.append((getattr(e, 'id', ''), getattr(e, 'name', '')))
        elif e0 is not None and has(e0, 'page') and has(e0, 'name'):   # SoBook
            for e in tbl:
                so_book.append((getattr(e, 'id', ''), getattr(e, 'name', '')))
        elif e0 is not None and has(e0, 'tblDef'):                    # SoChart
            for e in tbl:
                v = getattr(e, 'name', '')
                if v:
                    so_chart.append(v)
        elif hasattr(d, 'dscs'):                                       # SoQuest
            for e in getattr(d, 'dscs'):
                so_quest.append((getattr(e, 'id', ''), getattr(e, 'title', '')))
        elif hasattr(d, 'ones'):                                       # BhvMchHost
            for one in getattr(d, 'ones'):
                for pg in getattr(one, 'page', []):
                    n = norm_name(getattr(pg, 'name', ''))
                    m = norm_text(getattr(pg, 'msg', ''))
                    if m:
                        npc_lines.append((n, m))
        elif 'm_text' in fields:                                       # ScnMiniMap
            v = getattr(d, 'm_text', '')
            if v and re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', v):
                minimap.append(v)

    print('choice groups:', len(choice_map), ' npc lines:', len(npc_lines))
    print('辞書:', len(so_dict), ' Book:', len(so_book), ' Item:', len(so_item),
          ' Quest:', len(so_quest), ' EVT:', len(so_evt), ' chart:', len(so_chart))

    # ---------- 2. TKG TextAssets ----------
    files = sorted(os.listdir(TA_DIR))
    files = [f for f in files if not f.startswith('__')]

    def key(f):
        m = re.match(r'^(EV|QT)(\d+)_(\d+)$', f)
        if m:
            grp = 0 if m.group(1) == 'EV' else 1
            return (grp, int(m.group(2)), int(m.group(3)), f)
        return (2, 0, 0, f)

    files.sort(key=key)

    story = []
    stats = collections.OrderedDict()
    unmatched_choice = collections.Counter()
    ctrl = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
    for f in files:
        if f in EXCLUDE:
            continue
        data = open(os.path.join(TA_DIR, f), 'rb').read()
        evs = parse_tkg(data)
        nmsg = nsel = 0
        for e in evs:
            if e[0] == 'msg':
                t = norm_text(e[2])
                if t and not ctrl.search(t):
                    story.append(t)
                    nmsg += 1
            else:
                a = e[1]
                opts = choice_map.get(a)
                if opts:
                    for o in opts:
                        t = norm_text(o)
                        if t and not ctrl.search(t):
                            story.append(t)
                            nsel += 1
                elif a == '依頼':
                    # クエスト受注確認 (SceneAdv選択Q): 画面に出るのは SoQuest.title のみ
                    # -> 資料編に収録ずみ。ここでは何も出さない。
                    pass
                else:
                    unmatched_choice[a] += 1
        stats[f] = (nmsg, nsel)

    total_msg = sum(v[0] for v in stats.values())
    total_sel = sum(v[1] for v in stats.values())
    print('TKG files:', len(files), ' msg lines:', total_msg, ' choice lines:', total_sel)
    if unmatched_choice:
        print('UNMATCHED choice keys:', dict(unmatched_choice))

    # ---------- 3. write ----------
    p1 = os.path.join(OUT_DIR, '薔薇に隠されしヴェリテ_全文本.txt')
    with open(p1, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(story) + '\n')

    extras = []

    def sec(t):
        extras.append('')
        extras.append('■ ' + t)

    sec('用語辞典 見出し語 (So辞書)  ※ 本文は画像 SH_DICT/DICxxx_{0,1}')
    for i, (rid, idx, title) in enumerate(so_dict):
        extras.append('【%s】%s' % (rid, title))

    sec('本 題名 (SoBook)  ※ 本文は画像 BOOKxx_yy')
    for rid, n in so_book:
        extras.append('%s\t%s' % (rid, n))

    sec('アイテム名 (SoItem)')
    for rid, n in so_item:
        extras.append('%s\t%s' % (rid, n))

    sec('クエスト 題名 (SoQuest)')
    for rid, n in so_quest:
        extras.append('%s\t%s' % (rid, n))

    sec('イベント回想 題名 (SoEvtDesc)')
    for rid, n in so_evt:
        extras.append('%s\t%s' % (rid, n))

    sec('章チャート (SoChart)')
    for n in so_chart:
        extras.append(n)

    sec('ミニマップ・メッセージ (ScnMiniMap)')
    seen = set()
    for n in minimap:
        if n not in seen:
            seen.add(n)
            extras.append(n)

    sec('マップ NPC 会話 (BhvMchHost)  ※ 話者名は m1 相当')
    for n, m in npc_lines:
        extras.append(m)

    p2 = os.path.join(OUT_DIR, '薔薇に隠されしヴェリテ_資料・システムテキスト.txt')
    with open(p2, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(extras).lstrip('\n') + '\n')

    print('main  ->', p1, len(story))
    print('extra ->', p2, len(extras))

    # per-file stat dump
    with open(os.path.join(BASE, 'tkg_stats.txt'), 'w', encoding='utf-8') as fh:
        for k, v in stats.items():
            fh.write('%s\t%d\t%d\n' % (k, v[0], v[1]))


if __name__ == '__main__':
    main()
