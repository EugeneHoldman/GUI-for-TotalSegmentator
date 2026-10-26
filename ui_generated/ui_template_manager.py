# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'template_manager.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QHeaderView, QLabel,
    QLineEdit, QListView, QMainWindow, QMenuBar,
    QPushButton, QSizePolicy, QStatusBar, QTreeView,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(780, 670)
        MainWindow.setMinimumSize(QSize(780, 670))
        MainWindow.setMaximumSize(QSize(780, 670))
        font = QFont()
        font.setPointSize(9)
        MainWindow.setFont(font)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(20, 10, 71, 21))
        font1 = QFont()
        font1.setPointSize(11)
        self.label.setFont(font1)
        self.TemplName = QComboBox(self.centralwidget)
        self.TemplName.setObjectName(u"TemplName")
        self.TemplName.setGeometry(QRect(90, 10, 331, 22))
        self.TemplName.setFont(font1)
        self.NewTempl = QPushButton(self.centralwidget)
        self.NewTempl.setObjectName(u"NewTempl")
        self.NewTempl.setGeometry(QRect(90, 40, 160, 28))
        self.NewTempl.setFont(font1)
        self.Del = QPushButton(self.centralwidget)
        self.Del.setObjectName(u"Del")
        self.Del.setGeometry(QRect(260, 40, 160, 28))
        self.Del.setFont(font1)
        self.Remove = QPushButton(self.centralwidget)
        self.Remove.setObjectName(u"Remove")
        self.Remove.setGeometry(QRect(330, 370, 111, 28))
        self.Remove.setFont(font1)
        self.Add = QPushButton(self.centralwidget)
        self.Add.setObjectName(u"Add")
        self.Add.setGeometry(QRect(330, 320, 111, 28))
        self.Add.setFont(font1)
        self.AllStruct = QTreeView(self.centralwidget)
        self.AllStruct.setObjectName(u"AllStruct")
        self.AllStruct.setGeometry(QRect(450, 190, 300, 400))
        self.AllStruct.setFont(font1)
        self.CurrentStruct = QListView(self.centralwidget)
        self.CurrentStruct.setObjectName(u"CurrentStruct")
        self.CurrentStruct.setGeometry(QRect(20, 190, 300, 400))
        self.CurrentStruct.setFont(font1)
        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(20, 160, 141, 21))
        self.label_2.setFont(font1)
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(450, 160, 141, 21))
        self.label_3.setFont(font1)
        self.Save = QPushButton(self.centralwidget)
        self.Save.setObjectName(u"Save")
        self.Save.setGeometry(QRect(330, 420, 111, 28))
        self.Save.setFont(font1)
        self.Exit = QPushButton(self.centralwidget)
        self.Exit.setObjectName(u"Exit")
        self.Exit.setGeometry(QRect(660, 600, 93, 28))
        self.Exit.setFont(font1)
        self.Save_3 = QPushButton(self.centralwidget)
        self.Save_3.setObjectName(u"Save_3")
        self.Save_3.setGeometry(QRect(330, 470, 111, 28))
        self.Save_3.setFont(font1)
        self.SearchRequest = QLineEdit(self.centralwidget)
        self.SearchRequest.setObjectName(u"SearchRequest")
        self.SearchRequest.setGeometry(QRect(20, 119, 291, 28))
        self.SearchRequest.setFont(font1)
        self.Search = QPushButton(self.centralwidget)
        self.Search.setObjectName(u"Search")
        self.Search.setGeometry(QRect(320, 119, 81, 28))
        self.Search.setFont(font1)
        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(20, 90, 231, 16))
        self.label_5.setFont(font1)
        self.NextResult = QPushButton(self.centralwidget)
        self.NextResult.setObjectName(u"NextResult")
        self.NextResult.setGeometry(QRect(410, 119, 81, 28))
        self.NextResult.setFont(font1)
        self.Reload = QPushButton(self.centralwidget)
        self.Reload.setObjectName(u"Reload")
        self.Reload.setGeometry(QRect(330, 520, 111, 28))
        self.Reload.setFont(font1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 780, 21))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Template", None))
        self.NewTempl.setText(QCoreApplication.translate("MainWindow", u"Create new template", None))
        self.Del.setText(QCoreApplication.translate("MainWindow", u"Delete template", None))
        self.Remove.setText(QCoreApplication.translate("MainWindow", u"==>", None))
        self.Add.setText(QCoreApplication.translate("MainWindow", u"<==", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Template structures", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Available structures", None))
        self.Save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.Exit.setText(QCoreApplication.translate("MainWindow", u"Close", None))
        self.Save_3.setText(QCoreApplication.translate("MainWindow", u"Save as new", None))
        self.Search.setText(QCoreApplication.translate("MainWindow", u"Search", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Structure (task) search:", None))
        self.NextResult.setText(QCoreApplication.translate("MainWindow", u"Next", None))
        self.Reload.setText(QCoreApplication.translate("MainWindow", u"Reload", None))
    # retranslateUi

