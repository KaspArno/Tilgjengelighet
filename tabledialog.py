import os

from PyQt4 import QtCore, QtGui, uic


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/tableDock.ui'))

class TableDialog(QtGui.QDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        super(TableDialog, self).__init__(parent)
        #QtGui.QDockWidget.__init__(self)
        #self.ui = testDock()
        self.setupUi(self)

