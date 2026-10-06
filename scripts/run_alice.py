"""Batch extract scenario text from the 6 Alice-series PSP ISOs.

For each ISO:
  - find DATA0.QPI/DATA0.QPK, DATA1.QPI/DATA1.QPK, ... inside PSP_GAME/USRDIR/DATA/
  - extract each QPI/QPK pair to a temp dir
  - parse every KAG scenario via extract_alice.extract_game
  - concatenate (in pack order) and write one UTF-8-sig file per game
  - delete the temp QPK/QPI files for that ISO
"""
import os
import re
import sys
import glob
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_alice import extract_qpk, extract_cpk

HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
Z = os.environ.get('SEVENZ', r"C:\Program Files\7-Zip\7z.exe")
ISO_DIR = HOME
OUT_DIR = HOME
TMP = os.path.join(HOME, 'tmp_alice')

# (required_substrings, exclude_substring_or_None, output_base_name)
GAMES = [
    (("おもちゃ箱",), None, "おもちゃ箱の国のアリス"),
    (("ジョーカー",), None, "ジョーカーの国のアリス"),
    (("ダイヤ", "Mirror"), None, "ダイヤの国のアリス_MirrorWorld"),
    (("ダイヤ", "Wonderful"), "Mirror", "ダイヤの国のアリス"),
    (("ハート",), None, "ハートの国のアリス_TwinWorld"),
    (("クローバー",), None, "クローバーの国のアリス"),
]


def find_iso(required, exclude):
    for f in os.listdir(ISO_DIR):
        if not f.lower().endswith(".iso"):
            continue
        if all(s in f for s in required) and (exclude is None or exclude not in f):
            return os.path.join(ISO_DIR, f)
    return None


def list_members(iso):
    # plain listing (rc is 0 even with minor "Errors: 1"); -slt is unreliable on UMD ISOs
    out = subprocess.run([Z, "l", iso], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    text = out.stdout.decode("cp437", "replace")
    qpk, qpi, cpk = [], [], []
    for ln in text.splitlines():
        m = re.search(r"([\S]*\.(?:QPK|QPI|CPK))$", ln, re.I)
        if not m:
            continue
        p = m.group(1).replace("\\", "/")
        up = p.upper()
        if up.endswith(".QPK"):
            qpk.append(p)
        elif up.endswith(".QPI"):
            qpi.append(p)
        else:
            cpk.append(p)
    return qpk, qpi, cpk


def extract_member(iso, member, dest):
    # NOTE: these UMD ISOs report "Errors: 1" (minor read quirk), so 7z returns
    # rc=2 even on a successful extraction -> ignore the return code.
    subprocess.run([Z, "x", "-y", "-o" + dest, iso, member],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_one(iso_path, out_name):
    # 7z is an ANSI app and mangles Unicode paths passed via subprocess;
    # work around by creating an ASCII-named hardlink to the ISO.
    import hashlib
    os.makedirs(TMP, exist_ok=True)
    link_name = "iso_" + hashlib.md5(out_name.encode("utf-8")).hexdigest()[:10] + ".iso"
    link = os.path.join(TMP, link_name)
    if os.path.exists(link):
        os.remove(link)
    os.link(iso_path, link)
    all_lines = []
    per_pack = []
    work = os.path.join(TMP, "work_" + hashlib.md5(out_name.encode("utf-8")).hexdigest()[:10])
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    try:
        qpks, qpis, cpks = list_members(link)

        # --- QPK / QPI pairs ---
        qpi_map = {os.path.splitext(os.path.basename(m))[0]: m for m in qpis}
        bases = sorted({os.path.splitext(os.path.basename(m))[0] for m in qpks})
        for base in bases:
            qpk_member = next((m for m in qpks if os.path.splitext(os.path.basename(m))[0] == base), None)
            qpi_member = qpi_map.get(base)
            if not qpk_member or not qpi_member:
                continue
            sub = os.path.join(work, base)
            os.makedirs(sub, exist_ok=True)
            extract_member(link, qpk_member, sub)
            extract_member(link, qpi_member, sub)
            qpk_file = glob.glob(os.path.join(sub, "**", base + ".QPK"), recursive=True)[0]
            qpi_file = glob.glob(os.path.join(sub, "**", base + ".QPI"), recursive=True)[0]
            try:
                lines = extract_qpk(qpi_file, qpk_file)
            except Exception as e:
                lines = []
                print("  [%s] ERROR: %s" % (base, e), file=sys.stderr)
            per_pack.append((base, len(lines)))
            all_lines.extend(lines)
            shutil.rmtree(sub, ignore_errors=True)

        # --- CPK files (one at a time, delete after processing) ---
        for member in cpks:
            sub = os.path.join(work, "cpk")
            if os.path.exists(sub):
                shutil.rmtree(sub, ignore_errors=True)
            os.makedirs(sub, exist_ok=True)
            extract_member(link, member, sub)
            cpath = glob.glob(os.path.join(sub, "**", os.path.basename(member).replace("\\", "/")), recursive=True)
            if not cpath:
                cpath = glob.glob(os.path.join(sub, "**", "*.cpk"), recursive=True)
            if not cpath:
                continue
            try:
                lines = extract_cpk(cpath[0])
            except Exception as e:
                lines = []
                print("  [%s] ERROR: %s" % (member, e), file=sys.stderr)
            per_pack.append((os.path.basename(member), len(lines)))
            all_lines.extend(lines)
            shutil.rmtree(sub, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if os.path.exists(link):
            os.remove(link)
    out_path = os.path.join(OUT_DIR, out_name + ".txt")
    with open(out_path, "w", encoding="utf-8-sig") as f:
        for ln in all_lines:
            f.write(ln + "\n")
    print("%-28s -> %s  (%d lines)  packs: %s" %
          (out_name, out_path, len(all_lines), per_pack))
    return len(all_lines)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    for required, exclude, out_name in GAMES:
        if only and out_name != only:
            continue
        iso = find_iso(required, exclude)
        if not iso:
            print("ISO not found for", required, file=sys.stderr)
            continue
        print("Processing:", os.path.basename(iso))
        n = run_one(iso, out_name)
        total += n
    print("DONE. total lines:", total)


if __name__ == "__main__":
    main()
