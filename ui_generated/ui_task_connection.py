# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'task_connection.ui'
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
    QListView, QPushButton, QSizePolicy, QWidget)

class Ui_TasksConnection(object):
    def setupUi(self, TasksConnection):
        if not TasksConnection.objectName():
            TasksConnection.setObjectName(u"TasksConnection")
        TasksConnection.resize(679, 580)
        TasksConnection.setMaximumSize(QSize(780, 670))
        self.ConnectedTask = QListView(TasksConnection)
        self.ConnectedTask.setObjectName(u"ConnectedTask")
        self.ConnectedTask.setGeometry(QRect(20, 100, 300, 461))
        self.ConnectedTask.setMinimumSize(QSize(300, 400))
        self.ClassesInTask = QListView(TasksConnection)
        self.ClassesInTask.setObjectName(u"ClassesInTask")
        self.ClassesInTask.setGeometry(QRect(360, 100, 300, 400))
        self.label = QLabel(TasksConnection)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(20, 80, 121, 16))
        font = QFont()
        font.setPointSize(11)
        self.label.setFont(font)
        self.label_2 = QLabel(TasksConnection)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(360, 80, 121, 16))
        self.label_2.setFont(font)
        self.Save = QPushButton(TasksConnection)
        self.Save.setObjectName(u"Save")
        self.Save.setGeometry(QRect(360, 538, 140, 28))
        self.Save.setFont(font)
        self.pushButton_2 = QPushButton(TasksConnection)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setGeometry(QRect(520, 538, 140, 28))
        self.pushButton_2.setFont(font)
        self.Search = QPushButton(TasksConnection)
        self.Search.setObjectName(u"Search")
        self.Search.setGeometry(QRect(320, 39, 81, 28))
        self.Search.setFont(font)
        self.SearchRequest = QLineEdit(TasksConnection)
        self.SearchRequest.setObjectName(u"SearchRequest")
        self.SearchRequest.setGeometry(QRect(20, 39, 291, 28))
        self.SearchRequest.setFont(font)
        self.label_5 = QLabel(TasksConnection)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(20, 10, 231, 16))
        self.label_5.setFont(font)
        self.NextResult = QPushButton(TasksConnection)
        self.NextResult.setObjectName(u"NextResult")
        self.NextResult.setGeometry(QRect(410, 39, 81, 28))
        self.NextResult.setFont(font)
        self.ChooseAll = QPushButton(TasksConnection)
        self.ChooseAll.setObjectName(u"ChooseAll")
        self.ChooseAll.setGeometry(QRect(360, 505, 140, 28))
        self.ChooseAll.setFont(font)
        self.ChooseSelected = QPushButton(TasksConnection)
        self.ChooseSelected.setObjectName(u"ChooseSelected")
        self.ChooseSelected.setGeometry(QRect(520, 505, 140, 28))
        self.ChooseSelected.setFont(font)

        self.retranslateUi(TasksConnection)

        QMetaObject.connectSlotsByName(TasksConnection)
    # setupUi

    def retranslateUi(self, TasksConnection):
        TasksConnection.setWindowTitle(QCoreApplication.translate("TasksConnection", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("TasksConnection", u"Connected tasks:", None))
        self.label_2.setText(QCoreApplication.translate("TasksConnection", u"Classes in task:", None))
        self.Save.setText(QCoreApplication.translate("TasksConnection", u"Save", None))
        self.pushButton_2.setText(QCoreApplication.translate("TasksConnection", u"Close", None))
        self.Search.setText(QCoreApplication.translate("TasksConnection", u"Search", None))
        self.label_5.setText(QCoreApplication.translate("TasksConnection", u"Structure (task) search:", None))
        self.NextResult.setText(QCoreApplication.translate("TasksConnection", u"Next", None))
        self.ChooseAll.setText(QCoreApplication.translate("TasksConnection", u"(Un)Flag all", None))
        self.ChooseSelected.setText(QCoreApplication.translate("TasksConnection", u"(Un)Flag selected", None))
    # retranslateUi

