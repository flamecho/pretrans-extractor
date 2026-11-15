#!/usr/bin/env python3
"""Regression fixtures for source layout checks and task-scoped wrapup."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import check_text
import wrapup


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.test_root = Path(os.environ.get('VN_TEST_TMPDIR', os.getcwd())).resolve()
        self.temp = tempfile.TemporaryDirectory(prefix='vn_workflow_', dir=self.test_root)
        self.root = Path(self.temp.name).resolve()
        self.assertEqual(self.root.parent, self.test_root)

    def tearDown(self):
        self.assertEqual(self.root.parent, self.test_root)
        self.temp.cleanup()

    def text_fixture(self, lines, mode='单版'):
        out = self.root / 'out'
        out.mkdir(exist_ok=True)
        path = out / 'sample.txt'
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8-sig', newline='\n')
        report = self.root / 'report.md'
        report.write_text('---\n行数: %d\n---\n- **版式**：%s\n' % (len(lines), mode),
                          encoding='utf-8', newline='\n')
        allow = self.root / '解析报告' / 'allow'
        allow.mkdir(parents=True, exist_ok=True)
        chars = sorted({ch for line in lines for ch in line if not self.cjk(ch)})
        (allow / 'sample.charset').write_text(''.join(ch + '\t1\n' for ch in chars),
                                            encoding='utf-8', newline='\n')
        return path, report

    @staticmethod
    def cjk(ch):
        n = ord(ch)
        return any(lo <= n <= hi for lo, hi in ((0x3000, 0x30ff), (0x3400, 0x9fff),
                                                (0xff01, 0xff60), (0xffe0, 0xffee)))

    def page_map(self, pages):
        path = self.root / 'pages.json'
        path.write_text(json.dumps({'pages': pages}, ensure_ascii=False), encoding='utf-8')
        return str(path)

    def run_check(self, path, **kwargs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = check_text.check(str(path), [], 200, True, **kwargs)
        return result, output.getvalue()

    def run_wrap(self, arguments):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['wrapup.py', *map(str, arguments)]), contextlib.redirect_stdout(output):
            result = wrapup.main()
        return result, output.getvalue()

    def test_long_and_short_pages_are_not_limited_to_four_segments(self):
        segments = ['文章の第%d段です。' % n for n in range(18)]
        lines = segments + [''.join(segments)]
        self.assertEqual(check_text.merged_candidates(lines), 1)
        mapping = self.page_map([{'segments': list(range(1, 19)), 'merged': 19}])
        self.assertEqual(check_text.validate_layout(mapping, lines, True, True), (1, []))
        self.assertEqual(check_text.merged_candidates(['あ', 'い', 'あい']), 1)

    def test_single_click_coincidence_does_not_become_dual(self):
        path, report = self.text_fixture(['今日は晴れですね。', 'そうですね。', '今日は晴れですね。そうですね。'])
        passed, output = self.run_check(path, report=str(report))
        self.assertTrue(passed, output)
        self.assertIn('[W] 紧邻拼接候选', output)
        self.assertNotIn('[E]', output)

    def test_source_partial_quotes_and_two_dialogues_are_preserved(self):
        path, _ = self.text_fixture(['「ふたりともおはよ！」「！ お、おはようございます！」', '「途中', '」'])
        passed, output = self.run_check(path)
        self.assertTrue(passed, output)
        self.assertIn('[W]', output)
        self.assertNotIn('[E]', output)

    def test_named_page_can_supply_source_generated_merged_text(self):
        lines = ['甲「前半', '甲後半」', '甲「前半後半」']
        mapping = self.page_map([{'segments': [1, 2], 'merged': 3,
                                 'merged_text': lines[2], 'source': 'source.ks:10'}])
        self.assertEqual(check_text.merged_candidates(lines), 0)
        self.assertEqual(check_text.validate_layout(mapping, lines, True, True), (1, []))

    def test_wrong_missing_or_reused_mapped_lines_are_errors(self):
        for page in ({'segments': [1, 2], 'merged': 3}, {'segments': [1, 2], 'merged': 9},
                     {'segments': [True, 2], 'merged': 3}, {'segments': [2, 1], 'merged': 3}):
            with self.subTest(page=page):
                self.assertTrue(check_text.validate_layout(self.page_map([page]), ['あ', 'い', '誤'], True)[1])
        page = {'segments': [1, 2], 'merged': 3}
        self.assertTrue(check_text.validate_layout(self.page_map([page, page]), ['あ', 'い', 'あい'], True)[1])
        self.assertTrue(check_text.validate_layout(self.page_map([]), [], True, True)[1])
        self.assertTrue(check_text.validate_layout(self.page_map([page]), ['あ', 'い', 'あい'], False)[1])

    def test_report_field_is_explicit_and_conflicts_are_errors(self):
        self.assertIsNone(check_text.report_format('正文不需要双版对照；不使用 --inline-name。'))
        self.assertEqual(check_text.report_format('- **版式**：单版（无双版）'), 'single')
        with self.assertRaises(ValueError):
            check_text.report_format('版式：单版\n版式：双版对照')
        path, report = self.text_fixture(['文章です。'], '双版对照')
        self.assertFalse(self.run_check(path, report=str(report))[0])
        self.assertFalse(self.run_check(path, expect_dual=True)[0])

    def test_wrapup_default_only_runs_task_check_and_uses_declared_mode(self):
        path, report = self.text_fixture(['甲「前半', '後半」', '甲「前半後半」'], '双版对照')
        with report.open('a', encoding='utf-8') as f:
            f.write('本作不需要 --inline-name。\n')
        with patch.object(wrapup, 'run', return_value=(0, 'RESULT: PASS')) as runner:
            result, output = self.run_wrap(['--report', report, '--text', path])
        self.assertEqual(result, 0, output)
        self.assertEqual(runner.call_count, 1)
        script, arguments = runner.call_args.args
        self.assertEqual(script, 'check_text.py')
        self.assertIn('--report', arguments)
        self.assertIn('--dual', arguments)
        self.assertIn('--expect-dual', arguments)
        self.assertNotIn('--inline-name', arguments)

    def test_report_only_neither_discovers_text_nor_creates_artifacts(self):
        report = self.root / 'report.md'
        report.write_text('# 指定的清理记录\n版式：旧报告自定义字段\n', encoding='utf-8')
        before = sorted(self.root.rglob('*'))
        with patch.object(wrapup, 'run') as runner:
            result, output = self.run_wrap(['--report', report])
        self.assertEqual(result, 0, output)
        runner.assert_not_called()
        self.assertEqual(before, sorted(self.root.rglob('*')))

    def test_saved_check_is_reused_only_for_matching_hash(self):
        path, report = self.text_fixture(['文章です。'])
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        with patch.object(wrapup, 'run') as runner:
            self.assertEqual(self.run_wrap(['--report', report, '--text', path, '--checked-sha256', sha])[0], 0)
            self.assertEqual(self.run_wrap(['--report', report, '--text', path, '--checked-sha256', '0' * 64])[0], 1)
        runner.assert_not_called()

    def test_final_row_mismatch_blocks_even_when_text_check_passes(self):
        path, report = self.text_fixture(['文章です。'])
        report.write_text('---\n行数: 2\n---\n版式：单版\n', encoding='utf-8')
        with patch.object(wrapup, 'run', return_value=(0, 'PASS')):
            result, output = self.run_wrap(['--report', report, '--text', path])
        self.assertEqual(result, 1)
        self.assertIn('[行数] [E]', output)

    def test_apply_is_explicit_archive_without_other_maintenance(self):
        report = self.root / 'report.md'
        report.write_text('作品记录\n', encoding='utf-8')
        with patch.object(wrapup, 'run', return_value=(0, '落位：完成')) as runner:
            result, output = self.run_wrap(['--report', report, '--apply', '--game', '作品名'])
        self.assertEqual(result, 0, output)
        runner.assert_called_once_with('archive_work.py', ['--report', str(report), '--work', '作品名', '--apply'])

    def test_utf8_is_forced_for_children_and_real_check(self):
        script = self.root / 'utf8_fixture.py'
        script.write_text("print('中文验证：完成')\n", encoding='utf-8')
        with patch.dict(os.environ, {'PYTHONIOENCODING': 'ascii', 'PYTHONUTF8': '0'}):
            rc, output = wrapup.run(str(script), [])
        self.assertEqual(rc, 0, output)
        self.assertEqual(output.strip(), '中文验证：完成')
        path, report = self.text_fixture(['文章です。'])
        result, output = self.run_wrap(['--report', report, '--text', path])
        self.assertEqual(result, 0, output)
        self.assertIn('[品检] PASS', output)


if __name__ == '__main__':
    unittest.main()
