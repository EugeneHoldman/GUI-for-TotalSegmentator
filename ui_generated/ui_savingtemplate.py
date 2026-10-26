# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'savingtemplate.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(435, 104)
        self.NewName = QLineEdit(Dialog)
        self.NewName.setObjectName(u"NewName")
        self.NewName.setGeometry(QRect(20, 30, 400, 22))
        font = QFont()
        font.setPointSize(11)
        self.NewName.setFont(font)
        self.label = QLabel(Dialog)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(20, 10, 211, 16))
        self.label.setFont(font)
        self.Create = QPushButton(Dialog)
        self.Create.setObjectName(u"Create")
        self.Create.setGeometry(QRect(330, 60, 90, 28))
        self.Create.setFont(font)

        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"Define new template name:", None))
        self.Create.setText(QCoreApplication.translate("Dialog", u"Create", None))
    # retranslateUi

