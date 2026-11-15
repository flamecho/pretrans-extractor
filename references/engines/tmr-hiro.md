# TMR-Hiro ADV

## PAC

7字节头为u16 count、u8 name_width、u24 LE toc_end、保留字节。
项为name[name_width]、u32 offset、size；offset可相对toc_end。
匹配布局满足 `7+(name_width+8)×count=toc_end`，成员范围及累积长度另行验证。

## 剧本记录

命令体变换为每字节高低半字节互换 `(b>>4)|(b<<4)&FF`，不是前后半段互换。
匹配流为u32命令数后重复u16 L和L字节变换体，体内为u16 type、flags及data。
type0可为正文，flags区分名/文/语音参数；type1可为跳转或选择，选择中显示串和目标标签分开。
字面反斜线换行是排版，页界从正文命令及等待确认。＄α/＄β等槽值取初始化，不保存人物值与固定章节顺序。

## 工具

`scripts/tmrpac.py`、`scripts/tmr_srp.py`；复用前核对格式版本与参数。
