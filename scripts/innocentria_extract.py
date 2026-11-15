"""Extract Innocentria (NScripter 2.48 / game script ver.1.1).

The caller supplies the encrypted nscript.dat, output text, and evidence directory.
The two runtime total-time lines use an explicitly authorized placeholder.
No global deduplication or punctuation repair is performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

COLOR = re.compile(r"#[0-9a-fA-F]{6}")
RUBY = re.compile(r"\(([^()/]+)/([^()/]+)\)")
NAME = re.compile(r"(?:【[^】]*】)+")
COMMAND = re.compile(r"[A-Za-z_]")
MACRO = re.compile(r"\$\d+|%\d+")

# Actual interactive counter/result displays. Dialogue instructions and the
# story scenes before/after the games are retained.
GAME_UI_LABELS = {"newfinder", "finder3", "kei_scor", "kei_reco"}
IMAGE_TEXT = {
    "sys\\mono01.bmp": "君の声、君の瞳、君の笑顔",
    "sys\\mono02.bmp": "忘れはしない",
    "sys\\mono03.bmp": "たとえ、この世界で君を知る最後の１人となっても",
    "sys\\mono04.bmp": "永遠に",  # The preceding horizontal rule is a graphic decoration.
    "sys\\omake_dai1.jpg": "キャッツ・アイ",
    "sys\\omake_dai2.jpg": "ひつじ",
    "sys\\omake_dai3.jpg": "ツッコミ",
    "sys\\omake_dai4.jpg": "被虐精神",
    "sys\\omake_dai5.jpg": "属性",
    "sys\\omake_dai6.jpg": "萌え",
    "sys\\omake_dai0.jpg": "終",
}
IMAGE_TEXT.update({f"sys\\inter{i:02}.jpg": f"Interval-{i:02}" for i in range(16)})
IMAGE_TEXT["sys\\inter02b.jpg"] = "Interval-2b"
IMAGE_TEXT.update({f"sys\\day_{i}.bmp": f"The {ordinal} day"
                   for i, ordinal in enumerate(["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"], 1)})
IMAGE_TEXT.update({"sys\\day_next.bmp": "The next day", "sys\\day_other.bmp": "Other days"})
IMAGE_TEXT["bg\\trueend.jpg"] = "TRUE END"
IMAGE_CHOICES = {"sys\\kyositu_sel1.jpg": "・めがね",
                 "sys\\kyositu_sel2.jpg": "・騎士",
                 "sys\\kyositu_sel3.jpg": "・TRUE"}


def plain(text: str, time_value: str) -> str:
    text = text.replace("$777", "ルミナ").replace("%200", time_value)
    text = COLOR.sub("", text)
    text = RUBY.sub(r"\1", text)
    if MACRO.search(text) or "$" in text or "%" in text:
        raise ValueError(f"Unresolved displayed variable: {text}")
    return text


def strip_command_comment(text: str) -> str:
    quoted = False
    for i, ch in enumerate(text):
        if ch == '"':
            quoted = not quoted
        if ch == ";" and not quoted:
            return text[:i]
    return text


def extract(dat: Path, out: Path, work: Path, time_value: str):
    encrypted = dat.read_bytes()
    if hashlib.sha256(encrypted).hexdigest() != "49d8281b4a5292c94e3ad411ccee2cc4db072c6cee7b90f7042e78b038884980":
        raise ValueError("This extractor is verified for the bundled ver.1.1 script only")
    script = bytes(c ^ 0x84 for c in encrypted).decode("cp932")
    raw_lines = script.splitlines()
    work.mkdir(parents=True, exist_ok=True)
    (work / "nscript_decoded.txt").write_text(script, encoding="utf-8", newline="\n")

    rows: list[str] = []
    source: list[dict] = []
    excluded: list[dict] = []
    labels: dict[str, dict] = {}
    stats = Counter()
    pending: list[str] = []
    pending_src: list[int] = []
    page_segments: list[dict] = []
    all_pages: list[dict] = []
    dual_pages: list[dict] = []
    label = ""
    speaker = ""
    speaker_line = 0
    window = [30, 3]
    display_rows: list[str] = []
    max_rows = []
    route_terminated = False

    def append(text, kind, linenos, **extra):
        if not text:
            return
        rows.append(text)
        source.append(dict(output=len(rows), kind=kind, source=linenos, label=label, **extra))
        stats[kind] += 1

    def click():
        if pending:
            text = "".join(pending).strip()
            if text:
                page_segments.append(dict(text=text, source=list(pending_src), speaker=speaker))
        pending.clear()
        pending_src.clear()

    def page(reason, boundary_line):
        nonlocal speaker, speaker_line
        click()
        if page_segments:
            page_id = len(all_pages) + 1
            start = len(rows) + 1
            for n, segment in enumerate(page_segments):
                # Name text is actually drawn as this page's first row.
                prefix = speaker if n == 0 else ""
                text = prefix + segment["text"]
                append(text, "body", segment["source"], speaker=prefix,
                       name_source=speaker_line or None, page=page_id)
            page_map = dict(page=page_id, outputs=list(range(start, len(rows) + 1)),
                            boundary=reason, boundary_line=boundary_line,
                            window=list(window), raw_display_rows=list(display_rows))
            if len(page_segments) > 1:
                text = speaker + "".join(s["text"] for s in page_segments)
                append(text, "merged", [n for s in page_segments for n in s["source"]], page=page_id)
                dual_pages.append(dict(segments=page_map["outputs"], merged=len(rows), merged_text=text))
            all_pages.append(page_map)
            if len(display_rows) > window[1]:
                max_rows.append(page_map)
        elif display_rows or speaker:
            stats["name_or_blank_only_page"] += 1
        stats["boundary_" + reason] += 1
        page_segments.clear()
        display_rows.clear()
        speaker = ""
        speaker_line = 0

    def text(line, lineno):
        nonlocal speaker, speaker_line
        line = plain(line, time_value).strip()
        if NAME.fullmatch(line):
            if speaker:
                raise ValueError(f"Multiple name records without a page boundary at {lineno}")
            speaker = "".join(re.findall(r"【([^】]*)】", line))
            speaker_line = lineno
            display_rows.append(line)
            stats["name_records"] += 1
            # This exact source record precedes a narrated scene transition,
            # rather than dialogue: lecture ends, lecturer leaves, hall noise.
            if lineno == 15565:
                speaker = ""
                stats["narration_name_suppressed"] += 1
            return
        display_line = []
        for ch in line:
            if ch in "\\@":
                if display_line:
                    display_rows.append("".join(display_line))
                    display_line.clear()
                if ch == "\\":
                    stats["explicit_page_marks"] += 1
                    page("backslash", lineno)
                else:
                    stats["explicit_click_marks"] += 1
                    click()
            else:
                if not pending_src or pending_src[-1] != lineno:
                    pending_src.append(lineno)
                pending.append(ch)
                display_line.append(ch)
        if display_line:
            display_rows.append("".join(display_line))

    for lineno, raw in enumerate(raw_lines, 1):
        s = raw.strip()
        if s.startswith("*"):
            label = s[1:].split(";")[0].split()[0]
            labels[label] = dict(line=lineno, text_lines=0, scope="system")
            route_terminated = False
            continue
        if not s or s.startswith(";"):
            continue
        in_story = (2412 <= lineno < 69124) or lineno >= 71076
        scope = "body" if in_story and label not in GAME_UI_LABELS else "system"
        if route_terminated:
            scope = "unreachable_after_jump"
        labels[label]["scope"] = scope
        if not COMMAND.match(s) and not s.startswith((":", "~", '"')):
            labels[label]["text_lines"] += 1
            if scope != "body":
                excluded.append(dict(line=lineno, label=label, reason=scope, text=s))
                stats["excluded_text_lines"] += 1
                continue
            stats["source_text_lines"] += 1
            text(s, lineno)
            continue
        cmd = strip_command_comment(s)
        if scope != "body":
            continue
        # Choices use the csel pool and customsel/cselbtn drawing, rather than
        # image filename strings or menu callbacks.
        if cmd.startswith("csel "):
            page("choice", lineno)
            choices = re.findall(r'"([^"]*)"\s*,\s*\*([A-Za-z0-9_]+)', cmd)
            if not choices:
                raise ValueError(f"Unparsed choice command at {lineno}")
            stats["choice_commands"] += 1
            for choice, target in choices:
                append(plain(choice, time_value), "choice", [lineno], target=target)
            route_terminated = True
            continue
        if cmd == "click":
            click()
            stats["click_commands"] += 1
        if cmd.startswith("textclear") or re.match(r"gosub \*winset[123]\b", cmd) or cmd.startswith("setwindow "):
            page("clear_or_window", lineno)
        if cmd.startswith("setwindow "):
            m = re.match(r"setwindow\s+\d+,\d+,(\d+),(\d+)", cmd)
            if not m:
                raise ValueError(f"Unparsed window at {lineno}")
            window[:] = [int(m[1]), int(m[2])]
        elif re.match(r"gosub \*winset[123]\b", cmd):
            window[:] = [30, 3]
        if cmd.startswith(("goto ", "end")):
            page("flow", lineno)
            route_terminated = True
        # Timed sprite monologues are accumulated until their actual csp -1.
        if cmd.startswith("csp -1") and pending and label == "prologue2":
            page("sprite_clear", lineno)
        if re.match(r"lsp\s+\d+,\":s/", cmd):
            match = re.match(r'lsp\s+\d+,"(:s/[^;]*;[^\"]*)"', cmd)
            if not match:
                raise ValueError(f"Unparsed text sprite at {lineno}")
            sprite = plain(match[1].split(";", 1)[1], time_value).strip()
            pending.append(sprite)
            pending_src.append(lineno)
            stats["sprite_text_records"] += 1
        for filename in re.findall(r'"([^\"]+)"', cmd):
            if filename.startswith(":") and ";" in filename:
                filename = filename.split(";", 1)[1]
            filename = filename.replace("/", "\\")
            if filename in IMAGE_CHOICES:
                page("image_choice", lineno)
                append(IMAGE_CHOICES[filename], "choice", [lineno], asset=filename)
                stats["image_choice_records"] += 1
            if filename in IMAGE_TEXT:
                value = IMAGE_TEXT[filename]
                if not value:
                    raise ValueError(f"Image caption not verified: {filename}")
                # Image effects replace the preceding visible caption group.
                if not filename.startswith("sys\\mono"):
                    page("image_caption", lineno)
                    append(value, "image_caption", [lineno], asset=filename)
                else:
                    pending.append(value)
                    pending_src.append(lineno)
                    stats["image_text_records"] += 1
        if label == "prologue" and cmd.startswith("delay 500") and stats["image_text_records"] == 4:
            page("image_group", lineno)

    page("eof", len(raw_lines))
    if any("\n" in row or "\r" in row or not row.strip() for row in rows):
        raise ValueError("Invalid output row")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8-sig", newline="\n")
    summary = dict(stats=stats, rows=len(rows), raw_script_lines=len(raw_lines),
                   labels=len(labels), pages=len(all_pages), dual_pages=len(dual_pages),
                   time_value=time_value, text_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                   source_sha256=hashlib.sha256(dat.read_bytes()).hexdigest())
    for name, data in [("source_map.json", source), ("excluded_text.json", excluded),
                       ("label_audit.json", labels), ("pages.json", all_pages),
                       ("capacity_candidates.json", max_rows),
                       ("layout_map.json", dict(pages=dual_pages)), ("summary.json", summary)]:
        (work / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dat", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--time-value", required=True,
                        help="User-authorized numeric value or placeholder for the two dialogue results")
    args = parser.parse_args()
    extract(args.dat, args.out, args.work, args.time_value)
