"""ラッキードッグ1 Secret Diary F（PC-JP，Adobe AIR／jp.co.woga.was 引擎）文本提取器。

源：盘内 `dat\\VN_*.dat`（19 个）——每个是「[4B 文件头] + raw deflate 流串联」，
    其中 1 段（VN_SS18/19 各 14 段）是 UTF-8 脚本文本，其余为 PNG／MP3 资源。
    `mac/.../Resources/system.dat` 无脚本（443 PNG + 6 bin，已验）。

脚本 DSL（与 RAKIDOMania 同框架，但本作 message 无 label 字段）：
    __initialize / __<label>     分段标签
    //…　;…                      注释（全角分号是作者备注）
    @@message{json}              一条消息命令 → 一次显示步进（等点击）
    <TAB>一行文字                 该消息命令的显示文本；行首多一个全角空格＝折行续行
    <TAB>（空）                   框内空行＝排版空档（合并时丢弃）
    裸行（无 TAB、无 @@）          解析器不认：`END`、`//END`、`<<<<<<< .mine`、
                                 `（Tennenouji Web Site, …）` → 一律不收

成行口径（L0：脚本命令级判据）：
    一个 @@message{…} 块 ＝ 一次点击 ＝ 一个文本框 ＝ 输出一行；块内 TAB 行全部合并、不插分隔。
    空文本块（只有空 TAB 行）＝ 空拍子，丢弃。
    依据：① 每条 @@message 执行后引擎置 STATE_MESSAGE_WAIT（SWF `WASmessage.run`），
          ② append 连续段的行数被文本框高度硬卡在 ≤19 行（实测 526 组：max 19／mean 10.5），
             证明 append 是「往同一个框里续行」，框满才由无 append 的块换新框。

用法：
    python scripts/luckydogF_extract.py <源目录> <输出 txt> [--work <目录>]
"""
import json
import os
import re
import sys
import zlib

CH = 256 * 1024
IDEO_SP = '\u3000'
MSG = re.compile(r'^@@message\s*(\{.*\})?\s*$')
# 裸行里只有这些是脚本关键字／注释／合并残渣，属非文本
# 裸行＝和 TAB 行同类的正文（框架实证：RAKIDOMania 里「サア！…」三连裸行是台词，须合并成一框）。
# 但下面两类是构建残留，按「ASCII 全扫 ⇒ 脚本/资源残留」归类剔除，不是按内容猜：
#   ① `<<<<<<< .mine`（SVN 合并标记，42 行，全在 VN_anv01_04）
#   ② 整行只有 `-` 的装饰线（3 行，与 `;-----` 注释同形）
DASH_ONLY = re.compile(r'^-{3,}$')
BARE_SKIP = ('<<<<<<<', '=======', '>>>>>>>')
# 调试残留（不是剧本正文）：实测只此一处，`VN_SS14` 的 `\t...click`
DROP_TEXT = {'...click'}


def split_segments(d, start=4):
    """`[4B 头] + raw deflate 流` 串联 → [(offset, 解压后字节)]，线性复杂度。"""
    n = len(d)
    pos = start
    out = []
    while pos + 2 < n:
        o = zlib.decompressobj(-15)
        rd = pos
        parts = []
        while not o.eof and rd < n:
            chunk = d[rd:min(rd + CH, n)]
            parts.append(o.decompress(chunk))
            rd += len(chunk)
        if not o.eof:
            break
        body = b''.join(parts)
        used = rd - len(o.unused_data) - pos
        if used <= 0:
            break
        out.append((pos, body))
        pos += used
    return out, pos


def scripts_of(path):
    """取一份 .dat 里的脚本段（按段序）。"""
    segs, _ = split_segments(open(path, 'rb').read())
    out = []
    for off, b in segs:
        if b[:2] == b'__':
            try:
                out.append(b.decode('utf-8'))
            except UnicodeDecodeError:
                pass
    return out


def parse_script(text):
    """返回 [(kind, payload)]：kind='box' 为一条显示框的文本（成品一行）。"""
    rows = []
    cur = None          # 当前框的文本行
    mode = None         # None / 'text'（TAB 正文）/ 'bare'（裸行正文）

    def flush():
        nonlocal cur, mode
        if cur is not None:
            body = ''.join(cur)
            if body.strip():
                rows.append(('box', body))
        cur = None
        mode = None

    def start(kind):
        nonlocal cur, mode
        if mode != kind:
            flush()
            cur = []
            mode = kind
        elif cur is None:
            cur = []

    for line in text.split('\n'):
        s = line.rstrip('\r')
        if s.startswith('\t'):
            # TAB 行＝当前框的正文
            start('text')
            body = s[1:]
            if body[:1] == IDEO_SP:        # 折行续行的悬挂缩进，剥一层
                body = body[1:]
            if body.strip() and body not in DROP_TEXT:
                cur.append(body)
            continue
        if not s.strip():
            continue
        if s.startswith('@@'):
            flush()                        # 任何演出命令都结束当前框
            if MSG.match(s):               # 消息命令 ⇒ 起一个新文本框
                cur, mode = [], 'text'
            continue
        if s.startswith(';') or s.startswith('//'):
            continue
        if s.startswith('__'):
            flush()
            continue
        if s.startswith(BARE_SKIP) or DASH_ONLY.match(s):
            continue
        # 裸行正文：自成一段（不与 TAB 正文同框），连续裸行仍属同一个框
        start('bare')
        cur.append(s)
    flush()
    return rows


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    files = sorted(f for f in os.listdir(src) if f.lower().endswith('.dat'))
    lines = []
    stats = []
    for f in files:
        texts = scripts_of(os.path.join(src, f))
        nbox = 0
        nbare = []
        for t in texts:
            for kind, payload in parse_script(t):
                if kind == 'box':
                    lines.append(payload)
                    nbox += 1
                else:
                    nbare.append(payload)
        stats.append((f, len(texts), nbox, nbare))
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(lines) + '\n')
    for f, ns, nbox, nbare in stats:
        print('%-46s scripts=%-2d boxes=%-5d bare=%s' % (f[:46], ns, nbox, nbare[:3]))
    print('TOTAL boxes=%d  bytes=%d  chars=%d'
          % (len(lines), os.path.getsize(dst), sum(len(x) for x in lines)))


if __name__ == '__main__':
    main()
