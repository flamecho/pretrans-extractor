# -*- coding: utf-8 -*-
"""[NS-JP] オランピアソワレ Catharsis for Nintendo Switch —— STCM2L 文本提取

## 容器链
  dump/0100D8002067A000/romfs/CONTENTS/
    STORY.cpk   → SCRIPT/*.DAT ×126（全部同一构建串 `STCM2L Apr 12 2018 18:22:39`）
    SYSTEM.cpk  → DATABASE/dbDictionary.gbin（用語辞典）、dbEntryScript.gbin（脚本顺序表）

## 记录框架（L0，本作自证）
  `[u32 is_call][u32 opcode][u32 nparams][u32 length]` + nparams×12B 参数
  正文记录（op=0x1723c）多带一段固定尾巴：`[0x131][0x160][id][0x10]` + 紧跟**内联字符串对象**
  （`[0][L/4][1][L][utf8+pad]`），p0 正好指向该串 ⇒ `str_at(p0)` 即可取文。
  尾巴第 2 个 u32 = **有无正文的标记**：`0x160` = 有串，`0x12f` = 无串（语音/清屏），实测 18/161。

## 表（本作定表）
  | 用途 | opcode |
  |---|---|
  | 正文 | `0x1723c`（67,896 条含假名）／变体式 `0x49ba8`(n=8)、`0x4a280`(n=4) |
  | 名字窗 | `0x17a20`（= 正文 op + **0x7E4**） |
  | 选项 | `0x19ad0` n=4：param1=文本、param3=`sureN` |
  | 等待点击 | `0x1f4`（95,123）｜goto `0x6`（21,554）｜`switch`（n=2,p0='switch'，4,333） |
  | 标签/旗标（不收） | `0x3178` `0x1a070` `0xa7d8` `0xa9c0` `0xaf40` `0x27984` `0x28984` `0x27248` |

## 宏
  `#Name[1]` ×13,602 → **オランピア**（定值依据：107 条含宏正文里有 **62 条**替换后与语料中既有字面行
  逐字相同；换 `オリンピア`/`オランピア・エデン` 命中 0）
  `#Ruby[基底,读音]` → 只留基底；`#ijbName[1]` 是**源打字错误**（同一记录的另一套用的是 `#Name[1]`）⇒ 按 #Name 处理
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cr_extract as C

BUILD = 'STCM2L Apr 12 2018 18:22:39'
TAG = 'ol'
SRC = os.path.join(VNTRANS_HOME, '_w_ol/story')
DB = os.path.join(VNTRANS_HOME, '_w_ol/db')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]オランピアソワレ Catharsis.txt')
HERO = 'オランピア'
# 整份剔除：90.DAT = 開発用機能テスト（`地の文１２３４５…` `ルビの表示テスト` `エフェクトの機能テスト` 等 166 行全是测试串）
SKIP = {'90.DAT'}

C.TEXT_OPS[(BUILD, TAG)] = {0x1723C, 0x49BA8, 0x4A280}
C.NAME_DELTA[(BUILD, TAG)] = 0x7E4
C.LABEL_OPS |= {0x3178, 0x1A070, 0xA7D8, 0xA9C0, 0xAF40, 0x27984, 0x28984, 0x27248}
C.HERO = HERO

RUBY = re.compile(r'#Ruby\[([^,\]]*),([^\]]*)\]')


def clean(t):
    t = RUBY.sub(r'\1', t)                 # 注音：只留基底
    t = t.replace('#ijbName[1]', '#Name[1]')   # 源打字错误
    t = t.replace('#Name[1]', HERO)
    t = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', t)
    t = re.sub(r'</?(?:ruby|color|size|speed)[^>]*>', '', t)
    t = t.replace('\\n', '').replace('\r', '')
    t = t.replace('\u3000', ' ')
    return re.sub(r'[ \t]+', ' ', t).strip()


C.clean = clean


def script_order():
    """dbEntryScript.gbin = [u64 id][u64 名称off][u64 ?] ×152 + 字符串区（表长 = 字符串区起点）。"""
    d = open(os.path.join(DB, 'dbEntryScript.gbin'), 'rb').read()
    n = None
    for b in range(8, len(d), 8):
        if d[b:b + 7] == b'/SCRIPT':
            n = b // 24
            break
    assert n and n * 24 == b, '顺序表长度未闭合'
    rows = [struct.unpack_from('<3Q', d, i * 24) for i in range(n)]
    out = []
    for rid, noff, _ in rows:
        e = d.find(b'\x00', b + noff)
        nm = d[b + noff:e].decode('utf-8', 'replace')
        if nm.startswith('/SCRIPT/'):
            out.append((rid, os.path.basename(nm)))
    return out


def dictionary():
    """dbDictionary.gbin：表 40B/行 + 字符串区（表长 = 串区起点 0x1b60）。
    串区按 NUL 切开后是 [見出し語][(読み)][解説] 的连续序列 ⇒ 按此配对并校验「恰好消费完所有串」。"""
    d = open(os.path.join(DB, 'dbDictionary.gbin'), 'rb').read()
    m = re.search(rb'(?:[\xe3-\xe9][\x80-\xbf]{2}){3,}', d)
    assert m, '辞典串区起点未定位'
    B = m.start()
    # 自证：表 = 40B/行 + 8B 尾对齐，故 B % 40 == 8（本体 175 行）
    assert B % 40 == 8, '辞典表长与串区起点不闭合: 0x%x' % B
    off, strs = 0, []
    while off < len(d) - B:
        e = d.find(b'\x00', B + off)
        if e < 0:
            break
        strs.append(d[B + off:e].decode('utf-8', 'replace'))
        off = (e - B) + 1
    KANA = re.compile(r'^[\u3041-\u309f\u30a0-\u30ffー、・（）\s]+$')
    rows, i = [], 0
    while i < len(strs):
        name, i = strs[i], i + 1
        if i < len(strs) and KANA.match(strs[i]) and len(strs[i]) <= 24:
            i += 1                                  # 读音行（不收）
        if i >= len(strs):
            break
        desc, i = strs[i], i + 1
        name = clean(name).strip()
        desc = desc.replace('#n', '')
        desc = RUBY.sub(r'\1', desc)
        desc = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', desc).replace('\u3000', ' ').strip()
        if name and desc:
            rows.append('【%s】%s' % (name, desc))
    return rows


def main():
    order = script_order()
    rows, stat, missing = [], {}, []
    for rid, nm in order:
        if nm in SKIP:
            continue
        p = os.path.join(SRC, nm)
        if not os.path.exists(p):
            missing.append(nm)
            continue
        b, r, nopt = C.parse_file(p, TAG)
        if r is None:
            missing.append(nm + '(起点未定位)')
            continue
        stat[nm] = (len(r), nopt)
        rows.extend(r)
    n_body = len(rows)
    dct = dictionary()
    rows.extend(dct)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(rows) + '\n')
    nopt = sum(v[1] for v in stat.values())
    print('脚本 %d 个（顺序表）／缺 %d：%s' % (len(order), len(missing), missing[:5]))
    print('有正文的脚本 %d 个' % sum(1 for v in stat.values() if v[0]))
    print('其中选项 %d 条' % nopt)
    print('正文 %d 行 + 用語辞典 %d 条 = %d 行 -> %s' % (n_body, len(dct), len(rows), OUT))


if __name__ == '__main__':
    main()
