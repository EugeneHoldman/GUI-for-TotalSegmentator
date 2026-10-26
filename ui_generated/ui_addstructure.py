# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'addstructure.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTreeView,
    QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(505, 290)
        Dialog.setMinimumSize(QSize(505, 290))
        Dialog.setMaximumSize(QSize(505, 290))
        self.label = QLabel(Dialog)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(20, 70, 231, 16))
        font = QFont()
        font.setPointSize(11)
        self.label.setFont(font)
        self.Save = QPushButton(Dialog)
        self.Save.setObjectName(u"Save")
        self.Save.setGeometry(QRect(300, 250, 93, 28))
        self.Save.setFont(font)
        self.AllStruct = QTreeView(Dialog)
        self.AllStruct.setObjectName(u"AllStruct")
        self.AllStruct.setGeometry(QRect(20, 90, 471, 151))
        self.AllStruct.setFont(font)
        self.pushButton = QPushButton(Dialog)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(400, 250, 93, 28))
        self.pushButton.setFont(font)
        self.NextResult = QPushButton(Dialog)
        self.NextResult.setObjectName(u"NextResult")
        self.NextResult.setGeometry(QRect(410, 39, 81, 28))
        self.NextResult.setFont(font)
        self.Search = QPushButton(Dialog)
        self.Search.setObjectName(u"Search")
        self.Search.setGeometry(QRect(320, 39, 81, 28))
        self.Search.setFont(font)
        self.SearchRequest = QLineEdit(Dialog)
        self.SearchRequest.setObjectName(u"SearchRequest")
        self.SearchRequest.setGeometry(QRect(20, 39, 291, 28))
        self.SearchRequest.setFont(font)
        self.label_5 = QLabel(Dialog)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(20, 10, 231, 16))
        self.label_5.setFont(font)

        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"Choose structures you want to add:", None))
        self.Save.setText(QCoreApplication.translate("Dialog", u"Save", None))
        self.pushButton.setText(QCoreApplication.translate("Dialog", u"Close", None))
        self.NextResult.setText(QCoreApplication.translate("Dialog", u"Next", None))
        self.Search.setText(QCoreApplication.translate("Dialog", u"Search", None))
        self.label_5.setText(QCoreApplication.translate("Dialog", u"Structure (task) search:", None))
    # retranslateUi

