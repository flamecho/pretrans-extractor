# Aromarie 自研「ATL」引擎（`ATL.DLL` ＋ SQLite 剧本库 `scene.db`）

> 代表：**月ノ光太陽ノ影**（PC, 2006-04-21, vndb v2330）＋FD **-Another Moon-**（v2990, 2006-12-22）。两作 `ATL.DLL` 字节相同。
> ★ 同品牌另有 **KiriKiri XP3（区间 1 字节 XOR）** 系（蝶の毒 華の鎖 等，见 `kirikiri-xp3.md`）——**两套不同引擎，勿混**。
> ★ 本引擎最大特点：**文本 100% 落在明文 SQLite 里，无需任何解密/逆向**。

## 1. 文件构成（安装目录）

| 文件 | 作用 |
|---|---|
| `月ノ光太陽ノ影.exe` | 本体；**静态链入 SQLite**，内含全部剧本 SQL |
| `ATL.DLL` | 引擎（仅 68 KB，无文本串） |
| `scene.db` | **剧本库（SQLite 3，明文）** ← 文本全在这里 |
| `system.db` / `user.db` | 演出定义 / 设定（`VariableTable` 存改名值），**无正文** |
| `script.axr` / `bgm.axr` / `cg.axr` / `koe.axr` / `se.axr` | 「资源分层回退」归档（magic `AXRe` ＋ 密文）。exe 串表 `.ax8.ax7.ax6…ax2.axr` ⇒ `.axr` 是最底层扩展；**与文本无关，不必解** |

## 2. 认链路（30 秒判型）

对 exe 跑 `probe.py strings` → 见到下列 SQL 常量即命中：

```
SELECT text FROM talkText WHERE talkId=? AND sceneId=? ORDER BY phrase
SELECT target,name FROM talk WHERE talkId=? and sceneId=?
SELECT eval,text,no FROM choice WHERE sceneId=? AND choiceId=? ORDER BY no
SELECT title, number, prevNo, memo FROM scene WHERE sceneId=?
```
`talkText` / `talk` / `choice` 三表即落在 `scene.db`。

## 3. `scene.db` 表结构

| 表 | 行数（月ノ光） | 字段 / 作用 |
|---|---|---|
| `scene` | 511 | `sceneId, number, title, memo, prevNo` |
| `line` | 16,894 | **指令流**：`sceneId, lineNo, type, param` ← **显示顺序以此为准** |
| `talk` | 14,831 | `sceneId, talkId, target(话者), name(名框模板), flag, waitMul, waitAdd` |
| `talkText` | 14,846 | `sceneId, talkId, phrase, text` ← **正文**（CP932） |
| `choice` | 141 | `sceneId, choiceId, no, text, nextNo, script, eval` ← **选项** |
| `talkVoice` | 14,831 | 语音（filename/len…） |
| `talkCode` | 2,901 | 该 talk 的演出命令（二进制，含角色/图层名，**非正文**） |
| `next` | 484 | 场景跳转 |
| `AtomTable` | 72 | 编辑器字符串池（含**未使用残留串**，如本作 `美咲`——**勿当正文**） |

`line.type` 枚举：`0`＝制作注记（`[廊下,昼][周藤 出]`／`SE蝉の鳴き声`／**选项文案拷贝**）；
`1`＝talk（`param`＝talkId）；`2`＝二进制演出命令；`3`/`4`＝Lua 脚本；`5`＝跳转；`6`＝choice（`param`＝choiceId）。

## 4. 成行规则

1. `scene.sceneId` 升序 → 场景内 `line.lineNo` 升序。
2. `type=1` → `talkText` 取该 `(sceneId,talkId)`，**按 `phrase` 升序直接拼接**（无分隔符）。
3. `type=6` → `choice` 取该 `(sceneId,choiceId)` 按 `no` 升序，**每项一行**。
4. 其余 `type` 全跳。
5. **控制码**：`talkText.text` 只有 `\i`（对话起始样式符，恒在 `「` 后 index==1）⇒ 剥除。
   无 CR/LF、无其他转义。
6. **不加说话人前缀**：`talk.name` 只是名框模板 —— `%NA01%`＝空（旁白）／`%NA03%`＝主角名／
   `NULL`＝用 `talk.target`／`？？？`・`同級生`＝临时称呼。
7. **主角名宏**（可改名，见 §5）：正文内 `%NA00%`→姓、`%NA03%`→名、`%NA01%`→空，**inline 替换**。
8. ★**选项同组互斥去重**：`choice.eval` 是 **Lua 显示条件**（`return gameScene[N];`／`return not gameScene[N];`，空＝恒显示）。
   同组出现「同文案多行」＝互斥备选（实例 scene214：5 行 `誰かに相談？` 各绑不同 flag），只有条件为真者上屏
   ⇒ **组内按首现顺序取一**（月ノ光 141→132）。
9. ★★**同一 `lineNo` 可有多行；引擎按 `ORDER BY type,param` 逐条执行、文本框「后写覆盖」⇒ 生效的是 `param` 最大者**。
   判据（查询常量）：`SELECT type, param FROM line WHERE sceneId=? AND lineNo=? ORDER BY type,param;`。
   旁证：本篇 scene125 `lineNo=0` 有「空 talk(param 0)」＋「正文 talk(param 11)」，能正常显示 ⇒ **非首写优先**。
   ★ **FD 有 328 组同 lineNo 双行，其中 135 组是 (type=1,type=1) ＝旧版 vs 改稿版**：
   改稿版 `talkId` **成批追加**在原 talk 之后（scene0 追加 187–192、scene23 追加 273–278），
   且 `talkVoice` 文件名由 **`X<角色>NNNN`（旧録音）→ `Y<角色>NNNN+1`（新録音）**。
   两版差异：120 组只是「字面 `美希`」↔「宏 `%NA03%`」（替换后同文）；15 组是真改稿
   （`行こう、美希`↔`行こう。`／`美希みたいに`↔`あんたみたいに`——改稿版改用代名詞）。
   ⇒ **保留 param 大者**（不处理会输出 120 组相邻重复行）。本篇只 1 组（空 talk ＋ 正文 talk），本次修正对
   **本篇成品字节级零差**（改完必须 `cmp` 回归上一作）。

## 5. 主角默认名（可改名）取法

exe 内默认表（CP932）：

```
NameEditOnStart
NA03  -> 美希
NA00  -> 藤原
```
＋ `user.db.VariableTable` 里同名键（运行时值，玩家改名后覆盖）。
⇒ 默认全名 **藤原 美希**（vndb c28191「Fujiwara Miki」，Nameable 一致）。
`%NA01%` 无默认值（空），即「旁白＝无名框」。

## 6. 排除与坑

- `line.type=0` 是制作注记，**含选项文案拷贝**（`実は……\r\n別に……`）⇒ 别当选项收（真选项在 `choice`）。
- `AtomTable` 有未使用残留串（本篇 `美咲`）⇒ 别当正文/角色。
- 场景 `title` **不在 `line` 中**（仅「回想/场景选择」菜单用）⇒ 按 §0 不收。
- **可能有未被 `line` 引用的 `talkText` 行**（＝作废台词，本篇 1 行 `(34,22)`）
  与**被引用的空 talk**（本篇 `(125,0)`，被 param 11 覆盖）⇒ 交付前做双向覆盖审计，单列报告。
- ★ **`phrase` 必须先拼接再判形态**：源里大量 `phrase=0` 是**半句**（FD 112 条有续片，
  如 `……ふう。`＋`またこのパターンかい？`＋`…戻ってくれないかな」`）⇒ 漏拼＝丢文本＋**引号不配对假象**。
- ★ **原作笔误（漏收尾 `」`）用整行定值表 `LINE_FIX` 修**（勿正则泛修；FD 2 处 scene22，删表项即恢复原样）；
  判据＝原始 DB 里该 talk 就不存在收尾符、且相邻各行均正常。
- 文件无密码 / 无头部加密，7z 直解即可。

## 7. 工具

- `scripts/moon_atl_extract.py <scene.db> <out.txt>` —— 通用驱动（**本篇/FD 共用**；`LINE_FIX` 为定值表）。
