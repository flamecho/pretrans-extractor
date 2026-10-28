# Switch「BKTR」PatchRomFS（更新档）读取

> **触发场景**：NS 作品带官方更新档（NSP 里的 patch NCA），`hactool -t nca --romfsdir` 报
> **`Failed to read RomFS directory cache!`**，或报 `cannot save BKTR section without base romfs`。
> 这不是密钥错、不是包坏 —— 是 NCA 段 `crypt_type = 4`（**Patch RomFS**）。

## 0. 一句话结论

**BKTR 段不是完整 romfs，而是「相对 base romfs 的字节级差分 + 重定位表」，虚拟地址空间＝base romfs 整段（含 IVFC hash 层）。**
所以「导 base romfs 再合并」**注定失败**：hash 层、目录表、文件表跟 romfs 本体混在同一个虚拟空间里，
连 romfs 头本身都可能被切成「patch 前 0x40 + base 后 0x10」两段。**必须按重定位表逐段拼。**

## 1. 段内物理布局（2026-10-26 实测，两样本验证）

```
0x000..                    IVFC level 数据
rel_header.offset          重定位块（段尾往前 0x8000）
   {u32 _, u32 num_buckets, u64 total_size, u64 virt_offsets[]} ＋ bucket @ +0x4000
   entry 每条 0x14：{u64 virt_offset, u64 phys_offset, u32 is_patch}
     is_patch = 1 → 读本段物理数据
     is_patch = 0 → 读 base romfs 的**同偏移**
sub_header.offset          子段块（紧跟其后 0x8000）
   entry {u64 offset, u32 _, u32 ctr_val}
   物理读 CTR = ctr_hi(8B) | ctr_val(4B BE) | ((NCA 绝对偏移 >> 4) & 0xFFFFFFFF)
```

FS 头在 `0x600 + n*0x200`：

| 偏移 | 内容 |
|---|---|
| `+0x08` | IVFC（`level_count` @ `+0x14` ＝ 7；level 表 @ `+0x18`，每项 0x18） |
| `+0x100` | rel header `{u64 offset, u64 size, u32 "BKTR", u32 ver, u32 num_entries, u32}` |
| `+0x120` | sub header（同结构） |

**结构自证**：`rel.offset + rel.size == sub.offset` 且 `sub.offset + sub.size == 段大小`。

## 2. 工具

```bash
# 结构自检（不需要 base）
python scripts/bktr_romfs.py <update.nsp|update.nca> --info

# 列出 patch romfs 的全部文件（base 支持 nsp / nca / xci / 裸 romfs）
python scripts/bktr_romfs.py <update> --base <base.nsp|base.nca|base.xci|裸base.romfs> --list

# ★只列本次更新真正改到的文件（数据落在 patch 区间）—— 决定「要不要合并」就看这个
python scripts/bktr_romfs.py <update> --base <base> --changed

# 取文件
python scripts/bktr_romfs.py <update> --base <base> --get <路径子串> <输出目录>
```

`.nsz/.xcz` 先解：`nsz.exe -D --keys _sw/merged.keys -o <dir> <file>`（4.9 GB 的 xcz 约 6 分钟）。

**为什么不用 hactool**：1.4.0 其实认 BKTR（会打印 `Patch RomFS`），但两条路都不实用 ——
`--basenca` 需要 base 自己的 titlekey（报 `Unable to match rights id to titlekey`，1.4.0 没有可用的 `title.keys` 入口）；
`--baseromfs` 要的是 base romfs **段的原始镜像（含 IVFC hash 层）**，不是解包出来的 romfs 目录。这正是那个报错的主因之一。

## 3. 取键（与 BKTR 无关，但同批反复踩）

1. **`hactool --titlekey` 要的是 tik 里加密态那 16 字节（`tik[0x180:0x190]`）**，
   给成「解密后的 titlekey」就整段乱码 —— 报的正是 `Failed to read RomFS directory cache`。
2. `titlekey = AES_ECB_dec(tik[0x180:0x190], titlekek[hdr[0x220] − 1])`。
   索引是 **`hdr[0x220] − 1`**，不是 0x206／0x21C。例：`スチームプリズン` `hdr[0x220]=0x0B` ⇒ `titlekek_0a`。
3. **`prod_fixed.keys` 只到 `titlekek_0f`**；**keygen ≥ 16 必须换 `_sw/merged.keys`**（到 `titlekek_10`）。
4. **base NCA 的 key_area 下标 ≠ 段号**（实例：section1 实际用 `key_area[2]`）。
   别硬编 `i == i`，用「romfs 头 `header_size == 0x50`」这类**内容自证**来选 key。

## 4. 判断「更新值不值得合并」的实测参考

| 作品 | 更新档 | patch 区间 | 改动文件 | 改动内容 | 结论 |
|---|---|---:|---:|---|---|
| スチームプリズン 1.0.1 | 16 MB | 8 | **1** | `script_text.mrg` 12,413,688 → 12,414,048（+360 B） | 改动极小，合不合差别不大 |
| テミラーナ 1.0.1 | 1.27 GB | 146 | **135** | 含 `uma_text_2.bytes` 等文本表；`ResourceList_EV310_000.txt` 多 3 行 | **必须合并**（否则丢文本） |

⇒ **固定流程**：先 `--changed` 看改动面；改到脚本/文本文件就合并后再提取，只改资源就按本体 v0 交付并在报告写明。

## 5. 证据（两样本实解）

- スチームプリズン：合并后解出 45,702 行剧本，例 `それは悪い` / `恩に着る` / `本当にいいのか？`
- テミラーナ：合并后 `uma_name_2.txt` 解出 `ニルダ` / `ヘリングテール聖騎士` / `カルナップ国王` / `ゾンダリク王妃` / `トビアス`
