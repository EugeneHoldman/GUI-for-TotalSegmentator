# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'license.ui'
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
        Dialog.resize(403, 120)
        Dialog.setMinimumSize(QSize(403, 120))
        Dialog.setMaximumSize(QSize(403, 120))
        self.KeyValue = QLineEdit(Dialog)
        self.KeyValue.setObjectName(u"KeyValue")
        self.KeyValue.setGeometry(QRect(30, 40, 341, 22))
        font = QFont()
        font.setPointSize(11)
        self.KeyValue.setFont(font)
        self.label = QLabel(Dialog)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(30, 20, 171, 16))
        self.label.setFont(font)
        self.pushButton = QPushButton(Dialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(170, 70, 93, 28))
        self.pushButton.setFont(font)
        self.pushButton_2 = QPushButton(Dialog)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setGeometry(QRect(280, 70, 93, 28))
        self.pushButton_2.setFont(font)

        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"Enter your license key:", None))
        self.pushButton.setText(QCoreApplication.translate("Dialog", u"Validate", None))
        self.pushButton_2.setText(QCoreApplication.translate("Dialog", u"Close", None))
    # retranslateUi

