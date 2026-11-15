# -*- coding: utf-8 -*-
"""神足町人妖譚 ~迷イ子ノ章~ (PC / System-NNN「NNNLib」) 全文本提取

源：<工作区>
格式（本作逆向结论，与 asakiyumemishi 同族）：
  * 整文件逐字节 XOR 0xFF 混淆（字节取反）。
  * u32@0=0x20；"SPTHEADER0" 魔术字。
  * 消息池：每条消息为 \0 结尾的 cp932 串，格式 `<名>\r\n<正文>`。
      · 名 = charaname 名单 / `#名`(主人公宏) / `？？？` / `名前なし`(=narrative)
      · 正文内 `\r\n` = 框内软换行 ⇒ 合并；`#心`/`#［Nよみ］`/反斜杠码 = 内联控制码 ⇒ 剔。
  * 两层垃圾（asakiyumemishi 陷阱，本作更严重）：
      ① 消息头 ASCII 资源标签：bg_02a_3 / ta04S01a01 / ev01 / aa030027 …（场景/背景/动画指令）
      ② 名前之前的 1~数字节伪字（よ翠 / ば#名 / 里ｱs神足町》…）
      法：先按 `<名>\r\n` 锚定（剥前缀伪字），再剥 ASCII 标签，再剔内联码。
  * 名札一律保留（印在正文文本框内），与台词同行：`翠「そうだね」`；`#名` 宏原样保留。
  * 一次点击 = 一个文本框 = 一行；本作消息池为扁平序列，每消息独立一击 ⇒ 单版（无多击同页累积）。
"""
import os, re, glob, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SPT_DIR = os.path.join(VNTRANS_HOME, '_work_koutari/iso/app/spt')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]神足町人妖譚 ~迷イ子ノ章~.txt')

# 说话人名单（源自 namecol.xtx，最长优先避免子串误命中）
NAMES = ['耀＆翠','耀・翠','退魔師風の男','退魔師風の女','九天オーナー',
         '霊魂壱','霊魂弐','霊魂参','霊魂肆','妖の少年','妖の少女',
         '白髪の少年','囁く声','町内放送','死人憑き','青年','子猫','二人',
         '天遊','ハクア','猿妖','妖','店員','耀','翠','？？？','―――','名前なし','#名']
NAMES = sorted(set(NAMES), key=len, reverse=True)
NAME_ALT = '|'.join(re.escape(n) for n in NAMES)
NAME_RE = re.compile('(' + NAME_ALT + r')\r\n')
NONAME = '名前なし'

def recover_name(field):
    """名前字段可能带伪字前缀/中段，设法还原为已知名。"""
    if field in NAMES:
        return field
    # 1) 已知名作为子串出现
    for nm in NAMES:
        if nm in field:
            return nm
    # 2) 字段以某已知名的末尾 >=2 字结尾（伪字替换了前段）
    best = None; bl = 0
    for nm in NAMES:
        if len(nm) >= 2 and field.endswith(nm[-2:]):
            if len(nm) > bl:
                best = nm; bl = len(nm)
    if best:
        return best
    return field  # 无法还原，原样保留

def decrypt(p):
    return bytes(b ^ 0xFF for b in open(p, 'rb').read())

def is_lead(b):
    return (0x81 <= b <= 0x9f) or (0xe0 <= b <= 0xfc)

def cp932_len(n, i, L):
    j = i
    while j < L:
        c = n[j]
        if c == 0:
            break
        if is_lead(c):
            if j + 1 < L and ((0x40 <= n[j+1] <= 0x7e) or (0x80 <= n[j+1] <= 0xfc)):
                j += 2
            else:
                return -1
        elif 0x20 <= c <= 0x7e or 0xa1 <= c <= 0xdf or c in (0x0d, 0x0a, 0x09):
            j += 1
        else:
            return -1
    return j - i

def walk_strings(n, start):
    """从 start 起，按 \0 间隔走 cp932 串，遇 >256 字节空洞即停（池末）。"""
    L = len(n); out = []; i = start
    last_end = start
    while i < L:
        ln = cp932_len(n, i, L)
        if ln >= 2:
            try:
                t = n[i:i+ln].decode('cp932')
            except UnicodeDecodeError:
                t = None
            if t is not None and len(t) >= 1:
                out.append(t)
                i = i + ln + 1
                last_end = i
                continue
        if i - last_end > 256:
            break
        i += 1
    return out

# 行首 ASCII 标签（资源指令）。含 bg_/ta/ev/0300 字样或单控制符即判为标签。
TAG_RE = re.compile(r'^([0-9A-Za-z_|]+)')
def is_tag_run(run):
    if not run:
        return False
    if 'bg' in run or run.startswith('ta') or run.startswith('ev') or '0300' in run:
        return True
    if run in ('u', 'v', 'I', 'e'):
        return True
    return False

# 真·半角カナ（U+FF66-FF9F）—— 本作路线文件每消息行首腐化前缀专用，整体剥除。
HALFWIDTH_KANA = re.compile(r'[\uFF66-\uFF9F]')
# PUA（U+E000-F8FF）—— cp932 IBM/NEC 扩展把腐化字节映射成私用区字形槽，整体剥除。
PUA = re.compile(r'[\uE000-\uF8FF]')

# ── 系统/UI 排除（00-rules §不收：config/help/save/sysscn/通知/成就/场景标签/ED曲名）
# 用「结构签名」而非关键词黑名单：锚定在行首（可选垃圾前缀后），避免误杀正文中自然
# 出现这些词的对话（如 耀「ほい、終了っと」）。
GARB = r'[0-9A-Za-z_｡-ﾟぁ-ゖァ-ヿー]*'
UI_RES = [
    re.compile(GARB + r'(コンフィグ|ギャラリー|ＢＧＭ鑑賞|バックログ|タイトル|シーン鑑賞|システムメニュー)'),  # 菜单标签
    re.compile(GARB + r'称号(・|$)'),                     # 成就/称号 标签
    re.compile(GARB + r'ＥＤ・'),                          # ED 曲名（元数据）
    re.compile(GARB + r'第[０-９?？]*[^ル]*ルート[０-９?？]*(日目|終章)'),  # 场景/日 标签（引擎内部）
    re.compile(r'.*スキップしますか'),                     # 跳过提示
    re.compile(r'が解放されました'),                     # 解锁通知（迷你游戏/CG/BGM 等，シーン鑑賞 可能腐化）
    re.compile(r'ミニゲーム解放'),                       # 迷你游戏 解锁数 标签
]
UI_FULL = [re.compile(GARB + r'(ロード|セーブ)\s*')]       # 单独的 读取/保存 菜单项
def is_ui(t):
    for rx in UI_RES:
        if rx.search(t):
            return True
    for rx in UI_FULL:
        if rx.fullmatch(t):
            return True
    return False

def clean(t):
    # 1) 内联控制码：注音 / 心标记 / 反斜杠码（非 CRLF）
    t = re.sub(r'#［[^］]*］', '', t)
    t = re.sub(r'#心', '', t)
    t = re.sub(r'\\(?![\r\n])[^\r\n]', '', t)
    # 2) 剥全部半角カナ（U+FF66-FF9F）—— 本作路线文件每消息行首均有 1~3 字节腐化前缀，
    #    半角カナ 只可能来自该腐化，绝非负文字，整体剥除（不猜名、不丢正文）。
    t = HALFWIDTH_KANA.sub('', t)
    # 2b) 剥 PUA（U+E000-F8FF）—— cp932 的 IBM/NEC 扩展把腐化字节映射成私用区字形槽，整体剥除。
    t = PUA.sub('', t)
    # 3) 名/正文判定：仅当字段可还原为已知名（或 #名）才切分；否则整条作为正文
    #    （内部 \r\n 是软换行 ⇒ 合并，绝不按 \r\n 截断叙事）。
    #    ★ 不剥“行首孤立 ASCII”：那是腐化名（如 s/Ｉ），剥掉会把 `、。` 顶到行首触发伪 [E]；
    #      保留原名 ⇒ 仅落 [W] 拉丁字母（WARN 不阻断），符合「保留原文 / 不猜测」。
    if '\r\n' in t:
        field, body = t.split('\r\n', 1)
        nm = recover_name(field)
        if nm == NONAME:
            return body
        if nm != field:          # 字段含已知名（腐化前缀已舍去）
            return nm + body
        # 字段无已知名：腐化名 或 叙事软换行 —— 整条保留（合并后为一行）
        return field + body
    return t

def merge_crlf(t):
    return t.replace('\r\n', '').replace('\r', '').replace('\n', '')

def extract_file(fn):
    n = decrypt(fn)
    L = len(n)
    hdr = n.find(b'SPTHEADER0')
    start = hdr + 0x60 if hdr >= 0 else 0x100
    # 找到一个较长日文串作为池起点（避免头段噪声）
    pool = None
    for i in range(start, L - 8):
        if cp932_len(n, i, L) >= 8:
            pool = i; break
    if pool is None:
        return []
    raws = walk_strings(n, pool)
    out = []
    ui = 0
    for r in raws:
        c = clean(r)
        if not c:
            continue
        c = merge_crlf(c)
        if not c.strip():
            continue
        # 系统/UI 排除（菜单/通知/成就/场景标签/ED曲名/跳过提示）
        if is_ui(c):
            ui += 1
            continue
        # 至少含日文
        if not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', c):
            continue
        out.append(c)
    return out, ui

def main():
    files = sorted(glob.glob(os.path.join(SPT_DIR, '*.spt')))
    print("spt files:", len(files))
    all_lines = []
    per_file = {}
    for f in files:
        ls, ui = extract_file(f)
        per_file[os.path.basename(f)] = ls
        all_lines.extend(ls)
        print(f"  {os.path.basename(f):28} -> {len(ls):5} lines  (ui-excl {ui})")
    # 去重（相邻跨文件可能重复尾部）
    seen = set(); uniq = []
    for l in all_lines:
        if l not in seen:
            seen.add(l); uniq.append(l)
    print("total:", len(all_lines), "unique:", len(uniq))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(uniq) + '\n')
    print("->", OUT)

if __name__ == '__main__':
    main()
