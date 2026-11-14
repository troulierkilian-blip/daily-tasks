import csv
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QLocale, QTimer, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from dailytasks.gui import MainWindow, TaskCard, TaskDialog, as_qdate
from dailytasks.store import TaskStore


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QLocale.setDefault(QLocale(QLocale.Language.Chinese, QLocale.Country.China))
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')
        # The offscreen platform has no Windows font database; use OS fonts only in QA.
        if not QFontDatabase.families():
            for filename in ('msyh.ttc', 'msyhbd.ttc', 'segoeui.ttf'):
                path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / filename
                if path.exists():
                    QFontDatabase.addApplicationFont(str(path))
        cls.app.setFont(QFont('Microsoft YaHei UI', 10))

    def setUp(self):
        folder = Path(__file__).resolve().parents[1] / 'artifacts' / 'test-data'
        folder.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=folder)
        self.root = Path(self.temp.name)
        self.store = TaskStore(self.root / 'data')
        self.window = MainWindow(self.store)
        self.window.show()
        QTest.qWait(15)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QTest.qWait(10)
        self.store.close()
        self.temp.cleanup()

    def card(self, task_id):
        QTest.qWait(5)
        for widget in self.window.daily.findChildren(TaskCard):
            if widget.task.id == task_id and not widget.isHidden():
                return widget
        self.fail('任务卡片未显示')

    def test_add_through_dialog_defaults_and_state_controls(self):
        defaults = []

        def fill_dialog():
            dialog = QApplication.activeModalWidget()
            defaults.append(dialog.fields())
            dialog.title_input.setText('从界面新增的任务')
            dialog.notes_input.setPlainText('中文备注\n详细步骤')
            dialog.validate_and_accept()

        QTimer.singleShot(50, fill_dialog)
        QTest.mouseClick(self.window.add_button, Qt.MouseButton.LeftButton)
        self.assertEqual(defaults[0]['task_date'], date.today())
        self.assertEqual(defaults[0]['priority'], 2)
        self.assertEqual(defaults[0]['status'], 'pending')
        task = self.store.list_tasks()[0]
        card = self.card(task.id)
        card.status_combo.setCurrentIndex(card.status_combo.findData('in_progress'))
        QTest.qWait(10)
        self.assertEqual(self.store.get(task.id).status, 'in_progress')
        QTest.mouseClick(self.card(task.id).complete_button, Qt.MouseButton.LeftButton)
        QTest.qWait(10)
        self.assertEqual(self.store.get(task.id).status, 'done')
        self.assertEqual(self.window.daily.metrics.values[3].text(), '100%')
        QTest.mouseClick(self.card(task.id).complete_button, Qt.MouseButton.LeftButton)
        QTest.qWait(10)
        self.assertEqual(self.store.get(task.id).status, 'pending')

    def test_edit_and_confirmed_delete(self):
        task = self.store.add(date.today(), '原标题')
        self.window.refresh()

        def change_dialog():
            dialog = QApplication.activeModalWidget()
            dialog.title_input.setText('编辑后的标题')
            dialog.notes_input.setPlainText('长备注' * 1000)
            dialog.status_input.setCurrentIndex(dialog.status_input.findData('done'))
            dialog.validate_and_accept()

        QTimer.singleShot(30, change_dialog)
        self.window.edit_task(task.id)
        self.assertEqual(self.store.get(task.id).title, '编辑后的标题')
        self.assertEqual(self.store.get(task.id).status, 'done')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            self.window.delete_task(task.id)
        self.assertEqual(len(self.store.list_tasks()), 1)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            self.window.delete_task(task.id)
        self.assertEqual(self.store.list_tasks(), [])

    def test_history_filters_and_filtered_export(self):
        yesterday = date.today() - timedelta(days=1)
        self.store.add(yesterday, '历史实验', status='done')
        self.store.add(date.today(), '今天实验', status='pending')
        self.window.navigate(1)
        page = self.window.history
        self.assertEqual(len(page.displayed_tasks), 2)
        page.search.setText('历史')
        # Export must use the entered filter immediately, before the debounce timer.
        destination = self.root / '筛选.csv'
        with patch('dailytasks.gui.QFileDialog.getSaveFileName', return_value=(str(destination), '')):
            self.window.export_current()
        with destination.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], '历史实验')
        QTest.qWait(210)
        self.assertEqual(len(page.displayed_tasks), 1)
        page.search.clear()
        page.all_dates.setChecked(False)
        page.start_date.setDate(as_qdate(date.today()))
        page.end_date.setDate(as_qdate(date.today()))
        QTest.qWait(210)
        self.assertEqual([t.title for t in page.displayed_tasks], ['今天实验'])
        page.start_date.setDate(as_qdate(date.today() + timedelta(days=1)))
        self.assertIn('开始日期', page.count_label.text())

    def test_daily_summary_not_changed_by_list_filter(self):
        self.store.add(date.today(), '已完成任务', status='done')
        self.store.add(date.today(), '进行中任务', status='in_progress')
        self.window.refresh()
        self.window.daily.status_filter.setCurrentIndex(self.window.daily.status_filter.findData('done'))
        self.assertEqual(len(self.window.daily.displayed_tasks), 1)
        self.assertEqual(self.window.daily.metrics.values[0].text(), '2')
        self.assertEqual(self.window.daily.metrics.values[3].text(), '50%')

    def test_failed_save_reverts_status_widget(self):
        task = self.store.add(date.today(), '状态回退检查')
        self.store.connection.execute("CREATE TRIGGER block_ui BEFORE UPDATE ON tasks BEGIN SELECT RAISE(ABORT,'blocked'); END")
        self.window.refresh()
        with self.assertLogs(level='ERROR'), patch.object(QMessageBox, 'critical') as error:
            combo = self.card(task.id).status_combo
            combo.setCurrentIndex(combo.findData('done'))
        QTest.qWait(10)
        self.assertEqual(self.store.get(task.id).status, 'pending')
        self.assertEqual(self.card(task.id).status_combo.currentData(), 'pending')
        error.assert_called_once()

    def test_dialog_validation_and_empty_stats(self):
        dialog = TaskDialog(self.window)
        dialog.title_input.setText('  ')
        dialog.validate_and_accept()
        self.assertTrue(dialog.error_label.isHidden() is False)
        self.assertEqual(dialog.result(), 0)
        dialog.reject()
        self.window.navigate(2)
        self.assertEqual(self.window.stats.metrics.values[3].text(), '—')
        self.assertEqual(len(self.window.stats.chart.days), 7)
        self.window.stats.period.setCurrentIndex(self.window.stats.period.findData('month'))
        self.assertGreaterEqual(len(self.window.stats.chart.days), 28)

    def test_ui_backup_restore(self):
        from dailytasks.gui import QFileDialog
        task = self.store.add(date.today(), '备份记录')
        destination = self.root / '备份.db'
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(destination), '')):
            self.window.backup_data()
        self.store.delete(task.id)
        self.store.add(date.today(), '新记录')
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(destination), '')), \
             patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), \
             patch.object(QMessageBox, 'information') as notice:
            self.window.restore_data()
        self.assertEqual(self.store.get(task.id).title, '备份记录')
        self.assertEqual(len(self.window.daily.displayed_tasks), 1)
        notice.assert_called_once()


if __name__ == '__main__':
    unittest.main()
