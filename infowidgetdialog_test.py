import os

from PyQt4 import QtCore, QtGui, uic


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/infoWidget_test.ui'))

class infoWidgetDialog(QtGui.QWidget, FORM_CLASS):
    def __init__(self, parent=None):
        super(infoWidgetDialog, self).__init__(parent)
        #QtGui.QDockWidget.__init__(self)
        #self.ui = testDock()
        self.setupUi(self)
