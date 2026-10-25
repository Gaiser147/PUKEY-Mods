"""Shared desktop presentation tokens expressed as native Qt style rules."""
from pathlib import Path

STYLE = '''
QWidget { font-size: 10.5pt; color: #252620; }
QMainWindow, QWidget#mainWorkspace { background: #ffffff; }
QFrame#sidebar { background: #252620; }
QFrame#sidebar QLabel { color: #ffffff; background: transparent; }
QFrame#sidebar QLabel#sidebarMuted { color: #b8bdb0; font-size: 9pt; }
QFrame#sidebar QLabel#brandName { font-size: 14pt; font-weight: 600; }
QFrame#sidebar QLabel#brandMark { color: #252620; background: #e8af42; border-radius: 9px; font-size: 21pt; font-weight: 600; }
QFrame#sidebar QLabel#libraryLabel { color: #b8bdb0; font-size: 9.5pt; font-weight: 600; }
QListWidget#modNavigation { background: transparent; border: 0; outline: 0; }
QLabel#modTitle { font-size: 22pt; font-weight: 600; }
QLabel#emptyTitle { font-size: 18pt; font-weight: 600; }
QLabel#muted, QLabel#modStatus { color: #595c53; font-size: 9.5pt; }
QLabel#sectionTitle { font-weight: 600; }
QLabel#modIcon { background: #f5e9cf; border-radius: 10px; }
QPushButton { min-height: 28px; padding: 5px 12px; border: 1px solid #b8bdb0; border-radius: 6px; background: #ffffff; }
QPushButton:hover { background: #eeeee7; border-color: #73766d; }
QPushButton:pressed { background: #dfdfd6; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus { border: 2px solid #8a5c0d; }
QPushButton#primary, QPushButton[prominent="true"] { background: #e8af42; border-color: #be882b; font-weight: 600; }
QPushButton#primary:hover, QPushButton[prominent="true"]:hover { background: #efbf65; }
QPushButton:disabled, QPushButton#primary:disabled, QPushButton[prominent="true"]:disabled {
  color: #73766d; background: #e6e6df; border-color: #d0d3c8;
}
QPushButton#iconAction { min-width: 22px; min-height: 28px; padding: 5px 7px; border-color: transparent; }
QPushButton#activation { background: transparent; border-color: #d9dcd3; }
QPushButton#activation:checked { color: #31633e; border-color: #31633e; }
QPushButton#activation:disabled { color: #73766d; border-color: #d9dcd3; }
QPushButton#sideRefresh { color: #ffffff; background: #252620; border-color: #595c53; }
QPushButton#sideRefresh:hover { background: #393b33; border-color: #b8bdb0; }
QPushButton#sideRefresh:disabled { color: #a7ad9f; border-color: #595c53; }
QPushButton#sideLink { color: #b8bdb0; font-size: 9pt; background: transparent; border-color: transparent; padding: 4px 8px; }
QPushButton#sideLink:hover { color: #ffffff; background: #393b33; }
QPushButton#sideLink:focus, QPushButton#sideRefresh:focus { border: 2px solid #e8af42; }
QFrame#gamePanel { background: #f4f3ef; border: 1px solid #d9dcd3; border-radius: 8px; }
QFrame#gamePanel QLabel { background: transparent; }
QLineEdit, QComboBox, QDoubleSpinBox { min-height: 28px; padding: 4px 9px; background: #ffffff; border: 1px solid #b8bdb0; border-radius: 5px; }
QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled { color: #73766d; border-color: #d9dcd3; background: #f4f3ef; }
QDoubleSpinBox { padding-right: 23px; }
QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 22px; height: 18px; border-left: 1px solid #d9dcd3; }
QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 22px; height: 18px; border-left: 1px solid #d9dcd3; }
QComboBox::drop-down { width: 26px; border: 0; }
QComboBox::down-arrow { image: url("@assets@/chevron-down.svg"); width: 14px; height: 14px; }
QDoubleSpinBox::up-arrow { image: url("@assets@/chevron-up.svg"); width: 11px; height: 11px; }
QDoubleSpinBox::down-arrow { image: url("@assets@/chevron-down.svg"); width: 11px; height: 11px; }
QWidget#imageControls QLineEdit, QWidget#imageControls QComboBox, QWidget#imageControls QDoubleSpinBox {
  min-height: 24px; padding: 3px 8px;
}
QWidget#imageControls QDoubleSpinBox { padding-right: 23px; }
QWidget#imageControls QDoubleSpinBox::up-button, QWidget#imageControls QDoubleSpinBox::down-button { height: 16px; }
QLineEdit { placeholder-text-color: #595c53; }
QTabWidget::pane { border: 0; border-top: 1px solid #d9dcd3; margin-top: -1px; }
QTabBar::tab { padding: 12px 14px; color: #595c53; background: transparent; border-bottom: 2px solid transparent; margin-right: 12px; }
QTabBar::tab:selected { color: #252620; border-bottom: 2px solid #be882b; font-weight: 600; }
QTabBar::tab:hover:!selected { color: #252620; background: #f4f3ef; }
QScrollArea { border: 0; background: #ffffff; }
QScrollArea > QWidget > QWidget { background: #ffffff; }
QWidget#fieldRow { border-bottom: 1px solid #d9dcd3; }
QFrame#detailFooter { border-top: 1px solid #d9dcd3; background: #ffffff; }
QLabel#operationStatus { font-size: 9pt; color: #595c53; }
QProgressBar { border: 0; background: #dedfd6; }
QProgressBar::chunk { background: #a76d0f; }
QCheckBox { spacing: 9px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked { border: 1px solid #b8bdb0; border-radius: 4px; background: #ffffff; }
QCheckBox::indicator:checked { image: url("@assets@/check.svg"); border: 1px solid #be882b; border-radius: 4px; background: #e8af42; }
QScrollBar:vertical { background: #f4f3ef; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #a7ad9f; min-height: 26px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
'''.replace('@assets@', (Path(__file__).resolve().parent / 'assets').as_posix())
