# -*- coding: utf-8 -*-
"""[NS-JP]7'scarlet for Nintendo Switch 全文本提取（Otomate SScn 字节码）

## 容器链（全用现成工具）
  .xci（用户提供，头字段非标准 ⇒ hactool -t xci 失败）→ 手工 HFS0：secure@0x17022
  → Program NCA `9f74a269…`（NCA3，keygen 18，AES-CTR key 从 nstool 取）
  → `scripts/nca_stream_romfs.py` 流式读 romfs（hactool --romfsdir 在 2.77 GB romfs 上段错误）

## 剧本载体
  Unity 2022.3.10f1 + Addressables
  `Data/StreamingAssets/aa/Switch/scenario_assets_all.bundle` 内 9 个 TextAsset
  = 7s_prologue / 7s_common1 / 7s_common2 / 7s_hino / 7s_isora / 7s_toa / 7s_sosuke / 7s_yuduki / 7s_hanate

## 载荷解码（来自 `Coder.Decode` @0x18FA2B0 反汇编，非猜测）
  for i in range(len(buff)): buff[i] = (~buff[i] + i) & 0xFF      # MVN + ADD i
  → 变成 GZIP 流 → gunzip → JSON（SScnBinary.ScnData 序列化）

## 断行判据（L0）
  一个 `ComMessage(18)` / `ComMonologue(19)` 命令 = 一个文本框 = 一次点击。
  自证：21,669 条消息内换行数 ∈ {0,1,2}（**最多 3 行**，正是文本框容量），无一条超出；
        因此不存在「一条消息分两屏」的情形，粒度无需再拆。

## 选项
  `ComSelect(27)` 之后紧跟一串 **Arg 包**（实测只有 `ArgBranch(49){IdxLabel,IdxDesc}` 与
  `ArgMatch(65){IdxFlagNo,IdxCompare,Value}` 两种）：`ArgBranch` 就是选项，文本 = TextData[IdxDesc]，
  `ArgMatch` 是「该选项在什么旗标条件下才出现」的条件包 ⇒ 收组时必须一并跳过，否则会把条件后的选项漏掉。
  全篇 166 条 ArgBranch 全部落在这 70 个选项组内（8 条 ArgMatch 夹在中间）⇒ 闭合。

## 宏（Data_Context 表：ID 47/49/48）
  %player → 花蒔イチコ ／ %first → 花蒔 ／ %last → イチコ
"""
import json, base64, struct, os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

ROOT = os.path.join(VNTRANS_HOME, '_w_7sc/json')
OUT = os.path.join(VNTRANS_HOME, "提取结果/[NS-JP]7'scarlet for Nintendo Switch.txt")
HERO_FULL, HERO_SEI, HERO_MEI = '花蒔イチコ', '花蒔', 'イチコ'

# Data_Scene.SceneNo 顺序
ORDER = ['7s_prologue', '7s_common1', '7s_common2', '7s_hino', '7s_isora',
         '7s_toa', '7s_sosuke', '7s_yuduki', '7s_hanate']

TAG = re.compile(r'</?color[^>]*>')
RUBY = re.compile(r'\{([^{}:]+):[^{}]*\}')      # `{紫:シ}` / `{屍:し}{者:しゃ}` ⇒ 留基底、去读音
NONAME = {'NONAME', '', 'SCENE_NO'}


def clean(s):
    s = TAG.sub('', s)
    s = RUBY.sub(r'\1', s)
    s = s.replace('%player', HERO_FULL).replace('%first', HERO_SEI).replace('%last', HERO_MEI)
    s = re.sub(r'\r?\n\u3000?', '', s)      # 框内换行 + 缩进一并合并
    return s.strip()


def load(name):
    j = json.load(open(os.path.join(ROOT, name + '.json'), encoding='utf-8'))
    b = base64.b64decode(j['Buff'])
    vals = list(struct.unpack('<%dI' % (len(b) // 4), b))
    return j['TextData'], vals, j['Positions'] + [len(b)]


def build():
    rows, st = [], {'msg': 0, 'mono': 0, 'opt': 0, 'text': 0, 'branch_total': 0, 'redraw': 0}
    WAITCOM = (21, 41, 42, 43, 44)      # ComMsgOut / ComWait / WaitAnim / WaitLoad / WaitMovie
    for name in ORDER:
        td, vals, pos = load(name)
        prev = None          # (文本, 类型)
        waited = False
        i = 0
        while i < len(pos) - 1:
            p = pos[i] // 4
            c = vals[p]
            if c in (18, 19):                    # ComMessage / ComMonologue
                t = clean(td.get(str(vals[p + 3]), ''))
                # 同一文本紧接再来一次、且中间**没有**收框/等待命令 ⇒ 只是换立绘/表情后的重绘，不是新的一次点击
                if t and prev and t == prev[0] and prev[1] in (18, 19) and not waited:
                    st['redraw'] += 1
                else:
                    rows.append(t)
                st['msg'] += 1
                prev, waited = (t, c), False
            elif c == 33:                        # ComText（直接上屏的特效文）
                rows.append(clean(td.get(str(vals[p + 1]), '')))
                st['text'] += 1
                prev, waited = None, True
            elif c == 27:                        # ComSelect → 其后连排 Arg 包（49 选项 / 65 条件）
                j = i + 1
                while j < len(pos) - 1:
                    q = pos[j] // 4
                    if vals[q] < 45:                 # 命令 ⇒ 组结束
                        break
                    if vals[q] == 49:
                        rows.append(clean(td.get(str(vals[q + 2]), '')))
                        st['opt'] += 1
                    j += 1
                prev, waited = None, True
                i = j
                continue
            else:
                if c == 21:              # ComMsgOut = 收框（清空文本框）⇒ 之后的重绘才是一次新点击
                    waited = True
            i += 1
        for k in range(len(pos) - 1):
            if vals[pos[k] // 4] == 49:
                st['branch_total'] += 1
    return rows, st


def tips_lines():
    """用語辞典：`Data_Tips` 108 条 ⇒ 【見出し】解説，换行合并，并入末尾。"""
    p = os.path.join(ROOT, '_tips.json')
    if not os.path.exists(p):
        return []
    out = []
    for r in json.load(open(p, encoding='utf-8')):
        title = clean(r.get('Title', ''))
        desc = clean((r.get('Desc') or '').replace('\n', ''))
        if title and desc:
            out.append('【%s】%s' % (title, desc))
    return out


def main():
    rows, st = build()
    tips = tips_lines()
    out = [r for r in rows if r] + tips
    st['tips'] = len(tips)
    # 相邻完全重复**不删**：本作粒度是「一条命令＝一次点击」，重复即两次点击（多为「……」这类）；
    # 只统计出来供人工过目。
    dup = sum(1 for i in range(1, len(out)) if out[i] == out[i - 1])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')
    st['rows'] = len(out)
    st['adjacent_dup'] = dup
    st['chars'] = sum(len(x) for x in out)
    print(json.dumps(st, ensure_ascii=False))


if __name__ == '__main__':
    main()
