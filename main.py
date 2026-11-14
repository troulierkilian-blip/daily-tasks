"""Desktop entrypoint, with isolated verification flags for executable acceptance."""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import sys
import traceback
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QLockFile, QLocale, QStandardPaths, QTimer, qVersion
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from dailytasks import __version__
from dailytasks.gui import MainWindow, app_icon
from dailytasks.store import TaskStore


def main() -> int:
    parser = argparse.ArgumentParser(description='每日任务桌面软件')
    parser.add_argument('--data-dir', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--smoke-test', choices=['write', 'read'], help=argparse.SUPPRESS)
    parser.add_argument('--smoke-report', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--screenshot', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.smoke_test and (not args.data_dir or not args.smoke_report):
        parser.error('验收模式必须指定独立的数据目录和报告路径。')
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('DailyTasks.Desktop.1')
    QApplication.setApplicationName('DailyTasks')
    QApplication.setApplicationDisplayName('每日任务')
    QApplication.setOrganizationName('')
    QLocale.setDefault(QLocale(QLocale.Language.Chinese, QLocale.Country.China))
    app = QApplication([sys.argv[0]])
    app.setStyle('Fusion')
    app.setFont(QFont('Microsoft YaHei UI', 10))
    app.setWindowIcon(app_icon())
    directory = args.data_dir or Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation))
    directory = directory.resolve()
    store = None
    lock = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(
            directory / 'app.log', maxBytes=1_000_000, backupCount=2, encoding='utf-8')],
            format='%(asctime)s %(levelname)s %(message)s')
        lock = QLockFile(str(directory / 'instance.lock'))
        if not lock.tryLock(100):
            QMessageBox.information(None, '每日任务已在运行', '请切换到已打开的「每日任务」窗口。')
            return 0
        store = TaskStore(directory)
        window = MainWindow(store)
        screen = app.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            window.resize(min(1180, max(920, available.width() - 40)),
                          min(810, max(660, available.height() - 60)))

        def exception_hook(exc_type, exc, tb):
            logging.error('界面异常', exc_info=(exc_type, exc, tb))
            if args.smoke_test:
                write_report({'ok': False, 'error': str(exc), 'traceback': ''.join(traceback.format_exception(exc_type, exc, tb))})
                app.exit(1)
            else:
                QMessageBox.critical(window, '操作未完成', f'操作未完成：{exc}\n请重试。详情已记录到数据文件夹中的 app.log。')

        sys.excepthook = exception_hook
        window.show()

        def write_report(content):
            args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_report.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')

        def smoke():
            try:
                title = 'EXE 验收：新增、完成、重开'
                if args.smoke_test == 'write':
                    task = store.add(date.today(), title, '独立目录验收记录', 3)
                    window.change_status(task.id, 'in_progress')
                    assert store.get(task.id).status == 'in_progress'
                    window.change_status(task.id, 'done')
                    task = store.get(task.id)
                    assert task.completed_at is not None
                else:
                    tasks = store.list_tasks(keyword=title)
                    assert len(tasks) == 1, '重开后任务数量不一致'
                    task = tasks[0]
                    assert task.status == 'done' and task.completed_at is not None, '任务状态未持久化'
                window.refresh()
                app.processEvents()
                if args.screenshot:
                    args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                    assert window.grab().save(str(args.screenshot)), '截图保存失败'
                write_report({'ok': True, 'phase': args.smoke_test, 'frozen': bool(getattr(sys, 'frozen', False)),
                              'version': __version__, 'qt': qVersion(), 'data_dir': str(directory),
                              'task_title': task.title, 'task_status': task.status,
                              'task_id': task.id, 'completed_at': task.completed_at})
                app.exit(0)
            except Exception as error:
                logging.exception('EXE 验收失败')
                write_report({'ok': False, 'error': str(error), 'traceback': traceback.format_exc()})
                app.exit(1)

        if args.smoke_test:
            QTimer.singleShot(400, smoke)
        logging.info('应用启动 v%s，数据目录 %s', __version__, directory)
        return app.exec()
    except Exception as error:
        logging.exception('应用启动失败')
        if args.smoke_test:
            args.smoke_report.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_report.write_text(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False), encoding='utf-8')
        else:
            QMessageBox.critical(None, '无法启动每日任务',
                f'无法打开数据文件夹或数据库：\n{error}\n\n数据位置：\n{directory}\n\n原始数据会保留，请检查文件权限或联系维护者。')
        return 1
    finally:
        if store is not None:
            store.close()
        if lock is not None:
            lock.unlock()


if __name__ == '__main__':
    raise SystemExit(main())
