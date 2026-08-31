"""Диалог создания/редактирования аккаунта."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..models import (
    CARD_COLORS,
    PROXY_HTTP,
    PROXY_NONE,
    PROXY_SOCKS5,
    Account,
    Proxy,
    parse_proxy_line,
)


class AccountDialog(QDialog):
    def __init__(self, parent=None, account: Account | None = None):
        super().__init__(parent)
        self.editing = account is not None
        self.account = account or Account(name="")
        self.setWindowTitle("Изменить аккаунт" if self.editing else "Новый аккаунт")
        self.setMinimumWidth(420)
        self._build()
        self._load()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 18)
        root.setSpacing(16)

        title = QLabel("Изменить аккаунт" if self.editing else "Новый аккаунт")
        title.setObjectName("AppTitle")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Основной, Рабочий, Ваня…")
        form.addRow(self._lbl("Название"), self.name_edit)

        # Цвет карточки
        self.color_combo = QComboBox()
        for c in CARD_COLORS:
            self.color_combo.addItem(c)
        self.color_combo.currentIndexChanged.connect(self._paint_color)
        form.addRow(self._lbl("Цвет карточки"), self.color_combo)

        # Тип прокси
        self.proxy_combo = QComboBox()
        self.proxy_combo.addItem("Без прокси", PROXY_NONE)
        self.proxy_combo.addItem("HTTP", PROXY_HTTP)
        self.proxy_combo.addItem("SOCKS5", PROXY_SOCKS5)
        self.proxy_combo.currentIndexChanged.connect(self._toggle_proxy)
        form.addRow(self._lbl("Прокси"), self.proxy_combo)

        # Быстрый ввод одной строкой
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("host:port:логин:пароль  или  host:port")
        self.line_edit.textChanged.connect(self._apply_line)
        form.addRow(self._lbl("Строкой"), self.line_edit)
        self.line_hint = QLabel("")
        self.line_hint.setObjectName("Hint")
        form.addRow("", self.line_hint)

        # host:port
        hp = QHBoxLayout()
        hp.setSpacing(8)
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("host / IP")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(1080)
        self.port_spin.setFixedWidth(96)
        hp.addWidget(self.host_edit, 1)
        hp.addWidget(self.port_spin)
        self.hp_row = self._wrap(hp)
        form.addRow(self._lbl("Адрес:порт"), self.hp_row)

        # логин/пароль
        up = QHBoxLayout()
        up.setSpacing(8)
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("логин (необязательно)")
        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("пароль (необязательно)")
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        up.addWidget(self.user_edit, 1)
        up.addWidget(self.pass_edit, 1)
        self.up_row = self._wrap(up)
        form.addRow(self._lbl("Авторизация"), self.up_row)

        root.addLayout(form)

        hint = QLabel("После создания нажмите «Папка» на карточке и положите туда папку "
                      "tdata от нужного аккаунта.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setObjectName("Primary")
        save_btn.setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ---- helpers ----
    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl

    def _wrap(self, layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _paint_color(self) -> None:
        color = self.color_combo.currentText()
        self.color_combo.setStyleSheet(
            f"QComboBox {{ color: {color}; font-weight: 700; }}"
        )

    def _toggle_proxy(self) -> None:
        enabled = self.proxy_combo.currentData() != PROXY_NONE
        self.hp_row.setEnabled(enabled)
        self.up_row.setEnabled(enabled)

    def _apply_line(self, text: str) -> None:
        text = text.strip()
        if not text:
            self.line_hint.setText("")
            return
        parsed = parse_proxy_line(text)
        if not parsed:
            self.line_hint.setText("⚠ Не распознано. Формат: host:port:логин:пароль")
            self.line_hint.setStyleSheet("color:#ffb454;")
            return
        host, port, user, password = parsed
        # если тип не выбран — по умолчанию SOCKS5 (частый формат для таких строк)
        if self.proxy_combo.currentData() == PROXY_NONE:
            self.proxy_combo.setCurrentIndex(self.proxy_combo.findData(PROXY_SOCKS5))
        self.host_edit.setText(host)
        self.port_spin.setValue(port)
        self.user_edit.setText(user)
        self.pass_edit.setText(password)
        self.line_hint.setText("✓ Распознано и подставлено ниже")
        self.line_hint.setStyleSheet("color:#3ddc84;")

    # ---- data ----
    def _load(self) -> None:
        a = self.account
        self.name_edit.setText(a.name)
        idx = self.color_combo.findText(a.color)
        self.color_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._paint_color()
        pidx = self.proxy_combo.findData(a.proxy.type)
        self.proxy_combo.setCurrentIndex(pidx if pidx >= 0 else 0)
        if a.proxy.host:
            self.host_edit.setText(a.proxy.host)
        if a.proxy.port:
            self.port_spin.setValue(a.proxy.port)
        self.user_edit.setText(a.proxy.username)
        self.pass_edit.setText(a.proxy.password)
        self._toggle_proxy()

    def _accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Проверьте данные", "Введите название аккаунта.")
            return
        ptype = self.proxy_combo.currentData()
        if ptype != PROXY_NONE and not self.host_edit.text().strip():
            QMessageBox.warning(self, "Проверьте данные",
                                "Укажите адрес прокси или выберите «Без прокси».")
            return
        self.account.name = name
        self.account.color = self.color_combo.currentText()
        self.account.proxy = Proxy(
            type=ptype,
            host=self.host_edit.text().strip(),
            port=self.port_spin.value(),
            username=self.user_edit.text().strip(),
            password=self.pass_edit.text(),
        )
        self.accept()

    def result_account(self) -> Account:
        return self.account
