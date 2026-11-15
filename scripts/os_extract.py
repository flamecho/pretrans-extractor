# -*- coding: utf-8 -*-
"""[NS-JP] オランピアソワレ（本篇）for Nintendo Switch —— STCM2L 文本提取

## 容器链
  dump/0100F9D00C186000/romfs/CONTENTS/
    STORY.cpk   → SCRIPT/*.DAT ×156（全部同一构建串 `STCM2L Feb 10 2014 16:23:58`）
    SYSTEM.cpk  → DATABASE/dbDictionary.gbin（用語辞典）、dbEntryScript.gbin（脚本顺序表）

## 记录框架（L0，本作自证）
  `[u32 is_call][u32 opcode][u32 nparams][u32 length]` + nparams×12B 参数
  正文记录的 p0 直接指向紧随参数的**内联字符串对象** `[0][len/4][1][len][utf8+pad]`
  （本构建没有 [0x131][0x160] 那段尾巴，`p0 == i+16+12n`）。

## 表（本作定表）
  | 用途 | opcode |
  |---|---|
  | 正文 | `0x10940`（60,929 条含假名）／变体式 `0x44c3c`(n=4)、`0x3469c`(n=4) |
  | 名字窗 | `0x1103c`（= 正文 op + **0x6FC**） |
  | 选项 | `0x11c1c` n=4：param0=文本、**param2=`sureN`**（不在末位，故登记 SURE_ANY_OPS） |
  | 等待点击 / goto / 转移 | `0x1f4` ／ `0x6` ／ `switch`(n=2,p0='switch') |
  | 旗标 / 立绘 / 表情 | `0x8354` `0x817c` `0x8824` `0x8894` `0x31e78` 等（不收） |

## 宏
  `#NAME[1]` ×16,801 → **オランピア**；`#Ruby[基底,读音]` → 只留基底；`#Color[0/8]` → 去标记
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cr_extract as C

BUILD = 'STCM2L Feb 10 2014 16:23:58'
TAG = 'os'
SRC = os.path.join(VNTRANS_HOME, '_w_op2/story')
DB = os.path.join(VNTRANS_HOME, '_w_op2/db')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]オランピアソワレ.txt')
HERO = 'オランピア'
SKIP = set()          # 本 dump 无整份テスト台本（已逐个核对：`90.DAT` 不在 156 个脚本内）

C.TEXT_OPS[(BUILD, TAG)] = {0x10940, 0x44C3C, 0x3469C}
C.NAME_DELTA[(BUILD, TAG)] = 0x6FC
C.SURE_ANY_OPS |= {0x11C1C}
C.OPT_ALWAYS_OPS |= {0x11C1C}
C.OPT_SEEN = set()   # 选项按 (文件, 文本, sureN) 去重：同文本 + 同跳转标号 = 同一选择节点   # 选项是独立组件记录（前置记录是 0x3 表情步进或另一条选项）
C.LABEL_OPS |= {0x8354, 0x817C, 0x8824, 0x8894, 0x31E78}
C.HERO = HERO

RUBY = re.compile(r'#Ruby\[([^,\]]*),([^\]]*)\]')
# 同一记录里还会出现**方括号形式的注音**：`凌[しの]いで`（`811.DAT 0x04644c` —— 该记录前半正是
# `#Ruby[糊口,ここう]`，两种写法同义）⇒ 汉字+[假名] 一律只留汉字。
RUBY2 = re.compile(r'([\u4e00-\u9fff])\[([\u3041-\u309f\u30a1-\u30ff\u30fc]{1,10})\]')


def clean(t):
    t = RUBY.sub(r'\1', t)                     # 注音：只留基底
    t = RUBY2.sub(r'\1', t)                    # 方括号注音：`凌[しの]` → `凌`
    t = t.replace('#NAME[1]', HERO)
    t = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', t)  # #Color[n] 等
    t = re.sub(r'</?(?:ruby|color|size|speed)[^>]*>', '', t)
    t = t.replace('\\n', '').replace('\r', '')
    t = t.replace('\u3000', ' ')
    return re.sub(r'[ \t]+', ' ', t).strip()


C.clean = clean


def script_order():
    """dbEntryScript.gbin：表 **24B/行 × 156**（表长恰等于串区起点 0xeb0），行 = `[id][名称off][?]`。
    逐行按偏移取串，并校验每个名字都是 `/SCRIPT/…` 且文件确实存在。"""
    d = open(os.path.join(DB, 'dbEntryScript.gbin'), 'rb').read()
    b = d.find(b'/SCRIPT')
    # 串区起点 0xeb0 = 156×24 + 16B 尾对齐 ⇒ 行数取整除，余数必须是 <24 的尾对齐
    n = b // 24
    assert b > 0 and 0 <= b - n * 24 < 24, '顺序表长度未闭合: 0x%x' % b
    out = []
    for i in range(n):
        rid, noff, _ = struct.unpack_from('<3Q', d, i * 24)
        e = d.find(b'\x00', b + noff)
        nm = d[b + noff:e].decode('utf-8', 'replace')
        assert nm.startswith('/SCRIPT/'), '顺序表第 %d 行不是脚本路径: %r' % (i, nm)
        out.append((rid, os.path.basename(nm)))
    return out


def dictionary():
    """dbDictionary.gbin：表 **32B/行 × 224**（表长恰等于串区起点 0x1c00），
    行 = `[id][名称off][读音off][説明off]`；本作读音字段统一指向同一个空串。
    逐行按偏移取串 ⇒ 不依赖「串序列按 [名][读][说明] 排列」的假设。"""
    d = open(os.path.join(DB, 'dbDictionary.gbin'), 'rb').read()
    m = re.search(rb'(?:[\xe3-\xe9][\x80-\xbf]{2}){3,}', d)
    assert m, '辞典串区起点未定位'
    B = m.start()
    assert B % 32 == 0, '辞典表长与串区起点不闭合: 0x%x' % B
    starts, off = {}, 0
    while off < len(d) - B:
        e = d.find(b'\x00', B + off)
        if e < 0:
            break
        starts[off] = d[B + off:e].decode('utf-8', 'replace')
        off = (e - B) + 1
    rows = []
    for i in range(B // 32):
        _id, noff, _koff, doff = struct.unpack_from('<4Q', d, i * 32)
        name, desc = starts.get(noff, ''), starts.get(doff, '')
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
    print('脚本 %d 个（顺序表）／缺 %d：%s' % (len(order), len(missing), missing[:5]))
    print('有正文的脚本 %d 个' % sum(1 for v in stat.values() if v[0]))
    print('其中选项 %d 条' % sum(v[1] for v in stat.values()))
    print('正文 %d 行 + 用語辞典 %d 条 = %d 行 -> %s' % (n_body, len(dct), len(rows), OUT))


if __name__ == '__main__':
    main()
