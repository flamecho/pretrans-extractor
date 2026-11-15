#!/usr/bin/env python3
"""Task-local validation; maintenance steps run only when explicitly selected.

--report R --text T: check the supplied text and declared final row count.
--report R: read report metadata only; never find or regenerate finished text.
--checked-sha256 HASH: reuse a recorded successful check of unchanged text.
--audit-docs / --distill / --archive: opt-in maintenance; --apply implies archive.
This tool never deletes source or work directories.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

from check_text import report_format, validate_layout

HERE = Path(__file__).resolve().parent


def run(script, args):
    env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    process = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(HERE / script), *args],
                             capture_output=True, text=True, encoding='utf-8', env=env)
    return process.returncode, process.stdout + process.stderr


def report_rows(text):
    """Read the dedicated final-row field from frontmatter, without narrative guessing."""
    front = re.match(r'\A---\s*\n(.*?)\n---(?:\s*\n|$)', text, re.S)
    if not front:
        return None
    values = re.findall(r'^(?:行数|rows)\s*[:：]\s*[\'\"]?([\d,]+)[\'\"]?\s*(?:#.*)?$',
                        front.group(1), re.M)
    rows = {int(value.replace(',', '')) for value in values}
    if len(rows) > 1:
        raise ValueError('报告头部有相互冲突的最终行数')
    return next(iter(rows), None)


def show(label, rc, output):
    print('[%s] %s' % (label, 'PASS' if rc == 0 else 'FAIL'))
    issues = [line for line in output.splitlines() if '[E]' in line or '[W]' in line]
    if rc and not issues:
        issues = [line for line in output.splitlines() if line.strip()][-4:]
    for line in issues[:8]:
        print('  ' + line.strip()[:240])
    if len(issues) > 8:
        print('  其余 %d 项，详查对应工具输出' % (len(issues) - 8))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report')
    parser.add_argument('--text')
    parser.add_argument('--name', help='品检用的主角名')
    parser.add_argument('--game', help='记忆落位用的作品名')
    parser.add_argument('--allow')
    parser.add_argument('--layout-map')
    parser.add_argument('--checked-sha256', help='先前品检通过的文件摘要；匹配才复用品检结果')
    mode_args = parser.add_mutually_exclusive_group()
    mode_args.add_argument('--dual', action='store_const', const=True, dest='dual')
    mode_args.add_argument('--single', action='store_const', const=False, dest='dual')
    parser.add_argument('--inline-name', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--audit-docs', action='store_true')
    parser.add_argument('--distill', action='store_true')
    parser.add_argument('--archive', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--no-distill', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--no-archive', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.report and not args.text:
        parser.error('至少给 --report 或 --text')
    if (args.distill or args.archive or args.apply) and not args.report:
        parser.error('沉淀或落位需要明确 --report')
    if args.no_distill and args.distill:
        parser.error('--distill 与 --no-distill 冲突')
    if args.no_archive and (args.archive or args.apply):
        parser.error('--archive/--apply 与 --no-archive 冲突')
    if (args.checked_sha256 or args.layout_map or args.allow or args.dual is not None) and not args.text:
        parser.error('文本品检选项需要明确 --text；不会自动发现成品')
    if args.checked_sha256 and not re.fullmatch(r'[0-9a-fA-F]{64}', args.checked_sha256):
        parser.error('--checked-sha256 必须为 64 位十六进制摘要')

    failures = []
    report, mode, claim = '', None, None
    if args.report:
        try:
            report = Path(args.report).read_text(encoding='utf-8-sig')
            if args.text:
                mode, claim = report_format(report), report_rows(report)
            print('[报告] 已读取指定文件')
        except (OSError, ValueError) as exc:
            print('[报告] [E] %s' % exc)
            return 1
    dual = args.dual if args.dual is not None else mode == 'dual'
    if args.text and mode is not None and (mode == 'dual') != dual:
        print('[报告] [E] 版式与显式参数不一致')
        return 1

    if args.text:
        try:
            raw = Path(args.text).read_bytes()
            lines = raw.decode('utf-8-sig', 'strict').split('\n')
            if lines and not lines[-1]:
                lines.pop()
        except (OSError, UnicodeError) as exc:
            print('[文本] [E] %s' % exc)
            return 1
        if args.checked_sha256:
            if hashlib.sha256(raw).hexdigest() != args.checked_sha256.lower():
                print('[品检] [E] 摘要不同，不能复用通过记录')
                failures.append('文本已改变，重新品检')
            elif args.report and mode is None:
                print('[品检] [E] 报告未声明版式')
                failures.append('报告缺版式')
            else:
                print('[品检] 复用先前通过记录（SHA256 相同）')
                if args.layout_map:
                    count, errors = validate_layout(args.layout_map, lines, dual, dual)
                    for error in errors:
                        print('[页映射] [E] ' + error)
                    if errors:
                        failures.append('页映射未通过')
                    else:
                        print('[页映射] PASS（%d 个多段页）' % count)
        else:
            check_args = [args.text]
            if args.name:
                check_args += ['--name', args.name]
            if args.report:
                check_args += ['--report', args.report]
            if dual:
                check_args += ['--dual', '--expect-dual']
            if args.layout_map:
                check_args += ['--layout-map', args.layout_map]
            allow = args.allow
            if allow is None:
                text_path = Path(args.text).resolve()
                allow_dir = text_path.parent.parent / '解析报告' / 'allow'
                for filename in (text_path.stem + '.allow', text_path.stem + '_allow.txt'):
                    candidate = allow_dir / filename
                    if candidate.is_file():
                        allow = str(candidate)
                        break
            if allow:
                check_args += ['--allow', allow]
            if args.inline_name:
                check_args += ['--inline-name']
            rc, output = run('check_text.py', check_args)
            show('品检', rc, output)
            if rc:
                failures.append('文本品检未通过')
        if claim is not None:
            if len(lines) != claim:
                print('[行数] [E] 报告 %d ≠ 文本 %d' % (claim, len(lines)))
                failures.append('最终行数不一致')
            else:
                print('[行数] PASS（%d）' % claim)
    else:
        print('[品检] 未给 --text，不查找或生成成品')

    steps = []
    if args.audit_docs:
        steps.append(('文档维护', 'lint_docs.py', []))
    if args.distill:
        steps.append(('沉淀草案', 'distill.py', ['--report', args.report]))
    if args.archive or args.apply:
        archive_args = ['--report', args.report]
        if args.game:
            archive_args += ['--work', args.game]
        if args.apply:
            archive_args += ['--apply']
        steps.append(('记忆落位', 'archive_work.py', archive_args))
    for label, script, step_args in steps:
        rc, output = run(script, step_args)
        show(label, rc, output)
        if rc:
            failures.append(label + '失败（显式维护项）')
        else:
            for line in output.splitlines():
                if re.match(r'^(草案|片段|落位|候选|作品)', line):
                    print('  ' + line[:240])
    print('RESULT:', 'FAIL；' + '；'.join(failures) if failures else 'PASS（所选机器项）')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
