"""Generate isolated UI previews at different scales; no real user records are read."""

import argparse
import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser()
parser.add_argument('--scale', type=float, default=1)
args = parser.parse_args()
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_SCALE_FACTOR'] = str(args.scale)

from PySide6.QtCore import QLocale
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from dailytasks.gui import MainWindow, TaskCard, TaskDialog
from dailytasks.store import TaskStore
from build import prepare_assets

QLocale.setDefault(QLocale(QLocale.Language.Chinese, QLocale.Country.China))
app = QApplication([])
app.setStyle('Fusion')
for filename in ('msyh.ttc', 'msyhbd.ttc', 'segoeui.ttf'):
    path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / filename
    if path.exists():
        QFontDatabase.addApplicationFont(str(path))
app.setFont(QFont('Microsoft YaHei UI', 10))
prepare_assets(ROOT)
output = ROOT / 'artifacts' / 'ui'
output.mkdir(parents=True, exist_ok=True)
prefix = 'scale-' + str(args.scale).replace('.', '_')

with tempfile.TemporaryDirectory(dir=output) as temporary:
    store = TaskStore(Path(temporary) / 'data')
    today = date.today()
    examples = [
        ('整理今天的工作计划', '明确三项优先事项，留出实验和阅读时间。', 3, 'done'),
        ('阅读并整理两篇文献', '记录研究问题、方法与结论，补充到文献笔记。', 3, 'in_progress'),
        ('完成实验数据分析', '检查原始数据，绘制结果图，核对异常点。', 2, 'in_progress'),
        ('准备本周汇报', '汇总进展与待解决问题。', 2, 'pending'),
        ('备份项目资料', '', 1, 'pending'),
        ('散步 30 分钟', '晚饭后出门。', 1, 'done'),
    ]
    for title, notes, priority, status in examples:
        store.add(today, title, notes, priority, status)
    for offset in range(1, 7):
        for i in range(offset % 4 + 2):
            store.add(today - timedelta(days=offset), f'第 {offset} 天任务 {i + 1}',
                '需要继续的任务' if i else '', (i % 3) + 1, 'done' if i % 2 == 0 else 'pending')
    window = MainWindow(store)
    window.show()
    QTest.qWait(80)
    assert window.grab().save(str(output / (prefix + '-today.png')))
    metrics = []
    for card in window.daily.findChildren(TaskCard):
        if not card.isHidden():
            metrics.append({'title': card.task.title, 'height': card.height(),
                'hint': card.sizeHint().height(), 'width': card.width()})
    window.navigate(1)
    QTest.qWait(50)
    assert window.grab().save(str(output / (prefix + '-history.png')))
    window.navigate(2)
    QTest.qWait(50)
    assert window.grab().save(str(output / (prefix + '-stats.png')))
    window.stats.period.setCurrentIndex(window.stats.period.findData('month'))
    QTest.qWait(30)
    assert window.grab().save(str(output / (prefix + '-month.png')))
    window.resize(980, 680)
    QTest.qWait(50)
    assert window.grab().save(str(output / (prefix + '-minimum.png')))
    dialog = TaskDialog(window)
    dialog.title_input.setText('长标题与中文输入验证：' + '请核对实验记录和分析结果，' * 8)
    dialog.notes_input.setPlainText('这是一条包含多行内容的备注。\n' * 100)
    dialog.show()
    QTest.qWait(30)
    assert dialog.grab().save(str(output / (prefix + '-dialog.png')))
    dialog.close()
    dialog.deleteLater()
    window.close()
    window.deleteLater()
    QTest.qWait(20)
    store.close()
    print(json.dumps({'scale': args.scale, 'screenshots': str(output), 'cards': metrics}, ensure_ascii=False))
