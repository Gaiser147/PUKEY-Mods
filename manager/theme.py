"""PUKEY dialogue theme; native controls remain editable and keyboard accessible."""
from pathlib import Path
from PySide6.QtGui import QFontDatabase
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
import os

ASSETS = Path(__file__).resolve().parent / 'assets'


def load_fonts():
    body_path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/segoeui.ttf'
    if body_path.is_file() and 'Segoe UI' not in QFontDatabase.families():
        QFontDatabase.addApplicationFont(str(body_path))
    for name in ('Amarante-Regular.ttf', 'Oswald.ttf'):
        path = ASSETS / 'fonts' / name
        if QFontDatabase.addApplicationFont(str(path)) < 0:
            raise RuntimeError('Required interface font could not be loaded: ' + name)
    body = 'Segoe UI' if 'Segoe UI' in QFontDatabase.families() else 'DejaVu Sans'
    QApplication.setFont(QFont(body, 10))


STYLE = '''
QWidget { font-family: "Segoe UI", "DejaVu Sans"; font-size: 10.5pt; color: #f0ece8; background: transparent; }
QMainWindow, QWidget#mainWorkspace { background: #111012; }
QDialog, QMessageBox { background: #211b24; }
QComboBox QAbstractItemView { background: #18151a; color: #f0ece8; border: 1px solid #766a78;
    selection-background-color: #02e5a2; selection-color: #111012; }
QComboBox QAbstractItemView QWidget { background: #18151a; }
QLabel { background: transparent; }
QLabel#brandName { font-family: Amarante; font-size: 28pt; }
QLabel#modTitle { font-family: Amarante; font-size: 27pt; }
QLabel#emptyTitle { font-family: Amarante; font-size: 22pt; }
QLabel#sectionTitle { font-family: Oswald; font-size: 13pt; }
QLabel#muted, QLabel#modStatus, QLabel#operationStatus, QLabel#sidebarMuted {
    color: #b5adb5; font-size: 9.5pt;
}
QLabel#keyHeading { font-family: Amarante; font-size: 16pt; padding: 14px 5px 12px; }
QListWidget#modNavigation { background: transparent; border: 0; outline: 0; }
QPushButton { min-height: 27px; padding: 4px 11px; border: 1px solid #766a78; border-radius: 3px; background: #18151a; }
QPushButton:hover { border-color: #f0ece8; background: #302630; }
QPushButton:pressed { background: #422135; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 2px solid #02e5a2; }
QPushButton#primary, QPushButton[prominent="true"] {
    font-family: Oswald; font-size: 13pt; min-height: 28px; min-width: 165px; padding: 4px 17px;
    border: 1px solid #ff0060; background: #d90051;
}
QPushButton#primary:hover, QPushButton[prominent="true"]:hover { color: #ffffff; background: #691039; }
QPushButton:disabled, QPushButton#primary:disabled, QPushButton[prominent="true"]:disabled {
    border-image: none; color: #a69aa6; background: #29232b; border: 1px solid #514452;
}
QPushButton#iconAction { min-width: 22px; padding: 4px 6px; border-color: transparent; }
QPushButton#activation:checked { color: #02e5a2; border-color: #02e5a2; }
QPushButton#sideLink, QPushButton#headerAction { border-color: transparent; background: transparent; }
QPushButton#sideLink { font-size: 9pt; color: #b5adb5; }
QPushButton#sideLink:hover, QPushButton#headerAction:hover { color: #02e5a2; background: #211a24; }
QPushButton#sideLink:focus, QPushButton#headerAction:focus { border-color: #02e5a2; }
QFrame#gamePanel { background: #211b24; border: 1px solid #766a78; border-radius: 3px; }
QLineEdit, QComboBox, QDoubleSpinBox {
    min-height: 26px; padding: 4px 9px; background: #080709; border: 1px solid #766a78; border-radius: 2px;
}
QLineEdit { placeholder-text-color: #b5adb5; }
QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled { color: #a69aa6; border-color: #514452; background: #201a22; }
QWidget#keyRow QComboBox { color: #02e5a2; font-family: Oswald; font-size: 12pt; }
QWidget#keyRow QComboBox:disabled { color: #a69aa6; }
QWidget#keyRow QComboBox[conflict="true"] { border-color: #ff8ba5; }
QLabel#keyConflict { color: #ff8ba5; font-size: 9pt; }
QDoubleSpinBox { padding-right: 23px; }
QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 22px; height: 17px; border-left: 1px solid #514452; }
QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 22px; height: 17px; border-left: 1px solid #514452; }
QComboBox::drop-down { width: 26px; border: 0; }
QComboBox::down-arrow { image: url("@assets@/chevron-down.svg"); width: 14px; height: 14px; }
QDoubleSpinBox::up-arrow { image: url("@assets@/chevron-up.svg"); width: 11px; height: 11px; }
QDoubleSpinBox::down-arrow { image: url("@assets@/chevron-down.svg"); width: 11px; height: 11px; }
QWidget#imageControls QLineEdit, QWidget#imageControls QComboBox, QWidget#imageControls QDoubleSpinBox {
    min-height: 23px; padding: 3px 8px;
}
QWidget#imageControls QDoubleSpinBox { padding-right: 23px; }
QTabWidget::pane { border: 0; border-top: 1px solid #514452; margin-top: -1px; }
QTabBar::tab { font-family: Oswald; font-size: 13pt; padding: 7px 12px; color: #b5adb5; background: transparent; border-bottom: 2px solid transparent; margin-right: 12px; }
QTabBar::tab:selected { color: #f0ece8; border-bottom-color: #02e5a2; }
QTabBar::tab:hover:!selected { color: #02e5a2; }
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { border: 0; background: transparent; }
QWidget#fieldRow, QWidget#keyRow { border-bottom: 1px solid #514452; }
QFrame#detailFooter { background: transparent; }
QProgressBar { border: 0; background: #29232b; }
QProgressBar::chunk { background: #ff0060; }
QCheckBox { spacing: 9px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked { border: 1px solid #766a78; border-radius: 2px; background: #080709; }
QCheckBox::indicator:checked { image: url("@assets@/check.svg"); border: 1px solid #02e5a2; border-radius: 2px; background: #02e5a2; }
QScrollBar:vertical { background: #211b24; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #766a78; min-height: 26px; border-radius: 3px; }
QScrollBar:horizontal { background: #211b24; height: 8px; margin: 0; }
QScrollBar::handle:horizontal { background: #766a78; min-width: 30px; border-radius: 3px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolButton { background: transparent; color: #f0ece8; border: 1px solid transparent; border-radius: 2px; }
QToolButton:hover { background: #302630; border-color: #766a78; }
QToolButton:focus { border-color: #02e5a2; }
QToolButton:disabled { background: transparent; }
QToolTip { color: #f0ece8; background: #302630; border: 1px solid #766a78; }
'''.replace('@assets@', ASSETS.as_posix())


def stylesheet(game_theme=None):
    if not game_theme:
        return STYLE
    # Qt style sheets resolve plain paths only; a file:/// URL silently draws nothing.
    image_url = (Path(game_theme) / 'button-pink.png').as_posix()
    return STYLE + '''
QPushButton#primary, QPushButton[prominent="true"] {
    border: 6px solid transparent; border-image: url("%s") 18 28 18 28 stretch stretch;
    background: transparent;
}
QPushButton#primary:disabled, QPushButton[prominent="true"]:disabled {
    border-image: none; background: #29232b; border: 1px solid #514452;
}
''' % image_url
