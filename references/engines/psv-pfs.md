# PSV NoNpDrm / PFS

> 路由/一句话索引见 `../engines.md`；主索引见 `../MEMORY.md`。

- **PSV NoNpDrm**：pkg2zip -x → `<psvdec>/…/psvpfsparser.exe -i app/<ID> -o dec -z <zRIF> -f cma.henkaku.xyz`（zRIF 见 `games.json`；放行 `cma.henkaku.xyz:80`，前台运行）。
- **NoNpDrm `.zip` 直接解包（无 pkg）**：解压后 `-i` 指到含完整文件树的 `<PCSGxxxxx>/` 目录（须有 `eboot.bin`/`sce_pfs`）。
- **★ 许可证常就在包内 ⇒ 无需外部 work.bin / games.json**：app 目录的 `sce_sys/package/work.bin`（**512 B 明文**，
  内容 ID@0x10 如 `JP0031-PCSG01068_00-NEOANGELIQUE0000`、**klicensee@0x50:0x60**）可直接喂
  `util/zzzrif.py <work.bin> zrif.txt` 生成 zRIF（zzzrif 会把 AID 匿名为 `FAKE_AID`）。**先找它，再去找 pkg**。
  （2026-10-12 ネオ アンジェリーク 天使の涙 实证：源 zip 内即带此文件。）
- **★ psvpfsparser 必须前台运行**：后台进程无法弹网络授权 ⇒ 即使参数正确也会撞上上一条假错。
- **★ 报 `parsing  files.db...` 后紧跟 `Error: <unspecified file>(1): expected value`** ⇒ **不是 files.db 损坏**，
  而是 psvpfsparser 在解析前向 `cma.henkaku.xyz:80` 取 F00D 密钥（boost JSON 解析）**被网络拦截**（响应非 JSON）。
  放行网络 + 前台运行即可；成功判据仍是 `keystone: matched retail hmac`。（2026-10-11 参千世界遊戯 实证）
- eboot 转 ELF：`util/self2elf.py -i dec/eboot.bin -o eboot.elf -k <…/sce_sys/package/work.bin>`（**需 pycryptodome**，
  用 `~/.workbuddy/binaries/python/envs/default`）。ELF 常含**代码→Unicode 码表**等元数据（见 `rom2-snr.md`）。
