# Vridge · MEMFS / TAT

## MEMFS / TAT

script.memfs索引和script.membody通过偏移、长度关联，RZ包装可解出zlib后的UTF-8 BOM文本。
索引、压缩与脚本类型分别确认，TATC编译体使用[TATC](otomate-tatc-rson.md)。

## 文本显示

先扫描标签、行/块注释、命令和引号，再处理正文中的KW边界。
KW为等待，WinClear为清屏；同页多个KW保留新增点击段，物理换行按排版处理。
SltAdd通过参数取选项显示文案；姓名可有独立行或模板，按实际窗口确认。
#R基底/读音、#C颜色、#T条件模板及姓名变量均按完整语法展开。
