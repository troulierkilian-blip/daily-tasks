"""Native Qt Widgets interface. All visual assets are drawn locally."""

from __future__ import annotations

import calendar
import logging
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath, QPen,
    QPixmap, QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QCalendarWidget, QCheckBox, QComboBox, QDateEdit, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QToolButton,
    QToolTip, QVBoxLayout, QWidget,
)

from .store import PRIORITY_LABELS, STATUS_LABELS, Task, TaskStore, summary

ACCENT = '#7060de'
MUTED = '#8490a4'
WEEKDAYS = '一二三四五六日'

STYLE = """
QWidget { font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', sans-serif;
    font-size: 13px; color: #27334a; }
QMainWindow, #Workspace { background: #f5f6fa; }
#Sidebar { background: white; border-right: 1px solid #e7eaf2; }
QLabel { background: transparent; }
QLabel#Brand { font-size: 21px; font-weight: 700; color: #27334a; }
QLabel#PageTitle { font-size: 27px; font-weight: 700; }
QLabel#Muted { color: #8590a3; font-size: 12px; }
QLabel#SectionTitle { font-size: 15px; font-weight: 600; }
QLabel#MetricValue { font-size: 28px; font-weight: 700; }
QFrame#Panel, QFrame#TaskCard { background: white; border: 1px solid #e9ebf2; border-radius: 12px; }
QFrame#TaskCard:hover { border-color: #d3cdef; }
QFrame#TodayPanel { background: #f4f2ff; border: 0; border-radius: 12px; }
QPushButton { background: white; border: 1px solid #e1e5ee; border-radius: 7px;
    padding: 9px 15px; font-weight: 500; }
QPushButton:hover { background: #f3f1fc; border-color: #d2cbef; }
QPushButton:pressed { background: #e9e4fa; }
QPushButton:disabled { color: #b1b8c5; background: #f4f5f8; }
QPushButton#Primary { background: #7060de; color: white; border: 1px solid #7060de; }
QPushButton#Primary:hover { background: #6150d1; }
QPushButton#Primary:pressed { background: #5443bd; }
QPushButton#Nav { border: none; background: transparent; text-align: left;
    padding: 12px 17px; font-size: 14px; }
QPushButton#Nav:hover { background: #f7f6fc; }
QPushButton#Nav:checked { background: #eeebfc; color: #6b58d6; font-weight: 600; }
QPushButton#Link { border: 0; background: transparent; color: #7060de; padding: 7px; }
QToolButton { border: none; background: transparent; border-radius: 6px; padding: 6px; }
QToolButton:hover { background: #efecfb; }
QToolButton::menu-indicator { image: none; }
QLineEdit, QPlainTextEdit, QDateEdit, QComboBox { border: 1px solid #e1e5ee;
    border-radius: 7px; background: white; padding: 8px 10px; selection-background-color: #7060de; }
QLineEdit:focus, QPlainTextEdit:focus, QDateEdit:focus, QComboBox:focus { border-color: #9688e8; }
QLineEdit:disabled, QDateEdit:disabled { color: #a5adbd; background: #f1f2f7; }
QComboBox { padding-right: 25px; }
QComboBox::drop-down, QDateEdit::drop-down { width: 23px; border: none; }
QComboBox QAbstractItemView { background: white; border: 1px solid #e1e5ee;
    selection-background-color: #eeebfc; selection-color: #5948bf; padding: 4px; }
QCheckBox { spacing: 6px; }
QProgressBar { border: 0; border-radius: 4px; background: #e5e0f8; height: 7px; }
QProgressBar::chunk { background: #7060de; border-radius: 4px; }
QScrollArea { border: none; background: transparent; }
#TaskListContainer { background: transparent; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 2px; }
QScrollBar::handle:vertical { background: #d4d8e5; border-radius: 3px; min-height: 32px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QCalendarWidget { background: white; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: white; }
QCalendarWidget QToolButton { color: #344058; font-size: 13px; padding: 6px; }
QCalendarWidget QSpinBox { background: white; border: none; }
QCalendarWidget QAbstractItemView { background: white; color: #526077;
    selection-background-color: #7060de; selection-color: white; outline: none; border: 0; }
QMenu { background: white; border: 1px solid #e1e5ee; border-radius: 6px; padding: 6px; }
QMenu::item { padding: 8px 25px 8px 12px; border-radius: 4px; }
QMenu::item:selected { background: #eeebfc; }
QMenu::item:disabled { color: #b0b7c5; }
QMenu::separator { height: 1px; background: #edf0f5; margin: 4px; }
QDialog { background: #f9f9fc; }
QStatusBar { background: #f5f6fa; color: #9099aa; font-size: 11px; }
QToolTip { background: #27334a; color: white; border: none; padding: 7px; }
"""

_arrow_path = (Path(__file__).resolve().parents[1] / 'assets' / 'chevron-down.png').as_posix()
STYLE += f'QComboBox::down-arrow, QDateEdit::down-arrow {{ image: url("{_arrow_path}"); width: 10px; height: 10px; }}'


def as_qdate(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


def as_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def app_icon() -> QIcon:
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(ACCENT))
    painter.drawRoundedRect(QRectF(8, 8, 240, 240), 58, 58)
    painter.setBrush(QColor('#ffffff'))
    painter.drawRoundedRect(QRectF(60, 51, 137, 159), 15, 15)
    painter.setBrush(QColor('#b7acf7'))
    painter.drawRoundedRect(QRectF(93, 38, 70, 29), 9, 9)
    painter.setPen(QPen(QColor(ACCENT), 11, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(QPointF(86, 133), QPointF(111, 157))
    painter.drawLine(QPointF(111, 157), QPointF(167, 103))
    painter.end()
    return QIcon(pixmap)


def small_icon(kind: str, color: str = MUTED, size: int = 20) -> QIcon:
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 12, size / 12)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if kind == 'plus':
        p.drawLine(12, 5, 12, 19)
        p.drawLine(5, 12, 19, 12)
    elif kind == 'calendar':
        p.drawRoundedRect(QRectF(4, 5, 16, 16), 3, 3)
        p.drawLine(4, 10, 20, 10)
        p.drawLine(8, 3, 8, 7)
        p.drawLine(16, 3, 16, 7)
    elif kind == 'history':
        p.drawEllipse(QRectF(4, 4, 16, 16))
        p.drawLine(12, 7, 12, 12)
        p.drawLine(12, 12, 16, 14)
    elif kind == 'chart':
        p.drawLine(4, 3, 4, 21)
        p.drawLine(4, 21, 21, 21)
        p.drawLine(9, 17, 9, 12)
        p.drawLine(14, 17, 14, 6)
        p.drawLine(19, 17, 19, 9)
    elif kind == 'search':
        p.drawEllipse(QRectF(4, 3, 12, 12))
        p.drawLine(14, 14, 20, 20)
    elif kind == 'check':
        p.drawLine(5, 12, 10, 17)
        p.drawLine(10, 17, 20, 6)
    elif kind == 'circle':
        p.drawEllipse(QRectF(3, 3, 18, 18))
    elif kind == 'more':
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        for x in (5, 12, 19):
            p.drawEllipse(QPointF(x, 12), 1.6, 1.6)
    elif kind == 'download':
        p.drawLine(12, 3, 12, 15)
        p.drawLine(7, 10, 12, 15)
        p.drawLine(12, 15, 17, 10)
        p.drawLine(4, 16, 4, 21)
        p.drawLine(4, 21, 20, 21)
        p.drawLine(20, 21, 20, 16)
    p.end()
    return QIcon(pixmap)


def label(text='', name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text, name=None, icon=None):
    widget = QPushButton(text)
    if name:
        widget.setObjectName(name)
    if icon:
        widget.setIcon(icon)
        widget.setIconSize(QSize(18, 18))
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def format_rate(data):
    return f"{data['rate']:.0%}" if data['rate'] is not None else '—'


class MetricStrip(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName('Panel')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        self.values = []
        self.details = []
        for title, color in [('任务总数', '#27334a'), ('进行中', '#d9a14a'),
                             ('已完成', ACCENT), ('完成率', ACCENT)]:
            column = QVBoxLayout()
            column.setSpacing(5)
            column.addWidget(label(title, 'Muted'))
            value = label('0', 'MetricValue')
            value.setStyleSheet(f'color: {color};')
            column.addWidget(value)
            detail = label('', 'Muted')
            column.addWidget(detail)
            layout.addLayout(column, 1)
            self.values.append(value)
            self.details.append(detail)

    def update_data(self, data):
        for widget, value in zip(self.values, [data['total'], data['in_progress'], data['done'], format_rate(data)]):
            widget.setText(str(value))
        self.details[0].setText(f"待开始 {data['pending']} 项")
        self.details[1].setText('正在推进的任务')
        self.details[2].setText('已完成的任务')
        self.details[3].setText('已完成 / 全部任务' if data['total'] else '暂无任务')


class TaskDialog(QDialog):
    def __init__(self, parent=None, task: Task | None = None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle('编辑任务' if task else '新增任务')
        self.setMinimumWidth(490)
        self.resize(520, 510)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)
        root.addWidget(label(self.windowTitle(), 'SectionTitle'))
        form = QFormLayout()
        form.setVerticalSpacing(14)
        self.title_input = QLineEdit(task.title if task else '')
        self.title_input.setObjectName('taskTitleInput')
        self.title_input.setPlaceholderText('这项任务需要做什么？')
        self.title_input.setMaxLength(200)
        form.addRow('任务标题 *', self.title_input)
        self.date_input = QDateEdit()
        self.date_input.setObjectName('taskDateInput')
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat('yyyy-MM-dd')
        self.date_input.setDate(as_qdate(date.fromisoformat(task.task_date) if task else date.today()))
        form.addRow('计划日期', self.date_input)
        self.priority_input = QComboBox()
        for key in (3, 2, 1):
            self.priority_input.addItem(PRIORITY_LABELS[key], key)
        self.priority_input.setCurrentIndex(self.priority_input.findData(task.priority if task else 2))
        form.addRow('优先级', self.priority_input)
        self.status_input = QComboBox()
        for key, value in STATUS_LABELS.items():
            self.status_input.addItem(value, key)
        self.status_input.setCurrentIndex(self.status_input.findData(task.status if task else 'pending'))
        form.addRow('任务状态', self.status_input)
        self.notes_input = QPlainTextEdit(task.notes if task else '')
        self.notes_input.setPlaceholderText('补充步骤、安排或完成情况（可选）')
        self.notes_input.setMinimumHeight(140)
        form.addRow('备注', self.notes_input)
        root.addLayout(form)
        self.error_label = label('', wrap=True)
        self.error_label.setStyleSheet('color: #c25060;')
        self.error_label.hide()
        root.addWidget(self.error_label)
        actions = QDialogButtonBox()
        cancel = actions.addButton('取消', QDialogButtonBox.ButtonRole.RejectRole)
        save = actions.addButton('保存任务', QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName('Primary')
        save.setDefault(True)
        actions.rejected.connect(self.reject)
        actions.accepted.connect(self.validate_and_accept)
        root.addWidget(actions)
        self.title_input.setFocus()

    def fields(self):
        return {'task_date': as_date(self.date_input.date()), 'title': self.title_input.text(),
                'notes': self.notes_input.toPlainText(), 'priority': self.priority_input.currentData(),
                'status': self.status_input.currentData()}

    def validate_and_accept(self):
        if not self.title_input.text().strip():
            self.error_label.setText('请填写任务标题。')
            self.error_label.show()
            self.title_input.setFocus()
        elif len(self.notes_input.toPlainText()) > 20000:
            self.error_label.setText('备注最多 20,000 个字符，请缩短后保存。')
            self.error_label.show()
        else:
            self.accept()


class TaskCard(QFrame):
    status_requested = Signal(str, str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    copy_requested = Signal(str)

    def __init__(self, task: Task, history=False):
        super().__init__()
        self.task = task
        self.setObjectName('TaskCard')
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 17, 14, 17)
        layout.setSpacing(13)
        self.complete_button = QToolButton()
        self.complete_button.setObjectName('complete_' + task.id)
        self.complete_button.setIcon(small_icon('check' if task.status == 'done' else 'circle',
                                               ACCENT if task.status == 'done' else '#b8bfd0', 23))
        self.complete_button.setIconSize(QSize(23, 23))
        self.complete_button.setToolTip('恢复为待开始' if task.status == 'done' else '标记为已完成')
        self.complete_button.clicked.connect(lambda: self.status_requested.emit(
            task.id, 'pending' if task.status == 'done' else 'done'))
        layout.addWidget(self.complete_button, 0, Qt.AlignmentFlag.AlignTop)
        content = QVBoxLayout()
        content.setSpacing(7)
        title = label(task.title, wrap=True)
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setStyleSheet('font-size: 15px; font-weight: 600; color: ' +
                           ('#929bad' if task.status == 'done' else '#344058') + ';')
        content.addWidget(title)
        if task.notes.strip():
            preview = task.notes.replace('\n', '  ')
            note = label(preview[:160] + ('…' if len(preview) > 160 else ''), 'Muted', wrap=True)
            note.setTextFormat(Qt.TextFormat.PlainText)
            content.addWidget(note)
        metadata = QHBoxLayout()
        metadata.setSpacing(10)
        priority = label(PRIORITY_LABELS[task.priority] + '优先级')
        foreground, background = {1: ('#6e8a83', '#eef5f2'), 2: ('#798699', '#f0f2f7'),
                                  3: ('#c67751', '#fff1e8')}[task.priority]
        priority.setStyleSheet(f'color: {foreground}; background: {background}; border-radius: 4px; padding: 3px 7px; font-size: 11px;')
        metadata.addWidget(priority)
        if history:
            metadata.addWidget(label(task.task_date, 'Muted'))
        if task.completed_at:
            metadata.addWidget(label('完成于 ' + task.completed_at[:16].replace('T', ' '), 'Muted'))
        metadata.addStretch()
        content.addLayout(metadata)
        layout.addLayout(content, 1)
        actions = QVBoxLayout()
        actions.setSpacing(8)
        self.status_combo = QComboBox()
        self.status_combo.setObjectName('status_' + task.id)
        self.status_combo.setMinimumWidth(104)
        for key, text in STATUS_LABELS.items():
            self.status_combo.addItem(text, key)
        self.status_combo.setCurrentIndex(self.status_combo.findData(task.status))
        self.status_combo.currentIndexChanged.connect(lambda: self.status_requested.emit(task.id, self.status_combo.currentData()))
        actions.addWidget(self.status_combo)
        more = QToolButton()
        more.setIcon(small_icon('more'))
        more.setToolTip('编辑、复制或删除任务')
        more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(more)
        menu.addAction('编辑任务').triggered.connect(lambda: self.edit_requested.emit(task.id))
        copy = menu.addAction('复制到今天')
        copy.setEnabled(task.status != 'done' and task.task_date != date.today().isoformat())
        copy.triggered.connect(lambda: self.copy_requested.emit(task.id))
        menu.addSeparator()
        menu.addAction('删除任务').triggered.connect(lambda: self.delete_requested.emit(task.id))
        more.setMenu(menu)
        actions.addWidget(more, 0, Qt.AlignmentFlag.AlignRight)
        actions.addStretch()
        layout.addLayout(actions)


class TaskPage(QWidget):
    filters_changed = Signal()

    def __init__(self, history=False):
        super().__init__()
        self.history = history
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(20)
        self.metrics = MetricStrip()
        root.addWidget(self.metrics)
        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.search = QLineEdit()
        self.search.setObjectName('historySearch' if history else 'dailySearch')
        self.search.setPlaceholderText('搜索任务标题或备注…')
        self.search.addAction(small_icon('search'), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setClearButtonEnabled(True)
        filters.addWidget(self.search, 1)
        self.status_filter = QComboBox()
        self.status_filter.addItem('全部状态', None)
        for key, text in STATUS_LABELS.items():
            self.status_filter.addItem(text, key)
        self.status_filter.setMinimumWidth(115)
        filters.addWidget(self.status_filter)
        self.export_button = button('导出 CSV', icon=small_icon('download'))
        filters.addWidget(self.export_button)
        root.addLayout(filters)
        if history:
            dates = QHBoxLayout()
            self.all_dates = QCheckBox('全部日期')
            self.all_dates.setChecked(True)
            dates.addWidget(self.all_dates)
            dates.addSpacing(6)
            self.start_date, self.end_date = QDateEdit(), QDateEdit()
            for picker in (self.start_date, self.end_date):
                picker.setCalendarPopup(True)
                picker.setDisplayFormat('yyyy-MM-dd')
                picker.setEnabled(False)
                picker.setFixedWidth(135)
                picker.dateChanged.connect(lambda *_: self.filters_changed.emit())
            self.start_date.setDate(as_qdate(date.today() - timedelta(days=30)))
            self.end_date.setDate(QDate.currentDate())
            dates.addWidget(label('从', 'Muted'))
            dates.addWidget(self.start_date)
            dates.addWidget(label('到', 'Muted'))
            dates.addWidget(self.end_date)
            dates.addStretch()
            root.addLayout(dates)
            self.all_dates.toggled.connect(self._toggle_dates)
        self.count_label = label('', 'Muted')
        root.addWidget(self.count_label)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName('TaskListContainer')
        self.cards_layout = QVBoxLayout(content)
        self.cards_layout.setContentsMargins(0, 0, 5, 0)
        self.cards_layout.setSpacing(11)
        self.cards_layout.addStretch()
        self.scroll.setWidget(content)
        root.addWidget(self.scroll, 1)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(180)
        self.debounce.timeout.connect(self.filters_changed.emit)
        self.search.textChanged.connect(lambda: self.debounce.start())
        self.status_filter.currentIndexChanged.connect(lambda *_: self.filters_changed.emit())
        self.displayed_tasks = []

    def _toggle_dates(self, checked):
        self.start_date.setEnabled(not checked)
        self.end_date.setEnabled(not checked)
        self.filters_changed.emit()

    def filters(self, selected: date):
        result = {'keyword': self.search.text(), 'status': self.status_filter.currentData()}
        if not self.history:
            result.update(start=selected, end=selected)
        elif not self.all_dates.isChecked():
            result.update(start=as_date(self.start_date.date()), end=as_date(self.end_date.date()))
        return result

    def show_tasks(self, tasks, owner):
        position = self.scroll.verticalScrollBar().value()
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.displayed_tasks = tasks
        self.count_label.setText(f'共 {len(tasks)} 项任务' if tasks else '暂无符合条件的任务')
        for task in tasks:
            card = TaskCard(task, self.history)
            card.status_requested.connect(owner.change_status)
            card.edit_requested.connect(owner.edit_task)
            card.copy_requested.connect(owner.copy_task)
            card.delete_requested.connect(owner.delete_task)
            self.cards_layout.addWidget(card)
        if not tasks:
            empty = QFrame()
            empty.setMinimumHeight(220)
            empty_layout = QVBoxLayout(empty)
            empty_layout.addStretch()
            graphic = label()
            graphic.setPixmap(small_icon('calendar', '#c7c1e9', 52).pixmap(52, 52))
            empty_layout.addWidget(graphic, 0, Qt.AlignmentFlag.AlignCenter)
            text = label('暂无任务' if not self.search.text() and not self.status_filter.currentData() else '没有找到匹配的任务', 'SectionTitle')
            empty_layout.addWidget(text, 0, Qt.AlignmentFlag.AlignCenter)
            tip = label('点击右上角「新增任务」，开始安排今天。' if not self.history else '调整筛选条件，或记录你的第一项任务。', 'Muted', wrap=True)
            empty_layout.addWidget(tip, 0, Qt.AlignmentFlag.AlignCenter)
            empty_layout.addStretch()
            self.cards_layout.addWidget(empty)
        self.cards_layout.addStretch()
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(position))


class DailyChart(QWidget):
    def __init__(self):
        super().__init__()
        self.days = []
        self.bar_regions = []
        self.setMinimumHeight(200)
        self.setMouseTracking(True)

    def set_days(self, days):
        self.days = days
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        plot = QRectF(38, 18, max(1, width - 58), max(1, height - 64))
        maximum = max([day['total'] for day in self.days] + [1])
        self.bar_regions = []
        p.setFont(QFont('Microsoft YaHei UI', 9))
        for step in range(5):
            y = plot.bottom() - plot.height() * step / 4
            p.setPen(QPen(QColor('#eef0f6'), 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor('#97a0b1'))
            value = maximum * step / 4
            if float(value).is_integer():
                p.drawText(QRectF(0, y - 9, 28, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(int(value)))
        if self.days:
            step_width = plot.width() / len(self.days)
            bar_width = min(38, step_width * 0.58)
            interval = max(1, len(self.days) // 9)
            for index, day in enumerate(self.days):
                x = plot.left() + step_width * (index + .5)
                y = plot.bottom()
                for status, color in [('done', ACCENT), ('in_progress', '#f0b45c'), ('pending', '#e0e4ef')]:
                    segment = plot.height() * day[status] / maximum
                    if segment:
                        p.setPen(Qt.PenStyle.NoPen)
                        p.setBrush(QColor(color))
                        p.drawRoundedRect(QRectF(x - bar_width / 2, y - segment, bar_width, segment), 3, 3)
                        y -= segment
                self.bar_regions.append((QRectF(x - step_width / 2, plot.top(), step_width, plot.height()), day))
                if index % interval == 0 or index == len(self.days) - 1:
                    p.setPen(QColor('#8b96a8'))
                    caption = day['date'][5:] if len(self.days) <= 7 else day['date'][8:]
                    p.drawText(QRectF(x - 26, plot.bottom() + 10, 52, 22), Qt.AlignmentFlag.AlignCenter, caption)
        if not any(day['total'] for day in self.days):
            p.setPen(QColor('#99a2b3'))
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, '这个时间段暂无任务')
        p.end()

    def mouseMoveEvent(self, event):
        for region, day in self.bar_regions:
            if region.contains(event.position()):
                QToolTip.showText(event.globalPosition().toPoint(),
                    f"{day['date']}\n共 {day['total']} 项 · 已完成 {day['done']} 项\n"
                    f"进行中 {day['in_progress']} 项 · 待开始 {day['pending']} 项\n完成率 {format_rate(day)}", self)
                return
        QToolTip.hideText()


class StatsPage(QWidget):
    period_changed = Signal()

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(20)
        controls = QHBoxLayout()
        self.range_label = label('', 'Muted')
        controls.addWidget(self.range_label)
        controls.addStretch()
        self.period = QComboBox()
        for text, value in [('当日', 'today'), ('近七天', 'week'), ('本月', 'month')]:
            self.period.addItem(text, value)
        self.period.setCurrentIndex(1)
        self.period.setMinimumWidth(120)
        controls.addWidget(self.period)
        root.addLayout(controls)
        self.metrics = MetricStrip()
        root.addWidget(self.metrics)
        panel = QFrame()
        panel.setObjectName('Panel')
        contents = QVBoxLayout(panel)
        contents.setContentsMargins(22, 22, 22, 18)
        title = QHBoxLayout()
        title.addWidget(label('每日任务完成情况', 'SectionTitle'))
        title.addStretch()
        for name, color in [('已完成', ACCENT), ('进行中', '#f0b45c'), ('待开始', '#e0e4ef')]:
            chip = label('● ' + name)
            chip.setStyleSheet(f'color: {color}; font-size: 12px;')
            title.addWidget(chip)
        contents.addLayout(title)
        self.chart = DailyChart()
        contents.addWidget(self.chart, 1)
        contents.addWidget(label('柱高表示任务数量；将鼠标移到柱上查看当天详情。', 'Muted', wrap=True))
        root.addWidget(panel, 1)
        root.addWidget(label('完成率按这个时间段的已完成任务总数计算；进行中的任务不计入已完成。', 'Muted', wrap=True))
        self.period.currentIndexChanged.connect(lambda *_: self.period_changed.emit())

    def refresh(self, store):
        today = date.today()
        mode = self.period.currentData()
        if mode == 'today':
            start, end = today, today
        elif mode == 'week':
            start, end = today - timedelta(days=6), today
        else:
            start = today.replace(day=1)
            end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        result = store.report(start, end)
        self.range_label.setText(f'{start:%Y-%m-%d} 至 {end:%Y-%m-%d}')
        self.metrics.update_data(result)
        self.chart.set_days(result['days'])


class MainWindow(QMainWindow):
    def __init__(self, store: TaskStore):
        super().__init__()
        self.store = store
        self.selected_date = date.today()
        self._last_today = date.today()
        self.setWindowTitle('每日任务')
        self.setWindowIcon(app_icon())
        self.resize(1180, 810)
        self.setMinimumSize(920, 660)
        self.setStyleSheet(STYLE)
        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.setCentralWidget(shell)
        self.sidebar = QFrame()
        self.sidebar.setObjectName('Sidebar')
        self.sidebar.setMinimumHeight(740)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(20, 30, 20, 16)
        side.setSpacing(9)
        brand_row = QHBoxLayout()
        logo = label()
        logo.setPixmap(app_icon().pixmap(37, 37))
        brand_row.addWidget(logo)
        brand_row.addWidget(label('每日任务', 'Brand'))
        brand_row.addStretch()
        side.addLayout(brand_row)
        side.addWidget(label('记录计划 · 查看进展', 'Muted'))
        side.addSpacing(24)
        self.nav_buttons = []
        for index, (text, icon) in enumerate([('今天', 'calendar'), ('历史记录', 'history'), ('完成统计', 'chart')]):
            nav = button(text, 'Nav', small_icon(icon, '#8d83c3'))
            nav.setCheckable(True)
            nav.clicked.connect(lambda checked=False, idx=index: self.navigate(idx))
            side.addWidget(nav)
            self.nav_buttons.append(nav)
        side.addSpacing(22)
        side.addWidget(label('按日期查看', 'Muted'))
        self.calendar = QCalendarWidget()
        self.calendar.setObjectName('dayCalendar')
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.SingleLetterDayNames)
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setGridVisible(False)
        self.calendar.setFixedHeight(230)
        self.calendar.setMinimumWidth(0)
        self.calendar.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        # Make weekend text quiet rather than the native calendar's bright red.
        from PySide6.QtGui import QTextCharFormat
        weekend = QTextCharFormat()
        weekend.setForeground(QColor('#7d879a'))
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, weekend)
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, weekend)
        self.calendar.selectionChanged.connect(self.date_selected)
        side.addWidget(self.calendar)
        side.addSpacing(10)
        today_panel = QFrame()
        today_panel.setObjectName('TodayPanel')
        today_layout = QVBoxLayout(today_panel)
        today_layout.setContentsMargins(16, 15, 16, 15)
        today_layout.addWidget(label('今日完成', 'Muted'))
        self.today_count = label('', 'SectionTitle')
        today_layout.addWidget(self.today_count)
        self.today_progress = QProgressBar()
        self.today_progress.setTextVisible(False)
        self.today_progress.setRange(0, 100)
        self.today_progress.setFixedHeight(7)
        today_layout.addWidget(self.today_progress)
        self.today_hint = label('', 'Muted')
        today_layout.addWidget(self.today_hint)
        side.addWidget(today_panel)
        side.addStretch()
        settings = button('数据与备份', icon=small_icon('more'))
        settings_menu = QMenu(settings)
        settings_menu.addAction('备份全部数据…').triggered.connect(self.backup_data)
        settings_menu.addAction('从备份恢复…').triggered.connect(self.restore_data)
        settings_menu.addSeparator()
        settings_menu.addAction('打开数据文件夹').triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.data_dir))))
        settings_menu.addAction('关于每日任务').triggered.connect(self.about)
        settings.setMenu(settings_menu)
        side.addWidget(settings)
        side.addWidget(label('离线使用 · 自动保存', 'Muted'), 0, Qt.AlignmentFlag.AlignCenter)
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setFixedWidth(258)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setWidget(self.sidebar)
        shell_layout.addWidget(sidebar_scroll)
        workspace = QWidget()
        workspace.setObjectName('Workspace')
        main = QVBoxLayout(workspace)
        main.setContentsMargins(30, 31, 30, 14)
        main.setSpacing(23)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(7)
        self.heading = label('', 'PageTitle')
        self.subtitle = label('', 'Muted')
        titles.addWidget(self.heading)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)
        self.add_button = button('新增任务', 'Primary', small_icon('plus', '#ffffff'))
        self.add_button.setObjectName('Primary')
        self.add_button.setToolTip('新增任务（Ctrl+N）')
        self.add_button.clicked.connect(self.add_task)
        header.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignVCenter)
        main.addLayout(header)
        self.pages = QStackedWidget()
        self.daily = TaskPage()
        self.history = TaskPage(history=True)
        self.stats = StatsPage()
        for page in (self.daily, self.history, self.stats):
            self.pages.addWidget(page)
        main.addWidget(self.pages, 1)
        shell_layout.addWidget(workspace, 1)
        self.daily.filters_changed.connect(self.refresh)
        self.history.filters_changed.connect(self.refresh)
        self.stats.period_changed.connect(self.refresh)
        self.daily.export_button.clicked.connect(self.export_current)
        self.history.export_button.clicked.connect(self.export_current)
        QShortcut('Ctrl+N', self, activated=self.add_task)
        QShortcut('Ctrl+F', self, activated=self.focus_search)
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().showMessage('任务会自动保存到本机。')
        self.midnight_timer = QTimer(self)
        self.midnight_timer.setInterval(30000)
        self.midnight_timer.timeout.connect(self.check_new_day)
        self.midnight_timer.start()
        self.navigate(0)

    def check_new_day(self):
        today = date.today()
        if today != self._last_today:
            previous = self._last_today
            self._last_today = today
            if self.pages.currentIndex() == 0 and self.selected_date == previous:
                self.calendar.setSelectedDate(QDate.currentDate())
            self.refresh()

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        if index == 0:
            self.selected_date = date.today()
            self.calendar.blockSignals(True)
            self.calendar.setSelectedDate(QDate.currentDate())
            self.calendar.blockSignals(False)
        self.refresh()

    def date_selected(self):
        self.selected_date = as_date(self.calendar.selectedDate())
        self.pages.setCurrentIndex(0)
        self.refresh()

    def refresh(self):
        try:
            index = self.pages.currentIndex()
            for i, nav in enumerate(self.nav_buttons):
                nav.setChecked(i == index)
            if index == 0:
                selected = self.selected_date
                self.heading.setText('今天的任务' if selected == date.today() else '每日任务')
                self.subtitle.setText(f'{selected.year}年{selected.month}月{selected.day}日 · 星期{WEEKDAYS[selected.weekday()]}')
                base = self.store.list_tasks(start=selected, end=selected)
                self.daily.metrics.update_data(summary(base))
                self.daily.show_tasks(self.store.list_tasks(**self.daily.filters(selected)), self)
            elif index == 1:
                self.heading.setText('历史记录')
                self.subtitle.setText('查看过去的安排，按日期、状态或关键词筛选。')
                try:
                    tasks = self.store.list_tasks(**self.history.filters(self.selected_date))
                    self.history.show_tasks(tasks, self)
                    self.history.metrics.update_data(summary(tasks))
                except ValueError as error:
                    self.history.show_tasks([], self)
                    self.history.metrics.update_data(summary([]))
                    self.history.count_label.setText(str(error))
            else:
                self.heading.setText('完成统计')
                self.subtitle.setText('回顾任务数量与完成情况。')
                self.stats.refresh(self.store)
            today = summary(self.store.list_tasks(start=date.today(), end=date.today()))
            self.today_count.setText(f"{today['done']} / {today['total']} 项任务")
            self.today_progress.setValue(round((today['rate'] or 0) * 100))
            self.today_hint.setText('暂无任务' if not today['total'] else f"完成率 {format_rate(today)}")
        except Exception as error:
            self.report_error('读取任务失败', error)

    def report_error(self, title, error):
        logging.exception(title)
        QMessageBox.critical(self, title, f'{title}。\n{error}\n\n现有记录不会被自动清空，请重试或检查数据文件夹。')

    def _mutate(self, operation, message):
        try:
            result = operation()
        except Exception as error:
            self.report_error('保存失败', error)
            self.refresh()
            return None
        self.refresh()
        self.statusBar().showMessage(message, 6500)
        return result

    def add_task(self):
        dialog = TaskDialog(self)
        while dialog.exec() == QDialog.DialogCode.Accepted:
            result = self._mutate(lambda: self.store.add(**dialog.fields()), '任务已添加并自动保存。')
            if result is not None:
                self.selected_date = date.fromisoformat(result.task_date)
                self.calendar.setSelectedDate(as_qdate(self.selected_date))
                self.pages.setCurrentIndex(0)
                self.refresh()
                return

    def edit_task(self, task_id):
        try:
            task = self.store.get(task_id)
        except Exception as error:
            self.report_error('读取任务失败', error)
            return
        dialog = TaskDialog(self, task)
        while dialog.exec() == QDialog.DialogCode.Accepted:
            result = self._mutate(lambda: self.store.update(task_id, **dialog.fields()), '任务修改已自动保存。')
            if result is not None:
                if self.pages.currentIndex() == 0:
                    self.selected_date = date.fromisoformat(result.task_date)
                    self.calendar.setSelectedDate(as_qdate(self.selected_date))
                    self.refresh()
                return

    def change_status(self, task_id, status):
        self._mutate(lambda: self.store.set_status(task_id, status), '任务状态已自动保存。')

    def copy_task(self, task_id):
        self._mutate(lambda: self.store.copy_to_today(task_id), '已复制到今天，新任务为待开始；原记录保持不变。')

    def delete_task(self, task_id):
        try:
            task = self.store.get(task_id)
        except Exception as error:
            self.report_error('读取任务失败', error)
            return
        answer = QMessageBox.question(self, '删除任务', f'确定删除「{task.title[:65]}」吗？\n删除后将从任务列表和统计中移除。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self._mutate(lambda: self.store.delete(task_id), '任务已删除。')

    def export_current(self):
        page = self.pages.currentWidget()
        if page not in (self.daily, self.history):
            return
        # Read filters at click time, even if the search debounce has not fired yet.
        try:
            tasks = self.store.list_tasks(**page.filters(self.selected_date))
        except Exception as error:
            self.report_error('导出失败', error)
            return
        if not tasks:
            QMessageBox.information(self, '导出任务', '当前筛选结果暂无任务，请调整条件后再导出。')
            return
        path, _ = QFileDialog.getSaveFileName(self, '导出当前任务', '每日任务-' + date.today().isoformat() + '.csv', 'CSV 文件 (*.csv)')
        if path:
            if not path.lower().endswith('.csv'):
                path += '.csv'
            try:
                self.store.export_csv(path, tasks)
                self.statusBar().showMessage(f'已导出 {len(tasks)} 项任务，可用 Excel 打开。', 6500)
            except Exception as error:
                self.report_error('导出失败', error)

    def backup_data(self):
        path, _ = QFileDialog.getSaveFileName(self, '备份全部数据', '每日任务备份-' + date.today().isoformat() + '.db', '数据库备份 (*.db)')
        if path:
            if not path.lower().endswith('.db'):
                path += '.db'
            try:
                self.store.backup(path)
                self.statusBar().showMessage('全部任务已备份。', 6500)
            except Exception as error:
                self.report_error('备份失败', error)

    def restore_data(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择每日任务备份', '', '数据库备份 (*.db)')
        if not path:
            return
        answer = QMessageBox.question(self, '恢复备份',
            '恢复会用备份中的记录替换当前全部任务。\n恢复前会自动备份现有数据，是否继续？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            try:
                safety = self.store.restore(path)
                self.refresh()
                QMessageBox.information(self, '恢复成功', f'任务记录已恢复。\n恢复前的数据保存在：\n{safety}')
            except Exception as error:
                self.report_error('恢复失败', error)

    def focus_search(self):
        page = self.pages.currentWidget()
        if page in (self.daily, self.history):
            page.search.setFocus()

    def about(self):
        QMessageBox.information(self, '关于每日任务',
            f'每日任务 1.0.0\n\n个人离线任务管理工具\n自动保存 · 三种状态 · 历史统计\n\n'
            f'数据位置：\n{self.store.data_dir}\n\n快捷键：Ctrl+N 新增任务，Ctrl+F 搜索。')

    def closeEvent(self, event):
        self.midnight_timer.stop()
        super().closeEvent(event)
