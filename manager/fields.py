"""Input fields that never change a value the user did not mean to change."""
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QToolButton

from .widgets import icon

QT_KEYS = {getattr(Qt.Key, 'Key_F%d' % n): 'F%d' % n for n in range(1, 13)}
QT_KEYS.update({getattr(Qt.Key, 'Key_' + letter): letter for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'})
QT_KEYS.update({getattr(Qt.Key, 'Key_%d' % n): name for n, name in enumerate(
    ['ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE'])})
QT_KEYS.update({Qt.Key.Key_Home: 'HOME', Qt.Key.Key_End: 'END', Qt.Key.Key_PageUp: 'PAGE_UP',
                Qt.Key.Key_PageDown: 'PAGE_DOWN', Qt.Key.Key_Insert: 'INSERT', Qt.Key.Key_Delete: 'DELETE',
                Qt.Key.Key_Space: 'SPACE'})


def number_text(value, locale=None):
    """A number as the fields show it: the locale's decimal mark, never a thousands separator."""
    from PySide6.QtCore import QLocale
    locale = QLocale(locale or QLocale())
    locale.setNumberOptions(QLocale.NumberOption.OmitGroupSeparator)
    return locale.toString(float(value), 'g', 15)


class WheelGuard:
    """Scrolling the page over an unfocused field must scroll the page, not edit the field."""
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class ChoiceField(WheelGuard, QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


class NumberField(WheelGuard, QDoubleSpinBox):
    """Accepts "." and "," as the decimal mark and explains instead of silently dropping input.

    Qt rejects keystrokes that would leave the range, so "99999" in a 1–20 field became "9", and
    the German locale read "1.5" as 15. Out-of-range or over-precise text is now allowed while
    typing and corrected on leaving the field, with `adjusted` naming the correction. An empty
    message means the user has edited again and an earlier note no longer applies.
    """
    adjusted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setGroupSeparatorShown(False)
        self.lineEdit().textEdited.connect(lambda text: self.adjusted.emit(''))

    def _normal(self, text):
        mark = self.locale().decimalPoint()
        return text.replace('.', mark).replace(',', mark)

    def _number(self, text):
        body = text.strip()
        if self.suffix() and body.endswith(self.suffix().strip()):
            body = body[:-len(self.suffix().strip())].strip()
        if self.decimals() == 0 and re.fullmatch(r'-?\d{1,3}(?:[.,]\d{3})+', body):
            body = body.replace('.', '').replace(',', '')  # whole-number fields: "1.000" means a thousand
        body = self._normal(body)
        value, ok = self.locale().toDouble(body)
        places = len(body.split(self.locale().decimalPoint(), 1)[1]) if self.locale().decimalPoint() in body else 0
        return (value if ok else None), places

    def validate(self, text, position):
        value, places = self._number(text)
        if value is None:
            return super().validate(self._normal(text), position)
        if not self.minimum() <= value <= self.maximum() or places > self.decimals():
            return QValidator.State.Intermediate, text, position
        return QValidator.State.Acceptable, text, position

    def valueFromText(self, text):
        value, _ = self._number(text)
        return super().valueFromText(self._normal(text)) if value is None else value

    def _correct(self):
        # PySide ignores text returned from fixup(), so out-of-range input is corrected here,
        # before Qt would quietly fall back to the previous value.
        value, places = self._number(self.lineEdit().text())
        if value is None:
            return
        message = None
        if places > self.decimals():
            value = round(value, self.decimals())
            message = 'Rounded to {} decimal place{}.'.format(self.decimals(), '' if self.decimals() == 1 else 's')
        if value > self.maximum():
            value, message = self.maximum(), 'Maximum is ' + number_text(self.maximum(), self.locale()) + '.'
        elif value < self.minimum():
            value, message = self.minimum(), 'Minimum is ' + number_text(self.minimum(), self.locale()) + '.'
        if message:
            self.setValue(value)
            self.adjusted.emit(message)

    def stepBy(self, steps):
        self.adjusted.emit('')
        super().stepBy(steps)

    def focusOutEvent(self, event):
        self._correct()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._correct()
        super().keyPressEvent(event)


class KeyCaptureButton(QToolButton):
    """Assign a key by pressing it; the list beside it stays available."""
    captured = Signal(str)
    rejected = Signal(str)

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.label = label
        self.setCheckable(True)
        self.setAutoRaise(True)
        self.setFixedSize(26, 28)
        self.setIcon(icon('keyboard'))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Assign ' + label + ' by pressing a key')
        self.setToolTip('Press a key to assign it. Esc cancels.')
        self.toggled.connect(self._toggled)

    def _toggled(self, listening):
        if listening:
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            self.grabKeyboard()
        else:
            self.releaseKeyboard()

    def keyPressEvent(self, event):
        if not self.isChecked():
            return super().keyPressEvent(event)
        key = event.key()
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta, Qt.Key.Key_AltGr):
            return
        self.setChecked(False)
        if key == Qt.Key.Key_Escape:
            return
        code = None if event.modifiers() & Qt.KeyboardModifier.KeypadModifier else QT_KEYS.get(key)
        if code:
            self.captured.emit(code)
        else:
            self.rejected.emit(event.text().strip() or 'This key')

    def focusOutEvent(self, event):
        self.setChecked(False)
        super().focusOutEvent(event)
