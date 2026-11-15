#!/usr/bin/env python3
"""检查技能文档的文件、章节链接、导航可达性和 Markdown 排版。

python scripts/lint_docs.py --skill <技能目录> --mem <可选工作记录目录> --quiet
引擎与平台资料属于技能自身，按完整相对路径检查，覆盖嵌套构建目录。
"""
import argparse
import re
from collections import Counter, deque
from pathlib import Path

SKILL_DEF = Path(__file__).resolve().parent.parent
if not (SKILL_DEF / 'SKILL.md').is_file():
    SKILL_DEF = Path.home() / '.workbuddy/skills/vn-custom-bytecode-text'


def slug(text):
    text = re.sub(r'<[^>]*>', '', text).lower()
    return re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '-')


def parse(text):
    prose, anchors, layout, counts, fence, table = [], set(), [], Counter(), None, []
    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            fence = marker[1][0] if fence is None else None
            continue
        if fence:
            continue
        if line != line.rstrip():
            layout.append(f'L{number} 行尾空格')
        heading = re.match(r'^#{1,6}\s+(.+?)\s*#*\s*$', line)
        if heading:
            anchor = slug(heading[1])
            ordinal = counts[anchor]
            counts[anchor] += 1
            anchors.add(anchor + ('-' + str(ordinal) if ordinal else ''))
        if line.startswith('|') and line.endswith('|'):
            table.append((number, len(re.split(r'(?<!\\)\|', line)) - 2))
        else:
            if len(table) > 1 and len({width for _, width in table}) > 1:
                layout.append(f'L{table[0][0]} 表格列数不一')
            table = []
        prose.append(re.sub(r'`+[^`\n]*`+', '', line))
    if len(table) > 1 and len({width for _, width in table}) > 1:
        layout.append(f'L{table[0][0]} 表格列数不一')
    if fence:
        layout.append('代码围栏未闭合')
    return '\n'.join(prose), anchors, layout


def collect(skill, mem=None):
    skill = Path(skill).resolve()
    resources = [skill / 'SKILL.md', *sorted((skill / 'references').rglob('*.md')),
                 *sorted((skill / 'scripts').rglob('*.md'))]
    resources = [path for path in resources if path.is_file()]
    files = set(resources)
    if mem and Path(mem).is_dir():
        files.update(path.resolve() for path in Path(mem).glob('*.md')
                     if not re.match(r'^\d{4}-\d{2}-\d{2}', path.name))
    return resources, sorted(files)


def check(skill, mem=None):
    skill = Path(skill).resolve()
    resources, files = collect(skill, mem)
    metadata = {path: parse(path.read_text(encoding='utf-8')) for path in files}
    graph, broken, layout = {}, [], []
    for path, (prose, _, formatting) in metadata.items():
        graph[path] = set()
        if path in resources:
            layout.extend((path, message) for message in formatting)
            if b'\r' in path.read_bytes():
                layout.append((path, 'Markdown 行尾应为 LF'))
        for target in re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)', prose):
            if re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I) and not re.match(r'^[a-z]:[/\\]', target, re.I):
                continue
            filename, _, anchor = target.partition('#')
            destination = (path.parent / filename).resolve() if filename else path
            if not destination.is_file():
                broken.append((path, target, '文件不存在'))
                continue
            if destination in metadata:
                graph[path].add(destination)
            if anchor and destination.suffix == '.md':
                target_meta = metadata.get(destination) or parse(destination.read_text(encoding='utf-8'))
                if anchor not in target_meta[1]:
                    broken.append((path, target, '章节不存在'))
    reached, pending = set(), deque([skill / 'SKILL.md'])
    while pending:
        path = pending.popleft()
        if path in reached:
            continue
        reached.add(path)
        pending.extend(graph.get(path, ()))
    orphan = [path for path in resources if path not in reached]
    return files, broken, orphan, layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', default=str(SKILL_DEF))
    parser.add_argument('--mem', default=str(Path.cwd() / '.workbuddy/memory'))
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    files, broken, orphan, layout = check(args.skill, args.mem)
    if not args.quiet:
        for path, target, reason in broken[:20]:
            print(f'[断链] {path.name} → {target}：{reason}')
        for path in orphan[:20]:
            print(f'[孤儿] {path}')
        for path, message in layout[:20]:
            print(f'[排版] {path.name}：{message}')
    print(f'文件 {len(files)} ｜ 断链 {len(broken)} ｜ 孤儿 {len(orphan)} ｜ 排版 {len(layout)}')
    return int(bool(broken or orphan or layout))


if __name__ == '__main__':
    raise SystemExit(main())
