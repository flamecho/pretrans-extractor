# -*- coding: utf-8 -*-
"""ラスト・エスコート2 ～深夜の甘い棘～ 全文本生成

用法：python scripts/build_ls2.py <lsb目录> <输出txt> [统计json]
规则：文件自然序 → 每个 LSB 的条目按记录顺序成行；正文完全相同的文件折叠只留首见；
      排除 UI 操作提示行；0x26 → 主角名「芹香」；0x5C/0x23 同框换行合并；0x25 演出码丢弃。
输出 UTF-8 with BOM + 纯 LF。
"""
import sys, os, re, glob, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lsb

NAME = '芹香'          # 主角默认名（ELF 名槽 芹香 / 安藤；vndb c35939 安藤 芹香）
UI = {
    'ナンバーワンコール中！\x5c（○ボタンを押すと終了します）',
    'シャンパンコール中！\x5c（○ボタンを押すと終了します）',
}


def natkey(p):
    b = os.path.basename(p)
    return ([int(x) for x in re.findall(r'\d+', b)], b)


OK = re.compile(r'^[\u3000-\u303f\u3040-\u30ff\u4e00-\u9fff\uff01-\uff60\u2015\u2018-\u201f\u2026\u203b\u301c\s]+$')


def is_junk(t):
    """短残片 / 私用区 / 半角引号 / 断裂标点 ⇒ 结构垃圾（非正文）"""
    if re.search(r'[\ue000-\uf8ff]', t):
        return True
    if '"' in t or "'" in t:
        return True
    if re.search(r'[〓∀∨∧∃]', t) and len(t) <= 6:
        return True
    if re.match(r'^[、。]', t) and len(t) <= 8:
        return True
    if len(t) <= 4 and not OK.match(t):
        return True
    if len(t) <= 3 and re.search(r'[\uff21-\uff3a\uff41-\uff5a]', t):
        return True
    return False


def main(root, out, stat_path=None):
    files = sorted(glob.glob(os.path.join(root, '*.LSB')), key=natkey)
    lines, seen, dup, stat = [], {}, [], {}
    n_t = n_o = 0
    for f in files:
        name = os.path.basename(f)
        items, title = lsb.parse(f)
        txt = []
        for k, nm, t in items:
            t = lsb.clean(t, NAME)
            # 结构字节（长度字节 / 半角残片）粘在串首尾 ⇒ 裁掉
            t = re.sub(r'^[A-Za-z0-9\uff61-\uff9f]+', '', t)
            t = re.sub(r'[A-Za-z0-9\uff61-\uff9f]+$', '', t)
            if is_junk(t):
                continue
            if not t or t in UI or len(t) < 2:
                continue
            txt.append(t)
        key = hashlib.md5('\n'.join(txt).encode()).hexdigest()
        if txt and key in seen:
            dup.append((name, seen[key]))
            continue
        if txt:
            seen[key] = name
        stat[name] = {'title': title, 'lines': len(txt)}
        lines.extend(txt)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fp:
        fp.write('\n'.join(lines) + '\n')
    if stat_path:
        json.dump({'files': stat, 'collapsed': dup, 'lines': len(lines)},
                  open(stat_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'保留 {len(stat)} 个文件 / 折叠 {len(dup)} 个 / 行数 {len(lines)}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
