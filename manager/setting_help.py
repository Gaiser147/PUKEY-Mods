"""Keyboard-accessible plain-text setting explanations."""
import html

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtWidgets import QToolButton, QToolTip, QFrame, QVBoxLayout, QLabel, QScrollArea

from .widgets import icon


DIGITS = ['ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE']


def key_label(code):
    """Name a UE4SS key code the way the keyboard does; the code itself is still what gets saved."""
    if code in DIGITS:
        return str(DIGITS.index(code))
    if len(code) == 1 or (code[:1] == 'F' and code[1:].isdigit()):
        return code
    return code.replace('_', ' ').title()


def default_label(field):
    return key_label(str(field['default'])) if field['type'] == 'key' else str(field['default'])


def explanation(field):
    lines = [field['label'], field.get('description', 'Adjust this mod preference.')]
    for value in field.get('options', []):
        description = field.get('option_descriptions', {}).get(value)
        if description:
            lines.append(value + ': ' + description)
    lines.append('Default: ' + default_label(field))
    if field['type'] == 'number':
        lines.append('Range: ' + str(field['min']) + ' – ' + str(field['max']))
    lines.append('Save settings, then restart the game to apply changes.')
    return '\n\n'.join(lines)


class HelpButton(QToolButton):
    def __init__(self, field, parent=None):
        super().__init__(parent)
        self.help_text = explanation(field)
        self.setIcon(icon('info'))
        self.setFixedSize(26, 28)
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('About ' + field['label'])
        self.setAccessibleDescription(self.help_text)
        self.setToolTip('<p>' + html.escape(self.help_text).replace('\n', '<br>') + '</p>')
        self.clicked.connect(self.show_help)

    def show_help(self):
        QToolTip.hideText()
        popup = getattr(self, '_popup', None)
        if popup is None:
            popup = self._popup = HelpPopup(self.help_text, self)
        popup.adjustSize()
        position = self.mapToGlobal(QPoint(0, self.height()))
        area = self.screen().availableGeometry()
        position.setX(max(area.left(), min(position.x(), area.right() - popup.width())))
        position.setY(max(area.top(), min(position.y(), area.bottom() - popup.height())))
        popup.move(position)
        popup.show()
        popup.setFocus(Qt.FocusReason.PopupFocusReason)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QToolTip.showText(self.mapToGlobal(QPoint(0, self.height())),
                         html.escape(self.help_text).replace('\n', '<br>'), self)

    def focusOutEvent(self, event):
        QToolTip.hideText()
        super().focusOutEvent(event)


class HelpPopup(QFrame):
    def __init__(self, text, parent):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName('settingHelpPopup')
        self.setStyleSheet('QFrame#settingHelpPopup { background: #302630; border: 1px solid #766a78; }')
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setFixedWidth(420)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setMinimumHeight(label.heightForWidth(420))
        scroll = QScrollArea()
        scroll.setWidget(label)
        scroll.setWidgetResizable(True)
        height = min(max(80, label.heightForWidth(420) + 6), max(100, min(420, self.screen().availableGeometry().height() - 80)))
        scroll.setFixedSize(440, height)
        layout.addWidget(scroll)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)
