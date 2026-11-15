#!/usr/bin/env python3
# PWA (rUGP / age 2009) scenario 提取 —— 最终版，已迁移至 scripts/（原 _work_pwa/extract_text.py）
# 用法: python scripts/pwa_extract.py <PWA.rio> <PWA.rio.002> <candidates.json> <out.txt>
#
#   - 208 个 RIO_KEY 标准加密块，解密后为 rUGP 剧本字节码
#   - 文本字段 = 长度前缀 `00 LL` + LL 字节 cp932 文本，以 0x01 框结束，0x03 框内点击/等待分隔
#   - 单版：一个文本框 = 一行（用户决定：不再按 03 切成段行；03/01/0a/0d 控制码去除后按 cp932 解码，\n 软换行合并）。
#   - 名札【名】印在正文框内 ⇒ check_text 用 --inline-name 保留。
# 依赖: scripts/pwa_crypto.py（复制自 agerevex/rUGP/formats/rio/crypto.py，自包含）。
import sys, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pwa_crypto import RIO_KEY, decode_encrypted_block


def read_at(paths, s, n):
    RIO, RIO2, SZ1 = paths
    if s < SZ1:
        with open(RIO, "rb") as f:
            f.seek(s)
            d = f.read(min(n, SZ1 - s))
            if len(d) == n:
                return d
            with open(RIO2, "rb") as f2:
                return d + f2.read(n - len(d))
    else:
        with open(RIO2, "rb") as f:
            f.seek(s - SZ1)
            return f.read(n)


def is_lead(b):
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC)


def valid_trail(lead, t):
    return 0x40 <= t <= 0xFC and t != 0x7F


def is_text_field(field):
    if not field or field[-1] != 0x01:
        return False
    i = 0
    n = len(field)
    while i < n:
        b = field[i]
        # 0x0a/0x0d = 框内软换行（\n），视为合法字段内字节，提取时再合并
        if b in (0x03, 0x01, 0x0A, 0x0D):
            i += 1
            continue
        if is_lead(b) and i + 1 < n and valid_trail(b, field[i + 1]):
            i += 2
            continue
        return False
    return True


def field_to_line(field):
    # 去掉控制码后按 cp932 解码：03=框内点击(并入文本不分段)、01=框结束、
    # 0a/0d=框内软换行(合并)、00=字段外缀(不出现在字段体内)。
    body = bytes(b for b in field if b not in (0x00, 0x01, 0x03, 0x0A, 0x0D))
    try:
        return body.decode("cp932")
    except Exception:
        return ""


def parse_block(pt):
    lines = []
    i = 0
    n = len(pt)
    while i < n:
        if pt[i] == 0x00 and i + 1 < n:
            LL = pt[i + 1]
            if 4 <= LL <= 2000:
                j = i + 2
                end = j + LL
                if end <= n:
                    field = pt[j:end]
                    if is_text_field(field):
                        t = field_to_line(field)
                        if t:
                            lines.append(t)
                        i = end
                        continue
        i += 1
    return lines


def main():
    if len(sys.argv) != 5:
        print("usage: python pwa_extract.py <PWA.rio> <PWA.rio.002> <candidates.json> <out.txt>")
        sys.exit(2)
    RIO, RIO2, CANDS, OUT = sys.argv[1:5]
    SZ1 = os.path.getsize(RIO)
    cands = json.load(open(CANDS))
    paths = (RIO, RIO2, SZ1)
    out_lines = []
    n_boxes = 0
    n_blocks_used = 0
    for off, size in sorted(cands, key=lambda x: x[0]):
        need = 8 + size + 2 * (size // 0x20) + 32
        try:
            data = read_at(paths, off, need)
            pt = decode_encrypted_block(data, RIO_KEY).plaintext
        except Exception:
            continue
        lines = parse_block(pt)
        if not lines:
            continue
        n_blocks_used += 1
        out_lines.extend(lines)
        n_boxes += len(lines)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("\n".join(out_lines) + "\n")
    print("blocks used:", n_blocks_used, "boxes(lines):", n_boxes, "total lines:", len(out_lines))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
