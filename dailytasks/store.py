"""Transactional persistence, reporting and safe backup/restore; no UI dependency."""

from __future__ import annotations

import csv
import os
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

STATUS_LABELS = {"pending": "待开始", "in_progress": "进行中", "done": "已完成"}
PRIORITY_LABELS = {1: "低", 2: "中", 3: "高"}
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Task:
    id: str
    task_date: str
    title: str
    notes: str
    priority: int
    status: str
    created_at: str
    updated_at: str
    completed_at: str | None


def canonical_date(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("日期格式应为 YYYY-MM-DD。") from None
    if parsed.isoformat() != value:
        raise ValueError("日期格式应为 YYYY-MM-DD。")
    return value


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def validated_fields(task_date, title, notes, priority, status):
    task_date = canonical_date(task_date)
    title = title.strip()
    if not title:
        raise ValueError("请填写任务标题。")
    if len(title) > 200:
        raise ValueError("任务标题最多 200 个字符。")
    if len(notes) > 20000:
        raise ValueError("备注最多 20,000 个字符。")
    if priority not in PRIORITY_LABELS or status not in STATUS_LABELS:
        raise ValueError("任务优先级或状态无效。")
    return task_date, title, notes, int(priority), status


def summary(tasks: Iterable[Task]) -> dict:
    counts = {key: 0 for key in STATUS_LABELS}
    for task in tasks:
        counts[task.status] += 1
    total = sum(counts.values())
    return {**counts, "total": total, "rate": counts["done"] / total if total else None}


class TaskStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "tasks.db"
        self.connection: sqlite3.Connection | None = None
        self._connect()
        try:
            self._initialize()
        except Exception:
            self.close()
            raise

    def _connect(self):
        self.connection = sqlite3.connect(self.path, timeout=10)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout=10000")

    def _initialize(self):
        conn = self.connection
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        existing = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not existing and version == 0:
            with conn:
                conn.execute("""CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    task_date TEXT NOT NULL,
                    title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 200),
                    notes TEXT NOT NULL DEFAULT '',
                    priority INTEGER NOT NULL CHECK(priority IN (1,2,3)),
                    status TEXT NOT NULL CHECK(status IN ('pending','in_progress','done')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    CHECK((status='done' AND completed_at IS NOT NULL) OR
                          (status!='done' AND completed_at IS NULL))
                )""")
                conn.execute("CREATE INDEX idx_tasks_date ON tasks(task_date)")
                conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self._validate_connection(conn)

    @staticmethod
    def _validate_connection(conn):
        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("数据库完整性检查失败，请使用有效备份恢复。")
        if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise ValueError("这不是当前版本的每日任务数据库。")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        if columns != set(Task.__dataclass_fields__):
            raise ValueError("备份文件的任务结构不正确。")
        for row in conn.execute("SELECT * FROM tasks"):
            item = dict(row) if isinstance(row, sqlite3.Row) else dict(zip(
                [col[0] for col in conn.execute('SELECT * FROM tasks LIMIT 0').description], row
            ))
            validated_fields(item['task_date'], item['title'], item['notes'], item['priority'], item['status'])
            for field in ('created_at', 'updated_at'):
                datetime.fromisoformat(item[field])
            if not item['id'] or (item['status'] == 'done') != (item['completed_at'] is not None):
                raise ValueError("备份文件含有无效任务记录。")
            if item['completed_at'] is not None:
                datetime.fromisoformat(item['completed_at'])

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def get(self, task_id: str) -> Task:
        row = self.connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("任务不存在，可能已被删除。")
        return Task(**dict(row))

    def add(self, task_date: str | date, title: str, notes: str = "", priority: int = 2,
            status: str = "pending") -> Task:
        fields = validated_fields(task_date, title, notes, priority, status)
        stamp = now()
        task = Task(uuid.uuid4().hex, *fields, stamp, stamp, stamp if status == "done" else None)
        with self.connection:
            self.connection.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)", tuple(task.__dict__.values()))
        return task

    def update(self, task_id: str, *, task_date: str | date, title: str, notes: str,
               priority: int, status: str) -> Task:
        old = self.get(task_id)
        fields = validated_fields(task_date, title, notes, priority, status)
        stamp = now()
        completed = (old.completed_at or stamp) if status == 'done' else None
        with self.connection:
            self.connection.execute("""UPDATE tasks SET task_date=?, title=?, notes=?, priority=?,
                status=?, updated_at=?, completed_at=? WHERE id=?""", (*fields, stamp, completed, task_id))
        return self.get(task_id)

    def set_status(self, task_id: str, status: str) -> Task:
        task = self.get(task_id)
        return self.update(task_id, task_date=task.task_date, title=task.title, notes=task.notes,
                           priority=task.priority, status=status)

    def delete(self, task_id: str):
        self.get(task_id)
        with self.connection:
            self.connection.execute("DELETE FROM tasks WHERE id=?", (task_id,))

    def copy_to_today(self, task_id: str, today: date | None = None) -> Task:
        original = self.get(task_id)
        return self.add(today or date.today(), original.title, original.notes, original.priority)

    def list_tasks(self, *, start: str | date | None = None, end: str | date | None = None,
                   keyword: str = "", status: str | None = None) -> list[Task]:
        clauses, args = [], []
        if start is not None:
            clauses.append("task_date>=?")
            args.append(canonical_date(start))
        if end is not None:
            clauses.append("task_date<=?")
            args.append(canonical_date(end))
        if start is not None and end is not None and canonical_date(start) > canonical_date(end):
            raise ValueError("开始日期不能晚于结束日期。")
        if keyword.strip():
            # Escape LIKE metacharacters so a user's '%' or '_' is a literal search.
            needle = keyword.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            clauses.append("(title LIKE ? ESCAPE '\\' OR notes LIKE ? ESCAPE '\\')")
            args.extend([f"%{needle}%"] * 2)
        if status:
            if status not in STATUS_LABELS:
                raise ValueError("状态筛选无效。")
            clauses.append("status=?")
            args.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = "SELECT * FROM tasks" + where + " ORDER BY task_date DESC, (status='done'), priority DESC, created_at, id"
        return [Task(**dict(row)) for row in self.connection.execute(sql, args)]

    def report(self, start: date, end: date) -> dict:
        tasks = self.list_tasks(start=start, end=end)
        by_day = {}
        for task in tasks:
            by_day.setdefault(task.task_date, []).append(task)
        days = []
        current = start
        while current <= end:
            days.append({"date": current.isoformat(), **summary(by_day.get(current.isoformat(), []))})
            current += timedelta(days=1)
        return {**summary(tasks), "days": days}

    @staticmethod
    def export_csv(destination: str | Path, tasks: Iterable[Task]):
        # Prefix spreadsheet formulas while preserving ordinary Chinese and multiline text.
        def cell(text):
            return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text

        with Path(destination).open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['日期', '任务标题', '备注', '优先级', '状态', '创建时间', '完成时间'])
            for task in tasks:
                writer.writerow([task.task_date, cell(task.title), cell(task.notes),
                                 PRIORITY_LABELS[task.priority], STATUS_LABELS[task.status],
                                 task.created_at, task.completed_at or ''])

    def backup(self, destination: str | Path) -> Path:
        destination = Path(destination).resolve()
        if destination == self.path:
            raise ValueError("备份文件不能覆盖正在使用的数据库。")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with closing(sqlite3.connect(temp)) as target:
                self.connection.backup(target)
            os.replace(temp, destination)
        finally:
            if temp.exists():
                temp.unlink()
        return destination

    def restore(self, source: str | Path) -> Path:
        source = Path(source).resolve()
        if source == self.path:
            raise ValueError("请选择备份文件，而不是当前正在使用的数据库。")
        if not source.is_file():
            raise ValueError("备份文件不存在。")
        uri = source.as_uri() + '?mode=ro'
        temp = self.data_dir / ('restore-' + uuid.uuid4().hex + '.tmp')
        try:
            with closing(sqlite3.connect(uri, uri=True)) as incoming:
                incoming.row_factory = sqlite3.Row
                self._validate_connection(incoming)
                with closing(sqlite3.connect(temp)) as staged:
                    incoming.backup(staged)
            safety = self.backup(self.data_dir / 'backups' / (
                '恢复前备份-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.db'))
            self.close()
            try:
                os.replace(temp, self.path)
            finally:
                self._connect()
            return safety
        finally:
            if temp.exists():
                temp.unlink()
