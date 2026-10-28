# Takuyo gss · PSP 变体 3（星色のおくりもの）

> 总表见 `../engines.md`；
> PSP 第 1 作 étude prologue 见 `takuyo-gss-psp.md`；第 2 作 Little Aid 见 `takuyo-gss-psp-littleaid.md`。

## 作品 3：星色のおくりもの（PSP `ULJS00164`，2008-10-08，Takuyo）

- **源**：`<游戏 dump 目录>/[PSP-JP]星色のおくりもの.iso`（ISO9660，731,938,816 B）。未加密，`7z x` 取 `USRDIR/SCRDATA.{BIN,ARC}` ＋ `SYSDIR/BOOT.BIN`（**明文 ELF**；`EBOOT.BIN` 才是 `~PSP`）。
- **容器**：`LSDARC V.100`，**269 条，全部 `isPacked=0`**（与 étude 同组合：**PSP ＋ `SCR 2.00` ＋ 未打包**）；offset 链式累加 0 失步。
  索引里 **26 个名字有第二份字节完全相同的副本**（都在索引尾部，如 `PRG_NAME`／`PRG_*_LOVE`）⇒ 按名去重即安全。
- **脚本**：`SCR 2.00`，**269/269 精确铺满、零失步**（`himehibi_disasm` 直用）。正文脚本 **187 个** / 111,643 条指令。
- **上屏 opcode**：`0x5a` 正文（20,135）／`0xfc` 带 `%s`（625，替换源＝串后 slot）／**`0xf0` 场景标题卡（187，字面串，逐脚本恰好 1 条）**／`0x5c` 选项（99 op／220 串，`"文本,LABEL"` 取最后一个 ASCII `,` 之前）。
  ★**与 étude 不同：标题卡走 `0xf0`（不是 `0xfd (6,5802)` 槽拼接）**；正文脚本内 `0x107`＝0、`0x5d`＝0。
- **说话人名札＝`0xfd (6,d402)`**（étude＝`0c02`，**逐作变**）；`0x8480` 存 `"　　姓　名　　"` 整串再拷进 `d402`。名札表去重 **20** 项（4 攻略对象＋主角＋8 副角色＋泛用）。
- **主角＝由本 桜衣（可变名）**：`BOOT.BIN` 名字输入默认值表（`0x7d721` 区，紧邻 `name_bg.gim`/`name_selection.gim`/`vram_name_cursor.gim`）＝ `桜衣` `由本`；
  `DEBUG` 的 `DEBUG_TOP` 段直接把默认值播进槽：`0xfd(6,4c03)="桜衣"`（名）／`0xfd(6,5803)="由本"`（姓）／`0xfd(6,8480)`（札）。
  文面 `「稲船くん！　わ、私は%s%s」` 证 **5803＝姓在前**。
- **★ 顺序＝`PRG_ROUTE.SCR` 的 `0x1e` 派发表**（378 条，与 Little Aid 的 `STORYCTRL` 同构）：
  `09_prologue → 09_* → 10_* → 11_* → 12_* → EP_TAKASHI → 11_SIN_05.. → EP_SIN → 11_SEIGO_04.. → EP_SEIGO → 11_SOUYA_.. → EP_SOUYA →`
  **`EP_ALL_EP`（总集篇，由 `PRG_EYE-CATCH` 调用）追加末尾**。`PRG_BG/PRG_EFFECT/PRG_EYE-CATCH/PRG_FEELING` 夹在场景间→跳过；`10_SOUYA_14` 出现两次→去重。
- **★ 零成本完整性交叉验证**：`BOOT.BIN` 内有**「回想」标题表**（`<タイトル>`↔`<脚本名>.SCR` 成对，`0x79a00〜0x7f000`，370 条／185 唯一），
  与本作每个脚本的 `0xf0` 标题卡**逐条一致**，且只缺 `09_PROLOGUE`/`11_BAD_EP`（回想不登记）⇒ 脚本集合完整。**同族他作也可用此法反查漏项。**
- **排除（量化）**：`CERO` 1,497 行（主线整行重复 **93.5%**）、`DEBUG_VOICE_*` 8 个（88〜91% 重复）、
  `DEBUG_STAND` 462 行（**0% 重复但全是制作注记** `ＴＡＫ００＿Ａ＿Ｌ；…／／隆志：制服１：笑イ：（大）`）、`DEBUG`/`DEBUG_HAIKEI`、
  `AUTOEXEC/INIT/PRG_*/SELECT/SELECT2/YURASHI/RELOAD/SEGA`。
  `PRG_BG` 唯一 0x5a＝转场等待符 `………\n………………\n………………………`；`PRG_EYE-CATCH` 唯一 0x5a＝`#w0#＜想い出＞…追加されました！` 解锁通知。
- **★ 星占い（菜单功能）已收，走「槽拼接」**：`PRG_*_FORTUNE` 的整段**不是 `0x5a`** —— `0xfd (6,9406)<串>` 建立 → 连串 `0x107 (6,9406)<串>` 累加 → `0xfc (6,9406)` 打印
  （与 Little Aid 场景标题卡同一机制）⇒ 提取器须带**槽求值状态机**，在 `0xfc` 打印点还原整段。共 **524** 行（`PRG_HOSHITEXT` 382＋相性占い 142，其中 35 段为拼接还原）。
- **★ キャラ資料在 `BOOT.BIN`，不在 SCRDATA**：`0x7a8dc〜0x7ae5c`，CP932 ＋ NUL 分隔 ＋ **真实 `0x0A` 换行**（不是脚本里的 `\n` 两字符！），
  结束标记＝首个资源 id `pro_takashi`。8 角色×（名前＋よみ／年齢／誕生日／血液型／星座／身長／体重／好き／苦手／告白留言 1〜2 块），字段**按角色缺省**（紳 無身長、茉莉 無年齢…）⇒ 按串序整体输出，别按固定字段数解析。共 79 行。
- **仍不收**：`BOOT.BIN` 系统帮助/存档约 90 条（SKILL.md §0 系统/UI）；**无用語辞典**（`SYSDATA.ARC` 仅 2 条 `PGF0` 字体）。
- **源笔误 1 处**：`10_SEIGO_07` id=335 `（…見失って……` 以 `8169`（`（`）开、`8176`（`」`）收 ⇒ 整行定值改为 `）`。
- **工具 / 成品**：`scripts/hoshiiro_extract.py`（复用 `gss_lsdarc.py` ＋ `himehibi_disasm.py`；`TEXT_PATCH` 断言命中 1 次，`--slot` 可覆盖名字槽）。
  `提取结果/星色のおくりもの_全文本.txt`（**21,770 行**）【PASS】；报告 `提取结果/解析报告/星色のおくりもの_解析报告.md`。
