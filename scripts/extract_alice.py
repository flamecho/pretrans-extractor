"""Extract scenario text from the Alice-series PSP games (QuinRose).

Handles BOTH container types used across the 6 games:
  - CRI CPK  (older engine): DATA.cpk / DATA0.cpk ... containing scenario/*.ks
                scripts are UTF-16LE (BOM) KAG, protagonist placeholder = [firstname]
  - Qoo QPK  (newer engine): DATA0.QPK/DATA0.QPI containing KAG .ks (cp932),
                protagonist placeholder = [print value="firstname"]

Output standard (same as the previously processed Arabians games):
  - one line per [message] / [select] choice
  - original Japanese only (no translation, no annotations, no line numbers)
  - control codes / ruby / in-box newlines stripped
  - archive order
  - NO speaker-name prefix
  - protagonist name filled: firstname->given, familyname/lastname->surname
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- protagonist default name (user: アリス / リデル) ----
GIVEN = "アリス"
SURNAME = "リデル"
FULL = GIVEN + "＝" + SURNAME

NAME_MAP = {
    "firstname": GIVEN, "givenname": GIVEN, "inputname": GIVEN, "given": GIVEN,
    "familyname": SURNAME, "lastname": SURNAME, "surname": SURNAME,
    "fullname": FULL, "full": FULL,
}
_LIT_RE = re.compile(r"\[(firstname|givenname|inputname|given|familyname|lastname|surname|fullname|full)\]", re.I)


def decode(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return raw.decode("utf-16")
        except Exception:
            pass
    if b"\x00" in raw[:400]:
        for enc in ("utf-16-le", "utf-16-be"):
            try:
                return raw.decode(enc)
            except Exception:
                pass
    for enc in ("utf-8", "cp932"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("cp932", "replace")


_NL = "\n"


def _fill_print_q(m):
    v = m.group(1).lower()
    return NAME_MAP.get(v, m.group(0))


def _fill_print_bare(m):
    v = m.group(1).lower()
    return NAME_MAP.get(v, m.group(0))


def _fill_lit(m):
    v = m.group(1).lower()
    return NAME_MAP.get(v, m.group(0))


def fill_heroine(body):
    # [print value="firstname"]  (QPK engine)  / [print value=firstname]
    body = re.sub(r'\[print\b[^\]]*?value=["\']?([A-Za-z_]+)["\']?[^\]]*\]', _fill_print_q, body, flags=re.I)
    # literal [firstname]  (CPK engine)
    body = _LIT_RE.sub(_fill_lit, body)
    return body


def clean_inner(s):
    s = fill_heroine(s)
    # in-box newline
    s = re.sub(r"\[/?br\b[^\]]*\]", "", s, flags=re.I)
    # ruby / furigana
    for tag in ("ruby", "rb", "rt", "rup"):
        s = re.sub(r"\[/%s\]" % tag, "", s, flags=re.I)
        s = re.sub(r"\[%s\b[^\]]*\]" % tag, "", s, flags=re.I)
    # any leftover control tags (font [f], [i], [u], etc.) -> strip, keep text
    s = re.sub(r"\[/?[A-Za-z_]+\b[^\]]*\]", "", s)
    s = s.replace("\r", "").replace("\n", "").replace("\t", " ")
    s = re.sub(r"[ \t\u3000]+", " ", s)
    return s.strip()


TOKEN_RE = re.compile(
    r"\[message\b[^\]]*\].*?\[/message\]"
    r"|\[(?:select|selectcom|link)\b[^\]]*\]",
    re.S | re.I,
)


def parse_script(txt):
    lines = []
    for m in TOKEN_RE.finditer(txt):
        tok = m.group(0)
        if tok.lower().startswith("[message"):
            bm = re.search(r"\[message\b[^\]]*\](.*?)\[/message\]", tok, re.S | re.I)
            if not bm:
                continue
            inner = clean_inner(bm.group(1))
            if inner:
                lines.append(inner)
        else:
            wm = re.search(r'\b(?:word|text)="([^"]*)"', tok, re.I)
            if wm:
                inner = clean_inner(wm.group(1))
                if inner:
                    lines.append(inner)
    return lines


# ---------------- container backends ----------------

def extract_qpk(qpi_path, qpk_path):
    from qpk import QPK
    q = QPK(qpi_path, qpk_path)
    out = []
    for txt in q.iter_scripts():
        out.extend(parse_script(txt))
    return out


_SCRIPT_EXT = (".ks", ".scn", ".txt")


def extract_cpk(cpk_path):
    from cpk import CPK
    cpk = CPK(cpk_path)
    out = []
    found = False
    for e in cpk.entries:
        nm = e.get("name")
        if not nm or not nm.lower().endswith(_SCRIPT_EXT):
            continue
        try:
            raw = cpk.raw(e)
        except Exception:
            continue
        txt = decode(raw)
        if "[message" not in txt and "[select" not in txt:
            continue
        found = True
        out.extend(parse_script(txt))
    if not found:
        # fallback: scan every entry for KAG content
        for e in cpk.entries:
            try:
                raw = cpk.raw(e)
            except Exception:
                continue
            txt = decode(raw)
            if "[message" in txt:
                out.extend(parse_script(txt))
    return out


if __name__ == "__main__":
    kind = sys.argv[1]
    if kind == "qpk":
        lines = extract_qpk(sys.argv[2], sys.argv[3])
    else:
        lines = extract_cpk(sys.argv[2])
    for ln in lines[:20]:
        print(ln)
    print("... total lines:", len(lines))
