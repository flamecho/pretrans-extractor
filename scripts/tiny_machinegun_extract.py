#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tiny×MACHINEGUN THE GAME  (Rejet / PC-JP)  剧本・辞典文本提取器  —— 端到端定稿
================================================================================
容器链路：
  SFX .exe (RAR5, offset 0x48E00)
    -> 7z 解包 (TinyMachinegun/TinyMachinegun/{Module,Resource})
    -> Resource/Scenario.rpd  ── 整文件 XOR 0xFF ──> 索引 + 脚本区
    -> 索引: u32 h0 | u32 count | count×{u32 namelen, name(cp932), u32 size, u32 off, u32 flag}
    -> 取出 *.lt（明文 XML 风标签脚本，utf... 实为 cp932）
    -> 按 <pb>(=AlreadyReadTextDelimiter) 切分「一次点击」消息
  Module/gd.dat ── XOR 0xFF ──> SQLite；table `tips` = 用語辞典

关键判据（引擎配置 Module/pf.dat, Boost-XML）：
  <AlreadyReadTextDelimiter>pb</AlreadyReadTextDelimiter>  → 一个 <pb> = 一个文本框 = 一次点击
  <StartScriptFile>LTStart</StartScriptFile>              → 入口 ltstart.lt

用法：
  python tiny_machinegun_extract.py <游戏exe 或 已解包目录> [输出txt]
  例：
  python tiny_machinegun_extract.py "[PC-JP]Tiny x Machinegun.exe" out.txt
  python tiny_machinegun_extract.py ./TinyMachinegun/TinyMachinegun out.txt
"""
import sys, os, re, io, struct, sqlite3, subprocess, tempfile, shutil

SEVENZ = os.environ.get('SEVENZ', r"C:\Program Files\7-Zip\7z.exe")
XOR = lambda b: bytes(x ^ 0xFF for x in b)

TAGRE = re.compile(r"<[^>]*>")
PBRE = re.compile(r"<pb\b[^>]*>", re.I)
CASERE = re.compile(r"<case\b[^>]*>", re.I)
VALUE = re.compile(r'value\s*=\s*"([^"]*)"')
JUMPFILE = re.compile(r'<jump\s+file\s*=\s*"([^"]+)"', re.I)


def strip_tags(s):
    """删除 <...> 标签；引号内的 '>'（如 condition="A >= B"）不当作标签结束。"""
    out, i, n = [], 0, len(s)
    while i < n:
        if s[i] == "<":
            j, inq = i + 1, False
            while j < n:
                c = s[j]
                if c == '"':
                    inq = not inq
                elif c == ">" and not inq:
                    break
                j += 1
            i = j + 1          # 跳过整个标签（未闭合则跳到行尾）
            continue
        out.append(s[i]); i += 1
    return "".join(out)



# --------------------------------------------------------------------------- #
# 1) 解包 / 定位
# --------------------------------------------------------------------------- #
def locate_game(src):
    """返回 (Module目录, Resource目录)。src 可为 SFX exe 或已解包目录。"""
    if os.path.isfile(src):
        tmp = tempfile.mkdtemp(prefix="tm_")
        subprocess.run([SEVENZ, "x", "-y", "-o" + tmp, src,
                        "TinyMachinegun/TinyMachinegun/Module/*",
                        "TinyMachinegun/TinyMachinegun/Resource/Scenario.rpd"],
                       check=True, stdout=subprocess.DEVNULL)
        base = os.path.join(tmp, "TinyMachinegun", "TinyMachinegun")
        return base, tmp
    # 目录：可能是 .../TinyMachinegun 或 .../TinyMachinegun/TinyMachinegun
    for cand in (src, os.path.join(src, "TinyMachinegun"),
                 os.path.join(src, "TinyMachinegun", "TinyMachinegun")):
        if os.path.isdir(os.path.join(cand, "Module")) and \
           os.path.isdir(os.path.join(cand, "Resource")):
            return cand, None
    raise SystemExit("找不到 Module/ 与 Resource/：" + src)


def parse_rpd(path):
    """返回 [(name, bytes)]。整文件 XOR 0xFF。"""
    dec = XOR(open(path, "rb").read())
    _, count = struct.unpack_from("<II", dec, 0)
    off, out = 8, []
    for _ in range(count):
        nl = struct.unpack_from("<I", dec, off)[0]
        name = dec[off + 4:off + 4 + nl].decode("cp932")
        size, doff, _flag = struct.unpack_from("<III", dec, off + 4 + nl)
        out.append((name, dec[doff:doff + size]))
        off += 4 + nl + 12
    return out


# --------------------------------------------------------------------------- #
# 2) .lt 脚本解析
# --------------------------------------------------------------------------- #
def parse_lt(text):
    """
    顺序产出 ('msg', 正文) / ('choice', 选项文本)。
    规则：
      · 以 // 开头 = 注释，剔除；
      · 剥掉全部 <tag>，余下即显示文本（<tips>/<color> 的包裹文本保留）；
      · ＠名字 行 = 说话人（本管线不加前缀，直接丢弃该行）；
      · 一行内出现 <pb> → 结束当前文本框（= 一次点击），框内物理换行合并；
      · <case value="…"> → 一个选项，单独成行。
    """
    out, buf = [], []

    def flush():
        if buf:
            s = "".join(buf).strip()
            if s:
                out.append(("msg", s))
            buf.clear()

    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        st = line.strip()
        if not st or st.startswith("//"):
            continue
        for m in CASERE.finditer(line):
            v = VALUE.search(m.group(0))
            if v:
                out.append(("choice", v.group(1).strip()))
        # 去标签，再去行内 // 注释（全库仅 <set ...>//备注 与 "…。"//台詞無し 两类）
        txt = strip_tags(line).split("//")[0].strip()
        # ＠名字 = 说话人（本管线不加前缀）；可能被 <color> 包裹，故在去标签后再判
        if txt.startswith("＠"):
            txt = ""
        if txt:
            buf.append(txt)
        if PBRE.search(line):
            flush()
    flush()
    return out


def build_order(files):
    """从 ltstart 起，按 <jump file> 调用图 DFS 前序（= 实际执行顺序）。"""
    low = {k.lower(): k for k in files}
    graph = {k: JUMPFILE.findall(v.decode("cp932", "replace"))
             for k, v in files.items()}
    order = []

    def dfs(n):
        n = low.get(n.lower(), n)
        if n in order or n not in graph:
            return
        order.append(n)
        for m in graph[n]:
            dfs(m)

    dfs("ltstart")
    return order, graph


# --------------------------------------------------------------------------- #
# 3) 辞典
# --------------------------------------------------------------------------- #
def load_tips(gd_path):
    """gd.dat -> SQLite -> tips 表。返回 [(word, explain)]，按 id。"""
    tmp = gd_path + ".sqlite"
    open(tmp, "wb").write(XOR(open(gd_path, "rb").read()))
    con = sqlite3.connect(tmp)
    rows = con.execute(
        "select word, explain from tips order by id").fetchall()
    con.close()
    os.remove(tmp)
    return rows


def load_gd_extra(gd_path):
    """gd.dat 中其余面向玩家的文本：回想标题 / ボイス解锁条件 / ボイス菜单项。"""
    tmp = gd_path + ".sqlite"
    open(tmp, "wb").write(XOR(open(gd_path, "rb").read()))
    con = sqlite3.connect(tmp)
    recall = [r[0] for r in con.execute(
        "select title from special_subscenario_item order by rowid")]
    unlock = [r[0] for r in con.execute(
        "select description from special_voice_vol order by rowid")]
    vmenu, seen = [], set()
    for (t,) in con.execute(
            "select title from special_voice_menu order by character_id, vol_id, voice_id"):
        t = t.strip()
        if t and t not in seen:
            seen.add(t); vmenu.append(t)
    con.close()
    os.remove(tmp)
    return recall, unlock, vmenu


def load_pf_dialog(pf_path):
    """pf.dat（Boost-XML，XOR 0xFF）中的确认对话框文本 <Messages>…。</Messages>。"""
    t = XOR(open(pf_path, "rb").read()).decode("cp932", "replace")
    blk = re.search(r"<Messages\b.*?</Messages>", t, re.S)
    if not blk:
        return []
    out = []
    for m in re.finditer(r"<([A-Za-z]+)>(.*?)</\1>", blk.group(0), re.S):
        out.append(m.group(2).replace("\\n", "").replace("\n", "").strip())
    return [x for x in out if x]


def clean_dict(s):
    return (s.replace("<br>", "").replace("\r", "").replace("\n", "")).strip()



# --------------------------------------------------------------------------- #
# 4) 主流程
# --------------------------------------------------------------------------- #
def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "TinyMACHINEGUN_全文本.txt"

    base, tmp = locate_game(src)
    try:
        rpd = os.path.join(base, "Resource", "Scenario.rpd")
        scn = {os.path.splitext(os.path.basename(n))[0]: d
               for n, d in parse_rpd(rpd)}
        order, _ = build_order(scn)
        skipped = [k for k in scn if k not in order and not k.startswith("シーン回想")]

        lines = []
        for name in order:
            for kind, txt in parse_lt(scn[name].decode("cp932", "replace")):
                lines.append(txt)
        story_n = len(lines)

        gd = os.path.join(base, "Module", "gd.dat")
        # 用語辞典
        tips = load_tips(gd)
        for w, e in tips:
            lines.append("【%s】%s" % (w, clean_dict(e)))
        dict_n = len(lines) - story_n

        # 其余面向玩家文本：回想标题 / ボイス解锁条件 / ボイス菜单项 / 系统确认对话框
        recall, unlock, vmenu = load_gd_extra(gd)
        lines += [t.strip() for t in recall]
        lines += vmenu
        lines += [u.strip() for u in unlock]
        lines += load_pf_dialog(os.path.join(base, "Module", "pf.dat"))
        ui_n = len(lines) - story_n - dict_n

        # 写出：UTF-8-BOM / LF
        with io.open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
            for ln in lines:
                f.write(ln + "\n")

        print("剧本文件 DFS序 %d 个；未入序（非回想）%s" % (len(order), skipped))
        print("剧本 %d 行 + 辞典 %d 行 + 系统/UI %d 行 = %d 行 -> %s"
              % (story_n, dict_n, ui_n, len(lines), out_path))
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
