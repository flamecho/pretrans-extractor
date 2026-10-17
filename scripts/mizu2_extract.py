#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""水の旋律2 ～緋の記憶～ (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本
用法: python scripts/mizu2_extract.py <GAMEDATA.DAT> <out.txt> [--stat]
结构: THFS 头 0x18 + 条目 64B (name32[空格填充] + pad8 + off u32 + size u32 + z u32 + size u32 + hash8)
脚本: 无独立头（0x20 起即为指令流）; 文本串 = cp932 + NUL
页尾: %K%P(普通) / %K%p(选项前)；%O<num> = 上屏特效尾
"""
import struct, re, sys, collections

TXT_CTRL = re.compile(r'%C[0-9A-Fa-f]{6}|%[A-Za-z](?:[A-Za-z][0-9]{0,3}|[0-9]{0,3})')
JPCHAR = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
HIRA = re.compile(r'[\u3041-\u309f]')
HALFKANA = re.compile(r'[\uff66-\uff9f]')
PUA = re.compile(r'[\ue000-\uf8ff]')
ASCII2 = re.compile(r'[A-Za-z0-9]{2,}')
NAME = re.compile(r'^【[^】]{1,24}】')
# 不收：系统/UI/调试/码表（BATTLE＝战斗界面文案；BTL_MES*＝战斗事件台词，收但排到末尾）
EXCLUDE = ('SHORTCUT', 'DATA', 'MAIN', 'DMENU', 'DBG', 'INIT', 'JIS2UCS', 'SYS',
           'CLRFLG', 'BTL_EFF', 'DICT', 'BATTLE')
# 系统提示 / 开发注记：整行丢弃
DROP = ('クリアリスト画面に戻ります', '戦闘後アイテム取得ファイル（作成中）',
        '式紙入手', '鏡入手', 'ダミー')
# 飾り罫（├──┤ / ≪──≫：制御記号＋U+2500 罫線）＝画面装飾、正文不含
DECO = re.compile(r'[├┤≪≫][\u2500-\u257f]*[├┤≪≫]|[├┤≪≫]')


def thfs_entries(path):
    d = open(path, 'rb').read()
    magic, total, count, _ = struct.unpack_from('<4sIII', d, 0)
    assert magic == b'THFS', magic
    ents = []
    for i in range(count):
        o = 0x18 + i * 64
        nm = d[o:o+32].split(b'\0')[0].decode('cp932', 'replace').strip()
        off, sz, _z, sz3 = struct.unpack_from('<IIII', d, o + 40)
        ents.append((nm, off, sz))
    return d, ents


def dec_ok(seg):
    i, n = 0, len(seg)
    while i < n:
        c = seg[i]
        if c < 0x20 or c == 0x7f:
            return False
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            if i + 1 >= n:
                return False
            s = seg[i+1]
            if not (0x40 <= s <= 0x7e or 0x80 <= s <= 0xfc):
                return False
            i += 2
        elif c < 0x80 or 0xa1 <= c <= 0xdf:
            i += 1
        else:
            return False
    return True


def natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def clean(t):
    for k, v in NAME_MACRO:
        t = t.replace(k, v)
    had_deco = bool(DECO.search(t))
    t = DECO.sub('', t)
    if had_deco:
        t = re.sub(r'([「（『])\u3000', r'\1', t)
    t = TXT_CTRL.sub('', t)
    t = t.replace('\r', '').replace('\n', '')
    t = NAME.sub('', t)
    return t.strip(' \u3000')


def core_of(s):
    m = re.match(r'^(?:%C[0-9A-Fa-f]{6}|%[A-Za-z](?:[A-Za-z][0-9]{0,3}|[0-9]{0,3}))+', s)
    return s[m.end():] if m else s


def is_text_seg(s, opt=False, loose=False):
    if not s or not JPCHAR.search(s):
        return False
    if PUA.search(s):               # cp932 用户定义区 → 二进制表
        return False
    if HALFKANA.search(s):
        return False
    if s[0].isascii():
        return False
    if ASCII2.search(s) and not HIRA.search(s):
        return False
    if '好感度' in s:               # 调试用好感度读数
        return False
    if opt or loose:
        return True
    if HIRA.search(s):
        return True
    return len(s) >= 2 and bool(re.search(r'[…‥「」『』、。！？・]', s))


# 主角名插入宏：%IL0＝姓、%IF0＝名（默认名 柏木 きら；玩家可改名）
NAME_MACRO = (('%IL0', '柏木'), ('%IF0', 'きら'))


def sanitize(seg):
    """段首常夹带 8~12 字节二进制残留（命令操作数，含 0x00-0x1F）⇒
    取「第一个能完整解码、且以日文/引号起头」的起点；残留里的控制字节会让更早的起点直接判废"""
    for i in range(min(len(seg), 20)):
        sub = seg[i:]
        if not dec_ok(sub):
            continue
        try:
            s = sub.decode('cp932')
        except UnicodeDecodeError:
            continue
        s2 = re.sub(r'^[｡-ﾟA-Za-z0-9%]+', '', s)
        if s2 and re.match(r'^[「（『【ぁ-ヿ一-鿿]', s2):
            for k, v in NAME_MACRO:
                s2 = s2.replace(k, v)
            return s2
    return None


# 战斗结算处的开发用块（系统提示 + （＋１）选项 + 好感度读数）⇒ 整段丢弃且截断合并
DEV = ('クリアリスト画面', '好感度', '（＋', '画面に戻ります', 'フラグＯＮ')
FLAG = re.compile(r'（[^）]{0,14}フラグＯＮ）')   # 选项上的旗标注记：只删注记，保留选项正文


def extract_file(b):
    out = []
    pending = []
    opt_mode = False

    def flush(kind):
        nonlocal pending
        if pending:
            txt = ''.join(clean(x) for x in pending)
            pending = []
            if txt:
                out.append((kind, txt))

    segs = []
    st = 0
    for i, c in enumerate(b):
        if c == 0:
            segs.append(b[st:i])
            st = i + 1
    for seg in segs:
        if not seg:
            continue
        s = sanitize(seg)
        if s is not None and FLAG.search(s) and not FLAG.sub('', s).strip(' 　'):
            s = None
        elif s is not None:
            s = FLAG.sub('', s)
        if s is None:                 # 二进制表/命令残余：丢弃待合并（正确页面必以 %P 收尾）
            pending = []
            continue
        if any(d in s for d in DEV):  # 开发用块：文本丢弃，但 %p 的「选项前」语义要保留
            pending = []
            if '%p' in s:
                opt_mode = True
            elif '%P' in s:
                opt_mode = False
            continue
        core = core_of(s)
        if not core:
            if ('%P' in s or '%p' in s) and pending:
                flush('option' if opt_mode else 'body')
            if '%p' in s:
                opt_mode = True
            elif '%P' in s:
                opt_mode = False
            continue
        has_p = core.rstrip().endswith(('%P', '%p'))
        eff = re.sub(r'%O\d*$', '', core)
        is_eff = (eff != core) and bool(eff)
        if has_p:
            # 页文本可能被拆成 1~3 段（前段无尾、末段带 %P）；成片无尾串则是数据表（場所名/名札）
            if len(pending) > 3 or sum(len(x) for x in pending) > 300:
                pending = []
            else:
                flush('option' if opt_mode else 'body')
            if is_text_seg(eff if is_eff else core, loose=True):
                txt = clean(s)
                if txt:
                    out.append(('body', txt))
            opt_mode = core.rstrip().endswith('%p')
        elif is_eff:
            if len(pending) > 3:
                pending = []
            else:
                flush('option' if opt_mode else 'body')
            if len(eff) >= 4 and re.search(r'[\u3041-\u30ff\u4e00-\u9fff]{2,}', eff) \
                    and is_text_seg(eff, loose=True):
                txt = clean(s)
                if txt:
                    out.append(('effect', txt))
            opt_mode = False
        elif opt_mode:
            if is_text_seg(core, opt=True):
                txt = clean(s)
                if txt:
                    out.append(('option', txt))
        elif is_text_seg(core):
            pending.append(s)
    return out


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    d, ents = thfs_entries(src)
    files = [(n, o, s) for n, o, s in ents
             if n.upper().endswith('.BIN') and not any(n.upper().startswith(e) for e in EXCLUDE)]
    files.sort(key=lambda x: natkey(x[0]))
    # 战斗事件台词（BTL_MES*）不属于章节主线，排到全文末尾
    files = [x for x in files if not x[0].upper().startswith('BTL_MES')] + \
            [x for x in files if x[0].upper().startswith('BTL_MES')]
    lines = []
    stat = collections.Counter()
    for nm, off, sz in files:
        items = extract_file(d[off:off+sz])
        for kind, t in items:
            if len(t) < 2:
                stat['drop_1char'] += 1
                continue
            if re.search(r'[\[\]\{}|]', t):
                stat['drop_badchar'] += 1
                continue
            if any(x in t for x in DROP) or (kind == 'option' and '（＋' in t):
                stat['drop_dev'] += 1
                continue
            stat[kind] += 1
            lines.append(t)
    print('文件 %d / 行 %d / %s' % (len(files), len(lines), dict(stat)))
    if dst:
        with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('写出 %s' % dst)


if __name__ == '__main__':
    main()
