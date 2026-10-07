# 第三方工具与依赖（需自行获取，本包不附带）

本 skill **不携带**任何解密密钥、许可证串或第三方二进制。运行前请自行准备下列工具。
（下列地址为撰写时的常见来源，**请自行确认最新可用地址**。）

## 1. 基础

- **Python 3.10+**。按需安装：
  ```
  pip install pycryptodome Pillow capstone
  # Unity 系另需：pip install UnityPy
  # 部分脚本用到：pip install lz4 zstandard
  ```
- **7-Zip**：<https://www.7-zip.org/>（多数 `RAR5 SFX` / `ISO` 解包依赖；脚本用 `SEVENZ` 指定路径）。

## 2. PSV（PS Vita）

- **pkg2zip**：<https://github.com/mmozeiko/pkg2zip>（`pkg2zip -x <pkg> <zRIF>`）。
- **psvdec**（含 `psvpfsparser.exe` + `rif2zrif.py` + `self2elf.py` + `zzzrif.py`）：
  `rreha/psvdec`（GitHub）。放好目录后用 `PSVDEC` 环境变量指向它。
- **zRIF / work.bin**：
  - 从你自己的 NoNpDrm dump 的 `sce_sys/package/work.bin`（假许可，512B）用 `rif2zrif.py` 现场生成 zRIF；
    或使用 psvdec 自带的 `games.json`。
  - ★ 经验铁律：**zRIF 与 dump 自带 `work.bin` 一致 ≠ 可用**。`psvpfsparser` 以
    `header signature is valid` 为准；失败时改 `-k <work.bin[0x50:0x60] 的 hex>`（klicensee 常在 0x50）。
  - `psvpfsparser` 成功标志：`keystone: matched retail hmac`。
  - 注意：`psvpfsparser` 需要联网访问 F00D 服务 `cma.henkaku.xyz`（派生 drv_key）；网络被拦会报
    `Error: <unspecified file>(1): expected value`——**这不是 zRIF 错误**，是网络问题。

## 3. Switch

- **hactool**：`SciresM/hactool`（GitHub）。选项须写 `--keyset=<path>`；某些 build 的 `-k` 不生效。
- **prod.keys / title.keys**：**必须来自你自己的主机**（如 Lockpick_RCM / Lockpick）。本包不提供。
  - 已知坑：`prod.keys` 尾部的 `mariko_master_kek_source_*` / `master_kek_source_*` 可能是 17 字节坏条目
    → hactool 直接报错，需先过滤成合规 keys 文件。
- **titlekey**：`hactool --titlekey=` 收的是 ticket `.tik[0x180:0x190]` 里那段**加密** titlekey；
  真正生效值 = `AES_ECB_dec(titlekek_N, tik[0x180:0x190])`，其中 `N = max(hdr[0x206], hdr[0x220]) - 1`。
- 参考实现：**Kuriimu2** <https://github.com/FanTranslatorsInternational/Kuriimu2>。

## 4. 其他 / 通用

- **innoextract**：<https://github.com/dscharrer/innoextract>（Inno Setup 安装包解包，免安装/无密码）。
- **GARbro**：<https://github.com/morkt/GARbro>（多格式封包可视化查看，逆向时对照）。
- **CriPakTools**：`esperknight/CriPakTools`（CRI CPK 参考实现）。
- **KiriKiri**：`KrKrExtract` / `GARbro` 的 XP3 支持。
- **SiglusEngine 静态 key**：`xmoezzz/siglus_static_key_tool`（Rust；从明文头 + LZSS 文法恢复资源 key）。
- **Ethornell / BGI**：`Jair4x/ethornell-tools`、`KlparetlR/Bgi_asdis`、`lifegpc/msg-tool`（`scripts/bgi`）。
- **反编译（.NET）**：无 .NET SDK 时可从 NuGet 直下 `ilspycmd` nupkg 解包后用 `dotnet ilspycmd.dll`。
  ```
  https://api.nuget.org/v3-flatcontainer/ilspycmd/<ver>/ilspycmd.<ver>.nupkg
  ```

## 5. 外部核对来源

- **vndb**：<https://vndb.org/>（角色权威汉字 + 罗马字 + CV；`vndb.org/v<id>/chars`）。
- 官方站 / 攻略 wiki / まとめブログ（歌名、品牌、术语）。

---

## 合规提示

请**仅对你合法拥有的游戏副本**使用上述工具与方法，提取结果仅供个人学习 / 研究，
并用于制作 LunaTranslator 预翻译文件等翻译前置处理。
不要分发含密钥的中间产物，也不要把提取文本当作自己的作品二次发布。
