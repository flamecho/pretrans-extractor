# -*- coding: utf-8 -*-
"""
[JP]アニマムンディ 終りなき闇の舞踏 — 全文本提取（修订版 v3）
引擎：自研 Flash 引擎 "anima"（karin）；剧本唯一载体 = sys/scriptdata.swf
       （CWS/zlib，内部为自定义序列化：以 0x00 分隔的 UTF-8 字符串流 + 二进制控制块）

判据（严格遵循 skill 铁律：断框只认代码级判据，标点/引号配对仅作探针）：
- 字符串以 0x00 分隔；UTF-8 可解码 = 文本/标识符；解码失败 = 二进制控制块（忽略）。
- 剧本按 'msg' 关键字分段：每个 'msg' 起一个区块，到下一个 'msg' 结束。
  * 引擎区块（首个 'msg'@4466，内容 Array/fctMsg/flagmanagement）= 非文本，排除。
  * 场景区块（'msg'@5306 … @339340，共 53 块，内容为完整日文句子）＝剧本正文。
  * 资源/系统列表区块（'msg'@345148 … @356164，背景/EV/立绘表情/BGM/SE/小游戏标签）
    ＝资源名，非对白，排除。
- 区块内字符串流顺序即上屏顺序。对话片段（JP 文本）之间**无**框界控制码：
  已交叉验证（dlg_ctx 显示 5307–5336 为连续 JP 串，中间无二进制框界信号）。
  ⇒ 每个对话片段即「一次点击＝一框＝一行」。不做任何合并（合并须代码级判据，此处无）。
- 名字以独立窗口标签 `【…】` 形式出现 ⇒ **保留为单独一行**（用户 2026-11-08 修订：名札不再判断，一律保留；不并入正文行、也不加说话人前缀）。
- 独立省略号串（`……`/`…`，无假名汉字）：作为独立停顿/分隔行保留（已渲染文本）。
- 不收：引擎/资源列表（已按区块排除）、二进制控制块、ASCII 标识符、UI 串。

输出：单行＝一框（一次点击＝一文本框）；UTF-8 with BOM / 纯 LF。
文件名＝压缩包名（不加 _全文本/_双版对照 后缀）。

关于「开场顺序」：序章（msg@5306）是一段由内嵌自定义 VM 字节码（token 5505 起）驱动的分支剧本
（Mephisto 考验）。文本以池形式存储（5307–5504），真实上屏顺序由该字节码决定，不能按存储顺序直接输出。
用户 2026-11-08 进游戏核对：开场第一句是 `……まだできないのか？`（5308），第二句是
`私の求めている、永遠の美の秘薬は……`（5307）——与存储顺序相反。
⇒ 对序章前两条台词按用户实机核对顺序输出（5308 先于 5307）；序章其余线性段落维持存储顺序。

关于「双版对照」：本作对白片段之间无代码级框界信号，每个片段为独立一框；
未闭合的 `「`/`（` 等属正常的「跨框引用续行」（一句引语自然跨多个文本框），
并非「同框被拆」，故不产生双版（若强行合并反而会过度合并不同说话人/旁白，已证伪）。
"""
import os, zlib, re

SRC = r"_work_animamundi/src/[JP]アニマムンディ 終りなき闇の舞踏/program files/karin/anima/sys/scriptdata.swf"
OUT = r"提取结果/[JP]アニマムンディ 終りなき闇の舞踏.txt"

# 场景区块的 msg 索引范围（由 msg_list 内容核验：5306..339340 为剧本，其余为引擎/资源）
NARRATIVE_RANGE = (5306, 339340)
# 需要排除的已知非剧本区块 msg 索引（引擎 + 资源/系统列表）
EXCLUDE_MSG = {4466, 345148, 348484, 351484, 353291, 354385, 356164}

jp = re.compile(r'[\u3040-\u30FF\u4E00-\u9FFF]')

def load(path):
    b = open(path, 'rb').read()
    sig = b[:3]
    raw = zlib.decompress(b[8:]) if sig in (b'CWS', b'ZWS') else b[8:]
    return raw

def decode_token(chunk):
    if not chunk:
        return None
    try:
        return chunk.decode('utf-8')
    except Exception:
        return None

def is_name_window(t):
    return t.startswith('【') and t.endswith('】')

def is_pause(t):
    # 纯省略号（无假名汉字）：停顿/分隔行
    return bool(t) and ('…' in t) and not jp.search(t)

def is_placeholder(t):
    # 明确的开发占位符（非对白）：如 （空き）="(空)"
    return t in ('（空き）', '（空）', '(空き)', '(空)')

def main():
    raw = load(SRC)
    chunks = raw.split(b'\x00')
    toks = [decode_token(c) for c in chunks if c]  # None = 二进制控制块；跳过空分片

    msg_idx = [k for k, t in enumerate(toks) if t == 'msg']
    msg_idx.append(len(toks))  # 哨兵

    lines = []
    frag_total = 0
    name_kept = 0
    pause_lines = 0
    placeholder_dropped = 0
    blocks_used = 0

    for i in range(len(msg_idx) - 1):
        mi = msg_idx[i]
        mj = msg_idx[i + 1]
        if mi in EXCLUDE_MSG:
            continue
        if not (NARRATIVE_RANGE[0] <= mi <= NARRATIVE_RANGE[1]):
            continue
        blocks_used += 1
        block_lines = []
        for t in toks[mi + 1:mj]:
            if t is None:
                continue  # 二进制控制块
            if is_name_window(t):
                block_lines.append(t)   # ★ 名札一律保留（单独成行）
                name_kept += 1
                continue
            if is_placeholder(t):
                placeholder_dropped += 1
                continue  # 开发占位符 ⇒ 剔除
            if is_pause(t):
                block_lines.append(t)
                pause_lines += 1
                continue
            if not jp.search(t):
                continue  # 非日文（标识符/控制串/英文）⇒ 忽略
            block_lines.append(t)
            frag_total += 1
        # 序章（5306）开场顺序：用户实机核对 5308 先于 5307 ⇒ 交换前两条
        if mi == 5306 and len(block_lines) >= 2 and \
           block_lines[0].startswith('私の求めている') and block_lines[1].startswith('……まだできないのか'):
            block_lines[0], block_lines[1] = block_lines[1], block_lines[0]
        lines.extend(block_lines)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\ufeff')
        f.write('\n'.join(lines))
        if lines:
            f.write('\n')

    print(f"[done] blocks_used={blocks_used}  frag_total={frag_total}  lines={len(lines)}")
    print(f"        name_kept={name_kept}  pause_lines={pause_lines}  placeholder_dropped={placeholder_dropped}")
    print(f"        -> {OUT}")

if __name__ == '__main__':
    main()
