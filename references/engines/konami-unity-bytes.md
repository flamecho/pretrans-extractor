# KONAMI 自研 Unity ADV（`.bytes` 自研字节码）—— ときめきメモリアル Girl's Side 1st Love / 2nd Season for Nintendo Switch

> 首作：**ときめきメモリアル Girl's Side 2nd Season for Nintendo Switch**（KONAMI 2024，Unity 2021.3.29f1 + IL2CPP）。
> Title ID `010079201BD88000`；更新 `010079201BD88800`(v1.0.4, BKTR)。
> 第 2 作：**ときめきメモリアル Girl's Side 1st Love for Nintendo Switch**（2024-02-14，`0100D9A01BD86000`；
> 更新 `…86800` v1.0.4）⇒ **同引擎同格式**（`.bytes` 头魔数 `…,1,773,772` 在 5,366 个非空 bundle 全部吻合）；
> 差异仅 3 处，见 §8。
> 本文件自包含：容器 → 解密 → 结构 → 成行 → 排除 → 工具。

## 1. 容器 / 解密链路

```
NSP(PFS0) → Program NCA(4.27GB, Titlekey crypto) → ExeFS + RomFS
  RomFS/Data/StreamingAssets/scenario/<a-z>/<name>.assetbundle  ← 剧本（2,838 个）
  RomFS/Data/StreamingAssets/lang/ja/initialize.assetbundle     ← skinship/はばたきネット/UI 表
```

### ★★ hactool 的两个坑（本作必踩）
1. **`hactool --pfs0dir` 对 >1.7GB 的成员会写全零**（本体 Program NCA 从 `0x65DD1999` 起整段 0）。
   症状 = `Invalid NCA header!`（cnmt）／`section 0/1 is corrupted!`（Program）的**假故障**。
   ⇒ **NCA 一律改用 Python 逐块拷贝**（小文件 cnmt/tik/cert 同样会被写 0，必须一起改）。
2. **`--titlekey` 收的是「加密」titlekey**：直接给 `.tik[0x180:0x190]` 原值；
   hactool 打印 `Titlekey (Encrypted)/(Decrypted) (From CLI)` 并自行用 titlekek 解。
   传明文会**再解一次** ⇒ 全错。

   ```bash
   hactool.exe -t nca prog.nca -k prod.keys --titlekey=deb31b0fa8045e3bc28d56655d26e22f \
       --exefsdir=exefs --romfsdir=romfs
   ```

## 2. `.bytes` 结构（自研字节码）

```
0x00  28B 头 = 7×u32 LE：<0x10><poolOff><poolOff><poolOff><1><773><772>   # 773/772 恒定
0x1C..poolOff  代码区：每条 4B = <u8 A><u8 B><u16 BE 参数>（长度严格 mod 4）
poolOff..EOF   字符串池：条目以原始 0x00 分隔；**每条用随池内起始偏移变化的 XOR 键**
```
- **`05 03 <u16>` ＝ 引用字符串池**（参数＝池内偏移）。
- **消息块 ＝ `0316 … 0317`**：

| 骨架（块内指令） | 语义 | 处置 |
|---|---|---|
| `0316 0503 0400 0503 0317` 且 **块后 `0402` 再跟 `01 04`** | **选项块**（2 选项） | 2 个 0503 全收 |
| `0316 0503 0400 0503 0400 0503 0317` ＋ `0402 0104` | **选项块**（3 选项） | 3 个全收 |
| `0316 0503 0400 0503 0317`（其他后续） | **名札＋正文**（第 1＝说话人名，第 2＝正文） | 只收第 2 个 |
| `0316 0503 0400 031c 0500 0400 0504 0317` | 语音 ID（`B0708000_H00X00`） | 丢 |
| `0316 0500 …` / `0316 0500 0400 0503 …` | 无文本／资源 ID | 丢 |

> **选项块的钥匙＝块后 `0317 0402` 之后的 `01 04`**（三选项块 100% 命中；两选项块亦然）。
> 名札＋正文与两选项块骨架**完全相同**，只能靠 `01 04` 区分（别用「第 1 个是不是人名」判）。

## 3. ★★ 字符串池的 XOR 键 = f(池内起始偏移)

```python
K(off) = 0x3C ^ ((off & 0xC0) | (off & 0x03))     # off = 条目在池内起始偏移
明文 = raw XOR K

# 解码结果中的 0x00 字节 ⇒ 真实字节 ＝ K（编码器为规避「raw=0 撞分隔符」而写入 0x00）
```
- 同一条目内 K **恒定**（100+ 字节台词整条解通）；跨条目变化。
- 验证法：对每条尝试 256 键，取「唯一使结果成为合法日文」的键，与公式比对 —— 本作 **217/218 命中**。
- **0x00 还原必须做**：`（`=EF BC 88、`？`=EF BC 9F、好=E5 A5 BD、何=E4 BD 9C
  等中间/末位 `0xBC`/`0xBD` 会被写成 `0x00`；不还原就出现 `ｈ`(EF BD 88)／`！` 变 `ａ` 之类的假字。

## 4. 成行 / 文本约定
- 文本 = **UTF-8**；`\n`（反斜杠+n）＝框内换行；`@@`＝排版断行；`▼`＝「继续」提示符。
- 「一次点击＝一行」＝ 一个 0316…0317 块 → 一行（选项块则每条选项一行）。
- **名札不加前缀**（独立 `0503` operand）。
- ### ★ 历史遗留字符变体（实证）
  `∋`(U+220B) ≡ `？`、`∈`(U+2208) ≡ `！` —— 同一句并存两种写法：
  `（えっ∋）`/`（えっ？）`、`じゃあな∈`/`じゃあな！`（44 组归一后同文）⇒ 交付归一。

## 5. 运行时变量 `｛…｝`

| 形态 | 含义 | 处置 |
|---|---|---|
| `｛佐伯＊＊｝` 等 | 角色名（`＊＊`＝称呼形式位） | 取**姓氏**（＝名札/`AdvNameChN`） |
| `｛主人公｝`/`｛主人公姓名｝`/`｛主人公苗字｝`/`｛主人公名前｝` | 主角名 | 取游戏默认 **`主人公`**（`string_table.ExtraProfilePlayerName`） |
| `｛日付｝`/`｛待ち合わせ場所｝`/`｛流行服名｝`/`｛流行色名｝`/`｛流行アクセサリ名｝`/`｛学年｝` | 运行期变量 | 输出 `〔日付〕` 等 |
| `｛強調流行アクセサリ名｝` | `強調`＝样式标记 | 剥除 `強調` |
- `AddressBookAddress_N`（string_table）＝全角色全名（佐伯 瑛 等）；
  `lbl_to_char_id`（initialize 的 TextAsset）＝名札←→charId 对照表（21 名）＝**零成本 cast 核对源**。

## 6. 文本来源清单（RomFS）

| 路径 / 资源 | 内容 | 处置 |
|---|---|---|
| `scenario/*/*.assetbundle` : TextAsset `*.bytes` | 主剧本 正文＋选项 | **收**（65,717 行） |
| `lang/ja/initialize.assetbundle` : `skinship_dialogue_01〜26` | スキンシップ台词（`Tables[].Records[].Params[].DlgText[]`） | **收**（3,869 行，并入末尾） |
| 同上 : `habatakinet_column/news/event/schedule` | はばたきネット 读文（`Arg0/Arg1/Commentary/Title`） | **收**（573 行，并入末尾） |
| 同上 : `string_table` / `explanation` | UI 标签／操作说明 | **不收**（系统・UI） |
| 同上 : `endroll` | 片尾字幕 | **不收** |
| `sd/` `nss_character/` `ui/` `bg/` `character/` `fashion/` `still/` `sound/` | 图片／模型／UI／音频 | 不收 |

## 7. 工具
- `scripts/tokimemo_gs2_extract.py`（用法见文件头 docstring）
  `python scripts/tokimemo_gs2_extract.py <romfs> -o OUT.txt [--no-skinship|--no-net|--keep-markers]`
- 依赖：`UnityPy`（venv `default`，1.25.3）；`hactool.exe` + `prod.keys` 在 `_sw/`。

## 8. 逐作差异（GS1 / GS3）

> 拆出至 **`engines/konami-unity-bytes-works.md`**（2026-10-15；本文件保持引擎核心 ＋ GS2）。
