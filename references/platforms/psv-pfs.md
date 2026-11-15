# PSV PFS 与字形槽

## 解密路径

确认 app 根、PFS 元数据、实际资源签名及授权材料。
展开 ZIP 或存在 head.bin 不证明当前树已经解密；
同样，sce_pfs 目录或高熵也不能单独证明所有成员仍加密。

| 输入 | 操作 |
|---|---|
| PKG | 用支持版本的 pkg2zip 提取，核对 work.bin 使用方式 |
| NoNpDrm app 树 | psvpfsparser 的 -i 指向完整 PCSG 根，保留所需 sce_pfs、eboot 及资源 |
| zRIF/work.bin | 按资源格式和工具接口确认；常见工作键在 `work.bin[0x50:0x60]` |
| 已解资源 | 复用源及通过记录，不重复解 PFS |

授权来源优先用户提供或随包 work.bin；本机既有 games.json 仅作适用数据源。
按输入版本核对 key/zRIF，解密成功结合 keystone/HMAC 和相关资源结构确认。

## 故障定位

| 信号 | 核对 |
|---|---|
| files.db 后 JSON expected value | F00D 服务响应及网络、工具解析；也检查本地元数据 |
| header signature invalid | 授权字段、zRIF、源格式和工具支持，不直接判损坏 |
| unicv.db 缺失 | 输入根及资源树是否完整 |
| 零输出、0xC0000135 | 依赖 DLL、工作目录和实际退出码 |
| Crypto Engine failed | 失败文件、偏移、SDK/PFS 变体、ICV 及取键链 |

旧工具可能在大文件签名块后失败。
失败点、前段可验证内容及同工具对照只用于缩小原因；
固定失败偏移不证明授权正确、dump 无损或 SDK 不受支持。
不通过置零、截断、改名或占位成员绕过元数据检查。

需要时使用已支持的解析器、匹配源码版本或已授权的解密态来源。
未解关键文件记录缺口，不把跳过文件后的结果宣称完整。

## Windows 路径与依赖

按工具实际支持传 Windows 路径；只有 CJK 参数确实失败时，
在本作临时目录使用 ASCII 硬链接或副本。
同卷文件可用 `os.link`，跨卷再复制；目录联接与文件硬链接分别处理，
清理仅移除临时入口。

依赖 libcurl 的 psvpfsparser 版本在依赖目录运行或配置明确的 DLL 路径。
eboot 转 ELF 需匹配 self2elf 及授权接口，依赖按实际需要安装。
解密后按资源类型选择文本或二进制解析，不因平台预先做逆向。

## PUA 字形槽

CP932 用户区可映射 PUA，但码位类别不决定字形。
查码表、字体或渲染实现，确定后按槽映射并登记来源。
不按疑问句、断定句或前后文猜标点，不删除未映射字符。
详见 [字体](../decode.md#自定义字体) 与 [解码](../decode.md#字段与编码)。

## 构建记录：platform-psv-pfs

- PSV NoNpDrm：pkg2zip -x → `<psvdec>/…/psvpfsparser.exe -i app/<ID> -o dec -z <zRIF> -f cma.henkaku.xyz`（zRIF 见 `games.json`；放行 `cma.henkaku.xyz:80`，前台运行）。
- NoNpDrm `.zip` 直接解包（无 pkg）：解压后 `-i` 指到含完整文件树的 `<PCSGxxxxx>/` 目录（须有 `eboot.bin`/`sce_pfs`）。
- 许可证常就在包内 ⇒ 无需外部 work.bin / games.json：app 目录的 `sce_sys/package/work.bin`（512 B 明文，
  内容 ID@0x10 如 `JP0031-PCSG01068_00-NEOANGELIQUE0000`、klicensee@0x50:0x60）可直接喂
  `util/zzzrif.py <work.bin> zrif.txt` 生成 zRIF（zzzrif 会把 AID 匿名为 `FAKE_AID`）。先找它，再去找 pkg。
  （2026-10-12 ネオ アンジェリーク 天使の涙 实证：源 zip 内即带此文件。）
- psvpfsparser 必须前台运行：后台进程无法弹网络授权 ⇒ 即使参数正确也会撞上上一条假错。
- 报 `parsing  files.db...` 后紧跟 `Error: <unspecified file>(1): expected value` ⇒ 不是 files.db 损坏，
  而是 psvpfsparser 在解析前向 `cma.henkaku.xyz:80` 取 F00D 密钥（boost JSON 解析）被网络拦截（响应非 JSON）。
  放行网络 + 前台运行即可；成功判据仍是 `keystone: matched retail hmac`。（2026-10-11 参千世界遊戯 实证）
- eboot 转 ELF：`util/self2elf.py -i dec/eboot.bin -o eboot.elf -k <…/sce_sys/package/work.bin>`（需 pycryptodome，
  用 `~/.workbuddy/binaries/python/envs/default`）。ELF 常含代码→Unicode 码表等元数据（见 [rom2.md](../engines/rom2.md)）。

### 工具

本册讲外部工具链（`pkg2zip` / `psvpfsparser` / `zzzrif` / `self2elf`），不需要自研脚本——照上面的命令跑即可。
自己写的部分只有「拿到 romfs 之后」的成行，那属于具体作品，见对应引擎册。
