import csv
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from dailytasks.store import TaskStore, summary


class StoreTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / 'artifacts' / 'test-data'
        test_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=test_root)
        self.root = Path(self.temp.name)
        self.store = TaskStore(self.root / 'data')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_status_cycle_and_persistence(self):
        task = self.store.add(date.today(), '编写每日安排', '中文备注\n下一步', 3)
        self.assertEqual(task.status, 'pending')
        self.assertIsNone(task.completed_at)
        self.store.set_status(task.id, 'in_progress')
        done = self.store.set_status(task.id, 'done')
        self.assertIsNotNone(done.completed_at)
        self.store.close()
        self.store = TaskStore(self.root / 'data')
        reopened = self.store.get(task.id)
        self.assertEqual(reopened, done)
        unchanged = self.store.update(task.id, task_date=date.today(), title='编辑后标题',
            notes=task.notes, priority=2, status='done')
        self.assertEqual(unchanged.completed_at, done.completed_at)
        for state in ('in_progress', 'pending', 'done', 'pending'):
            result = self.store.set_status(task.id, state)
            self.assertEqual(result.status, state)
            self.assertEqual(result.completed_at is not None, state == 'done')

    def test_copy_preserves_yesterday_and_resets_status(self):
        yesterday = date.today() - timedelta(days=1)
        task = self.store.add(yesterday, '继续实验', '步骤不变', 3, 'in_progress')
        before = self.store.report(yesterday, yesterday)
        copied = self.store.copy_to_today(task.id)
        self.assertNotEqual(copied.id, task.id)
        self.assertEqual(copied.task_date, date.today().isoformat())
        self.assertEqual(copied.status, 'pending')
        self.assertEqual((copied.title, copied.notes, copied.priority), (task.title, task.notes, task.priority))
        self.assertEqual(self.store.get(task.id), task)
        self.assertEqual(self.store.report(yesterday, yesterday), before)

    def test_edit_and_delete(self):
        task = self.store.add('2026-10-01', '初稿')
        changed = self.store.update(task.id, task_date='2026-10-02', title='修改标题',
            notes='长备注' * 2000, priority=1, status='in_progress')
        self.assertEqual(changed.task_date, '2026-10-02')
        self.assertEqual(len(changed.notes), 6000)
        self.assertEqual(changed.created_at, task.created_at)
        self.store.delete(task.id)
        self.assertEqual(self.store.list_tasks(), [])

    def test_filters_and_literal_special_characters(self):
        self.store.add('2026-10-01', '读论文', '标记 100%_完成', status='done')
        self.store.add('2026-10-02', '整理数据', '读论文结果', status='in_progress')
        self.store.add('2026-10-03', '实验安排')
        self.assertEqual(len(self.store.list_tasks(keyword='读论文')), 2)
        self.assertEqual(len(self.store.list_tasks(keyword='%_')), 1)
        self.assertEqual(len(self.store.list_tasks(keyword="' OR 1=1 --")), 0)
        self.assertEqual(len(self.store.list_tasks(start='2026-10-01', end='2026-10-02')), 2)
        self.assertEqual(len(self.store.list_tasks(status='in_progress')), 1)
        self.assertEqual(len(self.store.list_tasks(keyword='读论文', status='done')), 1)
        with self.assertRaises(ValueError):
            self.store.list_tasks(start='2026-10-03', end='2026-10-01')

    def test_weighted_statistics_and_empty_dates(self):
        first, last = date(2026, 10, 1), date(2026, 10, 3)
        self.store.add(first, '完成', status='done')
        for i in range(3):
            self.store.add(first + timedelta(days=1), f'未完成{i}')
        result = self.store.report(first, last)
        self.assertEqual(result['total'], 4)
        self.assertEqual(result['rate'], .25)
        self.assertEqual(result['days'][0]['rate'], 1)
        self.assertEqual(result['days'][1]['rate'], 0)
        self.assertIsNone(result['days'][2]['rate'])
        self.assertIsNone(summary([])['rate'])

    def test_csv_bom_multiline_and_formula_escaping(self):
        task = self.store.add(date.today(), '=1+1', '备注,引号"\n第二行')
        destination = self.root / '导出.csv'
        self.store.export_csv(destination, [task])
        self.assertTrue(destination.read_bytes().startswith(b'\xef\xbb\xbf'))
        with destination.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[0][1], '任务标题')
        self.assertEqual(rows[1][1], "'=1+1")
        self.assertEqual(rows[1][2], task.notes)
        self.assertEqual(rows[1][4], '待开始')

    def test_backup_restore_preserves_safety_copy(self):
        task = self.store.add(date.today(), '备份前的记录', status='done')
        backup = self.store.backup(self.root / '备份.db')
        self.store.delete(task.id)
        new = self.store.add(date.today(), '恢复前的新记录')
        safety = self.store.restore(backup)
        self.assertEqual(self.store.list_tasks(), [task])
        self.assertTrue(safety.exists())
        with sqlite3.connect(safety) as conn:
            self.assertEqual(conn.execute('SELECT id FROM tasks').fetchone()[0], new.id)
        self.store.close()
        self.store = TaskStore(self.root / 'data')
        self.assertEqual(self.store.get(task.id), task)

    def test_invalid_backups_do_not_change_records(self):
        task = self.store.add(date.today(), '需要保留的任务')
        invalid = self.root / '无效.db'
        invalid.write_bytes(b'not sqlite')
        with self.assertRaises(sqlite3.DatabaseError):
            self.store.restore(invalid)
        self.assertEqual(self.store.get(task.id), task)
        unrelated = self.root / '其他软件.db'
        with sqlite3.connect(unrelated) as conn:
            conn.execute('CREATE TABLE unrelated (id INTEGER)')
        with self.assertRaises(ValueError):
            self.store.restore(unrelated)
        self.assertEqual(self.store.get(task.id), task)
        with self.assertRaises(ValueError):
            self.store.restore(self.store.path)

    def test_invalid_task_writes_are_rejected_without_mutation(self):
        invalid = [dict(title='  '), dict(title='长' * 201), dict(title='标题', notes='长' * 20001),
                   dict(title='标题', status='unknown'), dict(title='标题', priority=0),
                   dict(title='标题', task_date='2026-02-30')]
        for fields in invalid:
            values = {'task_date': date.today(), **fields}
            with self.assertRaises(ValueError):
                self.store.add(**values)
        self.assertEqual(self.store.list_tasks(), [])

    def test_broken_existing_database_is_not_replaced(self):
        self.store.close()
        original = b'broken existing database data'
        self.store.path.write_bytes(original)
        with self.assertRaises(sqlite3.DatabaseError):
            TaskStore(self.root / 'data')
        self.assertEqual(self.store.path.read_bytes(), original)

    def test_transaction_failure_does_not_show_a_successful_change(self):
        task = self.store.add(date.today(), '写入失败时保留')
        with sqlite3.connect(self.store.path) as conn:
            conn.execute("CREATE TRIGGER block_write BEFORE UPDATE ON tasks BEGIN SELECT RAISE(ABORT,'test blocked'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.set_status(task.id, 'done')
        self.assertEqual(self.store.get(task.id), task)


if __name__ == '__main__':
    unittest.main()
