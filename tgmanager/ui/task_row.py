"""Строка активной задачи (тот же формат списка, что и контейнеры)."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .style import GREEN, RED, TEXT_SEC, YELLOW

_ACTION_LABELS = {
    "channels": "каналы", "groups": "группы", "private": "личные",
    "bots": "боты", "saved": "избранное", "contacts": "контакты", "photos": "фото",
}


class TaskRow(QFrame):
    stop = pyqtSignal(str)
    remove = pyqtSignal(str)
    show_log = pyqtSignal(str)

    def __init__(self, task, parent: QWidget | None = None):
        super().__init__(parent)
        self.task = task
        self.setObjectName("Row")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(66)
        self._build()
        self.update_view()

    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(10)

        self.bar = QFrame()
        self.bar.setObjectName("AccentBar")
        self.bar.setFixedSize(3, 42)
        self.bar.setStyleSheet(f"background: {self.task.account.color}; border-radius: 2px;")
        root.addWidget(self.bar)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(3)
        self.name_label = QLabel(self.task.account.name)
        self.name_label.setObjectName("RowName")
        self.sub_label = QLabel()
        self.sub_label.setObjectName("RowMeta")
        info.addWidget(self.name_label)
        info.addWidget(self.sub_label)
        info_w = QWidget()
        info_w.setLayout(info)
        info_w.setMinimumWidth(240)
        root.addWidget(info_w, 1)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(150)
        self.progress.setTextVisible(False)  # текст выносим в отдельную подпись
        root.addWidget(self.progress)

        self.count_label = QLabel("")
        self.count_label.setObjectName("RowMeta")
        self.count_label.setFixedWidth(110)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self.count_label)

        self.pill = QLabel("● Идёт")
        self.pill.setObjectName("PillRunning")
        self.pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.pill)

        self.log_btn = QPushButton("Журнал")
        self.log_btn.setObjectName("Ghost")
        self.log_btn.setFixedWidth(84)
        self.log_btn.clicked.connect(lambda: self.show_log.emit(self.task.id))
        root.addWidget(self.log_btn)

        self.action_btn = QPushButton("Стоп")
        self.action_btn.setObjectName("Stop")
        self.action_btn.setFixedWidth(84)
        self.action_btn.clicked.connect(self._on_action)
        root.addWidget(self.action_btn)

    def _on_action(self) -> None:
        if self.task.state == "running":
            self.stop.emit(self.task.id)
        else:
            self.remove.emit(self.task.id)

    def update_view(self) -> None:
        t = self.task
        acts = ", ".join(_ACTION_LABELS.get(a, a) for a in t.actions)
        cur = t.current or acts
        self.sub_label.setText(f"{acts}  ·  {cur}" if t.current else acts)

        # прогресс
        if t.state == "running" and t.total <= 0:
            self.progress.setRange(0, 0)
            self.count_label.setText("…")
        else:
            self.progress.setRange(0, max(1, t.total))
            self.progress.setValue(t.done if t.total else (1 if t.finished else 0))
            if t.total:
                pct = int(t.done * 100 / t.total)
                self.count_label.setText(f"{t.done}/{t.total} · {pct}%")
            else:
                self.count_label.setText("")

        # статус
        state_map = {
            "running": ("● Идёт", "PillRunning", TEXT_SEC),
            "done": ("✓ Готово", "PillRunning", GREEN),
            "error": ("✗ Ошибка", "PillStopped", RED),
            "stopped": ("■ Остановлено", "PillStopped", YELLOW),
        }
        text, obj, _ = state_map.get(t.state, ("—", "PillStopped", TEXT_SEC))
        self.pill.setText(text)
        self.pill.setObjectName(obj)
        self.pill.style().unpolish(self.pill)
        self.pill.style().polish(self.pill)

        if t.state == "running":
            self.action_btn.setText("Стоп")
            self.action_btn.setObjectName("Stop")
        else:
            self.action_btn.setText("Убрать")
            self.action_btn.setObjectName("Ghost")
        self.action_btn.style().unpolish(self.action_btn)
        self.action_btn.style().polish(self.action_btn)


class TaskLogDialog(QDialog):
    def __init__(self, parent, task):
        super().__init__(parent)
        self.setWindowTitle(f"Журнал — {task.account.name}")
        self.setMinimumSize(560, 420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 14)
        lay.setSpacing(10)
        title = QLabel(f"Журнал задачи — «{task.account.name}»")
        title.setObjectName("DialogTitle")
        lay.addWidget(title)
        self.view = QPlainTextEdit()
        self.view.setObjectName("Log")
        self.view.setReadOnly(True)
        self.view.setPlainText("\n".join(task.log))
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())
        lay.addWidget(self.view, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton("Закрыть")
        close.setObjectName("Ghost")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        lay.addLayout(row)
