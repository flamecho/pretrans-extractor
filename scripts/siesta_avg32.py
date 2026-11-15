# -*- coding: utf-8 -*-
"""Siesta ～すすき野原の夢物語～ 文本提取（AVG32 / AMEDEO）

源链路：rar(otoame) -> ISO -> DAT/SEEN.TXT (PACL) -> PACK/LZ -> TPC32 字节码
字节码语义来源：avg32 crate 0.1.0（archive.rs / scene.rs / scenario.rs）

L0 版式判据：
  - 0x01 = click_wait + line_feed（每次点击结束一个文本框）
  - 0x03 = click_wait 不含 line_feed（同框内再多点一次）—— 本作全库 0 次
  - 0x04 = text_window（子命令 1/2/3/5 清屏；4 等待后清屏）
  - 0x02 = 段内 CR 软换行（合并，不拆）
  - 0x58 = 选项（sub 1/2 文本项，sub 4 读档选择器）
  - 0xfe/0xff = 文本包（v1714 带 4 字节前缀 int）
  - #NVL_SYSTEM=000（非 NVL）⇒ mes_line_feed 在非 novel 模式清缓冲重绘
    ⇒ 一次点击 = 一个文本框 = 一行 ⇒ 单版
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import collections

BASE = os.path.join(VNTRANS_HOME, "_work_siesta")
SRC = os.path.join(BASE, "iso", "DAT", "SEEN.TXT")
INI = os.path.join(BASE, "iso", "GAMEEXE.INI")
OUT = os.path.join(VNTRANS_HOME, "提取结果/[PC-JP]Siesta ～すすき野原の夢物語～.txt")
REPORT = os.path.join(VNTRANS_HOME, "解析报告/[PC-JP]Siesta ～すすき野原の夢物語～_解析报告.md")

VER = 1714  # AVG3217D.EXE = 348,160 B >= 330,000 ⇒ 1714

# ---------- PACL ----------
def parse_pacl(data):
    if data[:4] != b"PACL":
        raise SystemExit("not PACL")
    count = struct.unpack_from("<I", data, 0x10)[0]
    out = []
    for i in range(count):
        at = 0x20 + i * 0x20
        name = data[at:at + 0x10].split(b"\x00")[0].decode("cp932")
        off, psz, usz = struct.unpack_from("<III", data, at + 0x10)
        out.append((name, off, psz, usz))
    return out


def unpack_lz(inp, outlen):
    ip = 0
    out = bytearray()
    while len(out) < outlen:
        flags = inp[ip]
        ip += 1
        for bit in range(8):
            if len(out) == outlen:
                break
            if flags & (0x80 >> bit):
                out.append(inp[ip])
                ip += 1
                continue
            token = inp[ip] | (inp[ip + 1] << 8)
            ip += 2
            cnt = (token & 0x0F) + 2
            dist = (token >> 4) + 1
            for _ in range(cnt):
                if len(out) == outlen:
                    break
                out.append(out[len(out) - dist])
    return bytes(out)


def entry_bytes(data, off, psz, usz):
    packed = data[off:off + psz]
    if psz == usz:
        return packed
    if packed[:4] != b"PACK":
        raise SystemExit("PACK magic missing")
    dec_un, dec_pk = struct.unpack_from("<II", packed, 8)
    if dec_un != usz:
        raise SystemExit("PACK size mismatch")
    return unpack_lz(packed[0x10:], dec_un)


# ---------- TPC32 header ----------
def header_code_offset(b):
    if b[:5] != b"TPC32":
        raise ValueError("not TPC32")
    label_count = struct.unpack_from("<i", b, 0x18)[0]
    pad = label_count * 4 + 0x50
    pad2 = 4 if struct.unpack_from("<i", b, pad)[0] == 5 else 0
    menu_count = struct.unpack_from("<i", b, pad - 0x24)[0]
    c = pad
    n_strings = 0
    for _ in range(menu_count):
        sc = b[c + 1]
        c += 2
        n_strings += 1
        for _ in range(sc):
            rp = b[c + 1]
            c += 2
            n_strings += 1
            for _ in range(rp):
                conds = b[c]
                c += 1 + conds * 3
    for _ in range(n_strings):
        length = b[c]
        c += length + 1
    return c + pad2 + 0x13


# ---------- 字节码 ----------
def read_value(buf, pos):
    if pos >= len(buf):
        return 0, False, pos + 1
    first = buf[pos]
    ln = (first >> 4) & 0x07
    if ln == 0 or pos + ln > len(buf):
        return 0, False, pos + 1
    value = 0
    for k in range(ln - 1, 0, -1):
        value = (value << 8) | buf[pos + k]
    value = (value << 4) | (first & 0x0F)
    return value, bool(first & 0x80), pos + ln


def read_text(buf, pos):
    end = buf.find(b"\x00", pos)
    if end < 0:
        end = len(buf)
    return buf[pos:end], end + 1


class Scene:
    def __init__(self, name, code, names):
        self.name = name
        self.b = code
        self.pos = 0
        self.names = names
        self.boxes = []
        self.cur = None
        self.unknown = []
        self.strvars = {}

    # --- 文本 ---
    def dec(self, raw):
        return raw.decode("cp932", errors="replace")

    def subst_names(self, s):
        out = []
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == "＊" and i + 1 < len(s):
                nxt = s[i + 1]
                if "Ａ" <= nxt <= "Ｚ":
                    out.append(self.names.get(ord(nxt) - ord("Ａ"), ""))
                    i += 2
                    continue
                if "０" <= nxt <= "９" and i + 2 < len(s) and "０" <= s[i + 2] <= "９":
                    i += 3          # 外字槽：本作 0 次
                    continue
            out.append(ch)
            i += 1
        return "".join(out)

    def push(self, s):
        if self.cur is None:
            self.cur = ""
        self.cur += s

    def close(self):
        if self.cur is not None:
            t = self.cur.strip("\u0000")
            if t != "":
                self.boxes.append(t)
        self.cur = None

    # --- 操作数 ---
    def byte(self):
        v = self.b[self.pos] if self.pos < len(self.b) else 0
        self.pos += 1
        return v

    def peek(self):
        return self.b[self.pos] if self.pos < len(self.b) else 0

    def val(self):
        v, _isv, self.pos = read_value(self.b, self.pos)
        return v

    def int32(self):
        v = struct.unpack_from("<i", self.b, self.pos)[0] if self.pos + 4 <= len(self.b) else 0
        self.pos += 4
        return v

    def text(self):
        if self.peek() == 0x40:          # '@n' 字符串变量引用
            self.pos += 1
            return ("var", self.val())
        raw, self.pos = read_text(self.b, self.pos)
        return raw

    def text_str(self):
        t = self.text()
        if isinstance(t, tuple):
            return self.strvars.get(t[1], "")
        return self.subst_names(self.dec(t))

    def rect(self):
        for _ in range(4):
            self.val()

    def colour(self):
        for _ in range(3):
            self.val()

    def conditions(self):
        depth = 0
        while self.pos < len(self.b):
            c = self.byte()
            if c == 0x28:
                depth += 1
            elif c == 0x29:
                depth -= 1
                if depth <= 0:
                    break
            elif c in (0x26, 0x27):
                pass
            elif c == 0x58:
                kind = self.byte()
                if kind in (0x20, 0x22):
                    self.val()
            elif 0x36 <= c <= 0x55:
                self.val()
                self.val()
            elif self.pos >= len(self.b):
                break

    def formatted_text(self):
        out = []
        while self.pos < len(self.b):
            c = self.byte()
            if c == 0:
                break
            if c in (0xFE, 0xFF):
                out.append(self.text_str())
            elif c == 0xFD:
                idx = self.val()
                out.append(self.strvars.get(idx, ""))
            elif c == 0x28:
                self.pos -= 1
                self.conditions()
            elif c == 0x10:
                sub = self.byte()
                if sub == 0x01:
                    out.append(str(self.val()))
                elif sub == 0x02:
                    v = self.val()
                    w = self.val()
                    out.append(str(v).zfill(max(0, min(32, w))))
                elif sub == 0x03:
                    idx = self.val()
                    out.append(self.strvars.get(idx, ""))
                elif sub == 0x11:
                    self.val()
        return "".join(out)

    # --- 主循环 ---
    def run(self):
        while self.pos < len(self.b):
            cmd = self.byte()
            try:
                self.op(cmd)
            except Exception as e:
                self.unknown.append((self.pos, cmd, repr(e)))
                break
        self.close()

    def op(self, cmd):
        if cmd == 0x01:                     # click_wait + line_feed
            self.close()
        elif cmd == 0x02:                   # 段内 CR（软换行，合并）
            self.byte()
        elif cmd == 0x03:                   # click_wait 无 line_feed
            pass
        elif cmd == 0x04:                   # text_window
            sub = self.byte()
            if sub in (1, 2, 3, 5):
                self.close()
            elif sub == 4:
                self.close()
        elif cmd == 0x05:
            self.val()
        elif cmd in (0x06, 0x1A, 0x65) or 0x22 <= cmd <= 0x29:
            pass
        elif cmd == 0x08:
            sub = self.byte()
            if sub in (0x10, 0x11):
                self.val()
        elif cmd == 0x0B:
            self.graphics_load()
        elif cmd == 0x0C:
            self.animation()
        elif cmd == 0x0E:
            self.sound()
        elif cmd == 0x10:                   # 数值/字符串插入正文
            sub = self.byte()
            if sub == 0x01:
                self.push(str(self.val()))
            elif sub == 0x02:
                v = self.val()
                w = self.val()
                self.push(str(v).zfill(max(0, min(32, w))))
            elif sub == 0x03:
                idx = self.val()
                self.push(self.strvars.get(idx, ""))
        elif cmd == 0x13:
            self.fade()
        elif cmd == 0x15:
            self.conditions()
            self.int32()
        elif cmd == 0x16:
            self.byte()
            self.val()
        elif cmd == 0x17:
            if self.byte() == 1:
                self.val()
        elif cmd == 0x18:
            if self.byte() == 1:
                self.val()
        elif cmd == 0x19:
            self.wait()
        elif cmd == 0x1B:
            self.int32()
        elif cmd == 0x1C:
            self.int32()
        elif cmd in (0x1D, 0x1E):
            n = self.byte()
            self.val()
            for _ in range(n):
                self.int32()
        elif cmd == 0x20:
            self.byte()
        elif 0x2C <= cmd <= 0x31:
            self.legacy(cmd)
        elif cmd in (0x37, 0x39) or 0x3B <= cmd <= 0x43 or 0x49 <= cmd <= 0x51:
            self.val()
            self.val()
        elif cmd == 0x56:
            self.val()
        elif cmd == 0x57:
            self.val()
            self.val()
            self.val()
        elif cmd == 0x58:
            self.choice()
        elif cmd == 0x59:
            self.strings()
        elif cmd == 0x5B:
            self.byte()
            self.val()
            while self.peek() != 0:
                self.val()
            self.pos += 1
        elif cmd in (0x5C, 0x5D):
            self.byte()
            self.val()
            self.val()
            self.val()
        elif cmd == 0x5E:
            self.byte()
            self.val()
        elif cmd == 0x5F:
            self.multi_add()
        elif cmd == 0x60:
            self.system_command()
        elif cmd == 0x61:
            self.name_control()
        elif cmd == 0x63:
            sub = self.byte()
            if sub == 0x01:
                self.rect()
                self.val()
            elif sub == 0x02:
                self.val()
                self.val()
                self.val()
            elif sub == 0x20:
                self.byte()
                self.val()
        elif cmd in (0x64, 0x67, 0x68, 0x69, 0x6A):
            self.graphics(cmd)
        elif cmd == 0x66:
            self.byte()
            self.val()
            self.val()
            self.val()
            self.colour()
            self.push(self.formatted_text())
        elif cmd == 0x6C:
            sub = self.byte()
            if sub == 0x02:
                self.text()
                self.text()
            elif sub in (0x04, 0x05):
                self.val()
                self.val()
            elif sub in (0x10, 0x11):
                self.val()
            elif sub == 0x15:
                self.val()
                self.val()
                self.val()
            elif sub == 0x20:
                self.val()
                self.val()
        elif cmd == 0x6D:
            sub = self.byte()
            if sub in (0x01, 0x02):
                self.val()
                self.val()
                self.val()
        elif cmd == 0x6E:
            sub = self.byte()
            if sub in (0x01, 0x02, 0x03, 0x04):
                self.val()
            elif sub == 0x05:
                self.val()
                self.val()
                self.val()
        elif cmd == 0x6F:
            for _ in range(4):
                self.val()
        elif cmd == 0x70:
            sub = self.byte()
            if sub == 0x01:
                for _ in range(4):
                    self.val()
            elif sub == 0x02:
                self.val()
                self.colour()
            elif sub in (0x03, 0x04, 0x05, 0x06, 0x10, 0x11):
                self.val()
        elif cmd == 0x72:
            sub = self.byte()
            if 0x01 <= sub <= 0x05 or 0x11 <= sub <= 0x15:
                self.val()
                self.val()
        elif cmd == 0x73:
            sub = self.byte()
            if sub in (0x01, 0x02, 0x05, 0x06, 0x31):
                self.val()
                self.val()
            elif 0x10 <= sub <= 0x2B or 0x2C <= sub <= 0x34:
                self.val()
        elif cmd == 0x74:
            sub = self.byte()
            if sub in (0x01, 0x02):
                self.val()
            elif sub in (0x03, 0x04):
                self.val()
                self.val()
        elif cmd == 0x75:
            self.byte()
            self.val()
        elif cmd == 0x76:
            sub = self.byte()
            if sub in (0x01, 0x02):
                self.val()
        elif cmd == 0x7F:
            self.val()
        elif cmd in (0xFE, 0xFF):
            self.text_packet()
        elif cmd == 0x00:
            pass
        else:
            self.unknown.append((self.pos - 1, cmd, "unknown"))

    # --- 子处理 ---
    def text_packet(self):
        while True:
            if VER >= 1714:
                self.int32()          # 文本块 id
            self.push(self.text_str())
            nxt = self.peek()
            if nxt in (0xFE, 0xFF):
                self.pos += 1
                continue
            break

    def fade(self):
        sub = self.byte()
        if sub == 0x01:
            self.val()
        elif sub == 0x02:
            self.val()
            self.val()
        elif sub in (0x03, 0x04):
            self.colour()
            if sub == 0x04:
                self.val()
        elif sub == 0x10:
            self.val()
        elif sub == 0x11:
            self.colour()

    def wait(self):
        sub = self.byte()
        if sub in (0x01, 0x02):
            self.val()
            if sub == 0x02:
                self.val()
        elif sub in (0x04, 0x05):
            self.val()
            if sub == 0x05:
                self.val()
        elif sub == 0x06:
            self.val()

    def legacy(self, cmd):
        sub = self.byte()
        key = (cmd, sub)
        if key in ((0x2C, 1), (0x2D, 1), (0x2D, 2), (0x31, 1), (0x2E, 1)):
            self.val()
        elif key in ((0x2D, 3), (0x2D, 4), (0x2E, 2)):
            self.val()
            self.val()
        elif key == (0x2F, 1):
            self.val()
            self.val()
            self.val()

    def graphics_load(self):
        sub = self.byte()
        if sub in (0x01, 0x03, 0x05):
            self.text()
            self.val()
        elif sub in (0x02, 0x04, 0x06):
            self.text()
            for _ in range(15):
                self.val()
        elif sub in (0x09, 0x10, 0x54):
            self.text()
            self.val()
        elif sub == 0x11:
            self.text()
        elif sub in (0x22, 0x24):
            count = self.byte()
            if sub == 0x22:
                self.text()
            else:
                self.val()
            self.val()
            for _ in range(count):
                method = self.byte()
                self.text()
                if method == 0x02:
                    self.val()
                elif method in (0x03, 0x04):
                    self.rect()
                    self.val()
                    self.val()
                    if method == 0x04:
                        self.val()
        elif sub in (0x31, 0x32, 0x33, 0x52):
            self.val()

    def animation(self):
        sub = self.byte()
        if sub == 0x10:
            self.text()
            self.val()
        elif sub in (0x16, 0x18):
            self.text()
            if sub != 0x18:
                self.val()
            self.val()
            self.val()
        elif sub in (0x12, 0x30):
            self.text()
            while self.peek() != 0:
                self.val()
            self.pos += 1
        elif sub in (0x20, 0x24):
            self.text()
            while self.peek() != 0:
                self.val()
            self.pos += 1

    def sound(self):
        sub = self.byte()
        if sub in (0x01, 0x02, 0x03):
            self.text()
        elif sub in (0x05, 0x06, 0x07):
            self.text()
            self.val()
        elif sub == 0x10:
            self.val()
        elif sub in (0x20, 0x21, 0x22):
            self.val()
            if sub == 0x22:
                self.val()
        elif 0x30 <= sub <= 0x35:
            self.text()
            if sub in (0x31, 0x33, 0x35):
                self.val()
        elif sub in (0x37, 0x39, 0x40, 0x44):
            self.val()
        elif 0x50 <= sub <= 0x55:
            self.text()
            if sub >= 0x54:
                self.text()
            self.rect()

    def choice(self):
        sub = self.byte()
        if sub in (0x01, 0x02):
            self.val()
            self.close()
            if self.byte() == 0x22:
                if self.peek() == 0:
                    self.pos += 1
                while True:
                    t = self.formatted_text()
                    self.boxes.append(("OPT", t))
                    if self.peek() == 0x23 or self.pos >= len(self.b):
                        break
                self.pos += 1
        elif sub == 0x04:
            self.val()

    def strings(self):
        sub = self.byte()
        idx = self.val()
        if sub == 0x01:
            self.strvars[idx] = self.text_str()
        elif sub == 0x02:
            self.val()
        elif sub == 0x03:
            self.val()
            self.val()
        elif sub == 0x04:
            src = self.val()
            self.strvars[idx] = self.strvars.get(idx, "") + self.strvars.get(src, "")
        elif sub == 0x05:
            src = self.val()
            self.strvars[idx] = self.strvars.get(src, "")
        elif sub in (0x06,):
            self.val()
            self.val()
        elif sub == 0x08:
            self.val()
        elif sub == 0x07:
            pass

    def multi_add(self):
        sub = self.byte()
        if sub == 0x01:
            self.val()
            while True:
                code = self.byte()
                if code in (0x01, 0x11):
                    self.val()
                elif code in (0x02, 0x12):
                    self.val()
                    self.val()
                if code == 0 or self.peek() == 0:
                    if code != 0:
                        self.pos += 1
                    break
        elif sub == 0x10:
            self.val()
            self.val()
            self.val()
        elif sub == 0x20:
            count = self.byte()
            self.val()
            self.val()
            for _ in range(count):
                self.val()

    def system_command(self):
        sub = self.byte()
        if sub in (0x02, 0x03):
            self.val()
        elif sub == 0x04:
            self.formatted_text()          # 窗口标题（不上屏正文）
        elif sub in (0x30, 0x35, 0x31, 0x36, 0x37):
            self.val()
            self.val()

    def name_control(self):
        sub = self.byte()
        if sub == 0x01:
            self.rect()
            self.colour()
            self.colour()
        elif sub in (0x02, 0x03):
            self.val()
        elif sub in (0x10, 0x12):
            name = self.val()
            idx = self.val()
            self.strvars[idx] = self.names.get(name, "")
        elif sub == 0x11:
            name = self.val()
            idx = self.val()
            self.names[name] = self.strvars.get(idx, "")
        elif sub == 0x20:
            self.val()
        elif sub == 0x21:
            self.val()
            self.text()
            for _ in range(9):
                self.val()
        elif sub == 0x24:
            count = self.byte()
            for _ in range(count):
                self.val()
                self.formatted_text()      # 名字输入框标题（UI，不收）

    def graphics(self, cmd):
        if cmd == 0x64:
            sub = self.byte()
            if sub in (0x02, 0x04, 0x10):
                self.rect()
                self.val()
                self.colour()
            elif sub == 0x15:
                self.rect()
                self.val()
                self.colour()
                self.val()
            elif sub in (0x07, 0x11, 0x12, 0x20):
                self.rect()
                self.val()
            elif sub == 0x30:
                self.rect()
                self.val()
                self.rect()
                self.val()
            elif sub == 0x32:
                for _ in range(16):
                    self.val()
        elif cmd == 0x67:
            sub = self.byte()
            if sub == 0x00:
                self.rect()
                self.val()
                self.val()
            elif sub in (0x01, 0x02, 0x08):
                self.rect()
                self.val()
                self.val()
                self.val()
                self.val()
                if sub == 0x08 or (sub == 0x01 and VER >= 1704) or (sub == 0x02 and VER >= 1613):
                    self.val()
            elif sub == 0x03:
                self.rect()
                self.val()
                self.val()
                self.val()
                self.val()
                self.colour()
            elif sub == 0x05:
                self.rect()
                self.val()
                self.val()
                self.val()
                self.val()
            elif sub in (0x11, 0x12):
                self.val()
                self.val()
                if (sub == 0x11 and VER >= 1704) or (sub == 0x12 and VER >= 1613):
                    self.val()
            elif 0x20 <= sub <= 0x22:
                self.val()
                for _ in range(14):
                    self.val()
                if sub == 0x21:
                    self.val()
                elif sub == 0x22:
                    self.colour()
        elif cmd == 0x68:
            sub = self.byte()
            if sub == 0x01:
                self.val()
                self.colour()
            elif sub == 0x10:
                self.colour()
                self.val()
                self.val()
        elif cmd == 0x69:
            self.byte()
            self.byte()
            self.rect()
            self.val()
            self.val()
        elif cmd == 0x6A:
            mode = self.byte()
            if mode in (0x10, 0x20, 0x30):
                self.byte()
                count = self.byte()
                self.val()
                self.val()
                self.val()
                if mode == 0x30:
                    self.val()
                for _ in range(count):
                    self.text()
                    self.val()
                self.pos += 1
            elif mode in (0x03, 0x04):
                count = self.byte()
                self.val()
                self.val()
                for _ in range(count):
                    self.text()
                    self.val()
                self.pos += 1


# ---------- 名札 ----------
PLATE = re.compile(r"^【([^】]{0,20})】")


def strip_plates(s):
    """名札包装剥成「名」；空名札（【】）直接去掉。"""
    if "【】" in s:
        s = s.replace("【】", "")
    m = PLATE.match(s)
    if not m:
        return s
    name = m.group(1)
    rest = s[m.end():]
    return name + rest


def load_names():
    names = {}
    with open(INI, "rb") as f:
        txt = f.read().decode("cp932", errors="replace")
    for line in txt.splitlines():
        m = re.match(r"#NAME\.([A-Z])\s*=\s*\"(.*)\"", line)
        if m:
            names[ord(m.group(1)) - ord("A")] = m.group(2)
    return names


def main():
    data = open(SRC, "rb").read()
    entries = parse_pacl(data)
    names = load_names()

    lines = []
    stats = collections.Counter()
    unk = []
    pages = 0
    for name, off, psz, usz in entries:
        raw = entry_bytes(data, off, psz, usz)
        co = header_code_offset(raw)
        sc = Scene(name, raw[co:], dict(names))
        sc.run()
        if sc.unknown:
            unk.append((name, sc.unknown[:3]))
        for bx in sc.boxes:
            if isinstance(bx, tuple):
                lines.append(("OPT", bx[1], name))
                stats["opt"] += 1
            else:
                lines.append(("TXT", strip_plates(bx), name))
                stats["txt"] += 1
        stats["scenes"] += 1

    print("scenes", stats["scenes"], "txt", stats["txt"], "opt", stats["opt"])
    print("unknown:", unk)

    # 调试/系统串（按类型判据：引擎警告 PATTERN + 调试菜单）
    def is_debug(kind, s, name):
        if name == "SEEN777.TXT":                       # 日付えらー（开发调试）
            return True
        if s.startswith("※警告※"):                     # 引擎「PDT 未指定」警告
            return True
        if s.startswith("S[") and "〕" in s:             # 调试变量回显
            return True
        return False

    kept = [(k, s, n) for k, s, n in lines if not is_debug(k, s, n)]
    dropped = [(k, s, n) for k, s, n in lines if is_debug(k, s, n)]
    print("dropped debug/system:", len(dropped))
    for d in dropped:
        print("   ", d[2], d[1][:70])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        for k, s, n in kept:
            f.write(s + "\n")
    print("wrote", OUT, "lines", len(kept))
    return kept


if __name__ == "__main__":
    main()
