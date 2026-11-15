import os, re, glob
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SCN = os.path.join(VNTRANS_HOME, "_work_powdergray/out/package/data/scenario")
OUT = os.path.join(VNTRANS_HOME, "提取结果/[JP]powdergray.txt")

# 块：仅取 [tb_start_text ...] ... [_tb_end_text] 之间（L0 边界）
BLOCK_RE = re.compile(r"\[tb_start_text[^\]]*\](.*?)\[_tb_end_text\]", re.S)
# 页分隔：[p]（清框换页 -> 新框）
PAGE_RE = re.compile(r"\[p\b[^\]]*\]")
TAG_RE = re.compile(r"\[[^\]]*\]")          # 其余所有 [tag]
RUBY_BASE = re.compile(r"\[ruby[^]]*?base=\"([^\"]*)\"[^]]*?\]")
RUBY_PLAIN = re.compile(r"\[ruby[^]]*?\]")

# 系统属性泄漏安全网（不应出现在对白里）
LEAK = ("storage=", "layer=", "page=", "visible=", "vertical=", "backvisible=",
        "left=", "top=", "opacity=", "frame=", "cond=", "target=", "buf=",
        "sysbtn", "exp=", "edgecolor=", "face=", "size=", "color=", "method=",
        "time=", "repage=", "volume=", "loop=", "fadein=", "crossfade=",
        "buf=", "wait=", "effect=", "name=")

def clean_page(page):
    # 行内换行 = 文件折行 -> 合并
    page = page.replace("\r", "").replace("\n", "")
    # ruby：优先保留 base= 属性里的基字；否则删标签（基字以字面量跟在标签后）
    page = RUBY_BASE.sub(r"\1", page)
    page = RUBY_PLAIN.sub("", page)
    # 删所有 [tag]（[l]/[r]/[chara...]/[ruby 残り] 等），保留标签之间的正文
    page = TAG_RE.sub("", page)
    # 全角・半角空白压缩（保留文字间原意，仅压连续空白）
    page = re.sub(r"[ \t\u3000]+", " ", page)
    return page.strip()

def extract_file(path):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        t = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        t = raw.decode("cp932", errors="ignore")
    lines = []
    for m in BLOCK_RE.finditer(t):
        block = m.group(1)
        for page in PAGE_RE.split(block):
            txt = clean_page(page)
            if not txt:
                continue
            if any(k in txt for k in LEAK):
                continue
            lines.append(txt)
    return lines

def main():
    files = []
    for root, _, fs in os.walk(SCN):
        for fn in fs:
            if not fn.lower().endswith(".ks"):
                continue
            full = os.path.join(root, fn)
            if os.sep + "system" + os.sep in full.replace("/", os.sep):
                continue   # 预载桩，跳过
            files.append(full)
    # 仅含 tb_start_text 的主文件；按文件名自然序（章节顺序）
    SKIP = {"config.ks"}  # 系统 UI（菜单标题 ■■■ 占位块）
    cand = []
    for fp in files:
        rel = os.path.relpath(fp, SCN)
        if os.path.basename(fp) in SKIP:
            continue
        with open(fp, "rb") as f:
            if b"tb_start_text" in f.read(200000):
                cand.append(fp)
    cand.sort()
    all_lines = []
    print("%-34s -> lines" % "file")
    for fp in cand:
        ls = extract_file(fp)
        rel = os.path.relpath(fp, SCN)
        print("%-34s -> %d" % (rel, len(ls)))
        all_lines.extend(ls)
    # 保全文：不做相邻去重（相邻同文交由 check_text 标注 [W]，避免误删正文）
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as fh:
        fh.write("\n".join(all_lines) + "\n")
    print("TOTAL %d lines -> %s" % (len(all_lines), OUT))

if __name__ == "__main__":
    main()
