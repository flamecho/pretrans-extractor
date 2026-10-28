# -*- coding: utf-8 -*-
"""O*G*A 鬼ごっこロワイアル ハンターは孤島で恋をする (PSP-JP / Idea Factory・Otomate)

STS.DAT(.tob 脚本コンテナ) -> 正文・選択肢テキスト

格式（实测）
-----------
STS.DAT   = [5440 B 头部] + 271 × tob
tob       = [u32 'tob\0'][u32 size][u32 ver=1][u32 n]
            [u32 strOff][u32 0x28|0x2c][u32 0x20][u32 strEnd]
            + 代码区 + 字符串表
字符串表  = 4 字节对齐的 NUL 结尾串, **全字节 XOR 0xDA**, 内容为 cp932
            假名写成半角片假名(0xA1-0xDF), 汉字全角
          .vag = 该文本框的语音（语音名排在其框文本之后）
          ./../tob/x.tob / x.sts = 脚本自身名与标签命名空间

行粒度：一次点击 = 一行。⚠ 文本层只能近似：源串是**预折行**（单串 ≤25 字＝一行宽），
        作者的分框只写在 .tob 字节码里，字符串表无分隔标记。故按「句末优先 + 窗口行数」近似：
        上一串以 。！？!?」』 收尾（引号深度 0）／.vag 语音／已累积 maxlines 行 ⇒ 切框。
人名：白雲 + '＠'(可变名) ⇒ 默认名 美咲（EBOOT InputName 区字面量）。
"""
import re
import struct
import sys

XOR = 0xDA

# ★本作：**半角片假名＝原文的平假名**（真片假名词汇一律写成全角）
#   实证：世界ﾊ､突如現ﾚﾀ『新ﾀﾅﾙスポーツ』ﾆﾖﾘ
#         → `ca`=ﾊ(半角) / `83 58 83 7c 81 5b 83 63`=スポーツ(全角)
#   ⇒ 半角→**平假名**；全角片假名原样保留
_kana = "ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"
_hira = "をぁぃぅぇぉゃゅょっーあいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん"
HALF = {a: b for a, b in zip(_kana, _hira)}
HALF.update({"｡": "。", "｢": "「", "｣": "」", "､": "、", "･": "・"})
DAKU = {"か": "が", "き": "ぎ", "く": "ぐ", "け": "げ", "こ": "ご",
        "さ": "ざ", "し": "じ", "す": "ず", "せ": "ぜ", "そ": "ぞ",
        "た": "だ", "ち": "ぢ", "つ": "づ", "て": "で", "と": "ど",
        "は": "ば", "ひ": "び", "ふ": "ぶ", "へ": "べ", "ほ": "ぼ",
        "う": "ゔ", "わ": "ゎ"}
HANDAKU = {"は": "ぱ", "ひ": "ぴ", "ふ": "ぷ", "へ": "ぺ", "ほ": "ぽ"}

JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff01-\uff9f\u3000-\u303f]")
KANA = re.compile(r"[\u3040-\u30ff\uff66-\uff9f]")
LABEL = re.compile(r"^[A-Za-z0-9_./<>#%\-]{2,}$")
NAME_EXT = (".vag", ".tob", ".sts", ".sp2", ".mpb", ".dat")

# 系统/调试脚本（无正文；d00=启动路由, sts_deb=调试菜单, sts_omake/scene_play/sts_cmn=系统菜单）
EXCLUDE = {"d00", "sts_deb", "sts_omake", "scene_play", "sts_cmn", "r1_t1_01"}

HEROINE = "美咲"


def half_to_full(s):
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "ﾞﾟ":
            if out:
                prev = out[-1]
                out[-1] = (DAKU if c == "ﾞ" else HANDAKU).get(prev, prev)
            i += 1
            continue
        if i + 1 < n and s[i + 1] in "ﾞﾟ":
            base = HALF.get(c, c)
            out.append((DAKU if s[i + 1] == "ﾞ" else HANDAKU).get(base, base))
            i += 2
            continue
        out.append(HALF.get(c, c))
        i += 1
    return "".join(out)


def iter_tobs(d):
    for m in re.finditer(rb"tob\x00", d):
        p = m.start()
        hdr = struct.unpack("<8I", d[p:p + 32])
        if 32 < hdr[1] <= len(d) - p:
            yield p, hdr


def strtab(d, p, hdr):
    so, eo = hdr[4], hdr[7]
    if not (0 < so < eo <= hdr[1]):
        return []
    seg = bytes(v ^ XOR for v in d[p + so:p + eo])
    out, off = [], 0
    while off < len(seg):
        end = seg.find(b"\x00", off)
        if end < 0:
            break
        raw = seg[off:end]
        if raw and not (not out and len(raw) <= 4):
            out.append(raw.decode("cp932", "replace"))
        off = (end + 1 + 3) & ~3
    return out


def classify(s):
    """('text'|'voice'|'skip', 内容)"""
    t = s.strip()
    if not t:
        return "skip", ""
    low = t.lower()
    if low.endswith(NAME_EXT) or low.startswith("./"):
        return ("voice" if low.endswith(".vag") else "skip"), t
    if "<" in t or ">" in t or "\ufffd" in t:
        return "skip", t
    # 表头残留/2 字节垃圾记录里常夹 C0 控制符
    body = re.sub(r"[\x00-\x1f\x7f]", "", t)
    # 开头 1 字节样式码 (s / i / b / .)
    if len(body) > 1 and body[0] in "sib." and JP.match(body[1]):
        body = body[1:]
    if len(body) < 2 or LABEL.match(body) or not JP.search(body):
        return "skip", t
    # 标识符型标签：含下划线且无标点 / 全汉字无假名短串
    if "_" in body and not re.search(r"[。、…」』！？!?]", body):
        return "skip", t
    if len(body) <= 12 and not KANA.search(body) and not re.search(r"[。、…」』！？!?―‐\-｡｢｣､･]", body):
        return "skip", t
    return "text", body


def fix_name(s):
    s = re.sub(r"[ 　]*[@＠]チャン", HEROINE + "チャン", s)
    s = re.sub(r"[ 　]*[@＠]", HEROINE, s)
    return s


def depth(s):
    return s.count("「") + s.count("『") - s.count("」") - s.count("』")


def extract(d, maxlines=3):
    lines = []
    for p, hdr in iter_tobs(d):
        ss = strtab(d, p, hdr)
        name = next((s for s in ss[:3] if s.lower().endswith(".tob")), "")
        name = name.replace("./../tob/", "")[:-4]
        if name in EXCLUDE:
            continue
        cur = []
        for s in ss:
            kind, body = classify(s)
            if kind == "voice":
                # 语音名排在框文本之后；若引号尚未闭合，说明本框跨了多条语音
                if cur and (depth("".join(cur)) <= 0 or len(cur) >= 2 or len("".join(cur)) > 200):
                    lines.append(fix_name("".join(cur)))
                    cur = []
                continue
            if kind != "text":
                if "<switch_err>" in s:
                    # 选项组：分岐标记前的连续短串＝每项一行
                    if cur:
                        if all(len(x) <= 40 for x in cur) and len(cur) >= 2 and all(depth(x) == 0 for x in cur):
                            for x in cur:
                                lines.append(fix_name(x))
                        else:
                            lines.append(fix_name("".join(cur)))
                        cur = []
                continue
            txt = half_to_full(body)
            # 「……」收束：作者常在此处手动分框（用户实证）
            if cur and len(cur) >= 2 and depth("".join(cur)) <= 0 and cur[-1].endswith("……"):
                lines.append(fix_name("".join(cur)))
                cur = []
            if cur and (len(cur) >= maxlines or len("".join(cur)) > 240):
                lines.append(fix_name("".join(cur)))
                cur = []
            if cur:
                joined = "".join(cur)
                if depth(joined) <= 0 and cur[-1][-1:] in "。！？!?」』":
                    lines.append(fix_name(joined))
                    cur = []
                elif depth(joined) <= 0 and joined[-1:] in "。！？" and txt[:1] in "「『":
                    lines.append(fix_name(joined))
                    cur = []
            cur.append(txt)
        if cur:
            lines.append(fix_name("".join(cur)))
    return lines


def rebalance(lines):
    """切框把「…」切成两行时，向前合并直到配对（源侧真正缺 」 的少数行会保留，另行定值表处理）"""
    out = lines
    # 切框残留：左引号多于右引号 → 行尾补 」；右引号多于左引号 → 行首补 「
    fixed = []
    for ln in out:
        o, c = ln.count("「") + ln.count("『"), ln.count("」") + ln.count("』")
        if o > c:
            ln = ln + "」" * (o - c)
        elif c > o:
            ln = "「" * (c - o) + ln
        fixed.append(ln)
    return fixed


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    ml = 3
    for a in sys.argv[1:]:
        if a.startswith("--maxlines"):
            ml = int(a.split("=")[1]) if "=" in a else 3
        elif a.isdigit():
            ml = int(a)
    src, dst = argv[0], argv[1]
    out = rebalance(extract(open(src, "rb").read(), maxlines=ml))
    with open(dst, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("lines", len(out))
