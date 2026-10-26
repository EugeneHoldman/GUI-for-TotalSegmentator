# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Installation.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QGroupBox, QLabel, QLineEdit,
    QPushButton, QRadioButton, QSizePolicy, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(531, 258)
        Dialog.setMinimumSize(QSize(531, 258))
        Dialog.setMaximumSize(QSize(531, 258))
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(345, 217, 161, 41))
        font = QFont()
        font.setPointSize(11)
        self.buttonBox.setFont(font)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close|QDialogButtonBox.Save)
        self.groupBox = QGroupBox(Dialog)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(20, 10, 491, 126))
        self.groupBox.setFont(font)
        self.Pip = QRadioButton(self.groupBox)
        self.Pip.setObjectName(u"Pip")
        self.Pip.setGeometry(QRect(20, 23, 82, 17))
        self.Conda = QRadioButton(self.groupBox)
        self.Conda.setObjectName(u"Conda")
        self.Conda.setGeometry(QRect(20, 46, 82, 17))
        self.PathToConda = QLineEdit(self.groupBox)
        self.PathToConda.setObjectName(u"PathToConda")
        self.PathToConda.setGeometry(QRect(20, 86, 381, 28))
        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(20, 66, 221, 16))
        self.BrowseToConda = QPushButton(self.groupBox)
        self.BrowseToConda.setObjectName(u"BrowseToConda")
        self.BrowseToConda.setGeometry(QRect(410, 86, 75, 28))
        self.label_2 = QLabel(Dialog)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(40, 137, 221, 21))
        self.label_2.setFont(font)
        self.TSDefault = QCheckBox(Dialog)
        self.TSDefault.setObjectName(u"TSDefault")
        self.TSDefault.setGeometry(QRect(40, 160, 70, 17))
        self.TSDefault.setFont(font)
        self.PathToTS = QLineEdit(Dialog)
        self.PathToTS.setObjectName(u"PathToTS")
        self.PathToTS.setGeometry(QRect(40, 180, 381, 28))
        self.PathToTS.setFont(font)
        self.BrowseToTS = QPushButton(Dialog)
        self.BrowseToTS.setObjectName(u"BrowseToTS")
        self.BrowseToTS.setGeometry(QRect(430, 180, 75, 28))
        self.BrowseToTS.setFont(font)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.groupBox.setTitle(QCoreApplication.translate("Dialog", u"TS installation method", None))
        self.Pip.setText(QCoreApplication.translate("Dialog", u"Pip", None))
        self.Conda.setText(QCoreApplication.translate("Dialog", u"Conda", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"Path to the conda environment:", None))
        self.BrowseToConda.setText(QCoreApplication.translate("Dialog", u"Browse", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", u"Path to the TS weights:", None))
        self.TSDefault.setText(QCoreApplication.translate("Dialog", u"Default", None))
        self.BrowseToTS.setText(QCoreApplication.translate("Dialog", u"Browse", None))
    # retranslateUi

