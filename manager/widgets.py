"""Native presentation widgets and a small, consistent line-icon family."""
from functools import lru_cache
import math
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QRectF, QPoint, QPointF, QLineF
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QPen, QPolygonF, QFont, QTextOption, QRegion
from PySide6.QtWidgets import QLabel, QStyledItemDelegate, QStyle, QSizePolicy, QFrame, QListWidget, QListView


@lru_cache(maxsize=16)
def texture(name, directory=None):
    if not directory:
        return QPixmap()
    pixmap = QPixmap(str(Path(directory) / (name + '.png')))
    if pixmap.isNull():
        return pixmap
    bounds = QRegion(pixmap.mask()).boundingRect()
    return pixmap.copy(bounds) if not bounds.isEmpty() else pixmap


def widget_texture(widget, name):
    return texture(name, widget.window().property('gameThemePath'))


class DialoguePanel(QFrame):
    """Real texture, with stable corners rather than stretched edge decoration."""
    def __init__(self, kind='sheet', parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setObjectName('dialoguePanel')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        source = widget_texture(self, self.kind)
        if source.isNull() or min(source.width(), source.height()) <= 96:
            painter.fillRect(self.rect(), QColor('#18151a'))
            painter.setPen(QPen(QColor('#514452'), 1))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 3, 3)
            painter.end()
            return
        edge, inset = 48, 16
        xs = (0, edge, source.width()-edge, source.width())
        ys = (0, edge, source.height()-edge, source.height())
        dx = (0, inset, self.width()-inset, self.width())
        dy = (0, inset, self.height()-inset, self.height())
        for row in range(3):
            for col in range(3):
                painter.drawPixmap(QRectF(dx[col], dy[row], dx[col+1]-dx[col], dy[row+1]-dy[row]),
                    source, QRectF(xs[col], ys[row], xs[col+1]-xs[col], ys[row+1]-ys[row]))
        painter.end()


class ModNavigation(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(False)
        self.setMovement(QListView.Movement.Static)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(68)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateGeometries()
        self.doItemsLayout()


class OrnamentHeading(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(self.rect().adjusted(0, 7, 0, -7), widget_texture(self, 'heading'))
        painter.end()
        super().paintEvent(event)


@lru_cache(maxsize=128)
def icon(kind, color='#f0ece8'):
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


def mod_icon(mod, color='#f0ece8'):
    kind = ('image' if mod.get('images') else 'film' if mod.get('video_list') else
            'camera' if mod.get('id') == 'FreeCam' else 'sun' if mod.get('id') == 'LightTools' else 'package')
    return icon(kind, color)


class ModDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        view = self.parent()
        count = max(1, min(4, view.count()))
        return QSize(max(185, view.viewport().width() // count), 53)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = option.rect.adjusted(4, 5, -9, -5)
        if selected or hovered:
            painter.setOpacity(1 if selected else .22)
            ribbon = widget_texture(self.parent(), 'ribbon')
            if ribbon.isNull():
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor('#02e5a2'))
                painter.drawRoundedRect(QRectF(rect), 2, 2)
            else:
                painter.drawPixmap(rect, ribbon)
            painter.setOpacity(1)
        foreground = '#101113' if selected else '#f0ece8'
        lines = str(index.data(Qt.ItemDataRole.DisplayRole) or '').split('\n', 1)
        left = rect.x() + 19
        width = rect.width() - 38
        font = QFont('Oswald', 15)
        painter.setFont(font)
        painter.setPen(QColor(foreground))
        painter.drawText(QRectF(left, rect.y(), width, rect.height()), Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(lines[0], Qt.TextElideMode.ElideRight, width))
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor('#101113' if selected else '#02e5a2'), 1, Qt.PenStyle.DashLine))
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
        painter.fillRect(self.rect(), QColor('#141216'))
        pixmap = self.pixmap()
        if pixmap is not None and not pixmap.isNull():
            size = self.size() - QSize(28, 28)
            scaled = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x, y = (self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2
            painter.save()
            painter.setClipRect(x, y, scaled.width(), scaled.height())
            for row in range(y, y + scaled.height(), 12):
                for column in range(x, x + scaled.width(), 12):
                    shade = '#514c55' if ((row - y) // 12 + (column - x) // 12) % 2 else '#38343d'
                    painter.fillRect(column, row, 12, 12, QColor(shade))
            painter.drawPixmap(QPoint(x, y), scaled)
            painter.restore()
        else:
            icon('image', '#b5adb5').paint(painter, self.width() // 2 - 18, self.height() // 2 - 54, 36, 36)
            painter.setPen(QColor('#b5adb5'))
            text_option = QTextOption(Qt.AlignmentFlag.AlignHCenter)
            text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
            painter.drawText(QRectF(20, self.height() // 2 + 2, self.width() - 40, self.height() // 2 - 20),
                             self.text(), text_option)
        painter.end()
