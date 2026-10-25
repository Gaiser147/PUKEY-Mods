"""Native presentation widgets and a small, consistent line-icon family."""
from functools import lru_cache
import math

from PySide6.QtCore import Qt, QSize, QRectF, QPoint, QPointF, QLineF
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QPen, QPolygonF, QFont, QTextOption
from PySide6.QtWidgets import QLabel, QStyledItemDelegate, QStyle, QSizePolicy


@lru_cache(maxsize=128)
def icon(kind, color='#252620'):
    image = QPixmap(48, 48)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(2, 2)
    painter.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    def line(x1, y1, x2, y2):
        painter.drawLine(QLineF(x1, y1, x2, y2))
    def rounded(x, y, w, h, radius=2):
        painter.drawRoundedRect(QRectF(x, y, w, h), radius, radius)
    if kind == 'camera':
        rounded(3, 7, 18, 13)
        painter.drawEllipse(QRectF(8, 10, 8, 8))
        painter.drawPolyline(QPolygonF([QPointF(7, 7), QPointF(9, 4), QPointF(15, 4), QPointF(17, 7)]))
    elif kind == 'sun':
        painter.drawEllipse(QRectF(8, 8, 8, 8))
        for step in range(8):
            angle = step * math.pi / 4
            line(12 + math.cos(angle) * 7, 12 + math.sin(angle) * 7,
                 12 + math.cos(angle) * 10, 12 + math.sin(angle) * 10)
    elif kind == 'image':
        rounded(3, 3, 18, 18)
        painter.drawEllipse(QRectF(7, 6, 3, 3))
        painter.drawPolyline(QPolygonF([QPointF(4, 18), QPointF(10, 12), QPointF(14, 16), QPointF(17, 13), QPointF(21, 17)]))
    elif kind == 'film':
        rounded(3, 3, 18, 18)
        line(7, 3, 7, 21); line(17, 3, 17, 21)
        for y in (8, 13, 18):
            line(3, y, 7, y); line(17, y, 21, y)
    elif kind == 'folder':
        painter.drawPolyline(QPolygonF([QPointF(3, 7), QPointF(3, 5), QPointF(9, 5), QPointF(12, 8), QPointF(21, 8),
                                       QPointF(21, 20), QPointF(3, 20), QPointF(3, 7)]))
    elif kind == 'refresh':
        painter.drawArc(QRectF(4, 4, 16, 16), 35 * 16, 285 * 16)
        painter.drawPolyline(QPolygonF([QPointF(15, 3), QPointF(21, 4), QPointF(20, 10)]))
    elif kind in ('download', 'save'):
        line(12, 3, 12, 15)
        painter.drawPolyline(QPolygonF([QPointF(7, 10), QPointF(12, 15), QPointF(17, 10)]))
        painter.drawPolyline(QPolygonF([QPointF(4, 16), QPointF(4, 21), QPointF(20, 21), QPointF(20, 16)]))
    elif kind == 'power':
        painter.drawArc(QRectF(4, 4, 16, 16), 135 * 16, 270 * 16)
        line(12, 2, 12, 11)
    elif kind == 'book':
        rounded(4, 3, 16, 18)
        line(8, 3, 8, 21); line(11, 8, 17, 8); line(11, 12, 17, 12)
    elif kind == 'trash':
        line(3, 6, 21, 6); line(9, 3, 15, 3)
        painter.drawPolyline(QPolygonF([QPointF(6, 6), QPointF(7, 21), QPointF(17, 21), QPointF(18, 6)]))
        line(10, 10, 10, 17); line(14, 10, 14, 17)
    elif kind == 'link':
        rounded(3, 7, 10, 10, 4); rounded(11, 3, 10, 10, 4)
        line(9, 15, 15, 9)
    elif kind == 'eye':
        painter.drawEllipse(QRectF(3, 6, 18, 12))
        painter.drawEllipse(QRectF(9, 9, 6, 6))
    elif kind == 'undo':
        painter.drawArc(QRectF(5, 7, 15, 14), -60 * 16, 240 * 16)
        painter.drawPolyline(QPolygonF([QPointF(3, 10), QPointF(3, 4), QPointF(9, 4)]))
    elif kind == 'check':
        painter.drawPolyline(QPolygonF([QPointF(5, 12), QPointF(10, 17), QPointF(20, 6)]))
    else:
        painter.drawPolygon(QPolygonF([QPointF(12, 2), QPointF(21, 7), QPointF(21, 17),
                                      QPointF(12, 22), QPointF(3, 17), QPointF(3, 7)]))
        line(3, 7, 12, 12); line(21, 7, 12, 12); line(12, 12, 12, 22)
    painter.end()
    image.setDevicePixelRatio(2)
    return QIcon(image)


def mod_icon(mod, color='#252620'):
    kind = ('image' if mod.get('images') else 'film' if mod.get('video_list') else
            'camera' if mod.get('id') == 'FreeCam' else 'sun' if mod.get('id') == 'LightTools' else 'package')
    return icon(kind, color)


class ModDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(224, 76)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = option.rect.adjusted(8, 3, -8, -3)
        if selected or hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor('#e8af42') if selected else QColor('#393b33'))
            painter.drawRoundedRect(QRectF(rect), 8, 8)
        foreground = '#252620' if selected else '#ffffff'
        secondary = '#252620' if selected else '#b8bdb0'
        mod = index.data(Qt.ItemDataRole.UserRole) or {}
        mod_icon(mod, foreground).paint(painter, rect.x() + 14, rect.y() + 22, 24, 24)
        lines = str(index.data(Qt.ItemDataRole.DisplayRole) or '').split('\n', 1)
        left = rect.x() + 52
        width = rect.width() - 62
        font = QFont(option.font)
        font.setPointSizeF(10.5)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(foreground))
        painter.drawText(left, rect.y() + 29, painter.fontMetrics().elidedText(lines[0], Qt.TextElideMode.ElideRight, width))
        font.setPointSizeF(9)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor(secondary))
        painter.drawText(left, rect.y() + 48, painter.fontMetrics().elidedText(lines[1] if len(lines) > 1 else '', Qt.TextElideMode.ElideRight, width))
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor('#8a5c0d' if selected else '#b8bdb0'), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(rect.adjusted(2, 2, -2, -2)), 7, 7)
        painter.restore()


class PreviewCanvas(QLabel):
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setObjectName('previewCanvas')
        self.setAccessibleName('Replacement image preview')
        self.setMinimumSize(160, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self):
        return QSize(300, 260)

    def minimumSizeHint(self):
        return QSize(160, 220)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#f4f3ef'))
        pixmap = self.pixmap()
        if pixmap is not None and not pixmap.isNull():
            size = self.size() - QSize(28, 28)
            scaled = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x, y = (self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2
            painter.save()
            painter.setClipRect(x, y, scaled.width(), scaled.height())
            for row in range(y, y + scaled.height(), 12):
                for column in range(x, x + scaled.width(), 12):
                    shade = '#ffffff' if ((row - y) // 12 + (column - x) // 12) % 2 else '#d9dcd3'
                    painter.fillRect(column, row, 12, 12, QColor(shade))
            painter.drawPixmap(QPoint(x, y), scaled)
            painter.restore()
        else:
            icon('image', '#73766d').paint(painter, self.width() // 2 - 18, self.height() // 2 - 54, 36, 36)
            painter.setPen(QColor('#595c53'))
            text_option = QTextOption(Qt.AlignmentFlag.AlignHCenter)
            text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
            painter.drawText(QRectF(20, self.height() // 2 + 2, self.width() - 40, self.height() // 2 - 20),
                             self.text(), text_option)
        painter.end()
